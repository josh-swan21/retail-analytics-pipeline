-- Grain: one Chicago order-creation date with at least one non-test order.
-- Values describe the current snapshot, not refund-adjusted net revenue.
with daily_sales as (
    select
        sales_date,
        count(*) as order_count,
        count(distinct customer_id) as identified_customer_count,
        count_if(customer_id is null) as guest_order_count,
        sum(units_ordered) as units_ordered,
        sum(order_line_count) as order_line_count,
        sum(order_subtotal) as merchandise_subtotal,
        sum(order_discounts_total) as total_discounts_recorded,
        sum(order_shipping_total) as original_shipping,
        sum(order_shipping_discount) as shipping_discounts,
        sum(order_shipping_total - order_shipping_discount) as net_shipping_charged,
        sum(order_total_tax) as tax_collected,
        sum(order_total_duties) as duties_collected,
        sum(order_total) as total_order_value,
        avg(order_total) as average_order_value,
        -- Retain the supplied definition; "completed" is not accounting revenue.
        coalesce(count_if(
            financial_status in ('PAID', 'PARTIALLY_REFUNDED')
            and is_cancelled = false
        ), 0) as completed_order_count,
        sum(case
            when financial_status in ('PAID', 'PARTIALLY_REFUNDED')
                and is_cancelled = false
            then order_total else 0
        end) as completed_order_value,
        coalesce(count_if(fulfillment_status = 'FULFILLED'), 0) as fulfilled_order_count
    from {{ ref('int_orders_with_lines') }}
    group by sales_date
)
select
    daily_sales.*,
    completed_order_value / nullif(completed_order_count, 0)
        as average_completed_order_value
from daily_sales
