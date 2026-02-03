"""
DAG: Create Expectation Suites for Silver Layer
Fase 2 - Data Quality - Silver Layer
Autor: Hyego
Data: 2025-01-29

RESPONSABILIDADE DESTA DAG:
- Criar Expectation Suites para as 4 principais tabelas Silver
- Expectations AVANÇADAS (além das básicas da Bronze)
- Validar transformações técnicas aplicadas

Tabelas validadas:
1. customers (enriquecimento geográfico)
2. orders (status, timestamps)
3. products (dimensões, categorias)
4. order_items (valores monetários, PK composta)

IMPORTANTE:
- Executar DEPOIS da DAG 24 (setup)
- Executar UMA VEZ apenas
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging

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


def create_customers_suite():
    """Cria Expectation Suite para olist_silver.customers"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔧 Criando Expectation Suite: customers_silver_suite")
        
        from great_expectations.data_context import FileDataContext
        from great_expectations.core import ExpectationConfiguration
        
        context = FileDataContext(context_root_dir=GE_ROOT_DIR)
        
        suite_name = "customers_silver_suite"
        try:
            context.delete_expectation_suite(suite_name)
        except:
            pass
        
        suite = context.add_expectation_suite(expectation_suite_name=suite_name)
        
        expectations = [
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "customer_id"}},
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "geolocation_lat"}},
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "geolocation_lng"}},
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "has_geolocation"}},
            {"expectation_type": "expect_column_values_to_be_unique", "kwargs": {"column": "customer_id"}},
            {"expectation_type": "expect_column_values_to_not_be_null", "kwargs": {"column": "customer_id"}},
            {"expectation_type": "expect_column_values_to_be_between", "kwargs": {"column": "geolocation_lat", "min_value": -34, "max_value": 6, "mostly": 0.99}},
            {"expectation_type": "expect_column_values_to_be_between", "kwargs": {"column": "geolocation_lng", "min_value": -75, "max_value": -33, "mostly": 0.99}},
            {"expectation_type": "expect_column_values_to_be_in_set", "kwargs": {"column": "has_geolocation", "value_set": [True, False]}},
            {"expectation_type": "expect_column_value_lengths_to_equal", "kwargs": {"column": "customer_state", "value": 2}},
            {"expectation_type": "expect_table_row_count_to_be_between", "kwargs": {"min_value": 95000, "max_value": 105000}},
            {"expectation_type": "expect_table_column_count_to_equal", "kwargs": {"value": 11}}
        ]
        
        for exp in expectations:
            config = ExpectationConfiguration(**exp)
            suite.add_expectation(expectation_configuration=config)
        
        context.save_expectation_suite(suite)
        logger.info(f"✅ Suite customers criada com {len(expectations)} expectations!")
        
        return {'suite': suite_name, 'expectations': len(expectations), 'status': 'success'}
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def create_orders_suite():
    """Cria Expectation Suite para olist_silver.orders"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔧 Criando Expectation Suite: orders_silver_suite")
        
        from great_expectations.data_context import FileDataContext
        from great_expectations.core import ExpectationConfiguration
        
        context = FileDataContext(context_root_dir=GE_ROOT_DIR)
        
        suite_name = "orders_silver_suite"
        try:
            context.delete_expectation_suite(suite_name)
        except:
            pass
        
        suite = context.add_expectation_suite(expectation_suite_name=suite_name)
        
        expectations = [
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "order_id"}},
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "order_status"}},
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "is_delivered"}},
            {"expectation_type": "expect_column_values_to_be_unique", "kwargs": {"column": "order_id"}},
            {"expectation_type": "expect_column_values_to_not_be_null", "kwargs": {"column": "order_id"}},
            {"expectation_type": "expect_column_values_to_be_in_set", "kwargs": {"column": "order_status", "value_set": ["delivered", "shipped", "canceled", "unavailable", "invoiced", "processing", "approved", "created"]}},
            {"expectation_type": "expect_column_values_to_not_be_null", "kwargs": {"column": "order_purchase_timestamp"}},
            {"expectation_type": "expect_column_values_to_be_in_set", "kwargs": {"column": "is_delivered", "value_set": [True, False]}},
            {"expectation_type": "expect_column_values_to_be_in_set", "kwargs": {"column": "is_approved", "value_set": [True, False]}},
            {"expectation_type": "expect_column_values_to_not_be_null", "kwargs": {"column": "customer_id"}},
            {"expectation_type": "expect_table_row_count_to_be_between", "kwargs": {"min_value": 95000, "max_value": 105000}}
        ]
        
        for exp in expectations:
            config = ExpectationConfiguration(**exp)
            suite.add_expectation(expectation_configuration=config)
        
        context.save_expectation_suite(suite)
        logger.info(f"✅ Suite orders criada com {len(expectations)} expectations!")
        
        return {'suite': suite_name, 'expectations': len(expectations), 'status': 'success'}
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def create_products_suite():
    """Cria Expectation Suite para olist_silver.products"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔧 Criando Expectation Suite: products_silver_suite")
        
        from great_expectations.data_context import FileDataContext
        from great_expectations.core import ExpectationConfiguration
        
        context = FileDataContext(context_root_dir=GE_ROOT_DIR)
        
        suite_name = "products_silver_suite"
        try:
            context.delete_expectation_suite(suite_name)
        except:
            pass
        
        suite = context.add_expectation_suite(expectation_suite_name=suite_name)
        
        expectations = [
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "product_id"}},
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "product_volume_cm3"}},
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "has_dimensions"}},
            {"expectation_type": "expect_column_values_to_be_unique", "kwargs": {"column": "product_id"}},
            {"expectation_type": "expect_column_values_to_not_be_null", "kwargs": {"column": "product_id"}},
            {"expectation_type": "expect_column_values_to_be_between", "kwargs": {"column": "product_weight_g", "min_value": 0, "max_value": 50000, "mostly": 0.99}},
            {"expectation_type": "expect_column_values_to_be_between", "kwargs": {"column": "product_volume_cm3", "min_value": 0, "max_value": 1000000, "mostly": 0.99}},
            {"expectation_type": "expect_column_values_to_be_between", "kwargs": {"column": "product_photos_qty", "min_value": 0, "max_value": 100}},
            {"expectation_type": "expect_column_values_to_be_in_set", "kwargs": {"column": "has_category", "value_set": [True, False]}},
            {"expectation_type": "expect_column_values_to_be_in_set", "kwargs": {"column": "has_dimensions", "value_set": [True, False]}},
            {"expectation_type": "expect_table_row_count_to_be_between", "kwargs": {"min_value": 30000, "max_value": 35000}}
        ]
        
        for exp in expectations:
            config = ExpectationConfiguration(**exp)
            suite.add_expectation(expectation_configuration=config)
        
        context.save_expectation_suite(suite)
        logger.info(f"✅ Suite products criada com {len(expectations)} expectations!")
        
        return {'suite': suite_name, 'expectations': len(expectations), 'status': 'success'}
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def create_order_items_suite():
    """Cria Expectation Suite para olist_silver.order_items"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔧 Criando Expectation Suite: order_items_silver_suite")
        
        from great_expectations.data_context import FileDataContext
        from great_expectations.core import ExpectationConfiguration
        
        context = FileDataContext(context_root_dir=GE_ROOT_DIR)
        
        suite_name = "order_items_silver_suite"
        try:
            context.delete_expectation_suite(suite_name)
        except:
            pass
        
        suite = context.add_expectation_suite(expectation_suite_name=suite_name)
        
        expectations = [
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "order_id"}},
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "order_item_id"}},
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "price"}},
            {"expectation_type": "expect_column_to_exist", "kwargs": {"column": "item_total_value"}},
            {"expectation_type": "expect_column_values_to_not_be_null", "kwargs": {"column": "order_id"}},
            {"expectation_type": "expect_column_values_to_not_be_null", "kwargs": {"column": "order_item_id"}},
            {"expectation_type": "expect_column_values_to_not_be_null", "kwargs": {"column": "product_id"}},
            {"expectation_type": "expect_column_values_to_not_be_null", "kwargs": {"column": "seller_id"}},
            {"expectation_type": "expect_column_values_to_be_between", "kwargs": {"column": "price", "min_value": 0, "max_value": 10000, "mostly": 0.99}},
            {"expectation_type": "expect_column_values_to_be_between", "kwargs": {"column": "freight_value", "min_value": 0, "max_value": 1000, "mostly": 0.99}},
            {"expectation_type": "expect_column_values_to_be_between", "kwargs": {"column": "item_total_value", "min_value": 0, "max_value": 11000, "mostly": 0.99}},
            {"expectation_type": "expect_column_values_to_be_in_set", "kwargs": {"column": "has_price", "value_set": [True, False]}},
            {"expectation_type": "expect_table_row_count_to_be_between", "kwargs": {"min_value": 100000, "max_value": 120000}}
        ]
        
        for exp in expectations:
            config = ExpectationConfiguration(**exp)
            suite.add_expectation(expectation_configuration=config)
        
        context.save_expectation_suite(suite)
        logger.info(f"✅ Suite order_items criada com {len(expectations)} expectations!")
        
        return {'suite': suite_name, 'expectations': len(expectations), 'status': 'success'}
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Definição da DAG
with DAG(
    dag_id='25_create_expectation_suites_silver',
    default_args=default_args,
    description='[QUALITY] Criar Expectation Suites para as 4 principais tabelas Silver',
    schedule_interval=None,
    start_date=datetime(2025, 1, 29),
    catchup=False,
    tags=['fase-2', 'silver', 'data-quality', 'great-expectations', 'suites'],
) as dag:
    
    task_create_customers_suite = PythonOperator(
        task_id='create_customers_suite',
        python_callable=create_customers_suite,
    )
    
    task_create_orders_suite = PythonOperator(
        task_id='create_orders_suite',
        python_callable=create_orders_suite,
    )
    
    task_create_products_suite = PythonOperator(
        task_id='create_products_suite',
        python_callable=create_products_suite,
    )
    
    task_create_order_items_suite = PythonOperator(
        task_id='create_order_items_suite',
        python_callable=create_order_items_suite,
    )
    
    task_create_customers_suite >> task_create_orders_suite >> task_create_products_suite >> task_create_order_items_suite
