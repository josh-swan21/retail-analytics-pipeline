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
- `inventory_items_clean`: one row per inventory item
- `inventory_levels_clean`: one row per inventory item and Shopify location
- `locations_clean`: still to be materialized as a standalone location dimension; the current inventory export contains three validated locations

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

### Inventory items
- Raw grain: inventory-item attributes repeated across location-level quantity rows
- Clean grain: one row per `inventory_item_id`
- Key: `inventory_item_id`
- Duplicate rule: retain only item-level attributes after proving they are stable across locations
- Validation: the key must be non-null and unique, retained attributes must not conflict across locations, and `variant_id` must resolve uniquely to `variants_clean`

### Inventory levels
- Raw and clean grain: one row per inventory item and Shopify location in the current snapshot
- Key: (`inventory_item_id`, `location_id`)
- Duplicate rule: do not deduplicate repeated inventory-item IDs; they represent valid location assignments
- Validation: both key columns must be populated, the composite key must be unique, and every inventory item must resolve to `inventory_items_clean`
- Limitation: this is current state, not historical inventory; add `snapshot_at` to the key when dated snapshots are retained

### Locations
- Source grain: location attributes embedded in inventory-level rows
- Intended clean grain: one row per `location_id`
- Key: `location_id`
- Current evidence: three location IDs map one-to-one to three inventory-level source components
- Remaining work: materialize and validate `locations_clean`

## Relationships and join rules
- Customer-to-order relationship: optional on some orders, but populated customer IDs must resolve to a customer in `customers_clean`.
- Order-to-order-lines and order-to-fulfillments: these should be validated as strict parent-child relationships.
- Product-to-variant relationships should be checked before using variant-level metrics in analysis.
- Variant-to-inventory-item is validated as one-to-one in both directions.
- Inventory-level-to-inventory-item is a validated many-to-one relationship with zero orphan rows.
- Location relationships are proven in the source but still need a standalone `locations_clean` table.

## Key decisions made so far
- Use the order’s shipping geography for sales-location analysis rather than a customer’s saved address.
- Keep null customer IDs as null rather than inventing an unknown-customer record.
- Treat guest and anonymous purchases carefully; the analysis should include a fallback view for anonymous purchasers instead of assuming all orders belong to a clean customer record.
- Use frozen snapshots for published metrics and avoid relying on the latest synced file when reproducibility matters.
- Keep raw and clean tables separate to preserve a reliable audit trail.
- Use `(inventory_item_id, location_id)` as the business key for current inventory levels; preserve `inventory_level_id` for source traceability.
- Run semantic assertions after structural checks: event timestamps must be ordered, quantities must be internally consistent, monetary fields must reconcile within $0.01, and line-level currencies must agree.

## Open questions and remaining work
- How should selected variant options be normalized if option-level analysis requires more than the current variant table?
- What snapshot cadence and retention policy should be used to turn current inventory state into history?
- How should customer-address history be handled if location analysis expands beyond shipping geography?
- Should fulfillments remain a minimal order bridge or be expanded with event-level attributes for operational analysis?
- Which clean-table persistence format and frozen snapshot should downstream analysis notebooks use?

## Current status — 2026-07-30
- The latest executed cleaning run uses five July 30 exports. The raw Orders export has about two rows per order because line items are flattened into it, and about a third of raw customer rows are duplicates of another customer ID.
- The clean model has each table at its own grain: about 1.9 order lines per order, one inventory item per variant, and about 1.4 inventory-level rows per inventory item, plus a fulfillment child table.
- All 15 displayed Shopify ID normalization checks pass with zero failed extractions.
- Customer, order, order-line, product, variant, inventory-item, and inventory-level keys pass their implemented uniqueness and null checks.
- Populated order-line product and variant references resolve; historical lines with null catalog references are retained and counted separately.
- Variant and inventory-item references pass as a one-to-one relationship in both directions, and inventory levels have zero orphaned inventory-item references.
- The inventory export is now modeled at item and item-location grains. The three locations are mapped and validated, but `locations_clean` has not yet been materialized.
- Order timestamps parse successfully and have no updated-before-created or cancelled-before-created violations.
- Order-line quantities, totals, discounts, unit-price extensions, and USD currency fields pass the current semantic assertions.
- Results still come from `latest_file()` and therefore remain a moving development snapshot until a dated snapshot is frozen for reporting.

## Immediate next steps
- Materialize `locations_clean` and validate inventory-level foreign keys to it.
- Persist the validated clean tables from one explicitly frozen source snapshot for downstream reproducibility.
- Complete order-header monetary and currency contracts, then add equivalent type and domain checks to the remaining clean tables.
- Run the margin, sales-trend, RFM, and product/vendor notebooks against the same frozen clean outputs; distinguish exploratory notebooks from completed analysis.
- Reconcile guest-checkout handling before treating customer-level RFM results as final.

## Work completed since the 2026-07-30 update

### Python warehouse preparation
- Validated and normalized clean-table data types before export, including UTC timestamps, nullable identifiers, integer measures, booleans, strings, and monetary values.
- Added conversion-failure assertions before replacing populated source timestamps.
- Added checks preventing identifier cleanup from producing literal `nan`/`<NA>` strings or trailing `.0` values.
- Renamed clean-table columns to the snake_case contract used by Snowflake.
- Added the 8-table `data/clean` CSV export loop.
- Removed unused EDA, RFM, margin, sales-trend, and product/vendor notebooks so incomplete analysis is not represented as current project work.

### Snowflake model and loading
- Created `RETAIL_DB.CORE` tables for the 8 clean CSV outputs: customers, products, orders, variants, inventory items, inventory levels, order lines, and fulfillments.
- Added Snowflake primary- and foreign-key declarations matching the Python clean-table model.
- Added a manual internal-stage workflow that confirms all 8 files before replacing the existing snapshot.
- Added `COPY INTO` preflight validation with `VALIDATION_MODE = 'RETURN_ALL_ERRORS'` for every file.
- Added abort-on-error loads and post-load row-count queries for every destination table.
- The load remains a manual full-snapshot replacement; it is not yet atomic, and execution results are not stored in the repository.

### Snowflake structural and referential validation
- Added row-count queries for all 8 tables.
- Added null and duplicate primary-key checks, including the `(inventory_item_id, location_id)` inventory-level key.
- Added null-versus-unmatched foreign-key checks for:
  - orders → customers
  - order lines → orders, products, and variants
  - variants → products and inventory items
  - inventory items → variants
  - inventory levels → inventory items
  - fulfillments → orders
- These queries are implemented in `sql/core/03_validate_tables.sql`. No saved Snowflake result set exists in the repository, so passing warehouse counts are not asserted here.

### Snowflake semantic and currency validation
- Added order-line quantity checks: ordered quantity must be positive; remaining quantities must be non-negative and satisfy `fulfillable_quantity <= unfulfilled_quantity <= quantity`.
- Added checks that discounted totals do not exceed original totals.
- Added $0.01-tolerance reconciliations for `original_total - total_discount = discounted_total` and `unit_price * quantity = original_total`.
- Added a current-shop currency contract requiring all 4 order-line currency fields to be populated and equal to `USD`.
- The saved Python notebook already records 0 missing or inconsistent order-line currency rows and only `USD`; the matching Snowflake result is not stored.

## Updated next steps
- Run the complete Snowflake validation script after the current 8-file load and preserve an auditable result artifact.
- Add order-header and customer/inventory currency checks where monetary values are compared.
- Add Snowflake timestamp and event-order checks to mirror the notebook coverage.
- Freeze a dated clean snapshot and record expected source and destination counts before downstream reporting.
- Materialize `locations_clean` only if location-level analysis requires a standalone dimension, then add its foreign-key validation.
