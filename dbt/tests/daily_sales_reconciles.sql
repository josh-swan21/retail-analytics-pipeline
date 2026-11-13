-- Independently aggregate order headers: catches dropped/duplicated orders and join fanout.
with expected as (
    select
        cast(convert_timezone('America/Chicago', created_at) as date) as sales_date,
        count(*) as order_count,
        sum(order_total) as total_order_value
    from {{ source('retail_core', 'orders') }}
    where is_test = false
    group by 1
)
select coalesce(e.sales_date, m.sales_date) as sales_date
from expected e
full outer join {{ ref('mart_daily_sales') }} m on e.sales_date = m.sales_date
where e.sales_date is null or m.sales_date is null
   or e.order_count <> m.order_count
   or m.total_order_value is null
   or abs(e.total_order_value - m.total_order_value) > 0.01
