#!/bin/bash
# ============================================
# VALIDAÇÃO COMPLETA: SILVER PRODUCTS
# ============================================
# Execute: bash validate_silver_products.sh
# ============================================

echo "🔍 VALIDAÇÃO COMPLETA DA SILVER PRODUCTS"
echo "=========================================="
echo ""

# 1. Verificar tabela existe
echo "1️⃣ Verificando se tabela existe..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "\dt olist_silver.products"
echo ""

# 2. Comparar volumetria
echo "2️⃣ Comparando Bronze vs Silver..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT 
    'Bronze' AS layer, COUNT(*) AS records FROM olist_raw.products
UNION ALL
SELECT 
    'Silver' AS layer, COUNT(*) AS records FROM olist_silver.products;
"
echo ""

# 3. Verificar colunas
echo "3️⃣ Verificando colunas criadas..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'olist_silver' 
AND table_name = 'products'
ORDER BY ordinal_position;
"
echo ""

# 4. Categorias
echo "4️⃣ Verificando distribuição de categorias..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT 
    COUNT(*) AS total,
    SUM(CASE WHEN has_category = TRUE THEN 1 ELSE 0 END) AS with_category,
    ROUND(SUM(CASE WHEN has_category = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_category,
    COUNT(DISTINCT product_category_name) AS unique_categories
FROM olist_silver.products;
"
echo ""

# 5. Dimensões físicas
echo "5️⃣ Verificando dimensões físicas..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT 
    COUNT(*) AS total,
    SUM(CASE WHEN has_weight = TRUE THEN 1 ELSE 0 END) AS with_weight,
    SUM(CASE WHEN has_dimensions = TRUE THEN 1 ELSE 0 END) AS with_dimensions,
    SUM(CASE WHEN has_photos = TRUE THEN 1 ELSE 0 END) AS with_photos,
    SUM(CASE WHEN product_volume_cm3 IS NOT NULL THEN 1 ELSE 0 END) AS with_volume
FROM olist_silver.products;
"
echo ""

# 6. Estatísticas de peso e volume
echo "6️⃣ Estatísticas de peso e volume..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT 
    ROUND(AVG(product_weight_g), 2) AS avg_weight_g,
    ROUND(MIN(product_weight_g), 2) AS min_weight_g,
    ROUND(MAX(product_weight_g), 2) AS max_weight_g,
    ROUND(AVG(product_volume_cm3), 2) AS avg_volume_cm3
FROM olist_silver.products
WHERE product_weight_g > 0;
"
echo ""

# 7. Sample de dados
echo "7️⃣ Exemplo de dados (3 registros)..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT 
    product_id,
    product_category_name,
    product_weight_g,
    ROUND(product_volume_cm3::numeric, 2) AS volume,
    has_category,
    has_dimensions
FROM olist_silver.products
WHERE has_dimensions = TRUE
LIMIT 3;
"
echo ""

# 8. Verificar índices
echo "8️⃣ Verificando índices criados..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT indexname 
FROM pg_indexes 
WHERE schemaname = 'olist_silver' 
AND tablename = 'products'
ORDER BY indexname;
"
echo ""

# 9. Integridade (duplicatas)
echo "9️⃣ Verificando integridade (duplicatas)..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT 
    COUNT(*) AS total_records,
    COUNT(DISTINCT product_id) AS unique_ids,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT product_id) THEN '✅ OK - Sem duplicatas'
        ELSE '❌ ERRO - Duplicatas encontradas!'
    END AS status
FROM olist_silver.products;
"
echo ""

# 10. Top 5 categorias
echo "🔟 Top 5 categorias..."
docker exec -it olist-data-pipeline-postgres-1 psql -U airflow -d airflow -c "
SELECT 
    product_category_name,
    COUNT(*) AS total
FROM olist_silver.products
WHERE has_category = TRUE
GROUP BY product_category_name
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
echo "✅ Volumetria correta (~32.951 registros)"
echo "✅ 18 colunas criadas"
echo "✅ Categorias distribuídas"
echo "✅ Dimensões físicas processadas"
echo "✅ Volume calculado"
echo "✅ 5 índices criados"
echo "✅ Sem duplicatas"
echo ""
echo "🚀 PRONTO PARA PRÓXIMA DAG!"
echo ""
