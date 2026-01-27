# 🚀 Crypto Data Pipeline - Financial MLOps Platform

## 📊 Visão Geral

Sistema profissional de engenharia de dados que automatiza a coleta, processamento e análise de dados de criptomoedas com Machine Learning e orquestração via Apache Airflow.

### 🎯 Objetivo

Demonstrar competências avançadas em:
- **Engenharia de Dados**: Pipeline completo (ingestão → transformação → armazenamento)
- **MLOps**: Treino automático, versionamento de modelos, A/B testing
- **Data Quality**: Validações automáticas com Great Expectations
- **IA Analytics**: Diagnóstico inteligente de falhas com LLMs

---

## 🛠️ Stack Tecnológica

| Categoria | Tecnologia | Propósito |
|-----------|-----------|-----------|
| **Orquestração** | Apache Airflow | Gerenciamento de workflows |
| **Transformação** | DBT Core | Modelagem SQL (bronze/silver/gold) |
| **Data Lake** | Google Cloud Storage | Armazenamento de dados brutos |
| **Data Warehouse** | BigQuery | Analytics e queries SQL |
| **Data Quality** | Great Expectations | Validações automáticas |
| **ML Framework** | XGBoost + Scikit-learn | Modelos preditivos |
| **ML Tracking** | MLflow | Versionamento e registry |
| **IA Analytics** | Vertex AI (Gemini) | Diagnóstico de logs |
| **Alertas** | Telegram Bot API | Notificações em tempo real |
| **Containerização** | Docker | Ambiente reproduzível |

---

## 📐 Arquitetura
```
API Bybit → Airflow → GCS (Data Lake) → BigQuery (DWH)
                ↓
          Great Expectations (Validação)
                ↓
          DBT (Transformação: bronze → silver → gold)
                ↓
          XGBoost + MLflow (Treino/Inferência)
                ↓
          Telegram (Alertas) + Gemini (IA Analytics)
```

*(Diagramas detalhados serão adicionados conforme o projeto avança)*

---

## 🎯 Features Principais

- ✅ **Ingestão automática**: Coleta dados de 4 criptomoedas em 3 timeframes (5m, 15m, 1h)
- ✅ **Data Quality**: Validações automáticas de schema, nulls, ranges
- ✅ **Feature Engineering**: Cálculo de indicadores técnicos (RSI, EMAs, VWAP, ATR)
- ✅ **MLOps completo**: Re-treino semanal, model registry, A/B testing
- ✅ **IA Analytics**: Diagnóstico automático de falhas via Gemini
- ✅ **Alertas inteligentes**: Telegram notifica sinais de trading

---

## 📅 Status do Projeto

**Fase Atual:** FASE 0 - Setup e Fundação  
**Progresso:** 🟨🟨⬜⬜⬜⬜⬜⬜⬜⬜ 20%

### Roadmap

- [x] Estrutura de pastas criada
- [x] Git inicializado
- [ ] Airflow rodando localmente
- [ ] GCP configurado
- [ ] Primeiro DAG funcionando
- [ ] Pipeline de ingestão completo
- [ ] DBT transformações
- [ ] Modelo ML treinado
- [ ] Sistema de alertas
- [ ] IA Analytics
- [ ] Documentação completa

---

## 🚀 Quick Start

*(Instruções serão adicionadas conforme o setup for concluído)*

### Pré-requisitos

- Python 3.10+
- Docker Desktop
- Conta Google Cloud Platform (free tier)
- Git

---

## 📖 Documentação

- [Arquitetura Detalhada](docs/architecture.md) *(em breve)*
- [Guia de Setup](docs/setup_guide.md) *(em breve)*
- [Airflow DAGs](docs/airflow_guide.md) *(em breve)*
- [DBT Models](docs/dbt_guide.md) *(em breve)*

---

## 👤 Autor

**Hyego Jarllys**  
Engenheiro de Dados | IA Engineer  
São Fernando, RN - Brasil

📧 [Seu Email]  
🔗 [LinkedIn](seu-linkedin)  
💻 [GitHub](https://github.com/HyegoJarllys)

---

## 📄 Licença

MIT License - Sinta-se livre para usar este projeto como referência.

---

**⚠️ Nota:** Este é um projeto educacional e de portfólio. Não deve ser usado para trading real sem validação adequada.

**Última atualização:** Janeiro 2025