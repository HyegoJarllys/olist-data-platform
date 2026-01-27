-- =====================================================
-- OLIST E-COMMERCE DATABASE SCHEMA
-- 9 Tabelas Relacionais (PostgreSQL)
-- =====================================================

-- Tabela 1: Customers
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_unique_is VARCHAR(50),
    customer_zip_code_prefix INTEGER,
    customer_city VARCHAR(50),
    customer_state VARCHAR(10)
);

-- Tabela 2: Sellers
CREATE TABLE IF NOT EXISTS sellers (
    seller_id VARCHAR(100) PRIMARY KEY,
    seller_zip_code_prefix INTEGER,
    seller_city VARCHAR(50),
    seller_state VARCHAR(20)
);

-- Tabela 3: Products
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(100) PRIMARY KEY,
    product_category_name VARCHAR(100),
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g INTEGER,
    product_length_cm INTEGER,
    product_height_cm INTEGER,
    product_width_cm INTEGER
);

-- Tabela 4: Product Category Translation
CREATE TABLE IF NOT EXISTS product_category_name_translation (
    product_category_name VARCHAR(50),
    product_category_name_english VARCHAR(50)
);

-- Tabela 5: Geolocation
CREATE TABLE IF NOT EXISTS geolocation (
    geolocation_zip_code_prefix INTEGER,
    geolocation_lat NUMERIC(10,8),
    geolocation_lng NUMERIC(20,10),
    geolocation_city VARCHAR(50),
    geolocation_state VARCHAR(4)
);

-- Tabela 6: Orders (depende de customers)
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(100) PRIMARY KEY,
    customer_id VARCHAR(100),
    order_status VARCHAR(50),
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP,
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) 
        REFERENCES customers(customer_id)
);

-- Tabela 7: Order Items (depende de orders, products, sellers)
CREATE TABLE IF NOT EXISTS order_items (
    order_id VARCHAR(50) NOT NULL,
    order_item_id INTEGER NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    seller_id VARCHAR(50) NOT NULL,
    shipping_limit_date TIMESTAMP,
    price NUMERIC(10,2),
    freight_value NUMERIC(10,2),
    PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_items_order FOREIGN KEY (order_id) 
        REFERENCES orders(order_id),
    CONSTRAINT fk_items_product FOREIGN KEY (product_id) 
        REFERENCES products(product_id),
    CONSTRAINT fk_items_seller FOREIGN KEY (seller_id) 
        REFERENCES sellers(seller_id)
);

-- Tabela 8: Order Payments (depende de orders)
CREATE TABLE IF NOT EXISTS order_payments (
    order_id VARCHAR(50) NOT NULL,
    payment_sequential INTEGER NOT NULL,
    payment_type VARCHAR(30),
    payment_installments INTEGER,
    payment_value NUMERIC(10,2),
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_payments_order FOREIGN KEY (order_id) 
        REFERENCES orders(order_id)
);

-- Tabela 9: Order Reviews (depende de orders)
CREATE TABLE IF NOT EXISTS order_reviews (
    review_pk SERIAL PRIMARY KEY,
    review_id VARCHAR(50) UNIQUE NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    review_score INTEGER,
    review_comment_title VARCHAR(250),
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    CONSTRAINT fk_reviews_order FOREIGN KEY (order_id) 
        REFERENCES orders(order_id)
);