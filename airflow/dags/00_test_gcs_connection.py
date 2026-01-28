"""
DAG: Teste de Conexão com Google Cloud Storage
Autor: Hyego
Data: 2025-01-28
Objetivo: Validar credenciais e acesso ao bucket GCS
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging
import os

default_args = {
    'owner': 'hyego',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}


def test_gcp_credentials():
    """Testa se as credenciais GCP estão configuradas"""
    logger = logging.getLogger(__name__)
    
    try:
        # Verificar variáveis de ambiente
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        project_id = os.getenv('GCP_PROJECT_ID')
        bucket_name = os.getenv('GCS_BUCKET')
        
        logger.info(f"📋 Credenciais path: {creds_path}")
        logger.info(f"📋 Project ID: {project_id}")
        logger.info(f"📋 Bucket name: {bucket_name}")
        
        if not creds_path:
            raise ValueError("❌ GOOGLE_APPLICATION_CREDENTIALS não configurado!")
        
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"❌ Arquivo de credenciais não encontrado: {creds_path}")
        
        logger.info("✅ Variáveis de ambiente configuradas corretamente")
        logger.info(f"✅ Arquivo de credenciais existe: {creds_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar credenciais: {str(e)}")
        raise


def test_gcs_connection():
    """Testa conexão com Google Cloud Storage"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import storage
        
        bucket_name = os.getenv('GCS_BUCKET')
        
        # Criar cliente GCS
        logger.info("🔌 Conectando ao Google Cloud Storage...")
        client = storage.Client()
        
        # Acessar bucket
        logger.info(f"📦 Tentando acessar bucket: {bucket_name}")
        bucket = client.bucket(bucket_name)
        
        # Verificar se bucket existe
        if bucket.exists():
            logger.info(f"✅ Bucket '{bucket_name}' acessado com sucesso!")
        else:
            raise ValueError(f"❌ Bucket '{bucket_name}' não existe!")
        
        # Listar objetos (primeiros 10)
        logger.info("📂 Listando objetos no bucket...")
        blobs = list(bucket.list_blobs(max_results=10))
        
        if blobs:
            logger.info(f"✅ Bucket contém {len(blobs)} objetos (mostrando primeiros 10):")
            for blob in blobs:
                logger.info(f"  - {blob.name}")
        else:
            logger.info("ℹ️  Bucket está vazio (esperado em setup inicial)")
        
        logger.info("🎉 Conexão GCS validada com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao conectar no GCS: {str(e)}")
        raise


def test_write_file():
    """Testa escrita de arquivo no GCS"""
    logger = logging.getLogger(__name__)
    
    try:
        from google.cloud import storage
        from datetime import datetime
        
        bucket_name = os.getenv('GCS_BUCKET')
        
        # Criar cliente
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # Criar arquivo de teste
        test_content = f"Teste de escrita - {datetime.now().isoformat()}"
        blob_name = "test/airflow_connection_test.txt"
        
        logger.info(f"📝 Criando arquivo de teste: {blob_name}")
        blob = bucket.blob(blob_name)
        blob.upload_from_string(test_content)
        
        logger.info(f"✅ Arquivo criado com sucesso!")
        logger.info(f"🔗 URL: gs://{bucket_name}/{blob_name}")
        
        # Verificar se arquivo foi criado
        if blob.exists():
            logger.info("✅ Arquivo verificado no GCS!")
            
            # Ler conteúdo de volta
            content = blob.download_as_text()
            logger.info(f"✅ Conteúdo lido: {content}")
        
        logger.info("🎉 Teste de escrita concluído com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao escrever no GCS: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id='00_test_gcs_connection',
    default_args=default_args,
    description='Teste de conexão com Google Cloud Storage',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['setup', 'test', 'gcs'],
) as dag:
    
    # Task 1: Verificar credenciais
    task_test_credentials = PythonOperator(
        task_id='test_gcp_credentials',
        python_callable=test_gcp_credentials,
    )
    
    # Task 2: Testar conexão GCS
    task_test_connection = PythonOperator(
        task_id='test_gcs_connection',
        python_callable=test_gcs_connection,
    )
    
    # Task 3: Testar escrita
    task_test_write = PythonOperator(
        task_id='test_write_file',
        python_callable=test_write_file,
    )
    
    # Pipeline
    task_test_credentials >> task_test_connection >> task_test_write
