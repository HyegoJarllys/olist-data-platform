"""
DAG: Ingestão de Order Items no PostgreSQL
Fase 1 - Data Ingestion
Autor: Hyego
Data: 2025-01-28
ATENÇÃO: PK Composta + 3 Foreign Keys
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import logging
from sqlalchemy import create_engine, text

# Configurações
CSV_PATH = '/opt/airflow/data/raw/olist_order_items_dataset.csv'
TABLE_NAME = 'olist_raw.order_items'

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
            'order_item_id',
            'product_id',
            'seller_id',
            'shipping_limit_date',
            'price',
            'freight_value'
        ]
        
        missing_cols = set(expected_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"❌ Colunas faltando: {missing_cols}")
        
        logger.info(f"✅ Colunas validadas: {list(df.columns)}")
        
        # Validar valores nulos nas PKs
        null_order_ids = df['order_id'].isnull().sum()
        null_item_ids = df['order_item_id'].isnull().sum()
        
        if null_order_ids > 0 or null_item_ids > 0:
            raise ValueError(f"❌ PKs nulas: order_id={null_order_ids}, order_item_id={null_item_ids}")
        
        logger.info("✅ Sem PKs nulas")
        
        # Validar valores nulos nas FKs
        null_product_ids = df['product_id'].isnull().sum()
        null_seller_ids = df['seller_id'].isnull().sum()
        
        if null_product_ids > 0 or null_seller_ids > 0:
            raise ValueError(f"❌ FKs nulas: product_id={null_product_ids}, seller_id={null_seller_ids}")
        
        logger.info("✅ Sem FKs nulas")
        
        # Validar duplicatas na PK composta
        duplicates = df.duplicated(subset=['order_id', 'order_item_id']).sum()
        if duplicates > 0:
            logger.warning(f"⚠️ {duplicates} duplicatas encontradas - serão removidas")
        
        # Estatísticas
        logger.info(f"""
        📊 ESTATÍSTICAS DO CSV:
        - Total registros: {len(df)}
        - Orders únicos: {df['order_id'].nunique()}
        - Products únicos: {df['product_id'].nunique()}
        - Sellers únicos: {df['seller_id'].nunique()}
        - Preço médio: R$ {df['price'].mean():.2f}
        - Frete médio: R$ {df['freight_value'].mean():.2f}
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
        
        # Converter coluna de data
        df['shipping_limit_date'] = pd.to_datetime(df['shipping_limit_date'], errors='coerce')
        logger.info("✅ Convertido shipping_limit_date para datetime")
        
        # Remover duplicatas (PK composta)
        original_len = len(df)
        df = df.drop_duplicates(subset=['order_id', 'order_item_id'], keep='first')
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
            name='order_items',
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
            COUNT(DISTINCT product_id) as unique_products,
            COUNT(DISTINCT seller_id) as unique_sellers,
            AVG(price) as avg_price,
            AVG(freight_value) as avg_freight,
            MAX(price) as max_price,
            MIN(price) as min_price
        FROM olist_raw.order_items
        """)
        
        with engine.connect() as conn:
            result = conn.execute(validation_query).fetchone()
        
        logger.info(f"""
        📊 VALIDAÇÃO DE QUALIDADE:
        - Total registros: {result[0]}
        - Orders únicos: {result[1]}
        - Products únicos: {result[2]}
        - Sellers únicos: {result[3]}
        - Preço médio: R$ {result[4]:.2f}
        - Frete médio: R$ {result[5]:.2f}
        - Preço máximo: R$ {result[6]:.2f}
        - Preço mínimo: R$ {result[7]:.2f}
        """)
        
        # Validar integridade referencial - FK order_id
        fk_order_validation = text("""
        SELECT COUNT(*) 
        FROM olist_raw.order_items oi
        LEFT JOIN olist_raw.orders o ON oi.order_id = o.order_id
        WHERE o.order_id IS NULL
        """)
        
        with engine.connect() as conn:
            orphan_orders = conn.execute(fk_order_validation).scalar()
        
        if orphan_orders > 0:
            raise ValueError(f"❌ {orphan_orders} order_items com order_id inválido!")
        
        logger.info("✅ FK order_id validada!")
        
        # Validar integridade referencial - FK product_id
        fk_product_validation = text("""
        SELECT COUNT(*) 
        FROM olist_raw.order_items oi
        LEFT JOIN olist_raw.products p ON oi.product_id = p.product_id
        WHERE p.product_id IS NULL
        """)
        
        with engine.connect() as conn:
            orphan_products = conn.execute(fk_product_validation).scalar()
        
        if orphan_products > 0:
            raise ValueError(f"❌ {orphan_products} order_items com product_id inválido!")
        
        logger.info("✅ FK product_id validada!")
        
        # Validar integridade referencial - FK seller_id
        fk_seller_validation = text("""
        SELECT COUNT(*) 
        FROM olist_raw.order_items oi
        LEFT JOIN olist_raw.sellers s ON oi.seller_id = s.seller_id
        WHERE s.seller_id IS NULL
        """)
        
        with engine.connect() as conn:
            orphan_sellers = conn.execute(fk_seller_validation).scalar()
        
        if orphan_sellers > 0:
            raise ValueError(f"❌ {orphan_sellers} order_items com seller_id inválido!")
        
        logger.info("✅ FK seller_id validada!")
        logger.info("✅ Todas as FKs validadas!")
        logger.info("✅ Validação de qualidade aprovada!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id='09_ingest_order_items',
    default_args=default_args,
    description='Ingestão de order_items (CSV → PostgreSQL)',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['fase-1', 'ingestion', 'postgresql', 'order_items'],
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
