# First dbt mart: daily sales

Run commands from the repository root. dbt reads already-published CORE tables;
it does not ingest CSVs or execute the retail_batch publisher.

```sh
venv/bin/python -m pip install -r requirements-dbt.txt
venv/bin/python dbt/run.py parse
venv/bin/python dbt/run.py debug
venv/bin/python dbt/run.py build
```

`parse` checks the project's SQL references and YAML configuration without executing
warehouse queries. `debug` tests credentials/connectivity. `build` creates views
and runs tests in dependency order. These views live in RETAIL_DB.ANALYTICS_DEV;
CORE remains a read-only source for dbt. The Snowflake role needs read access to
CORE and permission to create the development schema/views and use the warehouse.
The wrapper loads the existing .env without printing credentials. profiles.yml is
safe to commit: it contains environment-variable references, not actual secrets.

The dependency graph is:

```
CORE.ORDERS ------> stg_orders ------\
                                    int_orders_with_lines --> mart_daily_sales
CORE.ORDER_LINES -> stg_order_lines-/
```

A model is a SELECT saved in a .sql file. dbt wraps it in CREATE VIEW according
to dbt_project.yml. `source('retail_core', 'orders')` identifies an existing external
table; `ref('stg_orders')` identifies another model and declares a dependency.
Models execute in dependency order, not filename order. Source/model YAML defines
documentation and tests; it does not create or reload CORE tables.

Files and responsibilities:
- dbt_project.yml: project identity, paths, and default view materialization.
- profiles.yml: development connection and destination schema.
- models/staging/sources.yml: the two existing CORE sources and source tests.
- models/staging/stg_*.sql: explicit source columns without business aggregation.
- models/intermediate/int_orders_with_lines.sql: one non-test order per row.
- models/marts/mart_daily_sales.sql: your daily aggregation and average.
- models/models.yml: model descriptions and key/null checks.
- tests/*.sql: failing-row queries; zero rows means pass.

Your query's most important safeguard is aggregating order lines BEFORE joining
orders. Joining raw lines to order money would repeat each order's dollar values.
The intermediate model has a unique order_id test to protect this grain. Missing
line summaries remain NULL and fail tests rather than being silently replaced by zero.

Metric contract:
- One row per America/Chicago order-creation date with at least one non-test order.
  No calendar spine means no rows for dates without orders.
- Overall counts and values include cancelled/unpaid/refunded non-test orders.
- identified_customer_count counts distinct known customers, not identified orders.
- completed means currently PAID or PARTIALLY_REFUNDED and not cancelled, preserving
  the supplied query. It is not a complete accounting definition of revenue.
- Partially refunded orders contribute their full order_total. There is no refund
  amount/date model yet; this is NOT net sales or a cash collections ledger.
- Merchandise subtotal already reflects merchandise discounts. Recorded discounts
  are informational and must not be subtracted again.
- Money is in shop USD, not customer presentment currency. Monetary column names
  such as tax_collected retain the submitted query's labels; they do not establish
  that cash was actually collected.
- Statuses describe the current snapshot. Historical date totals can change as
  orders are updated. A view is not a preserved historical snapshot.
- COUNT_IF completion/fulfillment counts are normalized to zero; the completed
  average is NULL when no order qualifies.
- No ORDER BY in the view: consumers must explicitly request sorting.

Query the result after a successful build:

```sql
SELECT *
FROM RETAIL_DB.ANALYTICS_DEV.MART_DAILY_SALES
ORDER BY sales_date DESC;
```

Tests cover source/model keys, required fields, order-line parent relationships,
USD order totals, missing line summaries, per-day counts/values reconciled directly
to order headers, and metric arithmetic. Daily amount reconciliation allows up to
one cent per order because the ingestion contract allows one cent per order.
`dbt build` is NOT an atomic publish of all models: a failed test does not roll
back views already created. Keep this development schema separate from production.
Tests also run only when invoked; views reflect subsequent CORE changes immediately.

After reviewing these definitions and a passing development build, add refund
facts and clarify the desired paid-sales measure before presenting a net-sales KPI.
Schedule dbt build after successful batch publication, without overlapping loads.
