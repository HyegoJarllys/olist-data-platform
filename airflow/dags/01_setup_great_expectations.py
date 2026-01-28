"""
DAG: Setup Great Expectations
Fase 1 - Data Quality
Autor: Hyego
Data: 2025-01-28
Objetivo: Inicializar e configurar Great Expectations
EXECUTE APENAS UMA VEZ!
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging
import os
import json

default_args = {
    'owner': 'hyego',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

GE_ROOT_DIR = "/opt/airflow/great_expectations"


def setup_directories():
    """Cria estrutura de diretórios para Great Expectations"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📁 Criando estrutura de diretórios...")
        
        directories = [
            GE_ROOT_DIR,
            f"{GE_ROOT_DIR}/expectations",
            f"{GE_ROOT_DIR}/checkpoints",
            f"{GE_ROOT_DIR}/plugins",
            f"{GE_ROOT_DIR}/uncommitted",
            f"{GE_ROOT_DIR}/uncommitted/data_docs",
            f"{GE_ROOT_DIR}/uncommitted/validations",
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"  ✅ {directory}")
        
        logger.info("✅ Estrutura de diretórios criada!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar diretórios: {str(e)}")
        raise


def create_config_file():
    """Cria arquivo great_expectations.yml"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📝 Criando great_expectations.yml...")
        
        config = {
            "config_version": 3.0,
            "plugins_directory": "plugins/",
            "stores": {
                "expectations_store": {
                    "class_name": "ExpectationsStore",
                    "store_backend": {
                        "class_name": "TupleFilesystemStoreBackend",
                        "base_directory": "expectations/"
                    }
                },
                "validations_store": {
                    "class_name": "ValidationsStore",
                    "store_backend": {
                        "class_name": "TupleFilesystemStoreBackend",
                        "base_directory": "uncommitted/validations/"
                    }
                },
                "evaluation_parameter_store": {
                    "class_name": "EvaluationParameterStore"
                },
                "checkpoint_store": {
                    "class_name": "CheckpointStore",
                    "store_backend": {
                        "class_name": "TupleFilesystemStoreBackend",
                        "base_directory": "checkpoints/"
                    }
                }
            },
            "expectations_store_name": "expectations_store",
            "validations_store_name": "validations_store",
            "evaluation_parameter_store_name": "evaluation_parameter_store",
            "checkpoint_store_name": "checkpoint_store",
            "data_docs_sites": {
                "local_site": {
                    "class_name": "SiteBuilder",
                    "show_how_to_buttons": True,
                    "store_backend": {
                        "class_name": "TupleFilesystemStoreBackend",
                        "base_directory": "uncommitted/data_docs/local_site/"
                    },
                    "site_index_builder": {
                        "class_name": "DefaultSiteIndexBuilder"
                    }
                }
            },
            "anonymous_usage_statistics": {
                "enabled": False
            }
        }
        
        # Converter para YAML manualmente (mais simples que instalar PyYAML)
        yaml_content = """# Great Expectations Configuration
config_version: 3.0
plugins_directory: plugins/

stores:
  expectations_store:
    class_name: ExpectationsStore
    store_backend:
      class_name: TupleFilesystemStoreBackend
      base_directory: expectations/

  validations_store:
    class_name: ValidationsStore
    store_backend:
      class_name: TupleFilesystemStoreBackend
      base_directory: uncommitted/validations/

  evaluation_parameter_store:
    class_name: EvaluationParameterStore

  checkpoint_store:
    class_name: CheckpointStore
    store_backend:
      class_name: TupleFilesystemStoreBackend
      base_directory: checkpoints/

expectations_store_name: expectations_store
validations_store_name: validations_store
evaluation_parameter_store_name: evaluation_parameter_store
checkpoint_store_name: checkpoint_store

data_docs_sites:
  local_site:
    class_name: SiteBuilder
    show_how_to_buttons: true
    store_backend:
      class_name: TupleFilesystemStoreBackend
      base_directory: uncommitted/data_docs/local_site/
    site_index_builder:
      class_name: DefaultSiteIndexBuilder

anonymous_usage_statistics:
  enabled: false
"""
        
        config_path = f"{GE_ROOT_DIR}/great_expectations.yml"
        with open(config_path, 'w') as f:
            f.write(yaml_content)
        
        logger.info(f"✅ Arquivo criado: {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar config: {str(e)}")
        raise


def verify_installation():
    """Verifica se Great Expectations está instalado corretamente"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Verificando instalação do Great Expectations...")
        
        import great_expectations as gx
        from great_expectations.data_context import FileDataContext
        
        logger.info(f"✅ Great Expectations versão: {gx.__version__}")
        
        # Tentar carregar contexto
        context = FileDataContext(context_root_dir=GE_ROOT_DIR)
        
        logger.info("✅ Contexto carregado com sucesso!")
        logger.info(f"  - Root dir: {context.root_directory}")
        logger.info(f"  - Expectations dir: {GE_ROOT_DIR}/expectations")
        logger.info(f"  - Checkpoints dir: {GE_ROOT_DIR}/checkpoints")
        
        logger.info("🎉 Great Expectations configurado com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na verificação: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id='06_setup_great_expectations',
    default_args=default_args,
    description='Configuração inicial do Great Expectations (executar UMA VEZ)',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['setup', 'great-expectations', 'one-time'],
) as dag:
    
    # Task 1: Criar diretórios
    task_setup_dirs = PythonOperator(
        task_id='setup_directories',
        python_callable=setup_directories,
    )
    
    # Task 2: Criar arquivo de configuração
    task_create_config = PythonOperator(
        task_id='create_config_file',
        python_callable=create_config_file,
    )
    
    # Task 3: Verificar instalação
    task_verify = PythonOperator(
        task_id='verify_installation',
        python_callable=verify_installation,
    )
    
    # Pipeline
    task_setup_dirs >> task_create_config >> task_verify
