from datetime import datetime

import pytest

from emporio.data import StoreData
from emporio.tools import StoreTools, brl

NOW = datetime(2026, 3, 23, 10, 30)


@pytest.fixture(scope="module")
def tools():
    return StoreTools(StoreData.load(), now=lambda: NOW)


def names(result):
    return [p["nome"] for p in result["produtos"]]


def test_brl_format():
    assert brl(1234.5) == "R$ 1.234,50"
    assert brl(11499) == "R$ 11.499,00"


def test_price_lookup_by_model(tools):
    result = tools.search_products(query="Takamine GD20")
    first = result["produtos"][0]
    assert first["nome"].startswith("Takamine GD20")
    assert first["preco_tabela"] == "R$ 2.199,00"
    assert first["preco_no_pix"] == "R$ 2.089,05"


def test_guitars_up_to_1000_only_available(tools):
    result = tools.search_products(category="Violões", max_price=1000)
    assert result["produtos"], "expected some violões up to R$1000"
    assert "Giannini GF-3D Dreadnought Sunburst" not in names(result)  # out of stock
    assert result["ocultos_indisponiveis"] >= 1
    for p in result["produtos"]:
        assert p["disponibilidade"].startswith("disponível")


def test_active_promotion_blocks_pix_discount(tools):
    # Product 90 (Crafter HT-100) has an active 18% promotion.
    details = tools.get_product_details(90)
    assert details["preco_promocional"] == brl(2399 * 0.82)
    assert "preco_no_pix" not in details


def test_expired_promotion_not_applied(tools):
    # Product 95 (Takamine GD20) only has an inactive promotion.
    assert "promocao" not in tools.get_product_details(95)


def test_unavailable_product_suggests_alternatives(tools):
    details = tools.get_product_details(96)  # active but stock 0
    assert details["disponibilidade"] == "esgotado no momento"
    assert details["alternativas_disponiveis"]


def test_discontinued_and_coming_soon(tools):
    assert tools.get_product_details(113)["disponibilidade"] == "descontinuado"
    assert tools.get_product_details(136)["estoque"] == 0  # discontinued: stock hidden
    assert tools.get_product_details(130)["disponibilidade"].startswith("em breve")


def test_installment_rules(tools):
    # R$ 349.90: 4x = 87.48 >= 80 ok, 5x = 69.98 < 80 -> max 4x
    calc = tools.calculate_payment_options([{"product_id": 120, "quantity": 1}])
    assert calc["credito"]["max_parcelas_sem_juros"] == 4
    assert calc["frete_campo_grande"] == "R$ 35,00"
    # R$ 2.199: 12x = 183.25 -> 12x; above R$ 2.000 allows split payment
    calc = tools.calculate_payment_options([{"product_id": 95, "quantity": 1}])
    assert calc["credito"]["max_parcelas_sem_juros"] == 12
    assert calc["pode_combinar_formas_de_pagamento"] is True
    assert calc["frete_campo_grande"] == "grátis"


def test_pix_only_on_non_promo_items(tools):
    calc = tools.calculate_payment_options(
        [{"product_id": 90, "quantity": 1}, {"product_id": 95, "quantity": 1}]
    )
    promo_price = 2399 * 0.82
    assert calc["pix"]["total"] == brl(promo_price + 2199 * 0.95)


def test_order_requires_identity(tools):
    assert "erro" in tools.lookup_order(1, "Maria")
    assert "erro" in tools.lookup_order(1, "Lucas Mendes")  # wrong customer (order 1 is customer 3)
    assert "erro" in tools.lookup_order(999, "Lucas Mendes")  # same message: no enumeration


def test_order_lookup_by_name_and_phone(tools):
    data = tools.data
    customer = data.customers[data.customers["customer_id"] == 2].iloc[0]
    by_phone = tools.lookup_order(8, customer["phone"])
    assert by_phone["status"] == "enviado"
    assert "alerta" in by_phone  # estimated 28/02, simulated today 23/03
    first, *_, last = customer["name"].split()
    assert tools.lookup_order(8, f"{first} {last}")["pedido"] == 8


def test_delivered_order_return_windows(tools):
    data = tools.data
    customer_id = int(data.orders.loc[data.orders["order_id"] == 7, "customer_id"].iloc[0])
    customer = data.customers[data.customers["customer_id"] == customer_id].iloc[0]
    order = tools.lookup_order(7, customer["phone"])
    windows = order["prazos_pos_venda"]
    assert windows["arrependimento_7_dias_apos_recebimento"].startswith("fora do prazo")
    assert windows["garantia_legal_90_dias_apos_recebimento"].startswith("dentro do prazo")


def test_search_handles_accents_and_plurals(tools):
    assert tools.search_products(query="violao nylon eletrico")["produtos"][0]["categoria"] == "Violões"


def test_identity_requires_first_and_last_name(tools):
    # Order 8 belongs to "Ana Carolina Ferreira".
    assert tools.lookup_order(8, "Ana Ferreira")["pedido"] == 8
    assert "erro" in tools.lookup_order(8, "Carolina Ferreira")
    assert "erro" in tools.lookup_order(8, "Ana")
    assert "erro" in tools.lookup_order(8, "Ana Souza")


def test_out_of_stock_model_is_reported_not_hidden(tools):
    result = tools.search_products(query="Giannini GF-3D", only_available=True)
    assert result["modelos_procurados_indisponiveis"][0]["disponibilidade"] == "esgotado no momento"


def test_ended_promotions_are_listed(tools):
    assert tools.get_product_details(95)["promocoes_encerradas"] == ["Oferta Especial (12%)"]
