"""
DAG: Setup Great Expectations for Silver Layer
Fase 2 - Data Quality - Silver Layer
Autor: Hyego
Data: 2025-01-29

RESPONSABILIDADE DESTA DAG:
- Configurar Great Expectations para Silver Layer
- Criar/atualizar Data Context
- Configurar datasource PostgreSQL (olist_silver schema)
- Preparar ambiente para validações Silver

IMPORTANTE:
- Executar UMA VEZ apenas
- Depois rodar DAG 25 (create suites) e DAG 26 (run validations)
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
    'retry_delay': timedelta(minutes=2),
}

GE_ROOT_DIR = "/opt/airflow/great_expectations"
DB_CONNECTION = "postgresql://airflow:airflow@postgres:5432/airflow"


def setup_great_expectations_silver():
    """
    Configura Great Expectations para validar Silver Layer.
    
    Passos:
    1. Verificar se contexto existe (da Bronze)
    2. Adicionar/atualizar datasource para Silver
    3. Configurar connection string
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔧 Iniciando setup Great Expectations para Silver Layer...")
        
        from great_expectations.data_context import FileDataContext
        
        # ============================================
        # PASSO 1: Carregar contexto existente
        # ============================================
        logger.info(f"📂 Carregando contexto de: {GE_ROOT_DIR}")
        
        if not os.path.exists(GE_ROOT_DIR):
            logger.error(f"❌ Diretório Great Expectations não existe: {GE_ROOT_DIR}")
            logger.error("❌ Execute primeiro as DAGs da Fase 1 (Bronze)!")
            raise Exception("Great Expectations não foi configurado (Fase 1 ausente)")
        
        context = FileDataContext(context_root_dir=GE_ROOT_DIR)
        logger.info("✅ Contexto Great Expectations carregado com sucesso!")
        
        # ============================================
        # PASSO 2: Configurar datasource para SILVER
        # ============================================
        datasource_name = "postgres_silver_datasource"
        
        logger.info(f"🔧 Configurando datasource: {datasource_name}")
        
        # Verificar se datasource já existe
        try:
            existing_datasource = context.get_datasource(datasource_name)
            logger.info(f"⚠️  Datasource {datasource_name} já existe. Recriando...")
            # Não há método direto para deletar, então vamos sobrescrever
        except:
            logger.info(f"✅ Datasource {datasource_name} não existe. Criando novo...")
        
        # Configuração do datasource para SILVER
        datasource_config = {
            "name": datasource_name,
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
        
        # Adicionar datasource
        context.add_datasource(**datasource_config)
        logger.info(f"✅ Datasource {datasource_name} configurado!")
        
        # ============================================
        # PASSO 3: Testar conexão
        # ============================================
        logger.info("🧪 Testando conexão com Silver schema...")
        
        from great_expectations.core.batch import RuntimeBatchRequest
        
        test_batch_request = RuntimeBatchRequest(
            datasource_name=datasource_name,
            data_connector_name="default_runtime_data_connector",
            data_asset_name="test_silver",
            runtime_parameters={
                "query": "SELECT COUNT(*) as total FROM olist_silver.customers LIMIT 1"
            },
            batch_identifiers={"default_identifier_name": "test_batch"},
        )
        
        # Tentar obter batch
        validator = context.get_validator(
            batch_request=test_batch_request,
            create_expectation_suite_with_name="test_suite_silver"
        )
        
        logger.info("✅ Conexão com Silver testada com sucesso!")
        
        # Deletar suite de teste
        try:
            context.delete_expectation_suite("test_suite_silver")
            logger.info("🗑️  Suite de teste removida")
        except:
            pass
        
        # ============================================
        # PASSO 4: Listar datasources disponíveis
        # ============================================
        logger.info("📋 Datasources disponíveis após setup:")
        datasources = context.list_datasources()
        for ds in datasources:
            logger.info(f"   - {ds['name']}")
        
        # ============================================
        # RESUMO FINAL
        # ============================================
        logger.info(f"""
        ═══════════════════════════════════════════
        ✅ SETUP GREAT EXPECTATIONS SILVER CONCLUÍDO!
        ═══════════════════════════════════════════
        
        📊 Configuração:
        - Contexto: {GE_ROOT_DIR}
        - Datasource Silver: {datasource_name}
        - Schema: olist_silver
        - Connection: PostgreSQL (airflow database)
        
        🎯 Próximos Passos:
        1. Executar DAG 25: Create Expectation Suites (Silver)
        2. Executar DAG 26: Run Validations (Silver)
        
        ✅ Ambiente pronto para validações Silver!
        """)
        
        return {
            'status': 'success',
            'datasource': datasource_name,
            'context_dir': GE_ROOT_DIR
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no setup: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Definição da DAG
with DAG(
    dag_id='24_setup_great_expectations_silver',
    default_args=default_args,
    description='[QUALITY] Setup Great Expectations para Silver Layer',
    schedule_interval=None,  # Execução manual (uma vez)
    start_date=datetime(2025, 1, 29),
    catchup=False,
    tags=['fase-2', 'silver', 'data-quality', 'great-expectations', 'setup'],
) as dag:
    
    task_setup_ge_silver = PythonOperator(
        task_id='setup_great_expectations_silver',
        python_callable=setup_great_expectations_silver,
    )
