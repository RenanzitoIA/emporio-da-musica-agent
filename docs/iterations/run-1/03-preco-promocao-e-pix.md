# Preco promocao e pix

> Price lookup, expired vs. active promotion, non-cumulative Pix discount
>
> Session `eb4a754f6971`

**Cliente:** Quanto custa o Takamine GD20?

<sub>🔧 `search_products({"query": "Takamine GD20", "category": null, "min_price": null, "max_price": null, "only_available": false})`</sub>  

**Lia:** Oi! Aqui é a Lia da Empório da Música — sua música começa aqui. 😊

O Takamine GD20 Dreadnought Natural está R$ 2.199,00 (no PIX fica R$ 2.089,05). Produto disponível.

Quer que eu calcule as opções de parcelamento e frete pra você? Posso ajudar em mais alguma coisa?

---

**Cliente:** Ele não estava com promoção de Oferta Especial?

<sub>🔧 `list_active_promotions({})`</sub>  

**Lia:** Boa pergunta — sou a Lia da Empório da Música. :)

Verifiquei as promoções ativas agora: o Takamine GD20 não consta em Oferta Especial no momento. Ou seja, o preço atual é o informado (R$ 2.199,00 / PIX R$ 2.089,05). Se você viu uma oferta antes, pode ter sido uma promoção encerrada.

Quer que eu:
- procure alternativas em promoção parecidas, ou
- calcule parcelamento e frete para esse GD20?

Posso ajudar em mais alguma coisa?

---

**Cliente:** E o Crafter HT-100? Se eu pagar no Pix tem os 5% em cima da promoção?

<sub>🔧 `get_product_details({"product_id": 90})`</sub>  
<sub>🔧 `calculate_payment_options({"items": [{"product_id": 90, "quantity": 1}]})`</sub>  

**Lia:** Oi — aqui é a Lia, da Empório da Música. Sua música começa aqui. 🙂

O Crafter HT-100 está em promoção: preço promocional R$ 1.967,18 (desconto exclusivo de 18%). Importante: o desconto de 5% no PIX não se aplica sobre preços que já estão em promoção, conforme nossa regra — então o valor no PIX permanece R$ 1.967,18.

Opções de pagamento e frete (para 1 unidade):
- PIX / Débito / Boleto: R$ 1.967,18
- Cartão de crédito: até 12x sem juros — exemplo: 12x de R$ 163,93 (parcelas seguem as regras de parcela mínima)
- Frete em Campo Grande: grátis (pedido acima de R$ 500)
- Frete para outras cidades: calculado por CEP (PAC/SEDEX/Jadlog)

Quer que eu calcule o parcelamento detalhado ou o frete pro seu CEP? Posso ajudar em mais alguma coisa?

---
