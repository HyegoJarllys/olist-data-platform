--
-- PostgreSQL database dump
--

\restrict AHdILO4XHW3e7rj0l9CyugfgVJHS88j9ZMNeg4arU1j1c71JbezdQ5aMjy9Ef6V

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

-- Started on 2026-01-27 15:54:14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 219 (class 1259 OID 16706)
-- Name: customers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.customers (
    customer_id character varying(50) CONSTRAINT costumers_customer_id_not_null NOT NULL,
    customer_unique_is character varying(50),
    customer_zip_code_prefix integer,
    customer_city character varying(50),
    customer_state character varying(10)
);


ALTER TABLE public.customers OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 16718)
-- Name: geolocation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.geolocation (
    geolocation_zip_code_prefix integer,
    geolocation_lat numeric(10,8),
    geolocation_lng numeric(20,10),
    geolocation_city character varying(50),
    geolocation_state character varying(4)
);


ALTER TABLE public.geolocation OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 16779)
-- Name: order_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.order_items (
    order_id character varying(50) NOT NULL,
    order_item_id integer NOT NULL,
    product_id character varying(50) NOT NULL,
    seller_id character varying(50) NOT NULL,
    shipping_limit_date timestamp without time zone,
    price numeric(10,2),
    freight_value numeric(10,2)
);


ALTER TABLE public.order_items OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 16766)
-- Name: order_payments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.order_payments (
    order_id character varying(50) NOT NULL,
    payment_sequential integer NOT NULL,
    payment_type character varying(30),
    payment_installments integer,
    payment_value numeric(10,2)
);


ALTER TABLE public.order_payments OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 16857)
-- Name: order_reviews; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.order_reviews (
    review_pk integer NOT NULL,
    review_id character varying(50) NOT NULL,
    order_id character varying(50) NOT NULL,
    review_score integer,
    review_comment_title character varying(250),
    review_comment_message text,
    review_creation_date timestamp without time zone,
    review_answer_timestamp timestamp without time zone
);


ALTER TABLE public.order_reviews OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 16856)
-- Name: order_reviews_review_pk_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.order_reviews_review_pk_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.order_reviews_review_pk_seq OWNER TO postgres;

--
-- TOC entry 4968 (class 0 OID 0)
-- Dependencies: 228
-- Name: order_reviews_review_pk_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.order_reviews_review_pk_seq OWNED BY public.order_reviews.review_pk;


--
-- TOC entry 224 (class 1259 OID 16746)
-- Name: orders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.orders (
    order_id character varying(100) NOT NULL,
    customer_id character varying(100),
    order_status character varying(50),
    order_purchase_timestamp timestamp without time zone,
    order_approved_at timestamp without time zone,
    order_delivered_carrier_date timestamp without time zone,
    order_delivered_customer_date timestamp without time zone,
    order_estimated_delivery_date timestamp without time zone
);


ALTER TABLE public.orders OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 16759)
-- Name: payments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payments (
    order_id character varying(50) NOT NULL,
    payment_sequential integer,
    payment_type character varying(30) NOT NULL,
    payment_installments integer,
    payment_value numeric(10,2)
);


ALTER TABLE public.payments OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 16715)
-- Name: product_category_name_translation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.product_category_name_translation (
    product_category_name character varying(50),
    product_category_name_english character varying(50)
);


ALTER TABLE public.product_category_name_translation OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 16721)
-- Name: products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.products (
    product_id character varying(100) NOT NULL,
    product_category_name character varying(100),
    product_name_lenght integer,
    product_description_lenght integer,
    product_photos_qty integer,
    product_weight_g integer,
    product_length_cm integer,
    product_height_cm integer,
    product_width_cm integer
);


ALTER TABLE public.products OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 16732)
-- Name: sellers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sellers (
    seller_id character varying(100) NOT NULL,
    seller_zip_code_prefix integer,
    seller_city character varying(50),
    seller_state character varying(20)
);


ALTER TABLE public.sellers OWNER TO postgres;

--
-- TOC entry 4791 (class 2604 OID 16860)
-- Name: order_reviews review_pk; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_reviews ALTER COLUMN review_pk SET DEFAULT nextval('public.order_reviews_review_pk_seq'::regclass);


--
-- TOC entry 4793 (class 2606 OID 16711)
-- Name: customers costumers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT costumers_pkey PRIMARY KEY (customer_id);


--
-- TOC entry 4805 (class 2606 OID 16787)
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (order_id, order_item_id);


--
-- TOC entry 4803 (class 2606 OID 16772)
-- Name: order_payments order_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_payments
    ADD CONSTRAINT order_payments_pkey PRIMARY KEY (order_id, payment_sequential);


--
-- TOC entry 4807 (class 2606 OID 16867)
-- Name: order_reviews order_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_reviews
    ADD CONSTRAINT order_reviews_pkey PRIMARY KEY (review_pk);


--
-- TOC entry 4809 (class 2606 OID 16869)
-- Name: order_reviews order_reviews_review_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_reviews
    ADD CONSTRAINT order_reviews_review_id_key UNIQUE (review_id);


--
-- TOC entry 4799 (class 2606 OID 16751)
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (order_id);


--
-- TOC entry 4801 (class 2606 OID 16765)
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (order_id);


--
-- TOC entry 4795 (class 2606 OID 16726)
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (product_id);


--
-- TOC entry 4797 (class 2606 OID 16737)
-- Name: sellers sellers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sellers
    ADD CONSTRAINT sellers_pkey PRIMARY KEY (seller_id);


--
-- TOC entry 4811 (class 2606 OID 16773)
-- Name: order_payments fk_payments_order; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_payments
    ADD CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES public.orders(order_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 4815 (class 2606 OID 16870)
-- Name: order_reviews fk_reviews_order; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_reviews
    ADD CONSTRAINT fk_reviews_order FOREIGN KEY (order_id) REFERENCES public.orders(order_id);


--
-- TOC entry 4812 (class 2606 OID 16798)
-- Name: order_items order_items_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(order_id);


--
-- TOC entry 4813 (class 2606 OID 16788)
-- Name: order_items order_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(product_id);


--
-- TOC entry 4814 (class 2606 OID 16793)
-- Name: order_items order_items_seller_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_seller_id_fkey FOREIGN KEY (seller_id) REFERENCES public.sellers(seller_id);


--
-- TOC entry 4810 (class 2606 OID 16752)
-- Name: orders orders_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(customer_id);


-- Completed on 2026-01-27 15:54:14

--
-- PostgreSQL database dump complete
--

\unrestrict AHdILO4XHW3e7rj0l9CyugfgVJHS88j9ZMNeg4arU1j1c71JbezdQ5aMjy9Ef6V

