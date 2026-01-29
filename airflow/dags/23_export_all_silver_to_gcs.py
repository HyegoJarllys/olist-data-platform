"""
DAG: Export All Silver Tables to GCS (Consolidated)
Fase 2 - Data Transformation - Silver Layer Export
Autor: Hyego
Data: 2025-01-29

RESPONSABILIDADE DESTA DAG:
- Exportar TODAS as 8 tabelas Silver para GCS
- Formato: Parquet (compressão Snappy)
- Particionamento: year=YYYY/month=MM (por processed_at)
- Versionamento: Data lake backup

IMPORTANTE:
- Esta DAG roda DEPOIS das DAGs 15-22
- Todas as tabelas Silver devem existir
- Export em PARALELO (tasks independentes)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging
import pandas as pd
from sqlalchemy import create_engine
from google.cloud import storage
import os

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
GCP_PROJECT_ID = "olist-data-platform"
GCS_BUCKET = "olist-data-lake-hyego"
GCP_CREDENTIALS_PATH = "/opt/airflow/gcp-credentials.json"


def export_table_to_gcs(table_name: str, partition_column: str = 'processed_at'):
    """
    Exporta uma tabela Silver para GCS com particionamento.
    
    Args:
        table_name: Nome da tabela (ex: 'customers')
        partition_column: Coluna para particionar (default: 'processed_at')
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🔄 Iniciando export: {table_name}")
        
        # Configurar credenciais GCP
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GCP_CREDENTIALS_PATH
        
        # Conectar ao PostgreSQL
        engine = create_engine(DB_CONNECTION)
        
        # Ler dados da Silver
        query = f"""
        SELECT 
            *,
            EXTRACT(YEAR FROM {partition_column}) AS year,
            EXTRACT(MONTH FROM {partition_column}) AS month
        FROM olist_silver.{table_name};
        """
        
        logger.info(f"📥 Lendo dados de olist_silver.{table_name}...")
        df = pd.read_sql(query, engine)
        
        total_records = len(df)
        logger.info(f"📊 Total de registros lidos: {total_records:,}")
        
        if total_records == 0:
            logger.warning(f"⚠️  Tabela {table_name} está vazia! Pulando export.")
            engine.dispose()
            return {
                'table': table_name,
                'status': 'skipped',
                'reason': 'empty_table',
                'records': 0,
                'partitions': 0
            }
        
        # Agrupar por partições (year/month)
        partitions = df.groupby(['year', 'month'])
        
        logger.info(f"📂 Total de partições a serem criadas: {len(partitions)}")
        
        # Inicializar cliente GCS
        storage_client = storage.Client(project=GCP_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET)
        
        uploaded_files = []
        
        # Exportar cada partição
        for (year, month), partition_df in partitions:
            # Remover colunas auxiliares
            partition_df = partition_df.drop(columns=['year', 'month'])
            
            # Criar path particionado
            partition_path = f"silver/{table_name}/year={int(year)}/month={int(month):02d}/data.parquet"
            
            logger.info(f"📤 Exportando partição: {partition_path} ({len(partition_df):,} registros)")
            
            # Salvar localmente temporariamente
            temp_file = f"/tmp/{table_name}_y{int(year)}_m{int(month):02d}.parquet"
            partition_df.to_parquet(temp_file, engine='pyarrow', compression='snappy', index=False)
            
            # Upload para GCS
            blob = bucket.blob(partition_path)
            blob.upload_from_filename(temp_file)
            
            logger.info(f"✅ Partição enviada: gs://{GCS_BUCKET}/{partition_path}")
            
            uploaded_files.append({
                'partition': partition_path,
                'records': len(partition_df),
                'year': int(year),
                'month': int(month)
            })
            
            # Remover arquivo temporário
            os.remove(temp_file)
        
        logger.info(f"""
        🎉 EXPORT CONCLUÍDO: {table_name}
        
        📊 Resumo:
        - Total de registros exportados: {total_records:,}
        - Total de partições criadas: {len(uploaded_files)}
        - Bucket: gs://{GCS_BUCKET}/silver/{table_name}/
        """)
        
        for file_info in uploaded_files:
            logger.info(f"   - year={file_info['year']}/month={file_info['month']:02d}: {file_info['records']:,} registros")
        
        engine.dispose()
        
        return {
            'table': table_name,
            'status': 'success',
            'records': total_records,
            'partitions': len(uploaded_files),
            'files': uploaded_files
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no export de {table_name}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Funções específicas para cada tabela (para tasks paralelas)
def export_customers():
    return export_table_to_gcs('customers', 'processed_at')

def export_orders():
    return export_table_to_gcs('orders', 'processed_at')

def export_products():
    return export_table_to_gcs('products', 'processed_at')

def export_sellers():
    return export_table_to_gcs('sellers', 'processed_at')

def export_order_items():
    return export_table_to_gcs('order_items', 'processed_at')

def export_order_payments():
    return export_table_to_gcs('order_payments', 'processed_at')

def export_order_reviews():
    return export_table_to_gcs('order_reviews', 'processed_at')

def export_geolocation():
    return export_table_to_gcs('geolocation', 'processed_at')


def generate_export_summary(**context):
    """
    Gera resumo consolidado de todos os exports.
    Coleta resultados de todas as tasks anteriores via XCom.
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📊 Gerando resumo consolidado dos exports...")
        
        # Lista de tasks para buscar resultados
        tables = [
            'customers', 'orders', 'products', 'sellers',
            'order_items', 'order_payments', 'order_reviews', 'geolocation'
        ]
        
        total_records = 0
        total_partitions = 0
        summary = []
        
        for table in tables:
            task_id = f"export_{table}"
            try:
                result = context['ti'].xcom_pull(task_ids=task_id)
                if result:
                    total_records += result.get('records', 0)
                    total_partitions += result.get('partitions', 0)
                    summary.append(result)
            except Exception as e:
                logger.warning(f"⚠️  Não foi possível obter resultado de {task_id}: {e}")
        
        logger.info(f"""
        ═══════════════════════════════════════════
        🎉 EXPORT SILVER TO GCS - RESUMO FINAL
        ═══════════════════════════════════════════
        
        📊 Estatísticas Gerais:
        - Tabelas exportadas: {len(summary)}/8
        - Total de registros: {total_records:,}
        - Total de partições: {total_partitions}
        - Bucket: gs://{GCS_BUCKET}/silver/
        
        📁 Detalhamento por Tabela:
        """)
        
        for item in summary:
            status_icon = '✅' if item['status'] == 'success' else '⚠️'
            logger.info(f"{status_icon} {item['table']}: {item['records']:,} registros em {item['partitions']} partições")
        
        logger.info("""
        ═══════════════════════════════════════════
        ✅ SILVER LAYER COMPLETA!
        ═══════════════════════════════════════════
        
        🎯 Próximos Passos:
        1. Validar arquivos no GCS
        2. Implementar Great Expectations (Silver)
        3. Iniciar Gold Layer (Fase 3)
        
        🎊 PARABÉNS! Fase 2 (Silver) concluída com sucesso!
        """)
        
        return {
            'total_tables': len(summary),
            'total_records': total_records,
            'total_partitions': total_partitions,
            'status': 'success'
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar resumo: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Definição da DAG
with DAG(
    dag_id='23_export_all_silver_to_gcs',
    default_args=default_args,
    description='[EXPORT] Exportar todas as tabelas Silver para GCS (Parquet particionado)',
    schedule_interval=None,  # Execução manual
    start_date=datetime(2025, 1, 29),
    catchup=False,
    tags=['fase-2', 'silver', 'export', 'gcs', 'consolidado'],
) as dag:
    
    # Tasks de export (PARALELAS - independentes entre si)
    task_export_customers = PythonOperator(
        task_id='export_customers',
        python_callable=export_customers,
    )
    
    task_export_orders = PythonOperator(
        task_id='export_orders',
        python_callable=export_orders,
    )
    
    task_export_products = PythonOperator(
        task_id='export_products',
        python_callable=export_products,
    )
    
    task_export_sellers = PythonOperator(
        task_id='export_sellers',
        python_callable=export_sellers,
    )
    
    task_export_order_items = PythonOperator(
        task_id='export_order_items',
        python_callable=export_order_items,
    )
    
    task_export_order_payments = PythonOperator(
        task_id='export_order_payments',
        python_callable=export_order_payments,
    )
    
    task_export_order_reviews = PythonOperator(
        task_id='export_order_reviews',
        python_callable=export_order_reviews,
    )
    
    task_export_geolocation = PythonOperator(
        task_id='export_geolocation',
        python_callable=export_geolocation,
    )
    
    # Task final: resumo consolidado
    task_generate_summary = PythonOperator(
        task_id='generate_export_summary',
        python_callable=generate_export_summary,
        provide_context=True,
    )
    
    # Pipeline: Todas as exports em PARALELO → Resumo final
    [
        task_export_customers,
        task_export_orders,
        task_export_products,
        task_export_sellers,
        task_export_order_items,
        task_export_order_payments,
        task_export_order_reviews,
        task_export_geolocation
    ] >> task_generate_summary
