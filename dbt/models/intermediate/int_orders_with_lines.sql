-- Grain: one row per non-test order. Aggregate lines BEFORE joining money.
with order_line_summary as (
    select
        order_id,
        sum(quantity) as units_ordered,
        count(distinct order_line_id) as order_line_count
    from {{ ref('stg_order_lines') }}
    group by order_id
)
select
    o.order_id,
    cast(convert_timezone('America/Chicago', o.created_at) as date) as sales_date,
    o.customer_id,
    o.financial_status,
    o.fulfillment_status,
    o.cancelled_at is not null as is_cancelled,
    ols.units_ordered,
    ols.order_line_count,
    o.order_subtotal,
    o.order_discounts_total,
    o.order_shipping_total,
    o.order_shipping_discount,
    o.order_total_tax,
    o.order_total_duties,
    o.order_total
from {{ ref('stg_orders') }} o
left join order_line_summary ols on o.order_id = ols.order_id
where o.is_test = false
