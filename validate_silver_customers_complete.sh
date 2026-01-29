#!/bin/bash
# ============================================
# VALIDAÇÃO COMPLETA: SILVER CUSTOMERS
# ============================================
# Execute: bash validate_silver_customers.sh
# ============================================

echo "🔍 VALIDAÇÃO COMPLETA DA SILVER CUSTOMERS"
echo "=========================================="
echo ""

# 1. Verificar tabela existe
echo "1️⃣ Verificando se tabela existe..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "\dt olist_silver.customers"
echo ""

# 2. Comparar volumetria
echo "2️⃣ Comparando Bronze vs Silver..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT 
    'Bronze' AS layer, COUNT(*) AS records FROM olist_raw.customers
UNION ALL
SELECT 
    'Silver' AS layer, COUNT(*) AS records FROM olist_silver.customers;
"
echo ""

# 3. Verificar colunas
echo "3️⃣ Verificando colunas criadas..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'olist_silver' 
AND table_name = 'customers'
ORDER BY ordinal_position;
"
echo ""

# 4. Enriquecimento geográfico
echo "4️⃣ Verificando enriquecimento geográfico..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT 
    COUNT(*) AS total,
    SUM(CASE WHEN has_geolocation = TRUE THEN 1 ELSE 0 END) AS with_geo,
    ROUND(SUM(CASE WHEN has_geolocation = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_geo
FROM olist_silver.customers;
"
echo ""

# 5. Sample de dados
echo "5️⃣ Exemplo de dados (3 registros)..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT 
    customer_id,
    customer_state,
    customer_city,
    ROUND(geolocation_lat::numeric, 2) AS lat,
    ROUND(geolocation_lng::numeric, 2) AS lng,
    has_geolocation
FROM olist_silver.customers
WHERE has_geolocation = TRUE
LIMIT 3;
"
echo ""

# 6. Verificar índices
echo "6️⃣ Verificando índices criados..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT indexname 
FROM pg_indexes 
WHERE schemaname = 'olist_silver' 
AND tablename = 'customers'
ORDER BY indexname;
"
echo ""

# 7. Integridade (duplicatas)
echo "7️⃣ Verificando integridade (duplicatas)..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT 
    COUNT(*) AS total_records,
    COUNT(DISTINCT customer_id) AS unique_ids,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT customer_id) THEN '✅ OK - Sem duplicatas'
        ELSE '❌ ERRO - Duplicatas encontradas!'
    END AS status
FROM olist_silver.customers;
"
echo ""

# 8. Top 5 estados
echo "8️⃣ Top 5 estados (distribuição)..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT 
    customer_state,
    COUNT(*) AS total
FROM olist_silver.customers
GROUP BY customer_state
ORDER BY total DESC
LIMIT 5;
"
echo ""

# Resumo final
echo "=========================================="
echo "✅ VALIDAÇÃO CONCLUÍDA!"
echo "=========================================="
echo ""
echo "Se todos os checks acima passaram:"
echo "✅ Tabela existe"
echo "✅ Volumetria correta (99.441 registros)"
echo "✅ 11 colunas criadas"
echo "✅ Enriquecimento geográfico (~19%)"
echo "✅ 5 índices criados"
echo "✅ Sem duplicatas"
echo "✅ Distribuição geográfica OK"
echo ""
echo "🚀 PRONTO PARA PRÓXIMA DAG (orders)!"
echo ""
