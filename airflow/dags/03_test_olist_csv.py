from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
import os

def test_read_csv(**context):
    """Testa leitura dos CSVs do Olist"""
    
    data_path = '/opt/airflow/data/raw'
    
    csv_files = [
        'olist_customers_dataset.csv',
        'olist_orders_dataset.csv',
        'olist_order_items_dataset.csv',
    ]
    
    print("=" * 60)
    print("📂 TESTANDO LEITURA DOS CSVs DO OLIST")
    print("=" * 60)
    
    for csv_file in csv_files:
        file_path = os.path.join(data_path, csv_file)
        
        try:
            # Ler apenas 5 linhas (teste rápido)
            df = pd.read_csv(file_path, nrows=5)
            
            print(f"\n✅ {csv_file}")
            print(f"   Colunas: {list(df.columns)}")
            print(f"   Shape: {df.shape}")
            print(f"   Primeiras linhas:")
            print(df.head(2).to_string(index=False))
            
        except Exception as e:
            print(f"\n❌ Erro ao ler {csv_file}: {e}")
    
    print("\n" + "=" * 60)
    print("✅ TESTE CONCLUÍDO!")
    print("=" * 60)

with DAG(
    '03_test_olist_csv',
    schedule_interval=None,  # Manual
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['test', 'olist', 'csv'],
    description='Testa leitura dos CSVs do Olist',
) as dag:

    test_task = PythonOperator(
        task_id='test_read_olist_csv',
        python_callable=test_read_csv,
    )
