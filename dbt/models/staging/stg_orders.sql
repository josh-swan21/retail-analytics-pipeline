select
    order_id,
    created_at,
    customer_id,
    financial_status,
    fulfillment_status,
    cancelled_at,
    is_test,
    order_subtotal,
    order_discounts_total,
    order_shipping_total,
    order_shipping_discount,
    order_total_tax,
    order_total_duties,
    order_total
from {{ source('retail_core', 'orders') }}
