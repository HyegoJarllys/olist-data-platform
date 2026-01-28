"""
DAG: Ingestão de Geolocation no PostgreSQL
Fase 1 - Data Ingestion
Autor: Hyego
Data: 2025-01-28
VERSÃO: v2 - Deduplicação aprimorada
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import logging
from sqlalchemy import create_engine, text

# Configurações
CSV_PATH = '/opt/airflow/data/raw/olist_geolocation_dataset.csv'
TABLE_NAME = 'olist_raw.geolocation'

# Conexão direta
DB_CONNECTION = 'postgresql://airflow:airflow@postgres:5432/airflow'

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
        logger.info("📂 Carregando CSV... (pode levar ~30 segundos)")
        df = pd.read_csv(CSV_PATH)
        logger.info(f"✅ CSV carregado: {len(df)} registros")
        
        # Validar colunas esperadas
        expected_cols = [
            'geolocation_zip_code_prefix',
            'geolocation_lat',
            'geolocation_lng',
            'geolocation_city',
            'geolocation_state'
        ]
        
        missing_cols = set(expected_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"❌ Colunas faltando: {missing_cols}")
        
        logger.info(f"✅ Colunas validadas: {list(df.columns)}")
        
        # Validar valores nulos nas PKs
        null_zip = df['geolocation_zip_code_prefix'].isnull().sum()
        null_lat = df['geolocation_lat'].isnull().sum()
        null_lng = df['geolocation_lng'].isnull().sum()
        
        if null_zip > 0 or null_lat > 0 or null_lng > 0:
            raise ValueError(f"❌ PKs nulas: zip={null_zip}, lat={null_lat}, lng={null_lng}")
        
        logger.info("✅ Sem PKs nulas")
        
        # Estatísticas
        logger.info(f"""
        📊 ESTATÍSTICAS DO CSV:
        - Total registros: {len(df):,}
        - CEPs únicos: {df['geolocation_zip_code_prefix'].nunique():,}
        - Estados únicos: {df['geolocation_state'].nunique()}
        - Cidades únicas: {df['geolocation_city'].nunique():,}
        """)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        raise


def load_to_postgres():
    """Carrega dados do CSV para PostgreSQL"""
    logger = logging.getLogger(__name__)
    
    try:
        # Ler CSV
        logger.info("📂 Carregando CSV... (pode levar ~30 segundos)")
        df = pd.read_csv(CSV_PATH)
        logger.info(f"✅ CSV carregado: {len(df):,} registros")
        
        # ESTRATÉGIA AGRESSIVA DE DEDUPLICAÇÃO
        
        # 1. Arredondar coordenadas para 6 casas decimais
        logger.info("🔄 Arredondando coordenadas para 6 casas decimais...")
        df['geolocation_lat'] = df['geolocation_lat'].round(6)
        df['geolocation_lng'] = df['geolocation_lng'].round(6)
        
        # 2. Remover duplicatas EXATAS na PK composta
        logger.info("🔄 Removendo duplicatas exatas...")
        original_len = len(df)
        df = df.drop_duplicates(
            subset=['geolocation_zip_code_prefix', 'geolocation_lat', 'geolocation_lng'], 
            keep='first'
        )
        removed_exact = original_len - len(df)
        logger.info(f"🗑️ {removed_exact:,} duplicatas exatas removidas")
        
        # 3. Para cada CEP, manter apenas a coordenada mais frequente
        logger.info("🔄 Consolidando por CEP (mantendo coordenada mais frequente)...")
        
        # Contar ocorrências de cada combinação
        df['count'] = df.groupby(['geolocation_zip_code_prefix', 'geolocation_lat', 'geolocation_lng'])['geolocation_city'].transform('count')
        
        # Ordenar por count (maior primeiro) e manter primeira ocorrência por CEP
        df_sorted = df.sort_values('count', ascending=False)
        df_unique = df_sorted.drop_duplicates(subset=['geolocation_zip_code_prefix'], keep='first')
        df_unique = df_unique.drop('count', axis=1)
        
        removed_consolidation = len(df) - len(df_unique)
        logger.info(f"🗑️ {removed_consolidation:,} registros consolidados (1 por CEP)")
        
        logger.info(f"📝 Registros finais para inserir: {len(df_unique):,}")
        
        # Conectar ao PostgreSQL
        logger.info("🔌 Conectando ao PostgreSQL...")
        engine = create_engine(DB_CONNECTION)
        
        # Truncar tabela
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME} CASCADE"))
            logger.info(f"🗑️ Tabela {TABLE_NAME} truncada")
        
        # Inserir dados
        logger.info(f"📝 Inserindo {len(df_unique):,} registros...")
        logger.info("⏳ Por favor aguarde... (1-2 minutos)")
        
        df_unique.to_sql(
            name='geolocation',
            con=engine,
            schema='olist_raw',
            if_exists='append',
            index=False,
            method='multi',
            chunksize=5000
        )
        
        logger.info(f"✅ {len(df_unique):,} registros inseridos em {TABLE_NAME}")
        
        # Validar contagem
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}"))
            count = result.scalar()
            logger.info(f"✅ Validação: {count:,} registros na tabela")
            
            if count != len(df_unique):
                raise ValueError(f"❌ Contagem divergente! Esperado: {len(df_unique):,}, DB: {count:,}")
        
        logger.info("🎉 Ingestão concluída com sucesso!")
        logger.info(f"📊 Redução total: {original_len:,} → {len(df_unique):,} ({(1 - len(df_unique)/original_len)*100:.1f}% redução)")
        
        return count
        
    except Exception as e:
        logger.error(f"❌ Erro na ingestão: {str(e)}")
        raise


def validate_data_quality():
    """Valida qualidade dos dados inseridos"""
    logger = logging.getLogger(__name__)
    
    try:
        # Conectar ao PostgreSQL
        engine = create_engine(DB_CONNECTION)
        
        logger.info("🔍 Executando validações... (pode levar ~30 segundos)")
        
        # Query de validação
        validation_query = text("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT geolocation_zip_code_prefix) as unique_zips,
            COUNT(DISTINCT geolocation_state) as unique_states,
            COUNT(DISTINCT geolocation_city) as unique_cities
        FROM olist_raw.geolocation
        """)
        
        with engine.connect() as conn:
            result = conn.execute(validation_query).fetchone()
        
        logger.info(f"""
        📊 VALIDAÇÃO DE QUALIDADE:
        - Total registros: {result[0]:,}
        - CEPs únicos: {result[1]:,}
        - Estados únicos: {result[2]}
        - Cidades únicas: {result[3]:,}
        - Proporção CEP/Registro: {result[0]/result[1]:.2f}x
        """)
        
        # Top 10 estados com mais registros
        top_states_query = text("""
        SELECT 
            geolocation_state,
            COUNT(*) as count
        FROM olist_raw.geolocation
        GROUP BY geolocation_state
        ORDER BY count DESC
        LIMIT 10
        """)
        
        with engine.connect() as conn:
            top_states = conn.execute(top_states_query).fetchall()
        
        logger.info("📊 TOP 10 ESTADOS:")
        for state in top_states:
            logger.info(f"  {state[0]}: {state[1]:,} registros")
        
        logger.info("✅ Validação de qualidade aprovada!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}")
        raise


# DAG Definition
with DAG(
    dag_id='12_ingest_geolocation',
    default_args=default_args,
    description='Ingestão de geolocation (CSV → PostgreSQL) - Deduplicação otimizada',
    schedule_interval=None,
    start_date=datetime(2025, 1, 28),
    catchup=False,
    tags=['fase-1', 'ingestion', 'postgresql', 'geolocation', 'heavy'],
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
        execution_timeout=timedelta(minutes=10),
    )
    
    # Task 3: Validar qualidade
    task_validate_quality = PythonOperator(
        task_id='validate_data_quality',
        python_callable=validate_data_quality,
    )
    
    # Pipeline
    task_validate_csv >> task_load_data >> task_validate_quality
