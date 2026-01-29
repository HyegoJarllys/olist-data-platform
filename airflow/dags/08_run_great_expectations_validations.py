"""
DAG: Executar Great Expectations Validations
Fase 1 - Data Quality
Autor: Hyego
Data: 2025-01-28
Objetivo: Validar dados com Great Expectations e gerar Data Docs
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging
import json
import os

default_args = {
    'owner': 'hyego',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

GE_ROOT_DIR = "/opt/airflow/great_expectations"
DB_CONNECTION = "postgresql://airflow:airflow@postgres:5432/airflow"


def run_orders_validation():
    """Executa validação da tabela orders"""
    logger = logging.getLogger(__name__)
    
    try:
        from great_expectations.data_context import FileDataContext
        from great_expectations.core.batch import RuntimeBatchRequest
        
        logger.info("🔍 Validando tabela: orders")
        
        # Carregar contexto
        context = FileDataContext(context_root_dir=GE_ROOT_DIR)
        
        # Criar datasource para PostgreSQL
        datasource_config = {
            "name": "postgres_datasource",
            "class_name": "Datasource",
            "execution_engine": {
                "class_name": "SqlAlchemyExecutionEngine",
                "connection_string": DB_CONNECTION,
            },
            "data_connectors": {
                "default_runtime_data_connector": {
                    "class_name": "RuntimeDataConnector",
                    "batch_identifiers": ["default_identifier_name"],
                }
            },
        }
        
        context.add_datasource(**datasource_config)
        
        # Criar batch request
        batch_request = RuntimeBatchRequest(
            datasource_name="postgres_datasource",
            data_connector_name="default_runtime_data_connector",
            data_asset_name="orders",
            runtime_parameters={
                "query": "SELECT * FROM olist_raw.orders LIMIT 10000"
            },
            batch_identifiers={"default_identifier_name": "orders_batch"},
        )
        
        # Criar checkpoint (verificar se já existe)
        checkpoint_name = "orders_checkpoint"
        
        try:
            context.get_checkpoint(checkpoint_name)
            logger.info(f"✅ Checkpoint {checkpoint_name} já existe, reutilizando...")
        except:
            checkpoint_config = {
                "name": checkpoint_name,
                "config_version": 1.0,
                "class_name": "SimpleCheckpoint",
                "run_name_template": "%Y%m%d-%H%M%S-orders-validation",
            }
            context.add_checkpoint(**checkpoint_config)
            logger.info(f"✅ Checkpoint {checkpoint_name} criado!")
        
        # Executar validação
        results = context.run_checkpoint(
            checkpoint_name="orders_checkpoint",
            validations=[
                {
                    "batch_request": batch_request,
                    "expectation_suite_name": "orders_suite",
                }
            ],
        )
        
        # Analisar resultados
        validation_result = results.list_validation_results()[0]
        success = validation_result["success"]
        statistics = validation_result["statistics"]
        
        logger.info(f"""
        📊 RESULTADO VALIDAÇÃO ORDERS:
        - Success: {success}
        - Expectations avaliadas: {statistics['evaluated_expectations']}
        - Expectations com sucesso: {statistics['successful_expectations']}
        - Success %: {statistics['success_percent']:.2f}%
        """)
        
        if not success:
            logger.warning("⚠️ Algumas validações falharam! Verifique Data Docs.")
        else:
            logger.info("✅ Todas as validações passaram!")
        
        return {
            'table': 'orders',
            'success': success,
            'statistics': statistics
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na validação orders: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def run_customers_validation():
    """Executa validação da tabela customers"""
    logger = logging.getLogger(__name__)
    
    try:
        from great_expectations.data_context import FileDataContext
        from great_expectations.core.batch import RuntimeBatchRequest
        
        logger.info("🔍 Validando tabela: customers")
        
        context = FileDataContext(context_root_dir=GE_ROOT_DIR)
        
        # Datasource já existe da task anterior, apenas criar batch
        batch_request = RuntimeBatchRequest(
            datasource_name="postgres_datasource",
            data_connector_name="default_runtime_data_connector",
            data_asset_name="customers",
            runtime_parameters={
                "query": "SELECT * FROM olist_raw.customers LIMIT 10000"
            },
            batch_identifiers={"default_identifier_name": "customers_batch"},
        )
        
        checkpoint_name = "customers_checkpoint"
        
        try:
            context.get_checkpoint(checkpoint_name)
            logger.info(f"✅ Checkpoint {checkpoint_name} já existe, reutilizando...")
        except:
            checkpoint_config = {
                "name": checkpoint_name,
                "config_version": 1.0,
                "class_name": "SimpleCheckpoint",
                "run_name_template": "%Y%m%d-%H%M%S-customers-validation",
            }
            context.add_checkpoint(**checkpoint_config)
            logger.info(f"✅ Checkpoint {checkpoint_name} criado!")
        
        results = context.run_checkpoint(
            checkpoint_name="customers_checkpoint",
            validations=[
                {
                    "batch_request": batch_request,
                    "expectation_suite_name": "customers_suite",
                }
            ],
        )
        
        validation_result = results.list_validation_results()[0]
        success = validation_result["success"]
        statistics = validation_result["statistics"]
        
        logger.info(f"""
        📊 RESULTADO VALIDAÇÃO CUSTOMERS:
        - Success: {success}
        - Expectations avaliadas: {statistics['evaluated_expectations']}
        - Expectations com sucesso: {statistics['successful_expectations']}
        - Success %: {statistics['success_percent']:.2f}%
        """)
        
        if not success:
            logger.warning("⚠️ Algumas validações falharam! Verifique Data Docs.")
        else:
            logger.info("✅ Todas as validações passaram!")
        
        return {
            'table': 'customers',
            'success': success,
            'statistics': statistics
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na validação customers: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def run_order_items_validation():
    """Executa validação da tabela order_items"""
    logger = logging.getLogger(__name__)
    
    try:
        from great_expectations.data_context import FileDataContext
        from great_expectations.core.batch import RuntimeBatchRequest
        
        logger.info("🔍 Validando tabela: order_items")
        
        context = FileDataContext(context_root_dir=GE_ROOT_DIR)
        
        batch_request = RuntimeBatchRequest(
            datasource_name="postgres_datasource",
            data_connector_name="default_runtime_data_connector",
            data_asset_name="order_items",
            runtime_parameters={
                "query": "SELECT * FROM olist_raw.order_items LIMIT 10000"
            },
            batch_identifiers={"default_identifier_name": "order_items_batch"},
        )
        
        checkpoint_name = "order_items_checkpoint"
        
        try:
            context.get_checkpoint(checkpoint_name)
            logger.info(f"✅ Checkpoint {checkpoint_name} já existe, reutilizando...")
        except:
            checkpoint_config = {
                "name": checkpoint_name,
                "config_version": 1.0,
                "class_name": "SimpleCheckpoint",
                "run_name_template": "%Y%m%d-%H%M%S-order_items-validation",
            }
            context.add_checkpoint(**checkpoint_config)
            logger.info(f"✅ Checkpoint {checkpoint_name} criado!")
        
        results = context.run_checkpoint(
            checkpoint_name="order_items_checkpoint",
            validations=[
                {
                    "batch_request": batch_request,
                    "expectation_suite_name": "order_items_suite",
                }
            ],
        )
        
        validation_result = results.list_validation_results()[0]
        success = validation_result["success"]
        statistics = validation_result["statistics"]
        
        logger.info(f"""
        📊 RESULTADO VALIDAÇÃO ORDER_ITEMS:
        - Success: {success}
        - Expectations avaliadas: {statistics['evaluated_expectations']}
        - Expectations com sucesso: {statistics['successful_expectations']}
        - Success %: {statistics['success_percent']:.2f}%
        """)
        
        if not success:
            logger.warning("⚠️ Algumas validações falharam! Verifique Data Docs.")
        else:
            logger.info("✅ Todas as validações passaram!")
        
        return {
            'table': 'order_items',
            'success': success,
            'statistics': statistics
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na validação order_items: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def build_data_docs():
    """Gera Data Docs HTML"""
    logger = logging.getLogger(__name__)
    
    try:
        from great_expectations.data_context import FileDataContext
        
        logger.info("📚 Gerando Data Docs...")
        
        context = FileDataContext(context_root_dir=GE_ROOT_DIR)
        
        # Build data docs
        context.build_data_docs()
        
        docs_path = f"{GE_ROOT_DIR}/uncommitted/data_docs/local_site/index.html"
        
        if os.path.exists(docs_path):
            logger.info(f"✅ Data Docs gerados com sucesso!")
            logger.info(f"📂 Localização: {docs_path}")
            logger.info(f"""
            🌐 PARA VISUALIZAR OS DATA DOCS:
            
            1. Copie o diretório data_docs para sua máquina:
               docker cp olist-data-pipeline-airflow-webserver-1:{GE_ROOT_DIR}/uncommitted/data_docs /tmp/
            
            2. Abra o arquivo index.html no navegador
            
            OU acesse via container:
               docker exec olist-data-pipeline-airflow-webserver-1 ls -la {docs_path}
            """)
        else:
            logger.warning("⚠️ Data Docs não foram encontrados!")
        
        logger.info("🎉 Data Docs build concluído!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar Data Docs: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# DAG Definition
with DAG(
    dag_id='08_run_great_expectations_validations',
    default_args=default_args,
    description='Executar validações Great Expectations e gerar Data Docs',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['data-quality', 'great-expectations', 'validation'],
) as dag:
    
    # Task 1: Validar orders
    task_validate_orders = PythonOperator(
        task_id='validate_orders',
        python_callable=run_orders_validation,
    )
    
    # Task 2: Validar customers
    task_validate_customers = PythonOperator(
        task_id='validate_customers',
        python_callable=run_customers_validation,
    )
    
    # Task 3: Validar order_items
    task_validate_order_items = PythonOperator(
        task_id='validate_order_items',
        python_callable=run_order_items_validation,
    )
    
    # Task 4: Gerar Data Docs
    task_build_docs = PythonOperator(
        task_id='build_data_docs',
        python_callable=build_data_docs,
    )
    
    # Pipeline: Validações em paralelo -> Gerar docs
    [task_validate_orders, task_validate_customers, task_validate_order_items] >> task_build_docs
