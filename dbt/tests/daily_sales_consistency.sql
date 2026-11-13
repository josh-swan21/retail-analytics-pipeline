select * from {{ ref('mart_daily_sales') }}
where order_count <= 0
   or completed_order_count > order_count
   or completed_order_count < 0
   or fulfilled_order_count > order_count
   or guest_order_count > order_count
   or units_ordered < order_line_count
   or abs(original_shipping - shipping_discounts - net_shipping_charged) > 0.01
   or abs(merchandise_subtotal + net_shipping_charged + tax_collected
          + duties_collected - total_order_value) > 0.01 * order_count
   or (completed_order_count = 0 and average_completed_order_value is not null)
   or (completed_order_count > 0 and (
       average_completed_order_value is null
       or abs(average_completed_order_value
              - completed_order_value / completed_order_count) > 0.01))
