# Preco promocao e pix

> Price lookup, expired vs. active promotion, non-cumulative Pix discount
>
> Session `0efa42e6aaf1`

**Cliente:** Quanto custa o Takamine GD20?

<sub>🔧 `search_products({"query": "Takamine GD20", "category": "Violões", "min_price": null, "max_price": null, "only_available": true})`</sub>  

**Lia:** Oi! Sou a Lia, assistente virtual da Empório da Música — prazer 🎸

O Takamine GD20 Dreadnought (Natural) está por R$ 2.199,00. No PIX fica por R$ 2.089,05.

Quer que eu calcule as opções de parcelamento e o valor total (cartão, parcelas e frete)?

---

**Cliente:** Ele não estava com promoção de Oferta Especial?

<sub>🔧 `get_product_details({"product_id": 95})`</sub>  

**Lia:** Boa pergunta — essa "Oferta Especial (12%)" terminou. O preço atual do Takamine GD20 é R$ 2.199,00 (PIX R$ 2.089,05). 

Quer que eu calcule as opções de parcelamento no cartão e o frete pro seu CEP? 🎸

---

**Cliente:** E o Crafter HT-100? Se eu pagar no Pix tem os 5% em cima da promoção?

<sub>🔧 `search_products({"query": "Crafter HT-100", "category": "Violões", "min_price": null, "max_price": null, "only_available": false})`</sub>  

**Lia:** O Crafter HT-100 Folk (Aço) está em promoção: R$ 1.967,18 (preço promocional — preço de tabela R$ 2.399,00). 

O desconto de 5% no PIX não é cumulativo sobre preços promocionais, então esse valor promocional já é o preço final (sem desconto extra no PIX). 🎸

Quer que eu calcule as opções de parcelamento e o frete pro seu CEP?

---
