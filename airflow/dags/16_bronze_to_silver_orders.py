"""
DAG: Bronze to Silver - Orders (Technical Transformations Only)
Fase 2 - Data Transformation - Silver Layer
Autor: Hyego
Data: 2025-01-29

RESPONSABILIDADE DESTA DAG:
- Transformações TÉCNICAS e NEUTRAS
- Limpeza, padronização, conversão de tipos
- SEM métricas de negócio, KPIs ou agregações

Transformações aplicadas:
1. Conversão de timestamps (strings → TIMESTAMP)
2. Padronização de status (lowercase, trim)
3. Tratamento de valores nulos em datas
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
TRANSFORM_ORDERS_SQL = """
-- ============================================
-- SILVER ORDERS: TRANSFORMAÇÕES TÉCNICAS
-- ============================================
-- Responsabilidade: Limpeza e padronização técnica
-- SEM métricas de negócio (atraso, valor total, etc)
-- ============================================

DROP TABLE IF EXISTS olist_silver.orders;

CREATE TABLE olist_silver.orders AS
SELECT DISTINCT
    -- ============================================
    -- CHAVES ORIGINAIS (preservadas)
    -- ============================================
    o.order_id,
    o.customer_id,
    
    -- ============================================
    -- STATUS PADRONIZADO (lowercase, trim)
    -- ============================================
    LOWER(TRIM(o.order_status)) AS order_status,
    
    -- ============================================
    -- TIMESTAMPS (garantir tipo correto)
    -- ============================================
    o.order_purchase_timestamp::TIMESTAMP AS order_purchase_timestamp,
    o.order_approved_at::TIMESTAMP AS order_approved_at,
    o.order_delivered_carrier_date::TIMESTAMP AS order_delivered_carrier_date,
    o.order_delivered_customer_date::TIMESTAMP AS order_delivered_customer_date,
    o.order_estimated_delivery_date::TIMESTAMP AS order_estimated_delivery_date,
    
    -- ============================================
    -- FLAGS TÉCNICAS (derivadas, mas neutras)
    -- ============================================
    o.order_approved_at IS NOT NULL AS is_approved,
    o.order_delivered_carrier_date IS NOT NULL AS is_shipped,
    o.order_delivered_customer_date IS NOT NULL AS is_delivered,
    
    -- ============================================
    -- TIMESTAMPS DE AUDITORIA (técnicos)
    -- ============================================
    CURRENT_TIMESTAMP AS processed_at,
    CURRENT_TIMESTAMP AS updated_at,
    CURRENT_TIMESTAMP AS created_at

FROM olist_raw.orders o

-- ============================================
-- GARANTIR: 1 registro por order_id
-- ============================================
ORDER BY o.order_id;

-- ============================================
-- ÍNDICES TÉCNICOS (para performance)
-- ============================================
CREATE INDEX idx_silver_orders_pk ON olist_silver.orders(order_id);
CREATE INDEX idx_silver_orders_customer_id ON olist_silver.orders(customer_id);
CREATE INDEX idx_silver_orders_status ON olist_silver.orders(order_status);
CREATE INDEX idx_silver_orders_purchase_date ON olist_silver.orders(order_purchase_timestamp);
CREATE INDEX idx_silver_orders_delivery_date ON olist_silver.orders(order_delivered_customer_date);
CREATE INDEX idx_silver_orders_processed_at ON olist_silver.orders(processed_at);

-- ============================================
-- COMENTÁRIOS TÉCNICOS (documentação)
-- ============================================
COMMENT ON TABLE olist_silver.orders IS 
'Silver Layer - Orders: Dados limpos e padronizados. SEM métricas de negócio.';

COMMENT ON COLUMN olist_silver.orders.order_id IS 
'Chave primária original (preservada da Bronze)';

COMMENT ON COLUMN olist_silver.orders.order_status IS 
'Status do pedido padronizado (lowercase, trim)';

COMMENT ON COLUMN olist_silver.orders.is_approved IS 
'Flag técnica: TRUE se pedido foi aprovado (order_approved_at NOT NULL)';

COMMENT ON COLUMN olist_silver.orders.is_shipped IS 
'Flag técnica: TRUE se pedido foi enviado (order_delivered_carrier_date NOT NULL)';

COMMENT ON COLUMN olist_silver.orders.is_delivered IS 
'Flag técnica: TRUE se pedido foi entregue (order_delivered_customer_date NOT NULL)';
"""


def validate_silver_orders():
    """
    Valida transformações TÉCNICAS da tabela silver orders.
    
    Validações:
    1. Volumetria (comparar com Bronze)
    2. Integridade de chaves (PK única, sem nulls)
    3. Padronização de status
    4. Conversão de timestamps
    5. Flags técnicas
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Iniciando validação TÉCNICA da Silver orders...")
        
        engine = create_engine(DB_CONNECTION)
        
        # ============================================
        # VALIDAÇÃO 1: VOLUMETRIA
        # ============================================
        validation_query = """
        WITH bronze_count AS (
            SELECT COUNT(*) AS total FROM olist_raw.orders
        ),
        silver_count AS (
            SELECT COUNT(*) AS total FROM olist_silver.orders
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
            COUNT(DISTINCT order_id) AS unique_order_ids,
            SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END) AS null_pks,
            SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS null_customer_ids,
            CASE 
                WHEN COUNT(*) = COUNT(DISTINCT order_id) THEN 'OK'
                ELSE 'ERROR'
            END AS pk_integrity
        FROM olist_silver.orders;
        """
        
        df_keys = pd.read_sql(keys_query, engine)
        keys = df_keys.iloc[0]
        
        logger.info(f"""
        🔑 VALIDAÇÃO 2: INTEGRIDADE DE CHAVES
        - Total registros: {keys['total_records']:,}
        - Order IDs únicos: {keys['unique_order_ids']:,}
        - Nulls em PK: {keys['null_pks']}
        - Nulls em customer_id: {keys['null_customer_ids']}
        - Status PK: {keys['pk_integrity']}
        """)
        
        assert keys['null_pks'] == 0, "❌ Existem nulls em order_id (PK)!"
        assert keys['pk_integrity'] == 'OK', "❌ Existem duplicatas em order_id!"
        
        # ============================================
        # VALIDAÇÃO 3: PADRONIZAÇÃO DE STATUS
        # ============================================
        status_query = """
        SELECT 
            order_status,
            COUNT(*) AS total,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
        FROM olist_silver.orders
        GROUP BY order_status
        ORDER BY total DESC;
        """
        
        df_status = pd.read_sql(status_query, engine)
        
        logger.info("""
        📋 VALIDAÇÃO 3: DISTRIBUIÇÃO DE STATUS
        """)
        for _, row in df_status.iterrows():
            logger.info(f"   - {row['order_status']}: {row['total']:,} ({row['percentage']}%)")
        
        # Verificar se status estão lowercase
        uppercase_status = df_status[df_status['order_status'].str.isupper()]
        assert len(uppercase_status) == 0, "❌ Status não foram convertidos para lowercase!"
        
        # ============================================
        # VALIDAÇÃO 4: TIMESTAMPS
        # ============================================
        timestamp_query = """
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN order_purchase_timestamp IS NULL THEN 1 ELSE 0 END) AS null_purchase,
            SUM(CASE WHEN is_approved = TRUE THEN 1 ELSE 0 END) AS approved_count,
            SUM(CASE WHEN is_shipped = TRUE THEN 1 ELSE 0 END) AS shipped_count,
            SUM(CASE WHEN is_delivered = TRUE THEN 1 ELSE 0 END) AS delivered_count,
            ROUND(SUM(CASE WHEN is_delivered = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS delivery_rate
        FROM olist_silver.orders;
        """
        
        df_ts = pd.read_sql(timestamp_query, engine)
        ts = df_ts.iloc[0]
        
        logger.info(f"""
        ⏰ VALIDAÇÃO 4: TIMESTAMPS E FLAGS
        - Total orders: {ts['total']:,}
        - Nulls em purchase_timestamp: {ts['null_purchase']}
        - Aprovados (is_approved): {ts['approved_count']:,}
        - Enviados (is_shipped): {ts['shipped_count']:,}
        - Entregues (is_delivered): {ts['delivered_count']:,}
        - Taxa de entrega: {ts['delivery_rate']}%
        """)
        
        assert ts['null_purchase'] == 0, "❌ Existem nulls em order_purchase_timestamp!"
        
        # ============================================
        # VALIDAÇÃO 5: ÍNDICES
        # ============================================
        index_query = """
        SELECT COUNT(*) AS total_indexes
        FROM pg_indexes
        WHERE schemaname = 'olist_silver' AND tablename = 'orders';
        """
        
        df_idx = pd.read_sql(index_query, engine)
        idx_count = df_idx.iloc[0]['total_indexes']
        
        logger.info(f"""
        🔧 VALIDAÇÃO 5: ÍNDICES TÉCNICOS
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
        - Status: ✅ Padronizados (lowercase)
        - Timestamps: ✅ Convertidos corretamente
        - Flags: ✅ {ts['delivery_rate']}% entregues
        - Índices: ✅ {idx_count} criados
        
        🎯 Silver Layer pronta para Gold Layer!
        """)
        
        engine.dispose()
        
        return {
            'status': 'success',
            'bronze_records': int(vol['bronze_records']),
            'silver_records': int(vol['silver_records']),
            'completeness_pct': float(vol['completeness_pct']),
            'delivery_rate': float(ts['delivery_rate'])
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Definição da DAG
with DAG(
    dag_id='16_bronze_to_silver_orders',
    default_args=default_args,
    description='[SILVER] Transformações técnicas: orders (limpeza + padronização)',
    schedule_interval=None,  # Execução manual
    start_date=datetime(2025, 1, 29),
    catchup=False,
    tags=['fase-2', 'silver', 'technical-transformation', 'orders'],
) as dag:
    
    # Task 1: Transformar Bronze → Silver (apenas técnico)
    task_transform_to_silver = PostgresOperator(
        task_id='transform_to_silver',
        postgres_conn_id='postgres_default',
        sql=TRANSFORM_ORDERS_SQL,
    )
    
    # Task 2: Validar transformações técnicas
    task_validate_silver = PythonOperator(
        task_id='validate_technical_transformations',
        python_callable=validate_silver_orders,
    )
    
    # Pipeline de execução (simples e linear)
    task_transform_to_silver >> task_validate_silver
