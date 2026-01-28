"""
DAG: Ingestão de Orders no PostgreSQL
Fase 1 - Data Ingestion
Autor: Hyego
Data: 2025-01-28
ATENÇÃO: Tabela com FK para customers e múltiplos timestamps
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import logging
from sqlalchemy import create_engine, text

# Configurações
CSV_PATH = '/opt/airflow/data/raw/olist_orders_dataset.csv'
TABLE_NAME = 'olist_raw.orders'

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
            'customer_id',
            'order_status',
            'order_purchase_timestamp',
            'order_approved_at',
            'order_delivered_carrier_date',
            'order_delivered_customer_date',
            'order_estimated_delivery_date'
        ]
        
        missing_cols = set(expected_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"❌ Colunas faltando: {missing_cols}")
        
        logger.info(f"✅ Colunas validadas: {list(df.columns)}")
        
        # Validar valores nulos em PK
        null_pks = df['order_id'].isnull().sum()
        if null_pks > 0:
            raise ValueError(f"❌ {null_pks} PKs nulas encontradas!")
        
        # Validar valores nulos em FK
        null_fks = df['customer_id'].isnull().sum()
        if null_fks > 0:
            raise ValueError(f"❌ {null_fks} FKs nulas encontradas!")
        
        logger.info("✅ Sem PKs ou FKs nulas")
        
        # Validar duplicatas em PK
        duplicates = df['order_id'].duplicated().sum()
        if duplicates > 0:
            logger.warning(f"⚠️ {duplicates} duplicatas encontradas - serão removidas")
        
        # Estatísticas
        logger.info(f"""
        📊 ESTATÍSTICAS DO CSV:
        - Total registros: {len(df)}
        - Orders únicos: {df['order_id'].nunique()}
        - Customers únicos: {df['customer_id'].nunique()}
        - Status únicos: {df['order_status'].unique().tolist()}
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
        
        # Converter colunas de data para datetime
        date_columns = [
            'order_purchase_timestamp',
            'order_approved_at',
            'order_delivered_carrier_date',
            'order_delivered_customer_date',
            'order_estimated_delivery_date'
        ]
        
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            logger.info(f"✅ Convertido {col} para datetime")
        
        # Remover duplicatas (manter primeira ocorrência)
        original_len = len(df)
        df = df.drop_duplicates(subset=['order_id'], keep='first')
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
            name='orders',
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
            COUNT(DISTINCT customer_id) as unique_customers,
            COUNT(CASE WHEN order_id IS NULL THEN 1 END) as null_pks,
            COUNT(CASE WHEN customer_id IS NULL THEN 1 END) as null_fks,
            COUNT(CASE WHEN order_status = 'delivered' THEN 1 END) as delivered_orders,
            COUNT(CASE WHEN order_delivered_customer_date IS NULL THEN 1 END) as null_delivery_dates
        FROM olist_raw.orders
        """)
        
        with engine.connect() as conn:
            result = conn.execute(validation_query).fetchone()
        
        logger.info(f"""
        📊 VALIDAÇÃO DE QUALIDADE:
        - Total registros: {result[0]}
        - Orders únicos: {result[1]}
        - Customers únicos: {result[2]}
        - PKs nulas: {result[3]}
        - FKs nulas: {result[4]}
        - Orders entregues: {result[5]}
        - Datas de entrega nulas: {result[6]}
        """)
        
        # Validações críticas
        if result[3] > 0:
            raise ValueError(f"❌ {result[3]} PKs nulas encontradas!")
        
        if result[4] > 0:
            raise ValueError(f"❌ {result[4]} FKs nulas encontradas!")
        
        if result[0] != result[1]:
            logger.warning(f"⚠️ Total ({result[0]}) != Únicos ({result[1]})")
        
        # Validar integridade referencial
        fk_validation = text("""
        SELECT COUNT(*) 
        FROM olist_raw.orders o
        LEFT JOIN olist_raw.customers c ON o.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
        """)
        
        with engine.connect() as conn:
            orphan_count = conn.execute(fk_validation).scalar()
        
        if orphan_count > 0:
            raise ValueError(f"❌ {orphan_count} orders com customer_id inválido!")
        
        logger.info("✅ Integridade referencial validada!")
        logger.info("✅ Validação de qualidade aprovada!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id='08_ingest_orders',
    default_args=default_args,
    description='Ingestão de orders (CSV → PostgreSQL)',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['fase-1', 'ingestion', 'postgresql', 'orders'],
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
