USE ROLE SYSADMIN;
USE WAREHOUSE COMPUTE_WH; 
USE DATABASE RETAIL_DB;
USE SCHEMA CORE;

SELECT 'CUSTOMERS' AS table_name, COUNT(*) AS actual_rows
FROM CUSTOMERS

UNION ALL

SELECT 'PRODUCTS', COUNT(*)
FROM PRODUCTS

UNION ALL

SELECT 'ORDERS', COUNT(*)
FROM ORDERS

UNION ALL

SELECT 'VARIANTS', COUNT(*)
FROM VARIANTS

UNION ALL

SELECT 'INVENTORY_ITEMS', COUNT(*)
FROM INVENTORY_ITEMS

UNION ALL

SELECT 'INVENTORY_LEVELS', COUNT(*)
FROM INVENTORY_LEVELS

UNION ALL

SELECT 'ORDER_LINES', COUNT(*)
FROM ORDER_LINES

UNION ALL

SELECT 'FULFILLMENTS', COUNT(*)
FROM FULFILLMENTS;



SELECT
    'CUSTOMERS' AS table_name,
    COUNT_IF(customer_id IS NULL) AS null_key_rows,
    COUNT(customer_id) - COUNT(DISTINCT customer_id) AS duplicate_key_rows
FROM CUSTOMERS

UNION ALL

SELECT
    'PRODUCTS',
    COUNT_IF(product_id IS NULL),
    COUNT(product_id) - COUNT(DISTINCT product_id)
FROM PRODUCTS

UNION ALL

SELECT
    'ORDERS',
    COUNT_IF(order_id IS NULL),
    COUNT(order_id) - COUNT(DISTINCT order_id)
FROM ORDERS

UNION ALL

SELECT
    'VARIANTS',
    COUNT_IF(variant_id IS NULL),
    COUNT(variant_id) - COUNT(DISTINCT variant_id)
FROM VARIANTS

UNION ALL

SELECT
    'INVENTORY_ITEMS',
    COUNT_IF(inventory_item_id IS NULL),
    COUNT(inventory_item_id) - COUNT(DISTINCT inventory_item_id)
FROM INVENTORY_ITEMS

UNION ALL

SELECT
    'ORDER_LINES',
    COUNT_IF(order_line_id IS NULL),
    COUNT(order_line_id) - COUNT(DISTINCT order_line_id)
FROM ORDER_LINES

UNION ALL

SELECT
    'FULFILLMENTS',
    COUNT_IF(fulfillment_id IS NULL),
    COUNT(fulfillment_id) - COUNT(DISTINCT fulfillment_id)
FROM FULFILLMENTS;

SELECT
    'INVENTORY_LEVELS' AS table_name,
    COUNT_IF(inventory_item_id is null OR location_id is null) as null_key_rows
FROM INVENTORY_LEVELS;



SELECT
    'INVENTORY_LEVELS' AS table_name,
    COUNT(*) AS duplicate_key_groups
FROM (
    SELECT
        inventory_item_id,
        location_id,
        COUNT(*) AS rows_per_key
    FROM INVENTORY_LEVELS
    GROUP BY inventory_item_id, location_id
    HAVING COUNT(*) > 1
) AS duplicate_keys;

-- Referential integrity checks: child foreign keys to parent primary keys
SELECT 
    COUNT_IF(o.customer_id is null) AS null_customer_ids,
    COUNT_IF(
        o.customer_id is not null
        AND c.customer_id is null
    ) AS unmatched_customer_ids
FROM ORDERS o  
LEFT JOIN CUSTOMERS c  
    ON o.customer_id = c.customer_id; 

SELECT 
    COUNT_IF(ol.order_id is null) as null_order_ids,
    COUNT_IF(
        ol.order_id is not null
        AND o.order_id is null
    ) AS unmatched_order_ids
FROM order_lines ol 
LEFT JOIN orders o 
    ON ol.order_id = o.order_id;

SELECT 
    COUNT_IF(ol.product_id is null) AS null_product_ids,
    COUNT_IF(
        ol.product_id is not null
        AND p.product_id is null
    ) AS unmatched_product_ids
FROM order_lines ol  
LEFT JOIN products p
    ON p.product_id = ol.product_id;

SELECT 
    COUNT_IF(ol.variant_id is null) AS null_variant_ids,
    COUNT_IF(
        ol.variant_id is not null 
        AND v.variant_id is null 
    ) AS unmatched_variant_ids
FROM order_lines ol 
LEFT JOIN variants v 
    ON v.variant_id = ol.variant_id;

SELECT 
    COUNT_IF(v.product_id is null) AS null_product_ids,
    COUNT_IF(
        v.product_id is not null 
        AND p.product_id is null 
    ) AS unmatched_product_ids
FROM variants v 
LEFT JOIN products p 
    ON v.product_id = p.product_id;

SELECT 
    COUNT_IF(v.inventory_item_id is null) AS null_inventory_item_ids,
    COUNT_IF(
        v.inventory_item_id is not null 
        AND ii.inventory_item_id is null
    ) AS unmatched_inventory_item_ids
FROM variants v
LEFT JOIN inventory_items ii  
    ON v.inventory_item_id = ii.inventory_item_id;

SELECT 
    COUNT_IF(ii.variant_id is null) AS null_variant_ids,
    COUNT_IF(
        ii.variant_id is not null 
        AND v.variant_id is null
    ) AS unmatched_variant_ids
FROM inventory_items ii  
LEFT JOIN variants v 
    ON ii.variant_id = v.variant_id;

SELECT 
    COUNT_IF(il.inventory_item_id is null) AS null_inventory_item_ids,
    COUNT_IF(
        il.inventory_item_id is not null 
        AND ii.inventory_item_id is null
    ) AS unmatched_inventory_item_ids
FROM inventory_levels il  
LEFT JOIN inventory_items ii
    ON il.inventory_item_id = ii.inventory_item_id;

SELECT 
    COUNT_IF(f.order_id is null) AS null_order_ids,
    COUNT_IF(
        f.order_id is not null 
        AND o.order_id is null
    ) AS unmatched_order_ids
FROM fulfillments f   
LEFT JOIN orders o  
    ON f.order_id = o.order_id;


SELECT 
    COUNT_IF(
        quantity <= 0
        OR unfulfilled_quantity < 0
        OR fulfillable_quantity < 0
        OR unfulfilled_quantity > quantity
        OR fulfillable_quantity > unfulfilled_quantity
    ) AS invalid_quantity_rows,
    COUNT_IF(
        quantity IS NULL 
        OR unfulfilled_quantity IS NULL 
        OR fulfillable_quantity IS NULL 
    ) AS null_quantity_rows
FROM order_lines;

-- Verify whether a line's price, after discounts, ever exceeds its original price 
SELECT
    COUNT_IF(discounted_total > original_total) AS invalid_discount_rows,
    COUNT_IF(
        discounted_total IS NULL
        OR original_total IS NULL
    ) AS null_discount_amount_rows
FROM ORDER_LINES;

SELECT 
    COUNT_IF(
        ABS(original_total - total_discount - discounted_total) > 0.01
    ) AS invalid_discount_calculation_rows,
    COUNT_IF(
        original_total IS NULL 
        OR total_discount IS NULL 
        OR discounted_total IS NULL
    ) AS null_discounted_calculation_rows
FROM ORDER_LINES;

SELECT 
    COUNT_IF(
        ABS((unit_price * quantity) - original_total) > 0.01
    ) AS invalid_original_total_rows,
    COUNT_IF(
        unit_price IS NULL
        OR quantity IS NULL 
        OR original_total IS NULL
    ) AS null_unit_calculation_rows
FROM ORDER_LINES;

SELECT 
    COUNT_IF(
        unit_price_currency IS NULL
        OR unit_price_currency <> 'USD'
        OR original_total_currency IS NULL 
        OR original_total_currency <> 'USD'
        OR discounted_total_currency IS NULL 
        OR discounted_total_currency <> 'USD'
        OR total_discount_currency IS NULL 
        OR total_discount_currency <> 'USD'
    ) AS invalid_order_line_currency_rows
FROM ORDER_LINES;

SELECT
    COUNT_IF(
        currency_code IS NULL 
        OR currency_code <> 'USD'
        OR order_subtotal_currency IS NULL 
        OR order_subtotal_currency <> 'USD'
        OR order_shipping_total_currency IS NULL
        OR order_shipping_total_currency <> 'USD'
        OR order_total_tax_currency IS NULL 
        OR order_total_tax_currency <> 'USD'
        OR order_discounts_total_currency IS NULL
        OR order_discounts_total_currency <> 'USD'
        OR order_total_currency IS NULL 
        OR order_total_currency <> 'USD'
    ) AS invalid_order_currency_rows
FROM ORDERS;

-- presentment_currency has 4 valid options; validate values fall within these options 
SELECT
    COUNT_IF(
        presentment_currency IS NULL OR presentment_currency NOT IN ('USD', 'CAD', 'EUR', 'GBP')
    ) AS invalid_presentment_currency_rows 
FROM ORDERS;

-- processed_at may precede created_at and is intentionally not sequence-tested.
SELECT 
    COUNT_IF(
        created_at IS NULL
        OR updated_at IS NULL
        OR processed_at IS NULL
    ) AS missing_required_timestamp_rows,
    COUNT_IF(updated_at < created_at) AS invalid_updated_created_rows,
    COUNT_IF(cancelled_at IS NOT NULL AND cancelled_at < created_at) AS cancellation_before_created_rows
FROM ORDERS;