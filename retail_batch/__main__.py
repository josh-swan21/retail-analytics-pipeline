"""Explicit, fail-closed snapshot batch runner. No network unless --live is supplied."""
import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import uuid

import pandas as pd
from dotenv import load_dotenv

from .clean import clean

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'customers': ('Dim_Customers', '_Customers.csv'),
    'orders': ('Fact_Orders', '_Orders.csv'),
    'products': ('Dim_Products', '_Products.csv'),
    'variants': ('Dim_Variants', '_Variants.csv'),
    'inventory': ('Dim_Inventory', '_Inventory_Items.csv'),
}
TABLES = ('customers', 'products', 'orders', 'variants', 'inventory_items',
          'inventory_levels', 'order_lines', 'fulfillments')
# These are observations, not failures: guest orders, deleted catalog references,
# and negative sellable/on-hand stock are explicitly allowed by the source model.
OBSERVATIONS = {'null_customer_ids', 'negative_on_hand_rows', 'negative_available_rows'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def statements(filename):
    from snowflake.connector.util_text import split_statements
    text = re.sub(r"(?m)^\s*--[^\n]*", "", (ROOT / filename).read_text())
    return [s.strip() for s, _ in split_statements(io.StringIO(text)) if s.strip()]


def validate(cursor, expected, results=None):
    if results is None:
        results = []
    for sql in statements('sql/core/03_validate_tables.sql'):
        if sql.startswith(('USE ROLE', 'USE WAREHOUSE')):
            continue
        cursor.execute(sql)
        if not sql.lstrip().upper().startswith(('SELECT', 'WITH', '--')):
            continue
        if cursor.description is None:
            continue
        columns = [d[0].lower() for d in cursor.description]
        rows = cursor.fetchall()
        results.append({'columns': columns, 'rows': rows})
        if 'actual_rows' in columns:
            actual = {str(r[0]).lower(): int(r[1]) for r in rows}
            if actual != expected:
                raise ValueError('Warehouse row counts differ from local manifest')
        elif 'unexplained_difference' in columns:
            if rows:
                raise ValueError('Order reconciliation returned discrepancies')
        else:
            for row in rows:
                for column, value in zip(columns, row):
                    optional = column in OBSERVATIONS or (
                        column in {'null_product_ids', 'null_variant_ids'}
                        and 'FROM order_lines' in sql)
                    if column == 'table_name' or optional:
                        continue
                    if value is not None and value != 0:
                        raise ValueError(f'Warehouse validation failed: {column}={value}')
    return results


def connection_settings():
    from cryptography.hazmat.primitives import serialization
    required = ('ACCOUNT', 'USER', 'PRIVATE_KEY_PATH')
    for key in required:
        if not os.environ.get('SNOWFLAKE_' + key):
            raise ValueError('Missing SNOWFLAKE_' + key)
    key_path = Path(os.environ['SNOWFLAKE_PRIVATE_KEY_PATH']).expanduser()
    if not key_path.is_absolute():
        key_path = ROOT / key_path
    password = os.environ.get('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE')
    key = serialization.load_pem_private_key(key_path.read_bytes(),
                                           password=password.encode() if password else None)
    settings = {k: os.environ['SNOWFLAKE_' + k.upper()] for k in ('account', 'user')}
    settings.update(authenticator='SNOWFLAKE_JWT', private_key=key.private_bytes(
        serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    settings.update({k: os.environ.get('SNOWFLAKE_' + k.upper(), default)
                     for k, default in [('role', 'SYSADMIN'), ('warehouse', 'COMPUTE_WH')]})
    return settings


def live(output, report):
    import snowflake.connector
    stage = '@RETAIL_DB.CORE.CLEAN_CSV_STAGE/' + report['run_id'] + '/'
    with snowflake.connector.connect(**connection_settings()) as conn:
        with conn.cursor() as cur:
            # Reuse setup, CREATE LIKE, and COPY contracts; never run destructive 01_create_tables.
            for sql in statements('sql/core/02_load_tables.sql'):
                if sql.lstrip().upper().startswith('COPY INTO'):
                    continue
                if sql.startswith(('USE ROLE', 'USE WAREHOUSE')):
                    continue
                if 'INFORMATION_SCHEMA.LOAD_HISTORY' in sql:
                    continue
                cur.execute(sql)
            for table in TABLES:
                path = (output / (table + '.csv')).as_posix().replace("'", "''")
                cur.execute(f"PUT 'file://{path}' {stage} AUTO_COMPRESS=FALSE OVERWRITE=TRUE")
                uploads = cur.fetchall()
                if len(uploads) != 1 or uploads[0][6] not in ('UPLOADED', 'SKIPPED'):
                    raise ValueError(f'Upload failed for {table}')
            copies = []
            for sql in statements('sql/core/02_load_tables.sql'):
                if sql.lstrip().upper().startswith('COPY INTO'):
                    copies.append(sql.replace('@RETAIL_DB.CORE.CLEAN_CSV_STAGE', stage))
            report['copy_preflight'] = []
            for sql in copies:
                cur.execute(sql.replace("ON_ERROR = 'ABORT_STATEMENT'", "VALIDATION_MODE = 'RETURN_ALL_ERRORS'"))
                columns = [d[0].lower() for d in cur.description]
                errors = [dict(zip(columns, row)) for row in cur.fetchall()]
                table = re.search(r'COPY INTO (\S+)', sql).group(1)
                report['copy_preflight'].append({
                    'table': table, 'query_id': cur.sfqid,
                    'error_count': len(errors), 'errors': errors[:20],
                })
            failed = [r for r in report['copy_preflight'] if r['error_count']]
            if failed:
                first = failed[0]
                raise ValueError(
                    f"COPY preflight failed for {first['table']}: "
                    f"{first['error_count']} errors; "
                    f"{first['errors'][0].get('error', 'see report.json')}"
                )
            for sql in copies:
                cur.execute(sql)
                rows = cur.fetchall()
                if not rows or any(r[1] != 'LOADED' or r[5] != 0 for r in rows):
                    raise ValueError('COPY did not load cleanly')
            report['warehouse_validation'] = []
            validate(cur, report['counts'], report['warehouse_validation'])
            # DML-only transaction preserves the previous eight-table snapshot on failure.
            try:
                for sql in statements('sql/core/04_publish_tables.sql'):
                    cur.execute(sql)
            except BaseException:
                cur.execute('ROLLBACK')
                raise
    report['status'] = 'published'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-date', required=True, help='ISO date prefix of all five exports')
    parser.add_argument('--manifest', type=Path, required=True,
                        help='JSON completeness declaration; see README')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', args.batch_date):
        parser.error('--batch-date must be YYYY-MM-DD')
    if not __debug__:
        raise RuntimeError('Do not run with -O: cleaning assertions are required')
    load_dotenv(ROOT / '.env')
    data_dir = args.data_dir or Path(os.environ['RETAIL_DATA_DIR']).expanduser()
    try:
        declaration = json.loads(args.manifest.read_text())
    except FileNotFoundError:
        parser.error(
            f"Manifest not found: {args.manifest}. Create it using the batch.json "
            "example in README.md, with the selected batch date and confirmed "
            "snapshot completeness."
        )
    except json.JSONDecodeError as exc:
        parser.error(f"Invalid JSON in {args.manifest}: {exc.msg}")
    if declaration.get('batch_date') != args.batch_date or declaration.get('mode') != 'full_snapshot' or declaration.get('complete') is not True:
        raise ValueError('Manifest must declare this batch a complete full_snapshot')
    output = ROOT / 'data' / 'batches' / args.batch_date / uuid.uuid4().hex
    output.mkdir(parents=True)
    report = {'run_id': output.name, 'batch_date': args.batch_date, 'status': 'started',
              'sources': {}, 'declaration': declaration}
    # Serialize invocations in this workspace, including different batch dates.
    with (ROOT / 'data' / 'batch.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            tables = {}
            for name, (folder, suffix) in SOURCES.items():
                matches = list((data_dir / folder).glob(args.batch_date + '*' + suffix))
                if len(matches) != 1:
                    raise ValueError(f'{name}: expected exactly one dated export, found {len(matches)}')
                path = matches[0]
                before = digest(path)
                tables[name] = pd.read_csv(path, low_memory=False)
                if digest(path) != before:
                    raise ValueError(f'{name}: source changed during read')
                if tables[name].empty:
                    raise ValueError(f'{name}: empty source')
                report['sources'][name] = {'file': path.name, 'sha256': before, 'rows': len(tables[name])}
            with (output / 'clean.log').open('w') as log, contextlib.redirect_stdout(log):
                cleaned = clean(tables)
            report['counts'] = {}
            report['outputs'] = {}
            for name, frame in cleaned.items():
                if frame.empty:
                    raise ValueError(f'{name}: empty snapshot output')
                ddl = (ROOT / 'sql/core/01_create_tables.sql').read_text()
                body = re.search(r'CREATE TABLE IF NOT EXISTS ' + name.upper() + r' \((.*?)PRIMARY KEY', ddl, re.S).group(1)
                columns = re.findall(r'^    ([a-z_]+) ', body, re.M)
                if list(frame.columns) != columns:
                    raise ValueError(f'{name}: CSV column order differs from Snowflake DDL')
                path = output / (name + '.csv')
                frame.to_csv(path, index=False, na_rep='')
                report['counts'][name] = len(frame)
                report['outputs'][name] = digest(path)
            report['status'] = 'local_checks_passed'
            if args.live:
                live(output, report)
        except BaseException as exc:
            report['status'] = 'failed'
            report['error_type'] = type(exc).__name__
            raise
        finally:
            (output / 'report.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
            print('Batch report:', output / 'report.json')
    print(report['status'])


if __name__ == '__main__':
    main()
