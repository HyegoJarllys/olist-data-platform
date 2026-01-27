from google.cloud import storage, bigquery
import os

# Configurar credenciais
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/opt/airflow/gcp-credentials.json'

print("=" * 50)
print("🔍 TESTANDO CONEXÃO COM GCP")
print("=" * 50)

# Teste 1: Cloud Storage
print("\n📦 Teste 1: Cloud Storage")
try:
    storage_client = storage.Client()
    buckets = list(storage_client.list_buckets())
    print(f"✅ Conectado! Buckets encontrados: {len(buckets)}")
    for bucket in buckets:
        print(f"   - {bucket.name}")
except Exception as e:
    print(f"❌ Erro: {e}")

# Teste 2: BigQuery
print("\n📊 Teste 2: BigQuery")
try:
    bq_client = bigquery.Client()
    datasets = list(bq_client.list_datasets())
    print(f"✅ Conectado! Datasets encontrados: {len(datasets)}")
    for dataset in datasets:
        print(f"   - {dataset.dataset_id}")
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n" + "=" * 50)
print("✅ TESTES CONCLUÍDOS!")
print("=" * 50)