## Retail Store Analytics -- Project Notes

## Project context
- Source: Shopify export files synced locally from Google Drive each day.
- Files are read from the local synced folder rather than the Drive API so the workflow stays simple and reproducible on a single laptop.
- Each table is stored in its own folder, and file names use an ISO date prefix so alphabetical order matches chronological order.
- Each export is a full snapshot (customers and orders go back to 2022), not a daily change file. The pipeline therefore publishes complete snapshots and rejects incremental batches.

## Pipeline overview
```
5 Shopify CSV exports
  -> retail_batch (Python): clean, normalize IDs, grain and type checks
  -> 8 clean CSVs + SHA-256 hashes + report.json   (local run folder)
  -> --live only: Snowflake stage -> INCOMING tables -> 03_validate_tables.sql
  -> pass: transactional publish to CORE   |   fail: CORE untouched
  -> dbt: staging -> intermediate -> mart_daily_sales (+ tests)
```

## Intake approach
- The batch runner (`python -m retail_batch`) takes an explicit `--batch-date` and a `--manifest` file. It does not pick the newest file.
- The manifest (`batch.json`) must declare the same batch date, `mode: full_snapshot` and `complete: true`. Code cannot prove that Shopify's exporter finished, so the manifest records that human check.
- Exactly one export prefixed with the batch date must exist in each of `Dim_Customers`, `Fact_Orders`, `Dim_Products`, `Dim_Variants` and `Dim_Inventory`. Missing, ambiguous, empty or changing files fail the batch. Each file is hashed before and after reading to catch changes mid-read.
- Settings and the data folder come from `.env` (`RETAIL_DATA_DIR`). `--data-dir` overrides the source folder.
- Cleaning lives in `retail_batch/clean.py`, extracted from `notebooks/01_clean.ipynb` with its assertions kept. Running Python with `-O` is refused, because it would disable those assertions.
- Clean CSV column order is checked against the Snowflake table definitions in `sql/core/01_create_tables.sql` before anything is written.
- Without `--live`, a run is a local rehearsal: it writes 8 CSVs, `clean.log` and `report.json` to a new folder `data/batches/<date>/<run-id>/` and stops at status `local_checks_passed`. Snowflake is never touched.
- A filesystem lock (`data/batch.lock`) prevents two runs from this workspace at the same time.
- Working principle: prove the grain first, then build the analytical tables from it.

## Working grain and data model
- A table is treated as one row per entity only after its key and grain have been verified.
- Five exports become eight clean tables:
  - `customers`: one row per customer
  - `orders`: one row per order
  - `order_lines`: one row per order line
  - `fulfillments`: one row per fulfillment
  - `products`: one row per product
  - `variants`: one row per sellable variant
  - `inventory_items`: one row per inventory item
  - `inventory_levels`: one row per inventory item and Shopify location
- `locations` is not a standalone table. The three validated locations are carried on `inventory_levels`.

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
- Validation: `customer_id` must be non-null and unique

### Orders
- Raw grain: order-level row with repeated values due to line-item and child-record expansion
- Clean grain: one row per `order_id`+

- Key: `order_id`
- Duplicate rule: use order-header fields only and exclude child-grain expansion from the clean table
- Validation: `order_id` must be non-null and unique

### Order lines
- Raw grain: one row per order line, with repeated IDs when nested child fields are flattened
- Clean grain: one row per `order_line_id`
- Key: `order_line_id`
- Duplicate rule: remove repeated child-grain rows and keep a single row per line
- Validation: `order_line_id` must be non-null and unique

### Fulfillments
- Raw grain: fulfillment child records embedded in the orders export
- Clean grain: one row per `fulfillment_id`
- Key: `fulfillment_id`
- Duplicate rule: drop null-parent fulfillment rows and preserve one row per fulfillment ID
- Validation: `fulfillment_id` must be non-null and unique

### Products and variants
- Raw grain: product and variant details may be mixed in the same export
- Clean grain: one row per product and one row per variant
- Keys: `product_id` and `variant_id`
- Duplicate rule: remove true duplicates and keep one logical row per entity
- Validation: each key must be non-null and unique in its table

### Inventory items
- Raw grain: inventory-item attributes repeated across location-level quantity rows
- Clean grain: one row per `inventory_item_id`
- Key: `inventory_item_id`
- Duplicate rule: retain only item-level attributes after proving they are stable across locations
- Validation: the key must be non-null and unique, retained attributes must not conflict across locations, and `variant_id` must resolve uniquely to variants

### Inventory levels
- Raw and clean grain: one row per inventory item and Shopify location in the current snapshot
- Key: (`inventory_item_id`, `location_id`), consistent across the notebook, the cleaning module and the SQL
- Duplicate rule: do not deduplicate repeated inventory-item IDs; they represent valid location assignments
- Validation: both key columns must be populated, the composite key must be unique, and every inventory item must resolve to inventory items
- Limitation: this is current state, not historical inventory; add `snapshot_at` to the key if dated inventory history is kept

## Relationships and join rules
- Customer-to-order: optional on guest orders, but populated customer IDs must resolve to a customer.
- Order-to-order-lines and order-to-fulfillments: strict parent-child relationships.
- Order lines to products and variants: populated references must resolve; historical lines with null catalog references are kept and counted.
- Variant-to-inventory-item: one-to-one in both directions.
- Inventory-level-to-inventory-item: many-to-one with zero orphan rows.

## Snowflake load, validation and publish (`--live`)
- One command runs the whole warehouse step: `python -m retail_batch --batch-date YYYY-MM-DD --manifest batch.json --live`.
- Clean files are uploaded to `RETAIL_DB.CORE.CLEAN_CSV_STAGE` under a unique run prefix. Stage files are kept for audit.
- `COPY INTO` runs a preflight check (`VALIDATION_MODE = 'RETURN_ALL_ERRORS'`) on all eight files before loading. Any preflight error blocks the load and is saved to the report.
- Data loads into freshly recreated `INCOMING` tables, never straight into CORE.
- Every check in `sql/core/03_validate_tables.sql` runs against INCOMING:
  - row counts, which must equal the local counts
  - null and duplicate primary keys, including the composite inventory-level key
  - null-versus-unmatched foreign keys for orders → customers; order lines → orders, products and variants; variants → products and inventory items; inventory items → variants; inventory levels → inventory items; fulfillments → orders
  - order-line quantity rules (`fulfillable_quantity <= unfulfilled_quantity <= quantity`, quantity positive)
  - $0.01-tolerance money reconciliations (`original_total - total_discount = discounted_total`, `unit_price * quantity = original_total`)
  - a currency contract requiring all four order-line currency fields to equal `USD`
- **Observations vs. blocking checks:** guest orders with no customer ID, null historical catalog references, and negative on-hand or available inventory are real business facts. They are recorded as observations. A populated reference that matches nothing fails the batch.
- Only a passing batch is published. `sql/core/04_publish_tables.sql` replaces all eight CORE tables inside one `BEGIN TRANSACTION … COMMIT`, so CORE never holds a half-loaded batch, and a publish error rolls back.
- The destructive table setup script (`01_create_tables.sql`) is never run automatically.
- Reruns replace the full snapshot, so running the same batch twice does not append duplicates.
- Every run writes `report.json` with status, source file names, SHA-256 hashes of sources and outputs, and row counts. Failed runs keep a failure report. Two independent local runs on the same batch produced identical output hashes.

## dbt analytics layer
- dbt reads the published CORE tables; it does not load CSVs or run the batch publisher.
- Models build as views in `RETAIL_DB.ANALYTICS_DEV`, and CORE stays read-only for dbt.
- Model chain: `stg_orders` + `stg_order_lines` → `int_orders_with_lines` (one non-test order with aggregated line measures) → `mart_daily_sales` (one row per sales date).
- Tests: unique and not-null keys on every model, plus two singular tests. `daily_sales_consistency` catches impossible daily counts, amounts and averages; `daily_sales_reconciles` re-aggregates CORE order headers independently to catch dropped orders, duplicates and join fan-out.
- Run with `venv/bin/python dbt/run.py build`. The wrapper loads `.env` without printing credentials. dbt packages are installed from `requirements-dbt.txt`.
- No saved dbt build result is stored in the repository.

## Repository guardrails
- `.env` holds credentials and paths and is gitignored. `.env.example` lists the required settings with placeholders. Snowflake sign-in uses key-pair authentication with a private `.p8` key file, not a password.
- `.gitignore` (Layer 1) blocks data exports (`*.csv`, `*.xlsx`, `*.parquet`), keys and certificates (`*.p8`, `*.pem`, `*.key`), `data/`, `batch.json` and `.sensitive-patterns` anywhere in the repo.
- `.pre-commit-config.yaml` (Layer 3) runs before every commit: gitleaks (secret formats), nbstripout (notebook outputs), large-file (500 KB), private-key and merge-conflict checks, and `scripts/check_sensitive.py` (emails, phone numbers and private terms).
- Python dependencies are split: `requirements.txt` for the batch runner, and `requirements-dbt.txt`, which includes it via `-r` and adds dbt.

## Testing
- `python -m unittest discover -s tests -v` runs eight unit tests in `tests/test_batch.py`. They cover detection of all eight COPY statements, orphans blocking validation, optional null catalog references, required variant references, count mismatches, reconciliation failures, rollback on publish failure, and preflight errors blocking the load.
- dbt schema and singular tests run with `dbt/run.py build`.

## Key decisions made so far
- Full snapshot replacement instead of incremental loads, because the exports carry full history. Tradeoff: run cost grows with history.
- Validate in INCOMING before publishing to CORE. Tradeoff: extra tables and a slower run, in exchange for CORE never holding a failed batch.
- Use a manifest as the completeness gate. Tradeoff: a manual step, made explicit instead of assumed.
- Use the order's shipping geography for sales-location analysis rather than a customer's saved address.
- Keep null customer IDs as null rather than inventing an unknown-customer record; treat guest purchases as observations, not failures.
- Use `(inventory_item_id, location_id)` as the business key for current inventory levels; keep `inventory_level_id` for source traceability.
- Run semantic checks after structural checks: timestamps must be ordered, quantities internally consistent, money reconciled within $0.01, and line currencies in agreement.
- Single writer: run only one loader at a time. The shared INCOMING tables do not isolate runs from different machines or checkouts.

## Current status — 2026-11-27
- The Python batch runner is complete, with unit tests.
- Live batches have been published to CORE: local run reports show status `published` for the November 10, 11 and 15 batches.
- A November 20 run failed locally with an `AttributeError` after cleaning finished. It has not been investigated yet.
- The dbt layer (two staging models, one intermediate model, `mart_daily_sales`, and tests) is implemented.
- Run artifacts under `data/batches/` are private and gitignored, so none of these results are stored in the repository.

## Open questions and remaining work
- Investigate and fix the November 20 batch failure.
- Add cross-host locking and stale-batch protection, so an older batch cannot be published over a newer one by mistake.
- Add more marts: customers and RFM, products and vendors, inventory.
- Add orchestration and CI/CD around the existing data contracts.
- Add order-header, customer and inventory currency checks where money values are compared, and Snowflake timestamp and event-order checks to mirror the notebook.
- Add a dependency lock file so installs are reproducible across machines.
- Decide whether location-level analysis needs a standalone `locations` table and its foreign-key check.
- How should selected variant options be normalized if option-level analysis needs more than the current variant table?
- What snapshot cadence and retention policy should turn current inventory state into history?
- How should customer-address history be handled if location analysis expands beyond shipping geography?
- Should fulfillments stay a minimal order bridge or gain event-level attributes for operational analysis?
- Settle guest-checkout handling before treating customer-level RFM results as final.
