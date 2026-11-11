USE ROLE SYSADMIN;
USE WAREHOUSE COMPUTE_WH;
USE DATABASE RETAIL_DB;
USE SCHEMA CORE;

SELECT
    financial_status,
    COUNT(*) AS order_count,
    COUNT_IF(
        cancelled_at IS NOT NULL
    ) AS cancelled_orders,
    SUM(order_total) order_total_collected
FROM ORDERS
WHERE is_test = FALSE
GROUP BY financial_status
ORDER BY financial_status DESC;

SELECT
    financial_status,
    fulfillment_status,
    cancelled_at IS NOT NULL AS is_cancelled,
    COUNT(*) AS order_count,
    SUM(order_total) AS order_total_collected
FROM ORDERS
WHERE is_test = FALSE
GROUP BY financial_status, fulfillment_status, is_cancelled
ORDER BY financial_status, fulfillment_status, is_cancelled; 





WITH order_line_summary AS (
    SELECT
        order_id,
        SUM(quantity) AS units_ordered,
        COUNT(DISTINCT order_line_id) AS order_line_count
    FROM ORDER_LINES 
    GROUP BY order_id
)

SELECT * 
FROM order_line_summary
LIMIT 20;




WITH order_line_summary AS (
    SELECT
        order_id,
        SUM(quantity) AS units_ordered,
        COUNT(DISTINCT order_line_id) AS order_line_count
    FROM ORDER_LINES 
    GROUP BY order_id
)

SELECT 
    COUNT_IF(
        order_id IS NULL
    ) AS null_order_id_count, 
    COUNT(*) - COUNT(DISTINCT order_id) AS duplicate_order_id_count
FROM order_line_summary;


WITH order_line_summary AS (
    SELECT
        order_id,
        SUM(quantity) AS units_ordered,
        COUNT(DISTINCT order_line_id) AS order_line_count
    FROM ORDER_LINES 
    GROUP BY order_id
), 

orders_with_lines AS (
    SELECT
        o.order_id, 
        CAST(CONVERT_TIMEZONE('America/Chicago', o.created_at) AS DATE) AS sales_date,
        o.customer_id, 
        o.financial_status,
        o.fulfillment_status,
        CASE 
            WHEN o.cancelled_at IS NOT NULL THEN TRUE
            ELSE FALSE
        END AS is_cancelled,
        ols.units_ordered,
        ols.order_line_count,
    FROM ORDERS o 
    LEFT JOIN order_line_summary ols
        ON o.order_id = ols.order_id
    WHERE o.is_test = FALSE
) 

SELECT 
    COUNT(*) total_joined_rows,
    COUNT(DISTINCT order_id) AS disctinct_order_ids,
    COUNT(*) - COUNT(DISTINCT owl.order_id) AS duplicated_order_id_count,
    COUNT_IF(
        owl.units_ordered IS NULL
    ) AS null_units_ordered_count,
    COUNT_IF(
        owl.order_line_count IS NULL
    ) AS null_order_line_count
FROM orders_with_lines owl;

-- validate order-level money fields. compare to order_total and order_subtotal from orders table
WITH order_line_summary AS (
    SELECT
        order_id,
        SUM(quantity) AS units_ordered,
        COUNT(DISTINCT order_line_id) AS order_line_count
    FROM ORDER_LINES 
    GROUP BY order_id
), 

orders_with_lines AS (
    SELECT
        o.order_id, 
        CAST(
            CONVERT_TIMEZONE('America/Chicago', o.created_at) 
            AS DATE
        ) AS sales_date,
        o.customer_id, 
        o.financial_status,
        o.fulfillment_status,
        CASE 
            WHEN o.cancelled_at IS NOT NULL THEN TRUE
            ELSE FALSE
        END AS is_cancelled,
        ols.units_ordered,
        ols.order_line_count,
        o.order_subtotal, 
        o.order_discounts_total,
        o.order_shipping_total,
        o.order_shipping_discount,
        o.order_total_tax,
        o.order_total_duties,
        o.order_total
    FROM ORDERS o 
    LEFT JOIN order_line_summary ols
        ON o.order_id = ols.order_id
    WHERE o.is_test = FALSE
) 

SELECT 
    COUNT(*),
    SUM(owl.order_total),
    SUM(owl.order_subtotal),
    SUM(owl.units_ordered)
FROM orders_with_lines owl;

-- compare to query above for order totals and subtotals
SELECT
    COUNT(*), 
    SUM(order_total),
    SUM(order_subtotal)
FROM ORDERS
WHERE is_test = FALSE;

-- build and validate daily_sales mart

WITH order_line_summary AS (
    SELECT
        order_id,
        SUM(quantity) AS units_ordered,
        COUNT(DISTINCT order_line_id) AS order_line_count
    FROM ORDER_LINES 
    GROUP BY order_id
), 

orders_with_lines AS (
    SELECT
        o.order_id, 
        CAST(CONVERT_TIMEZONE('America/Chicago', o.created_at) AS DATE) AS sales_date,
        o.customer_id, 
        o.financial_status,
        o.fulfillment_status,
        CASE 
            WHEN o.cancelled_at IS NOT NULL THEN TRUE
            ELSE FALSE
        END AS is_cancelled,
        ols.units_ordered,
        ols.order_line_count,
        o.order_subtotal, 
        o.order_discounts_total,
        o.order_shipping_total,
        o.order_shipping_discount,
        o.order_total_tax,
        o.order_total_duties,
        o.order_total
    FROM ORDERS o 
    LEFT JOIN order_line_summary ols
        ON o.order_id = ols.order_id
    WHERE o.is_test = FALSE
),

daily_sales AS (
    SELECT
        sales_date,
        COUNT(*) AS order_count,
        COUNT(DISTINCT customer_id) AS identified_customer_count,
        COUNT_IF(customer_id IS NULL) guest_order_count,
        SUM(units_ordered) AS units_ordered,
        SUM(order_line_count) AS order_line_count,
        SUM(order_subtotal) AS merchandise_subtotal,
        SUM(order_discounts_total) AS total_discounts_recorded,
        SUM(order_shipping_total) AS original_shipping,
        SUM(order_shipping_discount) AS shipping_discounts,
        SUM(order_shipping_total - order_shipping_discount) AS net_shipping_charged,
        SUM(order_total_tax) AS tax_collected,
        SUM(order_total_duties) AS duties_collected,
        SUM(order_total) AS total_order_value,
        AVG(order_total) AS average_order_value,
        COUNT_IF(
            financial_status IN ('PAID', 'PARTIALLY_REFUNDED')
            AND is_cancelled = FALSE
        ) AS completed_order_count,
        
        SUM(
            CASE
                WHEN financial_status IN ('PAID', 'PARTIALLY_REFUNDED')
                    AND is_cancelled = FALSE
                THEN order_total
                ELSE 0
            END
        ) AS completed_order_value,

        COUNT_IF(
            fulfillment_status = 'FULFILLED'
        ) AS fulfilled_order_count,

    FROM orders_with_lines
    GROUP BY sales_date
)

SELECT 
    daily_sales.*,
    completed_order_value / NULLIF(completed_order_count, 0) AS average_completed_order_value
FROM daily_sales
ORDER BY sales_date;