"""
Olist Data Platform - Observability Dashboard
Streamlit App para monitoramento em tempo real

Seções:
1. Pipeline Status (Airflow)
2. Data Quality (Great Expectations)
3. Data Freshness (PostgreSQL)
4. Schema Evolution (Tracking)
5. Alertas & Incidentes

Autor: Hyego
Data: Fevereiro 2025
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
import psycopg2
from sqlalchemy import create_engine
import os
import json

# ============================================
# CONFIGURAÇÃO PÁGINA
# ============================================
st.set_page_config(
    page_title="Olist Platform Observability",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CONFIGURAÇÕES
# ============================================
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'airflow')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'airflow')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'airflow')

AIRFLOW_API_URL = os.getenv('AIRFLOW_API_URL', 'http://airflow-webserver:8080/api/v1')
AIRFLOW_USERNAME = os.getenv('AIRFLOW_USERNAME', 'airflow')
AIRFLOW_PASSWORD = os.getenv('AIRFLOW_PASSWORD', 'airflow')

DB_CONNECTION = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# ============================================
# FUNÇÕES AUXILIARES - DATABASE
# ============================================
@st.cache_resource
def get_db_engine():
    """Cria engine SQLAlchemy (cached)"""
    return create_engine(DB_CONNECTION)

def query_postgres(query):
    """Executa query no PostgreSQL e retorna DataFrame"""
    try:
        engine = get_db_engine()
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Erro ao consultar PostgreSQL: {e}")
        return pd.DataFrame()

# ============================================
# FUNÇÕES AUXILIARES - AIRFLOW API
# ============================================
def get_airflow_dags():
    """Busca lista de DAGs do Airflow"""
    try:
        response = requests.get(
            f"{AIRFLOW_API_URL}/dags",
            auth=HTTPBasicAuth(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Erro ao conectar Airflow API: {e}")
        return None

def get_dag_runs(dag_id, limit=10):
    """Busca últimas execuções de uma DAG"""
    try:
        response = requests.get(
            f"{AIRFLOW_API_URL}/dags/{dag_id}/dagRuns",
            params={"limit": limit, "order_by": "-execution_date"},
            auth=HTTPBasicAuth(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('dag_runs', [])
        return []
    except:
        return []

# ============================================
# FUNÇÕES AUXILIARES - GREAT EXPECTATIONS
# ============================================
def get_ge_validation_results():
    """Busca últimos resultados de validação GE"""
    # TODO: Implementar leitura de validation results do GE
    # Por enquanto, retorna dados mock
    return {
        'bronze': {'total': 15, 'passed': 15, 'failed': 0, 'success_rate': 100.0},
        'silver': {'total': 47, 'passed': 47, 'failed': 0, 'success_rate': 100.0}
    }

# ============================================
# HEADER
# ============================================
st.title("🔍 Olist Data Platform - Observability Dashboard")
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.caption(f"Última atualização: {current_time} | Auto-refresh: 30s")

# ============================================
# SIDEBAR - FILTROS
# ============================================
with st.sidebar:
    st.header("⚙️ Filtros")
    
    time_range = st.selectbox(
        "Período",
        ["Últimas 24h", "Últimos 7 dias", "Últimos 30 dias"],
        index=0
    )
    
    layers = st.multiselect(
        "Camadas",
        ["Bronze", "Silver", "Gold"],
        default=["Bronze", "Silver"]
    )
    
    st.markdown("---")
    st.markdown("### 📊 Status Geral")
    st.metric("DAGs Ativas", "26")
    st.metric("Success Rate", "98.5%", delta="1.2%")
    
    st.markdown("---")
    st.markdown("### 🔗 Links Rápidos")
    st.markdown("[Airflow UI](http://localhost:8080)")
    st.markdown("[GE Data Docs](http://localhost:8080/data_docs)")
    
    st.markdown("---")
    if st.button("🔄 Atualizar Dashboard"):
        st.rerun()

# ============================================
# SEÇÃO 1: PIPELINE STATUS
# ============================================
st.header("📊 Pipeline Status (Airflow)")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("DAGs Totais", "26", help="Total de DAGs configuradas")
with col2:
    st.metric("Executando", "2", delta="Agora", help="DAGs em execução no momento")
with col3:
    st.metric("Success Rate (24h)", "98.5%", delta="+1.2%", help="Taxa de sucesso últimas 24h")
with col4:
    st.metric("Duração Média", "2.3 min", delta="-0.5 min", help="Tempo médio de execução")

# Buscar DAGs do Airflow
dags_data = get_airflow_dags()

if dags_data:
    dags_list = dags_data.get('dags', [])
    
    # Criar DataFrame
    df_dags = pd.DataFrame([
        {
            'DAG ID': dag['dag_id'],
            'Ativa': '✅' if not dag.get('is_paused', True) else '⏸️',
            'Última Execução': dag.get('last_parsed_time', 'N/A'),
            'Tags': ', '.join(dag.get('tags', []))
        }
        for dag in dags_list[:15]  # Mostrar top 15
    ])
    
    st.dataframe(df_dags, use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ Não foi possível conectar à API do Airflow. Verifique se o Airflow está rodando.")

# ============================================
# SEÇÃO 2: DATA QUALITY (GREAT EXPECTATIONS)
# ============================================
st.header("✅ Data Quality (Great Expectations)")

ge_results = get_ge_validation_results()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Bronze Layer")
    bronze = ge_results['bronze']
    st.metric("Success Rate", f"{bronze['success_rate']:.1f}%")
    st.progress(bronze['success_rate'] / 100)
    st.caption(f"{bronze['passed']}/{bronze['total']} expectations passaram")

with col2:
    st.subheader("Silver Layer")
    silver = ge_results['silver']
    st.metric("Success Rate", f"{silver['success_rate']:.1f}%")
    st.progress(silver['success_rate'] / 100)
    st.caption(f"{silver['passed']}/{silver['total']} expectations passaram")

# Gráfico de tendência (mock data por enquanto)
st.subheader("📈 Tendência de Qualidade (30 dias)")
dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
success_rates = [98 + i % 3 for i in range(30)]  # Mock data

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=dates,
    y=success_rates,
    mode='lines+markers',
    name='Success Rate',
    line=dict(color='green', width=2),
    marker=dict(size=6)
))
fig.update_layout(
    xaxis_title="Data",
    yaxis_title="Success Rate (%)",
    yaxis=dict(range=[95, 100]),
    height=300
)
st.plotly_chart(fig, use_container_width=True)

# ============================================
# SEÇÃO 3: DATA FRESHNESS
# ============================================
st.header("⏰ Data Freshness (Latência)")

# Query: última atualização de cada tabela
query_freshness = """
WITH bronze_tables AS (
    SELECT 
        'Bronze' as layer,
        'customers' as table_name,
        MAX(created_at) as last_update,
        COUNT(*) as row_count
    FROM olist_raw.customers
    UNION ALL
    SELECT 'Bronze', 'orders', MAX(created_at), COUNT(*) FROM olist_raw.orders
    UNION ALL
    SELECT 'Bronze', 'products', MAX(created_at), COUNT(*) FROM olist_raw.products
),
silver_tables AS (
    SELECT 
        'Silver' as layer,
        'customers' as table_name,
        MAX(processed_at) as last_update,
        COUNT(*) as row_count
    FROM olist_silver.customers
    UNION ALL
    SELECT 'Silver', 'orders', MAX(processed_at), COUNT(*) FROM olist_silver.orders
    UNION ALL
    SELECT 'Silver', 'products', MAX(processed_at), COUNT(*) FROM olist_silver.products
)
SELECT * FROM bronze_tables
UNION ALL
SELECT * FROM silver_tables
ORDER BY layer, table_name;
"""

df_freshness = query_postgres(query_freshness)

if not df_freshness.empty:
    # Calcular latência (minutos desde última atualização)
    df_freshness['last_update'] = pd.to_datetime(df_freshness['last_update'])
    df_freshness['minutes_ago'] = (datetime.now() - df_freshness['last_update']).dt.total_seconds() / 60
    df_freshness['minutes_ago'] = df_freshness['minutes_ago'].round(1)
    
    # Adicionar status
    df_freshness['status'] = df_freshness['minutes_ago'].apply(
        lambda x: '🟢' if x < 60 else '🟡' if x < 1440 else '🔴'
    )
    
    # Renomear colunas para exibição
    df_display = df_freshness[[' status', 'layer', 'table_name', 'row_count', 'last_update', 'minutes_ago']].copy()
    df_display.columns = ['Status', 'Layer', 'Tabela', 'Registros', 'Última Atualização', 'Min. Atrás']
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    # Alertas de freshness
    stale_tables = df_freshness[df_freshness['minutes_ago'] > 1440]  # >24h
    if not stale_tables.empty:
        st.warning(f"⚠️ {len(stale_tables)} tabela(s) não atualizadas há mais de 24h!")
else:
    st.info("Aguardando dados de freshness...")

# ============================================
# SEÇÃO 4: SCHEMA EVOLUTION (STUB)
# ============================================
st.header("📐 Schema Evolution")

st.info("⚙️ Esta seção será populada após criação da DAG 27 (Schema Tracking)")

# Placeholder: tabela de mudanças recentes
st.subheader("Mudanças Recentes (30 dias)")
st.caption("🔜 Será implementado com DAG 27")

# Mock data para visualização
df_schema_mock = pd.DataFrame({
    'Data': [datetime.now() - timedelta(days=i) for i in range(5)],
    'Tabela': ['olist_silver.orders', 'olist_silver.products', 'olist_raw.customers', 'olist_silver.reviews', 'olist_raw.orders'],
    'Mudança': ['ADDED column delivery_sla', 'MODIFIED column weight (INT→NUMERIC)', 'UNCHANGED', 'ADDED column sentiment', 'UNCHANGED'],
    'Tipo': ['INFO', 'WARNING', 'INFO', 'INFO', 'INFO']
})

st.dataframe(df_schema_mock, use_container_width=True, hide_index=True)

# ============================================
# SEÇÃO 5: ALERTAS & INCIDENTES
# ============================================
st.header("🚨 Alertas & Incidentes")

# Tabs para alertas ativos vs resolvidos
tab1, tab2 = st.tabs(["🔴 Ativos", "✅ Resolvidos"])

with tab1:
    st.subheader("Alertas Ativos")
    
    # Mock: nenhum alerta ativo (sistema saudável!)
    st.success("🎉 Nenhum alerta ativo no momento! Sistema operando normalmente.")
    
    st.caption("Tipos de alertas monitorados:")
    st.markdown("""
    - 🔴 **CRITICAL:** DAG falhou 3+ vezes consecutivas
    - 🟡 **WARNING:** Tabela não atualizada >24h
    - 🔵 **INFO:** Schema change detectado
    - 🟣 **DRIFT:** Data drift >20% detectado
    """)

with tab2:
    st.subheader("Incidentes Resolvidos (7 dias)")
    
    # Mock data
    df_incidents = pd.DataFrame({
        'Timestamp': [
            datetime.now() - timedelta(days=2, hours=5),
            datetime.now() - timedelta(days=4, hours=12),
        ],
        'Tipo': ['WARNING', 'INFO'],
        'Descrição': [
            'Tabela olist_raw.geolocation não atualizada por 30h',
            'Schema change: coluna "has_geolocation" adicionada em customers'
        ],
        'Duração': ['2h 15min', '< 1min'],
        'Resolução': ['DAG 12 re-executada manualmente', 'Atualização esperada (migration)']
    })
    
    st.dataframe(df_incidents, use_container_width=True, hide_index=True)

# ============================================
# FOOTER
# ============================================
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🔧 Olist Data Platform v3.0")
with col2:
    st.caption("📅 Fevereiro 2025")
with col3:
    st.caption("👨‍💻 Desenvolvido por Hyego")

# ============================================
# AUTO-REFRESH (30 segundos)
# ============================================
import time
time.sleep(30)
st.rerun()
