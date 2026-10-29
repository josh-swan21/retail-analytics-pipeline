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

SELECT
    COUNT_IF(
        quantity_available IS NULL
        OR quantity_on_hand IS NULL
        OR quantity_committed IS NULL
        OR quantity_incoming IS NULL
        OR quantity_reserved IS NULL
        OR safety_stock_quantity IS NULL
    ) missing_inventory_quantity_rows,
    COUNT_IF(
        quantity_committed < 0
        OR quantity_incoming < 0
        OR quantity_reserved < 0
        OR safety_stock_quantity < 0
    ) invalid_negative_inventory_rows,
    COUNT_IF(
        quantity_available_updated_at IS NULL
    ) missing_inventory_timestamp_rows,
    COUNT_IF(
        quantity_on_hand < 0
    ) negative_on_hand_rows,
    COUNT_IF(
        quantity_available < 0
    ) negative_available_rows
FROM INVENTORY_LEVELS;

SELECT
    COUNT_IF(
        quantity_available + quantity_committed + quantity_reserved + safety_stock_quantity > quantity_on_hand
    ) AS known_inventory_exceeds_on_hand_rows
FROM INVENTORY_LEVELS;

SELECT 
    COUNT_IF(
        order_subtotal IS NULL
        OR order_shipping_total IS NULL
        OR order_total_tax IS NULL
        OR order_discounts_total IS NULL 
        OR order_total IS NULL
    ) missing_order_amount_rows,
    COUNT_IF(
        order_subtotal < 0
        OR order_shipping_total < 0
        OR order_total_tax < 0
        OR order_discounts_total < 0
        OR order_total < 0
    ) negative_order_amount_rows
FROM ORDERS;

-- Validate the new amounts: zero is valid; NULL and negative are not.
SELECT
    COUNT_IF(
        order_shipping_discount IS NULL
        OR order_total_duties IS NULL
    ) AS missing_new_order_amount_rows,

    COUNT_IF(
        order_shipping_discount < 0
        OR order_total_duties < 0
    ) AS negative_new_order_amount_rows,

    COUNT_IF(
        order_shipping_discount > order_shipping_total
    ) AS shipping_discount_exceeds_shipping_rows
FROM ORDERS;


-- Both new currency fields should contain USD. 
SELECT
    COUNT_IF(
        order_shipping_discount_currency IS NULL
        OR order_shipping_discount_currency <> 'USD'
        OR order_total_duties_currency IS NULL
        OR order_total_duties_currency <> 'USD'
    ) AS invalid_new_order_currency_rows
FROM ORDERS;


-- Reconcile the order total.
-- Subtotal already reflects merchandise discounts, so do not
-- subtract order_discounts_total again.
-- Exactly $0.01 is within tolerance; anything greater is flagged.
SELECT
    COUNT_IF(
        order_subtotal IS NULL
        OR order_shipping_total IS NULL
        OR order_shipping_discount IS NULL
        OR order_total_tax IS NULL
        OR order_total_duties IS NULL
        OR order_total IS NULL
    ) AS missing_reconciliation_amount_rows,

    COUNT_IF(
        ABS(
            order_total - (
                order_subtotal
                + order_shipping_total
                - order_shipping_discount
                + order_total_tax
                + order_total_duties
            )
        ) > 0.01
    ) AS invalid_reconciled_order_total_rows
FROM ORDERS;


-- Inspect any remaining discrepancies or missing amounts.
-- Expected result: no rows.
WITH order_reconciliation AS (
    SELECT
        order_id,
        order_number,
        order_subtotal,
        order_shipping_total,
        order_shipping_discount,
        order_total_tax,
        order_total_duties,
        order_total,
        order_subtotal
            + order_shipping_total
            - order_shipping_discount
            + order_total_tax
            + order_total_duties AS calculated_order_total,
        shipping_country,
        financial_status,
        cancelled_at
    FROM ORDERS
)
SELECT
    *,
    order_total - calculated_order_total AS unexplained_difference
FROM order_reconciliation
WHERE order_total IS NULL
    OR calculated_order_total IS NULL
    OR ABS(order_total - calculated_order_total) > 0.01
ORDER BY ABS(order_total - calculated_order_total) DESC, order_id;

