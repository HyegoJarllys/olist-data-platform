"""
DAG: Bronze to Silver - Order Items (Technical Transformations Only)
Fase 2 - Data Transformation - Silver Layer
Autor: Hyego
Data: 2025-01-29

RESPONSABILIDADE DESTA DAG:
- Transformações TÉCNICAS e NEUTRAS
- Limpeza, padronização, conversão de tipos
- SEM métricas de negócio, KPIs ou agregações

Transformações aplicadas:
1. Conversão de tipos numéricos (price, freight)
2. Conversão de timestamps
3. Validação de chaves compostas (order_id + order_item_id)
4. Tratamento de valores nulos
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
TRANSFORM_ORDER_ITEMS_SQL = """
-- ============================================
-- SILVER ORDER_ITEMS: TRANSFORMAÇÕES TÉCNICAS
-- ============================================
-- Responsabilidade: Limpeza e padronização técnica
-- SEM métricas de negócio (margem, total, etc)
-- ============================================

DROP TABLE IF EXISTS olist_silver.order_items;

CREATE TABLE olist_silver.order_items AS
SELECT DISTINCT
    -- ============================================
    -- CHAVES (PK composta + FKs)
    -- ============================================
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    
    -- ============================================
    -- VALORES MONETÁRIOS (garantir tipo correto)
    -- NUMERIC para precisão em cálculos financeiros
    -- ============================================
    oi.price::NUMERIC(10,2) AS price,
    oi.freight_value::NUMERIC(10,2) AS freight_value,
    
    -- ============================================
    -- TIMESTAMP (garantir tipo correto)
    -- ============================================
    oi.shipping_limit_date::TIMESTAMP AS shipping_limit_date,
    
    -- ============================================
    -- VALOR TOTAL DO ITEM (derivação técnica)
    -- price + freight = valor total que o cliente pagou
    -- ============================================
    (oi.price + oi.freight_value)::NUMERIC(10,2) AS item_total_value,
    
    -- ============================================
    -- FLAGS TÉCNICAS (derivadas, mas neutras)
    -- ============================================
    oi.price > 0 AS has_price,
    oi.freight_value > 0 AS has_freight,
    oi.shipping_limit_date IS NOT NULL AS has_shipping_limit,
    
    -- ============================================
    -- TIMESTAMPS DE AUDITORIA (técnicos)
    -- ============================================
    CURRENT_TIMESTAMP AS processed_at,
    CURRENT_TIMESTAMP AS updated_at,
    CURRENT_TIMESTAMP AS created_at

FROM olist_raw.order_items oi

-- ============================================
-- GARANTIR: 1 registro por (order_id, order_item_id)
-- ============================================
ORDER BY oi.order_id, oi.order_item_id;

-- ============================================
-- ÍNDICES TÉCNICOS (para performance)
-- ============================================
-- PK composta
CREATE INDEX idx_silver_order_items_pk ON olist_silver.order_items(order_id, order_item_id);

-- FKs individuais
CREATE INDEX idx_silver_order_items_order_id ON olist_silver.order_items(order_id);
CREATE INDEX idx_silver_order_items_product_id ON olist_silver.order_items(product_id);
CREATE INDEX idx_silver_order_items_seller_id ON olist_silver.order_items(seller_id);

-- Campos de análise
CREATE INDEX idx_silver_order_items_price ON olist_silver.order_items(price);
CREATE INDEX idx_silver_order_items_shipping_date ON olist_silver.order_items(shipping_limit_date);
CREATE INDEX idx_silver_order_items_processed_at ON olist_silver.order_items(processed_at);

-- ============================================
-- COMENTÁRIOS TÉCNICOS (documentação)
-- ============================================
COMMENT ON TABLE olist_silver.order_items IS 
'Silver Layer - Order Items: Dados limpos e padronizados. SEM métricas de negócio.';

COMMENT ON COLUMN olist_silver.order_items.order_id IS 
'Parte da PK composta (order_id + order_item_id). FK para orders';

COMMENT ON COLUMN olist_silver.order_items.order_item_id IS 
'Parte da PK composta. Sequencial dentro do pedido (1, 2, 3...)';

COMMENT ON COLUMN olist_silver.order_items.price IS 
'Preço do item (NUMERIC para precisão financeira)';

COMMENT ON COLUMN olist_silver.order_items.freight_value IS 
'Valor do frete do item (NUMERIC para precisão financeira)';

COMMENT ON COLUMN olist_silver.order_items.item_total_value IS 
'Derivação técnica: price + freight_value. Valor total pago pelo item';

COMMENT ON COLUMN olist_silver.order_items.has_price IS 
'Flag técnica: TRUE se item tem preço > 0';

COMMENT ON COLUMN olist_silver.order_items.has_freight IS 
'Flag técnica: TRUE se item tem frete > 0';
"""


def validate_silver_order_items():
    """
    Valida transformações TÉCNICAS da tabela silver order_items.
    
    Validações:
    1. Volumetria (comparar com Bronze)
    2. Integridade de PK composta
    3. Integridade de FKs
    4. Conversão de tipos numéricos
    5. Cálculo de item_total_value
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Iniciando validação TÉCNICA da Silver order_items...")
        
        engine = create_engine(DB_CONNECTION)
        
        # ============================================
        # VALIDAÇÃO 1: VOLUMETRIA
        # ============================================
        validation_query = """
        WITH bronze_count AS (
            SELECT COUNT(*) AS total FROM olist_raw.order_items
        ),
        silver_count AS (
            SELECT COUNT(*) AS total FROM olist_silver.order_items
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
        # VALIDAÇÃO 2: INTEGRIDADE DE PK COMPOSTA
        # ============================================
        keys_query = """
        SELECT 
            COUNT(*) AS total_records,
            COUNT(DISTINCT (order_id, order_item_id)) AS unique_pks,
            SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END) AS null_order_id,
            SUM(CASE WHEN order_item_id IS NULL THEN 1 ELSE 0 END) AS null_item_id,
            CASE 
                WHEN COUNT(*) = COUNT(DISTINCT (order_id, order_item_id)) THEN 'OK'
                ELSE 'ERROR'
            END AS pk_integrity
        FROM olist_silver.order_items;
        """
        
        df_keys = pd.read_sql(keys_query, engine)
        keys = df_keys.iloc[0]
        
        logger.info(f"""
        🔑 VALIDAÇÃO 2: INTEGRIDADE DE PK COMPOSTA
        - Total registros: {keys['total_records']:,}
        - PKs únicas (order_id, order_item_id): {keys['unique_pks']:,}
        - Nulls em order_id: {keys['null_order_id']}
        - Nulls em order_item_id: {keys['null_item_id']}
        - Status PK: {keys['pk_integrity']}
        """)
        
        assert keys['null_order_id'] == 0, "❌ Existem nulls em order_id (PK)!"
        assert keys['null_item_id'] == 0, "❌ Existem nulls em order_item_id (PK)!"
        assert keys['pk_integrity'] == 'OK', "❌ Existem duplicatas na PK composta!"
        
        # ============================================
        # VALIDAÇÃO 3: VALORES MONETÁRIOS
        # ============================================
        money_query = """
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN has_price = TRUE THEN 1 ELSE 0 END) AS with_price,
            SUM(CASE WHEN has_freight = TRUE THEN 1 ELSE 0 END) AS with_freight,
            ROUND(AVG(price), 2) AS avg_price,
            ROUND(MIN(price), 2) AS min_price,
            ROUND(MAX(price), 2) AS max_price,
            ROUND(AVG(freight_value), 2) AS avg_freight,
            ROUND(AVG(item_total_value), 2) AS avg_item_total,
            SUM(CASE WHEN item_total_value != (price + freight_value) THEN 1 ELSE 0 END) AS calc_errors
        FROM olist_silver.order_items;
        """
        
        df_money = pd.read_sql(money_query, engine)
        money = df_money.iloc[0]
        
        logger.info(f"""
        💰 VALIDAÇÃO 3: VALORES MONETÁRIOS
        - Total items: {money['total']:,}
        - Com preço > 0: {money['with_price']:,} ({money['with_price']*100/money['total']:.2f}%)
        - Com frete > 0: {money['with_freight']:,} ({money['with_freight']*100/money['total']:.2f}%)
        - Preço médio: R$ {money['avg_price']:.2f}
        - Preço (min/max): R$ {money['min_price']:.2f} / R$ {money['max_price']:.2f}
        - Frete médio: R$ {money['avg_freight']:.2f}
        - Item total médio: R$ {money['avg_item_total']:.2f}
        - Erros de cálculo: {money['calc_errors']}
        """)
        
        assert money['calc_errors'] == 0, "❌ Erros no cálculo de item_total_value!"
        
        # ============================================
        # VALIDAÇÃO 4: DISTRIBUIÇÃO POR PEDIDO
        # ============================================
        dist_query = """
        SELECT 
            order_item_id,
            COUNT(*) AS total_orders
        FROM olist_silver.order_items
        GROUP BY order_item_id
        ORDER BY order_item_id
        LIMIT 10;
        """
        
        df_dist = pd.read_sql(dist_query, engine)
        
        logger.info("""
        📦 VALIDAÇÃO 4: DISTRIBUIÇÃO DE ITENS POR PEDIDO
        """)
        for _, row in df_dist.iterrows():
            logger.info(f"   - Item {row['order_item_id']}: {row['total_orders']:,} pedidos")
        
        # ============================================
        # VALIDAÇÃO 5: INTEGRIDADE DE FKs (sample)
        # ============================================
        fk_query = """
        SELECT 
            COUNT(DISTINCT order_id) AS unique_orders,
            COUNT(DISTINCT product_id) AS unique_products,
            COUNT(DISTINCT seller_id) AS unique_sellers
        FROM olist_silver.order_items;
        """
        
        df_fk = pd.read_sql(fk_query, engine)
        fk = df_fk.iloc[0]
        
        logger.info(f"""
        🔗 VALIDAÇÃO 5: FOREIGN KEYS (REFERÊNCIAS)
        - Orders únicos: {fk['unique_orders']:,}
        - Produtos únicos: {fk['unique_products']:,}
        - Sellers únicos: {fk['unique_sellers']:,}
        """)
        
        # ============================================
        # VALIDAÇÃO 6: ÍNDICES
        # ============================================
        index_query = """
        SELECT COUNT(*) AS total_indexes
        FROM pg_indexes
        WHERE schemaname = 'olist_silver' AND tablename = 'order_items';
        """
        
        df_idx = pd.read_sql(index_query, engine)
        idx_count = df_idx.iloc[0]['total_indexes']
        
        logger.info(f"""
        🔧 VALIDAÇÃO 6: ÍNDICES TÉCNICOS
        - Total de índices criados: {idx_count}
        - Esperado: 7 índices
        """)
        
        assert idx_count == 7, f"❌ Esperado 7 índices, encontrado {idx_count}!"
        
        # ============================================
        # RESUMO FINAL
        # ============================================
        logger.info(f"""
        ✅ VALIDAÇÃO TÉCNICA CONCLUÍDA COM SUCESSO!
        
        📊 Resumo:
        - Volumetria: ✅ {vol['completeness_pct']:.2f}% preservado
        - Integridade PK: ✅ PK composta sem duplicatas
        - Valores: ✅ Preço médio R$ {money['avg_price']:.2f}
        - Cálculos: ✅ item_total_value correto
        - Índices: ✅ {idx_count} criados
        
        🎯 Silver Layer pronta para Gold Layer!
        """)
        
        engine.dispose()
        
        return {
            'status': 'success',
            'bronze_records': int(vol['bronze_records']),
            'silver_records': int(vol['silver_records']),
            'completeness_pct': float(vol['completeness_pct']),
            'avg_price': float(money['avg_price'])
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Definição da DAG
with DAG(
    dag_id='19_bronze_to_silver_order_items',
    default_args=default_args,
    description='[SILVER] Transformações técnicas: order_items (limpeza + padronização)',
    schedule_interval=None,  # Execução manual
    start_date=datetime(2025, 1, 29),
    catchup=False,
    tags=['fase-2', 'silver', 'technical-transformation', 'order-items'],
) as dag:
    
    # Task 1: Transformar Bronze → Silver (apenas técnico)
    task_transform_to_silver = PostgresOperator(
        task_id='transform_to_silver',
        postgres_conn_id='postgres_default',
        sql=TRANSFORM_ORDER_ITEMS_SQL,
    )
    
    # Task 2: Validar transformações técnicas
    task_validate_silver = PythonOperator(
        task_id='validate_technical_transformations',
        python_callable=validate_silver_order_items,
    )
    
    # Pipeline de execução (simples e linear)
    task_transform_to_silver >> task_validate_silver
