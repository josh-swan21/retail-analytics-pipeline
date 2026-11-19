"""Cleaning logic extracted from notebooks/01_clean.ipynb; keep contracts in sync."""
import pandas as pd

def clean(tables):
    display = lambda *args, **kwargs: None
    # Notebook cell 3
    # Preserve untouched source tables. Cleaning will produce separate *_clean tables.
    customers_raw = tables["customers"].copy()
    orders_raw = tables["orders"].copy()
    products_raw = tables["products"].copy()
    inventory_raw = tables["inventory"].copy()
    variants_raw = tables["variants"].copy()

    # Notebook cell 4
    # Initial source verification; uniqueness alone does not establish semantic grain.
    raw_tables = {
        "customers_raw": (customers_raw, "ID"),
        "orders_raw": (orders_raw, "ID"),
        "products_raw": (products_raw, "ID"),
        "inventory_raw": (inventory_raw, "ID"),
        "variants_raw": (variants_raw, "ID")
    }
    
    for name, (df, candidate_key) in raw_tables.items():
        print(
            f"{name}: {len(df):,} rows; "
            f"{df[candidate_key].nunique(dropna=True):,} distinct non-null {candidate_key} values; "
            f"{df[candidate_key].isna().sum():,} nulls"
        )

    # Notebook cell 6
    # Normalize Shopify GIDs
    def extract_shopify_id(series, entity):
        return (
            series.astype("string")
            .str.extract(fr"^gid://shopify/{entity}/(\d+)$", expand=False)
        )

    # Notebook cell 7
    # Call extract_shopify_id on orders table
    orders_work = orders_raw.copy()
    
    orders_work["order_id"] = extract_shopify_id(orders_work["ID"], "Order")
    
    orders_work["customer_id"] = extract_shopify_id(orders_work["Customer: ID"], "Customer")
    
    orders_work["order_line_id"] = extract_shopify_id(orders_work["Line items: ID"], "LineItem")
    
    orders_work["product_id"] = extract_shopify_id(orders_work["Line items / Product: ID"], "Product")
    
    orders_work["variant_id"] = extract_shopify_id(orders_work["Line items / Variant: ID"], "ProductVariant")
    
    orders_work["fulfillment_id"] = extract_shopify_id(orders_work["Fulfillments: ID"], "Fulfillment")
    
    orders_work["shipping_line_id"] = extract_shopify_id(orders_work["Shipping lines: ID"], "ShippingLine")

    # Notebook cell 8
    # Call extract_shopify_id on customers table
    customers_work = customers_raw.copy()
    
    customers_work["customer_id"] = extract_shopify_id(customers_work["ID"], "Customer")

    # Notebook cell 9
    # Call extract_shopify_id on products table
    products_work = products_raw.copy()
    
    products_work["product_id"] = extract_shopify_id(products_work["ID"], "Product")

    # Notebook cell 10
    # Call extract_shopify_id on inventory table
    inventory_work = inventory_raw.copy()
    
    inventory_work["inventory_item_id"] = extract_shopify_id(inventory_work["ID"], "InventoryItem")
    
    inventory_work["variant_id"] = extract_shopify_id(inventory_work["Variant: ID"], "ProductVariant")
    
    inventory_work["inventory_level_id"] = inventory_work["Inventory levels: ID"].str.extract(r"gid://shopify/InventoryLevel/(\d+)\?", expand=False,).astype("string")
    
    inventory_work["location_id"] = extract_shopify_id(inventory_work["Inventory levels / Location: ID"], "Location")
    
    # One current inventory level is identified by its inventory item and level component.
    inventory_level_pk = ["inventory_item_id", "location_id"]

    # Notebook cell 11
    # Call extract_shopify_id on variants table
    variants_work = variants_raw.copy()
    
    variants_work["variant_id"] = extract_shopify_id(variants_work["ID"], "ProductVariant")
    
    variants_work["product_id"] = extract_shopify_id(variants_work["Product: ID"], "Product")
    
    variants_work["inventory_item_id"] = extract_shopify_id(variants_work["Inventory item: ID"], "InventoryItem")

    # Notebook cell 13
    # Validate ordinary Shopify GIDs and display all results before failing.
    id_checks = [
        ("orders", orders_work, "ID", "order_id"),
        ("orders", orders_work, "Customer: ID", "customer_id"),
        ("orders", orders_work, "Line items: ID", "order_line_id"),
        ("orders", orders_work, "Line items / Product: ID", "product_id"),
        ("orders", orders_work, "Line items / Variant: ID", "variant_id"),
        ("orders", orders_work, "Fulfillments: ID", "fulfillment_id"),
        ("orders", orders_work, "Shipping lines: ID", "shipping_line_id"),
    
        ("customers", customers_work, "ID", "customer_id"),
        ("products", products_work, "ID", "product_id"),
    
        ("variants", variants_work, "ID", "variant_id"),
        ("variants", variants_work, "Product: ID", "product_id"),
        ("variants", variants_work, "Inventory item: ID", "inventory_item_id"),
    
        ("inventory", inventory_work, "ID", "inventory_item_id"),
        ("inventory", inventory_work, "Variant: ID", "variant_id"),
        ("inventory", inventory_work, "Inventory levels / Location: ID", "location_id"),
        ("inventory", inventory_work, "Inventory levels: ID", "inventory_level_id")
    ]
    
    check_results = []
    
    for table_name, df, raw_column, normalized_column in id_checks:
        failed = df[raw_column].notna() & df[normalized_column].isna() # this identifies rows where Shopify provided a GID but normalization lost it
        failed_count = int(failed.sum())
    
        check_results.append({
            "table": table_name,
            "raw_column": raw_column,
            "normalized_column": normalized_column,
            "rows": len(df),
            "raw_non_null": int(df[raw_column].notna().sum()),
            "normalized_non_null": int(df[normalized_column].notna().sum()),
            "failed": failed_count,
            "status": "PASS" if failed_count == 0 else "FAIL",
        })
    
    # Dictionaries become a DataFrame, producing an auditable QA table
    check_results = pd.DataFrame(check_results)
    display(check_results)
    
    failed_checks = check_results.loc[check_results["failed"] > 0]
    
    assert failed_checks.empty, (
        "Some non-null Shopify GIDs failed normalization:\n"
        + failed_checks.to_string(index=False)
    )
    
    # Validate the composite primary key for the current Inventory Level snapshot.
    inventory_level_null_keys = int(
        inventory_work[inventory_level_pk].isna().any(axis=1).sum()
    )
    inventory_level_duplicate_keys = int(
        inventory_work.duplicated(inventory_level_pk, keep=False).sum()
    )
    
    inventory_level_pk_check = pd.DataFrame([{
        "table": "inventory_levels",
        "primary_key": " + ".join(inventory_level_pk),
        "rows": len(inventory_work),
        "null_key_rows": inventory_level_null_keys,
        "duplicate_key_rows": inventory_level_duplicate_keys,
        "status": (
            "PASS"
            if inventory_level_null_keys == 0 and inventory_level_duplicate_keys == 0
            else "FAIL"
        ),
    }])
    
    display(inventory_level_pk_check)
    
    assert inventory_level_null_keys == 0, "Inventory Level PK contains nulls"
    assert inventory_level_duplicate_keys == 0, "Inventory Level PK is not unique"

    # Notebook cell 15
    print("Rows:", len(orders_work))
    print("Orders:", orders_work["order_id"].nunique())
    print("Order lines:", orders_work["order_line_id"].nunique())
    print("Null line IDs:", orders_work["order_line_id"].isna().sum())
    print("Duplicate line IDs:", orders_work["order_line_id"].duplicated().sum())

    # Notebook cell 16
    duplicate_mask = orders_work.duplicated(
        "order_line_id",
        keep=False,
    )
    
    duplicate_order_lines = (
        orders_work[duplicate_mask]
        .sort_values(["order_line_id", "order_id"])
    )
    
    print(
        f"{len(duplicate_order_lines):,} rows across "
        f"{duplicate_order_lines['order_line_id'].nunique():,} "
        "duplicated order-line IDs"
    )
    
    display(duplicate_order_lines.head(50))

    # Notebook cell 17
    variation_by_line = (
        duplicate_order_lines
        .groupby("order_line_id")
        .nunique(dropna=False)
    )
    
    varying_columns = (
        variation_by_line.gt(1)
        .sum()
        .sort_values(ascending=False)
    )
    
    display(
        varying_columns[
            varying_columns > 0
        ].to_frame("duplicate_groups_with_variation")
    )

    # Notebook cell 19
    order_line_columns = [
        "order_line_id",
        "order_id",
        "product_id",
        "variant_id",
        "Line items: Quantity",
        "Line items: Unfulfilled quantity",
        "Line items: Fulfillable quantity",
        "Line items: Title",
        "Line items: Variant title",
        "Line items: Shop original unit price",
        "Line items: Shop original unit price currency",
        "Line items: Shop original total",
        "Line items: Shop original total currency",
        "Line items: Shop discounted total",
        "Line items: Shop discounted total currency",
        "Line items: Shop total discount",
        "Line items: Shop total discount currency",
        "Line items: Taxable",
        "Line items: Requires shipping",
    ]

    # Notebook cell 20
    # Remove identical rows and validate
    order_lines_clean = (
        orders_work[order_line_columns]
        .drop_duplicates()
        .copy()
    )
    
    assert order_lines_clean["order_line_id"].notna().all(), (
        "Order-line IDs contain nulls"
    )
    
    assert order_lines_clean["order_line_id"].is_unique, (
        "Some order lines have conflicting retained attributes"
    )

    # Notebook cell 22
    fulfillments_clean = (
        orders_work[
            ["fulfillment_id", "order_id"]
        ]
        .dropna(subset=["fulfillment_id"])
        .drop_duplicates()
        .copy()
    )

    # Notebook cell 23
    print("Rows:", len(fulfillments_clean))
    print("Null fulfillment IDs:", fulfillments_clean["fulfillment_id"].isna().sum())
    print("Duplicate fulfillment IDs:", fulfillments_clean["fulfillment_id"].duplicated().sum())
    print("Null order IDs:", fulfillments_clean["order_id"].isna().sum())
    
    assert fulfillments_clean["fulfillment_id"].notna().all()
    assert fulfillments_clean["fulfillment_id"].is_unique
    assert fulfillments_clean["order_id"].notna().all()

    # Notebook cell 25
    order_columns = [
        "order_id",
        "customer_id",
        "Name",
        "Created at",
        "Updated at",
        "Processed at",
        "Cancelled at",
        "Shipping address: City",
        "Shipping address: Province", 
        "Shipping address: Country",
        "Display financial status",
        "Display fulfillment status",
        "Payment gateways",
        "Currency code",
        "Presentment currency",
        "Shop subtotal price",
        "Shop subtotal price currency",
        "Shop total shipping price",
        "Shop total shipping price currency",
        "Shop original total duties",
        "Shop original total duties currency",
        "Shop total tax",
        "Shop total tax currency",
        "Shop total discounts",
        "Shop total discounts currency",
        "Shop total price",
        "Shop total price currency",
        "Test",
    ]

    # Notebook cell 26
    # Reduce repeated shipping-line records to one row per shipping line.
    shipping_line_columns = [
        "shipping_line_id",
        "order_id",
        "Shipping lines: Shop original price",
        "Shipping lines: Shop original price currency",
        "Shipping lines: Shop discounted price",
        "Shipping lines: Shop discounted price currency",
    ]
    
    shipping_lines_clean = (
        orders_work[shipping_line_columns]
        .dropna(subset=["shipping_line_id"])
        .drop_duplicates()
        .copy()
    )
    
    assert shipping_lines_clean["shipping_line_id"].is_unique
    assert shipping_lines_clean["order_id"].notna().all()
    assert shipping_lines_clean.iloc[:, 2:].notna().all().all()
    assert shipping_lines_clean.iloc[:, [3, 5]].eq("USD").all().all()
    
    # Calculate each shipping-line discount, then roll it up to one row per order.
    shipping_lines_clean["order_shipping_discount"] = (
        shipping_lines_clean["Shipping lines: Shop original price"]
        - shipping_lines_clean["Shipping lines: Shop discounted price"]
    )
    
    assert shipping_lines_clean["order_shipping_discount"].ge(0).all()
    
    shipping_by_order = (
        shipping_lines_clean
        .groupby("order_id", as_index=False)
        .agg(
            shipping_original_total=("Shipping lines: Shop original price", "sum"),
            order_shipping_discount=("order_shipping_discount", "sum"),
        )
    )
    
    # Create new orders table using order level fields from order_columns.
    orders_clean = (
        orders_work[order_columns]
        .drop_duplicates()
        .copy()
    )
    
    # Join shipping discounts to orders without changing the order grain.
    orders_clean = orders_clean.merge(
        shipping_by_order,
        on="order_id",
        how="left",
        validate="one_to_one",
    )
    
    orders_clean[["shipping_original_total", "order_shipping_discount"]] = (
        orders_clean[["shipping_original_total", "order_shipping_discount"]]
        .fillna(0.0)
    )
    orders_clean["order_shipping_discount_currency"] = "USD"
    orders_clean["Shop original total duties"] = (
        orders_clean["Shop original total duties"].fillna(0.0)
    )
    orders_clean["Shop original total duties currency"] = (
        orders_clean["Shop original total duties currency"].fillna("USD")
    )
    
    shipping_total_difference = (
        orders_clean["Shop total shipping price"]
        - orders_clean["shipping_original_total"]
    ).abs()
    
    assert shipping_total_difference.le(0.01).all()
    assert orders_clean["Shop original total duties"].ge(0).all()
    assert orders_clean["Shop original total duties currency"].eq("USD").all()
    
    orders_clean = orders_clean.drop(columns="shipping_original_total")
    
    # test row counts
    print("Orders:", len(orders_clean))
    print("Null order IDs:", orders_clean["order_id"].isna().sum())
    print("Duplicate order IDs:", orders_clean["order_id"].duplicated().sum())
    
    # lock in contract
    assert orders_clean["order_id"].notna().all()
    assert orders_clean["order_id"].is_unique

    # Notebook cell 28
    print(
        "Order-line orphan rows:",
        (~order_lines_clean["order_id"].isin(orders_clean["order_id"])).sum()
    )
    
    print(
        "Fulfillment orphan rows:",
        (~fulfillments_clean["order_id"].isin(orders_clean["order_id"])).sum()
    )
    
    assert order_lines_clean["order_id"].isin(
        orders_clean["order_id"]
    ).all()
    
    assert fulfillments_clean["order_id"].isin(
        orders_clean["order_id"]
    ).all()

    # Notebook cell 30
    for column in customers_work.columns:
        print(column)

    # Notebook cell 31
    customer_columns = [
        "customer_id", 
        "First name",
        "Last name", 
        "Lifetime duration", 
        "Email", 
        "Phone", 
        "Created at",
        "Number of orders",
        "Amount spent",
        "Amount spent currency", 
        "Updated at",
        "State", 
        "Tags"
    ]

    # Notebook cell 32
    # Create customers clean table using customer level columns from customers_work; customer_columns variable
    customers_clean = (
        customers_work[customer_columns]
        .drop_duplicates()
        .copy()
    )
    
    # Test customer row count; whether one customer_id gives one customer row
    print("Customers:", len(customers_clean))
    print("Null customer_id count:", customers_clean["customer_id"].isna().sum())
    print("Duplicate customer_id count:", customers_clean["customer_id"].duplicated().sum())
    
    assert customers_clean["customer_id"].notna().all()
    assert customers_clean["customer_id"].is_unique

    # Notebook cell 34
    # Validate relationship between orders_clean and customers_clean
    order_customer_ids = orders_clean["customer_id"]
    
    print("Orders with null customer_id:", orders_clean["customer_id"].isna().sum())
    print("Orders with unmatched customer_id:", (~order_customer_ids.dropna().isin(customers_clean["customer_id"])).sum())
    
    assert order_customer_ids.dropna().isin(customers_clean["customer_id"]).all()

    # Notebook cell 36
    for column in products_work.columns:
        print(column)

    # Notebook cell 37
    product_columns = [
        "product_id",
        "Title",
        "Vendor",
        "Product type",
        "Status",
        "Tags",
        "Created at",
        "Updated at",
        "Published at"    
    ]

    # Notebook cell 38
    products_clean = (
        products_work[product_columns]
        .drop_duplicates()
        .copy()
    )
    
    print("Product row count:", len(products_clean))
    print("Products with null product_id:", products_clean["product_id"].isna().sum())
    print("Duplicated product_id count:", products_clean["product_id"].duplicated().sum())
    
    assert products_clean["product_id"].notna().all()
    assert products_clean["product_id"].is_unique

    # Notebook cell 40
    order_line_product_ids = order_lines_clean["product_id"] # Which product, if any, each order line is connected to
    
    # Identify nulls -- then check if non-null product_id in order_lines_clean match products_clean product_id
    print("Null product_id in order_lines_clean count:", order_lines_clean["product_id"].isna().sum())
    print("Unmatched product_id count:", (~order_line_product_ids.dropna().isin(products_clean["product_id"])).sum()) 
    
    assert order_line_product_ids.dropna().isin(products_clean["product_id"]).all()

    # Notebook cell 42
    for column in variants_work.columns:
        print(column)

    # Notebook cell 43
    variant_columns = [
        "variant_id",
        "product_id",
        "inventory_item_id",
        "Title",
        "Created at",
        "Updated at",
        "SKU",
        "Price",
        "Inventory item: Unit cost",
        "Compare-at price",
        "Taxable",
        "Available for sale"
    ]

    # Notebook cell 44
    variants_clean = (
        variants_work[variant_columns]
        .drop_duplicates()
        .copy()
    )
    
    print("Variants count:", len(variants_clean))
    print("Null variant_id count:", variants_clean["variant_id"].isna().sum())
    print("Duplicated variant_id count:", variants_clean["variant_id"].duplicated().sum())
    
    assert variants_clean["variant_id"].notna().all()
    assert variants_clean["variant_id"].is_unique

    # Notebook cell 46
    variant_product_ids = variants_clean["product_id"]
    
    print("Null product_id in variants_clean count:", variants_clean["product_id"].isna().sum())
    print("Unmatched product_id count:", (~variant_product_ids.dropna().isin(products_clean["product_id"])).sum())
    
    assert variant_product_ids.dropna().isin(products_clean["product_id"]).all()

    # Notebook cell 48
    order_line_variant_ids = order_lines_clean["variant_id"]
    
    print("Null variant_id in order_line_clean count:", order_lines_clean["variant_id"].isna().sum())
    print("Unmatched variant_id count:", (~order_line_variant_ids.dropna().isin(variants_clean["variant_id"])).sum())
    
    assert order_line_variant_ids.dropna().isin(variants_clean["variant_id"]).all()

    # Notebook cell 50
    inventory_work.columns

    # Notebook cell 51
    inventory_level_columns = [
        "inventory_item_id",
        "inventory_level_id",
        "location_id",
        "Inventory levels / Location: Name",
        "Inventory levels / Quantities: Available quantity",
        "Inventory levels / Quantities: On hand quantity",
        "Inventory levels / Quantities: Committed quantity",
        "Inventory levels / Quantities: Incoming quantity",
        "Inventory levels / Quantities: Reserved quantity",
        "Inventory levels / Quantities: Safety stock quantity",
        "Inventory levels / Quantities: Available quantity updated at"
    ]

    # Notebook cell 53
    print("Rows:", len(inventory_work))
    
    print("Distinct inventory items:", inventory_work["inventory_item_id"].nunique())
    
    print("Distinct inventory levels:", inventory_work["inventory_level_id"].nunique())
    
    print("Distinct inventory locations:", inventory_work["location_id"].nunique())

    # Notebook cell 55
    level_location_match = (
        inventory_work["inventory_level_id"] 
        == inventory_work["location_id"]
    )
    
    print("Level ID always equals location ID:", level_location_match.all())

    # Notebook cell 56
    # Show the distinct technical level-to-location relationships.
    level_location_map = (
        inventory_work[
            [
                "inventory_level_id",
                "location_id",
                "Inventory levels / Location: Name",
            ]
        ]
        .drop_duplicates()
        .sort_values("inventory_level_id")
    )
    
    display(level_location_map)

    # Notebook cell 57
    # Confirm that each technical level maps to one location and vice versa.
    locations_per_level = (
        level_location_map
        .groupby("inventory_level_id")["location_id"]
        .nunique()
    )
    
    levels_per_location = (
        level_location_map
        .groupby("location_id")["inventory_level_id"]
        .nunique()
    )
    
    print("Levels mapped to multiple locations:", locations_per_level.gt(1).sum())
    print("Locations mapped to multiple levels:", levels_per_location.gt(1).sum())
    
    assert locations_per_level.eq(1).all()
    assert levels_per_location.eq(1).all()

    # Notebook cell 59
    locations_per_item = (
        inventory_work
        .groupby("inventory_item_id")["location_id"]
        .nunique()
    )
    
    print(
        "Inventory items at multiple locations:",
        locations_per_item.gt(1).sum()
    )
    
    display(
        locations_per_item
        .sort_values(ascending=False)
        .head(10)
    )

    # Notebook cell 60
    inventory_level_key = [
        "inventory_item_id",
        "location_id",
    ]
    
    print(
        "Rows with null key values:",
        inventory_work[inventory_level_key]
        .isna()
        .any(axis=1)
        .sum()
    )
    
    print(
        "Duplicate inventory-level keys:",
        inventory_work
        .duplicated(inventory_level_key)
        .sum()
    )
    
    assert inventory_work[inventory_level_key].notna().all().all()
    assert not inventory_work.duplicated(inventory_level_key).any()

    # Notebook cell 61
    duplicate_inventory_levels = (
        inventory_work[
            inventory_work.duplicated(
                inventory_level_key,
                keep=False,
            )
        ]
        .sort_values(inventory_level_key)
    )
    
    display(duplicate_inventory_levels.head(20))

    # Notebook cell 63
    inventory_item_columns = [
        "inventory_item_id",
        "variant_id",
        "Variant: SKU",
        "Tracked",
        "Unit cost",
        "Unit cost currency",
        "Requires shipping",
    ]

    # Notebook cell 64
    # Find inventory items whose retained attributes conflict across locations.
    inventory_item_attributes = [
        column
        for column in inventory_item_columns
        if column != "inventory_item_id"
    ]
    
    inventory_item_variation = (
        inventory_work
        .groupby("inventory_item_id")[inventory_item_attributes]
        .nunique(dropna=False)
    )
    
    conflicting_inventory_items = (
        inventory_item_variation.gt(1).any(axis=1)
    )
    
    print("Inventory items with conflicting attributes:", conflicting_inventory_items.sum())
    display(inventory_item_variation[conflicting_inventory_items].head(20))
    
    assert not conflicting_inventory_items.any()

    # Notebook cell 67
    inventory_items_clean = (
        inventory_work[inventory_item_columns]
        .drop_duplicates()
        .copy()
    )
    
    print("Inventory items:", len(inventory_items_clean))
    print("Null inventory_item_id count:", inventory_items_clean["inventory_item_id"].isna().sum())
    print("Duplicate inventory_item_id count:", inventory_items_clean["inventory_item_id"].duplicated().sum())
    
    assert inventory_items_clean["inventory_item_id"].notna().all()
    assert inventory_items_clean["inventory_item_id"].is_unique

    # Notebook cell 69
    inventory_variant_ids = inventory_items_clean["variant_id"]
    
    print("Inventory items with null variant_id:", inventory_variant_ids.isna().sum())
    print(
        "Inventory items with unmatched variant_id:",
        (~inventory_variant_ids.dropna().isin(variants_clean["variant_id"])).sum(),
    )
    print("Duplicate variant_id assignments:", inventory_variant_ids.dropna().duplicated().sum())
    
    assert inventory_variant_ids.dropna().isin(variants_clean["variant_id"]).all()
    assert inventory_variant_ids.dropna().is_unique

    # Notebook cell 70
    variant_inventory_item_ids = variants_clean["inventory_item_id"]
    
    print("Variants with null inventory_item_id:", variant_inventory_item_ids.isna().sum())
    print(
        "Variants with unmatched inventory_item_id:",
        (~variant_inventory_item_ids.dropna().isin(inventory_items_clean["inventory_item_id"])).sum(),
    )
    print("Duplicate inventory_item_id assignments:", variant_inventory_item_ids.dropna().duplicated().sum())
    
    assert variant_inventory_item_ids.dropna().isin(inventory_items_clean["inventory_item_id"]).all()
    assert variant_inventory_item_ids.dropna().is_unique

    # Notebook cell 72
    inventory_levels_clean = (
        inventory_work[inventory_level_columns]
        .copy()
    )
    
    print("Inventory levels:", len(inventory_levels_clean))
    print(
        "Rows with null inventory-level keys:",
        inventory_levels_clean[inventory_level_key].isna().any(axis=1).sum(),
    )
    print(
        "Duplicate inventory-level keys:",
        inventory_levels_clean.duplicated(inventory_level_key).sum(),
    )
    
    assert inventory_levels_clean[inventory_level_key].notna().all().all()
    assert not inventory_levels_clean.duplicated(inventory_level_key).any()

    # Notebook cell 74
    inventory_level_item_ids = inventory_levels_clean["inventory_item_id"]
    
    print(
        "Inventory-level orphan rows:",
        (~inventory_level_item_ids.isin(inventory_items_clean["inventory_item_id"])).sum(),
    )
    
    assert inventory_level_item_ids.isin(
        inventory_items_clean["inventory_item_id"]
    ).all()

    # Notebook cell 77
    orders_clean.dtypes

    # Notebook cell 79
    order_timestamp_columns = [
        "Created at", 
        "Updated at", 
        "Processed at", 
        "Cancelled at"
    ]
    
    for column in order_timestamp_columns:
        original = orders_clean[column].copy()
        converted = pd.to_datetime(original, errors="coerce", utc=True)
    
        failed = original.notna() & converted.isna()
        failed_count = int(failed.sum())
        print(column, "conversion failures", failed_count) # if all pass, this proves that every populated source timestamp parsed successfully
    
        assert failed_count == 0, f"{column} has {failed_count} conversion failures" 
    
        orders_clean[column] = converted

    # Notebook cell 80
    orders_clean[order_timestamp_columns].dtypes

    # Notebook cell 81
    # Validate date ranges are within expected ranges
    orders_clean[order_timestamp_columns].agg(["min","max"])

    # Notebook cell 82
    # Validate that updated at date does not come before created at date
    updated_before_created_count = (orders_clean["Updated at"] < orders_clean["Created at"]).sum()
    
    print("Orders updated before creation:", updated_before_created_count)
    
    assert updated_before_created_count == 0, f"There are {updated_before_created_count} rows updated before creation"

    # Notebook cell 83
    # Validate Cancelled at date does not come before Created at date
    cancelled_before_created_count = (orders_clean["Cancelled at"] < orders_clean["Created at"]).sum()
    
    print("Orders cancelled before creation:", cancelled_before_created_count)
    
    assert cancelled_before_created_count == 0, f"There are {cancelled_before_created_count} rows cancelled before creation"

    # Notebook cell 84
    order_lines_clean.dtypes

    # Notebook cell 85
    quantity_check_columns = [
        "Line items: Quantity", 
        "Line items: Unfulfilled quantity", 
        "Line items: Fulfillable quantity"
    ]
    
    order_lines_clean[quantity_check_columns].agg(["min", "max"])

    # Notebook cell 86
    zero_or_less_quantity_count = (order_lines_clean["Line items: Quantity"] <= 0).sum()
    
    print("Order lines with zero or less quantity:", zero_or_less_quantity_count)
    
    assert zero_or_less_quantity_count == 0, f"There are {zero_or_less_quantity_count} order lines less than, or equal to, 0"

    # Notebook cell 87
    remaining_quantity_columns = [
        "Line items: Unfulfilled quantity",
        "Line items: Fulfillable quantity"
    ]
    
    for column in remaining_quantity_columns:
        less_than_zero = (order_lines_clean[column] < 0).sum()
    
        print(f"{column} column has", less_than_zero, "rows with count less than zero")
    
        assert less_than_zero == 0, f"There are {less_than_zero} order lines less than zero"

    # Notebook cell 88
    # Unfulfilled order line quantity cannot be greater than quantity originally ordered
    
    unfulfilled_exceeds_quantity_count = (order_lines_clean["Line items: Unfulfilled quantity"] > order_lines_clean["Line items: Quantity"]).sum()
    
    print("The number of order lines where unfulfilled quantity is greater than quantity is", unfulfilled_exceeds_quantity_count)
    
    assert unfulfilled_exceeds_quantity_count == 0, f"There are {unfulfilled_exceeds_quantity_count} order lines where unfulfilled quantity exceeds ordered quantity"

    # Notebook cell 89
    # Fulfillable quantity cannot exceed the unfulfilled quantity on an order line.
    fulfillable_exceeds_unfulfilled_count = (
        order_lines_clean["Line items: Fulfillable quantity"]
        > order_lines_clean["Line items: Unfulfilled quantity"]
    ).sum()
    
    print(
        "Order lines where fulfillable quantity exceeds unfulfilled quantity:",
        fulfillable_exceeds_unfulfilled_count,
    )
    
    assert fulfillable_exceeds_unfulfilled_count == 0, (
        f"There are {fulfillable_exceeds_unfulfilled_count} order lines where "
        "fulfillable quantity exceeds unfulfilled quantity"
    )

    # Notebook cell 90
    order_line_monetary_columns = [
        "Line items: Shop original unit price",
        "Line items: Shop original total",
        "Line items: Shop discounted total", 
        "Line items: Shop total discount"
    ]
    
    order_lines_clean[order_line_monetary_columns].agg(["min", "max"])

    # Notebook cell 91
    for column in order_line_monetary_columns:
        less_than_zero = (order_lines_clean[column] < 0).sum()
    
        print(f"{column} column has", less_than_zero, "rows with count less than zero")
    
        assert less_than_zero == 0, f"{column} contains {less_than_zero} negative values"

    # Notebook cell 92
    discounted_total_exceeds_original_count = (order_lines_clean["Line items: Shop discounted total"] > order_lines_clean["Line items: Shop original total"]).sum()
    
    print(discounted_total_exceeds_original_count)
    
    assert discounted_total_exceeds_original_count == 0, f"There are {discounted_total_exceeds_original_count} order line items that have a discounted total that exceeds the original price"

    # Notebook cell 93
    calculated_original_total = order_lines_clean["Line items: Shop discounted total"] + order_lines_clean["Line items: Shop total discount"]
    
    original_total_difference = (
        order_lines_clean["Line items: Shop original total"] - calculated_original_total
    ).abs()

    # Notebook cell 94
    original_total_difference.agg(["min", "max"])

    # Notebook cell 95
    monetary_tolerance = 0.01
    
    original_total_difference_greater_than_tolerance = original_total_difference > monetary_tolerance
    
    original_total_mismatch_count = original_total_difference_greater_than_tolerance.sum()
    
    print(
        "Order lines where monetary totals exceed the reconciliation tolerance:",
        original_total_mismatch_count,
    )
    
    assert original_total_mismatch_count == 0, (
        f"There are {original_total_mismatch_count} order lines whose original total "
        f"does not reconcile within the {monetary_tolerance:.2f} tolerance"
    )

    # Notebook cell 96
    calculated_unit_price_quantity_total = order_lines_clean["Line items: Shop original unit price"] * order_lines_clean["Line items: Quantity"]
    
    unit_price_quantity_total_difference = (
        order_lines_clean["Line items: Shop original total"] - calculated_unit_price_quantity_total
    ).abs()

    # Notebook cell 97
    unit_price_quantity_total_difference.agg(["min", "max"])

    # Notebook cell 98
    unit_price_quantity_mismatch = (
        unit_price_quantity_total_difference > monetary_tolerance
    )
    
    unit_price_quantity_mismatch_count = unit_price_quantity_mismatch.sum()
    
    print(
        "Order lines where unit price times quantity does not reconcile with original total:",
        unit_price_quantity_mismatch_count,
    )
    
    assert unit_price_quantity_mismatch_count == 0, (
        f"There are {unit_price_quantity_mismatch_count} order lines where unit price "
        f"times quantity does not reconcile within the {monetary_tolerance:.2f} tolerance"
    )

    # Notebook cell 99
    order_line_currency_columns = [
        "Line items: Shop original unit price currency",
        "Line items: Shop original total currency",
        "Line items: Shop discounted total currency",
        "Line items: Shop total discount currency",
    ]

    # Notebook cell 100
    order_lines_clean[order_line_currency_columns].isna().sum()

    # Notebook cell 101
    for column in order_line_currency_columns:
        print(column)
        print(order_lines_clean[column].unique())

    # Notebook cell 102
    currency_values_per_order_line = (
        order_lines_clean[order_line_currency_columns]
        .nunique(axis=1, dropna=False)
    )
    
    currency_mismatch_count = currency_values_per_order_line.ne(1).sum()
    
    print(
        "Order lines with missing or inconsistent currency values:",
        currency_mismatch_count,
    )
    
    assert currency_mismatch_count == 0, (
        f"There are {currency_mismatch_count} order lines with missing or "
        "inconsistent currency values"
    )

    # Notebook cell 103
    customers_clean.dtypes

    # Notebook cell 104
    customer_timestamp_columns = [
        "Created at", 
        "Updated at"
    ]
    
    for column in customer_timestamp_columns:
        original = customers_clean[column].copy()
        converted = pd.to_datetime(original, errors="coerce", utc=True)
    
        failed = original.notna() & converted.isna()
        failed_count = int(failed.sum())
        print(column, "conversion failures", failed_count) # if all pass, this proves that every populated source timestamp parsed successfully
    
        assert failed_count == 0, f"{column} has {failed_count} conversion failures" 
    
        customers_clean[column] = converted

    # Notebook cell 105
    customers_clean[customer_timestamp_columns].dtypes

    # Notebook cell 106
    # Validate date ranges are within expected ranges
    customers_clean[customer_timestamp_columns].agg(["min","max"])

    # Notebook cell 107
    customers_clean.dtypes

    # Notebook cell 108
    customers_clean["Phone"] = (
        customers_clean["Phone"]
        .astype("Int64")
        .astype("str")
    )

    # Notebook cell 109
    customers_clean.dtypes

    # Notebook cell 110
    phone_null_count = customers_clean["Phone"].isna().sum() # check for any null values
    
    print("Customers with missing phone:", phone_null_count)
    
    # check for count of missing values with literal "nan" "<NA>" after conversion 
    literal_missing_count = (
        customers_clean["Phone"]
        .isin(["nan", "<NA>"])
        .sum()
    )
    
    print("Literal missing-value strings:", literal_missing_count)
    
    assert literal_missing_count == 0

    # Notebook cell 111
    # Check that no strings end with .0 in converted phone column
    trailing_decimal_count = (
        customers_clean["Phone"]
        .str.endswith(".0", na=False)
        .sum()
    )
    
    print("Phone values ending in .0:", trailing_decimal_count)
    
    assert trailing_decimal_count == 0

    # Notebook cell 112
    customers_work["Amount spent currency"].value_counts(dropna=False)

    # Notebook cell 114
    products_clean.dtypes

    # Notebook cell 115
    product_timestamp_columns = [
        "Created at", 
        "Updated at", 
        "Published at"
    ]
    
    for column in product_timestamp_columns:
        original = products_clean[column].copy()
        converted = pd.to_datetime(original, errors="coerce", utc=True)
    
        failed = original.notna() & converted.isna()
        failed_count = int(failed.sum())
        print(column, "conversion failures", failed_count) # if all pass, this proves that every populated source timestamp parsed successfully
    
        assert failed_count == 0, f"{column} has {failed_count} conversion failures" 
    
        products_clean[column] = converted

    # Notebook cell 116
    products_clean.dtypes

    # Notebook cell 117
    products_clean["Tags"].notna().sum()

    # Notebook cell 118
    products_clean["Tags"] = (
        products_clean["Tags"]
        .astype("str")
    )

    # Notebook cell 119
    products_clean.dtypes

    # Notebook cell 120
    variants_clean.dtypes

    # Notebook cell 121
    variant_timestamp_columns = [
        "Created at", 
        "Updated at", 
    ]
    
    for column in variant_timestamp_columns:
        original = variants_clean[column].copy()
        converted = pd.to_datetime(original, errors="coerce", utc=True)
    
        failed = original.notna() & converted.isna()
        failed_count = int(failed.sum())
        print(column, "conversion failures", failed_count) # if all pass, this proves that every populated source timestamp parsed successfully
    
        assert failed_count == 0, f"{column} has {failed_count} conversion failures" 
    
        variants_clean[column] = converted

    # Notebook cell 122
    variants_clean["SKU"] = (
        variants_clean["SKU"]
        .astype("str")
    )

    # Notebook cell 123
    variants_clean["SKU"].notna().sum()

    # Notebook cell 124
    variants_clean.dtypes

    # Notebook cell 125
    inventory_items_clean.dtypes

    # Notebook cell 126
    inventory_items_clean["Variant: SKU"] = (
        inventory_items_clean["Variant: SKU"]
        .astype("str")
    )

    # Notebook cell 127
    inventory_items_clean["Variant: SKU"].notna().sum()

    # Notebook cell 128
    inventory_items_clean.dtypes

    # Notebook cell 129
    inventory_levels_clean.dtypes

    # Notebook cell 130
    inventory_levels_timestamp_columns = [
    "Inventory levels / Quantities: Available quantity updated at"
    ]
    
    for column in inventory_levels_timestamp_columns:
        original = inventory_levels_clean[column].copy()
        converted = pd.to_datetime(original, errors="coerce", utc=True)
    
        failed = original.notna() & converted.isna()
        failed_count = int(failed.sum())
        print(column, "conversion failures", failed_count) # if all pass, this proves that every populated source timestamp parsed successfully
    
        assert failed_count == 0, f"{column} has {failed_count} conversion failures" 
    
        inventory_levels_clean[column] = converted

    # Notebook cell 131
    inventory_levels_clean.dtypes

    # Notebook cell 132
    orders_clean.dtypes

    # Notebook cell 133
    # Order columns dictionary
    
    order_column_names = {
        "Name": "order_number", 
        "Created at": "created_at", 
        "Updated at": "updated_at", 
        "Processed at": "processed_at", 
        "Cancelled at": "cancelled_at", 
        "Shipping address: City": "shipping_city", 
        "Shipping address: Province": "shipping_state_province",
        "Shipping address: Country": "shipping_country",
        "Display financial status": "financial_status",
        "Display fulfillment status": "fulfillment_status",
        "Payment gateways": "payment_gateways",
        "Currency code": "currency_code", 
        "Presentment currency": "presentment_currency", 
        "Shop subtotal price": "order_subtotal",
        "Shop subtotal price currency": "order_subtotal_currency",
        "Shop total shipping price": "order_shipping_total",
        "Shop total shipping price currency": "order_shipping_total_currency",
        "Shop original total duties": "order_total_duties",
        "Shop original total duties currency": "order_total_duties_currency",
        "Shop total tax": "order_total_tax", 
        "Shop total tax currency": "order_total_tax_currency",
        "Shop total discounts": "order_discounts_total", 
        "Shop total discounts currency": "order_discounts_total_currency", 
        "Shop total price": "order_total", 
        "Shop total price currency": "order_total_currency", 
        "Test": "is_test"
    }
    
    orders_clean = orders_clean.rename(columns=order_column_names)

    # Notebook cell 134
    orders_clean.dtypes

    # Notebook cell 135
    order_lines_clean.dtypes

    # Notebook cell 136
    order_line_column_names = {
        "Line items: Quantity": "quantity",
        "Line items: Unfulfilled quantity": "unfulfilled_quantity",
        "Line items: Fulfillable quantity": "fulfillable_quantity", 
        "Line items: Title": "title", 
        "Line items: Variant title": "variant_title", 
        "Line items: Shop original unit price": "unit_price",
        "Line items: Shop original unit price currency": "unit_price_currency", 
        "Line items: Shop original total": "original_total", 
        "Line items: Shop original total currency": "original_total_currency", 
        "Line items: Shop discounted total": "discounted_total",
        "Line items: Shop discounted total currency": "discounted_total_currency", 
        "Line items: Shop total discount": "total_discount",
        "Line items: Shop total discount currency": "total_discount_currency",
        "Line items: Taxable": "is_taxable", 
        "Line items: Requires shipping": "requires_shipping"
    }
    
    order_lines_clean = order_lines_clean.rename(columns=order_line_column_names)

    # Notebook cell 137
    order_lines_clean.dtypes

    # Notebook cell 138
    fulfillments_clean.dtypes

    # Notebook cell 139
    customers_clean.dtypes

    # Notebook cell 140
    customer_column_names = {
        "First name": "first_name",
        "Last name": "last_name",
        "Lifetime duration": "lifetime_duration",
        "Email": "email",
        "Phone": "phone", 
        "Created at": "created_at", 
        "Number of orders": "order_count",
        "Amount spent": "total_amount_spent",
        "Amount spent currency": "total_amount_spent_currency",
        "Updated at": "updated_at", 
        "State": "state", 
        "Tags": "tags"
    }
    
    customers_clean = customers_clean.rename(columns=customer_column_names)

    # Notebook cell 141
    customers_clean.dtypes

    # Notebook cell 142
    products_clean.dtypes

    # Notebook cell 143
    product_column_names = {
        "Title": "title",
        "Vendor": "vendor", 
        "Product type": "product_type", 
        "Status": "status",
        "Tags": "tags",
        "Created at": "created_at", 
        "Updated at": "updated_at", 
        "Published at": "published_at"
    }
    
    products_clean = products_clean.rename(columns=product_column_names)

    # Notebook cell 144
    products_clean.dtypes

    # Notebook cell 145
    variants_clean.dtypes

    # Notebook cell 146
    variants_column_names = {
        "Title": "title", 
        "Created at": "created_at",
        "Updated at": "updated_at",
        "SKU": "sku",
        "Price": "price",
        "Inventory item: Unit cost": "unit_cost", 
        "Compare-at price": "compare_at_price", 
        "Taxable": "is_taxable", 
        "Available for sale": "is_available_for_sale"
    }
    
    variants_clean = variants_clean.rename(columns=variants_column_names)

    # Notebook cell 147
    variants_clean.dtypes

    # Notebook cell 148
    inventory_items_clean.dtypes

    # Notebook cell 149
    inventory_items_column_names = {
        "Variant: SKU": "sku",
        "Tracked": "is_tracked",
        "Unit cost": "unit_cost", 
        "Unit cost currency": "unit_cost_currency", 
        "Requires shipping": "requires_shipping"
    }
    
    inventory_items_clean = inventory_items_clean.rename(columns=inventory_items_column_names)

    # Notebook cell 150
    inventory_items_clean.dtypes

    # Notebook cell 151
    inventory_levels_clean.dtypes

    # Notebook cell 152
    inventory_levels_column_names = {
        "Inventory levels / Location: Name": "location_name",
        "Inventory levels / Quantities: Available quantity": "quantity_available", 
        "Inventory levels / Quantities: On hand quantity": "quantity_on_hand",
        "Inventory levels / Quantities: Committed quantity": "quantity_committed",
        "Inventory levels / Quantities: Incoming quantity": "quantity_incoming",
        "Inventory levels / Quantities: Reserved quantity": "quantity_reserved",
        "Inventory levels / Quantities: Safety stock quantity": "safety_stock_quantity",
        "Inventory levels / Quantities: Available quantity updated at": "quantity_available_updated_at" 
    }
    
    inventory_levels_clean = inventory_levels_clean.rename(columns=inventory_levels_column_names)

    # Notebook cell 153
    inventory_levels_clean.dtypes

    return {name: locals_table for name, locals_table in [
        ("customers", customers_clean),
        ("products", products_clean),
        ("orders", orders_clean),
        ("variants", variants_clean),
        ("inventory_items", inventory_items_clean),
        ("inventory_levels", inventory_levels_clean),
        ("order_lines", order_lines_clean),
        ("fulfillments", fulfillments_clean),
    ]}
