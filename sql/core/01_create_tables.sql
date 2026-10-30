USE ROLE SYSADMIN;
USE WAREHOUSE COMPUTE_WH;
USE DATABASE RETAIL_DB;
USE SCHEMA CORE;

DROP TABLE IF EXISTS RETAIL_DB.CORE.ORDER_LINES CASCADE;
DROP TABLE IF EXISTS RETAIL_DB.CORE.FULFILLMENTS CASCADE;
DROP TABLE IF EXISTS RETAIL_DB.CORE.INVENTORY_LEVELS CASCADE;
DROP TABLE IF EXISTS RETAIL_DB.CORE.INVENTORY_ITEMS CASCADE;
DROP TABLE IF EXISTS RETAIL_DB.CORE.VARIANTS CASCADE;
DROP TABLE IF EXISTS RETAIL_DB.CORE.ORDERS CASCADE;
DROP TABLE IF EXISTS RETAIL_DB.CORE.PRODUCTS CASCADE;
DROP TABLE IF EXISTS RETAIL_DB.CORE.CUSTOMERS CASCADE;

CREATE TABLE IF NOT EXISTS CUSTOMERS (
    customer_id VARCHAR NOT NULL,
    first_name VARCHAR,
    last_name VARCHAR,
    lifetime_duration VARCHAR,
    email VARCHAR, 
    phone VARCHAR,
    created_at TIMESTAMP_TZ,
    order_count INT,
    total_amount_spent NUMBER(12, 2),
    total_amount_spent_currency VARCHAR, 
    updated_at TIMESTAMP_TZ,
    state VARCHAR, 
    tags VARCHAR,

    PRIMARY KEY (customer_id)
);

CREATE TABLE IF NOT EXISTS ORDERS (
    order_id VARCHAR NOT NULL,
    customer_id VARCHAR,
    order_number VARCHAR, 
    created_at TIMESTAMP_TZ,
    updated_at TIMESTAMP_TZ,
    processed_at TIMESTAMP_TZ,
    cancelled_at TIMESTAMP_TZ,
    shipping_city VARCHAR, 
    shipping_state_province VARCHAR, 
    shipping_country VARCHAR,
    financial_status VARCHAR,
    fulfillment_status VARCHAR,
    payment_gateways VARCHAR, 
    currency_code VARCHAR,
    presentment_currency VARCHAR,
    order_subtotal NUMBER(12, 2),
    order_subtotal_currency VARCHAR,
    order_shipping_total NUMBER(12, 2), 
    order_shipping_total_currency VARCHAR,
    order_total_duties NUMBER(12, 2),
    order_total_duties_currency VARCHAR,
    order_total_tax NUMBER(12, 2),
    order_total_tax_currency VARCHAR,
    order_discounts_total NUMBER(12, 2),
    order_discounts_total_currency VARCHAR, 
    order_total NUMBER(12, 2),
    order_total_currency VARCHAR,
    is_test BOOLEAN,
    order_shipping_discount NUMBER(12, 2),
    order_shipping_discount_currency VARCHAR,
    
    PRIMARY KEY (order_id),

    CONSTRAINT fk_orders_customers
        FOREIGN KEY (customer_id)
        REFERENCES CUSTOMERS (customer_id)
);

CREATE TABLE IF NOT EXISTS PRODUCTS (
    product_id VARCHAR NOT NULL,
    title VARCHAR, 
    vendor VARCHAR, 
    product_type VARCHAR, 
    status VARCHAR,
    tags VARCHAR, 
    created_at TIMESTAMP_TZ,
    updated_at TIMESTAMP_TZ, 
    published_at TIMESTAMP_TZ,

    PRIMARY KEY (product_id)
);


CREATE TABLE IF NOT EXISTS VARIANTS (
    variant_id VARCHAR NOT NULL, 
    product_id VARCHAR NOT NULL,
    inventory_item_id VARCHAR NOT NULL, 
    title VARCHAR, 
    created_at TIMESTAMP_TZ, 
    updated_at TIMESTAMP_TZ, 
    sku VARCHAR, 
    price NUMBER(12, 2), 
    unit_cost NUMBER(12, 2), 
    compare_at_price NUMBER(12, 2), 
    is_taxable BOOLEAN, 
    is_available_for_sale BOOLEAN,

    PRIMARY KEY (variant_id),

    CONSTRAINT fk_variant_products
        FOREIGN KEY (product_id)
        REFERENCES PRODUCTS (product_id)
);

CREATE TABLE IF NOT EXISTS INVENTORY_ITEMS (
    inventory_item_id VARCHAR NOT NULL, 
    variant_id VARCHAR NOT NULL, 
    sku VARCHAR, 
    is_tracked BOOLEAN, 
    unit_cost NUMBER(12, 2),
    unit_cost_currency VARCHAR,
    requires_shipping BOOLEAN,

    PRIMARY KEY (inventory_item_id),

    CONSTRAINT fk_inventory_items_variants
        FOREIGN KEY (variant_id)
        REFERENCES VARIANTS (variant_id)
);

CREATE TABLE IF NOT EXISTS INVENTORY_LEVELS (
    inventory_item_id VARCHAR NOT NULL,
    inventory_level_id VARCHAR NOT NULL,
    location_id VARCHAR NOT NULL,
    location_name VARCHAR,
    quantity_available INT,
    quantity_on_hand INT,
    quantity_committed INT,
    quantity_incoming INT,
    quantity_reserved INT,
    safety_stock_quantity INT,
    quantity_available_updated_at TIMESTAMP_TZ,

    PRIMARY KEY (inventory_item_id, location_id),

    CONSTRAINT fk_inventory_levels_items
        FOREIGN KEY (inventory_item_id)
        REFERENCES INVENTORY_ITEMS (inventory_item_id)
);

CREATE TABLE IF NOT EXISTS FULFILLMENTS (
    fulfillment_id VARCHAR NOT NULL,
    order_id VARCHAR NOT NULL,

    PRIMARY KEY (fulfillment_id),

    CONSTRAINT fk_fulfillments_orders
        FOREIGN KEY (order_id)
        REFERENCES ORDERS (order_id)
);

CREATE TABLE IF NOT EXISTS ORDER_LINES (
    order_line_id VARCHAR NOT NULL,
    order_id VARCHAR NOT NULL, 
    product_id VARCHAR, 
    variant_id VARCHAR, 
    quantity INT,
    unfulfilled_quantity INT, 
    fulfillable_quantity INT, 
    title VARCHAR,
    variant_title VARCHAR, 
    unit_price NUMBER(12, 2),
    unit_price_currency VARCHAR,
    original_total NUMBER(12, 2),
    original_total_currency VARCHAR,
    discounted_total NUMBER(12, 2),
    discounted_total_currency VARCHAR, 
    total_discount NUMBER(12, 2),
    total_discount_currency VARCHAR,
    is_taxable BOOLEAN, 
    requires_shipping BOOLEAN,

    PRIMARY KEY (order_line_id),

    CONSTRAINT fk_order_lines_orders
        FOREIGN KEY (order_id)
        REFERENCES ORDERS (order_id),

    CONSTRAINT fk_order_lines_products
        FOREIGN KEY (product_id)
        REFERENCES PRODUCTS (product_id),

    CONSTRAINT fk_order_lines_variants
        FOREIGN KEY (variant_id)
        REFERENCES VARIANTS (variant_id)
);
