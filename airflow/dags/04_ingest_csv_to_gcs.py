"""
DAG: Ingestão CSV → GCS (Bronze Layer)
Fase 1 - Data Ingestion
Autor: Hyego
Data: 2025-01-28
Objetivo: Converter CSVs para Parquet e armazenar no GCS
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import logging
import os
from google.cloud import storage

# Configurações
DATA_PATH = '/opt/airflow/data/raw'
BUCKET_NAME = os.getenv('GCS_BUCKET', 'olist-data-lake-hyego')
BRONZE_PREFIX = 'bronze'

# Lista de tabelas para processar
TABLES = [
    'customers',
    'sellers', 
    'products',
    'orders',
    'order_items',
    'order_payments',
    'order_reviews',
    'geolocation'
]

default_args = {
    'owner': 'hyego',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def csv_to_parquet_gcs(table_name: str):
    """
    Converte CSV para Parquet e faz upload para GCS
    
    Args:
        table_name: Nome da tabela (ex: 'customers')
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Construir caminhos
        csv_filename = f'olist_{table_name}_dataset.csv'
        csv_path = os.path.join(DATA_PATH, csv_filename)
        
        # Data para particionamento
        execution_date = datetime.now().strftime('%Y-%m-%d')
        
        # Caminho no GCS
        gcs_path = f'{BRONZE_PREFIX}/{table_name}/{execution_date}.parquet'
        
        logger.info(f"📂 Processando: {table_name}")
        logger.info(f"  CSV: {csv_path}")
        logger.info(f"  GCS: gs://{BUCKET_NAME}/{gcs_path}")
        
        # Verificar se CSV existe
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"❌ CSV não encontrado: {csv_path}")
        
        # Ler CSV
        logger.info(f"📖 Lendo CSV...")
        df = pd.read_csv(csv_path)
        logger.info(f"✅ CSV lido: {len(df):,} registros")
        
        # Adicionar metadados
        df['_loaded_at'] = datetime.now()
        df['_source_file'] = csv_filename
        
        # Converter para Parquet (em memória)
        logger.info("🔄 Convertendo para Parquet...")
        parquet_buffer = df.to_parquet(index=False, engine='pyarrow')
        
        # Calcular tamanho
        size_mb = len(parquet_buffer) / (1024 * 1024)
        logger.info(f"✅ Parquet gerado: {size_mb:.2f} MB")
        
        # Upload para GCS
        logger.info(f"☁️  Fazendo upload para GCS...")
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(gcs_path)
        
        blob.upload_from_string(
            parquet_buffer,
            content_type='application/octet-stream'
        )
        
        logger.info(f"✅ Upload concluído!")
        logger.info(f"🔗 URL: gs://{BUCKET_NAME}/{gcs_path}")
        
        # Estatísticas
        logger.info(f"""
        📊 ESTATÍSTICAS:
        - Tabela: {table_name}
        - Registros: {len(df):,}
        - Colunas: {len(df.columns)}
        - Tamanho Parquet: {size_mb:.2f} MB
        - Path GCS: {gcs_path}
        """)
        
        return {
            'table': table_name,
            'records': len(df),
            'size_mb': size_mb,
            'gcs_path': gcs_path
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar {table_name}: {str(e)}")
        raise


def validate_bronze_layer():
    """Valida que todos os arquivos foram carregados no GCS"""
    logger = logging.getLogger(__name__)
    
    try:
        execution_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info("🔍 Validando Bronze Layer no GCS...")
        
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        
        results = []
        
        for table in TABLES:
            expected_path = f'{BRONZE_PREFIX}/{table}/{execution_date}.parquet'
            blob = bucket.blob(expected_path)
            
            if blob.exists():
                # Obter metadados
                blob.reload()
                size_mb = blob.size / (1024 * 1024)
                
                logger.info(f"✅ {table}: {size_mb:.2f} MB")
                results.append({
                    'table': table,
                    'exists': True,
                    'size_mb': size_mb,
                    'path': expected_path
                })
            else:
                logger.error(f"❌ {table}: arquivo não encontrado!")
                results.append({
                    'table': table,
                    'exists': False
                })
        
        # Verificar se todos existem
        missing = [r['table'] for r in results if not r['exists']]
        
        if missing:
            raise ValueError(f"❌ Arquivos faltando no GCS: {missing}")
        
        # Calcular totais
        total_size = sum(r['size_mb'] for r in results)
        
        logger.info(f"""
        📊 VALIDAÇÃO BRONZE LAYER:
        - Tabelas processadas: {len(results)}/{len(TABLES)}
        - Tamanho total: {total_size:.2f} MB
        - Bucket: {BUCKET_NAME}
        - Prefix: {BRONZE_PREFIX}
        - Data: {execution_date}
        """)
        
        logger.info("🎉 Validação concluída com sucesso!")
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id='04_ingest_csv_to_gcs',
    default_args=default_args,
    description='Ingestão CSV → GCS Bronze Layer (Parquet)',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['fase-1', 'ingestion', 'gcs', 'bronze'],
) as dag:
    
    # Tasks para cada tabela
    upload_tasks = []
    
    for table in TABLES:
        task = PythonOperator(
            task_id=f'upload_{table}',
            python_callable=csv_to_parquet_gcs,
            op_kwargs={'table_name': table},
        )
        upload_tasks.append(task)
    
    # Task de validação
    task_validate = PythonOperator(
        task_id='validate_bronze_layer',
        python_callable=validate_bronze_layer,
    )
    
    # Pipeline: Todas as uploads em paralelo → validação
    upload_tasks >> task_validate
