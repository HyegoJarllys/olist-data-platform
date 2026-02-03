# 🗺️ OLIST DATA PLATFORM - ROADMAP FINAL V3

**Versão:** 3.0 (Production-Grade)  
**Autor:** Hyego + Claude  
**Data:** Fevereiro 2025  
**Duração:** 10-12 semanas | **Esforço:** 150-200h  
**Nível:** Pleno/Sênior  
**Status:** Fase 2 (85% completa)

---

## 📊 VISÃO EXECUTIVA

### **Objetivo do Projeto**
Construir plataforma de dados end-to-end production-grade demonstrando práticas enterprise em Data Engineering, Analytics Engineering, MLOps e BI, com foco em **entrega de valor** através de problema de negócio real.

### **Diferenciais Competitivos**
✅ Arquitetura Medalha completa (Bronze → Silver → Gold)  
✅ **DBT na Gold Layer** (versionamento, testes automáticos, documentação gerada)  
✅ Observability desde o início (Streamlit dashboard tempo real)  
✅ Data Quality em todas camadas (Great Expectations)  
✅ Schema Evolution Tracking (auditoria automática)  
✅ Problema de Negócio definido (não teórico)  
✅ MLOps completo (drift detection, retraining automático)  
✅ Documentação Executiva (apresentável C-level)

### **Stack Tecnológica**
- **Orquestração:** Apache Airflow 2.8+
- **Storage:** PostgreSQL 13, Google Cloud Storage
- **Transformação:** DBT Core 1.7+ (Gold Layer)
- **Qualidade:** Great Expectations 0.18+
- **Observability:** Streamlit, Custom dashboards
- **ML:** XGBoost, MLflow 2.0+, Evidently AI
- **BI:** Power BI Desktop, Metabase
- **Infra:** Docker Compose, GCP

### **Entregas Finais**
- 46+ DAGs Airflow
- 20+ DBT models (staging, intermediate, marts, aggregations)
- 50+ validações Great Expectations
- 1 Dashboard Observability (Streamlit)
- 1 Modelo ML em produção
- 4 Dashboards BI
- 70+ páginas documentação

---

## 🎯 ESTRUTURA DAS FASES

| Fase | Duração | Foco | Checkpoint | Status |
|------|---------|------|------------|--------|
| **0** | 1 sem | Setup | Airflow rodando | ✅ |
| **1** | 2-3 sem | **Bronze** | Dados validados | ✅ |
| **2** | 3-4 sem | **Silver + Observability** | Checkpoint | ✅ 85% |
| **3** | 4-5 sem | **Gold (DBT) + BI** | Dashboards | 🔜 |
| **4** | 2-3 sem | **ML + MLOps** | Modelo produção | 🔜 |

---

## 🚀 FASE 0: SETUP & FUNDAÇÃO
**Status:** ✅ CONCLUÍDA

### Objetivos
Ambiente desenvolvimento completo e funcional.

### Entregas
- Repositório GitHub estruturado
- Docker Compose (Airflow + PostgreSQL + Redis)
- GCP configurado (bucket, credenciais)
- 9 CSVs organizados (550k registros)
- Schema PostgreSQL documentado
- Primeiro DAG funcionando

### Arquitetura Base
```
Local: Docker (Airflow, PostgreSQL, Redis)
Cloud: GCP (GCS, BigQuery, Vertex AI)
Control: GitHub
```

---

## 📦 FASE 1: INGESTÃO (BRONZE)
**Status:** ✅ CONCLUÍDA

### Objetivos
Bronze Layer = fonte primária de dados brutos, 100% integridade.

### 1.1 Ingestão PostgreSQL
**DAGs 01-09 (uma por tabela)**
- Ordem respeitando Foreign Keys
- Validação integridade referencial
- Deduplicação Primary Keys
- Logs detalhados
- Idempotência

**Resultado:** 850k registros, 8 tabelas, 0 órfãos, 0 duplicatas

### 1.2 Ingestão GCS
- Export para `gs://bucket/bronze/`
- Formato Parquet (Snappy)
- Particionamento por `processed_date`
- Redução 60% tamanho vs CSV

### 1.3 Data Quality Bronze
**DAGs Great Expectations:**
- DAG 06: Setup GE
- DAG 07: Create 3 suites (customers, orders, products)
- DAG 08: Run validations

**15+ expectations:** PKs únicas, FKs válidas, tipos corretos, ranges válidos

**Resultado:** 100% success rate, Data Docs HTML gerado

### Métricas Fase 1
- Registros: 850.118
- Tabelas: 8
- DAGs: 12 (9 ingest + 3 quality)
- Expectations: 15+
- Success Rate: 100%

---

## 🥈 FASE 2: SILVER + QUALITY + OBSERVABILITY
**Status:** ✅ 85% (faltam 3 itens)

### Objetivos
- Silver = fonte da verdade (limpa, padronizada, enriquecida)
- Silver = **CHECKPOINT** do projeto (reutilizável)
- Observability completa
- Schema evolution tracking
- Data drift detection

### 2.1 Silver Layer - 8 Tabelas

**Filosofia:** Apenas transformações técnicas e neutras, SEM métricas de negócio.

**1. customers (99k registros, 11 colunas)**
- Enriquecimento: JOIN geolocation (lat/lng)
- Padronização: estado 2 chars uppercase
- Validação: coordenadas range Brasil
- Flags: `has_geolocation` (99.7%)
- NULLs preservados quando semântico

**2. orders (99k registros, 14 colunas)**
- Conversão: strings → TIMESTAMP
- Padronização: status lowercase + trim
- Flags: `is_delivered`, `is_approved`, `is_shipped`
- NULLs preservados (ex: approved_at NULL = "não aprovado ainda")

**3. products (33k registros, 17 colunas)**
- Cálculo: `volume_cm3` = L × H × W
- Conversão: NUMERIC para dimensões
- COALESCE: contadores com 0 default
- Flags: `has_category`, `has_dimensions`, `has_photos`, `has_weight`
- NULLs preservados em opcionais

**4. sellers (3k registros, 11 colunas)**
- Enriquecimento: geolocation
- Padronização: estado UPPERCASE
- Flags: `has_geolocation`

**5. order_items (113k registros, 14 colunas)**
- PK composta: (order_id, order_item_id)
- Conversão: NUMERIC(10,2) monetário
- Cálculo: `item_total_value` = price + freight
- Flags: `has_price`, `has_freight`, `has_shipping_limit`
- 7 índices (PK + FKs + filtros)

**6. order_payments (104k registros, 13 colunas)**
- PK composta: (order_id, payment_sequential)
- Padronização: type lowercase
- Conversão: INTEGER parcelas, NUMERIC valores
- Flags: `is_installment`, `is_credit_card`, `is_boleto`

**7. order_reviews (99k registros, 17 colunas)**
- Validação: score 1-5 (100% válidos)
- Tratamento: TRIM comentários
- Cálculo: `comment_length`
- Flags: `has_comment`, `is_positive_score` (≥4), `is_negative_score` (≤2)
- Estatística: 41% têm comentários, score médio 4.1

**8. geolocation (19k registros, 10 colunas) - TRANSFORMAÇÃO MASSIVA!**
- Deduplicação: 1M → 19k (98% redução!)
- Lógica: DISTINCT ON (zip_code) - 1 coordenada/CEP
- Validação: coordenadas Brasil
- Contador: `original_count` (duplicatas na Bronze)

**Padrões aplicados:**
- Deduplicação (DISTINCT)
- Conversão tipos (NUMERIC, TIMESTAMP, BOOLEAN)
- Padronização (lowercase, uppercase, TRIM)
- Enriquecimentos (JOINs)
- Cálculos técnicos
- Flags booleanas
- NULLs inteligentes (preservar quando semântico)
- Timestamps auditoria (processed_at, updated_at, created_at)
- Índices performance (PKs, FKs, filtros)

### 2.2 Export Silver GCS
**DAG 23:**
- 8 tabelas em PARALELO
- Formato Parquet (Snappy)
- Particionamento: `silver/{table}/year=YYYY/month=MM/`
- Resumo consolidado (task final)
- Tempo: 2-3 min
- ~570k registros exportados

### 2.3 Data Quality Silver
**DAG 24:** Setup GE Silver (datasource separado)

**DAG 25:** Create 4 suites (tabelas principais)
1. **customers_silver_suite (12 expectations)**
   - PK única, coordenadas Brasil, flags válidas, estado 2 chars
2. **orders_silver_suite (11 expectations)**
   - PK única, status padronizado, timestamps não nulos, flags
3. **products_silver_suite (11 expectations)**
   - PK única, dimensões positivas, contadores válidos, flags
4. **order_items_silver_suite (13 expectations)**
   - PK composta, FKs não nulas, valores monetários positivos, flags

**Total:** 47 expectations Silver

**DAG 26:** Run validations
- 4 suites em PARALELO
- Checkpoints reutilizáveis
- Data Docs HTML
- Resultado: 100% success!

### 2.4 Observability 🔄 EM ANDAMENTO (15% faltante)

**🔜 Dashboard Streamlit (5 dias)**

**Seções:**
1. **Pipeline Status** (tempo real)
   - Grid DAGs (success/fail/running)
   - Última execução + duração média vs atual
   - Taxa sucesso 30d
   - Alertas DAGs >3 falhas consecutivas

2. **Data Quality** (Great Expectations)
   - Cards: success rate por suite
   - Gráfico tendência (pass/fail over time)
   - Lista alertas ativos
   - Top 5 expectations que mais falham
   - Link Data Docs

3. **Data Freshness** (latência)
   - Tabela: última atualização (Bronze/Silver)
   - Row counts histórico (gráfico)
   - Latência pipelines (Bronze→Silver)
   - Alertas: tabelas não atualizadas >48h
   - SLA atualização (target vs real)

4. **Schema Evolution** (timeline)
   - Timeline mudanças (30d)
   - Tabela alterações (ADD/REMOVE/MODIFY)
   - Diff visual (antes/depois)
   - Severity (INFO/WARNING/CRITICAL)
   - Impacto (breaking vs non-breaking)

5. **Alertas & Incidentes**
   - Lista alertas ativos (severidade)
   - Incidentes resolvidos (7d)
   - MTTR (mean time to resolution)
   - Ações recomendadas automáticas

**Integrações:**
- Airflow REST API (dag_runs)
- PostgreSQL (row counts, schema metadata)
- GE Data Context (validation results)
- Tabelas monitoring (schema_history, data_statistics)

**Deploy:** Docker Compose, port 8501, auto-refresh 30s

**🔜 Schema Evolution Tracking - DAG 27 (1 dia)**

**Tabela:** `olist_monitoring.schema_history`
- Campos: captured_at, schema_name, table_name, column_name, data_type, is_nullable, change_type (ADDED/REMOVED/MODIFIED/UNCHANGED), previous_value, current_value

**Lógica:**
1. Capturar schema atual (information_schema.columns)
2. Comparar com última captura
3. Detectar mudanças
4. Inserir em schema_history (TODAS colunas)
5. Alertar se mudança detectada
6. Gerar diff report (JSON)

**Severidade:**
- INFO: Coluna adicionada (non-breaking)
- WARNING: Tipo alterado (pode quebrar)
- CRITICAL: Coluna removida (breaking)

**Schedule:** @daily (6h AM)

**🔜 Data Drift Detection - DAG 28 (1 dia)**

**Tabela:** `olist_monitoring.data_statistics`
- Campos: captured_at, table_name, column_name, metric_name (min/max/mean/median/p95/stddev), metric_value, row_count

**Lógica:**
1. Capturar estatísticas atuais (colunas numéricas críticas)
2. Comparar com baseline (7d atrás)
3. Calcular drift % = (current - baseline) / baseline × 100
4. Detectar desvios: WARNING >20%, CRITICAL >50%
5. Inserir em data_statistics
6. Alertar se drift detectado

**Métricas monitoradas:**
- orders.price (mean, p95)
- reviews.review_score (mean, distribuição)
- orders.order_status (% por status)
- order_items.freight_value (mean)

**Schedule:** @daily (7h AM)

**Pipeline Lineage (diagrama)**
- Arquivo: `docs/diagrams/data_lineage.mermaid`
- Mostra: CSV → Bronze → Silver → Gold → BI/ML
- Renderizado: GitHub + Streamlit
- Export: PNG/SVG para docs

### 2.5 Documentação Executiva 🔜 A FAZER

**Arquivo:** `docs/PHASE_2_SILVER_EXECUTIVE_SUMMARY.pdf`

**Estrutura (8-10 páginas):**
1. Executive Summary (1 pág) - objetivos, entregas, métricas, próximos passos
2. Arquitetura Silver (2 pág) - diagrama, fluxo, tecnologias, decisões design
3. Transformações (2 pág) - tabela comparativa, tipos, decisões técnicas, impacto
4. Data Quality (2 pág) - 47 expectations, 100% success, exemplos, benefício
5. Observability (1 pág) - dashboard, tracking, drift, alertas
6. Métricas Impacto (1 pág) - volumetria, qualidade, performance, economia
7. Próximos Passos (1 pág) - Fase 3 Gold+DBT+BI, timeline

### Métricas Fase 2
- Tabelas Silver: 8
- Registros: ~570k
- Colunas adicionadas: 40+
- DAGs: 14 (8 transform + 1 export + 3 quality + 2 monitoring)
- Expectations: 47
- Success Rate: 100%
- Data Docs: 2 sites

### Checklist Fase 2 (85%)
- [x] 8 tabelas Silver (DAGs 15-22)
- [x] Export GCS (DAG 23)
- [x] Great Expectations Silver (DAGs 24-26)
- [ ] Dashboard Streamlit 🔜 5 dias
- [ ] Schema Evolution (DAG 27) 🔜 1 dia
- [ ] Data Drift (DAG 28) 🔜 1 dia
- [ ] Lineage diagram
- [ ] Documentação Executiva PDF

**Tempo restante:** 5-7 dias | 8-12h

---

## 🥇 FASE 3: GOLD (DBT) + BI + PROBLEMA
**Status:** 🔜 PRÓXIMA (4-5 semanas)

### Objetivos
- Gold orientada a caso de uso (BI)
- **DBT para transformações** (versionamento, testes, docs)
- Problema de negócio definido
- Dashboards acionáveis

### Por quê DBT na Gold?
✅ Transformações versionadas (Git)  
✅ Testes automáticos (schema.yml)  
✅ Documentação gerada (dbt docs HTML)  
✅ Lineage visual (DAG)  
✅ Incremental models (performance)  
✅ Macros reutilizáveis (DRY)  
✅ CI/CD ready  
✅ Padrão indústria (Airbnb, GitLab, Spotify)

### 3.1 Problema de Negócio

**🎯 DEFINIDO:**
**"Como reduzir atrasos de entrega e melhorar satisfação no e-commerce Olist?"**

**Contexto:**
- Atrasos impactam review_score (correlação negativa)
- Reviews negativas afetam reputação e vendas
- Custo: cancelamentos, compensações, churn

**Sub-questões:**
1. Quais sellers/categorias têm maiores taxas de atraso?
2. Correlação atraso × review_score?
3. Impacto financeiro?
4. Rotas geográficas com maior risco?
5. Fatores preditivos?
6. Sazonalidade?

**Stakeholders:**
- Head Operations: SLA 80%→90%
- Head Customer Success: NPS 40→60
- CFO: Reduzir compensações 30%
- Marketplace: Identificar sellers problemáticos

### 3.2 Setup DBT (Semana 1 - 5 dias)

**Ações:**
- Adicionar serviço Docker
- Inicializar projeto: `dbt init olist_analytics`
- Configurar `profiles.yml` (conexão PostgreSQL)
- Configurar `dbt_project.yml` (materializations)
- Testar: `dbt debug`
- Instalar packages: dbt-utils, dbt-expectations

**Estrutura pastas:**
```
dbt/
├── models/
│   ├── sources.yml (Silver como source)
│   ├── staging/ (views bridge)
│   ├── intermediate/ (CTEs, lógica)
│   ├── marts/ (star schema)
│   └── aggregations/ (KPIs)
├── tests/
├── macros/
├── seeds/ (feriados CSV)
└── analyses/
```

### 3.3 DBT Staging (Semana 1-2 - 7 dias)

**Objetivo:** Views bridge Silver → DBT

**7 staging views criadas:**
- stg_customers
- stg_orders
- stg_products
- stg_sellers
- stg_order_items
- stg_order_payments
- stg_order_reviews

**Princípio:** Apenas SELECT, renomear, casting simples. Sem transformações negócio.

**Validação:** `dbt run --models staging` + `dbt test --models staging`

### 3.4 DBT Macros (Semana 2 - 2 dias)

**Funções SQL reutilizáveis:**

1. **calculate_delay.sql**
   - Calcula dias entre datas
   - Uso: `{{ calculate_delay('delivered', 'estimated') }}`

2. **classify_delay.sql**
   - Categorias: ON_TIME, 1-3d, 4-7d, 8-15d, >15d
   - Usa calculate_delay internamente

3. **generate_surrogate_key.sql**
   - Gera MD5 hash de colunas
   - Uso: `{{ generate_surrogate_key(['customer_id']) }}`

### 3.5 DBT Intermediate (Semana 2-3 - 7 dias)

**Lógica de negócio complexa, tables.**

**3 intermediate models:**

1. **int_order_metrics** (tabela central!)
   - JOIN: orders + items + payments + reviews
   - Cálculos: total_value, total_items, delivery_days, delay_days, is_delayed, delay_category
   - Output: 1 registro/order_id com todas métricas

2. **int_seller_performance**
   - Histórico performance de cada seller
   - Métricas: total_orders, revenue, avg_delay_days, pct_delayed, avg_review_score, seller_tier

3. **int_delivery_analysis**
   - Análise rotas (seller→customer)
   - Cálculo distância (por região)
   - distance_category: LOCAL/REGIONAL/NATIONAL
   - Tempo médio por rota

### 3.6 DBT Marts - Star Schema (Semana 3-4 - 10 dias)

**Modelagem dimensional para BI.**

**5 Dimensões:**

1. **dim_customers** (~99k)
   - Surrogate key: customer_sk (MD5)
   - Atributos: state, city, region (SUDESTE/SUL), is_capital, lat/lng
   - SCD Type 1

2. **dim_products** (~33k)
   - Surrogate key: product_sk
   - Atributos: category, weight, volume, size_category (SMALL/MEDIUM/LARGE)
   - SCD Type 1

3. **dim_sellers** (~3k)
   - Surrogate key: seller_sk
   - Atributos: state, region, performance_metrics, seller_tier
   - SCD Type 1

4. **dim_date** (~1.5k - 2016-2018)
   - Calendário: year, quarter, month, dow, is_weekend, is_holiday
   - Seed: br_holidays_2016_2018.csv

5. **dim_payment_method** (~5)
   - Mini-dimensão
   - Atributos: type, allows_installments

**3 Fatos:**

1. **fact_orders** (PRINCIPAL! ~99k)
   - Grain: 1/order_id
   - FKs: customer_sk, date_key_purchase, date_key_delivery
   - Métricas financeiras: total_value, total_items
   - **Métricas entrega (CORE!):** delivery_days, delay_days, is_delayed, delay_category
   - Métricas satisfação: review_score, review_sentiment
   - Materialization: incremental
   - Unique key: order_id

2. **fact_order_items** (~113k)
   - Grain: 1/(order_id, item_id)
   - FKs: order_sk, product_sk, seller_sk
   - Métricas: price, freight, total

3. **fact_reviews** (~99k)
   - Grain: 1/review_id
   - FK: order_sk
   - Atributos: score, comment, sentiment, has_complaint

**Validação:** `dbt run --models marts` + 30+ testes (schema.yml)

### 3.7 DBT Aggregations (Semana 4 - 3 dias)

**KPIs pré-calculados (performance dashboards).**

**4 aggregations:**

1. **agg_seller_performance**
   - Granularidade: seller_id, year_month
   - Métricas: orders, revenue, avg_delay, pct_delayed, review_score, nps

2. **agg_category_performance**
   - Granularidade: category, year_month
   - Métricas: orders, revenue, avg_delay, pct_delayed

3. **agg_geographic_analysis**
   - Granularidade: customer_region, seller_region, distance_category
   - Métricas: orders, avg_delay, pct_delayed

4. **kpi_dashboard**
   - Granularidade: 1/métrica
   - Métricas: Total Orders, On-Time %, Avg Review, Revenue, NPS
   - Cada métrica: value, target, status, variance_pct

### 3.8 Airflow + DBT (Semana 5 - 2 dias)

**DAG 30:** `run_dbt_gold`

**8 tasks sequenciais:**
1. dbt_deps (instalar packages)
2. dbt_seed (carregar feriados CSV)
3. dbt_run_staging (7 views)
4. dbt_run_intermediate (3 tables)
5. dbt_run_marts (8 tables)
6. dbt_run_aggregations (4 tables)
7. dbt_test (30+ testes)
8. dbt_docs_generate (HTML)

**Schedule:** @daily (após Silver)
**Tempo:** 5-10 min
**Alertas:** Se dbt_test falhar

### 3.9 DBT Documentation (Semana 5 - 1 dia)

**Gerada automaticamente:** `dbt docs generate` + `dbt docs serve`

**Conteúdo:**
- Lineage visual (DAG interativo)
- Model details (descrição, colunas, tipos, testes)
- Test results (pass/fail)
- Source freshness

**Acesso:** http://localhost:8080

### 3.10 Dashboards BI (Semana 5-6 - 10 dias)

**Ferramenta:** Power BI Desktop
**Conexão:** Power BI → PostgreSQL → olist_gold

**Dashboard 1: Executive Overview**
**Stakeholder:** CEO/CFO

**Página única:**
- KPI Cards: Orders, Revenue, On-Time %, NPS, Review Score
- Trend Line: Orders over time (mensal)
- Bar Chart: Revenue by category (top 10)
- Map: Orders by state (heatmap)
- Table: Top 5 sellers

**Dashboard 2: Operations - Delivery Performance**
**Stakeholder:** Head Operations

**3 páginas:**
- Pág 1: Overview (KPIs, histogram delays, bar delays by category, trend)
- Pág 2: Geographic (heatmap Brasil, matrix seller×customer, rotas problemáticas)
- Pág 3: Drill-down (sellers >30% delay rate)

**Filtros:** Date range, category, seller_tier, delay_category

**Dashboard 3: Customer Success - Satisfaction**
**Stakeholder:** Head Customer Success

**2 páginas:**
- Pág 1: NPS (gauge), review distribution, scatter delay×score, donut comments
- Pág 2: Sentiment (word cloud negativos, customers churn risk, trend)

**Filtros:** Date, review_score, has_comment

**Dashboard 4: Financial Impact**
**Stakeholder:** CFO

**1 página:**
- Waterfall: Revenue breakdown
- Bar: Revenue lost by delay category
- Line: Revenue trend (with/without delays)
- Table: ROI scenarios (10%/20%/30% reduction)

### 3.11 Análises e Insights (Semana 6 - 3 dias)

**5 análises executadas:**

1. **Correlation** (Pearson)
   - delay_days × review_score
   - Resultado esperado: r = -0.65 (forte negativa)
   - Insight: "Cada 3d atraso → -1 ponto review"

2. **Pareto** (80/20)
   - 20% sellers causam 80% atrasos?
   - Resultado: "15% sellers (450) = 82% atrasos"

3. **Seasonality**
   - Atrasos por mês
   - Resultado: Picos Nov (+40%), Dez (+30%)
   - Insight: "Black Friday sobrecarrega"

4. **Geographic**
   - Distância impacta?
   - Resultado: LOCAL 2d, REGIONAL 5d, NATIONAL 8d
   - Insight: "Nacionais atrasam 4x mais"

5. **Category Risk**
   - Categorias com maior delay_rate
   - Resultado: Móveis 60%, Eletro 55%
   - Insight: "Produtos pesados atrasam mais"

**Documento:** `docs/PHASE_3_BUSINESS_INSIGHTS.pdf` (12 páginas)

**Estrutura:**
1. Executive Summary (1) - problema, top 3 findings, top 3 recomendações
2. Metodologia (1) - dados, análises, limitações
3. Findings (5) - 1 pág/análise, gráficos, interpretações
4. Recommendations (2) - 5 recomendações acionáveis com timeline/responsável/KPI
5. Financial Impact (1) - custo atual R$2.5M, economia potencial, ROI
6. Next Steps (1) - Fase 4 ML, implementar Rec 1-2, monitorar KPIs

**Recomendações:**
1. Priorizar 450 sellers problemáticos (ações imediatas)
2. Ajustar SLA por categoria/distância (1 mês)
3. Alertas proativos ML (2 meses - Fase 4)
4. Preparação sazonalidade (contratar temporários Out/Nov)
5. Incentivar sellers locais (ajustar algoritmo busca)

### Entregas Fase 3
- 20+ DBT models
- 3 macros
- 30+ testes
- DBT docs (HTML)
- 1 DAG Airflow
- 12 tables Gold (5 dims + 3 facts + 4 aggs)
- 4 dashboards BI (7 páginas)
- 5 análises
- PDF insights (12 pág)
- Docs técnica (MD)

### Métricas Fase 3
- DBT Models: 20+
- DBT Tests: 30+
- Dashboards: 4
- Análises: 5
- Insights: 10+
- Recomendações: 5
- Tempo query: <2s

---

## 🤖 FASE 4: ML + MLOPS
**Status:** 🔜 APÓS FASE 3 (2-3 semanas)

### Objetivos
Modelo ML em produção para **prever atraso com 7d antecedência**, com drift monitoring e retraining automático.

### Problema ML
**"Prever probabilidade de atraso ANTES do envio para ação proativa"**

**Business Value:**
- Operations: Priorizar pedidos alto risco
- Customer Success: Avisar cliente proativamente
- Sellers: Notificar sellers em risco
- Outcome: -15% reviews negativos, +10 pontos NPS

### 4.1 Feature Engineering (Semana 1 - 3 dias)

**DAG 43:** `create_ml_features`

**25+ features:**

**Pedido (8):** total_value, total_items, unique_products, unique_sellers, payment_count, max_installments, used_credit_card, estimated_days

**Produto (5):** weight_g, volume_cm3, size_category, weight_category, category_name

**Seller histórico (4):** avg_delay_history, delay_rate_history, avg_review_score, seller_tier

**Geográfico (4):** seller_region, customer_region, distance_category, is_same_region

**Temporal (4):** order_dow, order_month, is_weekend, is_holiday

**Target (1):** 0=on-time, 1=delayed

**Split temporal:**
- Train: 2016-09 a 2018-02 (70%)
- Val: 2018-03-04 (15%)
- Test: 2018-05-06 (15%)

**Output:** `olist_gold.ml_delivery_features` (~90k)

### 4.2 Treinamento (Semana 1-2 - 5 dias)

**Script:** `ml/train_delay_predictor.py`

**Algoritmo:** XGBoost Classifier

**Por quê XGBoost:**
- Alta performance tabular
- Lida com imbalance
- Feature importance nativa
- Rápido

**Pipeline:**
1. Load features
2. Split temporal
3. Encoding (LabelEncoder)
4. Scaling (StandardScaler)
5. Train XGBoost (early stopping)
6. Evaluate (val, test)
7. Log MLflow (params, metrics, model)
8. Register model

**Hyperparameters:**
- n_estimators: 100
- max_depth: 6
- learning_rate: 0.1
- scale_pos_weight: 1.8

**Métricas alvo:**
- AUC-ROC: >0.75
- Precision@0.5: >0.70
- Recall@0.5: >0.60
- F1: >0.65

**Feature importance (top 10 esperado):**
1. seller_delay_rate_history (15%)
2. distance_category (12%)
3. seller_avg_delay_history (10%)
4. estimated_days (8%)
5. product_weight_g (7%)
6. total_value (6%)
7. seller_tier (5%)
8. order_month (5%)
9. is_holiday (4%)
10. product_volume_cm3 (3%)

### 4.3 MLflow Pipeline (Semana 2 - 3 dias)

**Componentes:**

**1. Experiment Tracking**
- URI: http://localhost:5000
- Experiment: olist_delivery_delay_prediction
- Registra: hyperparameters, metrics (AUC, P, R, F1), artifacts (model, encoders, scaler, feature_importance), tags, duration

**2. Model Registry**
- Name: olist_delay_predictor
- Versions: v1, v2, v3...
- Stages: None → Staging → Production
- Transitions log

**3. Model Serving (opcional)**
- API REST (FastAPI)
- Endpoint: POST /predict
- Input: features JSON
- Output: probability, risk_level

### 4.4 Batch Prediction (Semana 2 - 2 dias)

**DAG 44:** `batch_predict_delay`

**Fluxo:**
1. Load model (MLflow Production)
2. Query pedidos novos (7d, não entregues)
3. Load features
4. Predict probability
5. Classify risk_level (HIGH >0.7, MEDIUM 0.4-0.7, LOW <0.4)
6. Save `olist_gold.ml_predictions`
7. Alert HIGH RISK

**Tabela predictions:**
- prediction_id, order_id, delay_probability, risk_level, predicted_at, actual_outcome, model_version

**Schedule:** @daily
**Alertas:** >50 HIGH RISK → alerta Operations

### 4.5 Drift Monitoring (Semana 3 - 3 dias)

**DAG 45:** `monitor_ml_drift`

**Ferramenta:** Evidently AI

**2 tipos drift:**

**1. Data Drift**
- Compara features atuais vs baseline (treino)
- Evidently Report (DataDriftPreset)
- Identifica features com drift (KS test, chi-squared)
- Salva `olist_monitoring.ml_drift_monitoring`
- Alerta: >30% features drift → WARNING, >50% → CRITICAL

**2. Performance Drift**
- Query predictions + actual outcomes
- Calcula AUC atual (30d)
- Compara com baseline (treino ~0.78)
- Salva `olist_monitoring.ml_performance_monitoring`
- Alerta: drop >5% → WARNING, >10% → CRITICAL

**Tabelas:**
- ml_drift_monitoring: checked_at, baseline_size, current_size, n_drifted, drift_share, report_json
- ml_performance_monitoring: checked_at, auc_current, auc_baseline, auc_drop, sample_size

**Schedule:** @weekly (segunda 8h)
**Report:** HTML `/opt/airflow/reports/ml_drift_report.html`

### 4.6 Automatic Retraining (Semana 3 - 2 dias)

**DAG 46:** `retrain_model_if_drift`

**Fluxo:**
1. Check drift threshold (query última linha monitoring)
2. Se drift_share >30% OU auc_drop >10% → retrain
3. Retrain model (bash executa train_delay_predictor.py)
4. Validate new model (AUC >0.75?)
5. Se validado → Promote to Production (MLflow API)
6. Notify team (Slack)

**Decision tree:**
```
Drift >threshold?
├─ YES → Retrain
│   ├─ AUC >0.75?
│   │   ├─ YES → Promote
│   │   └─ NO → Keep old, alert
│   └─ Notify
└─ NO → Skip, log
```

**Schedule:** @weekly (após DAG 45)

### 4.7 A/B Testing (Opcional - 3 dias)

**Cenário:** v1 vs v2
- 50% pedidos v1 (Production)
- 50% pedidos v2 (Staging)
- 2 semanas
- Comparar AUC real
- Promover vencedor

### 4.8 Documentação ML (Semana 3 - 2 dias)

**Arquivo:** `docs/PHASE_4_ML_METHODOLOGY.md` (10 pág)

**Estrutura:**
1. Problema ML (1) - objetivo, business value, metrics
2. Feature Engineering (2) - 25+ features, importance, justificativas
3. Modeling (2) - XGBoost, hyperparameters, split temporal, imbalance
4. Results (2) - metrics, confusion matrix, ROC, feature importance
5. MLOps (2) - MLflow, batch prediction, drift, retraining
6. Business Impact (1) - ~500 high risk/mês, -15% reviews negativos, ROI R$300k/ano

### Entregas Fase 4
- Feature store (table)
- Modelo XGBoost (AUC >0.75)
- MLflow (tracking + registry)
- 4 DAGs (43-46)
- Evidently reports
- 2 tables monitoring
- API serving (opcional)
- A/B testing (opcional)
- Docs ML (10 pág)

### Métricas Fase 4
- AUC: >0.75
- Precision: >0.70
- Recall: >0.60
- Features: 25+
- Training: <10 min
- Prediction (1k): <30s
- Drift checks: Semanal
- Retraining: Automático

---

## 📊 MÉTRICAS FINAIS PROJETO

| Categoria | Métrica | Valor |
|-----------|---------|-------|
| **Dados** | Bronze | 850k |
| | Silver | 570k |
| | Tabelas Total | 31 |
| **Pipelines** | DAGs Airflow | 46+ |
| | DBT Models | 20+ |
| **Quality** | GE Expectations | 62+ |
| | Success Rate | 100% |
| **Observability** | Dashboards | 1 Streamlit |
| | Tracking | Schema + Data |
| **BI** | Dashboards | 4 |
| | Páginas | 7 |
| | Insights | 10+ |
| **ML** | Modelos | 1 |
| | AUC | >0.75 |
| | Features | 25+ |
| **Código** | Linhas | ~6.000 |
| | Commits | 100+ |
| **Docs** | Páginas | 70+ |
| | PDFs | 3 |

---

## 📅 CRONOGRAMA RESUMIDO

| Semana | Fase | Entregas | Horas |
|--------|------|----------|-------|
| 1 | Fase 0 | Setup | 15-20 |
| 2-3 | Fase 1 | Bronze + GE | 30-40 |
| 4-7 | Fase 2 | Silver + Obs | 50-60 |
| 8-12 | Fase 3 | DBT Gold + BI | 60-80 |
| 13-15 | Fase 4 | ML + MLOps | 40-50 |

**Total:** 15 semanas | 195-250h | ~15h/semana

---

## ✅ EVOLUÇÃO DOS ROADMAPS

### V1 (original - disperso)
❌ Sem DBT na Gold  
❌ Quality separada sem contexto  
❌ Sem observability  
❌ ML teórico sem MLOps  
❌ BI desconectado problema

### V2 (reestruturado)
✅ Bronze → Silver → Gold estruturado  
✅ Quality integrada  
❌ Faltava DBT na Gold  
❌ Faltava schema evolution  
❌ Faltava drift detection

### V3 FINAL (production-grade)
✅ **DBT na Gold Layer** (game changer!)  
✅ **Observability completa** (Streamlit)  
✅ **Schema Evolution Tracking**  
✅ **Data Drift Detection**  
✅ **ML Drift + Retraining automático**  
✅ **Problema de negócio real**  
✅ **Documentação executiva**  
✅ **Lineage completo**

---

## 🎯 PRÓXIMOS PASSOS IMEDIATOS

### Para completar Fase 2 (5-7 dias):
1. **Dashboard Streamlit** (5 dias)
   - Implementar 5 seções
   - Integrações (Airflow API, PostgreSQL, GE)
   - Deploy Docker

2. **DAG 27 - Schema Evolution** (1 dia)
   - Criar tabela schema_history
   - Lógica captura + comparação + alerta
   - Schedule @daily

3. **DAG 28 - Data Drift** (1 dia)
   - Criar tabela data_statistics
   - Lógica estatísticas + comparação baseline
   - Schedule @daily

4. **Pipeline Lineage** (meio dia)
   - Diagrama Mermaid
   - Export PNG/SVG

5. **Documentação Executiva** (1 dia)
   - PDF 8-10 páginas
   - Gráficos, diagramas, métricas

### Depois: Fase 3 DBT + BI (4-5 semanas)

---

**FIM DO ROADMAP V3**

**Status:** Ready to Execute  
**Última Atualização:** Fevereiro 2025  
**Autor:** Hyego + Claude  
**Versão:** 3.0 (Production-Grade)

🚀 **Projeto aprovado para execução!**
