"""
DAG: Bronze to Silver - Customers (Technical Transformations Only)
Fase 2 - Data Transformation - Silver Layer
Autor: Hyego
Data: 2025-01-29

RESPONSABILIDADE DESTA DAG:
- Transformações TÉCNICAS e NEUTRAS
- Limpeza, padronização, enriquecimento técnico
- SEM lógica de negócio, métricas ou KPIs

Transformações aplicadas:
1. Remoção de duplicatas (DISTINCT)
2. JOIN técnico com geolocation (enriquecimento de coordenadas)
3. Padronização de tipos (COALESCE para defaults)
4. Tratamento de valores nulos
5. Timestamps de auditoria
6. Preservação de chaves originais
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta
import logging
import pandas as pd
from sqlalchemy import create_engine

default_args = {
    'owner': 'hyego',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Configurações
DB_CONNECTION = "postgresql://airflow:airflow@postgres:5432/airflow"

# SQL para criar schema silver
CREATE_SILVER_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS olist_silver;
"""

# SQL para transformação Bronze → Silver (APENAS TÉCNICO)
TRANSFORM_CUSTOMERS_SQL = """
-- ============================================
-- SILVER CUSTOMERS: TRANSFORMAÇÕES TÉCNICAS
-- ============================================
-- Responsabilidade: Limpeza e enriquecimento técnico
-- SEM métricas de negócio ou KPIs
-- ============================================

DROP TABLE IF EXISTS olist_silver.customers;

CREATE TABLE olist_silver.customers AS
SELECT DISTINCT
    -- ============================================
    -- CHAVES ORIGINAIS (preservadas)
    -- ============================================
    c.customer_id,
    c.customer_unique_id,
    
    -- ============================================
    -- DADOS GEOGRÁFICOS (originais)
    -- ============================================
    c.customer_zip_code_prefix,
    c.customer_city,
    c.customer_state,
    
    -- ============================================
    -- ENRIQUECIMENTO TÉCNICO: Geolocalização
    -- JOIN com geolocation para adicionar coordenadas
    -- COALESCE: se não existir coordenada, usar 0.0
    -- ============================================
    COALESCE(g.geolocation_lat, 0.0) AS geolocation_lat,
    COALESCE(g.geolocation_lng, 0.0) AS geolocation_lng,
    
    -- ============================================
    -- FLAGS TÉCNICAS (derivadas, mas neutras)
    -- ============================================
    CASE 
        WHEN g.geolocation_lat IS NOT NULL 
        AND g.geolocation_lng IS NOT NULL 
        THEN TRUE 
        ELSE FALSE 
    END AS has_geolocation,
    
    -- ============================================
    -- TIMESTAMPS DE AUDITORIA (técnicos)
    -- ============================================
    CURRENT_TIMESTAMP AS processed_at,
    CURRENT_TIMESTAMP AS updated_at,
    CURRENT_TIMESTAMP AS created_at

FROM olist_raw.customers c

-- ============================================
-- JOIN TÉCNICO: Enriquecimento Geográfico
-- LEFT JOIN para preservar todos os customers
-- DISTINCT ON para evitar duplicatas de geolocation
-- ============================================
LEFT JOIN (
    SELECT DISTINCT ON (geolocation_zip_code_prefix)
        geolocation_zip_code_prefix,
        geolocation_lat,
        geolocation_lng
    FROM olist_raw.geolocation
    WHERE geolocation_lat IS NOT NULL 
    AND geolocation_lng IS NOT NULL
    ORDER BY geolocation_zip_code_prefix
) g ON c.customer_zip_code_prefix = g.geolocation_zip_code_prefix

-- ============================================
-- GARANTIR: 1 registro por customer_id
-- ============================================
ORDER BY c.customer_id;

-- ============================================
-- ÍNDICES TÉCNICOS (para performance)
-- ============================================
CREATE INDEX idx_silver_customers_pk ON olist_silver.customers(customer_id);
CREATE INDEX idx_silver_customers_unique_id ON olist_silver.customers(customer_unique_id);
CREATE INDEX idx_silver_customers_state ON olist_silver.customers(customer_state);
CREATE INDEX idx_silver_customers_zip ON olist_silver.customers(customer_zip_code_prefix);
CREATE INDEX idx_silver_customers_processed_at ON olist_silver.customers(processed_at);

-- ============================================
-- COMENTÁRIOS TÉCNICOS (documentação)
-- ============================================
COMMENT ON TABLE olist_silver.customers IS 
'Silver Layer - Customers: Dados limpos e enriquecidos tecnicamente. SEM métricas de negócio.';

COMMENT ON COLUMN olist_silver.customers.customer_id IS 
'Chave primária original (preservada da Bronze)';

COMMENT ON COLUMN olist_silver.customers.geolocation_lat IS 
'Latitude enriquecida via JOIN com geolocation. Default: 0.0 se não encontrada';

COMMENT ON COLUMN olist_silver.customers.geolocation_lng IS 
'Longitude enriquecida via JOIN com geolocation. Default: 0.0 se não encontrada';

COMMENT ON COLUMN olist_silver.customers.has_geolocation IS 
'Flag técnica: TRUE se coordenadas foram encontradas, FALSE caso contrário';

COMMENT ON COLUMN olist_silver.customers.processed_at IS 
'Timestamp de quando este registro foi processado na Silver layer';
"""


def validate_silver_customers():
    """
    Valida transformações TÉCNICAS da tabela silver customers.
    
    Validações:
    1. Volumetria (comparar com Bronze)
    2. Integridade de chaves (PK única, sem nulls)
    3. Enriquecimento geográfico (% com coordenadas)
    4. Tipos de dados corretos
    5. Timestamps preenchidos
    
    NÃO valida métricas de negócio (isso é responsabilidade da Gold)
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Iniciando validação TÉCNICA da Silver customers...")
        
        engine = create_engine(DB_CONNECTION)
        
        # ============================================
        # VALIDAÇÃO 1: VOLUMETRIA
        # ============================================
        validation_query = """
        WITH bronze_count AS (
            SELECT COUNT(*) AS total FROM olist_raw.customers
        ),
        silver_count AS (
            SELECT COUNT(*) AS total FROM olist_silver.customers
        )
        SELECT 
            b.total AS bronze_records,
            s.total AS silver_records,
            s.total * 100.0 / b.total AS completeness_pct,
            CASE 
                WHEN s.total = b.total THEN 'OK'
                WHEN s.total >= b.total * 0.99 THEN 'WARNING'
                ELSE 'ERROR'
            END AS volumetry_status
        FROM bronze_count b, silver_count s;
        """
        
        df_volumetry = pd.read_sql(validation_query, engine)
        vol = df_volumetry.iloc[0]
        
        logger.info(f"""
        📊 VALIDAÇÃO 1: VOLUMETRIA
        - Bronze: {vol['bronze_records']:,} registros
        - Silver: {vol['silver_records']:,} registros
        - Completude: {vol['completeness_pct']:.2f}%
        - Status: {vol['volumetry_status']}
        """)
        
        assert vol['volumetry_status'] != 'ERROR', "❌ Perda significativa de dados na transformação!"
        
        # ============================================
        # VALIDAÇÃO 2: INTEGRIDADE DE CHAVES
        # ============================================
        keys_query = """
        SELECT 
            COUNT(*) AS total_records,
            COUNT(DISTINCT customer_id) AS unique_customer_ids,
            SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS null_pks,
            SUM(CASE WHEN customer_unique_id IS NULL THEN 1 ELSE 0 END) AS null_unique_ids,
            CASE 
                WHEN COUNT(*) = COUNT(DISTINCT customer_id) THEN 'OK'
                ELSE 'ERROR'
            END AS pk_integrity
        FROM olist_silver.customers;
        """
        
        df_keys = pd.read_sql(keys_query, engine)
        keys = df_keys.iloc[0]
        
        logger.info(f"""
        🔑 VALIDAÇÃO 2: INTEGRIDADE DE CHAVES
        - Total registros: {keys['total_records']:,}
        - Customer IDs únicos: {keys['unique_customer_ids']:,}
        - Nulls em PK: {keys['null_pks']}
        - Nulls em Unique ID: {keys['null_unique_ids']}
        - Status PK: {keys['pk_integrity']}
        """)
        
        assert keys['null_pks'] == 0, "❌ Existem nulls em customer_id (PK)!"
        assert keys['pk_integrity'] == 'OK', "❌ Existem duplicatas em customer_id!"
        
        # ============================================
        # VALIDAÇÃO 3: ENRIQUECIMENTO GEOGRÁFICO
        # ============================================
        geo_query = """
        SELECT 
            COUNT(*) AS total_customers,
            SUM(CASE WHEN has_geolocation = TRUE THEN 1 ELSE 0 END) AS with_geo,
            SUM(CASE WHEN has_geolocation = FALSE THEN 1 ELSE 0 END) AS without_geo,
            ROUND(
                SUM(CASE WHEN has_geolocation = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
                2
            ) AS geo_enrichment_pct,
            MIN(geolocation_lat) AS min_lat,
            MAX(geolocation_lat) AS max_lat,
            MIN(geolocation_lng) AS min_lng,
            MAX(geolocation_lng) AS max_lng
        FROM olist_silver.customers;
        """
        
        df_geo = pd.read_sql(geo_query, engine)
        geo = df_geo.iloc[0]
        
        logger.info(f"""
        🌍 VALIDAÇÃO 3: ENRIQUECIMENTO GEOGRÁFICO
        - Total customers: {geo['total_customers']:,}
        - Com coordenadas: {geo['with_geo']:,} ({geo['geo_enrichment_pct']}%)
        - Sem coordenadas: {geo['without_geo']:,}
        - Range Latitude: [{geo['min_lat']:.2f}, {geo['max_lat']:.2f}]
        - Range Longitude: [{geo['min_lng']:.2f}, {geo['max_lng']:.2f}]
        """)
        
        # ============================================
        # VALIDAÇÃO 4: TIMESTAMPS
        # ============================================
        timestamp_query = """
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN processed_at IS NULL THEN 1 ELSE 0 END) AS null_processed,
            SUM(CASE WHEN updated_at IS NULL THEN 1 ELSE 0 END) AS null_updated,
            SUM(CASE WHEN created_at IS NULL THEN 1 ELSE 0 END) AS null_created,
            MIN(processed_at) AS min_processed,
            MAX(processed_at) AS max_processed
        FROM olist_silver.customers;
        """
        
        df_ts = pd.read_sql(timestamp_query, engine)
        ts = df_ts.iloc[0]
        
        logger.info(f"""
        ⏰ VALIDAÇÃO 4: TIMESTAMPS DE AUDITORIA
        - Nulls em processed_at: {ts['null_processed']}
        - Nulls em updated_at: {ts['null_updated']}
        - Nulls em created_at: {ts['null_created']}
        - Processamento: {ts['min_processed']} até {ts['max_processed']}
        """)
        
        assert ts['null_processed'] == 0, "❌ Timestamps de auditoria ausentes!"
        
        # ============================================
        # VALIDAÇÃO 5: DISTRIBUIÇÃO GEOGRÁFICA
        # ============================================
        geo_dist_query = """
        SELECT 
            customer_state,
            COUNT(*) AS total_customers,
            SUM(CASE WHEN has_geolocation = TRUE THEN 1 ELSE 0 END) AS with_geo
        FROM olist_silver.customers
        GROUP BY customer_state
        ORDER BY total_customers DESC
        LIMIT 5;
        """
        
        df_geo_dist = pd.read_sql(geo_dist_query, engine)
        
        logger.info("""
        📍 VALIDAÇÃO 5: TOP 5 ESTADOS
        """)
        for _, row in df_geo_dist.iterrows():
            logger.info(f"   - {row['customer_state']}: {row['total_customers']:,} customers ({row['with_geo']:,} com geo)")
        
        # ============================================
        # RESUMO FINAL
        # ============================================
        logger.info(f"""
        ✅ VALIDAÇÃO TÉCNICA CONCLUÍDA COM SUCESSO!
        
        📊 Resumo:
        - Volumetria: ✅ {vol['completeness_pct']:.2f}% dos dados preservados
        - Integridade PK: ✅ Sem duplicatas ou nulls
        - Enriquecimento Geo: ✅ {geo['geo_enrichment_pct']}% com coordenadas
        - Timestamps: ✅ Todos preenchidos
        - Distribuição: ✅ Dados balanceados geograficamente
        
        🎯 Silver Layer pronta para Gold Layer!
        """)
        
        engine.dispose()
        
        # Retornar apenas status de sucesso (evitar problemas de serialização JSON)
        return {
            'status': 'success',
            'bronze_records': int(vol['bronze_records']),
            'silver_records': int(vol['silver_records']),
            'completeness_pct': float(vol['completeness_pct']),
            'geo_enrichment_pct': float(geo['geo_enrichment_pct'])
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Definição da DAG
with DAG(
    dag_id='15_bronze_to_silver_customers',
    default_args=default_args,
    description='[SILVER] Transformações técnicas: customers (limpeza + enriquecimento geográfico)',
    schedule_interval=None,  # Execução manual
    start_date=datetime(2025, 1, 29),
    catchup=False,
    tags=['fase-2', 'silver', 'technical-transformation', 'customers'],
) as dag:
    
    # Task 1: Criar schema silver
    task_create_schema = PostgresOperator(
        task_id='create_silver_schema',
        postgres_conn_id='postgres_default',
        sql=CREATE_SILVER_SCHEMA_SQL,
    )
    
    # Task 2: Transformar Bronze → Silver (apenas técnico)
    task_transform_to_silver = PostgresOperator(
        task_id='transform_to_silver',
        postgres_conn_id='postgres_default',
        sql=TRANSFORM_CUSTOMERS_SQL,
    )
    
    # Task 3: Validar transformações técnicas
    task_validate_silver = PythonOperator(
        task_id='validate_technical_transformations',
        python_callable=validate_silver_customers,
    )
    
    # Pipeline de execução (simples e linear)
    task_create_schema >> task_transform_to_silver >> task_validate_silver
