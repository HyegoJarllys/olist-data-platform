"""
DAG: Bronze to Silver - Sellers (Technical Transformations Only)
Fase 2 - Data Transformation - Silver Layer
Autor: Hyego
Data: 2025-01-29

RESPONSABILIDADE DESTA DAG:
- Transformações TÉCNICAS e NEUTRAS
- Limpeza, padronização, enriquecimento geográfico
- SEM métricas de negócio, KPIs ou agregações

Transformações aplicadas:
1. JOIN técnico com geolocation (coordenadas)
2. Padronização de textos (trim, uppercase em UF)
3. Tratamento de valores nulos
4. Flags técnicas
5. Timestamps de auditoria
6. Índices para performance
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

# SQL para transformação Bronze → Silver (APENAS TÉCNICO)
TRANSFORM_SELLERS_SQL = """
-- ============================================
-- SILVER SELLERS: TRANSFORMAÇÕES TÉCNICAS
-- ============================================
-- Responsabilidade: Limpeza e enriquecimento técnico
-- SEM métricas de negócio (total vendido, rating, etc)
-- ============================================

DROP TABLE IF EXISTS olist_silver.sellers;

CREATE TABLE olist_silver.sellers AS
SELECT DISTINCT
    -- ============================================
    -- CHAVES ORIGINAIS (preservadas)
    -- ============================================
    s.seller_id,
    
    -- ============================================
    -- DADOS GEOGRÁFICOS (originais + padronizados)
    -- ============================================
    s.seller_zip_code_prefix,
    s.seller_city,
    UPPER(TRIM(s.seller_state)) AS seller_state,  -- Padronização: uppercase
    
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

FROM olist_raw.sellers s

-- ============================================
-- JOIN TÉCNICO: Enriquecimento Geográfico
-- LEFT JOIN para preservar todos os sellers
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
) g ON s.seller_zip_code_prefix = g.geolocation_zip_code_prefix

-- ============================================
-- GARANTIR: 1 registro por seller_id
-- ============================================
ORDER BY s.seller_id;

-- ============================================
-- ÍNDICES TÉCNICOS (para performance)
-- ============================================
CREATE INDEX idx_silver_sellers_pk ON olist_silver.sellers(seller_id);
CREATE INDEX idx_silver_sellers_state ON olist_silver.sellers(seller_state);
CREATE INDEX idx_silver_sellers_zip ON olist_silver.sellers(seller_zip_code_prefix);
CREATE INDEX idx_silver_sellers_city ON olist_silver.sellers(seller_city);
CREATE INDEX idx_silver_sellers_processed_at ON olist_silver.sellers(processed_at);

-- ============================================
-- COMENTÁRIOS TÉCNICOS (documentação)
-- ============================================
COMMENT ON TABLE olist_silver.sellers IS 
'Silver Layer - Sellers: Dados limpos e enriquecidos tecnicamente. SEM métricas de negócio.';

COMMENT ON COLUMN olist_silver.sellers.seller_id IS 
'Chave primária original (preservada da Bronze)';

COMMENT ON COLUMN olist_silver.sellers.seller_state IS 
'Estado do vendedor (padronizado: uppercase, trim)';

COMMENT ON COLUMN olist_silver.sellers.geolocation_lat IS 
'Latitude enriquecida via JOIN com geolocation. Default: 0.0 se não encontrada';

COMMENT ON COLUMN olist_silver.sellers.geolocation_lng IS 
'Longitude enriquecida via JOIN com geolocation. Default: 0.0 se não encontrada';

COMMENT ON COLUMN olist_silver.sellers.has_geolocation IS 
'Flag técnica: TRUE se coordenadas foram encontradas, FALSE caso contrário';
"""


def validate_silver_sellers():
    """
    Valida transformações TÉCNICAS da tabela silver sellers.
    
    Validações:
    1. Volumetria (comparar com Bronze)
    2. Integridade de chaves (PK única, sem nulls)
    3. Enriquecimento geográfico (% com coordenadas)
    4. Padronização de estado (uppercase)
    5. Distribuição geográfica
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Iniciando validação TÉCNICA da Silver sellers...")
        
        engine = create_engine(DB_CONNECTION)
        
        # ============================================
        # VALIDAÇÃO 1: VOLUMETRIA
        # ============================================
        validation_query = """
        WITH bronze_count AS (
            SELECT COUNT(*) AS total FROM olist_raw.sellers
        ),
        silver_count AS (
            SELECT COUNT(*) AS total FROM olist_silver.sellers
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
        
        assert vol['volumetry_status'] != 'ERROR', "❌ Perda significativa de dados!"
        
        # ============================================
        # VALIDAÇÃO 2: INTEGRIDADE DE CHAVES
        # ============================================
        keys_query = """
        SELECT 
            COUNT(*) AS total_records,
            COUNT(DISTINCT seller_id) AS unique_seller_ids,
            SUM(CASE WHEN seller_id IS NULL THEN 1 ELSE 0 END) AS null_pks,
            SUM(CASE WHEN seller_state IS NULL THEN 1 ELSE 0 END) AS null_states,
            CASE 
                WHEN COUNT(*) = COUNT(DISTINCT seller_id) THEN 'OK'
                ELSE 'ERROR'
            END AS pk_integrity
        FROM olist_silver.sellers;
        """
        
        df_keys = pd.read_sql(keys_query, engine)
        keys = df_keys.iloc[0]
        
        logger.info(f"""
        🔑 VALIDAÇÃO 2: INTEGRIDADE DE CHAVES
        - Total registros: {keys['total_records']:,}
        - Seller IDs únicos: {keys['unique_seller_ids']:,}
        - Nulls em PK: {keys['null_pks']}
        - Nulls em state: {keys['null_states']}
        - Status PK: {keys['pk_integrity']}
        """)
        
        assert keys['null_pks'] == 0, "❌ Existem nulls em seller_id (PK)!"
        assert keys['pk_integrity'] == 'OK', "❌ Existem duplicatas em seller_id!"
        
        # ============================================
        # VALIDAÇÃO 3: ENRIQUECIMENTO GEOGRÁFICO
        # ============================================
        geo_query = """
        SELECT 
            COUNT(*) AS total_sellers,
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
        FROM olist_silver.sellers;
        """
        
        df_geo = pd.read_sql(geo_query, engine)
        geo = df_geo.iloc[0]
        
        logger.info(f"""
        🌍 VALIDAÇÃO 3: ENRIQUECIMENTO GEOGRÁFICO
        - Total sellers: {geo['total_sellers']:,}
        - Com coordenadas: {geo['with_geo']:,} ({geo['geo_enrichment_pct']}%)
        - Sem coordenadas: {geo['without_geo']:,}
        - Range Latitude: [{geo['min_lat']:.2f}, {geo['max_lat']:.2f}]
        - Range Longitude: [{geo['min_lng']:.2f}, {geo['max_lng']:.2f}]
        """)
        
        # ============================================
        # VALIDAÇÃO 4: PADRONIZAÇÃO DE ESTADO
        # ============================================
        state_query = """
        SELECT 
            seller_state,
            COUNT(*) AS total,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
        FROM olist_silver.sellers
        GROUP BY seller_state
        ORDER BY total DESC
        LIMIT 10;
        """
        
        df_state = pd.read_sql(state_query, engine)
        
        logger.info("""
        📍 VALIDAÇÃO 4: TOP 10 ESTADOS
        """)
        for _, row in df_state.iterrows():
            logger.info(f"   - {row['seller_state']}: {row['total']:,} ({row['percentage']}%)")
        
        # Verificar se estados estão uppercase
        lowercase_states = df_state[df_state['seller_state'].str.islower()]
        assert len(lowercase_states) == 0, "❌ Estados não foram convertidos para uppercase!"
        
        # ============================================
        # VALIDAÇÃO 5: ÍNDICES
        # ============================================
        index_query = """
        SELECT COUNT(*) AS total_indexes
        FROM pg_indexes
        WHERE schemaname = 'olist_silver' AND tablename = 'sellers';
        """
        
        df_idx = pd.read_sql(index_query, engine)
        idx_count = df_idx.iloc[0]['total_indexes']
        
        logger.info(f"""
        🔧 VALIDAÇÃO 5: ÍNDICES TÉCNICOS
        - Total de índices criados: {idx_count}
        - Esperado: 5 índices
        """)
        
        assert idx_count == 5, f"❌ Esperado 5 índices, encontrado {idx_count}!"
        
        # ============================================
        # RESUMO FINAL
        # ============================================
        logger.info(f"""
        ✅ VALIDAÇÃO TÉCNICA CONCLUÍDA COM SUCESSO!
        
        📊 Resumo:
        - Volumetria: ✅ {vol['completeness_pct']:.2f}% preservado
        - Integridade PK: ✅ Sem duplicatas ou nulls
        - Enriquecimento Geo: ✅ {geo['geo_enrichment_pct']}% com coordenadas
        - Padronização: ✅ Estados em uppercase
        - Índices: ✅ {idx_count} criados
        
        🎯 Silver Layer pronta para Gold Layer!
        """)
        
        engine.dispose()
        
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
    dag_id='18_bronze_to_silver_sellers',
    default_args=default_args,
    description='[SILVER] Transformações técnicas: sellers (limpeza + enriquecimento geográfico)',
    schedule_interval=None,  # Execução manual
    start_date=datetime(2025, 1, 29),
    catchup=False,
    tags=['fase-2', 'silver', 'technical-transformation', 'sellers'],
) as dag:
    
    # Task 1: Transformar Bronze → Silver (apenas técnico)
    task_transform_to_silver = PostgresOperator(
        task_id='transform_to_silver',
        postgres_conn_id='postgres_default',
        sql=TRANSFORM_SELLERS_SQL,
    )
    
    # Task 2: Validar transformações técnicas
    task_validate_silver = PythonOperator(
        task_id='validate_technical_transformations',
        python_callable=validate_silver_sellers,
    )
    
    # Pipeline de execução (simples e linear)
    task_transform_to_silver >> task_validate_silver
