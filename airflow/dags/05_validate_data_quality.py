"""
DAG: Validação Consolidada de Qualidade de Dados
Fase 1 - Data Quality
Autor: Hyego
Data: 2025-01-28
Objetivo: Validar integridade dos dados em PostgreSQL e GCS
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging
from sqlalchemy import create_engine, text
from google.cloud import storage
import os

# Configurações
DB_CONNECTION = 'postgresql://airflow:airflow@postgres:5432/airflow'
BUCKET_NAME = os.getenv('GCS_BUCKET', 'olist-data-lake-hyego')
BRONZE_PREFIX = 'bronze'

# Expectativas de row counts (baseado nos CSVs originais)
EXPECTED_COUNTS = {
    'customers': 99441,
    'sellers': 3095,
    'products': 32951,
    'orders': 99441,
    'order_items': 112650,
    'order_payments': 103886,
    'order_reviews': 99224,
    'geolocation': 19000  # Após deduplicação (1 por CEP)
}

default_args = {
    'owner': 'hyego',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}


def validate_row_counts():
    """Valida contagem de registros no PostgreSQL"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Validando row counts no PostgreSQL...")
        
        engine = create_engine(DB_CONNECTION)
        results = []
        errors = []
        
        for table, expected in EXPECTED_COUNTS.items():
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM olist_raw.{table}"))
                actual = result.scalar()
            
            # Calcular diferença
            diff = actual - expected
            diff_pct = (diff / expected * 100) if expected > 0 else 0
            
            status = "✅" if abs(diff_pct) < 1 else "⚠️"
            
            logger.info(f"{status} {table}: {actual:,} registros (esperado: {expected:,}, diff: {diff:+,} [{diff_pct:+.2f}%])")
            
            results.append({
                'table': table,
                'expected': expected,
                'actual': actual,
                'diff': diff,
                'diff_pct': diff_pct,
                'status': 'OK' if abs(diff_pct) < 1 else 'WARNING'
            })
            
            # Considerar erro se diferença > 5%
            if abs(diff_pct) > 5:
                errors.append(f"{table}: diferença de {diff_pct:.2f}%")
        
        # Resumo
        total_expected = sum(EXPECTED_COUNTS.values())
        total_actual = sum(r['actual'] for r in results)
        
        logger.info(f"""
        📊 RESUMO ROW COUNTS:
        - Total esperado: {total_expected:,}
        - Total atual: {total_actual:,}
        - Diferença: {total_actual - total_expected:+,}
        - Tabelas OK: {sum(1 for r in results if r['status'] == 'OK')}/{len(results)}
        """)
        
        if errors:
            raise ValueError(f"❌ Divergências significativas: {errors}")
        
        logger.info("✅ Validação de row counts aprovada!")
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro na validação de row counts: {str(e)}")
        raise


def validate_foreign_keys():
    """Valida integridade de Foreign Keys"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Validando integridade de Foreign Keys...")
        
        engine = create_engine(DB_CONNECTION)
        
        # Definir validações de FK
        fk_checks = [
            {
                'name': 'orders → customers',
                'query': """
                    SELECT COUNT(*) 
                    FROM olist_raw.orders o
                    LEFT JOIN olist_raw.customers c ON o.customer_id = c.customer_id
                    WHERE c.customer_id IS NULL
                """
            },
            {
                'name': 'order_items → orders',
                'query': """
                    SELECT COUNT(*) 
                    FROM olist_raw.order_items oi
                    LEFT JOIN olist_raw.orders o ON oi.order_id = o.order_id
                    WHERE o.order_id IS NULL
                """
            },
            {
                'name': 'order_items → products',
                'query': """
                    SELECT COUNT(*) 
                    FROM olist_raw.order_items oi
                    LEFT JOIN olist_raw.products p ON oi.product_id = p.product_id
                    WHERE p.product_id IS NULL
                """
            },
            {
                'name': 'order_items → sellers',
                'query': """
                    SELECT COUNT(*) 
                    FROM olist_raw.order_items oi
                    LEFT JOIN olist_raw.sellers s ON oi.seller_id = s.seller_id
                    WHERE s.seller_id IS NULL
                """
            },
            {
                'name': 'order_payments → orders',
                'query': """
                    SELECT COUNT(*) 
                    FROM olist_raw.order_payments op
                    LEFT JOIN olist_raw.orders o ON op.order_id = o.order_id
                    WHERE o.order_id IS NULL
                """
            },
            {
                'name': 'order_reviews → orders',
                'query': """
                    SELECT COUNT(*) 
                    FROM olist_raw.order_reviews r
                    LEFT JOIN olist_raw.orders o ON r.order_id = o.order_id
                    WHERE o.order_id IS NULL
                """
            }
        ]
        
        results = []
        errors = []
        
        for check in fk_checks:
            with engine.connect() as conn:
                orphans = conn.execute(text(check['query'])).scalar()
            
            status = "✅" if orphans == 0 else "❌"
            logger.info(f"{status} {check['name']}: {orphans} órfãos")
            
            results.append({
                'fk': check['name'],
                'orphans': orphans,
                'status': 'OK' if orphans == 0 else 'FAIL'
            })
            
            if orphans > 0:
                errors.append(f"{check['name']}: {orphans} órfãos")
        
        logger.info(f"""
        📊 RESUMO FOREIGN KEYS:
        - Total FKs validadas: {len(fk_checks)}
        - FKs OK: {sum(1 for r in results if r['status'] == 'OK')}/{len(results)}
        """)
        
        if errors:
            raise ValueError(f"❌ Órfãos encontrados: {errors}")
        
        logger.info("✅ Integridade de Foreign Keys validada!")
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro na validação de FKs: {str(e)}")
        raise


def validate_gcs_files():
    """Valida existência e tamanho dos arquivos no GCS"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Validando arquivos no GCS Bronze Layer...")
        
        execution_date = datetime.now().strftime('%Y-%m-%d')
        
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        
        results = []
        errors = []
        
        for table in EXPECTED_COUNTS.keys():
            expected_path = f'{BRONZE_PREFIX}/{table}/{execution_date}.parquet'
            blob = bucket.blob(expected_path)
            
            if blob.exists():
                blob.reload()
                size_mb = blob.size / (1024 * 1024)
                status = "✅"
                
                logger.info(f"{status} {table}: {size_mb:.2f} MB")
                
                results.append({
                    'table': table,
                    'exists': True,
                    'size_mb': size_mb,
                    'path': expected_path
                })
                
                # Validar tamanho mínimo (arquivos muito pequenos podem indicar problema)
                if size_mb < 0.01:
                    errors.append(f"{table}: arquivo muito pequeno ({size_mb:.4f} MB)")
            else:
                status = "❌"
                logger.error(f"{status} {table}: arquivo não encontrado!")
                
                results.append({
                    'table': table,
                    'exists': False
                })
                
                errors.append(f"{table}: arquivo não encontrado no GCS")
        
        total_size = sum(r.get('size_mb', 0) for r in results)
        files_ok = sum(1 for r in results if r['exists'])
        
        logger.info(f"""
        📊 RESUMO GCS BRONZE LAYER:
        - Arquivos validados: {files_ok}/{len(EXPECTED_COUNTS)}
        - Tamanho total: {total_size:.2f} MB
        - Bucket: {BUCKET_NAME}
        - Data: {execution_date}
        """)
        
        if errors:
            raise ValueError(f"❌ Problemas no GCS: {errors}")
        
        logger.info("✅ Arquivos GCS validados com sucesso!")
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro na validação GCS: {str(e)}")
        raise


def validate_schema():
    """Valida schema das tabelas PostgreSQL"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Validando schemas das tabelas...")
        
        engine = create_engine(DB_CONNECTION)
        
        # Colunas esperadas por tabela (mínimo necessário)
        expected_schemas = {
            'customers': ['customer_id', 'customer_unique_id', 'customer_zip_code_prefix', 'customer_city', 'customer_state'],
            'sellers': ['seller_id', 'seller_zip_code_prefix', 'seller_city', 'seller_state'],
            'products': ['product_id', 'product_category_name'],
            'orders': ['order_id', 'customer_id', 'order_status', 'order_purchase_timestamp'],
            'order_items': ['order_id', 'order_item_id', 'product_id', 'seller_id', 'price'],
            'order_payments': ['order_id', 'payment_sequential', 'payment_type', 'payment_value'],
            'order_reviews': ['review_id', 'order_id', 'review_score'],
            'geolocation': ['geolocation_zip_code_prefix', 'geolocation_lat', 'geolocation_lng', 'geolocation_city', 'geolocation_state']
        }
        
        results = []
        errors = []
        
        for table, expected_cols in expected_schemas.items():
            # Obter colunas atuais
            query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'olist_raw' 
                  AND table_name = :table_name
                ORDER BY ordinal_position
            """)
            
            with engine.connect() as conn:
                result = conn.execute(query, {'table_name': table})
                actual_cols = [row[0] for row in result]
            
            # Verificar colunas esperadas
            missing = [col for col in expected_cols if col not in actual_cols]
            
            if missing:
                status = "❌"
                logger.error(f"{status} {table}: colunas faltando: {missing}")
                errors.append(f"{table}: colunas faltando: {missing}")
            else:
                status = "✅"
                logger.info(f"{status} {table}: {len(actual_cols)} colunas OK")
            
            results.append({
                'table': table,
                'expected_cols': len(expected_cols),
                'actual_cols': len(actual_cols),
                'missing': missing,
                'status': 'OK' if not missing else 'FAIL'
            })
        
        logger.info(f"""
        📊 RESUMO SCHEMA VALIDATION:
        - Tabelas validadas: {len(results)}
        - Schemas OK: {sum(1 for r in results if r['status'] == 'OK')}/{len(results)}
        """)
        
        if errors:
            raise ValueError(f"❌ Problemas de schema: {errors}")
        
        logger.info("✅ Schemas validados com sucesso!")
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro na validação de schema: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id='05_validate_data_quality',
    default_args=default_args,
    description='Validação consolidada de qualidade dos dados',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['fase-1', 'validation', 'quality'],
) as dag:
    
    # Task 1: Validar row counts
    task_validate_counts = PythonOperator(
        task_id='validate_row_counts',
        python_callable=validate_row_counts,
    )
    
    # Task 2: Validar Foreign Keys
    task_validate_fks = PythonOperator(
        task_id='validate_foreign_keys',
        python_callable=validate_foreign_keys,
    )
    
    # Task 3: Validar arquivos GCS
    task_validate_gcs = PythonOperator(
        task_id='validate_gcs_files',
        python_callable=validate_gcs_files,
    )
    
    # Task 4: Validar schemas
    task_validate_schemas = PythonOperator(
        task_id='validate_schema',
        python_callable=validate_schema,
    )
    
    # Pipeline: Todas as validações em paralelo
    [task_validate_counts, task_validate_fks, task_validate_gcs, task_validate_schemas]
