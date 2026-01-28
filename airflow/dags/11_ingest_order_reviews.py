"""
DAG: Ingestão de Order Reviews no PostgreSQL
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
CSV_PATH = '/opt/airflow/data/raw/olist_order_reviews_dataset.csv'
TABLE_NAME = 'olist_raw.order_reviews'

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
            'review_id',
            'order_id',
            'review_score',
            'review_comment_title',
            'review_comment_message',
            'review_creation_date',
            'review_answer_timestamp'
        ]
        
        missing_cols = set(expected_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"❌ Colunas faltando: {missing_cols}")
        
        logger.info(f"✅ Colunas validadas: {list(df.columns)}")
        
        # Validar valores nulos em PK
        null_pks = df['review_id'].isnull().sum()
        if null_pks > 0:
            raise ValueError(f"❌ {null_pks} PKs nulas encontradas!")
        
        # Validar valores nulos em FK
        null_fks = df['order_id'].isnull().sum()
        if null_fks > 0:
            raise ValueError(f"❌ {null_fks} FKs nulas encontradas!")
        
        logger.info("✅ Sem PKs ou FKs nulas")
        
        # Validar duplicatas em PK
        duplicates = df['review_id'].duplicated().sum()
        if duplicates > 0:
            logger.warning(f"⚠️ {duplicates} duplicatas encontradas - serão removidas")
        
        # Validar range de scores
        invalid_scores = df[(df['review_score'] < 1) | (df['review_score'] > 5)].shape[0]
        if invalid_scores > 0:
            raise ValueError(f"❌ {invalid_scores} scores inválidos (fora de 1-5)")
        
        # Estatísticas
        score_dist = df['review_score'].value_counts().sort_index().to_dict()
        
        logger.info(f"""
        📊 ESTATÍSTICAS DO CSV:
        - Total registros: {len(df)}
        - Reviews únicos: {df['review_id'].nunique()}
        - Orders únicos: {df['order_id'].nunique()}
        - Distribuição de scores: {score_dist}
        - Reviews com título: {df['review_comment_title'].notna().sum()}
        - Reviews com mensagem: {df['review_comment_message'].notna().sum()}
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
        
        # Converter colunas de data
        df['review_creation_date'] = pd.to_datetime(df['review_creation_date'], errors='coerce')
        df['review_answer_timestamp'] = pd.to_datetime(df['review_answer_timestamp'], errors='coerce')
        logger.info("✅ Datas convertidas para datetime")
        
        # Remover duplicatas
        original_len = len(df)
        df = df.drop_duplicates(subset=['review_id'], keep='first')
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
            name='order_reviews',
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
            COUNT(DISTINCT review_id) as unique_reviews,
            COUNT(DISTINCT order_id) as unique_orders,
            AVG(review_score) as avg_score,
            COUNT(CASE WHEN review_comment_title IS NOT NULL THEN 1 END) as reviews_with_title,
            COUNT(CASE WHEN review_comment_message IS NOT NULL THEN 1 END) as reviews_with_message
        FROM olist_raw.order_reviews
        """)
        
        with engine.connect() as conn:
            result = conn.execute(validation_query).fetchone()
        
        logger.info(f"""
        📊 VALIDAÇÃO DE QUALIDADE:
        - Total registros: {result[0]}
        - Reviews únicos: {result[1]}
        - Orders únicos: {result[2]}
        - Score médio: {result[3]:.2f}
        - Reviews com título: {result[4]}
        - Reviews com mensagem: {result[5]}
        """)
        
        # Distribuição de scores
        score_dist_query = text("""
        SELECT 
            review_score,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
        FROM olist_raw.order_reviews
        GROUP BY review_score
        ORDER BY review_score
        """)
        
        with engine.connect() as conn:
            scores = conn.execute(score_dist_query).fetchall()
        
        logger.info("📊 DISTRIBUIÇÃO DE SCORES:")
        for score in scores:
            logger.info(f"  Score {score[0]}: {score[1]} reviews ({score[2]}%)")
        
        # Validar integridade referencial
        fk_validation = text("""
        SELECT COUNT(*) 
        FROM olist_raw.order_reviews r
        LEFT JOIN olist_raw.orders o ON r.order_id = o.order_id
        WHERE o.order_id IS NULL
        """)
        
        with engine.connect() as conn:
            orphan_count = conn.execute(fk_validation).scalar()
        
        if orphan_count > 0:
            raise ValueError(f"❌ {orphan_count} reviews com order_id inválido!")
        
        logger.info("✅ FK order_id validada!")
        logger.info("✅ Validação de qualidade aprovada!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id='11_ingest_order_reviews',
    default_args=default_args,
    description='Ingestão de order_reviews (CSV → PostgreSQL)',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['fase-1', 'ingestion', 'postgresql', 'order_reviews'],
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
