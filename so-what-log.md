# So What Log
*Working log of friction points, discoveries, and key details. Finding → mechanism → decision (with a number) → check.*

<!-- TEMPLATE — copy this block for each new day
## YYYY-MM-DD · source · #tag
**Finding:** 
**Mechanism:** 
**Decision:** 
**Check:** 
**Post:** 
-->

## 2026-06-15 · Retail Business · #grain
**Finding:** A unique-looking `ID` does not prove a table's business grain.
**Mechanism:** Shopify exports can repeat an entity across address, line-item, location, or option rows; the export structure determines what one row represents.
**Decision:** Define 1 explicit grain and 1 candidate primary key for every table before cleaning or joining it.
**Check:** Compare row count, distinct non-null key count, null-key count, and repeated rows' differing columns.
**Post:** maybe

## 2026-06-16 · Retail Business · #customers
**Finding:** The customers export is not one row per customer: repeated customer GIDs appear in the raw data.
**Mechanism:** Customer details can be expanded across records, likely because address or contact fields vary while the customer entity remains the same.
**Decision:** Build `customers_clean` at exactly 1 row per `customer_id`, preserving `customers_raw` unchanged.
**Check:** Require `customers_clean["customer_id"].nunique() == len(customers_clean)` and document which row wins each duplicate group.
**Post:** maybe

## 2026-06-17 · Retail Business · #orders
**Finding:** The orders export mixes order-header fields with line-item fields, so repeated order IDs are expected rather than automatically bad duplicates.
**Mechanism:** One order can contain multiple `Line items: ID` values; dropping duplicate order IDs early would discard product-level sales detail.
**Decision:** Preserve 2 grains: one order-header table at 1 row per `order_id` and one order-line table at 1 row per `order_line_id`.
**Check:** Confirm order-level fields are constant within each `order_id` and every order line maps to exactly 1 order.
**Post:** maybe

## 2026-06-18 · Retail Business · #inventory
**Finding:** Inventory is a point-in-time snapshot, not a history, so stock at the time of a past order cannot be reconstructed directly.
**Mechanism:** Shopify exports current inventory while order lines record what sold; restocks and manual adjustments between those moments are absent.
**Decision:** Use 1 exported starting-inventory field if available; otherwise label `current stock + units sold` as an estimate, not observed inventory.
**Check:** Spot-check implied opening inventory against known reorders and flag any SKU affected by restocks or manual adjustments.
**Post:** maybe

## 2026-06-19 · Retail Business · #variants
**Finding:** Product-level data is too coarse for size, color, SKU, price, and inventory analysis.
**Mechanism:** A product can have multiple sellable variants, while order lines and inventory reference variant-level IDs.
**Decision:** Add 1 `variants_clean` bridge between products, inventory, and order lines rather than forcing SKU-level facts onto products.
**Check:** Require each `variant_id` to map to exactly 1 `product_id` and 1 inventory item before using it in joins.
**Post:** maybe

## 2026-06-20 · Retail Business · #raw-data
**Finding:** Cleaning in place makes it difficult to tell whether a surprising value came from Shopify or from the transformation code.
**Mechanism:** Overwriting loaded DataFrames removes the untouched comparison point needed for debugging and validation.
**Decision:** Keep 2 layers in the notebook: immutable `*_raw` tables and separate `*_work`/`*_clean` tables.
**Check:** Verify raw row counts and columns remain unchanged after every cleaning step.
**Post:** maybe

## 2026-06-21 · Retail Business · #keys
**Finding:** Shopify GIDs are useful source identifiers but awkward portable join keys.
**Mechanism:** Values such as `gid://shopify/Order/...` combine an entity type and numeric ID in one string.
**Decision:** Use 1 shared, entity-aware extraction function to create string IDs for every Shopify entity while retaining the original GID.
**Check:** Assert that every non-null source GID produces a non-null normalized ID and reject values that do not match the full expected pattern.
**Post:** maybe

## 2026-06-22 · Retail Business · #data-model
**Finding:** The table grains and relationships must be finalized before analysis can be trusted.
**Mechanism:** The proposed model is `customers 1—< orders 1—< order lines >—1 variants >—1 products`, with inventory attached at the variant/inventory-item level.
**Decision:** Adopt the 5-entity analytical model only when every primary key is unique and every required foreign-key orphan rate is 0%.
**Check:** Measure primary-key uniqueness, null keys, foreign-key orphan counts, and rows per parent for every relationship.
**Post:** maybe

## 2026-06-23 · Retail Business · #contracts
**Finding:** Duplicate removal rules must follow table grain; one blanket `drop_duplicates` rule is unsafe.
**Mechanism:** A repeated customer may need record selection, a repeated order may represent valid line expansion, and a repeated true product row may indicate an export issue.
**Decision:** Write 1 table-specific duplicate contract for customers, orders, products, variants, and inventory before producing final clean tables.
**Check:** For each table, record the target grain, primary key, duplicate rule, and an executable validation assertion.
**Post:** maybe

## 2026-06-24 · Retail Business · #naming
**Finding:** `Line items: ID` identifies an order line and uses the Shopify entity spelling `LineItem`.
**Mechanism:** The earlier `Lineitem` regex capitalization does not match the source GID, and `line_item_id` can be confused with a product rather than a row in an order.
**Decision:** Standardize on 1 name, `order_line_id`, extracted with the exact `LineItem` entity token.
**Check:** Compare non-null source IDs with extracted IDs and require `order_line_id` to be unique at the intended order-line grain.
**Post:** maybe

## 2026-06-25 · Retail Business · #validation
**Finding:** Successful ID extraction is a prerequisite for deduplication and relationship tests.
**Mechanism:** A permissive regex can silently return missing IDs, causing false duplicates and false foreign-key orphans later.
**Decision:** Use 3 extraction-coverage assertions now—for orders, customers, and products—then add one for each remaining GID column.
**Check:** Require source non-null count to equal normalized-ID non-null count for every mapped entity field.
**Post:** maybe

## 2026-06-26 · Retail Business · #reproducibility
**Finding:** Loading the newest synced export is convenient for exploration but makes notebook results drift from day to day.
**Mechanism:** ISO-dated files sort chronologically, and `latest_file()` intentionally selects the last match whenever the notebook runs.
**Decision:** Keep 1 environment variable (`RETAIL_DATA_DIR`) for the local source path and freeze 1 dated raw snapshot before publishing analysis.
**Check:** Record the five selected source filenames and confirm a rerun against the frozen snapshot reproduces the same row counts.
**Post:** maybe

## 2026-06-27 · Retail Business · #pipeline
**Finding:** The cleaning notebook now loads five current Shopify sources and preserves raw copies, but the repeated-ID patterns still need semantic validation before clean tables are finalized.
**Mechanism:** Today's run loaded N customer rows/N IDs, N order rows/N IDs, N product rows/N IDs, N inventory rows/N IDs, and N variant rows/N IDs.
**Decision:** Do not begin EDA or RFM until all 5 clean-table contracts pass their primary-key and relationship checks.
**Check:** Finish variant and inventory ID normalization, inspect what differs inside repeated-ID groups, and run the complete PK/FK validation suite.
**Post:** maybe
