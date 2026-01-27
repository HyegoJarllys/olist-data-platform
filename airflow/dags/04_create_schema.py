from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime
import os

def read_sql_file():
    """Le o arquivo SQL e retorna como string"""
    sql_path = '/opt/airflow/src/database/schema_clean.sql'
    with open(sql_path, 'r') as f:
        return f.read()

def create_tables(**context):
    """Cria tabelas executando SQL"""
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Ler SQL
    sql_content = read_sql_file()
    
    print("=" * 60)
    print("EXECUTANDO SQL PARA CRIAR TABELAS")
    print("=" * 60)
    print(f"SQL tem {len(sql_content)} caracteres")
    
    # Executar SQL
    pg_hook.run(sql_content)
    
    print("=" * 60)
    print("✅ SQL EXECUTADO COM SUCESSO!")
    print("=" * 60)

def validate_tables(**context):
    """Valida que todas as 9 tabelas foram criadas"""
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    expected_tables = [
        'customers', 'sellers', 'products', 
        'product_category_name_translation', 'geolocation',
        'orders', 'order_items', 'order_payments', 'order_reviews'
    ]
    
    print("=" * 60)
    print("VALIDANDO CRIACAO DAS TABELAS")
    print("=" * 60)
    
    query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """
    
    tables = pg_hook.get_records(query)
    table_names = [t[0] for t in tables]
    
    print(f"\nTabelas encontradas: {len(table_names)}")
    print(table_names)
    
    for table in expected_tables:
        if table in table_names:
            print(f"✅ {table}")
        else:
            print(f"❌ {table} - NAO ENCONTRADA!")
            raise ValueError(f"Tabela {table} nao foi criada!")
    
    print("\n" + "=" * 60)
    print(f"✅ SUCESSO! {len(expected_tables)} tabelas criadas!")
    print("=" * 60)

with DAG(
    '04_create_schema',
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['setup', 'schema', 'postgres'],
    description='Cria schema PostgreSQL (9 tabelas Olist)',
) as dag:

    create = PythonOperator(
        task_id='create_tables',
        python_callable=create_tables,
    )

    validate = PythonOperator(
        task_id='validate_tables',
        python_callable=validate_tables,
    )

    create >> validate