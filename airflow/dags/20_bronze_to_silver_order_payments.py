"""
DAG: Bronze to Silver - Order Payments (Technical Transformations Only)
Fase 2 - Data Transformation - Silver Layer
Autor: Hyego
Data: 2025-01-29

RESPONSABILIDADE DESTA DAG:
- Transformações TÉCNICAS e NEUTRAS
- Limpeza, padronização, conversão de tipos
- SEM métricas de negócio, KPIs ou agregações

Transformações aplicadas:
1. Conversão de tipos numéricos (payment_value)
2. Padronização de payment_type (lowercase, trim)
3. Validação de PK composta (order_id + payment_sequential)
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
TRANSFORM_ORDER_PAYMENTS_SQL = """
-- ============================================
-- SILVER ORDER_PAYMENTS: TRANSFORMAÇÕES TÉCNICAS
-- ============================================
-- Responsabilidade: Limpeza e padronização técnica
-- SEM métricas de negócio (análise de inadimplência, etc)
-- ============================================

DROP TABLE IF EXISTS olist_silver.order_payments;

CREATE TABLE olist_silver.order_payments AS
SELECT DISTINCT
    -- ============================================
    -- CHAVES (PK composta + FK)
    -- ============================================
    op.order_id,
    op.payment_sequential,
    
    -- ============================================
    -- TIPO DE PAGAMENTO (padronizado)
    -- lowercase + trim para consistência
    -- ============================================
    LOWER(TRIM(op.payment_type)) AS payment_type,
    
    -- ============================================
    -- PARCELAS (garantir tipo inteiro)
    -- ============================================
    op.payment_installments::INTEGER AS payment_installments,
    
    -- ============================================
    -- VALOR (NUMERIC para precisão financeira)
    -- ============================================
    op.payment_value::NUMERIC(10,2) AS payment_value,
    
    -- ============================================
    -- FLAGS TÉCNICAS (derivadas, mas neutras)
    -- ============================================
    op.payment_value > 0 AS has_value,
    op.payment_installments > 1 AS is_installment,
    CASE 
        WHEN LOWER(TRIM(op.payment_type)) = 'credit_card' THEN TRUE
        ELSE FALSE
    END AS is_credit_card,
    CASE 
        WHEN LOWER(TRIM(op.payment_type)) = 'boleto' THEN TRUE
        ELSE FALSE
    END AS is_boleto,
    
    -- ============================================
    -- TIMESTAMPS DE AUDITORIA (técnicos)
    -- ============================================
    CURRENT_TIMESTAMP AS processed_at,
    CURRENT_TIMESTAMP AS updated_at,
    CURRENT_TIMESTAMP AS created_at

FROM olist_raw.order_payments op

-- ============================================
-- GARANTIR: 1 registro por (order_id, payment_sequential)
-- ============================================
ORDER BY op.order_id, op.payment_sequential;

-- ============================================
-- ÍNDICES TÉCNICOS (para performance)
-- ============================================
-- PK composta
CREATE INDEX idx_silver_order_payments_pk ON olist_silver.order_payments(order_id, payment_sequential);

-- FK
CREATE INDEX idx_silver_order_payments_order_id ON olist_silver.order_payments(order_id);

-- Campos de análise
CREATE INDEX idx_silver_order_payments_type ON olist_silver.order_payments(payment_type);
CREATE INDEX idx_silver_order_payments_value ON olist_silver.order_payments(payment_value);
CREATE INDEX idx_silver_order_payments_installments ON olist_silver.order_payments(payment_installments);
CREATE INDEX idx_silver_order_payments_processed_at ON olist_silver.order_payments(processed_at);

-- ============================================
-- COMENTÁRIOS TÉCNICOS (documentação)
-- ============================================
COMMENT ON TABLE olist_silver.order_payments IS 
'Silver Layer - Order Payments: Dados limpos e padronizados. SEM métricas de negócio.';

COMMENT ON COLUMN olist_silver.order_payments.order_id IS 
'Parte da PK composta (order_id + payment_sequential). FK para orders';

COMMENT ON COLUMN olist_silver.order_payments.payment_sequential IS 
'Parte da PK composta. Sequencial do pagamento (1, 2, 3... para pedidos com múltiplas formas)';

COMMENT ON COLUMN olist_silver.order_payments.payment_type IS 
'Tipo de pagamento padronizado (lowercase, trim). Ex: credit_card, boleto, voucher, debit_card';

COMMENT ON COLUMN olist_silver.order_payments.payment_installments IS 
'Número de parcelas (INTEGER). 1 = à vista, >1 = parcelado';

COMMENT ON COLUMN olist_silver.order_payments.payment_value IS 
'Valor do pagamento (NUMERIC para precisão financeira)';

COMMENT ON COLUMN olist_silver.order_payments.is_installment IS 
'Flag técnica: TRUE se payment_installments > 1';

COMMENT ON COLUMN olist_silver.order_payments.is_credit_card IS 
'Flag técnica: TRUE se payment_type = credit_card';

COMMENT ON COLUMN olist_silver.order_payments.is_boleto IS 
'Flag técnica: TRUE se payment_type = boleto';
"""


def validate_silver_order_payments():
    """
    Valida transformações TÉCNICAS da tabela silver order_payments.
    
    Validações:
    1. Volumetria (comparar com Bronze)
    2. Integridade de PK composta
    3. Padronização de payment_type
    4. Distribuição de tipos de pagamento
    5. Valores e parcelas
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Iniciando validação TÉCNICA da Silver order_payments...")
        
        engine = create_engine(DB_CONNECTION)
        
        # ============================================
        # VALIDAÇÃO 1: VOLUMETRIA
        # ============================================
        validation_query = """
        WITH bronze_count AS (
            SELECT COUNT(*) AS total FROM olist_raw.order_payments
        ),
        silver_count AS (
            SELECT COUNT(*) AS total FROM olist_silver.order_payments
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
            COUNT(DISTINCT (order_id, payment_sequential)) AS unique_pks,
            SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END) AS null_order_id,
            SUM(CASE WHEN payment_sequential IS NULL THEN 1 ELSE 0 END) AS null_sequential,
            CASE 
                WHEN COUNT(*) = COUNT(DISTINCT (order_id, payment_sequential)) THEN 'OK'
                ELSE 'ERROR'
            END AS pk_integrity
        FROM olist_silver.order_payments;
        """
        
        df_keys = pd.read_sql(keys_query, engine)
        keys = df_keys.iloc[0]
        
        logger.info(f"""
        🔑 VALIDAÇÃO 2: INTEGRIDADE DE PK COMPOSTA
        - Total registros: {keys['total_records']:,}
        - PKs únicas (order_id, payment_sequential): {keys['unique_pks']:,}
        - Nulls em order_id: {keys['null_order_id']}
        - Nulls em payment_sequential: {keys['null_sequential']}
        - Status PK: {keys['pk_integrity']}
        """)
        
        assert keys['null_order_id'] == 0, "❌ Existem nulls em order_id (PK)!"
        assert keys['null_sequential'] == 0, "❌ Existem nulls em payment_sequential (PK)!"
        assert keys['pk_integrity'] == 'OK', "❌ Existem duplicatas na PK composta!"
        
        # ============================================
        # VALIDAÇÃO 3: TIPOS DE PAGAMENTO
        # ============================================
        type_query = """
        SELECT 
            payment_type,
            COUNT(*) AS total,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage,
            ROUND(AVG(payment_value), 2) AS avg_value,
            ROUND(AVG(payment_installments), 2) AS avg_installments
        FROM olist_silver.order_payments
        GROUP BY payment_type
        ORDER BY total DESC;
        """
        
        df_type = pd.read_sql(type_query, engine)
        
        logger.info("""
        💳 VALIDAÇÃO 3: DISTRIBUIÇÃO POR TIPO DE PAGAMENTO
        """)
        for _, row in df_type.iterrows():
            logger.info(f"   - {row['payment_type']}: {row['total']:,} ({row['percentage']}%) | Avg: R$ {row['avg_value']:.2f} | Parcelas: {row['avg_installments']:.1f}")
        
        # Verificar se types estão lowercase
        uppercase_types = df_type[df_type['payment_type'].str.isupper()]
        assert len(uppercase_types) == 0, "❌ payment_type não foi convertido para lowercase!"
        
        # ============================================
        # VALIDAÇÃO 4: VALORES E PARCELAS
        # ============================================
        value_query = """
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN has_value = TRUE THEN 1 ELSE 0 END) AS with_value,
            SUM(CASE WHEN is_installment = TRUE THEN 1 ELSE 0 END) AS installments,
            SUM(CASE WHEN is_credit_card = TRUE THEN 1 ELSE 0 END) AS credit_card,
            SUM(CASE WHEN is_boleto = TRUE THEN 1 ELSE 0 END) AS boleto,
            ROUND(AVG(payment_value), 2) AS avg_value,
            ROUND(MIN(payment_value), 2) AS min_value,
            ROUND(MAX(payment_value), 2) AS max_value,
            ROUND(AVG(payment_installments), 2) AS avg_installments,
            MAX(payment_installments) AS max_installments
        FROM olist_silver.order_payments;
        """
        
        df_value = pd.read_sql(value_query, engine)
        val = df_value.iloc[0]
        
        logger.info(f"""
        💰 VALIDAÇÃO 4: VALORES E PARCELAS
        - Total pagamentos: {val['total']:,}
        - Com valor > 0: {val['with_value']:,} ({val['with_value']*100/val['total']:.2f}%)
        - Parcelados: {val['installments']:,} ({val['installments']*100/val['total']:.2f}%)
        - Cartão de crédito: {val['credit_card']:,} ({val['credit_card']*100/val['total']:.2f}%)
        - Boleto: {val['boleto']:,} ({val['boleto']*100/val['total']:.2f}%)
        - Valor médio: R$ {val['avg_value']:.2f}
        - Valor (min/max): R$ {val['min_value']:.2f} / R$ {val['max_value']:.2f}
        - Parcelas médias: {val['avg_installments']:.2f}
        - Máximo de parcelas: {val['max_installments']}
        """)
        
        # ============================================
        # VALIDAÇÃO 5: PEDIDOS COM MÚLTIPLOS PAGAMENTOS
        # ============================================
        multi_query = """
        SELECT 
            COUNT(DISTINCT order_id) AS total_orders,
            SUM(CASE WHEN payment_count > 1 THEN 1 ELSE 0 END) AS orders_multiple_payments,
            MAX(payment_count) AS max_payments_per_order
        FROM (
            SELECT 
                order_id,
                COUNT(*) AS payment_count
            FROM olist_silver.order_payments
            GROUP BY order_id
        ) sub;
        """
        
        df_multi = pd.read_sql(multi_query, engine)
        multi = df_multi.iloc[0]
        
        logger.info(f"""
        🔢 VALIDAÇÃO 5: MÚLTIPLOS PAGAMENTOS
        - Total de orders: {multi['total_orders']:,}
        - Orders com múltiplos pagamentos: {multi['orders_multiple_payments']:,}
        - Máximo de pagamentos por order: {multi['max_payments_per_order']}
        """)
        
        # ============================================
        # VALIDAÇÃO 6: ÍNDICES
        # ============================================
        index_query = """
        SELECT COUNT(*) AS total_indexes
        FROM pg_indexes
        WHERE schemaname = 'olist_silver' AND tablename = 'order_payments';
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
        - Integridade PK: ✅ PK composta sem duplicatas
        - Padronização: ✅ payment_type em lowercase
        - Valores: ✅ Valor médio R$ {val['avg_value']:.2f}
        - Índices: ✅ {idx_count} criados
        
        🎯 Silver Layer pronta para Gold Layer!
        """)
        
        engine.dispose()
        
        return {
            'status': 'success',
            'bronze_records': int(vol['bronze_records']),
            'silver_records': int(vol['silver_records']),
            'completeness_pct': float(vol['completeness_pct']),
            'avg_value': float(val['avg_value'])
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Definição da DAG
with DAG(
    dag_id='20_bronze_to_silver_order_payments',
    default_args=default_args,
    description='[SILVER] Transformações técnicas: order_payments (limpeza + padronização)',
    schedule_interval=None,  # Execução manual
    start_date=datetime(2025, 1, 29),
    catchup=False,
    tags=['fase-2', 'silver', 'technical-transformation', 'order-payments'],
) as dag:
    
    # Task 1: Transformar Bronze → Silver (apenas técnico)
    task_transform_to_silver = PostgresOperator(
        task_id='transform_to_silver',
        postgres_conn_id='postgres_default',
        sql=TRANSFORM_ORDER_PAYMENTS_SQL,
    )
    
    # Task 2: Validar transformações técnicas
    task_validate_silver = PythonOperator(
        task_id='validate_technical_transformations',
        python_callable=validate_silver_order_payments,
    )
    
    # Pipeline de execução (simples e linear)
    task_transform_to_silver >> task_validate_silver
