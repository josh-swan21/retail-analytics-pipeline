import unittest
from unittest.mock import patch
from retail_batch.__main__ import statements, validate, live, TABLES
from pathlib import Path


class Cursor:
    description = None

    def __init__(self, columns=(), rows=()):
        self.columns, self.rows = columns, rows
        self.commands = []

    def execute(self, sql):
        self.commands.append(sql)
        self.description = [(x,) for x in self.columns]

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class Tests(unittest.TestCase):
    def test_all_eight_copy_statements_detected(self):
        sql = statements('sql/core/02_load_tables.sql')
        self.assertEqual(sum(s.startswith('COPY INTO') for s in sql), 8)
        self.assertTrue(all(not s.startswith('--') for s in sql))

    def test_validation_blocks_orphans(self):
        c = Cursor(['unmatched_customer_ids'], [(1,)])
        results = []
        with patch('retail_batch.__main__.statements', return_value=['SELECT 1']):
            with self.assertRaises(ValueError):
                validate(c, {}, results)
        self.assertEqual(results[0]['rows'], [(1,)])

    def test_optional_null_catalog_refs(self):
        c = Cursor(['null_product_ids', 'unmatched_product_ids'], [(42, 0)])
        with patch('retail_batch.__main__.statements', return_value=['SELECT 1 FROM order_lines']):
            validate(c, {})

    def test_required_variant_ref(self):
        c = Cursor(['null_product_ids'], [(1,)])
        with patch('retail_batch.__main__.statements', return_value=['SELECT 1 FROM variants']):
            with self.assertRaises(ValueError):
                validate(c, {})

    def test_counts_must_match(self):
        c = Cursor(['table_name', 'actual_rows'], [('ORDERS', 3)])
        with patch('retail_batch.__main__.statements', return_value=['SELECT 1']):
            with self.assertRaises(ValueError):
                validate(c, {'orders': 4})

    def test_reconciliation_rows_block(self):
        c = Cursor(['unexplained_difference'], [(0.02,)])
        with patch('retail_batch.__main__.statements', return_value=['WITH x AS (SELECT 1) SELECT * FROM x']):
            with self.assertRaises(ValueError):
                validate(c, {})

    def test_publish_failure_rolls_back(self):
        class LoadCursor(Cursor):
            def execute(self, sql):
                super().execute(sql)
                if sql == 'INSERT FAIL':
                    raise RuntimeError('simulated publish failure')
            def fetchall(self):
                if self.commands[-1].startswith('PUT'):
                    return [('a', 'a', 1, 1, 'NONE', 'NONE', 'UPLOADED')]
                return []
        class Connection:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def cursor(self): return c
        c = LoadCursor()
        def script(filename):
            return ['BEGIN TRANSACTION', 'INSERT FAIL', 'COMMIT'] if '04_' in filename else []
        with patch('snowflake.connector.connect', return_value=Connection()), patch('retail_batch.__main__.connection_settings', return_value={}), patch('retail_batch.__main__.statements', side_effect=script), patch('retail_batch.__main__.validate', return_value=[]):
            with self.assertRaises(RuntimeError):
                live(Path('/tmp'), {'run_id': 'test', 'counts': {}})
        self.assertEqual(c.commands[-1], 'ROLLBACK')
        self.assertNotIn('COMMIT', c.commands)
        uploads = [sql for sql in c.commands if sql.startswith('PUT')]
        self.assertEqual(len(uploads), 8)
        self.assertTrue(all('@RETAIL_DB.CORE.CLEAN_CSV_STAGE/test/ ' in sql
                            for sql in uploads))

    def test_preflight_errors_saved_and_block_load(self):
        class ErrorCursor(Cursor):
            sfqid = 'test-query'
            def execute(self, sql):
                super().execute(sql)
                self.description = [('ERROR',)]
            def fetchall(self):
                if self.commands[-1].startswith('PUT'):
                    return [('a', 'a', 1, 1, 'NONE', 'NONE', 'UPLOADED')]
                return [('file not found',)]
        class Connection:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def cursor(self): return c
        c = ErrorCursor()
        report = {'run_id': 'test', 'counts': {}}
        copy = "COPY INTO RETAIL_DB.INCOMING.CUSTOMERS FROM @RETAIL_DB.CORE.CLEAN_CSV_STAGE FILES=('customers.csv') ON_ERROR = 'ABORT_STATEMENT'"
        with patch('snowflake.connector.connect', return_value=Connection()), patch('retail_batch.__main__.connection_settings', return_value={}), patch('retail_batch.__main__.statements', return_value=[copy]):
            with self.assertRaisesRegex(ValueError, 'file not found'):
                live(Path('/tmp'), report)
        self.assertEqual(report['copy_preflight'][0]['query_id'], 'test-query')
        copies = [s for s in c.commands if s.startswith('COPY')]
        self.assertEqual(len(copies), 1)
        self.assertIn('/test/ FILES=', copies[0])
        self.assertIn('VALIDATION_MODE', copies[0])


if __name__ == '__main__':
    unittest.main()
