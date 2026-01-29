# OLIST DATA PLATFORM - PHASE 2 ROADMAP: DATA TRANSFORMATION

**Projeto:** Olist E-commerce Data Platform  
**Autor:** Hyego Jarllys  
**Data:** Janeiro 2025  
**Fase Atual:** Fase 1 (Concluída) ✅  
**Próxima Fase:** Fase 2 - Data Transformation 🔄  

---

## 📋 ÍNDICE

1. [Visão Geral da Fase 2](#visão-geral-da-fase-2)
2. [Objetivos e Entregas](#objetivos-e-entregas)
3. [Arquitetura Silver/Gold](#arquitetura-silvergold)
4. [Transformações Planejadas](#transformações-planejadas)
5. [Modelo Dimensional](#modelo-dimensional)
6. [DAGs da Fase 2](#dags-da-fase-2)
7. [Timeline e Milestones](#timeline-e-milestones)
8. [Critérios de Aceite](#critérios-de-aceite)

---

## 🎯 VISÃO GERAL DA FASE 2

### Contexto

A **Fase 1** estabeleceu a fundação: ingestão de dados brutos (bronze layer), validações básicas e infraestrutura de orquestração. A **Fase 2** transforma esses dados brutos em informação analytics-ready, criando as camadas **Silver** (dados limpos) e **Gold** (agregações).

### Princípio: Medallion Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  FASE 1 (Concluída) ✅                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  BRONZE LAYER (Raw Data)                              │  │
│  │  - CSVs → PostgreSQL (olist_raw)                      │  │
│  │  - CSVs → GCS Parquet (bronze/)                       │  │
│  │  - Validações básicas                                 │  │
│  │  - Great Expectations setup                           │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  FASE 2 (Planejada) 🔄                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  SILVER LAYER (Cleaned Data)                          │  │
│  │  - Limpeza e normalização                             │  │
│  │  - Enriquecimento (joins, cálculos)                   │  │
│  │  - Deduplicação avançada                              │  │
│  │  - Particionamento por data                           │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  GOLD LAYER (Aggregated Data)                         │  │
│  │  - Star schema (fatos + dimensões)                    │  │
│  │  - Métricas de negócio (RFM, cohorts)                 │  │
│  │  - Agregações pré-calculadas                          │  │
│  │  - Tabelas otimizadas para BI                         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  FASE 3 (Futura) 🔍                                         │
│  - Expansão Great Expectations                              │
│  - Alertas automatizados                                    │
│  - Monitoramento avançado                                   │
└─────────────────────────────────────────────────────────────┘
```

### Por Que Data Transformation Vem Antes de Quality Avançado?

1. ✅ **Quality básico já existe** (Great Expectations funcionando)
2. ✅ **Transformações criam valor imediato** (analytics-ready data)
3. ✅ **Quality avançado faz mais sentido** após ter dados transformados
4. ✅ **Prioridade: entregar insights** para stakeholders

---

## 🎯 OBJETIVOS E ENTREGAS

### Objetivos Primários

1. **Criar Silver Layer**
   - Tabelas limpas e validadas
   - Enriquecimento com cálculos derivados
   - Particionamento temporal

2. **Criar Gold Layer**
   - Modelo dimensional (star schema)
   - Fatos de vendas, logística, customer behavior
   - Dimensões: customers, products, sellers, date

3. **Estabelecer Pipelines de Transformação**
   - DAGs Airflow Bronze → Silver → Gold
   - Incremental loads (apenas novos dados)
   - Testes automatizados

### Entregas Esperadas

| Entrega | Descrição | Storage |
|---------|-----------|---------|
| **Silver Tables** | 8 tabelas limpas + enriquecidas | PostgreSQL + GCS |
| **Gold Tables** | 4 fatos + 5 dimensões | PostgreSQL |
| **DAGs** | 10-15 DAGs de transformação | Airflow |
| **Métricas** | RFM, NPS, cohorts, CLV | PostgreSQL |
| **Documentação** | Data lineage, transformações | Markdown |

---

## 🏗️ ARQUITETURA SILVER/GOLD

### Schemas PostgreSQL

```sql
-- Schema structure
olist_raw       -- Bronze (Fase 1) ✅
olist_silver    -- Silver (Fase 2) 🔄
olist_gold      -- Gold (Fase 2) 🔄
```

### Google Cloud Storage Structure

```
gs://olist-data-lake-hyego/
├── bronze/           # Fase 1 ✅
│   ├── customers/
│   ├── orders/
│   └── ...
├── silver/           # Fase 2 🔄
│   ├── customers/
│   │   └── year=2017/month=01/
│   ├── orders/
│   │   └── year=2017/month=01/
│   └── ...
└── gold/             # Fase 2 🔄
    ├── fact_sales/
    ├── dim_customers/
    └── ...
```

**Particionamento:**
- Silver: particionado por `year=YYYY/month=MM`
- Gold: não particionado (tabelas agregadas pequenas)

---

## 🔄 TRANSFORMAÇÕES PLANEJADAS

### Silver Layer Transformations

#### 1. CUSTOMERS (Silver)

**Transformações:**
```sql
CREATE TABLE olist_silver.customers AS
SELECT 
    -- IDs preservados
    customer_id,
    customer_unique_id,
    
    -- Geolocalização enriquecida
    c.customer_zip_code_prefix,
    c.customer_city,
    c.customer_state,
    g.geolocation_lat,
    g.geolocation_lng,
    
    -- Métricas agregadas
    COUNT(DISTINCT o.order_id) AS total_orders,
    MIN(o.order_purchase_timestamp) AS first_order_date,
    MAX(o.order_purchase_timestamp) AS last_order_date,
    SUM(oi.price + oi.freight_value) AS total_spent,
    AVG(oi.price + oi.freight_value) AS avg_order_value,
    AVG(r.review_score) AS avg_review_score,
    
    -- Recency
    CURRENT_DATE - MAX(o.order_purchase_timestamp)::date AS days_since_last_order,
    
    -- Timestamps
    CURRENT_TIMESTAMP AS processed_at,
    CURRENT_TIMESTAMP AS updated_at
    
FROM olist_raw.customers c
LEFT JOIN olist_raw.geolocation g 
    ON c.customer_zip_code_prefix = g.geolocation_zip_code_prefix
LEFT JOIN olist_raw.orders o 
    ON c.customer_id = o.customer_id
LEFT JOIN olist_raw.order_items oi 
    ON o.order_id = oi.order_id
LEFT JOIN olist_raw.order_reviews r 
    ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY 
    customer_id, customer_unique_id,
    c.customer_zip_code_prefix, c.customer_city, c.customer_state,
    g.geolocation_lat, g.geolocation_lng;
```

**Enriquecimentos:**
- ✅ Coordenadas geográficas via JOIN com geolocation
- ✅ Total de pedidos por customer
- ✅ Primeira e última compra
- ✅ Total gasto (lifetime value)
- ✅ Ticket médio
- ✅ Rating médio

#### 2. ORDERS (Silver)

**Transformações:**
```sql
CREATE TABLE olist_silver.orders AS
SELECT 
    -- IDs
    o.order_id,
    o.customer_id,
    
    -- Status e timestamps
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    
    -- Métricas calculadas
    SUM(oi.price) AS total_items_value,
    SUM(oi.freight_value) AS total_freight,
    SUM(oi.price + oi.freight_value) AS total_order_value,
    COUNT(oi.order_item_id) AS total_items,
    
    -- Tempo de entrega (dias)
    EXTRACT(DAY FROM 
        o.order_delivered_customer_date - o.order_purchase_timestamp
    ) AS delivery_days,
    
    -- Atraso (dias)
    CASE 
        WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
        THEN EXTRACT(DAY FROM 
            o.order_delivered_customer_date - o.order_estimated_delivery_date
        )
        ELSE 0
    END AS delay_days,
    
    -- Flags
    o.order_delivered_customer_date > o.order_estimated_delivery_date AS is_late,
    o.order_status = 'delivered' AS is_delivered,
    
    -- Review info
    r.review_score,
    r.review_comment_message IS NOT NULL AS has_review_comment,
    
    -- Payment info
    STRING_AGG(DISTINCT p.payment_type, ', ') AS payment_types,
    SUM(p.payment_value) AS total_payment_value,
    AVG(p.payment_installments) AS avg_installments,
    
    -- Timestamps
    CURRENT_TIMESTAMP AS processed_at,
    CURRENT_TIMESTAMP AS updated_at
    
FROM olist_raw.orders o
JOIN olist_raw.order_items oi ON o.order_id = oi.order_id
LEFT JOIN olist_raw.order_reviews r ON o.order_id = r.order_id
LEFT JOIN olist_raw.order_payments p ON o.order_id = p.order_id
GROUP BY 
    o.order_id, o.customer_id, o.order_status,
    o.order_purchase_timestamp, o.order_approved_at,
    o.order_delivered_carrier_date, o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    r.review_score, r.review_comment_message;
```

**Enriquecimentos:**
- ✅ Valor total do pedido (itens + frete)
- ✅ Quantidade de itens
- ✅ Tempo de entrega calculado
- ✅ Atraso calculado
- ✅ Flags booleanas (is_late, is_delivered)
- ✅ Informações de review
- ✅ Informações de payment agregadas

#### 3. PRODUCTS (Silver)

**Transformações:**
```sql
CREATE TABLE olist_silver.products AS
SELECT 
    -- IDs e info básica
    p.product_id,
    p.product_category_name,
    COALESCE(p.product_category_name, 'unknown') AS product_category_clean,
    
    -- Dimensões físicas
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm,
    
    -- Volume calculado (cm³)
    (p.product_length_cm * p.product_height_cm * p.product_width_cm) AS product_volume_cm3,
    
    -- Métricas de vendas
    COUNT(DISTINCT oi.order_id) AS total_sales,
    SUM(oi.price) AS total_revenue,
    AVG(oi.price) AS avg_price,
    MIN(oi.price) AS min_price,
    MAX(oi.price) AS max_price,
    
    -- Métricas de review
    AVG(r.review_score) AS avg_review_score,
    COUNT(r.review_id) AS total_reviews,
    COUNT(CASE WHEN r.review_score = 5 THEN 1 END) AS five_star_reviews,
    COUNT(CASE WHEN r.review_score <= 2 THEN 1 END) AS negative_reviews,
    
    -- Sellers únicos
    COUNT(DISTINCT oi.seller_id) AS unique_sellers,
    
    -- Timestamps
    CURRENT_TIMESTAMP AS processed_at,
    CURRENT_TIMESTAMP AS updated_at
    
FROM olist_raw.products p
LEFT JOIN olist_raw.order_items oi ON p.product_id = oi.product_id
LEFT JOIN olist_raw.orders o ON oi.order_id = o.order_id
LEFT JOIN olist_raw.order_reviews r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered' OR o.order_status IS NULL
GROUP BY 
    p.product_id, p.product_category_name,
    p.product_weight_g, p.product_length_cm,
    p.product_height_cm, p.product_width_cm;
```

**Enriquecimentos:**
- ✅ Categoria limpa (substituir NULL por 'unknown')
- ✅ Volume calculado (L x H x W)
- ✅ Métricas de vendas (total, média, min, max)
- ✅ Rating médio e distribuição de reviews
- ✅ Número de sellers vendendo o produto

#### 4. SELLERS (Silver)

**Transformações similares:**
- Geolocalização enriquecida
- Total de vendas e revenue
- Rating médio
- Tempo médio de entrega

---

### Gold Layer: Modelo Dimensional

#### Star Schema Overview

```
         ┌─────────────────────┐
         │    dim_date         │
         │─────────────────────│
         │ PK date_sk          │
         │    date             │
         │    year             │
         │    month            │
         │    quarter          │
         │    day_name         │
         │    week_of_year     │
         └──────────┬──────────┘
                    │
                    │
         ┌──────────▼──────────┐
         │   fact_sales        │
         │─────────────────────│
         │ PK sale_sk          │
         │ FK date_sk          │◄─────────┐
         │ FK customer_sk      │          │
         │ FK product_sk       │          │
         │ FK seller_sk        │          │
         │    order_id         │          │
         │    quantity         │          │
         │    unit_price       │          │
         │    freight_value    │          │
         │    total_value      │          │
         │    is_delivered     │          │
         │    delivery_days    │          │
         └─────┬───┬───┬───────┘          │
               │   │   │                  │
      ┌────────┘   │   └────────┐         │
      │            │            │         │
┌─────▼──────┐ ┌──▼─────────┐ ┌▼─────────▼───┐
│dim_customer│ │dim_product │ │ dim_seller   │
│────────────│ │────────────│ │──────────────│
│PK cust_sk  │ │PK prod_sk  │ │PK seller_sk  │
│  cust_id   │ │  prod_id   │ │  seller_id   │
│  city      │ │  category  │ │  city        │
│  state     │ │  weight_g  │ │  state       │
│  segment   │ │  volume    │ │  rating      │
│  rfm_score │ │  rating    │ └──────────────┘
│  is_active │ └────────────┘
└────────────┘
```

#### Fact Tables

**1. fact_sales**

```sql
CREATE TABLE olist_gold.fact_sales (
    sale_sk SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    date_sk INTEGER NOT NULL,
    customer_sk INTEGER NOT NULL,
    product_sk INTEGER NOT NULL,
    seller_sk INTEGER NOT NULL,
    
    -- Degenerate Dimensions (IDs originais)
    order_id VARCHAR(50),
    order_item_id INTEGER,
    
    -- Métricas
    quantity INTEGER DEFAULT 1,
    unit_price DECIMAL(10,2),
    freight_value DECIMAL(10,2),
    total_value DECIMAL(10,2),  -- unit_price + freight_value
    
    -- Atributos descritivos
    is_delivered BOOLEAN,
    is_late BOOLEAN,
    delivery_days INTEGER,
    delay_days INTEGER,
    review_score INTEGER,
    
    -- Timestamps
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_fact_sales_date 
        FOREIGN KEY (date_sk) 
        REFERENCES olist_gold.dim_date(date_sk),
    CONSTRAINT fk_fact_sales_customer 
        FOREIGN KEY (customer_sk) 
        REFERENCES olist_gold.dim_customers(customer_sk),
    CONSTRAINT fk_fact_sales_product 
        FOREIGN KEY (product_sk) 
        REFERENCES olist_gold.dim_products(product_sk),
    CONSTRAINT fk_fact_sales_seller 
        FOREIGN KEY (seller_sk) 
        REFERENCES olist_gold.dim_sellers(seller_sk)
);

CREATE INDEX idx_fact_sales_date ON olist_gold.fact_sales(date_sk);
CREATE INDEX idx_fact_sales_customer ON olist_gold.fact_sales(customer_sk);
CREATE INDEX idx_fact_sales_product ON olist_gold.fact_sales(product_sk);
CREATE INDEX idx_fact_sales_seller ON olist_gold.fact_sales(seller_sk);
```

**2. fact_deliveries**

Fato separado para análise de logística:
- Tempo de entrega por rota
- Distância customer-seller
- Custo de frete vs distância
- SLA compliance

#### Dimension Tables

**1. dim_date**

```sql
CREATE TABLE olist_gold.dim_date (
    date_sk INTEGER PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    month_name VARCHAR(20),
    week_of_year INTEGER,
    day_of_month INTEGER,
    day_of_week INTEGER,
    day_name VARCHAR(20),
    is_weekend BOOLEAN,
    is_holiday BOOLEAN
);
```

Populado para todo o período: 2016-2018 + futuro (até 2030).

**2. dim_customers**

```sql
CREATE TABLE olist_gold.dim_customers (
    customer_sk SERIAL PRIMARY KEY,
    
    -- Natural key
    customer_id VARCHAR(50) UNIQUE NOT NULL,
    customer_unique_id VARCHAR(50),
    
    -- Localização
    customer_city VARCHAR(100),
    customer_state VARCHAR(2),
    customer_lat DECIMAL(10,8),
    customer_lng DECIMAL(11,8),
    
    -- Métricas agregadas
    first_order_date DATE,
    last_order_date DATE,
    total_orders INTEGER,
    total_spent DECIMAL(10,2),
    avg_order_value DECIMAL(10,2),
    avg_review_score DECIMAL(3,2),
    
    -- Segmentação RFM
    recency INTEGER,
    frequency INTEGER,
    monetary DECIMAL(10,2),
    rfm_score VARCHAR(3),
    customer_segment VARCHAR(20),
    
    -- Status
    is_active BOOLEAN,  -- Comprou nos últimos 6 meses
    
    -- SCD Type 2 (slowly changing dimension)
    effective_from DATE,
    effective_to DATE,
    is_current BOOLEAN DEFAULT TRUE,
    
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_customers_state ON olist_gold.dim_customers(customer_state);
CREATE INDEX idx_dim_customers_segment ON olist_gold.dim_customers(customer_segment);
```

**3. dim_products**

```sql
CREATE TABLE olist_gold.dim_products (
    product_sk SERIAL PRIMARY KEY,
    
    -- Natural key
    product_id VARCHAR(50) UNIQUE NOT NULL,
    
    -- Atributos
    product_category VARCHAR(100),
    product_weight_g INTEGER,
    product_volume_cm3 INTEGER,
    
    -- Métricas agregadas
    total_sales INTEGER,
    total_revenue DECIMAL(10,2),
    avg_price DECIMAL(10,2),
    avg_review_score DECIMAL(3,2),
    
    -- Status
    is_active BOOLEAN,  -- Vendido nos últimos 6 meses
    
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**4. dim_sellers**

Similar a dim_products, com métricas de performance.

**5. dim_geolocation**

Dimensão de coordenadas geográficas para análises espaciais.

---

### Métricas Pré-calculadas (Gold)

#### 1. customer_rfm

```sql
CREATE TABLE olist_gold.customer_rfm AS
WITH customer_metrics AS (
    SELECT 
        customer_sk,
        CURRENT_DATE - MAX(date) AS recency,
        COUNT(DISTINCT order_id) AS frequency,
        SUM(total_value) AS monetary
    FROM olist_gold.fact_sales fs
    JOIN olist_gold.dim_date d ON fs.date_sk = d.date_sk
    GROUP BY customer_sk
)
SELECT 
    customer_sk,
    recency,
    frequency,
    monetary,
    NTILE(5) OVER (ORDER BY recency DESC) AS r_score,
    NTILE(5) OVER (ORDER BY frequency) AS f_score,
    NTILE(5) OVER (ORDER BY monetary) AS m_score,
    CONCAT(
        NTILE(5) OVER (ORDER BY recency DESC),
        NTILE(5) OVER (ORDER BY frequency),
        NTILE(5) OVER (ORDER BY monetary)
    ) AS rfm_score,
    CASE 
        WHEN rfm_score IN ('555', '554', '544', '545') THEN 'Champion'
        WHEN rfm_score IN ('543', '444', '435', '355') THEN 'Loyal'
        WHEN rfm_score IN ('331', '321', '312', '221') THEN 'At Risk'
        ELSE 'Others'
    END AS segment
FROM customer_metrics;
```

#### 2. cohort_analysis

```sql
CREATE TABLE olist_gold.cohort_analysis AS
WITH first_purchase AS (
    SELECT 
        customer_sk,
        MIN(DATE_TRUNC('month', date)) AS cohort_month
    FROM olist_gold.fact_sales fs
    JOIN olist_gold.dim_date d ON fs.date_sk = d.date_sk
    GROUP BY customer_sk
),
purchases AS (
    SELECT 
        fp.cohort_month,
        DATE_TRUNC('month', d.date) AS purchase_month,
        fs.customer_sk
    FROM olist_gold.fact_sales fs
    JOIN olist_gold.dim_date d ON fs.date_sk = d.date_sk
    JOIN first_purchase fp ON fs.customer_sk = fp.customer_sk
)
SELECT 
    cohort_month,
    purchase_month,
    DATE_PART('month', AGE(purchase_month, cohort_month)) AS month_number,
    COUNT(DISTINCT customer_sk) AS customers,
    COUNT(DISTINCT customer_sk)::FLOAT / 
        FIRST_VALUE(COUNT(DISTINCT customer_sk)) 
        OVER (PARTITION BY cohort_month ORDER BY purchase_month) 
        AS retention_rate
FROM purchases
GROUP BY cohort_month, purchase_month
ORDER BY cohort_month, purchase_month;
```

---

## 📋 DAGS DA FASE 2

### Estrutura de DAGs

```
BRONZE → SILVER → GOLD

15_bronze_to_silver_customers
16_bronze_to_silver_orders
17_bronze_to_silver_products
18_bronze_to_silver_sellers
19_bronze_to_silver_items
20_bronze_to_silver_payments
21_bronze_to_silver_reviews
22_bronze_to_silver_geolocation

23_silver_to_gold_dimensions
24_silver_to_gold_fact_sales
25_silver_to_gold_fact_deliveries

26_gold_metrics_rfm
27_gold_metrics_cohorts
28_gold_metrics_nps
```

### Exemplo de DAG: Bronze → Silver

```python
"""
DAG: Bronze to Silver - Customers
Fase 2: Data Transformation
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'hyego',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# SQL para criar tabela silver
CREATE_SILVER_CUSTOMERS_SQL = """
CREATE TABLE IF NOT EXISTS olist_silver.customers AS
SELECT 
    c.customer_id,
    c.customer_unique_id,
    c.customer_zip_code_prefix,
    c.customer_city,
    c.customer_state,
    g.geolocation_lat,
    g.geolocation_lng,
    COUNT(DISTINCT o.order_id) AS total_orders,
    MIN(o.order_purchase_timestamp) AS first_order_date,
    MAX(o.order_purchase_timestamp) AS last_order_date,
    SUM(oi.price + oi.freight_value) AS total_spent,
    AVG(oi.price + oi.freight_value) AS avg_order_value,
    AVG(r.review_score) AS avg_review_score,
    CURRENT_DATE - MAX(o.order_purchase_timestamp)::date AS days_since_last_order,
    CURRENT_TIMESTAMP AS processed_at
FROM olist_raw.customers c
LEFT JOIN olist_raw.geolocation g 
    ON c.customer_zip_code_prefix = g.geolocation_zip_code_prefix
LEFT JOIN olist_raw.orders o 
    ON c.customer_id = o.customer_id
LEFT JOIN olist_raw.order_items oi 
    ON o.order_id = oi.order_id
LEFT JOIN olist_raw.order_reviews r 
    ON o.order_id = r.order_id
WHERE o.order_status = 'delivered' OR o.order_status IS NULL
GROUP BY 
    c.customer_id, c.customer_unique_id,
    c.customer_zip_code_prefix, c.customer_city, c.customer_state,
    g.geolocation_lat, g.geolocation_lng;
"""

with DAG(
    dag_id='15_bronze_to_silver_customers',
    default_args=default_args,
    description='Transform bronze customers to silver layer',
    schedule_interval='@daily',  # Executar diariamente
    start_date=datetime(2025, 2, 1),
    catchup=False,
    tags=['fase-2', 'silver', 'transformation'],
) as dag:
    
    create_schema = PostgresOperator(
        task_id='create_silver_schema',
        postgres_conn_id='postgres_default',
        sql="CREATE SCHEMA IF NOT EXISTS olist_silver;"
    )
    
    drop_table = PostgresOperator(
        task_id='drop_existing_table',
        postgres_conn_id='postgres_default',
        sql="DROP TABLE IF EXISTS olist_silver.customers;"
    )
    
    transform_to_silver = PostgresOperator(
        task_id='transform_to_silver',
        postgres_conn_id='postgres_default',
        sql=CREATE_SILVER_CUSTOMERS_SQL
    )
    
    validate_silver = PythonOperator(
        task_id='validate_silver',
        python_callable=validate_silver_customers
    )
    
    export_to_gcs = PythonOperator(
        task_id='export_to_gcs',
        python_callable=export_silver_to_gcs
    )
    
    create_schema >> drop_table >> transform_to_silver >> validate_silver >> export_to_gcs
```

---

## ⏱️ TIMELINE E MILESTONES

### Estimativa de Duração: 3-4 semanas

#### Semana 1: Setup e Silver Layer

**Dias 1-2:**
- [ ] Criar schemas olist_silver e olist_gold
- [ ] Implementar DAG 15-18 (customers, orders, products, sellers)
- [ ] Testar transformações básicas

**Dias 3-5:**
- [ ] Implementar DAG 19-22 (items, payments, reviews, geolocation)
- [ ] Validar todas as tabelas silver
- [ ] Exportar para GCS com particionamento

#### Semana 2: Gold Layer - Dimensões

**Dias 1-2:**
- [ ] Criar dim_date (popolar 2016-2030)
- [ ] Criar dim_customers com SCD Type 2
- [ ] Implementar DAG 23 (dimensions)

**Dias 3-5:**
- [ ] Criar dim_products, dim_sellers, dim_geolocation
- [ ] Validar todas as dimensões
- [ ] Testes de integridade (surrogate keys)

#### Semana 3: Gold Layer - Fatos

**Dias 1-3:**
- [ ] Criar fact_sales
- [ ] Criar fact_deliveries
- [ ] Implementar DAGs 24-25

**Dias 4-5:**
- [ ] Validar fatos (contagem de registros)
- [ ] Testar JOINs fato-dimensão
- [ ] Performance tuning (índices)

#### Semana 4: Métricas e Finalização

**Dias 1-2:**
- [ ] Implementar customer_rfm (DAG 26)
- [ ] Implementar cohort_analysis (DAG 27)
- [ ] Implementar NPS metrics (DAG 28)

**Dias 3-4:**
- [ ] Documentar lineage (bronze → silver → gold)
- [ ] Criar queries de referência para BI
- [ ] Atualizar Great Expectations para silver/gold

**Dia 5:**
- [ ] Revisão final
- [ ] Documentação Phase 2 Summary
- [ ] Apresentação para stakeholders

---

## ✅ CRITÉRIOS DE ACEITE

### Funcional

- [ ] **Silver Layer:** 8 tabelas criadas com dados enriquecidos
- [ ] **Gold Layer:** 5 dimensões + 2 fatos criados
- [ ] **Métricas:** RFM, cohorts, NPS calculados
- [ ] **GCS:** Silver exportado com particionamento correto
- [ ] **DAGs:** 14 DAGs executando com sucesso
- [ ] **Integridade:** 100% FKs válidas em fact_sales

### Não-Funcional

- [ ] **Performance:** Transformação bronze→silver < 5min
- [ ] **Performance:** Transformação silver→gold < 2min
- [ ] **Incremental:** DAGs suportam reprocessamento idempotente
- [ ] **Documentação:** Lineage documentado (diagram + markdown)
- [ ] **Testes:** Great Expectations para silver/gold (>85% success)

### Qualidade

- [ ] **Deduplicação:** 0 duplicatas em dim_customers
- [ ] **Surrogate Keys:** Sequenciais sem gaps
- [ ] **Cálculos:** Métricas validadas manualmente (sample)
- [ ] **Particionamento:** Arquivos Parquet corretos no GCS
- [ ] **Logs:** Estruturados e compreensíveis

---

## 📊 MÉTRICAS DE SUCESSO

| Métrica | Target | Medição |
|---------|--------|---------|
| Tabelas Silver | 8 | COUNT schemas |
| Tabelas Gold | 9 | COUNT dimensions + facts + metrics |
| Registros fact_sales | 112k | SELECT COUNT(*) |
| DAGs Fase 2 | 14 | Airflow UI |
| Success Rate GE | >85% | Data Docs |
| Tempo Bronze→Silver | <5min | Airflow logs |
| Tempo Silver→Gold | <2min | Airflow logs |

---

## 🔮 PREPARAÇÃO PARA FASE 3

### O Que Fase 2 Habilita para Fase 3

1. **Dados Transformados** → Mais fácil criar validações avançadas
2. **Métricas Calculadas** → Monitorar drifts e anomalias
3. **Modelo Dimensional** → Dashboards no Power BI
4. **Lineage Completo** → Rastreabilidade end-to-end

### Próximas Fases (Overview)

**Fase 3: Data Quality & Monitoring**
- Great Expectations para silver/gold
- Alertas Slack/email
- Dashboard de observabilidade

**Fase 4: Analytics & Visualization**
- Power BI conectado ao gold
- Dashboards de vendas, logística, NPS
- Self-service BI

**Fase 5: Machine Learning**
- Churn prediction
- Demand forecasting
- Recomendação de produtos

---

## 📚 REFERÊNCIAS

### Conceitos Aplicados

- **Medallion Architecture:** Databricks
- **Star Schema:** Kimball Methodology
- **RFM Analysis:** Marketing Analytics
- **Cohort Analysis:** Retention Metrics
- **SCD Type 2:** Slowly Changing Dimensions

### Ferramentas

- Apache Airflow: Orquestração
- PostgreSQL: Data Warehouse
- GCS Parquet: Data Lake
- Great Expectations: Data Quality

---

## 🎯 CALL TO ACTION

**Ready to Start Phase 2?**

1. ✅ Revisar este roadmap
2. ✅ Confirmar timeline (3-4 semanas)
3. ✅ Alocar recursos (tempo dedicado)
4. ✅ Executar Semana 1: Setup + Silver Layer

**Let's transform raw data into business insights!** 🚀

---

**Última atualização:** 29 de Janeiro de 2025  
**Autor:** Hyego Jarllys  
**Versão:** 1.0  
**Status:** Ready to Execute
