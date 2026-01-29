"""
DAG: Forçar Build de Data Docs
Fase 1 - Data Quality
Autor: Hyego
Data: 2025-01-28
Objetivo: Gerar Data Docs HTML do Great Expectations
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

GE_ROOT_DIR = "/opt/airflow/great_expectations"


def verify_ge_structure():
    """Verifica estrutura do Great Expectations"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔍 Verificando estrutura do Great Expectations...")
        
        paths_to_check = [
            GE_ROOT_DIR,
            f"{GE_ROOT_DIR}/great_expectations.yml",
            f"{GE_ROOT_DIR}/expectations",
            f"{GE_ROOT_DIR}/uncommitted",
            f"{GE_ROOT_DIR}/uncommitted/validations",
        ]
        
        for path in paths_to_check:
            if os.path.exists(path):
                logger.info(f"✅ {path}")
            else:
                logger.warning(f"❌ {path} NÃO EXISTE!")
        
        # Listar suites
        suites_dir = f"{GE_ROOT_DIR}/expectations"
        if os.path.exists(suites_dir):
            suites = os.listdir(suites_dir)
            logger.info(f"📋 Suites encontradas: {suites}")
        
        # Listar validations
        validations_dir = f"{GE_ROOT_DIR}/uncommitted/validations"
        if os.path.exists(validations_dir):
            validations = os.listdir(validations_dir)
            logger.info(f"📊 Validations encontradas: {len(validations)} arquivos")
        
        logger.info("✅ Verificação concluída!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        raise


def force_build_data_docs():
    """Força build dos Data Docs"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🏗️ Forçando build dos Data Docs...")
        
        from great_expectations.data_context import FileDataContext
        
        # Carregar contexto
        logger.info(f"📂 Carregando contexto de: {GE_ROOT_DIR}")
        context = FileDataContext(context_root_dir=GE_ROOT_DIR)
        
        # Verificar configuração
        logger.info("📋 Configuração do contexto:")
        logger.info(f"  - Root dir: {context.root_directory}")
        logger.info(f"  - Data docs sites: {list(context.get_docs_sites_urls())}")
        
        # Build data docs
        logger.info("🔨 Executando build_data_docs()...")
        index_page_locator_infos = context.build_data_docs()
        
        logger.info(f"✅ Build concluído! Páginas geradas: {len(index_page_locator_infos)}")
        
        for site_name, locator_info in index_page_locator_infos.items():
            logger.info(f"  📄 {site_name}: {locator_info}")
        
        # Verificar se arquivos foram criados
        docs_dir = f"{GE_ROOT_DIR}/uncommitted/data_docs/local_site"
        
        if os.path.exists(docs_dir):
            logger.info(f"✅ Diretório criado: {docs_dir}")
            
            # Listar arquivos
            files = []
            for root, dirs, filenames in os.walk(docs_dir):
                for filename in filenames:
                    if filename.endswith('.html'):
                        full_path = os.path.join(root, filename)
                        files.append(full_path)
            
            logger.info(f"✅ Arquivos HTML criados: {len(files)}")
            for f in files[:10]:  # Mostrar primeiros 10
                logger.info(f"  📄 {f}")
            
            # Verificar index.html
            index_path = f"{docs_dir}/index.html"
            if os.path.exists(index_path):
                logger.info(f"✅ INDEX.HTML CRIADO: {index_path}")
                
                # Mostrar tamanho do arquivo
                size = os.path.getsize(index_path)
                logger.info(f"  📏 Tamanho: {size} bytes")
            else:
                logger.error(f"❌ index.html NÃO FOI CRIADO!")
        else:
            logger.error(f"❌ Diretório não foi criado: {docs_dir}")
        
        logger.info("🎉 Build de Data Docs concluído!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar Data Docs: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def list_data_docs_files():
    """Lista arquivos HTML gerados"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("📂 Listando arquivos Data Docs...")
        
        docs_dir = f"{GE_ROOT_DIR}/uncommitted/data_docs/local_site"
        
        if not os.path.exists(docs_dir):
            raise FileNotFoundError(f"❌ Diretório não existe: {docs_dir}")
        
        # Contar arquivos
        html_count = 0
        for root, dirs, files in os.walk(docs_dir):
            for file in files:
                if file.endswith('.html'):
                    html_count += 1
        
        logger.info(f"""
        📊 RESUMO DATA DOCS:
        - Localização: {docs_dir}
        - Arquivos HTML: {html_count}
        - Index: {docs_dir}/index.html
        
        🚀 PARA COPIAR PARA SUA MÁQUINA:
        docker cp olist-data-pipeline-airflow-webserver-1:{docs_dir} "C:\\Users\\Hyego Jarllys\\OneDrive\\Ambiente de Trabalho\\PROJETO SQL+PBI\\data_docs"
        """)
        
        logger.info("✅ Listagem concluída!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id='09_force_build_data_docs',
    default_args=default_args,
    description='Forçar build dos Data Docs do Great Expectations',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['data-quality', 'great-expectations', 'data-docs'],
) as dag:
    
    # Task 1: Verificar estrutura
    task_verify = PythonOperator(
        task_id='verify_ge_structure',
        python_callable=verify_ge_structure,
    )
    
    # Task 2: Forçar build
    task_build = PythonOperator(
        task_id='force_build_data_docs',
        python_callable=force_build_data_docs,
    )
    
    # Task 3: Listar arquivos
    task_list = PythonOperator(
        task_id='list_data_docs_files',
        python_callable=list_data_docs_files,
    )
    
    # Pipeline
    task_verify >> task_build >> task_list
