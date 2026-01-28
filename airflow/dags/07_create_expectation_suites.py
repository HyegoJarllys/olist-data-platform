"""
DAG: Criar Expectation Suites
Fase 1 - Data Quality
Autor: Hyego
Data: 2025-01-28
Objetivo: Criar suites de validação para tabelas principais
EXECUTE APENAS UMA VEZ após 06_setup_great_expectations!
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


def create_orders_suite():
    """Cria Expectation Suite para tabela orders"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📝 Criando Expectation Suite: orders_suite")
        
        # Definir expectations manualmente (JSON)
        suite = {
            "expectation_suite_name": "orders_suite",
            "ge_cloud_id": None,
            "expectations": [
                # Coluna order_id
                {
                    "expectation_type": "expect_column_to_exist",
                    "kwargs": {"column": "order_id"}
                },
                {
                    "expectation_type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "order_id"}
                },
                {
                    "expectation_type": "expect_column_values_to_be_unique",
                    "kwargs": {"column": "order_id"}
                },
                # Coluna customer_id
                {
                    "expectation_type": "expect_column_to_exist",
                    "kwargs": {"column": "customer_id"}
                },
                {
                    "expectation_type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "customer_id"}
                },
                # Coluna order_status
                {
                    "expectation_type": "expect_column_to_exist",
                    "kwargs": {"column": "order_status"}
                },
                {
                    "expectation_type": "expect_column_values_to_be_in_set",
                    "kwargs": {
                        "column": "order_status",
                        "value_set": [
                            "delivered",
                            "shipped",
                            "canceled",
                            "unavailable",
                            "invoiced",
                            "processing",
                            "created",
                            "approved"
                        ]
                    }
                },
                # Coluna order_purchase_timestamp
                {
                    "expectation_type": "expect_column_to_exist",
                    "kwargs": {"column": "order_purchase_timestamp"}
                },
                {
                    "expectation_type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "order_purchase_timestamp"}
                },
                # Row count
                {
                    "expectation_type": "expect_table_row_count_to_be_between",
                    "kwargs": {
                        "min_value": 90000,
                        "max_value": 110000
                    }
                },
                # Column count
                {
                    "expectation_type": "expect_table_column_count_to_equal",
                    "kwargs": {"value": 10}
                }
            ],
            "data_asset_type": "Table",
            "meta": {
                "great_expectations_version": "0.18.8"
            }
        }
        
        # Salvar suite
        suite_dir = f"{GE_ROOT_DIR}/expectations"
        os.makedirs(suite_dir, exist_ok=True)
        
        suite_file = f"{suite_dir}/orders_suite.json"
        with open(suite_file, 'w') as f:
            json.dump(suite, f, indent=2)
        
        logger.info(f"✅ Suite criada: {suite_file}")
        logger.info(f"📊 Total de expectations: {len(suite['expectations'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar orders_suite: {str(e)}")
        raise


def create_customers_suite():
    """Cria Expectation Suite para tabela customers"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📝 Criando Expectation Suite: customers_suite")
        
        suite = {
            "expectation_suite_name": "customers_suite",
            "ge_cloud_id": None,
            "expectations": [
                # Coluna customer_id
                {
                    "expectation_type": "expect_column_to_exist",
                    "kwargs": {"column": "customer_id"}
                },
                {
                    "expectation_type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "customer_id"}
                },
                {
                    "expectation_type": "expect_column_values_to_be_unique",
                    "kwargs": {"column": "customer_id"}
                },
                # Coluna customer_unique_id
                {
                    "expectation_type": "expect_column_to_exist",
                    "kwargs": {"column": "customer_unique_id"}
                },
                {
                    "expectation_type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "customer_unique_id"}
                },
                # Coluna customer_state
                {
                    "expectation_type": "expect_column_to_exist",
                    "kwargs": {"column": "customer_state"}
                },
                {
                    "expectation_type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "customer_state"}
                },
                {
                    "expectation_type": "expect_column_value_lengths_to_equal",
                    "kwargs": {
                        "column": "customer_state",
                        "value": 2
                    }
                },
                # Row count
                {
                    "expectation_type": "expect_table_row_count_to_be_between",
                    "kwargs": {
                        "min_value": 95000,
                        "max_value": 105000
                    }
                },
                # Column count
                {
                    "expectation_type": "expect_table_column_count_to_equal",
                    "kwargs": {"value": 7}
                }
            ],
            "data_asset_type": "Table",
            "meta": {
                "great_expectations_version": "0.18.8"
            }
        }
        
        suite_dir = f"{GE_ROOT_DIR}/expectations"
        suite_file = f"{suite_dir}/customers_suite.json"
        
        with open(suite_file, 'w') as f:
            json.dump(suite, f, indent=2)
        
        logger.info(f"✅ Suite criada: {suite_file}")
        logger.info(f"📊 Total de expectations: {len(suite['expectations'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar customers_suite: {str(e)}")
        raise


def create_order_items_suite():
    """Cria Expectation Suite para tabela order_items"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📝 Criando Expectation Suite: order_items_suite")
        
        suite = {
            "expectation_suite_name": "order_items_suite",
            "ge_cloud_id": None,
            "expectations": [
                # Coluna order_id
                {
                    "expectation_type": "expect_column_to_exist",
                    "kwargs": {"column": "order_id"}
                },
                {
                    "expectation_type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "order_id"}
                },
                # Coluna order_item_id
                {
                    "expectation_type": "expect_column_to_exist",
                    "kwargs": {"column": "order_item_id"}
                },
                {
                    "expectation_type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "order_item_id"}
                },
                # Coluna price
                {
                    "expectation_type": "expect_column_to_exist",
                    "kwargs": {"column": "price"}
                },
                {
                    "expectation_type": "expect_column_values_to_not_be_null",
                    "kwargs": {"column": "price"}
                },
                {
                    "expectation_type": "expect_column_values_to_be_between",
                    "kwargs": {
                        "column": "price",
                        "min_value": 0,
                        "max_value": 10000
                    }
                },
                # Coluna freight_value
                {
                    "expectation_type": "expect_column_to_exist",
                    "kwargs": {"column": "freight_value"}
                },
                {
                    "expectation_type": "expect_column_values_to_be_between",
                    "kwargs": {
                        "column": "freight_value",
                        "min_value": 0,
                        "max_value": 1000
                    }
                },
                # Row count
                {
                    "expectation_type": "expect_table_row_count_to_be_between",
                    "kwargs": {
                        "min_value": 100000,
                        "max_value": 120000
                    }
                }
            ],
            "data_asset_type": "Table",
            "meta": {
                "great_expectations_version": "0.18.8"
            }
        }
        
        suite_dir = f"{GE_ROOT_DIR}/expectations"
        suite_file = f"{suite_dir}/order_items_suite.json"
        
        with open(suite_file, 'w') as f:
            json.dump(suite, f, indent=2)
        
        logger.info(f"✅ Suite criada: {suite_file}")
        logger.info(f"📊 Total de expectations: {len(suite['expectations'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar order_items_suite: {str(e)}")
        raise


def verify_suites():
    """Verifica se as suites foram criadas"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Verificando Expectation Suites...")
        
        suite_dir = f"{GE_ROOT_DIR}/expectations"
        expected_suites = [
            "orders_suite.json",
            "customers_suite.json",
            "order_items_suite.json"
        ]
        
        results = []
        
        for suite_name in expected_suites:
            suite_path = f"{suite_dir}/{suite_name}"
            
            if os.path.exists(suite_path):
                with open(suite_path, 'r') as f:
                    suite_data = json.load(f)
                
                expectation_count = len(suite_data.get('expectations', []))
                logger.info(f"✅ {suite_name}: {expectation_count} expectations")
                
                results.append({
                    'suite': suite_name,
                    'exists': True,
                    'expectations': expectation_count
                })
            else:
                logger.error(f"❌ {suite_name}: não encontrado!")
                results.append({
                    'suite': suite_name,
                    'exists': False
                })
        
        # Verificar se todas existem
        missing = [r['suite'] for r in results if not r['exists']]
        
        if missing:
            raise FileNotFoundError(f"❌ Suites não encontradas: {missing}")
        
        total_expectations = sum(r['expectations'] for r in results)
        
        logger.info(f"""
        📊 RESUMO EXPECTATION SUITES:
        - Total de suites: {len(results)}
        - Total de expectations: {total_expectations}
        - Localização: {suite_dir}
        """)
        
        logger.info("✅ Todas as Expectation Suites foram criadas com sucesso!")
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro na verificação: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id='07_create_expectation_suites',
    default_args=default_args,
    description='Criar Expectation Suites para Great Expectations (executar UMA VEZ)',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['setup', 'great-expectations', 'one-time'],
) as dag:
    
    # Task 1: Criar suite orders
    task_create_orders = PythonOperator(
        task_id='create_orders_suite',
        python_callable=create_orders_suite,
    )
    
    # Task 2: Criar suite customers
    task_create_customers = PythonOperator(
        task_id='create_customers_suite',
        python_callable=create_customers_suite,
    )
    
    # Task 3: Criar suite order_items
    task_create_order_items = PythonOperator(
        task_id='create_order_items_suite',
        python_callable=create_order_items_suite,
    )
    
    # Task 4: Verificar suites
    task_verify = PythonOperator(
        task_id='verify_suites',
        python_callable=verify_suites,
    )
    
    # Pipeline: Criar todas em paralelo -> verificar
    [task_create_orders, task_create_customers, task_create_order_items] >> task_verify
