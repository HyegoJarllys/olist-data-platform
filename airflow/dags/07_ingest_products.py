"""
DAG: Ingestão de Products no PostgreSQL
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
CSV_PATH = '/opt/airflow/data/raw/olist_products_dataset.csv'
TABLE_NAME = 'olist_raw.products'

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
        
        # Validar colunas esperadas (com typo original do CSV)
        expected_cols = [
            'product_id',
            'product_category_name',
            'product_name_lenght',  # typo original
            'product_description_lenght',  # typo original
            'product_photos_qty',
            'product_weight_g',
            'product_length_cm',
            'product_height_cm',
            'product_width_cm'
        ]
        
        missing_cols = set(expected_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"❌ Colunas faltando: {missing_cols}")
        
        logger.info(f"✅ Colunas validadas: {list(df.columns)}")
        
        # Validar valores nulos em PK
        null_pks = df['product_id'].isnull().sum()
        if null_pks > 0:
            raise ValueError(f"❌ {null_pks} PKs nulas encontradas!")
        
        logger.info("✅ Sem PKs nulas")
        
        # Validar duplicatas em PK
        duplicates = df['product_id'].duplicated().sum()
        if duplicates > 0:
            logger.warning(f"⚠️ {duplicates} duplicatas encontradas - serão removidas")
        
        # Estatísticas
        logger.info(f"""
        📊 ESTATÍSTICAS DO CSV:
        - Total registros: {len(df)}
        - Products únicos: {df['product_id'].nunique()}
        - Categorias únicas: {df['product_category_name'].nunique()}
        - Produtos sem categoria: {df['product_category_name'].isnull().sum()}
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
        
        # Remover duplicatas (manter primeira ocorrência)
        original_len = len(df)
        df = df.drop_duplicates(subset=['product_id'], keep='first')
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
            name='products',
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
            COUNT(DISTINCT product_id) as unique_products,
            COUNT(DISTINCT product_category_name) as unique_categories,
            COUNT(CASE WHEN product_id IS NULL THEN 1 END) as null_pks,
            COUNT(CASE WHEN product_category_name IS NULL THEN 1 END) as null_categories,
            COUNT(CASE WHEN product_weight_g IS NULL THEN 1 END) as null_weights,
            AVG(product_weight_g) as avg_weight,
            MAX(product_weight_g) as max_weight
        FROM olist_raw.products
        """)
        
        with engine.connect() as conn:
            result = conn.execute(validation_query).fetchone()
        
        logger.info(f"""
        📊 VALIDAÇÃO DE QUALIDADE:
        - Total registros: {result[0]}
        - Products únicos: {result[1]}
        - Categorias únicas: {result[2]}
        - PKs nulas: {result[3]}
        - Categorias nulas: {result[4]}
        - Pesos nulos: {result[5]}
        - Peso médio: {result[6]:.2f}g
        - Peso máximo: {result[7]}g
        """)
        
        # Validações críticas
        if result[3] > 0:
            raise ValueError(f"❌ {result[3]} PKs nulas encontradas!")
        
        if result[0] != result[1]:
            logger.warning(f"⚠️ Total ({result[0]}) != Únicos ({result[1]})")
        
        logger.info("✅ Validação de qualidade aprovada!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id='07_ingest_products',
    default_args=default_args,
    description='Ingestão de products (CSV → PostgreSQL)',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['fase-1', 'ingestion', 'postgresql', 'products'],
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
