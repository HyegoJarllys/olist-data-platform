"""
DAG: Ingestão de Order Payments no PostgreSQL
Fase 1 - Data Ingestion
Autor: Hyego
Data: 2025-01-28
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import logging
from sqlalchemy import create_engine, text

# Configurações
CSV_PATH = '/opt/airflow/data/raw/olist_order_payments_dataset.csv'
TABLE_NAME = 'olist_raw.order_payments'

# Conexão direta
DB_CONNECTION = 'postgresql://airflow:airflow@postgres:5432/airflow'

default_args = {
    'owner': 'hyego',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def validate_csv():
    """Valida estrutura e qualidade do CSV"""
    logger = logging.getLogger(__name__)
    
    try:
        # Ler CSV
        df = pd.read_csv(CSV_PATH)
        logger.info(f"✅ CSV carregado: {len(df)} registros")
        
        # Validar colunas esperadas
        expected_cols = [
            'order_id',
            'payment_sequential',
            'payment_type',
            'payment_installments',
            'payment_value'
        ]
        
        missing_cols = set(expected_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"❌ Colunas faltando: {missing_cols}")
        
        logger.info(f"✅ Colunas validadas: {list(df.columns)}")
        
        # Validar valores nulos na PK composta
        null_order_ids = df['order_id'].isnull().sum()
        null_sequential = df['payment_sequential'].isnull().sum()
        
        if null_order_ids > 0 or null_sequential > 0:
            raise ValueError(f"❌ PKs nulas: order_id={null_order_ids}, payment_sequential={null_sequential}")
        
        logger.info("✅ Sem PKs nulas")
        
        # Validar duplicatas na PK composta
        duplicates = df.duplicated(subset=['order_id', 'payment_sequential']).sum()
        if duplicates > 0:
            logger.warning(f"⚠️ {duplicates} duplicatas encontradas - serão removidas")
        
        # Estatísticas
        payment_types = df['payment_type'].value_counts().to_dict()
        
        logger.info(f"""
        📊 ESTATÍSTICAS DO CSV:
        - Total registros: {len(df)}
        - Orders únicos: {df['order_id'].nunique()}
        - Tipos de pagamento: {payment_types}
        - Valor médio: R$ {df['payment_value'].mean():.2f}
        - Valor total: R$ {df['payment_value'].sum():.2f}
        - Parcelas médias: {df['payment_installments'].mean():.2f}
        - Valores nulos por coluna:
        {df.isnull().sum().to_dict()}
        """)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        raise


def load_to_postgres():
    """Carrega dados do CSV para PostgreSQL"""
    logger = logging.getLogger(__name__)
    
    try:
        # Ler CSV
        df = pd.read_csv(CSV_PATH)
        logger.info(f"📂 CSV carregado: {len(df)} registros")
        
        # Remover duplicatas (PK composta)
        original_len = len(df)
        df = df.drop_duplicates(subset=['order_id', 'payment_sequential'], keep='first')
        removed = original_len - len(df)
        if removed > 0:
            logger.warning(f"🗑️ {removed} duplicatas removidas")
        
        # Conectar ao PostgreSQL
        logger.info("🔌 Conectando ao PostgreSQL...")
        engine = create_engine(DB_CONNECTION)
        
        # Truncar tabela
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME} CASCADE"))
            logger.info(f"🗑️ Tabela {TABLE_NAME} truncada")
        
        # Inserir dados
        logger.info(f"📝 Inserindo {len(df)} registros...")
        df.to_sql(
            name='order_payments',
            con=engine,
            schema='olist_raw',
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )
        
        logger.info(f"✅ {len(df)} registros inseridos em {TABLE_NAME}")
        
        # Validar contagem
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}"))
            count = result.scalar()
            logger.info(f"✅ Validação: {count} registros na tabela")
            
            if count != len(df):
                raise ValueError(f"❌ Contagem divergente! CSV: {len(df)}, DB: {count}")
        
        logger.info("🎉 Ingestão concluída com sucesso!")
        return count
        
    except Exception as e:
        logger.error(f"❌ Erro na ingestão: {str(e)}")
        raise


def validate_data_quality():
    """Valida qualidade dos dados inseridos"""
    logger = logging.getLogger(__name__)
    
    try:
        # Conectar ao PostgreSQL
        engine = create_engine(DB_CONNECTION)
        
        # Query de validação
        validation_query = text("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT order_id) as unique_orders,
            COUNT(DISTINCT payment_type) as unique_payment_types,
            AVG(payment_value) as avg_payment,
            SUM(payment_value) as total_payment,
            AVG(payment_installments) as avg_installments,
            MAX(payment_installments) as max_installments
        FROM olist_raw.order_payments
        """)
        
        with engine.connect() as conn:
            result = conn.execute(validation_query).fetchone()
        
        logger.info(f"""
        📊 VALIDAÇÃO DE QUALIDADE:
        - Total registros: {result[0]}
        - Orders únicos: {result[1]}
        - Tipos de pagamento: {result[2]}
        - Valor médio: R$ {result[3]:.2f}
        - Valor total: R$ {result[4]:.2f}
        - Parcelas médias: {result[5]:.2f}
        - Parcelas máximas: {result[6]}
        """)
        
        # Validar integridade referencial
        fk_validation = text("""
        SELECT COUNT(*) 
        FROM olist_raw.order_payments op
        LEFT JOIN olist_raw.orders o ON op.order_id = o.order_id
        WHERE o.order_id IS NULL
        """)
        
        with engine.connect() as conn:
            orphan_count = conn.execute(fk_validation).scalar()
        
        if orphan_count > 0:
            raise ValueError(f"❌ {orphan_count} payments com order_id inválido!")
        
        logger.info("✅ FK order_id validada!")
        
        # Distribuição de tipos de pagamento
        payment_types_query = text("""
        SELECT 
            payment_type,
            COUNT(*) as count,
            SUM(payment_value) as total_value
        FROM olist_raw.order_payments
        GROUP BY payment_type
        ORDER BY count DESC
        """)
        
        with engine.connect() as conn:
            payment_types = conn.execute(payment_types_query).fetchall()
        
        logger.info("📊 DISTRIBUIÇÃO DE PAGAMENTOS:")
        for pt in payment_types:
            logger.info(f"  {pt[0]}: {pt[1]} pagamentos (R$ {pt[2]:.2f})")
        
        logger.info("✅ Validação de qualidade aprovada!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id='10_ingest_order_payments',
    default_args=default_args,
    description='Ingestão de order_payments (CSV → PostgreSQL)',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['fase-1', 'ingestion', 'postgresql', 'order_payments'],
) as dag:
    
    # Task 1: Validar CSV
    task_validate_csv = PythonOperator(
        task_id='validate_csv',
        python_callable=validate_csv,
    )
    
    # Task 2: Carregar dados
    task_load_data = PythonOperator(
        task_id='load_to_postgres',
        python_callable=load_to_postgres,
    )
    
    # Task 3: Validar qualidade
    task_validate_quality = PythonOperator(
        task_id='validate_data_quality',
        python_callable=validate_data_quality,
    )
    
    # Pipeline
    task_validate_csv >> task_load_data >> task_validate_quality
