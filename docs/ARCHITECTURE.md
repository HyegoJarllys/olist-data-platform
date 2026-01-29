# OLIST DATA PLATFORM - ARCHITECTURE DOCUMENTATION

**Projeto:** Olist E-commerce Data Platform  
**Autor:** Hyego Jarllys  
**Data:** Janeiro 2025  
**Versão:** 1.0  
**Status:** Production  

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Arquitetura de Alto Nível](#arquitetura-de-alto-nível)
3. [Componentes Técnicos](#componentes-técnicos)
4. [Fluxo de Dados](#fluxo-de-dados)
5. [Infraestrutura](#infraestrutura)
6. [Segurança](#segurança)
7. [Escalabilidade](#escalabilidade)
8. [Disaster Recovery](#disaster-recovery)
9. [Diagramas Técnicos](#diagramas-técnicos)

---

## 🎯 VISÃO GERAL

### Objetivo da Arquitetura

A arquitetura do Olist Data Platform foi projetada seguindo princípios modernos de engenharia de dados:

- **Modularidade:** Componentes independentes e substituíveis
- **Escalabilidade:** Capacidade de crescer horizontalmente
- **Observabilidade:** Monitoramento em todas as camadas
- **Resiliência:** Tolerância a falhas e recuperação automática
- **Simplicidade:** Minimal viable architecture (MVA) para MVP

### Princípios de Design

1. **Separation of Concerns**
   - Orquestração (Airflow) separada de armazenamento (PostgreSQL/GCS)
   - Camadas de dados claramente definidas (bronze/silver/gold)
   - Validação de qualidade independente do processamento

2. **Infrastructure as Code**
   - Docker Compose para reprodutibilidade
   - Configurações versionadas
   - Ambientes idênticos (dev/staging/prod)

3. **Data Contracts**
   - Schemas explícitos (DDL versionado)
   - Great Expectations como contrato de qualidade
   - Documentação como código

4. **Fail Fast**
   - Validações antes de processar
   - Rollback automático em caso de falha
   - Alertas proativos

---

## 🏗️ ARQUITETURA DE ALTO NÍVEL

### Camadas da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Airflow UI  │  │  Data Docs   │  │   pgAdmin    │          │
│  │  (port 8080) │  │    (HTML)    │  │  (future)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Apache Airflow 2.8.1                        │   │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐  │   │
│  │  │ Webserver  │  │ Scheduler  │  │   LocalExecutor  │  │   │
│  │  └────────────┘  └────────────┘  └──────────────────┘  │   │
│  │         13 DAGs (Python)    +    Task Dependencies      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PROCESSING LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Pandas     │  │  SQLAlchemy  │  │Great Expect. │          │
│  │ (Transform)  │  │   (I/O DB)   │  │ (Validation) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       STORAGE LAYER                              │
│  ┌────────────────────────┐  ┌──────────────────────────────┐  │
│  │   PostgreSQL 13        │  │   Google Cloud Storage       │  │
│  │  ┌─────────────────┐   │  │  ┌────────────────────────┐ │  │
│  │  │ olist_raw       │   │  │  │ bronze/                │ │  │
│  │  │  - customers    │   │  │  │  - customers.parquet   │ │  │
│  │  │  - orders       │   │  │  │  - orders.parquet      │ │  │
│  │  │  - products     │   │  │  │  - products.parquet    │ │  │
│  │  │  - sellers      │   │  │  │  - sellers.parquet     │ │  │
│  │  │  - order_items  │   │  │  │  - order_items.parquet │ │  │
│  │  │  - payments     │   │  │  │  - payments.parquet    │ │  │
│  │  │  - reviews      │   │  │  │  - reviews.parquet     │ │  │
│  │  │  - geolocation  │   │  │  │  - geolocation.parquet │ │  │
│  │  └─────────────────┘   │  │  └────────────────────────┘ │  │
│  │  850k+ registros       │  │  ~20 MB total              │  │
│  └────────────────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SOURCE LAYER                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  CSV Files (Local)                       │   │
│  │  olist_customers_dataset.csv         (99.441 linhas)    │   │
│  │  olist_orders_dataset.csv            (99.441 linhas)    │   │
│  │  olist_order_items_dataset.csv       (112.650 linhas)   │   │
│  │  olist_order_payments_dataset.csv    (103.886 linhas)   │   │
│  │  olist_order_reviews_dataset.csv     (99.224 linhas)    │   │
│  │  olist_products_dataset.csv          (32.951 linhas)    │   │
│  │  olist_sellers_dataset.csv           (3.095 linhas)     │   │
│  │  olist_geolocation_dataset.csv       (1M+ linhas)       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Padrão Arquitetural: Medallion Architecture

A arquitetura segue o padrão **Medallion** (bronze/silver/gold) da Databricks:

**Bronze Layer (Raw Data):**
- Dados brutos, sem transformações
- Formato: Parquet (compressão, schema)
- Storage: Google Cloud Storage
- Objetivo: Data lake para auditoria e reprocessamento

**Silver Layer (Cleaned Data) - FASE 2:**
- Dados limpos, validados, normalizados
- Formato: Parquet particionado
- Storage: GCS + PostgreSQL (tabelas otimizadas)
- Objetivo: Analytics-ready data

**Gold Layer (Business Data) - FASE 2:**
- Agregações, métricas de negócio
- Formato: Tabelas relacionais otimizadas
- Storage: PostgreSQL (star schema)
- Objetivo: Dashboards e relatórios

---

## 🔧 COMPONENTES TÉCNICOS

### 1. Apache Airflow

**Versão:** 2.8.1  
**Executor:** LocalExecutor  
**Backend:** PostgreSQL  

**Componentes:**

```
┌─────────────────────────────────────────────────┐
│         Apache Airflow Architecture             │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │         Airflow Webserver                │  │
│  │  - Flask application (port 8080)         │  │
│  │  - UI para monitoramento                 │  │
│  │  - Autenticação básica (admin/admin)     │  │
│  └──────────────────────────────────────────┘  │
│                     │                           │
│                     ▼                           │
│  ┌──────────────────────────────────────────┐  │
│  │         Airflow Scheduler                │  │
│  │  - Parse DAGs (cada 30s)                 │  │
│  │  - Cria DagRuns e TaskInstances          │  │
│  │  - Enfileira tasks                       │  │
│  └──────────────────────────────────────────┘  │
│                     │                           │
│                     ▼                           │
│  ┌──────────────────────────────────────────┐  │
│  │         LocalExecutor                    │  │
│  │  - Executa tasks em subprocessos         │  │
│  │  - Paralelismo configurável              │  │
│  │  - Logs em arquivos                      │  │
│  └──────────────────────────────────────────┘  │
│                     │                           │
│                     ▼                           │
│  ┌──────────────────────────────────────────┐  │
│  │         Metadata Database                │  │
│  │  - PostgreSQL (mesmo container)          │  │
│  │  - Schema: airflow                       │  │
│  │  - Tabelas: dag, dag_run, task_instance  │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**Configurações Importantes:**

```yaml
AIRFLOW__CORE__EXECUTOR: LocalExecutor
AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: true
AIRFLOW__CORE__LOAD_EXAMPLES: false
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
```

**DAG Structure Pattern:**

```python
with DAG(
    dag_id='XX_<action>_<entity>',
    default_args={
        'owner': 'hyego',
        'retries': 2,
        'retry_delay': timedelta(minutes=5)
    },
    schedule_interval=None,  # Manual trigger
    catchup=False,
    tags=['fase-1', 'category']
) as dag:
    
    validate_task >> load_task >> quality_task
```

### 2. PostgreSQL

**Versão:** 13  
**Role:** Transactional database + Airflow metadata  

**Schemas:**

```sql
-- Airflow metadata (auto-criado)
airflow
  ├── dag
  ├── dag_run
  ├── task_instance
  └── ... (40+ tabelas)

-- Dados do projeto
olist_raw
  ├── customers (99.441 registros)
  ├── sellers (3.095 registros)
  ├── products (32.951 registros)
  ├── orders (99.441 registros)
  ├── order_items (112.650 registros)
  ├── order_payments (103.886 registros)
  ├── order_reviews (99.224 registros)
  └── geolocation (19.000 registros)
```

**Configurações:**

```yaml
POSTGRES_USER: airflow
POSTGRES_PASSWORD: airflow
POSTGRES_DB: airflow
Port: 5432
Max Connections: 100 (default)
Shared Buffers: 128MB (default)
```

**Índices Criados:**

Total: 28 índices

- Primary Keys: 8 (1 por tabela)
- Foreign Keys: 6 índices automáticos
- Custom Indexes: 14 (em colunas de filtro/join)

**Exemplo:**
```sql
CREATE INDEX idx_orders_customer ON olist_raw.orders(customer_id);
CREATE INDEX idx_orders_status ON olist_raw.orders(order_status);
CREATE INDEX idx_orders_purchase_date ON olist_raw.orders(order_purchase_timestamp);
```

### 3. Google Cloud Storage

**Bucket:** `olist-data-lake-hyego`  
**Region:** us-central1 (configurável)  
**Storage Class:** Standard  

**Estrutura de Diretórios:**

```
gs://olist-data-lake-hyego/
├── bronze/
│   ├── customers/
│   │   └── 2025-01-28.parquet (metadados: _loaded_at, _source_file)
│   ├── sellers/
│   │   └── 2025-01-28.parquet
│   ├── products/
│   │   └── 2025-01-28.parquet
│   ├── orders/
│   │   └── 2025-01-28.parquet
│   ├── order_items/
│   │   └── 2025-01-28.parquet
│   ├── order_payments/
│   │   └── 2025-01-28.parquet
│   ├── order_reviews/
│   │   └── 2025-01-28.parquet
│   └── geolocation/
│       └── 2025-01-28.parquet
├── silver/ (Fase 2)
└── gold/ (Fase 2)
```

**Parquet Schema:**

Cada arquivo Parquet contém:
- Todas as colunas do CSV original
- Tipos de dados preservados (int, float, timestamp, string)
- Metadados adicionais:
  - `_loaded_at`: TIMESTAMP (quando foi carregado)
  - `_source_file`: STRING (nome do CSV original)

**Configuração de Acesso:**

```python
# Credenciais via Service Account
GOOGLE_APPLICATION_CREDENTIALS=/opt/airflow/gcp-credentials.json

# Bibliotecas
google-cloud-storage==2.14.0
google-auth>=2.23.3
```

### 4. Great Expectations

**Versão:** 0.18.8  
**Context Type:** FileDataContext  
**Location:** `/opt/airflow/great_expectations` (volume persistido)  

**Estrutura de Arquivos:**

```
great_expectations/
├── great_expectations.yml           # Config principal
├── expectations/                    # Suites de validação
│   ├── orders_suite.json           # 11 expectations
│   ├── customers_suite.json        # 10 expectations
│   └── order_items_suite.json      # 10 expectations
├── checkpoints/                     # Pontos de execução
│   ├── orders_checkpoint.yml
│   ├── customers_checkpoint.yml
│   └── order_items_checkpoint.yml
├── plugins/                         # Custom expectations (vazio)
└── uncommitted/                     # Não versionado
    ├── data_docs/                   # HTML gerado
    │   └── local_site/
    │       ├── index.html
    │       ├── expectations/
    │       └── validations/
    └── validations/                 # Resultados das execuções
        └── orders_suite/
            └── orders/
                └── 20250129-*.json
```

**Datasource Configuration:**

```python
datasource_config = {
    "name": "postgres_datasource",
    "class_name": "Datasource",
    "execution_engine": {
        "class_name": "SqlAlchemyExecutionEngine",
        "connection_string": "postgresql://airflow:airflow@postgres:5432/airflow"
    },
    "data_connectors": {
        "default_runtime_data_connector": {
            "class_name": "RuntimeDataConnector",
            "batch_identifiers": ["default_identifier_name"]
        }
    }
}
```

**Checkpoint Pattern:**

```python
checkpoint_config = {
    "name": "table_checkpoint",
    "config_version": 1.0,
    "class_name": "SimpleCheckpoint",
    "run_name_template": "%Y%m%d-%H%M%S-table-validation",
}

results = context.run_checkpoint(
    checkpoint_name="table_checkpoint",
    validations=[{
        "batch_request": batch_request,
        "expectation_suite_name": "table_suite"
    }]
)
```

### 5. Docker & Docker Compose

**Docker Version:** 20.10+  
**Docker Compose Version:** 2.x  

**Serviços Definidos:**

```yaml
services:
  postgres:
    image: postgres:13
    ports: ["5432:5432"]
    volumes: [postgres-db-volume:/var/lib/postgresql/data]
    
  airflow-webserver:
    build: .
    command: webserver
    ports: ["8080:8080"]
    depends_on: [postgres, airflow-init]
    
  airflow-scheduler:
    build: .
    command: scheduler
    depends_on: [postgres, airflow-init]
    
  airflow-init:
    build: .
    command: airflow version
    environment:
      _AIRFLOW_DB_UPGRADE: 'true'
      _AIRFLOW_WWW_USER_CREATE: 'true'
```

**Volumes Montados:**

```yaml
volumes:
  - ./airflow/dags:/opt/airflow/dags
  - ./airflow/logs:/opt/airflow/logs
  - ./data:/opt/airflow/data
  - ./great_expectations:/opt/airflow/great_expectations
  - ./gcp-credentials.json:/opt/airflow/gcp-credentials.json:ro
```

**Dockerfile Customizado:**

```dockerfile
FROM apache/airflow:2.8.1-python3.10

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    && apt-get clean

USER airflow
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

RUN mkdir -p /opt/airflow/great_expectations
```

---

## 🔄 FLUXO DE DADOS

### Fluxo End-to-End

```
┌──────────────────────────────────────────────────────────────────┐
│  FASE 1: DATA INGESTION (Implementado)                          │
└──────────────────────────────────────────────────────────────────┘

1. SOURCE → VALIDATION
   CSV Files (local)
      │
      ▼
   [validate_csv task]
      ├─ Verificar colunas esperadas
      ├─ Validar PKs não nulas
      ├─ Validar FKs não nulas
      ├─ Detectar duplicatas
      └─ Gerar estatísticas

2. VALIDATION → POSTGRESQL
   [load_to_postgres task]
      ├─ Remover duplicatas (drop_duplicates)
      ├─ Converter timestamps (pd.to_datetime)
      ├─ TRUNCATE table (limpar dados antigos)
      ├─ INSERT com chunks (1000 registros/batch)
      └─ Validar row count

3. POSTGRESQL → QUALITY CHECK
   [validate_data_quality task]
      ├─ Queries agregadas (COUNT, AVG, SUM)
      ├─ Validar Foreign Keys (0 órfãos)
      ├─ Distribuições (ex: status de orders)
      └─ Log de métricas

4. SOURCE → GCS (paralelo)
   CSV Files
      │
      ▼
   [csv_to_parquet_gcs task]
      ├─ Ler CSV com Pandas
      ├─ Adicionar metadados (_loaded_at, _source_file)
      ├─ Converter para Parquet (pyarrow)
      ├─ Upload para GCS (google-cloud-storage)
      └─ Validar upload

5. POSTGRESQL → GREAT EXPECTATIONS
   PostgreSQL tables
      │
      ▼
   [run_great_expectations_validations]
      ├─ Criar Runtime Batch (LIMIT 10k)
      ├─ Executar Expectation Suite
      ├─ Gerar Validation Results
      ├─ Build Data Docs
      └─ Log success rate
```

### Fluxo de uma DAG de Ingestão (Exemplo: orders)

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  validate_csv                       │
│  - Ler: olist_orders_dataset.csv   │
│  - Validar: 8 colunas esperadas    │
│  - PKs nulas: 0                    │
│  - FKs nulas: 0 (customer_id)      │
│  - Duplicatas: X removidas         │
│  - Output: Log estatísticas        │
└─────────────────────────────────────┘
  │ SUCCESS
  ▼
┌─────────────────────────────────────┐
│  load_to_postgres                   │
│  - Conectar: SQLAlchemy engine      │
│  - TRUNCATE olist_raw.orders        │
│  - Converter timestamps (4 cols)    │
│  - INSERT 99.441 registros          │
│  - Chunks: 1000 registros/batch    │
│  - Validar COUNT(*) = 99.441       │
└─────────────────────────────────────┘
  │ SUCCESS
  ▼
┌─────────────────────────────────────┐
│  validate_data_quality              │
│  - Query: COUNT DISTINCT order_id   │
│  - Query: COUNT por order_status    │
│  - Query: FK órfãos (orders → cust) │
│  - Resultado: 0 órfãos              │
│  - Output: Métricas agregadas       │
└─────────────────────────────────────┘
  │ SUCCESS
  ▼
END (DAG Success)
```

### Fluxo de Validação Great Expectations

```
START
  │
  ▼
┌──────────────────────────────────────┐
│  Carregar FileDataContext            │
│  - Path: /opt/airflow/great_expect.. │
│  - Config: great_expectations.yml    │
└──────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────┐
│  Criar Datasource (PostgreSQL)       │
│  - Connection string                 │
│  - RuntimeDataConnector              │
└──────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────┐
│  Criar Batch Request                 │
│  - Query: SELECT * FROM table LIMIT  │
│  - Batch identifier                  │
└──────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────┐
│  Executar Checkpoint                 │
│  - Load Expectation Suite            │
│  - Run validations                   │
│  - Generate results JSON             │
└──────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────┐
│  Parse Results                       │
│  - success: true/false               │
│  - statistics.success_percent        │
│  - evaluated_expectations            │
└──────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────┐
│  Build Data Docs                     │
│  - Generate HTML pages               │
│  - Create index.html                 │
│  - Save to uncommitted/data_docs/    │
└──────────────────────────────────────┘
  │
  ▼
END
```

---

## 🖥️ INFRAESTRUTURA

### Ambientes

**Desenvolvimento (Atual):**
- Local machine (Windows)
- Docker Desktop
- Recursos: 4 CPU, 8GB RAM
- Storage: SSD local

**Produção (Futuro - Recomendado):**
- Google Cloud Platform
- Cloud Composer (Airflow gerenciado)
- Cloud SQL (PostgreSQL gerenciado)
- Networking: VPC privada

### Requisitos de Sistema

**Mínimo:**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 20 GB SSD
- Network: 10 Mbps

**Recomendado:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB SSD
- Network: 50 Mbps

**Para Produção:**
- CPU: 8+ cores
- RAM: 16+ GB
- Disk: 100+ GB SSD (com backup)
- Network: 100+ Mbps

### Network Topology

```
┌────────────────────────────────────────────────────┐
│  Docker Network: olist-data-pipeline_default      │
│  Driver: bridge                                    │
│  Subnet: 172.x.0.0/16 (auto-assigned)            │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────┐      ┌──────────────┐          │
│  │  Webserver   │◄────►│  Scheduler   │          │
│  │  172.x.0.2   │      │  172.x.0.3   │          │
│  └──────┬───────┘      └──────┬───────┘          │
│         │                     │                   │
│         └─────────┬───────────┘                   │
│                   ▼                               │
│         ┌──────────────────┐                      │
│         │    PostgreSQL    │                      │
│         │    172.x.0.4     │                      │
│         │  hostname: postgres                     │
│         └──────────────────┘                      │
│                                                    │
└────────────────────────────────────────────────────┘
         │
         │ (Port forwarding)
         ▼
┌────────────────────────────────────────────────────┐
│  Host Machine                                      │
│  localhost:8080 → Webserver:8080                  │
│  localhost:5432 → PostgreSQL:5432                 │
└────────────────────────────────────────────────────┘
```

### Comunicação entre Serviços

| From | To | Protocol | Port | Purpose |
|------|-----|----------|------|---------|
| Webserver | PostgreSQL | TCP | 5432 | Metastore queries |
| Scheduler | PostgreSQL | TCP | 5432 | DAG metadata |
| Webserver | Scheduler | HTTP | 8974 | Health checks |
| Host | Webserver | HTTP | 8080 | UI access |
| Host | PostgreSQL | TCP | 5432 | Direct queries (optional) |
| Airflow | GCS | HTTPS | 443 | Upload Parquet files |

---

## 🔒 SEGURANÇA

### Autenticação e Autorização

**Airflow UI:**
- Método: Basic Auth (username/password)
- Default user: `admin` / `admin`
- Recomendação prod: integrar com LDAP/OAuth2

**PostgreSQL:**
- User: `airflow`
- Password: `airflow` (env variable)
- Acesso: limitado à rede Docker
- Recomendação prod: passwords complexos via Secret Manager

**Google Cloud:**
- Método: Service Account
- File: `gcp-credentials.json`
- Permissions: Storage Object Admin
- Acesso: read-only mount no container

### Secrets Management

**Atual (Dev):**
```yaml
environment:
  POSTGRES_PASSWORD: airflow  # Plain text (OK para dev)
  AIRFLOW__CORE__FERNET_KEY: '' # Vazio (sem encryption)
```

**Recomendado (Prod):**
```python
# Usar Airflow Connections
from airflow.hooks.base import BaseHook

postgres_conn = BaseHook.get_connection('postgres_default')
gcs_conn = BaseHook.get_connection('google_cloud_default')

# Ou GCP Secret Manager
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
password = client.access_secret_version(name="projects/.../secrets/db-password")
```

### Network Security

**Atual:**
- Docker network isolada
- Apenas portas 8080 e 5432 expostas ao host
- GCS via HTTPS (TLS 1.2+)

**Recomendado (Prod):**
- VPC privada no GCP
- Cloud SQL proxy para PostgreSQL
- Private Service Connect para GCS
- Firewall rules restritivas

### Data Security

**Em Trânsito:**
- GCS uploads: HTTPS (TLS 1.3)
- PostgreSQL: não encriptado dentro da rede Docker
- Recomendação prod: SSL/TLS para conexões PostgreSQL

**Em Repouso:**
- PostgreSQL: sem encryption (filesystem default)
- GCS: encryption at rest padrão do GCP (AES-256)
- Recomendação: habilitar Transparent Data Encryption (TDE)

**PII e Compliance:**
- Dataset Olist: sem PII (customer_id = UUID)
- Não aplicável: LGPD/GDPR
- Recomendação: para dados reais, implementar tokenização/masking

---

## 📈 ESCALABILIDADE

### Escalabilidade Horizontal

**Airflow:**
- Atual: LocalExecutor (single node)
- Próximo passo: CeleryExecutor com Redis
- Futuro: KubernetesExecutor (pods on-demand)

**PostgreSQL:**
- Atual: Single instance
- Próximo passo: Read replicas
- Futuro: Cloud SQL HA com failover automático

**GCS:**
- Já escalável infinitamente (managed service)
- Rate limits: 5000 writes/s, 20000 reads/s por bucket

### Escalabilidade Vertical

**Recursos Ajustáveis:**

```yaml
# docker-compose.yml
services:
  airflow-webserver:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

**Parâmetros PostgreSQL:**

```sql
-- Ajustar para workload maior
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET work_mem = '50MB';
ALTER SYSTEM SET max_connections = 200;
```

### Performance Optimization

**Já Implementado:**
- Chunked inserts (1000 registros/batch)
- Parquet com compressão Snappy
- Índices em colunas de filtro/join
- Great Expectations com LIMIT 10k

**Próximos Passos:**
- Particionamento de tabelas por data
- Incremental loads (apenas novos dados)
- Connection pooling (pgbouncer)
- Materialized views para agregações

---

## 🔄 DISASTER RECOVERY

### Backup Strategy

**PostgreSQL:**

Atual:
- Volume Docker com dados persistidos
- Backup manual: `docker exec postgres pg_dump`

Recomendado:
```bash
# Backup automatizado (cron diário)
pg_dump -h postgres -U airflow airflow > backup_$(date +%Y%m%d).sql

# Retention: 7 dias locais, 30 dias em GCS
gsutil cp backup_*.sql gs://olist-backups/postgres/
```

**GCS:**
- Versionamento de objetos habilitado
- Lifecycle policy: mover para Nearline após 30 dias
- Retenção: 1 ano

**Great Expectations:**
- Arquivos versionados no Git
- Backup automático via volume Docker
- Data Docs regeneráveis a qualquer momento

### Recovery Time Objective (RTO)

| Componente | RTO Atual | RTO Prod Recomendado |
|------------|-----------|----------------------|
| Airflow Webserver | 5 minutos (restart container) | 2 minutos (auto-healing) |
| Airflow Scheduler | 5 minutos (restart container) | 1 minuto (standby replica) |
| PostgreSQL | 10 minutos (restore backup) | 5 minutos (failover automático) |
| GCS | N/A (managed, 99.9% SLA) | N/A |

### Recovery Point Objective (RPO)

| Dado | RPO Atual | RPO Prod Recomendado |
|------|-----------|----------------------|
| Metadados Airflow | 24 horas (backup diário) | 1 hora (streaming replication) |
| Dados olist_raw | 0 (reprocessável dos CSVs) | 0 (reprocessável) |
| GCS bronze | 0 (versioned) | 0 (versioned) |
| Great Expectations config | 0 (Git) | 0 (Git) |

### Disaster Scenarios

**Scenario 1: Container crash**
- Impacto: Serviço indisponível
- Recovery: `docker-compose restart`
- Tempo: ~1 minuto
- Perda de dados: nenhuma (volumes persistidos)

**Scenario 2: Corrupção de dados PostgreSQL**
- Impacto: Queries falham
- Recovery: Restore do último backup + reprocessar DAGs
- Tempo: ~30 minutos
- Perda de dados: até 24h de metadados Airflow

**Scenario 3: Perda de host machine**
- Impacto: Tudo offline
- Recovery: Provisionar novo host + restore backups
- Tempo: ~2 horas
- Perda de dados: até 24h de metadados; 0 para dados (CSVs + GCS)

**Scenario 4: Exclusão acidental de bucket GCS**
- Impacto: Bronze layer perdido
- Recovery: Reprocessar DAG `04_ingest_csv_to_gcs`
- Tempo: ~10 minutos
- Perda de dados: nenhuma (CSVs originais existem)

---

## 📊 DIAGRAMAS TÉCNICOS

### Entity Relationship Diagram (ERD)

```
┌─────────────────┐
│   CUSTOMERS     │
│─────────────────│
│ PK customer_id  │───┐
│    cust_unique  │   │
│    zip_code     │   │
│    city         │   │
│    state        │   │
└─────────────────┘   │
                      │ 1:N
                      ▼
                ┌─────────────────┐
                │     ORDERS      │
                │─────────────────│
                │ PK order_id     │───┐
                │ FK customer_id  │   │
                │    status       │   │ 1:N
                │    purchase_ts  │   │
                │    delivered_ts │   │
                └─────────────────┘   │
                      │               │
                      │ 1:N           │
                      ▼               ▼
            ┌─────────────────┐  ┌──────────────────┐
            │  ORDER_PAYMENTS │  │   ORDER_REVIEWS  │
            │─────────────────│  │──────────────────│
            │PK order_id      │  │PK review_id      │
            │PK payment_seq   │  │FK order_id       │
            │   type          │  │   score (1-5)    │
            │   installments  │  │   comment        │
            │   value         │  │   creation_date  │
            └─────────────────┘  └──────────────────┘

                ┌─────────────────┐
                │   ORDER_ITEMS   │
                │─────────────────│
                │PK order_id      │───┐
                │PK item_id       │   │
                │FK product_id    │───┼──┐
                │FK seller_id     │───┼──┼──┐
                │   price         │   │  │  │
                │   freight       │   │  │  │
                └─────────────────┘   │  │  │
                      │               │  │  │
                      │               │  │  │
┌─────────────────┐   │  ┌────────────▼──┐  │  ┌─────────────────┐
│    PRODUCTS     │◄──┘  │   SELLERS     │◄─┘  │   GEOLOCATION   │
│─────────────────│      │───────────────│      │─────────────────│
│ PK product_id   │      │PK seller_id   │      │PK zip_code_pref │
│    category     │      │   zip_code    │      │PK lat           │
│    name_length  │      │   city        │      │PK lng           │
│    weight       │      │   state       │      │   city          │
│    dimensions   │      └───────────────┘      │   state         │
└─────────────────┘                             └─────────────────┘
```

### DAG Dependency Graph

```
Fase 1 - Setup (One-time)
┌──────────────────────────┐
│ 00_test_gcs_connection   │
└──────────────────────────┘
            │
            ▼
┌──────────────────────────┐
│ 04_create_schema         │
└──────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────┐
│           Ingestion (Paralelo)                       │
│  ┌────────────────┐  ┌────────────────┐            │
│  │ 05_customers   │  │ 06_sellers     │            │
│  └────────────────┘  └────────────────┘            │
│  ┌────────────────┐  ┌────────────────┐            │
│  │ 07_products    │  │ 12_geolocation │            │
│  └────────────────┘  └────────────────┘            │
└──────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────┐
│ 08_orders                │ (depende: customers)
└──────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────┐
│           Items/Payments/Reviews (Paralelo)          │
│  ┌────────────────┐  ┌────────────────┐            │
│  │ 09_order_items │  │ 10_payments    │            │
│  └────────────────┘  └────────────────┘            │
│  ┌────────────────┐                                 │
│  │ 11_reviews     │  (depende: orders)             │
│  └────────────────┘                                 │
└──────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────┐
│ 04_ingest_csv_to_gcs     │ (paralelo com PostgreSQL)
└──────────────────────────┘
            │
            ▼
┌──────────────────────────┐
│ 05_validate_data_quality │
└──────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────┐
│           Great Expectations (One-time Setup)        │
│  ┌────────────────────────────┐                     │
│  │ 06_setup_great_expectations│                     │
│  └────────────────────────────┘                     │
│            │                                         │
│            ▼                                         │
│  ┌────────────────────────────┐                     │
│  │ 07_create_expectation_suites│                    │
│  └────────────────────────────┘                     │
└──────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────┐
│           Great Expectations (Recorrente)            │
│  ┌────────────────────────────┐                     │
│  │ 08_run_ge_validations      │                     │
│  └────────────────────────────┘                     │
│            │                                         │
│            ▼                                         │
│  ┌────────────────────────────┐                     │
│  │ 09_force_build_data_docs   │                     │
│  └────────────────────────────┘                     │
└──────────────────────────────────────────────────────┘
```

### Data Flow Diagram (DFD) - Nível 1

```
┌──────────────┐
│  CSV Files   │
│  (Source)    │
└──────┬───────┘
       │
       ├──────────────────────┬────────────────────────┐
       │                      │                        │
       ▼                      ▼                        ▼
┌──────────────┐    ┌──────────────┐        ┌──────────────┐
│   Airflow    │    │   Airflow    │        │   Airflow    │
│   Validate   │    │   Transform  │        │   Load GCS   │
│              │    │              │        │              │
└──────┬───────┘    └──────┬───────┘        └──────┬───────┘
       │                   │                        │
       │ ✅ OK             │                        │
       ▼                   ▼                        ▼
┌──────────────┐    ┌──────────────┐        ┌──────────────┐
│  PostgreSQL  │    │  PostgreSQL  │        │     GCS      │
│  (olist_raw) │◄───┤  (olist_raw) │        │  (bronze/)   │
└──────┬───────┘    └──────────────┘        └──────────────┘
       │
       │
       ▼
┌──────────────┐
│Great Expect. │
│  Validations │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Data Docs   │
│   (HTML)     │
└──────────────┘
```

---

## 🔍 MONITORAMENTO E OBSERVABILIDADE

### Métricas Atuais

**Airflow UI:**
- Status de DAGs (success/failed/running)
- Duração de tasks
- Logs detalhados
- Gantt chart de execução

**PostgreSQL:**
```sql
-- Query para monitorar tamanho das tabelas
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'olist_raw'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Great Expectations:**
- Data Docs HTML (success rate, expectations detalhadas)
- Validation results JSON
- Historical trend (manual via validations files)

### Alertas (Futuro)

**Recomendado implementar:**
- Slack webhook quando DAG falha
- Email quando Great Expectations < 80% success
- CloudWatch/Prometheus metrics
- Grafana dashboards

---

## 📚 REFERÊNCIAS ARQUITETURAIS

### Padrões Utilizados

1. **Medallion Architecture**
   - Bronze/Silver/Gold layers
   - Origem: Databricks

2. **ELT (Extract, Load, Transform)**
   - Load first, transform later
   - Vantagem: auditabilidade, reprocessamento

3. **Idempotency**
   - DAGs podem ser re-executadas sem side effects
   - TRUNCATE + INSERT vs UPSERT

4. **Schema-on-Read**
   - GCS bronze layer sem schema enforcement
   - Schema aplicado na leitura (silver layer)

### Trade-offs Arquiteturais

| Decisão | Prós | Contras |
|---------|------|---------|
| LocalExecutor vs CeleryExecutor | Simples, sem Redis | Não escala horizontalmente |
| PostgreSQL transacional | ACID, relacional | Não otimizado para analytics |
| Parquet no GCS | Eficiente, portável | Overhead de conversão |
| Great Expectations | Observabilidade | Complexidade adicional |
| Docker Compose | Reproduzível, local | Não cloud-native |

---

## 📝 CONCLUSÃO

A arquitetura do Olist Data Platform estabelece uma fundação sólida para crescimento futuro. Os princípios de modularidade, observabilidade e simplicidade permitem evolução incremental sem rewrites completos.

**Próximas Evoluções Arquiteturais:**
1. Migração para Cloud Composer (Airflow gerenciado)
2. Implementação de camadas Silver/Gold
3. CI/CD com testes automatizados
4. Monitoring avançado (Prometheus + Grafana)
5. Incremental loads e CDC

---

**Última atualização:** 29 de Janeiro de 2025  
**Autor:** Hyego Jarllys  
**Versão:** 1.0  
**Status:** Aprovado para Produção MVP
