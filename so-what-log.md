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

## 2026-06-15 · Shopify Retail Analytics · #grain
**Finding:** A unique-looking `ID` does not prove a table's business grain.
**Mechanism:** Shopify exports can repeat an entity across address, line-item, location, or option rows; the export structure determines what one row represents.
**Decision:** Define 1 explicit grain and 1 candidate primary key for every table before cleaning or joining it.
**Check:** Compare row count, distinct non-null key count, null-key count, and repeated rows' differing columns.
**Post:** Combine — use in a post about why source-table grain must be proven rather than assumed.

## 2026-06-16 · Shopify Retail Analytics · #customers
**Finding:** The customers export is not one row per customer: repeated customer GIDs appear in the raw data.
**Mechanism:** Customer details can be expanded across records, likely because address or contact fields vary while the customer entity remains the same.
**Decision:** Build `customers_clean` at exactly 1 row per `customer_id`, preserving `customers_raw` unchanged.
**Check:** Require `customers_clean["customer_id"].nunique() == len(customers_clean)` and document which row wins each duplicate group.
**Post:** Combine — supporting example for the table-grain and deduplication post.

## 2026-06-17 · Shopify Retail Analytics · #orders
**Finding:** The orders export mixes order-header fields with line-item fields, so repeated order IDs are expected rather than automatically bad duplicates.
**Mechanism:** One order can contain multiple `Line items: ID` values; dropping duplicate order IDs early would discard product-level sales detail.
**Decision:** Preserve 2 grains: one order-header table at 1 row per `order_id` and one order-line table at 1 row per `order_line_id`.
**Check:** Confirm order-level fields are constant within each `order_id` and every order line maps to exactly 1 order.
**Post:** Yes — strong concrete example of how dropping “duplicates” can silently destroy valid sales data.

## 2026-06-18 · Shopify Retail Analytics · #inventory
**Finding:** Inventory is a point-in-time snapshot, not a history, so stock at the time of a past order cannot be reconstructed directly.
**Mechanism:** Shopify exports current inventory while order lines record what sold; restocks and manual adjustments between those moments are absent.
**Decision:** Use 1 exported starting-inventory field if available; otherwise label `current stock + units sold` as an estimate, not observed inventory.
**Check:** Spot-check implied opening inventory against known reorders and flag any SKU affected by restocks or manual adjustments.
**Post:** Yes — useful standalone lesson on the limits of snapshot inventory data.

## 2026-06-19 · Shopify Retail Analytics · #variants
**Finding:** Product-level data is too coarse for size, color, SKU, price, and inventory analysis.
**Mechanism:** A product can have multiple sellable variants, while order lines and inventory reference variant-level IDs.
**Decision:** Add 1 `variants_clean` bridge between products, inventory, and order lines rather than forcing SKU-level facts onto products.
**Check:** Require each `variant_id` to map to exactly 1 `product_id` and 1 inventory item before using it in joins.
**Post:** Combine — include in a post explaining the Shopify analytical data model.

## 2026-06-20 · Shopify Retail Analytics · #raw-data
**Finding:** Cleaning in place makes it difficult to tell whether a surprising value came from Shopify or from the transformation code.
**Mechanism:** Overwriting loaded DataFrames removes the untouched comparison point needed for debugging and validation.
**Decision:** Keep 2 layers in the notebook: immutable `*_raw` tables and separate `*_work`/`*_clean` tables.
**Check:** Verify raw row counts and columns remain unchanged after every cleaning step.
**Post:** No — sound internal workflow, but too routine for a standalone post.

## 2026-06-21 · Shopify Retail Analytics · #keys
**Finding:** Shopify GIDs are useful source identifiers but awkward portable join keys.
**Mechanism:** Values such as `gid://shopify/Order/...` combine an entity type and numeric ID in one string.
**Decision:** Use 1 shared, entity-aware extraction function to create string IDs for every Shopify entity while retaining the original GID.
**Check:** Assert that every non-null source GID produces a non-null normalized ID and reject values that do not match the full expected pattern.
**Post:** Combine — technical detail for a broader post about making Shopify exports analysis-ready.

## 2026-06-22 · Shopify Retail Analytics · #data-model
**Finding:** The table grains and relationships must be finalized before analysis can be trusted.
**Mechanism:** The proposed model is `customers 1—< orders 1—< order lines >—1 variants >—1 products`, with inventory attached at the variant/inventory-item level.
**Decision:** Adopt the 5-entity analytical model only when every primary key is unique and every required foreign-key orphan rate is 0%.
**Check:** Measure primary-key uniqueness, null keys, foreign-key orphan counts, and rows per parent for every relationship.
**Post:** Yes — the five-entity model could anchor a practical Shopify data-modeling post.

## 2026-06-23 · Shopify Retail Analytics · #contracts
**Finding:** Duplicate removal rules must follow table grain; one blanket `drop_duplicates` rule is unsafe.
**Mechanism:** A repeated customer may need record selection, a repeated order may represent valid line expansion, and a repeated true product row may indicate an export issue.
**Decision:** Write 1 table-specific duplicate contract for customers, orders, products, variants, and inventory before producing final clean tables.
**Check:** For each table, record the target grain, primary key, duplicate rule, and an executable validation assertion.
**Post:** Yes — table-specific duplicate rules are broadly useful and counter the common “just drop duplicates” habit.

## 2026-06-24 · Shopify Retail Analytics · #naming
**Finding:** `Line items: ID` identifies an order line and uses the Shopify entity spelling `LineItem`.
**Mechanism:** The earlier `Lineitem` regex capitalization does not match the source GID, and `line_item_id` can be confused with a product rather than a row in an order.
**Decision:** Standardize on 1 name, `order_line_id`, extracted with the exact `LineItem` entity token.
**Check:** Compare non-null source IDs with extracted IDs and require `order_line_id` to be unique at the intended order-line grain.
**Post:** No — useful implementation detail, but too narrow to publish on its own.

## 2026-06-25 · Shopify Retail Analytics · #validation
**Finding:** Successful ID extraction is a prerequisite for deduplication and relationship tests.
**Mechanism:** A permissive regex can silently return missing IDs, causing false duplicates and false foreign-key orphans later.
**Decision:** Use 3 extraction-coverage assertions now—for orders, customers, and products—then add one for each remaining GID column.
**Check:** Require source non-null count to equal normalized-ID non-null count for every mapped entity field.
**Post:** Combine — include the assertions in a technical post about trustworthy key normalization.

## 2026-06-26 · Shopify Retail Analytics · #reproducibility
**Finding:** Loading the newest synced export is convenient for exploration but makes notebook results drift from day to day.
**Mechanism:** ISO-dated files sort chronologically, and `latest_file()` intentionally selects the last match whenever the notebook runs.
**Decision:** Keep 1 environment variable (`RETAIL_DATA_DIR`) for the local source path and freeze 1 dated raw snapshot before publishing analysis.
**Check:** Record the five selected source filenames and confirm a rerun against the frozen snapshot reproduces the same row counts.
**Post:** Yes — the tension between live exports and reproducible analysis is a useful standalone topic.

## 2026-06-27 · Shopify Retail Analytics · #pipeline
**Finding:** The cleaning notebook now loads five current Shopify sources and preserves raw copies, but the repeated-ID patterns still need semantic validation before clean tables are finalized.
**Mechanism:** Today's run loaded more rows than unique IDs in most exports: about 1.5 rows per customer ID, 2.0 per order ID, 1.4 per inventory item and 1.4 per variant, while products were exactly one row per ID.
**Decision:** Do not begin EDA or RFM until all 5 clean-table contracts pass their primary-key and relationship checks.
**Check:** Finish variant and inventory ID normalization, inspect what differs inside repeated-ID groups, and run the complete PK/FK validation suite.
**Post:** No — project-status checkpoint rather than a transferable insight.

## 2026-06-28 · Shopify Retail Analytics · #id-normalization
**Finding:** The five raw tables contain 14 GID-bearing fields needed to connect orders, customers, products, variants, inventory items, inventory levels, and locations.
**Mechanism:** Each field uses an entity-specific Shopify GID, so using one generic substring rule would hide entity mismatches and incomplete extraction.
**Decision:** Validate all 14 raw-to-normalized ID mappings through 1 shared coverage loop before testing table relationships.
**Check:** For every mapping, count non-null raw IDs, normalized IDs, and failed extractions; require the failed count to equal 0.
**Post:** Combine — evidence for the key-normalization post, not a standalone story.

## 2026-06-29 · Shopify Retail Analytics · #order-lines
**Finding:** `order_line_id` is fully populated but is not unique in the raw orders export.
**Mechanism:** The current snapshot has about two rows per order, and about 5% of rows repeat an order line ID through an expansion mechanism that is not yet confirmed.
**Decision:** Inspect at least 10 repeated `order_line_id` groups before choosing a deduplication rule or declaring the clean order-line grain.
**Check:** Compare every column within repeated groups, identify which fields vary, and verify whether each line still maps to exactly 1 order, product, and variant.
**Post:** Hold — potentially strong, but only after the repeated-line expansion mechanism is identified.

## 2026-06-30 · Shopify Retail Analytics · #order-line-grain
**Finding:** Repeated `order_line_id` rows preserve the retained order-line attributes but vary in nested child fields.
**Mechanism:** The raw Orders export flattens line items alongside fulfillments, returns, and shipping lines. `Fulfillments: ID` varied in the large majority of repeated-line groups, `Returns: ID` in 98, and `Shipping lines: ID` in 1.
**Decision:** Build `order_lines_clean` at exactly 1 row per `order_line_id`, exclude all 3 child-grain fields, and model fulfillment relationships separately.
**Check:** Derive the stability test from every retained order-line column, then require each clean `order_line_id` to be non-null and unique.
**Post:** Yes — this completes the story of why duplicate-looking rows must be explained at the source grain before they are removed.

## 2026-07-01 · Shopify Retail Analytics · #inventory-keys
**Finding:** The numeric component of an Inventory Level GID repeats across different inventory items, so it is not a valid standalone primary key.
**Mechanism:** Shopify encodes Inventory Level as a parameterized GID containing both a level component and its parent inventory item.
**Decision:** Use the 2-column key `(inventory_item_id, inventory_level_id)` for the current snapshot; add `snapshot_at` as a third key column when daily history is retained.
**Check:** Require 0 null composite-key rows and 0 duplicated composite-key rows before building `inventory_levels_clean`.
**Post:** Yes — a compact example of why parsing an ID is not the same as proving key uniqueness.

## 2026-07-02 · Shopify Retail Analytics · #source-drift
**Finding:** The latest Shopify export changed the working counts even though the cleaning logic stayed the same.
**Mechanism:** `latest_file()` pulled the newest synced files; the current Orders snapshot still has about two rows per order and about 1.9 order lines per order.
**Decision:** Treat development runs as moving snapshots and keep dated source filenames visible in the notebook output.
**Check:** Compare raw row counts, distinct ID counts, and selected source filenames before interpreting any downstream metric movement.
**Post:** Combine — supports the reproducibility post about why “latest” and “publishable” are different modes.

## 2026-07-03 · Shopify Retail Analytics · #id-qa
**Finding:** The ID QA loop now covers 15 raw-to-normalized mappings, including fulfillment IDs.
**Mechanism:** Orders, customers, products, variants, and inventory each provide entity-specific GIDs, and fulfillment IDs add another child entity nested in Orders.
**Decision:** Keep fulfillment ID normalization inside the shared validation table instead of checking it manually.
**Check:** Require all 15 mappings to show `failed = 0`; the current run passes every mapping, including every non-null fulfillment ID.
**Post:** Combine — useful proof for a broader post on auditable key normalization.

## 2026-07-04 · Shopify Retail Analytics · #inventory-levels
**Finding:** The Inventory Level composite key passes on the current snapshot.
**Mechanism:** `inventory_item_id + inventory_level_id` identifies every inventory-level row, with no null-key rows and no duplicate-key rows.
**Decision:** Keep this as the current-state inventory-level primary key until a dated inventory history is introduced.
**Check:** Display the composite-PK check table and assert both `null_key_rows == 0` and `duplicate_key_rows == 0`.
**Post:** Hold — good technical evidence, but it overlaps with the July 1 inventory-key story.

## 2026-07-05 · Shopify Retail Analytics · #fulfillments
**Finding:** Fulfillments belong in their own child table rather than inside order lines.
**Mechanism:** The Orders export repeats fulfillment IDs across flattened order rows, but the retained fulfillment grain is one `fulfillment_id` associated with one `order_id`.
**Decision:** Build `fulfillments_clean` from only `fulfillment_id` and `order_id`, dropping null fulfillment rows and duplicate pairs.
**Check:** The current `fulfillments_clean` has 0 null fulfillment IDs, 0 duplicate fulfillment IDs, and 0 null order IDs.
**Post:** Yes — a practical example of separating nested operational events from sales-line facts.

## 2026-07-06 · Shopify Retail Analytics · #orders-clean
**Finding:** Order headers can be separated from the expanded Orders export once order-level fields are selected deliberately.
**Mechanism:** Raw order rows repeat because of order lines and child records, while the clean header table should contain exactly one row per `order_id`.
**Decision:** Build `orders_clean` from approved order-header columns and deduplicate after excluding line, fulfillment, return, and shipping-grain fields.
**Check:** The current `orders_clean` has 0 null order IDs and 0 duplicate order IDs.
**Post:** Combine — pair with the order-line duplicate story as the “split the grain before summing” lesson.

## 2026-07-07 · Shopify Retail Analytics · #relationships
**Finding:** The first cleaned order-family tables now connect without orphaned order references.
**Mechanism:** `order_lines_clean` and `fulfillments_clean` both retain `order_id`, so their foreign keys can be checked directly against `orders_clean`.
**Decision:** Require 0 orphan rows before using order lines or fulfillments in EDA, RFM, or fulfillment analysis.
**Check:** The current run reports 0 order-line orphan rows and 0 fulfillment orphan rows.
**Post:** No — important validation checkpoint, but not enough narrative by itself.

## 2026-07-08 · Shopify Retail Analytics · #data-contracts
**Finding:** The project now needs more than the original five clean tables because source exports contain nested entities.
**Mechanism:** Orders split into orders, order lines, and fulfillments; inventory splits into inventory items, inventory levels, and locations.
**Decision:** Document 9 planned analytical tables and their target grains in `notes.md`: customers, orders, order lines, products, variants, inventory items, inventory levels, locations, and fulfillments.
**Check:** For every table, record target grain, primary key, duplicate rule, and validation expectations before building analysis notebooks.
**Post:** Yes — this is a strong “source exports are not the analytical model” post.

## 2026-07-09 · Shopify Retail Analytics · #content-pipeline
**Finding:** Several so-what entries are already strong enough to become publishable LinkedIn drafts.
**Mechanism:** Entries marked `Post: Yes` have a transferable lesson, concrete mechanism, and a check or number; weaker entries are better used as supporting evidence.
**Decision:** Gather the `Post: Yes` items into `linkedin-post-drafts.md` and turn them into reusable draft posts.
**Check:** Confirm the number of Yes entries matches the number of drafted posts before publishing or scheduling.
**Post:** No — meta-work about the content pipeline, not a public analytics lesson.

## 2026-07-10 · Shopify Retail Analytics · #current-status
**Finding:** The cleaning work has moved from raw ID normalization into validated clean-table construction for the order family.
**Mechanism:** The notebook now has passing checks for ID coverage, inventory-level composite keys, order-line uniqueness, fulfillment uniqueness, order-header uniqueness, and order-family foreign keys.
**Decision:** Next focus should stay on unresolved grains: customers expanded by addresses, variants expanded by selected options, and inventory split into item/location/location-level tables.
**Check:** Before starting EDA or RFM, run the notebook top to bottom and require all clean-table PK/FK assertions to pass.
**Post:** No — current project status and next-step control point.

## 2026-07-11 · Shopify Retail Analytics · #customers-clean
**Finding:** The clean customer table now satisfies its intended grain of one row per customer.
**Mechanism:** Selecting customer-level fields removed the address expansion from the clean table while retaining the normalized Shopify customer key.
**Decision:** Use `customers_clean` as the customer dimension at exactly 1 row per `customer_id`; do not manufacture an “unknown customer” record for orders whose customer ID is null.
**Check:** The current table has 0 null customer IDs and 0 duplicate customer IDs. Of the clean orders, under 1% have no customer ID and 0 have an unmatched non-null customer ID.
**Post:** Yes — a useful example of why a null foreign key and a broken foreign key are different data-quality conditions.

## 2026-07-11 · Shopify Retail Analytics · #sales-geography
**Finding:** A customer's saved address is not the best basis for attributing sales by city or state.
**Mechanism:** Customer addresses can change or multiply over time, while an order's shipping address describes the destination of that specific transaction.
**Decision:** Add shipping city and state to the Orders source and carry them into `orders_clean`; defer a separate customer-address table until customer-location analysis requires it.
**Check:** Confirm shipping fields are stable within each raw `order_id`, then report their null counts before using them in the Streamlit regional-sales views.
**Post:** Yes — this distinction between customer geography and transaction geography is directly relevant to dashboard metric design.

## 2026-07-30 · Shopify Retail Analytics · #inventory-grain
**Finding:** Repeated inventory-item IDs represent valid location assignments, not duplicate inventory items.
**Mechanism:** The current snapshot contains about 1.4 item-location rows per inventory item across 3 locations; about 21% of items appear at more than one location, while retained item attributes remain stable across those rows.
**Decision:** Split the export into `inventory_items_clean` at 1 row per `inventory_item_id` and `inventory_levels_clean` at 1 row per `(inventory_item_id, location_id)`.
**Check:** The current run has 0 null keys, 0 duplicate item-location keys, 0 conflicting item attributes, and 0 inventory-level orphan rows.
**Post:** Yes — a clear example of proving that repeated IDs encode a relationship before deduplicating them.

## 2026-07-30 · Shopify Retail Analytics · #variant-inventory
**Finding:** Shopify variants and inventory items form a one-to-one relationship in the current export.
**Mechanism:** Both clean tables have the same row count, and each populated key resolves uniquely in both directions.
**Decision:** Keep variants and inventory items as separate entities connected by `inventory_item_id`; do not merge their grains just because the current relationship is one-to-one.
**Check:** Require 0 null or unmatched variant references, 0 duplicate variant assignments in inventory items, and 0 duplicate inventory-item assignments in variants. The current run passes all checks.
**Post:** Combine — useful evidence for the broader Shopify analytical-model post.

## 2026-07-30 · Shopify Retail Analytics · #semantic-validation
**Finding:** Unique keys and valid foreign keys are necessary but do not prove that order facts are analytically valid.
**Mechanism:** Timestamps, quantities, prices, discounts, totals, and currencies can violate business rules even when every row joins correctly.
**Decision:** Add executable semantic contracts after structural PK/FK checks: timestamps must parse and follow event order; quantities must be non-negative and internally bounded; monetary components must reconcile within $0.01; currencies must be present and consistent.
**Check:** The July 30 run has 0 timestamp conversion failures, 0 orders updated or cancelled before creation, 0 invalid quantity relationships, 0 monetary reconciliation failures, and 0 missing or inconsistent order-line currencies.
**Post:** Yes — strong reminder that referential integrity is only one layer of data quality.

## 2026-07-30 · Shopify Retail Analytics · #current-status
**Finding:** The cleaning notebook now constructs and validates the core customer, order, catalog, and inventory tables from the latest exports.
**Mechanism:** The July 30 snapshot produces all eight clean tables; all displayed PK/FK and semantic assertions pass.
**Decision:** Treat the cleaning model as analysis-ready for the checks currently implemented, then finish the standalone location dimension and persist a frozen snapshot before publishing metrics.
**Check:** Rerun `notebooks/01_clean.ipynb` top to bottom, require every assertion to pass, record the five selected source filenames, and confirm downstream notebooks use the same frozen outputs.
**Post:** No — project-status checkpoint and handoff into analysis.

## 2026-08-01 · Shopify Retail Analytics · #data-types
**Finding:** Valid keys and relationships are not enough for warehouse loading when clean columns still carry ambiguous pandas types.
**Mechanism:** CSV inputs can leave timestamps as strings, nullable identifiers such as phone and SKU as numeric-looking values, and integer measures in types that do not preserve missingness cleanly.
**Decision:** Validate timestamp conversions before assignment and normalize identifiers, integer measures, booleans, strings, and monetary values to types that match their analytical meaning.
**Check:** The notebook asserts zero populated timestamp conversion failures and checks converted identifier strings for literal missing-value tokens and unwanted trailing `.0` values.
**Post:** Combine — type normalization is the bridge between clean DataFrames and a typed warehouse.

## 2026-08-04 · Shopify Retail Analytics · #warehouse-handoff
**Finding:** Clean DataFrames need a stable external contract before they can be loaded consistently into Snowflake.
**Mechanism:** Source-style column labels with spaces and punctuation do not match the warehouse schema, and keeping unused analysis notebooks makes unfinished work look current.
**Decision:** Rename all 8 clean tables to consistent snake_case columns, export them as named CSVs in `data/clean`, and remove unused analysis notebooks until validated downstream work exists.
**Check:** `01_clean.ipynb` defines the 8-table export loop; the August 4 commit removes the unused EDA, RFM, margin, sales-trend, and product/vendor notebooks.
**Post:** No — project handoff and scope-control milestone.

## 2026-08-05 · Shopify Retail Analytics · #snowflake-model
**Finding:** The validated Python model needs an explicit warehouse schema rather than relying on CSV inference.
**Mechanism:** IDs, timestamps, booleans, quantities, and money have different storage and relationship requirements that a generic file load cannot express safely.
**Decision:** Create `RETAIL_DB.CORE` and define typed Snowflake tables for the 8 clean entities, including their primary- and foreign-key declarations.
**Check:** `00_setup.sql` creates the database and schema; `01_create_tables.sql` defines all 8 tables with timestamp, numeric, boolean, key, and relationship contracts.
**Post:** Combine — the warehouse schema makes the Python data contracts durable.

## 2026-08-05 · Shopify Retail Analytics · #snowflake-loading
**Finding:** Moving validated Python outputs into Snowflake requires a controlled snapshot-replacement sequence.
**Mechanism:** Eight clean CSVs are uploaded to an internal stage and loaded into typed `RETAIL_DB.CORE` tables; stale staged files or partial loads could mix snapshots.
**Decision:** Confirm all 8 staged files, truncate in child-to-parent order, preflight each file with `VALIDATION_MODE = 'RETURN_ALL_ERRORS'`, and load with `ON_ERROR = 'ABORT_STATEMENT'`.
**Check:** `02_load_tables.sql` includes preflight, load, and post-load row-count statements for all 8 clean tables.
**Post:** Yes — warehouse loading is part of the data contract, not just file movement.

## 2026-08-08 · Shopify Retail Analytics · #referential-integrity
**Finding:** Declaring Snowflake foreign keys documents the model but does not replace explicit integrity testing.
**Mechanism:** Optional customer references and nullable historical catalog references must be distinguished from populated keys that fail to resolve.
**Decision:** Count null and unmatched foreign keys separately for every modeled relationship.
**Check:** `03_validate_tables.sql` covers orders→customers, order lines→orders/products/variants, variants→products/inventory items, inventory items→variants, inventory levels→inventory items, and fulfillments→orders. Snowflake result counts are not stored in the repository, so none are claimed.
**Post:** Yes — declared constraints and measured integrity answer different questions.

## 2026-08-29 · Shopify Retail Analytics · #semantic-validation
**Finding:** The notebook's order-line business rules now have warehouse-side equivalents.
**Mechanism:** Valid joins can still contain impossible quantities or monetary components that do not reconcile.
**Decision:** Validate quantity bounds, require discounted totals not to exceed original totals, and reconcile both discount arithmetic and unit-price extensions within $0.01 in Snowflake.
**Check:** The queries are implemented in `03_validate_tables.sql`; their Snowflake result set is not stored in the repository.
**Post:** Yes — semantic checks should follow the data into the warehouse.

## 2026-08-29 · Shopify Retail Analytics · #currency
**Finding:** Correct arithmetic is not enough unless the compared amounts share a populated currency.
**Mechanism:** Each order line carries four shop-money currency fields, and a missing, mixed, or unexpected code can invalidate a reconciliation.
**Decision:** Require `unit_price_currency`, `original_total_currency`, `discounted_total_currency`, and `total_discount_currency` to be populated and equal to the current shop-currency contract of `USD`.
**Check:** The saved notebook run records only `USD` and 0 missing or inconsistent line-currency rows; Snowflake now has a matching invalid-row query, but its result is not stored.
**Post:** Yes — currency is part of a monetary value's meaning, not display metadata.
