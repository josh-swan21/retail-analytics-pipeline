## Retail Store Analytics -- Project Notes

## Project context
- Source: Shopify export files synced locally from Google Drive each day.
- Files are read from the local synced folder rather than the Drive API so the workflow stays simple and reproducible on a single laptop.
- Each table is stored in its own folder, and file names use an ISO date prefix so alphabetical order matches chronological order.
- The raw export is treated as a source snapshot; analysis should use a frozen snapshot or an explicit complete-export marker when results are intended for reporting.

## Intake approach
- The loading workflow uses a helper to select the newest CSV file per folder.
- The notebook keeps raw tables separate from cleaned tables so the transformation logic can be audited.
- Key normalization is done before joins, deduplication, or analysis.
- The current working principle is: prove the grain first, then build the analytical tables from it.

## Working grain and data model
- A table is treated as one row per entity only after its key and grain have been verified.
- The current analytical model is centered on the following entities:
  - customers
  - orders
  - order lines
  - fulfillments
  - products
  - variants
  - inventory items
  - inventory levels
  - locations

### Current clean-table intent
- `customers_clean`: one row per customer
- `orders_clean`: one row per order
- `order_lines_clean`: one row per order line
- `fulfillments_clean`: one row per fulfillment
- `products_clean`: one row per product
- `variants_clean`: one row per sellable variant
- `inventory_items_clean`, `inventory_levels_clean`, and `locations_clean`: planned and partially validated as the inventory side of the model is completed

## Initial grain checks
- The first pass confirmed that the raw exports do not all share the same grain.
- The raw customers export contains repeated customer IDs, which suggests address or contact expansions rather than true duplicate customers.
- The raw orders export contains repeated order IDs because one order can contain multiple line items and nested child records.
- Products were initially closer to a true one-row-per-product grain, while the line-item and variant concepts needed a separate analytical layer.

## Data contracts

### Customers
- Raw grain: customer export record, potentially repeated for the same customer
- Clean grain: one row per `customer_id`
- Key: `customer_id`
- Duplicate rule: keep one logical customer row per customer ID
- Validation: `customer_id` must be non-null and unique in `customers_clean`

### Orders
- Raw grain: order-level row with repeated values due to line-item and child-record expansion
- Clean grain: one row per `order_id`
- Key: `order_id`
- Duplicate rule: use order-header fields only and exclude child-grain expansion from the clean table
- Validation: `order_id` must be non-null and unique in `orders_clean`

### Order lines
- Raw grain: one row per order line, with repeated IDs when nested child fields are flattened
- Clean grain: one row per `order_line_id`
- Key: `order_line_id`
- Duplicate rule: remove repeated child-grain rows and keep a single row per line
- Validation: `order_line_id` must be non-null and unique in `order_lines_clean`

### Fulfillments
- Raw grain: fulfillment child records embedded in the orders export
- Clean grain: one row per `fulfillment_id`
- Key: `fulfillment_id`
- Duplicate rule: drop null-parent fulfillment rows and preserve one row per fulfillment ID
- Validation: `fulfillment_id` must be non-null and unique in `fulfillments_clean`

### Products and variants
- Raw grain: product and variant details may be mixed in the same export
- Clean grain: one row per product and one row per variant once parsed correctly
- Keys: `product_id` and `variant_id`
- Duplicate rule: remove true duplicates and keep one logical row per entity
- Validation: each key must be non-null and unique in its clean table

## Relationships and join rules
- Customer-to-order relationship: optional on some orders, but populated customer IDs must resolve to a customer in `customers_clean`.
- Order-to-order-lines and order-to-fulfillments: these should be validated as strict parent-child relationships.
- Product-to-variant relationships should be checked before using variant-level metrics in analysis.
- Inventory relationships should be validated only after the inventory item, inventory level, and location tables are fully defined.

## Key decisions made so far
- Use the order’s shipping geography for sales-location analysis rather than a customer’s saved address.
- Keep null customer IDs as null rather than inventing an unknown-customer record.
- Treat guest and anonymous purchases carefully; the analysis should include a fallback view for anonymous purchasers instead of assuming all orders belong to a clean customer record.
- Use frozen snapshots for published metrics and avoid relying on the latest synced file when reproducibility matters.
- Keep raw and clean tables separate to preserve a reliable audit trail.

## Open questions and remaining work
- Which columns in the raw orders export are truly order-level versus line-item or product-level?
- How should product, variant, and SKU-level detail be represented in the final analytical model?
- Which inventory fields are point-in-time and which are historical?
- How should customer-address history be handled if location analysis expands beyond shipping geography?
- Should the final analysis treat some tables as facts and others as dimensions, or is a hybrid model more appropriate?

## Current status — 2026-07-21
- The project has moved beyond initial cleaning and into analysis.
- RFM outputs are now being interpreted with caution because guest-checkout orders and duplicate-email patterns can distort customer-level segmentation.
- A conservative anonymous-purchaser attribution approach is being used to avoid overstating repeat-customer behavior.
- Trend and daily-sales metrics are sensitive to source drift, so frozen snapshots should be used for any reporting output.
- Variant option parsing has been improved to handle quoted and multi-token option values more reliably.
- The Streamlit experience has been improved through a cached `variant_lookup` table.
- Notebook memory use has been reduced by persisting key intermediate tables and dropping earlier temporary frames after validation steps.
- The validation workflow has been optimized for faster repeated runs.
- Documentation and publication notes have been consolidated so the next analysis work is easier to follow.

## Immediate next steps
- Finish the margin, sales-trend, and product/vendor analysis notebooks on top of the validated clean tables.
- Continue validating customer, product, variant, and inventory relationships before treating any result as final.
- Keep using frozen snapshots for any metric intended for publication.
- Revisit the remaining grain and model questions once the analysis notebooks are complete.


