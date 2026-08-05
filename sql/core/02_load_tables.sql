USE ROLE SYSADMIN;
USE WAREHOUSE COMPUTE_WH;
USE DATABASE RETAIL_DB;

USE SCHEMA CORE;


-- ============================================================
-- MANUAL PRE-UPLOAD STEP
--
-- Before running this file:
-- 1. Run 01_clean.ipynb and export the updated CSVs.
-- 2. Run the REMOVE command separately.
-- 3. Upload all eight updated CSVs.
--
-- Do not uncomment this command inside the loading script:
--
-- REMOVE @RETAIL_DB.CORE.CLEAN_CSV_STAGE
-- PATTERN = '.*[.]csv';
-- ============================================================

CREATE OR REPLACE FILE FORMAT CLEAN_CSV_FORMAT
    TYPE = CSV
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    EMPTY_FIELD_AS_NULL = TRUE
    NULL_IF = ('', 'NULL');

CREATE STAGE IF NOT EXISTS RETAIL_DB.CORE.CLEAN_CSV_STAGE
    FILE_FORMAT = (
        FORMAT_NAME = RETAIL_DB.CORE.CLEAN_CSV_FORMAT
    );

SHOW FILE FORMATS IN SCHEMA RETAIL_DB.CORE;
SHOW STAGES IN SCHEMA RETAIL_DB.CORE;


ALTER STAGE RETAIL_DB.CORE.CLEAN_CSV_STAGE
    SET FILE_FORMAT = (
        FORMAT_NAME = RETAIL_DB.CORE.CLEAN_CSV_FORMAT
    );

LIST @RETAIL_DB.CORE.CLEAN_CSV_STAGE;

-- Clear the existing snapshot only after confirming
-- that all updated source files are staged.

TRUNCATE TABLE ORDER_LINES;
TRUNCATE TABLE FULFILLMENTS;
TRUNCATE TABLE INVENTORY_LEVELS;
TRUNCATE TABLE INVENTORY_ITEMS;
TRUNCATE TABLE VARIANTS;
TRUNCATE TABLE ORDERS;
TRUNCATE TABLE PRODUCTS;
TRUNCATE TABLE CUSTOMERS;


-- CUSTOMERS: Confirm destination is empty after truncation
SELECT COUNT(*)
FROM RETAIL_DB.CORE.CUSTOMERS;

-- CUSTOMERS: Validate the CSV against the table without inserting rows
COPY INTO RETAIL_DB.CORE.CUSTOMERS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('customers.csv')
VALIDATION_MODE = 'RETURN_ALL_ERRORS';

-- CUSTOMERS: Load staged file
COPY INTO RETAIL_DB.CORE.CUSTOMERS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('customers.csv')
ON_ERROR = 'ABORT_STATEMENT';

-- CUSTOMERS: Validate row count post-load 
SELECT COUNT(*)
FROM RETAIL_DB.CORE.CUSTOMERS;

-- PRODUCTS: Confirm destination is empty after truncation
SELECT COUNT(*)
FROM retail_db.core.products;

-- Validate the CSV against the table without inserting rows
COPY INTO RETAIL_DB.CORE.PRODUCTS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('products.csv')
VALIDATION_MODE = 'RETURN_ALL_ERRORS';

-- PRODUCTS: Load staged file
COPY INTO RETAIL_DB.CORE.PRODUCTS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('products.csv')
ON_ERROR = 'ABORT_STATEMENT';

-- Validate row count post-load
SELECT COUNT(*)
FROM RETAIL_DB.CORE.PRODUCTS;

-- ========== ORDERS ==========
-- Confirm destination is empty after truncation
SELECT COUNT(*)
FROM retail_db.core.orders;

-- Validate the CSV against the table without inserting rows
COPY INTO RETAIL_DB.CORE.ORDERS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('orders.csv')
VALIDATION_MODE = 'RETURN_ALL_ERRORS';

-- Load staged file
COPY INTO RETAIL_DB.CORE.ORDERS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('orders.csv')
ON_ERROR = 'ABORT_STATEMENT';

-- Validate row count post-load
SELECT COUNT(*)
FROM RETAIL_DB.CORE.ORDERS;

-- ========== VARIANTS ==========
-- Confirm destination is empty after truncation
SELECT COUNT(*)
FROM retail_db.core.variants;

-- Validate the CSV against the table without inserting rows
COPY INTO RETAIL_DB.CORE.VARIANTS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('variants.csv')
VALIDATION_MODE = 'RETURN_ALL_ERRORS';

-- Load staged file
COPY INTO RETAIL_DB.CORE.VARIANTS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('variants.csv')
ON_ERROR = 'ABORT_STATEMENT';

-- Validate row count post-load
SELECT COUNT(*)
FROM RETAIL_DB.CORE.VARIANTS;

-- ========== INVENTORY ITEMS ==========
-- Confirm destination is empty after truncation
SELECT COUNT(*)
FROM retail_db.core.inventory_items;

-- Validate the CSV against the table without inserting rows
COPY INTO RETAIL_DB.CORE.INVENTORY_ITEMS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('inventory_items.csv')
VALIDATION_MODE = 'RETURN_ALL_ERRORS';

-- Load staged file
COPY INTO RETAIL_DB.CORE.INVENTORY_ITEMS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('inventory_items.csv')
ON_ERROR = 'ABORT_STATEMENT';

-- Validate row count post-load
SELECT COUNT(*)
FROM RETAIL_DB.CORE.INVENTORY_ITEMS;

-- ========== INVENTORY LEVELS ==========
-- Confirm destination is empty after truncation
SELECT COUNT(*)
FROM retail_db.core.inventory_levels;

-- Validate the CSV against the table without inserting rows
COPY INTO RETAIL_DB.CORE.INVENTORY_LEVELS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('inventory_levels.csv')
VALIDATION_MODE = 'RETURN_ALL_ERRORS';

-- Load staged file
COPY INTO RETAIL_DB.CORE.INVENTORY_LEVELS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('inventory_levels.csv')
ON_ERROR = 'ABORT_STATEMENT';

-- Validate row count post-load
SELECT COUNT(*)
FROM RETAIL_DB.CORE.INVENTORY_LEVELS;

-- ========== ORDER LINES ==========
-- Confirm destination is empty after truncation
SELECT COUNT(*)
FROM retail_db.core.order_lines;

-- Validate the CSV against the table without inserting rows
COPY INTO RETAIL_DB.CORE.ORDER_LINES
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('order_lines.csv')
VALIDATION_MODE = 'RETURN_ALL_ERRORS';

-- Load staged file
COPY INTO RETAIL_DB.CORE.ORDER_LINES
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('order_lines.csv')
ON_ERROR = 'ABORT_STATEMENT';

-- Validate row count post-load
SELECT COUNT(*)
FROM RETAIL_DB.CORE.ORDER_LINES;

-- ========== FULFILLMENTS ==========
-- Confirm destination is empty after truncation
SELECT COUNT(*)
FROM retail_db.core.fulfillments;

-- Validate the CSV against the table without inserting rows
COPY INTO RETAIL_DB.CORE.FULFILLMENTS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('fulfillments.csv')
VALIDATION_MODE = 'RETURN_ALL_ERRORS';

-- Load staged file
COPY INTO RETAIL_DB.CORE.FULFILLMENTS
FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE
FILES = ('fulfillments.csv')
ON_ERROR = 'ABORT_STATEMENT';

-- Validate row count post-load
SELECT COUNT(*)
FROM RETAIL_DB.CORE.FULFILLMENTS;
