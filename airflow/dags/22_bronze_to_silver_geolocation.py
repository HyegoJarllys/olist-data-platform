"""
DAG: Bronze to Silver - Geolocation (Technical Transformations Only)
Fase 2 - Data Transformation - Silver Layer
Autor: Hyego
Data: 2025-01-29

RESPONSABILIDADE DESTA DAG:
- Transformações TÉCNICAS e NEUTRAS
- Limpeza, deduplicação, padronização
- SEM métricas de negócio, KPIs ou agregações

Transformações aplicadas:
1. Deduplicação (1 coordenada por CEP)
2. Padronização de UF (uppercase, trim)
3. Validação de coordenadas (range válido Brasil)
4. Conversão de tipos numéricos
5. Timestamps de auditoria
6. Índices para performance

NOTA: Esta é a ÚLTIMA tabela Silver da Fase 2!
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
TRANSFORM_GEOLOCATION_SQL = """
-- ============================================
-- SILVER GEOLOCATION: TRANSFORMAÇÕES TÉCNICAS
-- ============================================
-- Responsabilidade: Limpeza, deduplicação, padronização
-- SEM métricas de negócio
-- ============================================

DROP TABLE IF EXISTS olist_silver.geolocation;

CREATE TABLE olist_silver.geolocation AS
SELECT DISTINCT ON (geolocation_zip_code_prefix)
    -- ============================================
    -- CEP (chave primária após deduplicação)
    -- ============================================
    g.geolocation_zip_code_prefix,
    
    -- ============================================
    -- COORDENADAS (NUMERIC para precisão)
    -- Filtrar apenas coordenadas válidas (não NULL)
    -- ============================================
    g.geolocation_lat::NUMERIC(10,6) AS geolocation_lat,
    g.geolocation_lng::NUMERIC(10,6) AS geolocation_lng,
    
    -- ============================================
    -- LOCALIZAÇÃO (padronizados)
    -- ============================================
    TRIM(g.geolocation_city) AS geolocation_city,
    UPPER(TRIM(g.geolocation_state)) AS geolocation_state,
    
    -- ============================================
    -- FLAGS TÉCNICAS (validação de coordenadas)
    -- Brasil: Lat -33 a 5, Lng -74 a -34
    -- ============================================
    CASE 
        WHEN g.geolocation_lat BETWEEN -33 AND 5 
        AND g.geolocation_lng BETWEEN -74 AND -34 
        THEN TRUE 
        ELSE FALSE 
    END AS is_valid_brazil_coords,
    
    -- ============================================
    -- CONTAGEM DE DUPLICATAS ORIGINAIS
    -- Quantas vezes este CEP aparecia na Bronze
    -- ============================================
    (
        SELECT COUNT(*) 
        FROM olist_raw.geolocation g2 
        WHERE g2.geolocation_zip_code_prefix = g.geolocation_zip_code_prefix
    ) AS original_count,
    
    -- ============================================
    -- TIMESTAMPS DE AUDITORIA (técnicos)
    -- ============================================
    CURRENT_TIMESTAMP AS processed_at,
    CURRENT_TIMESTAMP AS updated_at,
    CURRENT_TIMESTAMP AS created_at

FROM olist_raw.geolocation g

-- ============================================
-- FILTROS: Apenas coordenadas válidas
-- ============================================
WHERE g.geolocation_lat IS NOT NULL 
AND g.geolocation_lng IS NOT NULL
AND g.geolocation_lat BETWEEN -33 AND 5 
AND g.geolocation_lng BETWEEN -74 AND -34

-- ============================================
-- DEDUPLICAÇÃO: 1 registro por CEP
-- DISTINCT ON pega a primeira ocorrência
-- ============================================
ORDER BY g.geolocation_zip_code_prefix;

-- ============================================
-- ÍNDICES TÉCNICOS (para performance)
-- ============================================
CREATE INDEX idx_silver_geolocation_pk ON olist_silver.geolocation(geolocation_zip_code_prefix);
CREATE INDEX idx_silver_geolocation_state ON olist_silver.geolocation(geolocation_state);
CREATE INDEX idx_silver_geolocation_city ON olist_silver.geolocation(geolocation_city);
CREATE INDEX idx_silver_geolocation_coords ON olist_silver.geolocation(geolocation_lat, geolocation_lng);
CREATE INDEX idx_silver_geolocation_processed_at ON olist_silver.geolocation(processed_at);

-- ============================================
-- COMENTÁRIOS TÉCNICOS (documentação)
-- ============================================
COMMENT ON TABLE olist_silver.geolocation IS 
'Silver Layer - Geolocation: Dados deduplicados (1 coordenada por CEP). SEM métricas de negócio.';

COMMENT ON COLUMN olist_silver.geolocation.geolocation_zip_code_prefix IS 
'CEP (5 dígitos). Chave primária após deduplicação';

COMMENT ON COLUMN olist_silver.geolocation.geolocation_lat IS 
'Latitude (NUMERIC 10,6). Validada: Brasil (-33 a 5)';

COMMENT ON COLUMN olist_silver.geolocation.geolocation_lng IS 
'Longitude (NUMERIC 10,6). Validada: Brasil (-74 a -34)';

COMMENT ON COLUMN olist_silver.geolocation.geolocation_state IS 
'UF (padronizado: uppercase, trim)';

COMMENT ON COLUMN olist_silver.geolocation.is_valid_brazil_coords IS 
'Flag técnica: TRUE se coordenadas dentro do range do Brasil';

COMMENT ON COLUMN olist_silver.geolocation.original_count IS 
'Contador: quantas vezes este CEP aparecia na Bronze (antes da deduplicação)';
"""


def validate_silver_geolocation():
    """
    Valida transformações TÉCNICAS da tabela silver geolocation.
    
    Validações:
    1. Deduplicação (1 registro por CEP)
    2. Redução de volumetria (esperada)
    3. Coordenadas válidas (range Brasil)
    4. Padronização de estado
    5. Distribuição geográfica
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Iniciando validação TÉCNICA da Silver geolocation...")
        
        engine = create_engine(DB_CONNECTION)
        
        # ============================================
        # VALIDAÇÃO 1: DEDUPLICAÇÃO
        # ============================================
        dedup_query = """
        WITH bronze_count AS (
            SELECT 
                COUNT(*) AS total,
                COUNT(DISTINCT geolocation_zip_code_prefix) AS unique_zips
            FROM olist_raw.geolocation
        ),
        silver_count AS (
            SELECT 
                COUNT(*) AS total,
                COUNT(DISTINCT geolocation_zip_code_prefix) AS unique_zips
            FROM olist_silver.geolocation
        )
        SELECT 
            b.total AS bronze_records,
            b.unique_zips AS bronze_unique_zips,
            s.total AS silver_records,
            s.unique_zips AS silver_unique_zips,
            ROUND((b.total - s.total) * 100.0 / b.total, 2) AS reduction_pct
        FROM bronze_count b, silver_count s;
        """
        
        df_dedup = pd.read_sql(dedup_query, engine)
        dedup = df_dedup.iloc[0]
        
        logger.info(f"""
        📊 VALIDAÇÃO 1: DEDUPLICAÇÃO
        - Bronze (total): {dedup['bronze_records']:,} registros
        - Bronze (CEPs únicos): {dedup['bronze_unique_zips']:,}
        - Silver (total): {dedup['silver_records']:,} registros
        - Silver (CEPs únicos): {dedup['silver_unique_zips']:,}
        - Redução: {dedup['reduction_pct']:.2f}% (esperado!)
        """)
        
        # Silver deve ter exatamente 1 registro por CEP
        assert dedup['silver_records'] == dedup['silver_unique_zips'], "❌ Silver tem duplicatas!"
        
        # ============================================
        # VALIDAÇÃO 2: INTEGRIDADE DE CHAVE
        # ============================================
        keys_query = """
        SELECT 
            COUNT(*) AS total_records,
            COUNT(DISTINCT geolocation_zip_code_prefix) AS unique_zips,
            SUM(CASE WHEN geolocation_zip_code_prefix IS NULL THEN 1 ELSE 0 END) AS null_pks,
            CASE 
                WHEN COUNT(*) = COUNT(DISTINCT geolocation_zip_code_prefix) THEN 'OK'
                ELSE 'ERROR'
            END AS pk_integrity
        FROM olist_silver.geolocation;
        """
        
        df_keys = pd.read_sql(keys_query, engine)
        keys = df_keys.iloc[0]
        
        logger.info(f"""
        🔑 VALIDAÇÃO 2: INTEGRIDADE DE CHAVE
        - Total registros: {keys['total_records']:,}
        - CEPs únicos: {keys['unique_zips']:,}
        - Nulls em PK: {keys['null_pks']}
        - Status PK: {keys['pk_integrity']}
        """)
        
        assert keys['null_pks'] == 0, "❌ Existem nulls em geolocation_zip_code_prefix (PK)!"
        assert keys['pk_integrity'] == 'OK', "❌ Existem duplicatas!"
        
        # ============================================
        # VALIDAÇÃO 3: COORDENADAS VÁLIDAS
        # ============================================
        coords_query = """
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN is_valid_brazil_coords = TRUE THEN 1 ELSE 0 END) AS valid_coords,
            ROUND(MIN(geolocation_lat), 2) AS min_lat,
            ROUND(MAX(geolocation_lat), 2) AS max_lat,
            ROUND(MIN(geolocation_lng), 2) AS min_lng,
            ROUND(MAX(geolocation_lng), 2) AS max_lng,
            ROUND(AVG(geolocation_lat), 2) AS avg_lat,
            ROUND(AVG(geolocation_lng), 2) AS avg_lng
        FROM olist_silver.geolocation;
        """
        
        df_coords = pd.read_sql(coords_query, engine)
        coords = df_coords.iloc[0]
        
        logger.info(f"""
        🌎 VALIDAÇÃO 3: COORDENADAS
        - Total CEPs: {coords['total']:,}
        - Coordenadas válidas (Brasil): {coords['valid_coords']:,} ({coords['valid_coords']*100/coords['total']:.2f}%)
        - Latitude (min/max): {coords['min_lat']} / {coords['max_lat']}
        - Longitude (min/max): {coords['min_lng']} / {coords['max_lng']}
        - Centro médio: ({coords['avg_lat']}, {coords['avg_lng']})
        """)
        
        # Todas devem ser válidas (filtro aplicado no SQL)
        assert coords['valid_coords'] == coords['total'], "❌ Existem coordenadas inválidas!"
        
        # ============================================
        # VALIDAÇÃO 4: DISTRIBUIÇÃO POR ESTADO
        # ============================================
        state_query = """
        SELECT 
            geolocation_state,
            COUNT(*) AS total,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
        FROM olist_silver.geolocation
        GROUP BY geolocation_state
        ORDER BY total DESC
        LIMIT 10;
        """
        
        df_state = pd.read_sql(state_query, engine)
        
        logger.info("""
        📍 VALIDAÇÃO 4: TOP 10 ESTADOS
        """)
        for _, row in df_state.iterrows():
            logger.info(f"   - {row['geolocation_state']}: {row['total']:,} CEPs ({row['percentage']}%)")
        
        # Verificar se estados estão uppercase
        lowercase_states = df_state[df_state['geolocation_state'].str.islower()]
        assert len(lowercase_states) == 0, "❌ Estados não foram convertidos para uppercase!"
        
        # ============================================
        # VALIDAÇÃO 5: ANÁLISE DE DEDUPLICAÇÃO
        # ============================================
        dedup_analysis_query = """
        SELECT 
            AVG(original_count) AS avg_duplicates,
            MAX(original_count) AS max_duplicates,
            SUM(CASE WHEN original_count > 1 THEN 1 ELSE 0 END) AS zips_had_duplicates
        FROM olist_silver.geolocation;
        """
        
        df_analysis = pd.read_sql(dedup_analysis_query, engine)
        analysis = df_analysis.iloc[0]
        
        logger.info(f"""
        🔍 VALIDAÇÃO 5: ANÁLISE DE DEDUPLICAÇÃO
        - Média de duplicatas por CEP (Bronze): {analysis['avg_duplicates']:.2f}
        - Máximo de duplicatas (Bronze): {analysis['max_duplicates']}
        - CEPs que tinham duplicatas: {analysis['zips_had_duplicates']:,}
        """)
        
        # ============================================
        # VALIDAÇÃO 6: ÍNDICES
        # ============================================
        index_query = """
        SELECT COUNT(*) AS total_indexes
        FROM pg_indexes
        WHERE schemaname = 'olist_silver' AND tablename = 'geolocation';
        """
        
        df_idx = pd.read_sql(index_query, engine)
        idx_count = df_idx.iloc[0]['total_indexes']
        
        logger.info(f"""
        🔧 VALIDAÇÃO 6: ÍNDICES TÉCNICOS
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
        - Deduplicação: ✅ 1 registro por CEP ({keys['unique_zips']:,} CEPs)
        - Redução: ✅ {dedup['reduction_pct']:.2f}% (esperado)
        - Coordenadas: ✅ 100% válidas (Brasil)
        - Padronização: ✅ Estados em uppercase
        - Índices: ✅ {idx_count} criados
        
        🎉 ÚLTIMA TABELA SILVER CONCLUÍDA!
        🎯 Todas as 8 tabelas Silver prontas para Gold Layer!
        """)
        
        engine.dispose()
        
        return {
            'status': 'success',
            'bronze_records': int(dedup['bronze_records']),
            'silver_records': int(dedup['silver_records']),
            'unique_zips': int(keys['unique_zips']),
            'reduction_pct': float(dedup['reduction_pct'])
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Definição da DAG
with DAG(
    dag_id='22_bronze_to_silver_geolocation',
    default_args=default_args,
    description='[SILVER] Transformações técnicas: geolocation (deduplicação + validação) - ÚLTIMA SILVER!',
    schedule_interval=None,  # Execução manual
    start_date=datetime(2025, 1, 29),
    catchup=False,
    tags=['fase-2', 'silver', 'technical-transformation', 'geolocation', 'final'],
) as dag:
    
    # Task 1: Transformar Bronze → Silver (apenas técnico)
    task_transform_to_silver = PostgresOperator(
        task_id='transform_to_silver',
        postgres_conn_id='postgres_default',
        sql=TRANSFORM_GEOLOCATION_SQL,
    )
    
    # Task 2: Validar transformações técnicas
    task_validate_silver = PythonOperator(
        task_id='validate_technical_transformations',
        python_callable=validate_silver_geolocation,
    )
    
    # Pipeline de execução (simples e linear)
    task_transform_to_silver >> task_validate_silver
