# ============================================
# Dockerfile customizado do Airflow
# Adiciona Great Expectations
# ============================================

FROM apache/airflow:2.8.1-python3.10

USER root

# Instalar dependências do sistema se necessário
RUN apt-get update && apt-get install -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copiar requirements e instalar
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Criar diretório para Great Expectations
RUN mkdir -p /opt/airflow/great_expectations
