# Pedido atrasado e chamado

> Failed verification, late delivery, complaint ticket, out-of-stock product
>
> Session `553fac903fc5`

**Cliente:** Cadê meu pedido 8? Era pra ter chegado faz tempo

**Lia:** Oi — sou a Lia, assistente virtual do Empório da Música. Vou checar seu pedido pra você. 😊

Tenho o número do pedido (8). Pode me informar o nome completo ou o telefone usado na compra pra eu buscar no sistema?

---

**Cliente:** Ana Souza

<sub>🔧 `lookup_order({"order_id": 8, "customer_name_or_phone": "Ana Souza"})`</sub>  

**Lia:** Não consegui confirmar com "Ana Souza" e o pedido 8 — pode conferir pra mim o telefone usado na compra ou o nome completo (como está no pedido), por favor? 😊

---

**Cliente:** Meu telefone é (67) 99654-7821

<sub>🔧 `lookup_order({"order_id": 8, "customer_name_or_phone": "(67) 99654-7821"})`</sub>  

**Lia:** Ana, sinto muito pelo atraso — vamos resolver isso. 😕  
Seu pedido 8 (1x Kala KA-C Concert Mogno) consta como "enviado". Código de rastreio: BRJL5544332BR. A entrega estimada era 28/02/2026, então está atrasado em relação à previsão.

Posso abrir um chamado para a equipe verificar com a transportadora e agilizar a entrega? (se quiser, já registro com seu telefone para retorno)

---

**Cliente:** Quero registrar uma reclamação, pode ser?

**Lia:** Perfeito, Ana — eu posso registrar a reclamação para a equipe. Vou abrir um chamado informando que o pedido 8 (Kala KA-C Concert Mogno) está atrasado, com o código de rastreio BRJL5544332BR, pedindo verificação com a transportadora e retorno por telefone (67) 99654-7821.  

Posso abrir o chamado com esse resumo e contato agora?

---

**Cliente:** Pode abrir sim. Aproveitando: o violão Giannini GF-3D tem em estoque?

<sub>🔧 `open_ticket({"kind": "reclamacao", "summary": "Reclamação: pedido 8 (Kala KA-C Concert Mogno) atrasado. Enviado com rastreio BRJL5544332BR; solicitar verificação com transportadora e posicionamento por telefone.", "order_id": 8, "contact": "(67) 99654-7821"})`</sub>  
<sub>🔧 `search_products({"query": "Giannini GF-3D", "category": "Violões", "min_price": null, "max_price": null, "only_available": true})`</sub>  

**Lia:** Chamado registrado com sucesso — protocolo EM-00005. A equipe vai retornar em até 24 horas úteis sobre o atraso do seu pedido 8.

Sobre o Giannini GF-3D: infelizmente está esgotado no momento. Posso sugerir alguns violões Giannini que estão disponíveis agora:
- Giannini GF-1R Aço Folk Sunburst — R$ 579,90 (Pix R$ 550,90)  
- Giannini GN-15 Nylon Cedr Natural — R$ 689,00 (Pix R$ 654,55)  
- Giannini GNF-3 CEQ Elétrico Nylon Natural — R$ 1.049,00 (Pix R$ 996,55)  
- Giannini GWNE-7 7 Cordas Nylon Natural — R$ 1.149,00 (Pix R$ 1.091,55)

A loja não faz reserva nem aviso automático de reposição para produtos esgotados. Quer que eu abra um chamado de interesse de compra para a equipe (para eles entrarem em contato se houver reposição ou alternativa), ou prefere que eu traga condições de pagamento/parcelamento de algum dos modelos disponíveis?

---
