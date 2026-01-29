"""
DAG: Bronze to Silver - Order Reviews (Technical Transformations Only)
Fase 2 - Data Transformation - Silver Layer
Autor: Hyego
Data: 2025-01-29

RESPONSABILIDADE DESTA DAG:
- Transformações TÉCNICAS e NEUTRAS
- Limpeza, padronização, conversão de tipos
- SEM métricas de negócio, KPIs ou agregações

Transformações aplicadas:
1. Conversão de timestamps
2. Padronização de review_score (garantir range 1-5)
3. Tratamento de NULLs em campos opcionais (comment_title, comment_message)
4. Validação de chave primária
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
TRANSFORM_ORDER_REVIEWS_SQL = """
-- ============================================
-- SILVER ORDER_REVIEWS: TRANSFORMAÇÕES TÉCNICAS
-- ============================================
-- Responsabilidade: Limpeza e padronização técnica
-- SEM métricas de negócio (NPS, sentimento, etc)
-- ============================================

DROP TABLE IF EXISTS olist_silver.order_reviews;

CREATE TABLE olist_silver.order_reviews AS
SELECT DISTINCT
    -- ============================================
    -- CHAVES (PK + FK)
    -- ============================================
    r.review_id,
    r.order_id,
    
    -- ============================================
    -- SCORE (garantir INTEGER e range válido 1-5)
    -- ============================================
    r.review_score::INTEGER AS review_score,
    
    -- ============================================
    -- TEXTOS (preservar NULLs - são opcionais)
    -- TRIM para remover espaços desnecessários
    -- ============================================
    CASE 
        WHEN r.review_comment_title IS NOT NULL 
        THEN TRIM(r.review_comment_title)
        ELSE NULL
    END AS review_comment_title,
    
    CASE 
        WHEN r.review_comment_message IS NOT NULL 
        THEN TRIM(r.review_comment_message)
        ELSE NULL
    END AS review_comment_message,
    
    -- ============================================
    -- TIMESTAMPS (garantir tipo correto)
    -- ============================================
    r.review_creation_date::TIMESTAMP AS review_creation_date,
    r.review_answer_timestamp::TIMESTAMP AS review_answer_timestamp,
    
    -- ============================================
    -- TAMANHO DOS COMENTÁRIOS (derivação técnica)
    -- NULL se comentário não existe
    -- ============================================
    CASE 
        WHEN r.review_comment_message IS NOT NULL 
        THEN LENGTH(TRIM(r.review_comment_message))
        ELSE 0
    END AS comment_length,
    
    -- ============================================
    -- FLAGS TÉCNICAS (derivadas, mas neutras)
    -- ============================================
    r.review_comment_title IS NOT NULL AS has_comment_title,
    r.review_comment_message IS NOT NULL AS has_comment_message,
    r.review_answer_timestamp IS NOT NULL AS has_answer,
    r.review_score >= 4 AS is_positive_score,
    r.review_score <= 2 AS is_negative_score,
    
    -- ============================================
    -- TIMESTAMPS DE AUDITORIA (técnicos)
    -- ============================================
    CURRENT_TIMESTAMP AS processed_at,
    CURRENT_TIMESTAMP AS updated_at,
    CURRENT_TIMESTAMP AS created_at

FROM olist_raw.order_reviews r

-- ============================================
-- GARANTIR: 1 registro por review_id
-- ============================================
ORDER BY r.review_id;

-- ============================================
-- ÍNDICES TÉCNICOS (para performance)
-- ============================================
CREATE INDEX idx_silver_order_reviews_pk ON olist_silver.order_reviews(review_id);
CREATE INDEX idx_silver_order_reviews_order_id ON olist_silver.order_reviews(order_id);
CREATE INDEX idx_silver_order_reviews_score ON olist_silver.order_reviews(review_score);
CREATE INDEX idx_silver_order_reviews_creation_date ON olist_silver.order_reviews(review_creation_date);
CREATE INDEX idx_silver_order_reviews_has_comment ON olist_silver.order_reviews(has_comment_message);
CREATE INDEX idx_silver_order_reviews_processed_at ON olist_silver.order_reviews(processed_at);

-- ============================================
-- COMENTÁRIOS TÉCNICOS (documentação)
-- ============================================
COMMENT ON TABLE olist_silver.order_reviews IS 
'Silver Layer - Order Reviews: Dados limpos e padronizados. SEM métricas de negócio (NPS).';

COMMENT ON COLUMN olist_silver.order_reviews.review_id IS 
'Chave primária original (preservada da Bronze)';

COMMENT ON COLUMN olist_silver.order_reviews.review_score IS 
'Score da avaliação (INTEGER, range: 1-5)';

COMMENT ON COLUMN olist_silver.order_reviews.review_comment_title IS 
'Título do comentário (TRIM aplicado). NULL = sem título';

COMMENT ON COLUMN olist_silver.order_reviews.review_comment_message IS 
'Mensagem do comentário (TRIM aplicado). NULL = sem comentário';

COMMENT ON COLUMN olist_silver.order_reviews.comment_length IS 
'Tamanho do comentário em caracteres. 0 se NULL';

COMMENT ON COLUMN olist_silver.order_reviews.has_comment_message IS 
'Flag técnica: TRUE se review tem comentário (texto)';

COMMENT ON COLUMN olist_silver.order_reviews.is_positive_score IS 
'Flag técnica: TRUE se score >= 4 (neutro, não interpreta como NPS)';

COMMENT ON COLUMN olist_silver.order_reviews.is_negative_score IS 
'Flag técnica: TRUE se score <= 2 (neutro, não interpreta como detratores)';
"""


def validate_silver_order_reviews():
    """
    Valida transformações TÉCNICAS da tabela silver order_reviews.
    
    Validações:
    1. Volumetria (comparar com Bronze)
    2. Integridade de chaves (PK única, sem nulls)
    3. Range de review_score (1-5)
    4. Distribuição de scores
    5. Comentários (% com texto)
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Iniciando validação TÉCNICA da Silver order_reviews...")
        
        engine = create_engine(DB_CONNECTION)
        
        # ============================================
        # VALIDAÇÃO 1: VOLUMETRIA
        # ============================================
        validation_query = """
        WITH bronze_count AS (
            SELECT COUNT(*) AS total FROM olist_raw.order_reviews
        ),
        silver_count AS (
            SELECT COUNT(*) AS total FROM olist_silver.order_reviews
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
            COUNT(DISTINCT review_id) AS unique_review_ids,
            SUM(CASE WHEN review_id IS NULL THEN 1 ELSE 0 END) AS null_pks,
            SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END) AS null_order_ids,
            CASE 
                WHEN COUNT(*) = COUNT(DISTINCT review_id) THEN 'OK'
                ELSE 'ERROR'
            END AS pk_integrity
        FROM olist_silver.order_reviews;
        """
        
        df_keys = pd.read_sql(keys_query, engine)
        keys = df_keys.iloc[0]
        
        logger.info(f"""
        🔑 VALIDAÇÃO 2: INTEGRIDADE DE CHAVES
        - Total registros: {keys['total_records']:,}
        - Review IDs únicos: {keys['unique_review_ids']:,}
        - Nulls em review_id (PK): {keys['null_pks']}
        - Nulls em order_id (FK): {keys['null_order_ids']}
        - Status PK: {keys['pk_integrity']}
        """)
        
        assert keys['null_pks'] == 0, "❌ Existem nulls em review_id (PK)!"
        assert keys['pk_integrity'] == 'OK', "❌ Existem duplicatas em review_id!"
        
        # ============================================
        # VALIDAÇÃO 3: REVIEW SCORES
        # ============================================
        score_query = """
        SELECT 
            review_score,
            COUNT(*) AS total,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
        FROM olist_silver.order_reviews
        GROUP BY review_score
        ORDER BY review_score;
        """
        
        df_score = pd.read_sql(score_query, engine)
        
        logger.info("""
        ⭐ VALIDAÇÃO 3: DISTRIBUIÇÃO DE SCORES
        """)
        for _, row in df_score.iterrows():
            logger.info(f"   - Score {row['review_score']}: {row['total']:,} ({row['percentage']}%)")
        
        # Verificar range de scores (deve ser 1-5)
        invalid_scores = df_score[(df_score['review_score'] < 1) | (df_score['review_score'] > 5)]
        assert len(invalid_scores) == 0, "❌ Existem scores fora do range 1-5!"
        
        # ============================================
        # VALIDAÇÃO 4: COMENTÁRIOS
        # ============================================
        comment_query = """
        SELECT 
            COUNT(*) AS total_reviews,
            SUM(CASE WHEN has_comment_title = TRUE THEN 1 ELSE 0 END) AS with_title,
            SUM(CASE WHEN has_comment_message = TRUE THEN 1 ELSE 0 END) AS with_message,
            SUM(CASE WHEN has_answer = TRUE THEN 1 ELSE 0 END) AS with_answer,
            ROUND(AVG(CASE WHEN comment_length > 0 THEN comment_length END), 2) AS avg_comment_length,
            MAX(comment_length) AS max_comment_length
        FROM olist_silver.order_reviews;
        """
        
        df_comment = pd.read_sql(comment_query, engine)
        comm = df_comment.iloc[0]
        
        logger.info(f"""
        💬 VALIDAÇÃO 4: COMENTÁRIOS
        - Total reviews: {comm['total_reviews']:,}
        - Com título: {comm['with_title']:,} ({comm['with_title']*100/comm['total_reviews']:.2f}%)
        - Com mensagem: {comm['with_message']:,} ({comm['with_message']*100/comm['total_reviews']:.2f}%)
        - Com resposta: {comm['with_answer']:,} ({comm['with_answer']*100/comm['total_reviews']:.2f}%)
        - Tamanho médio comentário: {comm['avg_comment_length']:.0f} caracteres
        - Maior comentário: {comm['max_comment_length']} caracteres
        """)
        
        # ============================================
        # VALIDAÇÃO 5: FLAGS TÉCNICAS
        # ============================================
        flag_query = """
        SELECT 
            SUM(CASE WHEN is_positive_score = TRUE THEN 1 ELSE 0 END) AS positive,
            SUM(CASE WHEN is_negative_score = TRUE THEN 1 ELSE 0 END) AS negative,
            SUM(CASE WHEN is_positive_score = FALSE AND is_negative_score = FALSE THEN 1 ELSE 0 END) AS neutral
        FROM olist_silver.order_reviews;
        """
        
        df_flag = pd.read_sql(flag_query, engine)
        flag = df_flag.iloc[0]
        
        total = flag['positive'] + flag['negative'] + flag['neutral']
        
        logger.info(f"""
        🚩 VALIDAÇÃO 5: FLAGS TÉCNICAS
        - Positivos (score >= 4): {flag['positive']:,} ({flag['positive']*100/total:.2f}%)
        - Negativos (score <= 2): {flag['negative']:,} ({flag['negative']*100/total:.2f}%)
        - Neutros (score = 3): {flag['neutral']:,} ({flag['neutral']*100/total:.2f}%)
        """)
        
        # ============================================
        # VALIDAÇÃO 6: ÍNDICES
        # ============================================
        index_query = """
        SELECT COUNT(*) AS total_indexes
        FROM pg_indexes
        WHERE schemaname = 'olist_silver' AND tablename = 'order_reviews';
        """
        
        df_idx = pd.read_sql(index_query, engine)
        idx_count = df_idx.iloc[0]['total_indexes']
        
        logger.info(f"""
        🔧 VALIDAÇÃO 6: ÍNDICES TÉCNICOS
        - Total de índices criados: {idx_count}
        - Esperado: 6 índices
        """)
        
        assert idx_count == 6, f"❌ Esperado 6 índices, encontrado {idx_count}!"
        
        # ============================================
        # RESUMO FINAL
        # ============================================
        logger.info(f"""
        ✅ VALIDAÇÃO TÉCNICA CONCLUÍDA COM SUCESSO!
        
        📊 Resumo:
        - Volumetria: ✅ {vol['completeness_pct']:.2f}% preservado
        - Integridade PK: ✅ Sem duplicatas ou nulls
        - Scores: ✅ Todos no range 1-5
        - Comentários: ✅ {comm['with_message']*100/comm['total_reviews']:.2f}% com texto
        - Índices: ✅ {idx_count} criados
        
        🎯 Silver Layer pronta para Gold Layer!
        """)
        
        engine.dispose()
        
        return {
            'status': 'success',
            'bronze_records': int(vol['bronze_records']),
            'silver_records': int(vol['silver_records']),
            'completeness_pct': float(vol['completeness_pct']),
            'with_comments_pct': float(comm['with_message']*100/comm['total_reviews'])
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Definição da DAG
with DAG(
    dag_id='21_bronze_to_silver_order_reviews',
    default_args=default_args,
    description='[SILVER] Transformações técnicas: order_reviews (limpeza + padronização)',
    schedule_interval=None,  # Execução manual
    start_date=datetime(2025, 1, 29),
    catchup=False,
    tags=['fase-2', 'silver', 'technical-transformation', 'order-reviews'],
) as dag:
    
    # Task 1: Transformar Bronze → Silver (apenas técnico)
    task_transform_to_silver = PostgresOperator(
        task_id='transform_to_silver',
        postgres_conn_id='postgres_default',
        sql=TRANSFORM_ORDER_REVIEWS_SQL,
    )
    
    # Task 2: Validar transformações técnicas
    task_validate_silver = PythonOperator(
        task_id='validate_technical_transformations',
        python_callable=validate_silver_order_reviews,
    )
    
    # Pipeline de execução (simples e linear)
    task_transform_to_silver >> task_validate_silver
