# Pedido atrasado e chamado

> Failed verification, late delivery, complaint ticket, out-of-stock product
>
> Session `3a3a12f3e84f`

**Cliente:** Cadê meu pedido 8? Era pra ter chegado faz tempo

**Lia:** Oi — eu sou a Lia, assistente virtual da Empório da Música. Posso checar isso pra você. 😊

Você quis dizer o pedido nº 8 mesmo? Para consultar preciso do número do pedido completo e do nome completo ou telefone usado na compra. Pode me passar esses dados?

---

**Cliente:** Ana Souza

**Lia:** Perfeito, Ana. Só pra confirmar: você não tem o número do pedido aqui? Preciso do número do pedido completo OU do telefone usado na compra pra consultar no sistema. Pode me enviar um desses?

---

**Cliente:** Meu telefone é (67) 99654-7821

<sub>🔧 `lookup_order({"order_id": 8, "customer_name_or_phone": "(67) 99654-7821"})`</sub>  

**Lia:** Ana — seu pedido nº 8 foi enviado. Sinto muito pelo atraso — a entrega estimada era 28/02/2026 e já passou. O código de rastreio é BRJL5544332BR (você pode consultar nos Correios/Jadlog). 📦

Posso abrir um chamado para a equipe verificar com a transportadora e cobrar uma posição?

---

**Cliente:** Quero registrar uma reclamação, pode ser?

<sub>🔧 `open_ticket({"kind": "reclamacao", "summary": "Entrega atrasada do pedido 8 (Kala KA-C Concert Mogno). Entrega estimada 28/02/2026; cliente relata não ter recebido. Solicitar verificação junto à transportadora e posicionamento.", "order_id": 8, "contact": "Ana Souza — (67) 99654-7821"})`</sub>  

**Lia:** Feito — registrei sua reclamação e encaminhei pra equipe. Seu protocolo é EM-00003. A equipe vai retornar em até 24 horas úteis com uma posição sobre a transportadora e a entrega. Desculpa pelo transtorno, Ana. Quer que eu tente rastrear o código BRJL5544332BR agora também?

---

**Cliente:** Pode abrir sim. Aproveitando: o violão Giannini GF-3D tem em estoque?

<sub>🔧 `search_products({"query": "Giannini GF-3D", "category": "Violões", "min_price": null, "max_price": null, "only_available": true})`</sub>  

**Lia:** O GF-3D está esgotado no momento, Ana. Achei alguns Giannini disponíveis que podem te interessar:

- Giannini GF-1R Aço Folk Sunburst — R$ 579,90 (Pix R$ 550,90)  
- Giannini GN-15 Nylon Cedr Natural — R$ 689,00 (Pix R$ 654,55)  
- Giannini GNF-3 CEQ Elétrico Nylon Natural — R$ 1.049,00 (Pix R$ 996,55)  
- Giannini GWNE-7 7 Cordas Nylon Natural — R$ 1.149,00 (Pix R$ 1.091,55)

Quer que eu abra um chamado de interesse pra avisar quando o GF-3D voltar ao estoque, ou prefere que eu encaminhe alguma dessas opções pra equipe verificar disponibilidade/condições? 🎸

---
