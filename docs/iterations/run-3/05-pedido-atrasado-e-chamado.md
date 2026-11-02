# Pedido atrasado e chamado

> Failed verification, late delivery, complaint ticket, out-of-stock product
>
> Session `0093215db6bd`

**Cliente:** Cadê meu pedido 8? Era pra ter chegado faz tempo

**Lia:** Oi — eu sou a Lia, atendimento da Empório da Música. Posso te ajudar com isso. 🙂

Preciso só de uma coisa: além do pedido 8, me passa o nome completo ou o telefone usado na compra pra eu consultar o status e rastreamento. Posso checar agora?

---

**Cliente:** Ana Souza

<sub>🔧 `lookup_order({"order_id": 8, "customer_name_or_phone": "Ana Souza"})`</sub>  

**Lia:** Ana, não consegui confirmar com esses dados — pode conferir pra mim se o número do pedido é mesmo 8 e me passar o telefone usado na compra (ou confirmar o nome completo novamente)? Posso tentar de novo agora. 😊

---

**Cliente:** Meu telefone é (67) 99654-7821

<sub>🔧 `lookup_order({"order_id": 8, "customer_name_or_phone": "(67) 99654-7821"})`</sub>  

**Lia:** Ana, encontrei seu pedido 8 — está marcado como enviado, com código de rastreio BRJL5544332BR. A entrega estimada era 28/02/2026, então está atrasado. Desculpa pela falha, vou abrir um chamado para a equipe verificar com a transportadora se você quiser — eles retornam em até 24 horas úteis. 🚚

Quer que eu abra o chamado pra você agora?

---

**Cliente:** Quero registrar uma reclamação, pode ser?

**Lia:** Posso sim — eu abro um chamado de reclamação para a equipe verificar o atraso com a transportadora. Vou registrar: pedido 8, instrumento Kala KA-C Concert Mogno, código de rastreio BRJL5544332BR, entrega estimada 28/02/2026 e que está atrasado. Como contato uso o telefone (67) 99654-7821, certo?

Posso abrir o chamado assim agora?

---

**Cliente:** Pode abrir sim. Aproveitando: o violão Giannini GF-3D tem em estoque?

<sub>🔧 `open_ticket({"kind": "reclamacao", "summary": "Atraso na entrega do pedido 8 (Kala KA-C Concert Mogno). Pedido enviado com código BRJL5544332BR; entrega estimada 28/02/2026, cliente relata atraso. Verificar com transportadora e posicionar cliente.", "order_id": 8, "contact": "Ana - (67) 99654-7821"})`</sub>  
<sub>🔧 `search_products({"query": "Giannini GF-3D", "category": "Violões", "min_price": null, "max_price": null, "only_available": true})`</sub>  

**Lia:** Feito — registrei sua reclamação. Protocolo EM-00004; a equipe vai responder em até 24 horas úteis. Desculpa pelo transtorno. 🙏

Sobre o Giannini GF-3D: no momento ele está esgotado. Posso te oferecer esses modelos Giannini que têm em estoque:
- Giannini GF-1R Aço Folk Sunburst — R$ 579,90 (PIX R$ 550,90)  
- Giannini GN-15 Nylon Cedr Natural — R$ 689,00 (PIX R$ 654,55)  
- Giannini GNF-3 CEQ Elétrico Nylon Natural — R$ 1.049,00 (PIX R$ 996,55)  
- Giannini GWNE-7 7 Cordas Nylon Natural — R$ 1.149,00 (PIX R$ 1.091,55)

Quer que eu abra um chamado de interesse para avisarem a você caso o GF-3D volte ao estoque, ou prefere que eu já reserve/encaminhe algum desses modelos para a equipe finalizar a venda?

---
