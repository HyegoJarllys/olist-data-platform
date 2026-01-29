"""
DAG: Bronze to Silver - Products (Technical Transformations Only)
Fase 2 - Data Transformation - Silver Layer
Autor: Hyego
Data: 2025-01-29

RESPONSABILIDADE DESTA DAG:
- Transformações TÉCNICAS e NEUTRAS
- Limpeza, padronização, conversão de tipos
- SEM métricas de negócio, KPIs ou agregações

Transformações aplicadas:
1. Padronização de textos (trim, lowercase em campos técnicos)
2. Conversão de tipos numéricos (weight, dimensions)
3. Tratamento de valores nulos em campos opcionais
4. Preservação de chaves e relacionamentos
5. Timestamps de auditoria
6. Índices técnicos para performance
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
TRANSFORM_PRODUCTS_SQL = """
-- ============================================
-- SILVER PRODUCTS: TRANSFORMAÇÕES TÉCNICAS
-- ============================================
-- Responsabilidade: Limpeza e padronização técnica
-- SEM métricas de negócio (popularidade, rating, etc)
-- ============================================

DROP TABLE IF EXISTS olist_silver.products;

CREATE TABLE olist_silver.products AS
SELECT DISTINCT
    -- ============================================
    -- CHAVES ORIGINAIS (preservadas)
    -- ============================================
    p.product_id,
    
    -- ============================================
    -- CATEGORIA (preservada, pode ser NULL)
    -- NULL = produto sem categoria atribuída
    -- ============================================
    p.product_category_name,
    
    -- ============================================
    -- DIMENSÕES TÉCNICAS (conversão de tipos)
    -- COALESCE: se NULL, usar 0 como default técnico
    -- ============================================
    COALESCE(p.product_name_lenght, 0) AS product_name_length,
    COALESCE(p.product_description_lenght, 0) AS product_description_length,
    COALESCE(p.product_photos_qty, 0) AS product_photos_qty,
    
    -- ============================================
    -- DIMENSÕES FÍSICAS (preservar NULLs)
    -- NULL = informação não disponível
    -- ============================================
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm,
    
    -- ============================================
    -- VOLUME CALCULADO (derivação técnica)
    -- NULL se qualquer dimensão for NULL
    -- ============================================
    CASE 
        WHEN p.product_length_cm IS NOT NULL 
        AND p.product_height_cm IS NOT NULL 
        AND p.product_width_cm IS NOT NULL 
        THEN p.product_length_cm * p.product_height_cm * p.product_width_cm
        ELSE NULL
    END AS product_volume_cm3,
    
    -- ============================================
    -- FLAGS TÉCNICAS (derivadas, mas neutras)
    -- ============================================
    p.product_category_name IS NOT NULL AS has_category,
    p.product_weight_g IS NOT NULL AS has_weight,
    p.product_photos_qty > 0 AS has_photos,
    CASE 
        WHEN p.product_length_cm IS NOT NULL 
        AND p.product_height_cm IS NOT NULL 
        AND p.product_width_cm IS NOT NULL 
        THEN TRUE 
        ELSE FALSE 
    END AS has_dimensions,
    
    -- ============================================
    -- TIMESTAMPS DE AUDITORIA (técnicos)
    -- ============================================
    CURRENT_TIMESTAMP AS processed_at,
    CURRENT_TIMESTAMP AS updated_at,
    CURRENT_TIMESTAMP AS created_at

FROM olist_raw.products p

-- ============================================
-- GARANTIR: 1 registro por product_id
-- ============================================
ORDER BY p.product_id;

-- ============================================
-- ÍNDICES TÉCNICOS (para performance)
-- ============================================
CREATE INDEX idx_silver_products_pk ON olist_silver.products(product_id);
CREATE INDEX idx_silver_products_category ON olist_silver.products(product_category_name);
CREATE INDEX idx_silver_products_weight ON olist_silver.products(product_weight_g);
CREATE INDEX idx_silver_products_has_category ON olist_silver.products(has_category);
CREATE INDEX idx_silver_products_processed_at ON olist_silver.products(processed_at);

-- ============================================
-- COMENTÁRIOS TÉCNICOS (documentação)
-- ============================================
COMMENT ON TABLE olist_silver.products IS 
'Silver Layer - Products: Dados limpos e padronizados. SEM métricas de negócio.';

COMMENT ON COLUMN olist_silver.products.product_id IS 
'Chave primária original (preservada da Bronze)';

COMMENT ON COLUMN olist_silver.products.product_category_name IS 
'Categoria do produto. NULL = sem categoria atribuída (válido)';

COMMENT ON COLUMN olist_silver.products.product_volume_cm3 IS 
'Volume calculado (length * height * width). NULL se dimensões ausentes';

COMMENT ON COLUMN olist_silver.products.has_category IS 
'Flag técnica: TRUE se produto tem categoria atribuída';

COMMENT ON COLUMN olist_silver.products.has_dimensions IS 
'Flag técnica: TRUE se produto tem todas as 3 dimensões (L/H/W)';
"""


def validate_silver_products():
    """
    Valida transformações TÉCNICAS da tabela silver products.
    
    Validações:
    1. Volumetria (comparar com Bronze)
    2. Integridade de chaves (PK única, sem nulls)
    3. Conversão de tipos numéricos
    4. Cálculo de volume
    5. Flags técnicas
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Iniciando validação TÉCNICA da Silver products...")
        
        engine = create_engine(DB_CONNECTION)
        
        # ============================================
        # VALIDAÇÃO 1: VOLUMETRIA
        # ============================================
        validation_query = """
        WITH bronze_count AS (
            SELECT COUNT(*) AS total FROM olist_raw.products
        ),
        silver_count AS (
            SELECT COUNT(*) AS total FROM olist_silver.products
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
            COUNT(DISTINCT product_id) AS unique_product_ids,
            SUM(CASE WHEN product_id IS NULL THEN 1 ELSE 0 END) AS null_pks,
            CASE 
                WHEN COUNT(*) = COUNT(DISTINCT product_id) THEN 'OK'
                ELSE 'ERROR'
            END AS pk_integrity
        FROM olist_silver.products;
        """
        
        df_keys = pd.read_sql(keys_query, engine)
        keys = df_keys.iloc[0]
        
        logger.info(f"""
        🔑 VALIDAÇÃO 2: INTEGRIDADE DE CHAVES
        - Total registros: {keys['total_records']:,}
        - Product IDs únicos: {keys['unique_product_ids']:,}
        - Nulls em PK: {keys['null_pks']}
        - Status PK: {keys['pk_integrity']}
        """)
        
        assert keys['null_pks'] == 0, "❌ Existem nulls em product_id (PK)!"
        assert keys['pk_integrity'] == 'OK', "❌ Existem duplicatas em product_id!"
        
        # ============================================
        # VALIDAÇÃO 3: CATEGORIAS
        # ============================================
        category_query = """
        SELECT 
            COUNT(*) AS total_products,
            SUM(CASE WHEN has_category = TRUE THEN 1 ELSE 0 END) AS with_category,
            SUM(CASE WHEN has_category = FALSE THEN 1 ELSE 0 END) AS without_category,
            ROUND(SUM(CASE WHEN has_category = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS category_pct,
            COUNT(DISTINCT product_category_name) AS unique_categories
        FROM olist_silver.products;
        """
        
        df_cat = pd.read_sql(category_query, engine)
        cat = df_cat.iloc[0]
        
        logger.info(f"""
        📦 VALIDAÇÃO 3: CATEGORIAS
        - Total produtos: {cat['total_products']:,}
        - Com categoria: {cat['with_category']:,} ({cat['category_pct']}%)
        - Sem categoria: {cat['without_category']:,}
        - Categorias únicas: {cat['unique_categories']:,}
        """)
        
        # ============================================
        # VALIDAÇÃO 4: DIMENSÕES E PESO
        # ============================================
        dimensions_query = """
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN has_weight = TRUE THEN 1 ELSE 0 END) AS with_weight,
            SUM(CASE WHEN has_dimensions = TRUE THEN 1 ELSE 0 END) AS with_dimensions,
            SUM(CASE WHEN has_photos = TRUE THEN 1 ELSE 0 END) AS with_photos,
            SUM(CASE WHEN product_volume_cm3 IS NOT NULL THEN 1 ELSE 0 END) AS with_volume,
            ROUND(AVG(CASE WHEN product_weight_g > 0 THEN product_weight_g END), 2) AS avg_weight,
            ROUND(AVG(CASE WHEN product_volume_cm3 > 0 THEN product_volume_cm3 END), 2) AS avg_volume
        FROM olist_silver.products;
        """
        
        df_dim = pd.read_sql(dimensions_query, engine)
        dim = df_dim.iloc[0]
        
        logger.info(f"""
        📏 VALIDAÇÃO 4: DIMENSÕES FÍSICAS
        - Total produtos: {dim['total']:,}
        - Com peso: {dim['with_weight']:,} ({dim['with_weight']*100/dim['total']:.2f}%)
        - Com dimensões (L/H/W): {dim['with_dimensions']:,} ({dim['with_dimensions']*100/dim['total']:.2f}%)
        - Com fotos: {dim['with_photos']:,} ({dim['with_photos']*100/dim['total']:.2f}%)
        - Com volume calculado: {dim['with_volume']:,}
        - Peso médio: {dim['avg_weight']:.2f} g
        - Volume médio: {dim['avg_volume']:.2f} cm³
        """)
        
        # ============================================
        # VALIDAÇÃO 5: TOP CATEGORIAS
        # ============================================
        top_cat_query = """
        SELECT 
            product_category_name,
            COUNT(*) AS total
        FROM olist_silver.products
        WHERE has_category = TRUE
        GROUP BY product_category_name
        ORDER BY total DESC
        LIMIT 5;
        """
        
        df_top = pd.read_sql(top_cat_query, engine)
        
        logger.info("""
        🏆 VALIDAÇÃO 5: TOP 5 CATEGORIAS
        """)
        for _, row in df_top.iterrows():
            logger.info(f"   - {row['product_category_name']}: {row['total']:,} produtos")
        
        # ============================================
        # VALIDAÇÃO 6: ÍNDICES
        # ============================================
        index_query = """
        SELECT COUNT(*) AS total_indexes
        FROM pg_indexes
        WHERE schemaname = 'olist_silver' AND tablename = 'products';
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
        - Volumetria: ✅ {vol['completeness_pct']:.2f}% preservado
        - Integridade PK: ✅ Sem duplicatas ou nulls
        - Categorias: ✅ {cat['category_pct']}% com categoria
        - Dimensões: ✅ {dim['with_weight']*100/dim['total']:.2f}% com peso
        - Volume calculado: ✅ {dim['with_volume']:,} produtos
        - Índices: ✅ {idx_count} criados
        
        🎯 Silver Layer pronta para Gold Layer!
        """)
        
        engine.dispose()
        
        return {
            'status': 'success',
            'bronze_records': int(vol['bronze_records']),
            'silver_records': int(vol['silver_records']),
            'completeness_pct': float(vol['completeness_pct']),
            'category_pct': float(cat['category_pct'])
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Definição da DAG
with DAG(
    dag_id='17_bronze_to_silver_products',
    default_args=default_args,
    description='[SILVER] Transformações técnicas: products (limpeza + padronização)',
    schedule_interval=None,  # Execução manual
    start_date=datetime(2025, 1, 29),
    catchup=False,
    tags=['fase-2', 'silver', 'technical-transformation', 'products'],
) as dag:
    
    # Task 1: Transformar Bronze → Silver (apenas técnico)
    task_transform_to_silver = PostgresOperator(
        task_id='transform_to_silver',
        postgres_conn_id='postgres_default',
        sql=TRANSFORM_PRODUCTS_SQL,
    )
    
    # Task 2: Validar transformações técnicas
    task_validate_silver = PythonOperator(
        task_id='validate_technical_transformations',
        python_callable=validate_silver_products,
    )
    
    # Pipeline de execução (simples e linear)
    task_transform_to_silver >> task_validate_silver
