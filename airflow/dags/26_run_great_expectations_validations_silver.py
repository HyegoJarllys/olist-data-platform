"""
DAG: Run Great Expectations Validations for Silver Layer
Fase 2 - Data Quality - Silver Layer
Autor: Hyego
Data: 2025-01-29

RESPONSABILIDADE DESTA DAG:
- Executar validações nas 4 tabelas Silver
- Gerar Data Docs (documentação HTML)
- Criar checkpoints para cada tabela
- Reportar resultados

IMPORTANTE:
- Executar DEPOIS das DAGs 24 (setup) e 25 (create suites)
- Pode executar MÚLTIPLAS VEZES (sempre que quiser validar)
- ÚLTIMA DAG DA FASE 2 SILVER!
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
DATASOURCE_NAME = "postgres_silver_datasource"


def validate_table(table_name: str, suite_name: str):
    """
    Executa validação Great Expectations em uma tabela Silver.
    
    Args:
        table_name: Nome da tabela (ex: 'customers')
        suite_name: Nome da suite (ex: 'customers_silver_suite')
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🔍 Validando tabela: {table_name}")
        
        from great_expectations.data_context import FileDataContext
        from great_expectations.core.batch import RuntimeBatchRequest
        
        context = FileDataContext(context_root_dir=GE_ROOT_DIR)
        
        # ============================================
        # PASSO 1: Criar BatchRequest
        # ============================================
        batch_request = RuntimeBatchRequest(
            datasource_name=DATASOURCE_NAME,
            data_connector_name="default_runtime_data_connector",
            data_asset_name=f"silver_{table_name}",
            runtime_parameters={
                "query": f"SELECT * FROM olist_silver.{table_name}"
            },
            batch_identifiers={"default_identifier_name": f"silver_{table_name}_batch"}
        )
        
        logger.info(f"✅ BatchRequest criado para {table_name}")
        
        # ============================================
        # PASSO 2: Criar/Atualizar Checkpoint
        # ============================================
        checkpoint_name = f"silver_{table_name}_checkpoint"
        
        checkpoint_config = {
            "name": checkpoint_name,
            "config_version": 1.0,
            "class_name": "SimpleCheckpoint",
            "run_name_template": f"%Y%m%d-%H%M%S-silver-{table_name}",
            "validations": [
                {
                    "batch_request": batch_request,
                    "expectation_suite_name": suite_name
                }
            ]
        }
        
        # Adicionar checkpoint
        try:
            context.add_checkpoint(**checkpoint_config)
            logger.info(f"✅ Checkpoint {checkpoint_name} criado")
        except Exception as e:
            logger.warning(f"⚠️  Checkpoint já existe ou erro: {e}")
        
        # ============================================
        # PASSO 3: Executar Validação
        # ============================================
        logger.info(f"🚀 Executando validação em {table_name}...")
        
        results = context.run_checkpoint(checkpoint_name=checkpoint_name)
        
        # ============================================
        # PASSO 4: Analisar Resultados
        # ============================================
        validation_result = results.list_validation_results()[0]
        
        success = validation_result["success"]
        statistics = validation_result.get("statistics", {})
        
        evaluated_expectations = statistics.get("evaluated_expectations", 0)
        successful_expectations = statistics.get("successful_expectations", 0)
        unsuccessful_expectations = statistics.get("unsuccessful_expectations", 0)
        success_percent = statistics.get("success_percent", 0)
        
        logger.info(f"""
        {'✅' if success else '❌'} RESULTADO: {table_name}
        
        📊 Estatísticas:
        - Expectations avaliadas: {evaluated_expectations}
        - Sucesso: {successful_expectations}
        - Falhas: {unsuccessful_expectations}
        - Taxa de sucesso: {success_percent:.2f}%
        """)
        
        if not success:
            logger.warning(f"⚠️  Validação {table_name} teve falhas!")
            # Listar falhas
            for result in validation_result.get("results", []):
                if not result.get("success", True):
                    exp_type = result.get("expectation_config", {}).get("expectation_type", "unknown")
                    logger.warning(f"   ❌ {exp_type}: {result.get('exception_info', {}).get('raised_exception', False)}")
        
        return {
            'table': table_name,
            'success': success,
            'evaluated': evaluated_expectations,
            'successful': successful_expectations,
            'unsuccessful': unsuccessful_expectations,
            'success_percent': success_percent
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na validação de {table_name}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def validate_customers():
    """Valida tabela customers"""
    return validate_table('customers', 'customers_silver_suite')


def validate_orders():
    """Valida tabela orders"""
    return validate_table('orders', 'orders_silver_suite')


def validate_products():
    """Valida tabela products"""
    return validate_table('products', 'products_silver_suite')


def validate_order_items():
    """Valida tabela order_items"""
    return validate_table('order_items', 'order_items_silver_suite')


def build_data_docs(**context):
    """
    Gera Data Docs (documentação HTML) com resultados das validações.
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📚 Gerando Data Docs...")
        
        from great_expectations.data_context import FileDataContext
        
        context_ge = FileDataContext(context_root_dir=GE_ROOT_DIR)
        
        # Construir Data Docs
        context_ge.build_data_docs()
        
        logger.info("✅ Data Docs gerados com sucesso!")
        
        # ============================================
        # COLETAR RESULTADOS DE TODAS AS TASKS
        # ============================================
        tables = ['customers', 'orders', 'products', 'order_items']
        
        total_evaluated = 0
        total_successful = 0
        total_unsuccessful = 0
        results_summary = []
        
        for table in tables:
            task_id = f"validate_{table}"
            try:
                result = context['ti'].xcom_pull(task_ids=task_id)
                if result:
                    total_evaluated += result.get('evaluated', 0)
                    total_successful += result.get('successful', 0)
                    total_unsuccessful += result.get('unsuccessful', 0)
                    results_summary.append(result)
            except Exception as e:
                logger.warning(f"⚠️  Não foi possível obter resultado de {task_id}: {e}")
        
        overall_success_rate = (total_successful / total_evaluated * 100) if total_evaluated > 0 else 0
        
        # ============================================
        # RESUMO FINAL
        # ============================================
        logger.info(f"""
        ═══════════════════════════════════════════
        📊 VALIDAÇÕES SILVER - RESUMO FINAL
        ═══════════════════════════════════════════
        
        🎯 Estatísticas Gerais:
        - Total de expectations: {total_evaluated}
        - Sucesso: {total_successful}
        - Falhas: {total_unsuccessful}
        - Taxa de sucesso geral: {overall_success_rate:.2f}%
        
        📋 Detalhamento por Tabela:
        """)
        
        for res in results_summary:
            status_icon = '✅' if res['success'] else '❌'
            logger.info(f"{status_icon} {res['table']}: {res['success_percent']:.2f}% ({res['successful']}/{res['evaluated']})")
        
        logger.info(f"""
        ═══════════════════════════════════════════
        🎉 FASE 2 (SILVER) CONCLUÍDA!
        ═══════════════════════════════════════════
        
        ✅ Conquistas:
        - 8 tabelas Silver criadas
        - Transformações técnicas aplicadas
        - Dados exportados para GCS (Parquet)
        - 4 Expectation Suites criadas
        - Validações executadas
        - Data Docs gerados
        
        📚 Data Docs disponíveis em:
        {GE_ROOT_DIR}/uncommitted/data_docs/local_site/index.html
        
        🎯 Próximos Passos:
        1. Revisar Data Docs (relatório HTML)
        2. Iniciar Fase 3: Gold Layer
        3. Implementar métricas de negócio
        
        🎊 PARABÉNS! Silver Layer 100% completa!
        """)
        
        return {
            'total_evaluated': total_evaluated,
            'total_successful': total_successful,
            'total_unsuccessful': total_unsuccessful,
            'success_rate': overall_success_rate,
            'status': 'success'
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar Data Docs: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Definição da DAG
with DAG(
    dag_id='26_run_great_expectations_validations_silver',
    default_args=default_args,
    description='[QUALITY] Executar validações Great Expectations + gerar Data Docs (Silver)',
    schedule_interval=None,  # Execução manual (pode rodar múltiplas vezes)
    start_date=datetime(2025, 1, 29),
    catchup=False,
    tags=['fase-2', 'silver', 'data-quality', 'great-expectations', 'validations', 'final'],
) as dag:
    
    # Tasks de validação (PARALELAS - mais rápido!)
    task_validate_customers = PythonOperator(
        task_id='validate_customers',
        python_callable=validate_customers,
    )
    
    task_validate_orders = PythonOperator(
        task_id='validate_orders',
        python_callable=validate_orders,
    )
    
    task_validate_products = PythonOperator(
        task_id='validate_products',
        python_callable=validate_products,
    )
    
    task_validate_order_items = PythonOperator(
        task_id='validate_order_items',
        python_callable=validate_order_items,
    )
    
    # Task final: gerar Data Docs
    task_build_docs = PythonOperator(
        task_id='build_data_docs',
        python_callable=build_data_docs,
        provide_context=True,
    )
    
    # Pipeline: Validações em PARALELO → Data Docs
    [
        task_validate_customers,
        task_validate_orders,
        task_validate_products,
        task_validate_order_items
    ] >> task_build_docs
