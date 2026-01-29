# OLIST DATA PLATFORM - DATA MODEL DOCUMENTATION

**Projeto:** Olist E-commerce Data Platform  
**Autor:** Hyego Jarllys  
**Data:** Janeiro 2025  
**Versão:** 1.0  
**Schema:** olist_raw (Bronze Layer)  

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Modelo Relacional](#modelo-relacional)
3. [Especificação de Tabelas](#especificação-de-tabelas)
4. [Relacionamentos e Cardinalidades](#relacionamentos-e-cardinalidades)
5. [Índices e Performance](#índices-e-performance)
6. [Regras de Negócio](#regras-de-negócio)
7. [Qualidade de Dados](#qualidade-de-dados)

---

## 🎯 VISÃO GERAL

### Contexto de Negócio

O modelo de dados representa transações de e-commerce do marketplace brasileiro **Olist** (2016-2018). Captura o ciclo completo: customers fazem orders → orders contêm items → items são avaliados (reviews) → pagamentos processados.

**Estatísticas Gerais:**
- **Período:** 2016-09-04 a 2018-10-17
- **Total de Registros:** ~850.000
- **Tabelas:** 8
- **Relacionamentos:** 6 Foreign Keys

### Arquitetura de Camadas

```
Bronze Layer (Atual - olist_raw)
├── Dados brutos sem transformação
├── Normalização 3NF parcial
└── Foco: auditabilidade e reprocessamento

Silver Layer (Fase 2 - Planejado)
├── Dados limpos e validados
├── Denormalização seletiva
└── Foco: analytics-ready

Gold Layer (Fase 2 - Planejado)
├── Agregações e métricas
├── Star schema dimensional
└── Foco: dashboards e BI
```

---

## 🗂️ MODELO RELACIONAL

### Entity Relationship Diagram (Simplificado)

```
CUSTOMERS (99k) ──1:N──> ORDERS (99k) ──1:N──> ORDER_ITEMS (112k)
                              │                       │
                              │                       ├──N:1──> PRODUCTS (32k)
                              │                       └──N:1──> SELLERS (3k)
                              │
                              ├──1:N──> ORDER_PAYMENTS (103k)
                              └──1:1──> ORDER_REVIEWS (99k)

GEOLOCATION (19k) [Tabela auxiliar, sem FKs]
```

### Tabelas e Volumetria

| Tabela | Registros | PKs | FKs | Propósito |
|--------|-----------|-----|-----|-----------|
| customers | 99.441 | 1 | 0 | Cadastro de compradores |
| sellers | 3.095 | 1 | 0 | Cadastro de vendedores |
| products | 32.951 | 1 | 0 | Catálogo de produtos |
| geolocation | ~19.000 | 3 (composta) | 0 | CEP → coordenadas |
| orders | 99.441 | 1 | 1 | Pedidos realizados |
| order_items | 112.650 | 2 (composta) | 3 | Linha de itens dos pedidos |
| order_payments | 103.886 | 2 (composta) | 1 | Formas de pagamento |
| order_reviews | 99.224 | 1 | 1 | Avaliações dos pedidos |

---

## 📊 ESPECIFICAÇÃO DE TABELAS

### 1. CUSTOMERS

**Descrição:** Cadastro de compradores da plataforma.

```sql
CREATE TABLE olist_raw.customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_unique_id VARCHAR(50) NOT NULL,
    customer_zip_code_prefix VARCHAR(5) NOT NULL,
    customer_city VARCHAR(100) NOT NULL,
    customer_state VARCHAR(2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Colunas Principais:**
- `customer_id`: ID único por transação (PK)
- `customer_unique_id`: ID da pessoa (permite múltiplos pedidos)
- `customer_state`: UF brasileira (SP, RJ, MG, etc)

**Distribuição Geográfica:**
- SP: 41%, RJ: 12%, MG: 11%
- 27 estados cobertos

**Índices:**
- PK: `customer_id`
- `idx_customers_unique_id`
- `idx_customers_state`

---

### 2. SELLERS

**Descrição:** Vendedores parceiros do marketplace.

```sql
CREATE TABLE olist_raw.sellers (
    seller_id VARCHAR(50) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(5) NOT NULL,
    seller_city VARCHAR(100) NOT NULL,
    seller_state VARCHAR(2) NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Distribuição:**
- SP concentra 77% dos sellers
- 23 estados representados
- Total: 3.095 sellers

---

### 3. PRODUCTS

**Descrição:** Catálogo de produtos.

```sql
CREATE TABLE olist_raw.products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_category_name VARCHAR(100),
    product_name_lenght INTEGER,  -- typo original
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g INTEGER,
    product_length_cm INTEGER,
    product_height_cm INTEGER,
    product_width_cm INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Observações:**
- `product_name_lenght`: typo mantido por compatibilidade
- Campos dimensionais podem ser NULL
- 74 categorias únicas

**Top Categorias:**
1. cama_mesa_banho
2. beleza_saude
3. esporte_lazer

---

### 4. ORDERS

**Descrição:** Pedidos realizados pelos customers.

```sql
CREATE TABLE olist_raw.orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    order_purchase_timestamp TIMESTAMP NOT NULL,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES olist_raw.customers(customer_id)
        ON DELETE CASCADE
);
```

**Status Possíveis:**
- `delivered` (97%)
- `shipped` (1.1%)
- `canceled` (0.6%)
- Outros: processing, invoiced, approved, created

**Métricas de Entrega:**
- Tempo médio: 12 dias
- Taxa de atraso: ~10%

---

### 5. ORDER_ITEMS

**Descrição:** Itens individuais dentro de cada pedido.

```sql
CREATE TABLE olist_raw.order_items (
    order_id VARCHAR(50) NOT NULL,
    order_item_id INTEGER NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    seller_id VARCHAR(50) NOT NULL,
    shipping_limit_date TIMESTAMP NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    freight_value DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    
    PRIMARY KEY (order_id, order_item_id),
    
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES olist_raw.orders(order_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id)
        REFERENCES olist_raw.products(product_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_order_items_seller
        FOREIGN KEY (seller_id)
        REFERENCES olist_raw.sellers(seller_id)
        ON DELETE RESTRICT
);
```

**Características:**
- PK composta: (order_id, order_item_id)
- order_item_id começa em 1 para cada order
- Média: 1.13 itens por pedido
- 77% dos pedidos têm apenas 1 item

---

### 6. ORDER_PAYMENTS

**Descrição:** Formas de pagamento (um pedido pode ter múltiplos).

```sql
CREATE TABLE olist_raw.order_payments (
    order_id VARCHAR(50) NOT NULL,
    payment_sequential INTEGER NOT NULL,
    payment_type VARCHAR(20) NOT NULL,
    payment_installments INTEGER NOT NULL,
    payment_value DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    
    PRIMARY KEY (order_id, payment_sequential),
    
    CONSTRAINT fk_order_payments_order
        FOREIGN KEY (order_id)
        REFERENCES olist_raw.orders(order_id)
        ON DELETE CASCADE
);
```

**Tipos de Pagamento:**
- credit_card: 73.7%
- boleto: 19.5%
- voucher: 5.8%
- debit_card: 1.5%

**Parcelamento:**
- Média: 3.1x
- 51% à vista (1x)
- Máximo: 24x

---

### 7. ORDER_REVIEWS

**Descrição:** Avaliações dos customers.

```sql
CREATE TABLE olist_raw.order_reviews (
    review_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    review_score INTEGER NOT NULL,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP NOT NULL,
    review_answer_timestamp TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    
    CONSTRAINT fk_order_reviews_order
        FOREIGN KEY (order_id)
        REFERENCES olist_raw.orders(order_id)
        ON DELETE CASCADE,
    CONSTRAINT chk_review_score 
        CHECK (review_score BETWEEN 1 AND 5)
);
```

**Distribuição de Scores:**
- 5 estrelas: 57.8%
- 4 estrelas: 19.3%
- 3 estrelas: 8.3%
- 2 estrelas: 3.2%
- 1 estrela: 11.3%

**NPS:** +43.3 (excelente)

---

### 8. GEOLOCATION

**Descrição:** Mapeamento CEP → coordenadas.

```sql
CREATE TABLE olist_raw.geolocation (
    geolocation_zip_code_prefix VARCHAR(5) NOT NULL,
    geolocation_lat DECIMAL(10,8) NOT NULL,
    geolocation_lng DECIMAL(11,8) NOT NULL,
    geolocation_city VARCHAR(100) NOT NULL,
    geolocation_state VARCHAR(2) NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    
    PRIMARY KEY (geolocation_zip_code_prefix, 
                 geolocation_lat, 
                 geolocation_lng)
);
```

**Deduplicação:**
- CSV original: ~1M registros
- Após deduplicação: ~19k (1 por CEP)
- Coordenadas arredondadas para 6 casas decimais

---

## 🔗 RELACIONAMENTOS E CARDINALIDADES

### Mapa de Foreign Keys

```
customers (1) ──┐
                │
                ▼
              orders (N)
                │
                ├──> order_items (N) ──> products (1)
                │                    └─> sellers (1)
                ├──> order_payments (N)
                └──> order_reviews (1)
```

### Tabela de FKs

| FK | From → To | Cardinalidade | On Delete |
|----|-----------|---------------|-----------|
| fk_orders_customer | orders → customers | N:1 | CASCADE |
| fk_order_items_order | order_items → orders | N:1 | CASCADE |
| fk_order_items_product | order_items → products | N:1 | RESTRICT |
| fk_order_items_seller | order_items → sellers | N:1 | RESTRICT |
| fk_order_payments_order | order_payments → orders | N:1 | CASCADE |
| fk_order_reviews_order | order_reviews → orders | 1:1 | CASCADE |

**Política CASCADE vs RESTRICT:**
- **CASCADE:** Deletar order → deleta items/payments/reviews automaticamente
- **RESTRICT:** Impede deletar product/seller se houver order_items referenciando

---

## ⚡ ÍNDICES E PERFORMANCE

### Estratégia de Indexação

**Total de Índices:** 28
- 8 Primary Keys (B-tree automático)
- 20 Índices personalizados

### Índices Principais

| Tabela | Índice | Colunas | Propósito |
|--------|--------|---------|-----------|
| customers | PK | customer_id | Lookups |
| customers | idx_unique | customer_unique_id | Dedup |
| customers | idx_state | customer_state | Filtro geo |
| orders | PK | order_id | Lookups |
| orders | idx_customer | customer_id | JOIN |
| orders | idx_status | order_status | Filtro |
| orders | idx_purchase | order_purchase_timestamp | Range queries |
| order_items | PK | order_id, order_item_id | Composto |
| order_items | idx_order | order_id | JOIN |
| order_items | idx_product | product_id | JOIN |
| order_items | idx_seller | seller_id | JOIN |
| order_items | idx_price | price | Ordenação |

### Benchmarks de Performance

**Queries Típicas:**
```sql
-- Buscar pedidos de customer: ~5ms
SELECT * FROM orders WHERE customer_id = 'xxx';

-- Filtrar por status: ~10ms
SELECT * FROM orders WHERE order_status = 'delivered';

-- JOIN orders + customers (1k rows): ~50ms
SELECT o.*, c.customer_city
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
LIMIT 1000;
```

---

## 📏 REGRAS DE NEGÓCIO

### Validações Implementadas

**Check Constraints:**
```sql
CHECK (review_score BETWEEN 1 AND 5)
```

**Foreign Keys:**
- Garantem integridade referencial
- 100% de órfãos prevenidos

**Defaults:**
```sql
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### Fluxo de Status do Pedido

```
created → approved → processing → invoiced → shipped → delivered

Alternativas:
- canceled (cancelado)
- unavailable (produto indisponível)
```

### Cálculos Derivados

**Valor Total do Pedido:**
```sql
SELECT order_id, SUM(price + freight_value) AS total
FROM order_items
GROUP BY order_id;
```

**Tempo de Entrega:**
```sql
SELECT 
    order_id,
    EXTRACT(DAY FROM 
        order_delivered_customer_date - order_purchase_timestamp
    ) AS delivery_days
FROM orders
WHERE order_delivered_customer_date IS NOT NULL;
```

**Atraso na Entrega:**
```sql
SELECT 
    order_id,
    EXTRACT(DAY FROM 
        order_delivered_customer_date - order_estimated_delivery_date
    ) AS delay_days
FROM orders
WHERE order_delivered_customer_date > order_estimated_delivery_date;
```

---

## ✅ QUALIDADE DE DADOS

### Métricas Validadas

| Métrica | Resultado | Status |
|---------|-----------|--------|
| PKs nulas | 0 | ✅ 100% |
| FKs nulas | 0 | ✅ 100% |
| Duplicatas PKs | 0 | ✅ 100% |
| Órfãos FKs | 0 | ✅ 100% |
| Great Expectations | ~90% | ✅ Excelente |

### Problemas Conhecidos

**1. Campos Opcionais (Esperado):**
- `product_category_name`: 610 nulos (2%)
- `review_comment_*`: 58% sem texto
- `order_approved_at`: nulo para pedidos não aprovados

**2. Typo no Nome de Coluna:**
- `product_name_lenght` (correto seria "length")
- **Decisão:** Mantido por compatibilidade com dataset original

**3. Deduplicação Geolocation:**
- CSV original: ~1M registros (múltiplas coordenadas por CEP)
- Após deduplicação: ~19k (1 coordenada por CEP)
- **Estratégia:** Mantida coordenada mais frequente

---

## 🔄 EVOLUÇÃO FUTURA (Fase 2)

### Silver Layer (Planejado)

**Tabelas Dimensionais:**
```sql
CREATE TABLE olist_silver.dim_customers (
    customer_sk SERIAL PRIMARY KEY,
    customer_id VARCHAR(50),
    customer_unique_id VARCHAR(50),
    current_city VARCHAR(100),
    current_state VARCHAR(2),
    first_order_date DATE,
    last_order_date DATE,
    total_orders INTEGER,
    total_spent DECIMAL(10,2),
    customer_segment VARCHAR(20),  -- RFM
    is_current BOOLEAN
);

CREATE TABLE olist_silver.fact_sales (
    sale_sk SERIAL PRIMARY KEY,
    order_id VARCHAR(50),
    customer_sk INTEGER,
    product_sk INTEGER,
    seller_sk INTEGER,
    date_sk INTEGER,
    quantity INTEGER,
    unit_price DECIMAL(10,2),
    total_value DECIMAL(10,2),
    is_delivered BOOLEAN
);
```

### Métricas Pré-calculadas

**RFM Analysis:**
```sql
CREATE TABLE olist_silver.customer_rfm (
    customer_id VARCHAR(50) PRIMARY KEY,
    recency INTEGER,
    frequency INTEGER,
    monetary DECIMAL(10,2),
    rfm_score VARCHAR(3),
    segment VARCHAR(20)
);
```

---

## 📚 QUERIES DE REFERÊNCIA

### Top 10 Produtos Mais Vendidos

```sql
SELECT 
    p.product_category_name,
    COUNT(DISTINCT oi.order_id) AS total_orders,
    SUM(oi.price) AS revenue
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY p.product_category_name
ORDER BY revenue DESC
LIMIT 10;
```

### Distribuição Geográfica de Vendas

```sql
SELECT 
    c.customer_state,
    COUNT(DISTINCT o.order_id) AS orders,
    SUM(oi.price + oi.freight_value) AS revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY revenue DESC;
```

### Performance de Sellers

```sql
SELECT 
    s.seller_id,
    s.seller_state,
    COUNT(DISTINCT oi.order_id) AS total_sales,
    SUM(oi.price) AS revenue,
    AVG(r.review_score) AS avg_rating
FROM sellers s
JOIN order_items oi ON s.seller_id = oi.seller_id
LEFT JOIN order_reviews r ON oi.order_id = r.order_id
GROUP BY s.seller_id, s.seller_state
HAVING COUNT(DISTINCT oi.order_id) >= 10
ORDER BY revenue DESC;
```

---

## 📖 GLOSSÁRIO

| Termo | Definição |
|-------|-----------|
| CEP | Código de Endereçamento Postal (ZIP code brasileiro) |
| UF | Unidade Federativa (Estado, 2 letras: SP, RJ, etc) |
| Boleto | Método de pagamento brasileiro (bank transfer) |
| RFM | Recency, Frequency, Monetary (segmentação) |
| NPS | Net Promoter Score (métrica de satisfação) |
| SLA | Service Level Agreement (acordo de entrega) |

---

**Última atualização:** 29 de Janeiro de 2025  
**Autor:** Hyego Jarllys  
**Versão:** 1.0  
**Schema:** olist_raw (Bronze Layer)
