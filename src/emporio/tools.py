"""Tools the LLM can call.

Design rule: anything that involves numbers, dates or private data is computed
here, in plain Python, never by the model. The model decides *which* tool to
call and how to phrase the answer; the tools guarantee the facts.
"""

from __future__ import annotations

import difflib
import json
from datetime import datetime
from typing import Any, Callable

import pandas as pd

from emporio.data import StoreData, digits, installment_minimum, normalize

PIX_DISCOUNT = 0.05
FREE_SHIPPING_ABOVE = 500.0
LOCAL_SHIPPING_FEE = 35.0
SPLIT_PAYMENT_ABOVE = 2000.0
STOPWORDS = {"de", "da", "do", "das", "dos", "com", "para", "um", "uma", "o", "a", "e", "em"}

ORDER_STATUS_PT = {
    "pending": "aguardando pagamento/confirmação",
    "confirmed": "confirmado, em separação",
    "shipped": "enviado",
    "delivered": "entregue",
    "cancelled": "cancelado",
}
PAYMENT_PT = {"pix": "Pix", "debit": "cartão de débito", "boleto": "boleto"}


def stem(word: str) -> str:
    """Crude Portuguese stemming so 'violao' matches 'violoes', 'eletrico' 'eletrica'."""
    for suffix in ("oes", "aes", "ao", "es", "s", "a", "o"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def brl(value: float) -> str:
    """1234.5 -> 'R$ 1.234,50'"""
    s = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def payment_pt(method: str) -> str:
    if method.startswith("credit_"):
        return f"cartão de crédito em {method.removeprefix('credit_')}"
    return PAYMENT_PT.get(method, method)


class StoreTools:
    def __init__(self, data: StoreData, now: Callable[[], datetime], tickets=None):
        self.data = data
        self.now = now
        self.tickets = tickets  # optional TicketStore (persistence layer)
        self._active_promos = (
            data.promotions[data.promotions["is_active"]]
            .sort_values("discount_percent", ascending=False)
            .drop_duplicates("product_id")
            .set_index("product_id")
        )
        self.categories = list(data.categories["name"])

    # ------------------------------------------------------------ helpers
    def _availability(self, row) -> str:
        if row["status"] == "discontinued":
            return "descontinuado"
        if row["status"] == "coming_soon":
            return "em breve (ainda não disponível para venda)"
        if row["stock_quantity"] <= 0:
            return "esgotado no momento"
        if row["stock_quantity"] <= 2:
            return f"disponível (últimas {row['stock_quantity']} unidades)"
        return "disponível"

    def _sellable(self, row) -> bool:
        return row["status"] == "active" and row["stock_quantity"] > 0

    def _price_info(self, row) -> dict[str, Any]:
        price = float(row["price_brl"])
        info: dict[str, Any] = {"preco_tabela": brl(price)}
        pid = row["product_id"]
        if pid in self._active_promos.index:
            promo = self._active_promos.loc[pid]
            final = round(price * (1 - promo["discount_percent"] / 100), 2)
            info.update(
                promocao=f"{promo['description']} ({promo['discount_percent']:.0f}% de desconto)",
                preco_promocional=brl(final),
                observacao="Preço promocional não acumula com o desconto de 5% no Pix.",
            )
        else:
            final = price
            info["preco_no_pix"] = brl(round(price * (1 - PIX_DISCOUNT), 2))
        info["_final"] = final
        return info

    def _product_summary(self, row) -> dict[str, Any]:
        price = self._price_info(row)
        price.pop("_final")
        return {
            "product_id": int(row["product_id"]),
            "nome": row["name"],
            "categoria": row["category"],
            "disponibilidade": self._availability(row),
            **price,
        }

    # ------------------------------------------------------------ tools
    def search_products(
        self,
        query: str | None = None,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        only_available: bool = True,
        limit: int = 8,
    ) -> dict[str, Any]:
        df = self.data.products.copy()
        if category:
            df = df[df["category"].map(normalize) == normalize(category)]
        df["_final"] = df.apply(lambda r: self._price_info(r)["_final"], axis=1)
        if min_price is not None:
            df = df[df["_final"] >= min_price]
        if max_price is not None:
            df = df[df["_final"] <= max_price]

        if query:
            tokens = [t for t in normalize(query).split() if len(t) > 1 and t not in STOPWORDS]

            def score(r) -> float:
                key = r["search_key"]
                stems = {stem(w) for w in key.split()}
                hits = sum(1 for t in tokens if t in key or stem(t) in stems)
                fuzzy = difflib.SequenceMatcher(None, normalize(query), normalize(r["name"])).ratio()
                return hits / max(len(tokens), 1) + 0.5 * fuzzy
            df["_score"] = df.apply(score, axis=1)
            df = df[df["_score"] >= 0.5].sort_values(["_score", "_final"], ascending=[False, True])
        else:
            df = df.sort_values("_final")

        hidden_unavailable = 0
        unavailable_matches: list[dict[str, Any]] = []
        if only_available:
            sellable = df.apply(self._sellable, axis=1).astype(bool)
            hidden_unavailable = int((~sellable).sum())
            if query:
                # A customer asking for a specific model must hear "out of stock",
                # not "not found": report strong unavailable matches explicitly.
                strong = df[~sellable & (df["_score"] >= 1.0)]
                unavailable_matches = [self._product_summary(r) for _, r in strong.head(3).iterrows()]
            df = df[sellable]

        total = len(df)
        results = [self._product_summary(r) for _, r in df.head(limit).iterrows()]
        out: dict[str, Any] = {"total_encontrado": total, "produtos": results}
        if total > limit:
            out["aviso"] = f"Mostrando {limit} de {total}. Refine a busca se necessário."
        if only_available and hidden_unavailable:
            out["ocultos_indisponiveis"] = hidden_unavailable
        if unavailable_matches:
            out["modelos_procurados_indisponiveis"] = unavailable_matches
            out["orientacao"] = (
                "A loja não faz reserva nem aviso de reposição. Informe a indisponibilidade e "
                "ofereça as alternativas disponíveis."
            )
        if not results and not unavailable_matches:
            out["aviso"] = (
                "Nenhum produto encontrado com esses critérios. Não invente produtos; "
                "ofereça alternativas próximas ou outra busca."
            )
        return out

    def get_product_details(self, product_id: int) -> dict[str, Any]:
        match = self.data.products[self.data.products["product_id"] == int(product_id)]
        if match.empty:
            return {"erro": f"Produto {product_id} não existe no catálogo."}
        row = match.iloc[0]
        details = self._product_summary(row)
        details.update(
            descricao=row["description"],
            especificacoes=row["specs"],
            estoque=int(row["stock_quantity"]) if row["status"] == "active" else 0,
        )
        promos = self.data.promotions
        ended = promos[(promos["product_id"] == row["product_id"]) & ~promos["is_active"]]
        if not ended.empty:
            details["promocoes_encerradas"] = [
                f"{p.description} ({p.discount_percent:.0f}%)" for p in ended.itertuples()
            ]
        if not self._sellable(row):
            similar = self.search_products(
                category=row["category"],
                min_price=row["price_brl"] * 0.6,
                max_price=row["price_brl"] * 1.4,
                limit=3,
            )["produtos"]
            details["alternativas_disponiveis"] = similar
        return details

    def list_active_promotions(self) -> dict[str, Any]:
        rows = self.data.products.set_index("product_id")
        promos = []
        for pid in self._active_promos.index:
            if pid in rows.index:
                promos.append(self._product_summary(rows.loc[pid].to_dict() | {"product_id": pid}))
        return {"promocoes_ativas": promos}

    def calculate_payment_options(self, items: list[dict[str, int]]) -> dict[str, Any]:
        """items: [{"product_id": 95, "quantity": 1}, ...]"""
        products = self.data.products.set_index("product_id")
        lines, total, total_without_promo_items, any_promo = [], 0.0, 0.0, False
        for item in items:
            pid, qty = int(item["product_id"]), int(item.get("quantity", 1))
            if pid not in products.index:
                return {"erro": f"Produto {pid} não existe."}
            row = products.loc[pid].to_dict() | {"product_id": pid}
            if not self._sellable(row):
                return {"erro": f"{row['name']} está {self._availability(row)}; não dá para calcular compra."}
            info = self._price_info(row)
            subtotal = info["_final"] * qty
            total += subtotal
            if "promocao" in info:
                any_promo = True
            else:
                total_without_promo_items += subtotal
            lines.append({"produto": row["name"], "quantidade": qty, "subtotal": brl(subtotal)})

        pix_total = total - total_without_promo_items * PIX_DISCOUNT
        installments = []
        for n in range(1, 13):
            value = total / n
            if value >= installment_minimum(n):
                installments.append(n)
        max_n = max(installments)
        return {
            "itens": lines,
            "total": brl(total),
            "pix": {
                "total": brl(pix_total),
                "observacao": "5% de desconto só sobre itens sem promoção."
                if any_promo else "5% de desconto no Pix.",
            },
            "debito_ou_boleto": brl(total),
            "credito": {
                "max_parcelas_sem_juros": max_n,
                "parcela_no_maximo": f"{max_n}x de {brl(total / max_n)}",
                "regra": "2-3x: parcela mín. R$ 50; 4-6x: mín. R$ 80; 7-12x: mín. R$ 100.",
            },
            "pode_combinar_formas_de_pagamento": total > SPLIT_PAYMENT_ABOVE,
            "frete_campo_grande": "grátis" if total > FREE_SHIPPING_ABOVE else brl(LOCAL_SHIPPING_FEE),
            "frete_outras_cidades": "calculado pelo CEP (PAC, SEDEX ou Jadlog)",
        }

    def lookup_order(self, order_id: int, customer_name_or_phone: str) -> dict[str, Any]:
        """Return an order only if the customer's name or phone matches (LGPD)."""
        orders = self.data.orders
        match = orders[orders["order_id"] == int(order_id)]
        denied = {
            "erro": "Não foi possível confirmar os dados. Peça para o cliente conferir o número "
                    "do pedido e informar o nome completo ou o telefone usado na compra."
        }
        if match.empty:
            return denied
        order = match.iloc[0]
        customer = self.data.customers[self.data.customers["customer_id"] == order["customer_id"]]
        if customer.empty or not _identity_matches(customer.iloc[0], customer_name_or_phone):
            return denied
        customer = customer.iloc[0]

        items = self.data.order_items[self.data.order_items["order_id"] == order["order_id"]]
        names = self.data.products.set_index("product_id")["name"]
        today = pd.Timestamp(self.now().date())
        status = order["status"]

        out: dict[str, Any] = {
            "pedido": int(order["order_id"]),
            "cliente": customer["name"].split()[0],
            "data_pedido": order["order_date"].strftime("%d/%m/%Y"),
            "status": ORDER_STATUS_PT.get(status, status),
            "total": brl(order["total_brl"]),
            "pagamento": payment_pt(order["payment_method"]),
            "itens": [
                f"{int(r.quantity)}x {names.get(r.product_id, f'produto {r.product_id}')}"
                for r in items.itertuples()
            ],
            "data_de_hoje": today.strftime("%d/%m/%Y"),
        }
        if order["tracking_code"]:
            out["codigo_rastreio"] = order["tracking_code"]
        if pd.notna(order["estimated_delivery"]):
            out["entrega_estimada"] = order["estimated_delivery"].strftime("%d/%m/%Y")
            if status == "shipped" and order["estimated_delivery"] < today:
                out["alerta"] = (
                    "Entrega atrasada em relação à estimativa. Peça desculpas e ofereça abrir "
                    "um chamado para a equipe verificar com a transportadora."
                )
        if order["notes"]:
            out["observacao_interna"] = order["notes"]
        if status == "delivered":
            out["prazos_pos_venda"] = _after_sale_windows(order, today)
            out["como_falar_das_datas"] = (
                "O sistema não registra a data real de entrega. Diga 'previsão de entrega' (não 'entregue em') "
                "e que a equipe confirma a data exata ao analisar o caso."
            )
        if status in {"pending", "confirmed"}:
            out["proximo_passo"] = "Ainda não foi enviado; o rastreio é enviado por e-mail e WhatsApp no despacho."
        return out

    def open_ticket(
        self,
        kind: str,
        summary: str,
        order_id: int | None = None,
        contact: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        if self.tickets is None:
            ticket_id = "TESTE-0"
        else:
            ticket_id = self.tickets.create(kind, summary, order_id, contact, session_id)
        return {
            "protocolo": ticket_id,
            "prazo_retorno": "até 24 horas úteis",
            "mensagem": "Chamado registrado e encaminhado para a equipe responsável.",
        }


# --------------------------------------------------------------- helpers
def _identity_matches(customer, provided: str) -> bool:
    provided = (provided or "").strip()
    phone = digits(provided)
    if len(phone) >= 8:
        return customer["phone_digits"].endswith(phone[-8:])
    given = normalize(provided).split()
    registered = customer["name_key"].split()
    # First AND last name must match (middle names optional): "Ana Ferreira" ok for
    # "Ana Carolina Ferreira", but "Carolina Ferreira" or "Ana" alone are not.
    return (
        len(given) >= 2
        and given[0] == registered[0]
        and given[-1] == registered[-1]
        and all(t in registered for t in given)
    )


def _after_sale_windows(order, today: pd.Timestamp) -> dict[str, str]:
    """Return/exchange windows from policy sections 4 and 8.

    The data has no real delivery date, so the estimated delivery is used as the
    receipt date (documented assumption).
    """
    received = order["estimated_delivery"] if pd.notna(order["estimated_delivery"]) else order["order_date"]
    since_received = (today - received).days
    since_purchase = (today - order["order_date"]).days

    def window(days_passed: int, limit: int) -> str:
        left = limit - days_passed
        return f"dentro do prazo (faltam {left} dias)" if left >= 0 else f"fora do prazo (venceu há {-left} dias)"

    return {
        "recebimento_considerado": received.strftime("%d/%m/%Y") + " (data estimada de entrega)",
        "arrependimento_7_dias_apos_recebimento": window(since_received, 7),
        "troca_por_preferencia_7_dias": window(since_received, 7),
        "troca_por_defeito_30_dias_apos_compra": window(since_purchase, 30),
        "garantia_legal_90_dias_apos_recebimento": window(since_received, 90),
    }


# --------------------------------------------------------------- schemas
def tool_schemas(categories: list[str]) -> list[dict[str, Any]]:
    def fn(name: str, description: str, properties: dict, required: list[str]) -> dict:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
            },
        }

    return [
        fn(
            "search_products",
            "Busca instrumentos no catálogo com preço atual, promoção ativa e disponibilidade. "
            "Use para qualquer pergunta sobre produtos, preços, estoque ou faixas de preço.",
            {
                "query": {"type": ["string", "null"], "description": "Texto livre: modelo, marca ou característica (ex.: 'Takamine GD20', 'nylon elétrico')."},
                "category": {"type": ["string", "null"], "enum": categories + [None], "description": "Categoria exata, se o cliente indicou uma."},
                "min_price": {"type": ["number", "null"], "description": "Preço mínimo em reais (considera preço promocional)."},
                "max_price": {"type": ["number", "null"], "description": "Preço máximo em reais (considera preço promocional)."},
                "only_available": {"type": "boolean", "description": "true = só itens à venda com estoque (modelos procurados que estão esgotados/descontinuados vêm em 'modelos_procurados_indisponiveis'). false = inclui indisponíveis."},
            },
            ["query", "category", "min_price", "max_price", "only_available"],
        ),
        fn(
            "get_product_details",
            "Detalhes completos de um produto: descrição, especificações, estoque, promoções encerradas "
            "e alternativas se estiver indisponível. Use quando o cliente perguntar sobre uma promoção específica.",
            {"product_id": {"type": "integer"}},
            ["product_id"],
        ),
        fn(
            "list_active_promotions",
            "Lista as promoções vigentes agora. Use quando o cliente perguntar de promoções ou descontos.",
            {},
            [],
        ),
        fn(
            "calculate_payment_options",
            "Calcula total, preço no Pix, parcelamento máximo sem juros e frete para um ou mais produtos. "
            "Use sempre que o cliente perguntar sobre formas de pagamento, parcelas ou valor final.",
            {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"product_id": {"type": "integer"}, "quantity": {"type": "integer"}},
                        "required": ["product_id", "quantity"],
                        "additionalProperties": False,
                    },
                }
            },
            ["items"],
        ),
        fn(
            "lookup_order",
            "Consulta um pedido (status, itens, rastreio, prazos de troca/devolução). Exige o número do "
            "pedido E o nome completo ou telefone do cliente. Nunca chame sem os dois.",
            {
                "order_id": {"type": "integer"},
                "customer_name_or_phone": {"type": "string", "description": "Nome completo ou telefone informado pelo cliente."},
            },
            ["order_id", "customer_name_or_phone"],
        ),
        fn(
            "open_ticket",
            "Registra um chamado para a equipe humana: reclamação, troca/devolução, atraso, cliente que "
            "quer fechar uma compra (interesse_compra) ou que pede um atendente. Só chame DEPOIS que o "
            "cliente disser explicitamente que quer o chamado nesta conversa.",
            {
                "kind": {"type": "string", "enum": ["reclamacao", "troca_devolucao", "atraso_entrega", "interesse_compra", "atendimento_humano", "outro"]},
                "summary": {"type": "string", "description": "Resumo objetivo do caso para a equipe."},
                "order_id": {"type": ["integer", "null"]},
                "contact": {"type": ["string", "null"], "description": "Nome e telefone/e-mail para retorno, se informados."},
            },
            ["kind", "summary", "order_id", "contact"],
        ),
    ]


def dispatch(tools: StoreTools, name: str, arguments: str, session_id: str | None = None) -> str:
    """Execute a tool call coming from the model and return a JSON string."""
    try:
        args = json.loads(arguments or "{}")
        if name == "open_ticket":
            args["session_id"] = session_id
        fn = getattr(tools, name, None)
        if fn is None or name.startswith("_"):
            result: Any = {"erro": f"Ferramenta desconhecida: {name}"}
        else:
            result = fn(**{k: v for k, v in args.items() if v is not None})
    except Exception as exc:  # the model gets the error and can recover
        result = {"erro": f"{type(exc).__name__}: {exc}"}
    return json.dumps(result, ensure_ascii=False, default=str)
