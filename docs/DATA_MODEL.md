# OLIST DATA PLATFORM - DATA MODEL DOCUMENTATION

**Projeto:** Olist E-commerce Data Platform  
**Autor:** Hyego Jarllys  
**Data:** Janeiro 2025  
**Versão:** 1.0  
**Schema:** olist_raw  

---

## 📋 ÍNDICE

1. [Visão Geral do Modelo](#visão-geral-do-modelo)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Dicionário de Dados](#dicionário-de-dados)
4. [Relacionamentos e Cardinalidades](#relacionamentos-e-cardinalidades)
5. [Regras de Negócio](#regras-de-negócio)
6. [Queries de Referência](#queries-de-referência)
7. [Análises Possíveis](#análises-possíveis)

---

## 🎯 VISÃO GERAL DO MODELO

### Contexto de Negócio

O dataset Olist representa transações de um marketplace brasileiro de e-commerce. O modelo captura:

- **Clientes** que fazem pedidos
- **Pedidos** compostos por múltiplos itens
- **Itens** vendidos por sellers (vendedores)
- **Produtos** com categorias e especificações
- **Pagamentos** que podem ser parcelados
- **Reviews** com avaliações de 1-5 estrelas
- **Geolocalização** para análise espacial

### Período dos Dados

- **Início:** Janeiro 2016
- **Fim:** Agosto 2018
- **Total de pedidos:** 99.441
- **Total de itens:** 112.650
- **Total de clientes:** 99.441 (únicos)

### Estrutura do Schema

**Schema:** `olist_raw`  
**Tabelas:** 8  
**Total de registros:** ~850.000  
**Relacionamentos:** 6 Foreign Keys  

---

## 📐 ENTITY RELATIONSHIP DIAGRAM

### Diagrama Conceitual

```
                        ┌─────────────────────────┐
                        │      CUSTOMERS          │
                        │─────────────────────────│
                        │ PK  customer_id         │
                        │     customer_unique_id  │
                        │     customer_zip_code   │
                        │     customer_city       │
                        │     customer_state      │
                        │     created_at          │
                        │     updated_at          │
                        └────────────┬────────────┘
                                     │
                                     │ 1:N (um cliente, muitos pedidos)
                                     │
                        ┌────────────▼────────────┐
                        │        ORDERS           │
                        │─────────────────────────│
                        │ PK  order_id            │
                        │ FK  customer_id         │◄────────┐
                        │     order_status        │         │
                        │     order_purchase_ts   │         │
                        │     order_approved_at   │         │
                        │     order_delivered_cd  │         │ Relacionamentos
                        │     order_delivered_cd  │         │ 1:N de ORDERS
                        │     order_estimated_dd  │         │
                        │     created_at          │         │
                        │     updated_at          │         │
                        └─────┬──────────┬────────┘         │
                              │          │                  │
                ┌─────────────┘          └──────────┐       │
                │                                   │       │
                │ 1:N                               │ 1:N   │
                │                                   │       │
   ┌────────────▼─────────────┐      ┌─────────────▼───────┴───────┐
   │    ORDER_PAYMENTS        │      │     ORDER_REVIEWS            │
   │──────────────────────────│      │──────────────────────────────│
   │ PK  order_id             │      │ PK  review_id                │
   │ PK  payment_sequential   │      │ FK  order_id                 │
   │     payment_type         │      │     review_score             │
   │     payment_installments │      │     review_comment_title     │
   │     payment_value        │      │     review_comment_message   │
   │     created_at           │      │     review_creation_date     │
   │     updated_at           │      │     review_answer_timestamp  │
   └──────────────────────────┘      │     created_at               │
                                     │     updated_at               │
                                     └──────────────────────────────┘

                        ┌─────────────────────────┐
                        │     ORDER_ITEMS         │
                        │─────────────────────────│
                        │ PK  order_id            │
                        │ PK  order_item_id       │
                        │ FK  product_id          │◄──────┐
                        │ FK  seller_id           │◄──────┼──┐
                        │     shipping_limit_date │       │  │
                        │     price               │       │  │
                        │     freight_value       │       │  │
                        │     created_at          │       │  │
                        │     updated_at          │       │  │
                        └─────────────────────────┘       │  │
                                                          │  │
        ┌─────────────────────────┐      ┌───────────────┘  │
        │       PRODUCTS          │      │                  │
        │─────────────────────────│      │                  │
        │ PK  product_id          │──────┘                  │
        │     product_category    │                         │
        │     product_name_length │                         │
        │     product_desc_length │                         │
        │     product_photos_qty  │                         │
        │     product_weight_g    │                         │
        │     product_length_cm   │                         │
        │     product_height_cm   │                         │
        │     product_width_cm    │                         │
        │     created_at          │                         │
        │     updated_at          │                         │
        └─────────────────────────┘                         │
                                                            │
        ┌─────────────────────────┐      ┌──────────────────┘
        │       SELLERS           │      │
        │─────────────────────────│      │
        │ PK  seller_id           │──────┘
        │     seller_zip_code     │
        │     seller_city         │
        │     seller_state        │
        │     created_at          │
        │     updated_at          │
        └─────────────────────────┘

        ┌─────────────────────────┐
        │     GEOLOCATION         │
        │─────────────────────────│
        │ PK  geolocation_zip     │
        │ PK  geolocation_lat     │
        │ PK  geolocation_lng     │
        │     geolocation_city    │
        │     geolocation_state   │
        │     created_at          │
        │     updated_at          │
        └─────────────────────────┘
        (Tabela auxiliar - sem FKs)
```

### Diagrama Físico (DDL)

```sql
-- Schema
CREATE SCHEMA IF NOT EXISTS olist_raw;

-- Tabelas independentes (sem FKs)
CREATE TABLE olist_raw.customers (...);
CREATE TABLE olist_raw.sellers (...);
CREATE TABLE olist_raw.products (...);
CREATE TABLE olist_raw.geolocation (...);

-- Tabela com 1 FK
CREATE TABLE olist_raw.orders (
    -- ...
    CONSTRAINT fk_orders_customer 
        FOREIGN KEY (customer_id) 
        REFERENCES olist_raw.customers(customer_id)
);

-- Tabelas com múltiplas FKs
CREATE TABLE olist_raw.order_items (
    -- ...
    CONSTRAINT fk_order_items_order 
        FOREIGN KEY (order_id) 
        REFERENCES olist_raw.orders(order_id),
    CONSTRAINT fk_order_items_product 
        FOREIGN KEY (product_id) 
        REFERENCES olist_raw.products(product_id),
    CONSTRAINT fk_order_items_seller 
        FOREIGN KEY (seller_id) 
        REFERENCES olist_raw.sellers(seller_id)
);

CREATE TABLE olist_raw.order_payments (
    -- ...
    CONSTRAINT fk_order_payments_order 
        FOREIGN KEY (order_id) 
        REFERENCES olist_raw.orders(order_id)
);

CREATE TABLE olist_raw.order_reviews (
    -- ...
    CONSTRAINT fk_order_reviews_order 
        FOREIGN KEY (order_id) 
        REFERENCES olist_raw.orders(order_id)
);
```

---

## 📚 DICIONÁRIO DE DADOS

### Tabela: CUSTOMERS

**Descrição:** Cadastro de clientes do marketplace  
**Registros:** 99.441  
**Primary Key:** customer_id  
**Foreign Keys:** Nenhuma  

| Coluna | Tipo | Nulo | Descrição | Exemplo |
|--------|------|------|-----------|---------|
| customer_id | VARCHAR(50) | NOT NULL | Identificador único do cliente no pedido | `8d50f5ea...` |
| customer_unique_id | VARCHAR(50) | NOT NULL | Identificador único do cliente (pode fazer vários pedidos) | `861eff4711...` |
| customer_zip_code_prefix | VARCHAR(5) | NOT NULL | Primeiros 5 dígitos do CEP | `14409` |
| customer_city | VARCHAR(100) | NOT NULL | Cidade do cliente | `Franca` |
| customer_state | VARCHAR(2) | NOT NULL | Estado (UF) | `SP` |
| created_at | TIMESTAMP | NOT NULL | Timestamp de criação do registro | `2025-01-28 10:00:00` |
| updated_at | TIMESTAMP | NOT NULL | Timestamp de última atualização | `2025-01-28 10:00:00` |

**Índices:**
- `PRIMARY KEY (customer_id)`
- `idx_customers_unique_id ON (customer_unique_id)`
- `idx_customers_zip ON (customer_zip_code_prefix)`
- `idx_customers_state ON (customer_state)`

**Regras de Negócio:**
- Um cliente pode fazer múltiplos pedidos (customer_unique_id)
- Cada pedido tem um customer_id único (PK)
- Relação: customer_unique_id (1) → customer_id (N)

**Queries Úteis:**
```sql
-- Clientes que fizeram mais de 1 pedido
SELECT 
    customer_unique_id,
    COUNT(DISTINCT customer_id) as num_pedidos
FROM olist_raw.customers
GROUP BY customer_unique_id
HAVING COUNT(DISTINCT customer_id) > 1;

-- Distribuição de clientes por estado
SELECT 
    customer_state,
    COUNT(*) as total_customers
FROM olist_raw.customers
GROUP BY customer_state
ORDER BY total_customers DESC;
```

---

### Tabela: SELLERS

**Descrição:** Cadastro de vendedores (sellers) do marketplace  
**Registros:** 3.095  
**Primary Key:** seller_id  
**Foreign Keys:** Nenhuma  

| Coluna | Tipo | Nulo | Descrição | Exemplo |
|--------|------|------|-----------|---------|
| seller_id | VARCHAR(50) | NOT NULL | Identificador único do vendedor | `3442f8959...` |
| seller_zip_code_prefix | VARCHAR(5) | NOT NULL | Primeiros 5 dígitos do CEP | `13023` |
| seller_city | VARCHAR(100) | NOT NULL | Cidade do vendedor | `Campinas` |
| seller_state | VARCHAR(2) | NOT NULL | Estado (UF) | `SP` |
| created_at | TIMESTAMP | NOT NULL | Timestamp de criação | `2025-01-28 10:00:00` |
| updated_at | TIMESTAMP | NOT NULL | Timestamp de atualização | `2025-01-28 10:00:00` |

**Índices:**
- `PRIMARY KEY (seller_id)`
- `idx_sellers_zip ON (seller_zip_code_prefix)`
- `idx_sellers_state ON (seller_state)`
- `idx_sellers_city ON (seller_city)`

**Queries Úteis:**
```sql
-- Top 10 sellers por volume de vendas
SELECT 
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(oi.order_id) as total_sales,
    SUM(oi.price) as revenue
FROM olist_raw.sellers s
JOIN olist_raw.order_items oi ON s.seller_id = oi.seller_id
GROUP BY s.seller_id, s.seller_city, s.seller_state
ORDER BY revenue DESC
LIMIT 10;
```

---

### Tabela: PRODUCTS

**Descrição:** Catálogo de produtos  
**Registros:** 32.951  
**Primary Key:** product_id  
**Foreign Keys:** Nenhuma  

| Coluna | Tipo | Nulo | Descrição | Exemplo |
|--------|------|------|-----------|---------|
| product_id | VARCHAR(50) | NOT NULL | Identificador único do produto | `1e9e8ef04...` |
| product_category_name | VARCHAR(100) | NULL | Categoria do produto | `beleza_saude` |
| product_name_lenght | INTEGER | NULL | Comprimento do nome (caracteres) | `40` |
| product_description_lenght | INTEGER | NULL | Comprimento da descrição | `287` |
| product_photos_qty | INTEGER | NULL | Quantidade de fotos | `1` |
| product_weight_g | INTEGER | NULL | Peso em gramas | `225` |
| product_length_cm | INTEGER | NULL | Comprimento em cm | `16` |
| product_height_cm | INTEGER | NULL | Altura em cm | `10` |
| product_width_cm | INTEGER | NULL | Largura em cm | `14` |
| created_at | TIMESTAMP | NOT NULL | Timestamp de criação | `2025-01-28 10:00:00` |
| updated_at | TIMESTAMP | NOT NULL | Timestamp de atualização | `2025-01-28 10:00:00` |

**Observação:** `product_name_lenght` contém typo do dataset original (correto seria "length")

**Índices:**
- `PRIMARY KEY (product_id)`
- `idx_products_category ON (product_category_name)`
- `idx_products_weight ON (product_weight_g)`

**Queries Úteis:**
```sql
-- Top 10 categorias por volume de vendas
SELECT 
    p.product_category_name,
    COUNT(oi.order_id) as total_sales,
    SUM(oi.price) as revenue,
    AVG(oi.price) as avg_price
FROM olist_raw.products p
JOIN olist_raw.order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_category_name
ORDER BY revenue DESC
LIMIT 10;

-- Produtos mais pesados (outliers)
SELECT *
FROM olist_raw.products
WHERE product_weight_g > 10000  -- > 10kg
ORDER BY product_weight_g DESC;
```

---

### Tabela: ORDERS

**Descrição:** Pedidos realizados no marketplace  
**Registros:** 99.441  
**Primary Key:** order_id  
**Foreign Keys:** customer_id → customers  

| Coluna | Tipo | Nulo | Descrição | Exemplo |
|--------|------|------|-----------|---------|
| order_id | VARCHAR(50) | NOT NULL | Identificador único do pedido | `e481f51cb...` |
| customer_id | VARCHAR(50) | NOT NULL | FK para customers | `9ef432eb6...` |
| order_status | VARCHAR(20) | NOT NULL | Status do pedido | `delivered` |
| order_purchase_timestamp | TIMESTAMP | NOT NULL | Data/hora da compra | `2017-10-02 10:56:33` |
| order_approved_at | TIMESTAMP | NULL | Data/hora de aprovação | `2017-10-02 11:07:15` |
| order_delivered_carrier_date | TIMESTAMP | NULL | Data de postagem | `2017-10-04 19:55:00` |
| order_delivered_customer_date | TIMESTAMP | NULL | Data de entrega | `2017-10-10 21:25:13` |
| order_estimated_delivery_date | TIMESTAMP | NULL | Prazo estimado | `2017-10-18 00:00:00` |
| created_at | TIMESTAMP | NOT NULL | Timestamp de criação | `2025-01-28 10:00:00` |
| updated_at | TIMESTAMP | NOT NULL | Timestamp de atualização | `2025-01-28 10:00:00` |

**Valores Possíveis de order_status:**
- `delivered` - Entregue (maioria)
- `shipped` - Enviado
- `canceled` - Cancelado
- `unavailable` - Indisponível
- `invoiced` - Faturado
- `processing` - Processando
- `created` - Criado
- `approved` - Aprovado

**Índices:**
- `PRIMARY KEY (order_id)`
- `idx_orders_customer ON (customer_id)` (FK)
- `idx_orders_status ON (order_status)`
- `idx_orders_purchase_date ON (order_purchase_timestamp)`

**Métricas Derivadas:**
```sql
-- Tempo de entrega (em dias)
SELECT 
    order_id,
    order_purchase_timestamp,
    order_delivered_customer_date,
    EXTRACT(DAY FROM (order_delivered_customer_date - order_purchase_timestamp)) as delivery_days,
    EXTRACT(DAY FROM (order_estimated_delivery_date - order_purchase_timestamp)) as estimated_days
FROM olist_raw.orders
WHERE order_delivered_customer_date IS NOT NULL;

-- Pedidos atrasados
SELECT 
    order_id,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    EXTRACT(DAY FROM (order_delivered_customer_date - order_estimated_delivery_date)) as delay_days
FROM olist_raw.orders
WHERE order_delivered_customer_date > order_estimated_delivery_date;
```

---

### Tabela: ORDER_ITEMS

**Descrição:** Itens de cada pedido (relação N:M entre orders e products)  
**Registros:** 112.650  
**Primary Key:** (order_id, order_item_id)  
**Foreign Keys:** order_id → orders, product_id → products, seller_id → sellers  

| Coluna | Tipo | Nulo | Descrição | Exemplo |
|--------|------|------|-----------|---------|
| order_id | VARCHAR(50) | NOT NULL | FK para orders (PK composta) | `00010242...` |
| order_item_id | INTEGER | NOT NULL | Número sequencial do item (PK composta) | `1` |
| product_id | VARCHAR(50) | NOT NULL | FK para products | `4244733e0...` |
| seller_id | VARCHAR(50) | NOT NULL | FK para sellers | `48436dade...` |
| shipping_limit_date | TIMESTAMP | NOT NULL | Prazo limite para envio | `2017-09-19 09:45:35` |
| price | DECIMAL(10,2) | NOT NULL | Preço do item | `58.90` |
| freight_value | DECIMAL(10,2) | NOT NULL | Valor do frete | `13.29` |
| created_at | TIMESTAMP | NOT NULL | Timestamp de criação | `2025-01-28 10:00:00` |
| updated_at | TIMESTAMP | NOT NULL | Timestamp de atualização | `2025-01-28 10:00:00` |

**Índices:**
- `PRIMARY KEY (order_id, order_item_id)`
- `idx_order_items_order ON (order_id)` (FK)
- `idx_order_items_product ON (product_id)` (FK)
- `idx_order_items_seller ON (seller_id)` (FK)
- `idx_order_items_price ON (price)`

**Regras de Negócio:**
- order_item_id começa em 1 para cada order_id
- Um pedido pode ter múltiplos itens
- Um item pertence a apenas 1 pedido
- Cada item é vendido por 1 seller

**Queries Úteis:**
```sql
-- Pedidos com mais de 1 item
SELECT 
    order_id,
    COUNT(*) as num_items,
    SUM(price) as total_price,
    SUM(freight_value) as total_freight
FROM olist_raw.order_items
GROUP BY order_id
HAVING COUNT(*) > 1
ORDER BY num_items DESC;

-- Ticket médio por pedido
SELECT 
    AVG(order_total) as avg_ticket
FROM (
    SELECT 
        order_id,
        SUM(price + freight_value) as order_total
    FROM olist_raw.order_items
    GROUP BY order_id
) subquery;
```

---

### Tabela: ORDER_PAYMENTS

**Descrição:** Pagamentos de pedidos (um pedido pode ter múltiplos pagamentos)  
**Registros:** 103.886  
**Primary Key:** (order_id, payment_sequential)  
**Foreign Keys:** order_id → orders  

| Coluna | Tipo | Nulo | Descrição | Exemplo |
|--------|------|------|-----------|---------|
| order_id | VARCHAR(50) | NOT NULL | FK para orders (PK composta) | `b81ef226f...` |
| payment_sequential | INTEGER | NOT NULL | Número sequencial do pagamento (PK composta) | `1` |
| payment_type | VARCHAR(20) | NOT NULL | Tipo de pagamento | `credit_card` |
| payment_installments | INTEGER | NOT NULL | Número de parcelas | `8` |
| payment_value | DECIMAL(10,2) | NOT NULL | Valor do pagamento | `99.33` |
| created_at | TIMESTAMP | NOT NULL | Timestamp de criação | `2025-01-28 10:00:00` |
| updated_at | TIMESTAMP | NOT NULL | Timestamp de atualização | `2025-01-28 10:00:00` |

**Valores Possíveis de payment_type:**
- `credit_card` - Cartão de crédito (maioria)
- `boleto` - Boleto bancário
- `voucher` - Vale/cupom
- `debit_card` - Cartão de débito
- `not_defined` - Não definido

**Índices:**
- `PRIMARY KEY (order_id, payment_sequential)`
- `idx_order_payments_order ON (order_id)` (FK)
- `idx_order_payments_type ON (payment_type)`
- `idx_order_payments_value ON (payment_value)`

**Queries Úteis:**
```sql
-- Distribuição de tipos de pagamento
SELECT 
    payment_type,
    COUNT(*) as num_payments,
    SUM(payment_value) as total_value,
    AVG(payment_installments) as avg_installments
FROM olist_raw.order_payments
GROUP BY payment_type
ORDER BY total_value DESC;

-- Pedidos com múltiplas formas de pagamento
SELECT 
    order_id,
    COUNT(*) as num_payments,
    STRING_AGG(payment_type, ', ') as payment_types,
    SUM(payment_value) as total_value
FROM olist_raw.order_payments
GROUP BY order_id
HAVING COUNT(*) > 1;
```

---

### Tabela: ORDER_REVIEWS

**Descrição:** Avaliações de pedidos pelos clientes  
**Registros:** 99.224  
**Primary Key:** review_id  
**Foreign Keys:** order_id → orders  

| Coluna | Tipo | Nulo | Descrição | Exemplo |
|--------|------|------|-----------|---------|
| review_id | VARCHAR(50) | NOT NULL | Identificador único da review | `7bc2406110...` |
| order_id | VARCHAR(50) | NOT NULL | FK para orders | `73fc7af87e...` |
| review_score | INTEGER | NOT NULL | Nota de 1 a 5 | `4` |
| review_comment_title | TEXT | NULL | Título do comentário | `Muito bom` |
| review_comment_message | TEXT | NULL | Comentário detalhado | `Produto de qualidade...` |
| review_creation_date | TIMESTAMP | NOT NULL | Data da criação da review | `2018-01-18 00:00:00` |
| review_answer_timestamp | TIMESTAMP | NULL | Data da resposta do seller | `2018-01-18 21:46:59` |
| created_at | TIMESTAMP | NOT NULL | Timestamp de criação | `2025-01-28 10:00:00` |
| updated_at | TIMESTAMP | NOT NULL | Timestamp de atualização | `2025-01-28 10:00:00` |

**Constraint:**
- `CHECK (review_score BETWEEN 1 AND 5)`

**Índices:**
- `PRIMARY KEY (review_id)`
- `idx_order_reviews_order ON (order_id)` (FK)
- `idx_order_reviews_score ON (review_score)`
- `idx_order_reviews_creation_date ON (review_creation_date)`

**Queries Úteis:**
```sql
-- Distribuição de scores
SELECT 
    review_score,
    COUNT(*) as num_reviews,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM olist_raw.order_reviews
GROUP BY review_score
ORDER BY review_score;

-- Reviews negativas com comentário
SELECT 
    r.review_id,
    r.order_id,
    r.review_score,
    r.review_comment_title,
    r.review_comment_message
FROM olist_raw.order_reviews r
WHERE r.review_score <= 2
  AND r.review_comment_message IS NOT NULL
LIMIT 10;

-- Taxa de resposta dos sellers
SELECT 
    COUNT(CASE WHEN review_answer_timestamp IS NOT NULL THEN 1 END) as answered,
    COUNT(*) as total,
    ROUND(COUNT(CASE WHEN review_answer_timestamp IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as answer_rate
FROM olist_raw.order_reviews;
```

---

### Tabela: GEOLOCATION

**Descrição:** Mapeamento de CEPs para coordenadas geográficas  
**Registros:** ~19.000 (1 por CEP único após deduplicação)  
**Primary Key:** (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng)  
**Foreign Keys:** Nenhuma (tabela auxiliar)  

| Coluna | Tipo | Nulo | Descrição | Exemplo |
|--------|------|------|-----------|---------|
| geolocation_zip_code_prefix | VARCHAR(5) | NOT NULL | Primeiros 5 dígitos do CEP (PK) | `01037` |
| geolocation_lat | DECIMAL(10,8) | NOT NULL | Latitude (PK) | `-23.54562712` |
| geolocation_lng | DECIMAL(11,8) | NOT NULL | Longitude (PK) | `-46.63929849` |
| geolocation_city | VARCHAR(100) | NOT NULL | Cidade | `Sao Paulo` |
| geolocation_state | VARCHAR(2) | NOT NULL | Estado (UF) | `SP` |
| created_at | TIMESTAMP | NOT NULL | Timestamp de criação | `2025-01-28 10:00:00` |
| updated_at | TIMESTAMP | NOT NULL | Timestamp de atualização | `2025-01-28 10:00:00` |

**Índices:**
- `PRIMARY KEY (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng)`
- `idx_geolocation_zip ON (geolocation_zip_code_prefix)`
- `idx_geolocation_state ON (geolocation_state)`
- `idx_geolocation_city ON (geolocation_city)`
- `idx_geolocation_coords ON (geolocation_lat, geolocation_lng)`

**Observação:** 
- Dados originais tinham ~1M de registros
- Após deduplicação: mantida 1 coordenada por CEP (a mais frequente)
- Coordenadas arredondadas para 6 casas decimais (~10cm de precisão)

**Queries Úteis:**
```sql
-- JOIN com customers para obter coordenadas
SELECT 
    c.customer_id,
    c.customer_city,
    c.customer_state,
    g.geolocation_lat,
    g.geolocation_lng
FROM olist_raw.customers c
LEFT JOIN olist_raw.geolocation g 
    ON c.customer_zip_code_prefix = g.geolocation_zip_code_prefix;

-- Distância entre customer e seller (fórmula de Haversine)
WITH customer_coords AS (
    SELECT 
        o.order_id,
        g.geolocation_lat as customer_lat,
        g.geolocation_lng as customer_lng
    FROM olist_raw.orders o
    JOIN olist_raw.customers c ON o.customer_id = c.customer_id
    JOIN olist_raw.geolocation g ON c.customer_zip_code_prefix = g.geolocation_zip_code_prefix
),
seller_coords AS (
    SELECT 
        oi.order_id,
        g.geolocation_lat as seller_lat,
        g.geolocation_lng as seller_lng
    FROM olist_raw.order_items oi
    JOIN olist_raw.sellers s ON oi.seller_id = s.seller_id
    JOIN olist_raw.geolocation g ON s.seller_zip_code_prefix = g.geolocation_zip_code_prefix
)
SELECT 
    cc.order_id,
    -- Fórmula de Haversine (simplificada)
    6371 * ACOS(
        COS(RADIANS(cc.customer_lat)) * 
        COS(RADIANS(sc.seller_lat)) * 
        COS(RADIANS(sc.seller_lng) - RADIANS(cc.customer_lng)) + 
        SIN(RADIANS(cc.customer_lat)) * 
        SIN(RADIANS(sc.seller_lat))
    ) as distance_km
FROM customer_coords cc
JOIN seller_coords sc ON cc.order_id = sc.order_id;
```

---

## 🔗 RELACIONAMENTOS E CARDINALIDADES

### Mapeamento Completo

| Tabela Pai | Tabela Filha | Cardinalidade | FK Column | Constraint Name | ON DELETE |
|------------|--------------|---------------|-----------|-----------------|-----------|
| customers | orders | 1:N | customer_id | fk_orders_customer | CASCADE |
| orders | order_items | 1:N | order_id | fk_order_items_order | CASCADE |
| orders | order_payments | 1:N | order_id | fk_order_payments_order | CASCADE |
| orders | order_reviews | 1:1 | order_id | fk_order_reviews_order | CASCADE |
| products | order_items | 1:N | product_id | fk_order_items_product | RESTRICT |
| sellers | order_items | 1:N | seller_id | fk_order_items_seller | RESTRICT |

### Políticas de Deleção

**CASCADE:**
- Deletar um customer → deleta seus orders → deleta order_items/payments/reviews
- Usado quando dados filhos não fazem sentido sem o pai

**RESTRICT:**
- Impede deletar um product/seller se houver order_items referenciando
- Usado para preservar integridade histórica

### Paths de Navegação

**Customer → Pedidos → Itens → Produtos:**
```sql
SELECT 
    c.customer_id,
    c.customer_city,
    o.order_id,
    o.order_status,
    oi.order_item_id,
    p.product_category_name,
    oi.price
FROM olist_raw.customers c
JOIN olist_raw.orders o ON c.customer_id = o.customer_id
JOIN olist_raw.order_items oi ON o.order_id = oi.order_id
JOIN olist_raw.products p ON oi.product_id = p.product_id;
```

**Seller → Itens → Pedidos → Reviews:**
```sql
SELECT 
    s.seller_id,
    s.seller_city,
    oi.order_id,
    r.review_score,
    r.review_comment_message
FROM olist_raw.sellers s
JOIN olist_raw.order_items oi ON s.seller_id = oi.seller_id
JOIN olist_raw.order_reviews r ON oi.order_id = r.order_id;
```

---

## 📐 REGRAS DE NEGÓCIO

### Validações Implementadas

1. **Primary Keys não nulas:**
   - Todas as PKs têm constraint NOT NULL
   - Validado em tempo de ingestão (DAG validate_csv)

2. **Foreign Keys válidas:**
   - 100% de integridade (0 órfãos)
   - Validado em tempo de ingestão (DAG validate_data_quality)

3. **Valores enumerados:**
   - order_status: lista fechada de 8 valores
   - payment_type: lista fechada de 5 valores
   - review_score: CHECK entre 1 e 5

4. **Timestamps lógicos:**
   - order_approved_at >= order_purchase_timestamp
   - order_delivered_customer_date >= order_delivered_carrier_date

### Regras de Deduplicação

**customers:**
- Duplicatas removidas por customer_id (PK)
- Mantida primeira ocorrência

**geolocation:**
- Múltiplas coordenadas por CEP consolidadas
- Critério: coordenada mais frequente
- Lat/lng arredondados para 6 casas decimais

### Regras de Valores Nulos

**Permitidos:**
- product_category_name (produtos sem categoria)
- order_approved_at, order_delivered_* (pedidos não finalizados)
- review_comment_* (reviews sem texto)
- review_answer_timestamp (seller não respondeu)

**Não Permitidos:**
- Todas as PKs
- Todas as FKs
- order_purchase_timestamp
- review_score
- payment_value, price, freight_value

---

## 🔍 QUERIES DE REFERÊNCIA

### Queries Analíticas Comuns

#### 1. Análise RFM (Recency, Frequency, Monetary)

```sql
WITH customer_metrics AS (
    SELECT 
        c.customer_unique_id,
        MAX(o.order_purchase_timestamp) as last_purchase,
        COUNT(DISTINCT o.order_id) as num_orders,
        SUM(oi.price + oi.freight_value) as total_spent
    FROM olist_raw.customers c
    JOIN olist_raw.orders o ON c.customer_id = o.customer_id
    JOIN olist_raw.order_items oi ON o.order_id = oi.order_id
    GROUP BY c.customer_unique_id
),
rfm_scores AS (
    SELECT 
        customer_unique_id,
        EXTRACT(DAY FROM (CURRENT_TIMESTAMP - last_purchase)) as recency_days,
        num_orders as frequency,
        total_spent as monetary,
        NTILE(5) OVER (ORDER BY EXTRACT(DAY FROM (CURRENT_TIMESTAMP - last_purchase)) DESC) as r_score,
        NTILE(5) OVER (ORDER BY num_orders) as f_score,
        NTILE(5) OVER (ORDER BY total_spent) as m_score
    FROM customer_metrics
)
SELECT 
    customer_unique_id,
    recency_days,
    frequency,
    monetary,
    r_score || f_score || m_score as rfm_segment
FROM rfm_scores
ORDER BY monetary DESC;
```

#### 2. Cohort Analysis (Retenção por Mês)

```sql
WITH first_purchase AS (
    SELECT 
        customer_id,
        MIN(DATE_TRUNC('month', order_purchase_timestamp)) as cohort_month
    FROM olist_raw.orders
    GROUP BY customer_id
),
purchases AS (
    SELECT 
        o.customer_id,
        fp.cohort_month,
        DATE_TRUNC('month', o.order_purchase_timestamp) as purchase_month
    FROM olist_raw.orders o
    JOIN first_purchase fp ON o.customer_id = fp.customer_id
)
SELECT 
    cohort_month,
    COUNT(DISTINCT CASE WHEN purchase_month = cohort_month THEN customer_id END) as month_0,
    COUNT(DISTINCT CASE WHEN purchase_month = cohort_month + INTERVAL '1 month' THEN customer_id END) as month_1,
    COUNT(DISTINCT CASE WHEN purchase_month = cohort_month + INTERVAL '2 months' THEN customer_id END) as month_2,
    COUNT(DISTINCT CASE WHEN purchase_month = cohort_month + INTERVAL '3 months' THEN customer_id END) as month_3
FROM purchases
GROUP BY cohort_month
ORDER BY cohort_month;
```

#### 3. Performance de Sellers

```sql
SELECT 
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT oi.order_id) as num_orders,
    COUNT(oi.order_item_id) as num_items,
    SUM(oi.price) as total_revenue,
    AVG(oi.price) as avg_item_price,
    AVG(r.review_score) as avg_review_score,
    COUNT(CASE WHEN r.review_score <= 2 THEN 1 END) as negative_reviews
FROM olist_raw.sellers s
JOIN olist_raw.order_items oi ON s.seller_id = oi.seller_id
LEFT JOIN olist_raw.order_reviews r ON oi.order_id = r.order_id
GROUP BY s.seller_id, s.seller_city, s.seller_state
HAVING COUNT(DISTINCT oi.order_id) >= 10  -- Mínimo 10 vendas
ORDER BY total_revenue DESC;
```

#### 4. Análise de Entrega (SLA)

```sql
SELECT 
    DATE_TRUNC('month', order_purchase_timestamp) as month,
    COUNT(*) as total_orders,
    COUNT(CASE WHEN order_delivered_customer_date IS NOT NULL THEN 1 END) as delivered_orders,
    AVG(EXTRACT(DAY FROM (order_delivered_customer_date - order_purchase_timestamp))) as avg_delivery_days,
    AVG(EXTRACT(DAY FROM (order_estimated_delivery_date - order_purchase_timestamp))) as avg_estimated_days,
    COUNT(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 END) as late_deliveries,
    ROUND(COUNT(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 END) * 100.0 / 
          COUNT(CASE WHEN order_delivered_customer_date IS NOT NULL THEN 1 END), 2) as late_delivery_rate
FROM olist_raw.orders
WHERE order_status = 'delivered'
GROUP BY DATE_TRUNC('month', order_purchase_timestamp)
ORDER BY month;
```

#### 5. Basket Analysis (Produtos Comprados Juntos)

```sql
WITH order_products AS (
    SELECT 
        oi1.order_id,
        oi1.product_id as product_a,
        oi2.product_id as product_b
    FROM olist_raw.order_items oi1
    JOIN olist_raw.order_items oi2 
        ON oi1.order_id = oi2.order_id 
        AND oi1.product_id < oi2.product_id  -- Evita duplicatas
)
SELECT 
    p1.product_category_name as category_a,
    p2.product_category_name as category_b,
    COUNT(*) as co_purchase_count
FROM order_products op
JOIN olist_raw.products p1 ON op.product_a = p1.product_id
JOIN olist_raw.products p2 ON op.product_b = p2.product_id
GROUP BY p1.product_category_name, p2.product_category_name
HAVING COUNT(*) >= 10  -- Mínimo 10 co-ocorrências
ORDER BY co_purchase_count DESC
LIMIT 20;
```

---

## 📊 ANÁLISES POSSÍVEIS

### Análises de Clientes

1. **Segmentação RFM**
   - Recency: Há quanto tempo comprou
   - Frequency: Quantas compras
   - Monetary: Quanto gastou

2. **Customer Lifetime Value (CLV)**
   - Valor médio por pedido × frequência × duração

3. **Churn Prediction**
   - Clientes inativos por X meses

4. **Cohort Analysis**
   - Retenção por coorte de entrada

### Análises de Produtos

1. **Top Sellers por Categoria**
2. **Análise de Sazonalidade**
3. **Produtos com Maior Margem**
4. **Análise de Reviews por Produto**
5. **Basket Analysis (produtos comprados juntos)**

### Análises de Logística

1. **Tempo Médio de Entrega por Região**
2. **Taxa de Atraso (SLA)**
3. **Distância Customer-Seller**
4. **Custo de Frete vs Distância**

### Análises de Sellers

1. **Performance de Vendedores**
2. **Distribuição Geográfica**
3. **Rating Médio por Seller**
4. **Velocity (vendas/mês)**

### Análises de Pagamento

1. **Preferência de Método de Pagamento**
2. **Parcelamento Médio por Categoria**
3. **Ticket Médio**

---

## 📝 NOTAS TÉCNICAS

### Limitações Conhecidas

1. **Dados Históricos:**
   - Período fixo: 2016-2018
   - Não há dados real-time

2. **Anonimização:**
   - customer_id e seller_id são UUIDs
   - Impossível identificar pessoas reais

3. **Geolocalização:**
   - Apenas primeiros 5 dígitos do CEP
   - Precisão limitada (~bairro)

4. **Produtos:**
   - Sem nomes de produtos (apenas IDs)
   - Typo no campo "product_name_lenght"

### Possíveis Extensões (Fase 2)

1. **Tabelas Derivadas:**
   - `dim_customers` (dimensão desnormalizada)
   - `dim_products` (com traduções de categorias)
   - `fact_sales` (fato de vendas agregado)
   - `fact_deliveries` (fato de entregas)

2. **Métricas Pré-calculadas:**
   - `customer_metrics` (RFM, CLV)
   - `seller_metrics` (performance, rating)
   - `product_metrics` (sales velocity, rating)

3. **Time Series:**
   - Agregações diárias/mensais para dashboards

---

## 📚 REFERÊNCIAS

### Dataset Original

- **Nome:** Brazilian E-Commerce Public Dataset by Olist
- **Fonte:** Kaggle
- **URL:** https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- **Licença:** CC BY-NC-SA 4.0
- **Período:** 2016-2018
- **Tamanho:** ~100k pedidos

### Documentação Adicional

- **ER Diagram Tool:** dbdiagram.io
- **PostgreSQL Docs:** https://www.postgresql.org/docs/13/
- **Data Modeling Best Practices:** Kimball Group

---

**Última atualização:** 29 de Janeiro de 2025  
**Autor:** Hyego Jarllys  
**Versão:** 1.0  
**Schema Version:** olist_raw_v1
