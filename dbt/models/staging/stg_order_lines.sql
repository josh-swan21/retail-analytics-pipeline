select order_line_id, order_id, quantity
from {{ source('retail_core', 'order_lines') }}
