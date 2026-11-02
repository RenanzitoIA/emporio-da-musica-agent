# Preco promocao e pix

> Price lookup, expired vs. active promotion, non-cumulative Pix discount
>
> Session `6d56517232a0`

**Cliente:** Quanto custa o Takamine GD20?

<sub>🔧 `search_products({"query": "Takamine GD20", "category": "Violões", "min_price": null, "max_price": null, "only_available": false})`</sub>  

**Lia:** Oi — eu sou a Lia, assistente virtual da Empório da Música. Tudo bem? 😊

O Takamine GD20 Dreadnought (Natural) está R$ 2.199,00 na tabela. No PIX fica R$ 2.089,05.

Quer que eu mostre opções de pagamento em parcelas ou abro um chamado de interesse_compra para a equipe finalizar a venda?

---

**Cliente:** Ele não estava com promoção de Oferta Especial?

<sub>🔧 `get_product_details({"product_id": 95})`</sub>  

**Lia:** Boa pergunta — verifiquei o produto pra você. A promoção "Oferta Especial (12%)" já terminou; foi registrada como promoção encerrada no sistema. 

O preço atual é R$ 2.199,00 (tabela) e R$ 2.089,05 no PIX. Quer que eu consulte as opções de parcelamento e total com cartão, ou prefere que eu abra um chamado de interesse_compra para a equipe finalizar a venda?

---

**Cliente:** E o Crafter HT-100? Se eu pagar no Pix tem os 5% em cima da promoção?

<sub>🔧 `search_products({"query": "Crafter HT-100", "category": "Violões", "min_price": null, "max_price": null, "only_available": false})`</sub>  

**Lia:** O Crafter HT-100 Folk Aço (Natural) está em promoção: preço promocional R$ 1.967,18 (preço de tabela R$ 2.399,00). 

O desconto de 5% no PIX não é aplicado sobre preços que já estão em promoção, então o valor no PIX é o próprio preço promocional R$ 1.967,18. 😉

Quer que eu calcule as opções de parcelamento no cartão e o total com frete (preciso só confirmar quantas unidades)?

---
