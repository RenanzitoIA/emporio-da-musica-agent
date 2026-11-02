# Catalogo violoes ate 1000

> Catalog search with price filter + installment follow-up
>
> Session `e75779c36ee9`

**Cliente:** Oi! Quais opções de violões disponíveis custando até R$1000?

<sub>🔧 `search_products({"query": null, "category": "Violões", "min_price": null, "max_price": 1000, "only_available": true})`</sub>  

**Lia:** Oi! Sou a Lia, assistente virtual da Empório da Música — prazer. Vou listar os violões disponíveis até R$1.000 (preço tabela e preço no PIX):

- Tagima Memphis AC-39 Nylon Natural — R$ 429,90 (PIX R$ 408,40)  
- Rozini RC-104 Nylon Estudante — R$ 459,90 (PIX R$ 436,90)  
- Shelby SN-100 Folk Aço Preto — R$ 549,00 (PIX R$ 521,55)  
- Giannini GF-1R Aço Folk Sunburst — R$ 579,90 (PIX R$ 550,90)  
- Yamaha C40 Nylon Natural — R$ 599,90 (PIX R$ 569,90)  
- Giannini GN-15 Nylon Cedr Natural — R$ 689,00 (PIX R$ 654,55)  
- Yamaha F310 Aço Natural — R$ 699,90 (PIX R$ 664,90)  
- Tagima Dallas Tuner Aço Natural — R$ 749,00 (PIX R$ 711,55)

Quer que eu calcule as opções de pagamento (parcelas, valor no PIX e frete) para algum desses modelos?

---

**Cliente:** Gostei do Yamaha C40. Dá pra parcelar? E o frete pra Campo Grande?

<sub>🔧 `calculate_payment_options({"items": [{"product_id": 81, "quantity": 1}]})`</sub>  

**Lia:** Boa escolha — o Yamaha C40 está disponível. Resumo das formas de pagamento e frete para Campo Grande:

- PIX: R$ 569,90 (5% de desconto)  
- Cartão de débito / boleto: R$ 599,90  
- Cartão de crédito: até 6x sem juros — 6x de R$ 99,98 (regras: 2–3x parcela mínima R$50; 4–6x mínima R$80)  
- Frete para a região metropolitana de Campo Grande: grátis (prazo de entrega 1 a 3 dias úteis — prazo estimado)

Quer que eu abra um chamado de interesse_compra para a equipe fechar a venda e combinar retirada/entrega? 😊

---
