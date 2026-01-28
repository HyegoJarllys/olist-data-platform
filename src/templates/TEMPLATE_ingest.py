"""
TEMPLATE: Ingestão de Tabelas no PostgreSQL
Fase 1 - Data Ingestion

INSTRUÇÕES DE USO:
1. Copiar este arquivo
2. Renomear para XX_ingest_<TABELA>.py
3. Ajustar CONFIGURAÇÕES abaixo
4. Ajustar expected_cols com colunas da tabela
5. Salvar em airflow/dags/
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import pandas as pd
import logging

# ============================================================
# CONFIGURAÇÕES - AJUSTAR PARA CADA TABELA
# ============================================================
CSV_FILENAME = 'olist_NOME_dataset.csv'  # ⚠️ AJUSTAR
TABLE_NAME = 'nome_tabela'                # ⚠️ AJUSTAR
DAG_ID = '0X_ingest_nome_tabela'          # ⚠️ AJUSTAR
DAG_DESCRIPTION = 'Ingestão de NOME'      # ⚠️ AJUSTAR
PRIMARY_KEY = 'id_coluna'                 # ⚠️ AJUSTAR

# Colunas esperadas no CSV (ordem não importa)
EXPECTED_COLUMNS = [
    'coluna1',  # ⚠️ AJUSTAR
    'coluna2',
    'coluna3',
]

# Foreign Keys para validar (opcional)
# Formato: {'coluna_fk': 'tabela_referenciada'}
FOREIGN_KEYS = {
    # 'customer_id': 'customers',  # Exemplo
}
# ============================================================

CSV_PATH = f'/opt/airflow/data/raw/{CSV_FILENAME}'
POSTGRES_CONN_ID = 'postgres_olist'

default_args = {
    'owner': 'hyego',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def validate_csv():
    """Valida estrutura e qualidade do CSV"""
    logger = logging.getLogger(__name__)
    
    try:
        # Ler CSV
        df = pd.read_csv(CSV_PATH)
        logger.info(f"✅ CSV carregado: {len(df):,} registros")
        
        # Validar colunas esperadas
        missing_cols = set(EXPECTED_COLUMNS) - set(df.columns)
        if missing_cols:
            raise ValueError(f"❌ Colunas faltando: {missing_cols}")
        
        extra_cols = set(df.columns) - set(EXPECTED_COLUMNS)
        if extra_cols:
            logger.warning(f"⚠️  Colunas extras (ignoradas): {extra_cols}")
        
        logger.info(f"✅ Colunas validadas: {len(EXPECTED_COLUMNS)} colunas")
        
        # Validar valores nulos em PK
        null_pks = df[PRIMARY_KEY].isnull().sum()
        if null_pks > 0:
            raise ValueError(f"❌ {null_pks} PKs nulas encontradas!")
        
        logger.info("✅ Sem PKs nulas")
        
        # Validar duplicatas em PK
        duplicates = df[PRIMARY_KEY].duplicated().sum()
        if duplicates > 0:
            logger.warning(f"⚠️  {duplicates} duplicatas encontradas - serão removidas")
        
        # Estatísticas gerais
        logger.info(f"""
        📊 ESTATÍSTICAS DO CSV:
        - Total registros: {len(df):,}
        - PKs únicas: {df[PRIMARY_KEY].nunique():,}
        - Valores nulos por coluna:
        {df.isnull().sum().to_dict()}
        """)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        raise


def load_to_postgres():
    """Carrega dados do CSV para PostgreSQL"""
    logger = logging.getLogger(__name__)
    
    try:
        # Ler CSV (apenas colunas esperadas)
        df = pd.read_csv(CSV_PATH, usecols=EXPECTED_COLUMNS)
        logger.info(f"📂 CSV carregado: {len(df):,} registros")
        
        # Remover duplicatas (manter primeira ocorrência)
        original_len = len(df)
        df = df.drop_duplicates(subset=[PRIMARY_KEY], keep='first')
        removed = original_len - len(df)
        if removed > 0:
            logger.warning(f"🗑️  {removed} duplicatas removidas")
        
        # Conectar ao PostgreSQL
        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        engine = hook.get_sqlalchemy_engine()
        
        # Truncar tabela (use CASCADE se houver dependências)
        with engine.connect() as conn:
            conn.execute(f"TRUNCATE TABLE {TABLE_NAME} CASCADE")
            conn.commit()
            logger.info(f"🗑️  Tabela {TABLE_NAME} truncada")
        
        # Inserir dados em chunks
        df.to_sql(
            name=TABLE_NAME,
            con=engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )
        
        logger.info(f"✅ {len(df):,} registros inseridos em {TABLE_NAME}")
        
        # Validar contagem
        with engine.connect() as conn:
            result = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
            count = result.scalar()
            logger.info(f"✅ Validação: {count:,} registros na tabela")
            
            if count != len(df):
                raise ValueError(f"❌ Contagem divergente! CSV: {len(df)}, DB: {count}")
        
        logger.info("🎉 Ingestão concluída com sucesso!")
        return count
        
    except Exception as e:
        logger.error(f"❌ Erro na ingestão: {str(e)}")
        raise


def validate_foreign_keys():
    """Valida integridade das Foreign Keys (se houver)"""
    logger = logging.getLogger(__name__)
    
    if not FOREIGN_KEYS:
        logger.info("ℹ️  Sem FKs para validar (tabela independente)")
        return True
    
    try:
        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        
        for fk_column, ref_table in FOREIGN_KEYS.items():
            # Query para detectar órfãos
            orphan_query = f"""
            SELECT COUNT(*) 
            FROM {TABLE_NAME} t
            LEFT JOIN {ref_table} r ON t.{fk_column} = r.{fk_column}
            WHERE r.{fk_column} IS NULL
              AND t.{fk_column} IS NOT NULL;
            """
            
            orphans = hook.get_first(orphan_query)[0]
            
            if orphans > 0:
                raise ValueError(
                    f"❌ {orphans} registros órfãos! "
                    f"FK: {fk_column} → {ref_table}"
                )
            
            logger.info(f"✅ FK válida: {fk_column} → {ref_table} (0 órfãos)")
        
        logger.info("✅ Todas FKs validadas!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação de FKs: {str(e)}")
        raise


def validate_data_quality():
    """Valida qualidade dos dados inseridos"""
    logger = logging.getLogger(__name__)
    
    try:
        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        
        # Query de validação básica
        validation_query = f"""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT {PRIMARY_KEY}) as unique_pks,
            COUNT(CASE WHEN {PRIMARY_KEY} IS NULL THEN 1 END) as null_pks
        FROM {TABLE_NAME};
        """
        
        result = hook.get_first(validation_query)
        
        logger.info(f"""
        📊 VALIDAÇÃO DE QUALIDADE:
        - Total registros: {result[0]:,}
        - PKs únicas: {result[1]:,}
        - PKs nulas: {result[2]:,}
        """)
        
        # Validações críticas
        if result[2] > 0:  # PKs nulas
            raise ValueError(f"❌ {result[2]} PKs nulas encontradas!")
        
        if result[0] != result[1]:  # Duplicatas
            raise ValueError(
                f"❌ Duplicatas detectadas! "
                f"Total: {result[0]}, Únicos: {result[1]}"
            )
        
        logger.info("✅ Validação de qualidade aprovada!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description=DAG_DESCRIPTION,
    schedule_interval=None,  # Manual trigger
    start_date=datetime(2025, 1, 27),
    catchup=False,
    tags=['fase-1', 'ingestion', 'postgresql', TABLE_NAME],
) as dag:
    
    # Task 1: Validar CSV
    task_validate_csv = PythonOperator(
        task_id='validate_csv',
        python_callable=validate_csv,
    )
    
    # Task 2: Carregar dados
    task_load_data = PythonOperator(
        task_id='load_to_postgres',
        python_callable=load_to_postgres,
    )
    
    # Task 3: Validar FKs (somente se houver)
    if FOREIGN_KEYS:
        task_validate_fks = PythonOperator(
            task_id='validate_foreign_keys',
            python_callable=validate_foreign_keys,
        )
    
    # Task 4: Validar qualidade
    task_validate_quality = PythonOperator(
        task_id='validate_data_quality',
        python_callable=validate_data_quality,
    )
    
    # Pipeline
    if FOREIGN_KEYS:
        task_validate_csv >> task_load_data >> task_validate_fks >> task_validate_quality
    else:
        task_validate_csv >> task_load_data >> task_validate_quality
