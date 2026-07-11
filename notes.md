## Retail Store Analytics -- Project Notes

## Data Source
- Origin: Shopify files exported to Google drive folder daily (~12:00am)
- Accessed locally via Google Drive desktop sync (Finder path), NOT the Drive API
    - Reason: the GD sync app already lands files onto disk; API would add OAuth/token complexity to re-solve a solved problem. API only justified if this ran off-laptop (other laptop/device).
- Folder layout: one subfolder per table, dimensional naming: 
    - Dim_Customers, Fact_Orders, Dim_Products, Dim_LineItems
- Filenames carry an ISO date prefix, e.g. `2026-05-29...._Orders.csv` 
    - Remember that each word is capitalized in filename, e.g. `_Orders.csv`, `_Customers.csv`, `_Line Items.csv`, `_Products.csv`
    - New dated file each day --> file overwrites previous day file; one file per folder
    - ISO date means alphabetical sort == chronological sort

## Intake Approach
- `latest_file(folder, suffix)` returns the newest CSV per folder via sorted(glob)[-1]
- `folders` dict: table nickname -> folder path
- `suffixes` dict: table nickname -> file ending (keys must match `folders` exactly)
- All tables loaded into a `tables` dict for reuse 
- TODO: once exploration ends, snapshot one day's files into data/raw/ and read from the frozen copy so analysis reproduces and doesn't drift with daily exports.

---
## Step 1 - Inventory & grain verification 
Method: a table is "one row per X" if its key column's nunique() == len().

### Initial grain check (keyed on `ID` for all four - this is accurate but with caveat - all tables PK is labeled `ID` but will need renaming and character stripping to get unique identifier to be used for indexing, joining and summarizing) - snapshot in time 6/7/2026

| table      | unique | rows  | verdict| 
|------------|--------|-------|----------------------------------------------------------------------------------------------------------|
| customers  | 10088  | 14938 | unique < rows -- duplicate customers potentially due to address changes, name misspelling, email changes | 
| orders     | 29883  | 66706 | unique < rows -- Is order table showing grain based on line items? One row per line item in order        | 
| products   | 1178   | 1178  | true grain, confirmed                                                                                    | 
| line items | 4813   | 4813  | true grain, confirmed                                                                                    | 

Unique count vs row count possibly due to duplicates, customer table address changes, and/or line item aggregation of orders table (e.g. one row per order per line item in order)

## Step 2 - Data Contracts: Grain, Keys, and Duplicate Rules

### Customers

| field | decision |
|-------|----------|
| Raw grain observed | Each row represents a customer export record; duplicate customer `ID`s appear in the raw data, possibly due to address/contact detail variations. |
| Clean grain target | One row per unique customer: new df = `customers_clean` |
| Primary key | `customer_id`, extracted from Shopify GID | 
| Duplicate handling rule | Keep one row per `customer_id`; choose the row with the latest reliable customer/update timestamp if available; otherwise document fallback rule. |
| Validation check | `customers_clean['customer_id'].nunique() == len(customers_clean)` |

### Orders

| field | decisions |
|-------|-----------|
| Raw grain observed | Each row appears to represent an order-line export record; the same Shopify order `ID` can appear across multiple rows when an order contains multiple line items. |
| Clean grain target | One row per unique order: new df = `orders_clean` | 
| Primary key | `order_id`, extracted from Shopify GID | 
| Duplicate handling rule | Treat repeated `order_id` rows as order-line expansion in the raw export; create an order-header table with one row per `order_id` using order-level fields only, and preserve product-level detail in the line-items table. |
| Validation check | `orders_clean['order_id'].nunique() == len(orders_clean)`  | 


### Products 

| field | decisions |
|-------|-----------|
| Raw grain observed | Each row appears to represent one unique product and may have multiple colors and/or sizes |
| Clean grain target | One row per unique product: new df = `products_clean` |
| Primary key | `product_id`, extracted from Shopify GID |
| Duplicate handling rule | In this table, duplicates would likely represent an error or product-line expansion in raw export. Check all fields for TRUE duplicates and remove. |
| Validation check | products_clean['product_id'].nunique() == len(products_clean)`|


### Line Items

| field | decisions |
|-------|-----------|
| Raw grain observed | Each row appears to represent one product variant per order number |
| Clean grain target | One row per unique line item |
| Primary key | `line_item_id`, extracted from Shopify GID |
| Duplicate handling rule | In this table, duplicates would likely represent an error. Check all fields for complete duplicates and remove |
| Validation check | line_items_clean['line_item_id'].nunique() == len(line_items_clean) |

## Variants
- Added at a later step while thinking about joins and relationships

| field | decisions |
|-------|-----------|
| Raw grain observed | 


## Relationships -- Describe the relationships between tables 

customers 1 --< orders 1 --< order line items >-- 1 variants >-- 1 products 

| table | primary/foreign keys | cardinality |
|-------|--------------|-------------|
| customers | customers.customer_id PK| customers 1 --< orders |
| orders | orders.order_id PK, customers.customer_id FK | orders 1 --< line_items |
| line items | line_items.line_item_id PK, line_items.order_id FK, line_items.product_id FK, line_items.variant_id FK | 
| products | product_id PK | products 1 --< variants |
| variant | variant.variant_id PK | variant.product_id FK | variants 1 --< line_items | 

## Open Questions / To Validate
- What are fact tables vs dimension tables in my analysis? 
- Orders columns containing product id and variant id have many null cells - based on what management has stated, this is due to a lack of data entry in early phases of business - Will need to determine how to handle


### Line Items
- What exactly does one line item represent in Shopify exports?
- Does each line item connect to exactly one `order_id`?
- Does each line item connect to exactly one `product_id`?
- Is `line_item_id` unique and stable enough to use as the primary key?
- Does the line-items table preserve the product-level detail removed from `orders_clean`?

### Products / Variants
- Does `product_id` represent the parent product, a product variant, or SKU-level item?
- Are variants stored in the products table, line-items table, or another export?
- Do size/color combinations need a separate `variants_clean` table?
- What column uniquely identifies a sellable item?

### Orders
- Which columns are truly order-level fields?
- Which columns are actually line-item/product-level fields inside the orders export?

### Customers
- Which timestamp should determine the latest customer record?
- Are duplicate customer rows caused by address changes, contact changes, or export structure?


## Data Modeling Decisions

## Data Dictionary


## Cross-table/join readiness (pending)
- Shopify stores all ID's in GID FORMAT: `gid://shopify/Customer/...` -> convert this to number only string -> extract unique ID using `customers['ID'].str.extract(r'Customer/(\d+)', expand=False).astype('object')`
    - Repeat for all tables (orders['ID'], customers['ID'], products['ID'], line items['ID'])
        - Verify df variable names match above
    - Convert ALL GID's in each table -> some tables have multiple GID's


## Column renaming deferred 
- Plan: rename raw `ID` columns to -> `order_id`, `customer_id`, `product_id`, `line_item_id` for readability & clarity
- DECISION: renaming happens AFTER key mapping
## Decisions still open/notes (carry forward)
- Consider changing s

---

## Current Cleaning Progress — 2026-07-11

### Customers clean table
- Selected customer-level attributes only and created `customers_clean` at one row per `customer_id`.
- Current result: N customers, 0 null `customer_id` values, and 0 duplicate `customer_id` values.
- The primary-key assertions pass, so the saved notebook currently supports `customer_id` as the clean customer key.

### Orders-to-customers relationship
- Tested non-null `orders_clean.customer_id` values against `customers_clean.customer_id`.
- Current result: N orders have a null `customer_id`, but 0 orders have an unmatched non-null `customer_id`.
- Interpretation: the relationship is optional for some orders, but all populated customer references are valid. Null customer IDs should remain null rather than being replaced with one artificial “unknown customer.”

### Geographic analysis decision
- Regional, state, and city sales should be attributed using the order's shipping geography, not a customer's saved address.
- Reason: a customer can save or change addresses, while shipping city/state describe where a specific order was sent.
- Planned flow: add shipping city and shipping state to the raw Orders export, confirm they load into `orders_work`, then retain them in `order_columns` so they flow into `orders_clean`.
- Use explicit names such as `shipping_city` and `shipping_state` so they remain distinct from future billing or customer-address fields.
- A separate customer-address table is deferred. It may still be useful later for customer-profile analysis, but it is not the primary source for sales geography.

### Immediate next checks
- Measure missing shipping city/state values without dropping the associated orders.
- Confirm shipping geography is stable within each repeated raw `order_id` before creating the one-row-per-order table.
- Keep geography at order grain; join orders to order lines when product-level regional sales are needed.
- After order geography is validated, continue clean-table construction for products and variants.


