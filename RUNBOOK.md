# Retail analytics batch

Five Shopify exports become eight clean CSVs and a validated Snowflake CORE snapshot.
Run from this repository with Python 3.10+ (the existing `venv` works):

```sh
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m retail_batch --batch-date 2026-11-10 --manifest batch.json
```

The default performs local checks only. Add `--live` to upload, load, validate, and
publish in one command. Credentials and `RETAIL_DATA_DIR` come from `.env` (see
`.env.example`); `--data-dir` overrides the source root. No credentials are logged.
The database and stage are intentionally the SQL project's fixed
`RETAIL_DB.CORE.CLEAN_CSV_STAGE`; role and warehouse use environment settings.

Create `batch.json` after confirming the exporter finished all five complete exports:

```json
{
  "batch_date": "2026-11-10",
  "mode": "full_snapshot",
  "complete": true,
  "evidence": "Describe the exporter completion check here"
}
```

Exactly one matching date-prefixed CSV is required in each of `Dim_Customers`,
`Fact_Orders`, `Dim_Products`, `Dim_Variants`, and `Dim_Inventory`. Ambiguous, missing,
empty, or changing files fail. Different source timestamps within that date are
allowed. The date prefix is the export's date, not a filter on order timestamps.

Each run writes eight CSVs, a cleaning log, source/output SHA-256 hashes, counts,
and `report.json` under `data/batches/<date>/<run-id>/` (gitignored, contains private
data). Keep these artifacts private. Failed runs retain a failure report; warehouse
check details are saved on successful validation. Exceptions propagate with a
nonzero exit code. An uncertain commit outcome can be retried with the same batch.

The cleaning module was extracted from `01_clean.ipynb` and preserves its assertions,
shipping-discount aggregation, grain checks, ID normalization, and type conversions.
Keep notebook and module contracts in sync. CSV order is checked against the table DDL.
Do not use Python `-O`, which disables assertions.

Live execution requires the existing CORE tables and permissions to create the
format, stage, schema, and INCOMING tables. It reuses `02_load_tables.sql`, uploads
to a unique run prefix, runs COPY preflight for all eight files, loads freshly
recreated INCOMING tables, and evaluates every result in `03_validate_tables.sql`.
Local cleaning is not a substitute for the additional warehouse semantic checks.
Destination counts must equal local counts. Guest customer IDs and null historical
catalog references are observations; populated unmatched references fail. Negative
available/on-hand inventory is observed; the other SQL inventory checks block.
Only passing batches execute the eight DML replacements in the transaction from
`04_publish_tables.sql`; a publish error triggers rollback. No destructive table
setup script is automatically executed. Stage artifacts are retained for audit.

Reruns replace the complete snapshot without appending duplicates. A filesystem
lock prevents simultaneous runners from this workspace. **Use a single writer:**
do not run manual loads or runners from another checkout/machine concurrently;
the shared INCOMING tables do not provide cross-host isolation. Do not publish an
older batch over a newer one unless deliberately restoring that snapshot. Cross-host
locking and stale-batch protection remain orchestration work.

Snapshot evidence: `notes.md` explicitly describes source snapshots and manual
full replacement. The locally available November 10 files include customers and
orders created in 2022, rather than just daily changes. This supports snapshot
publishing but cannot prove export completeness; the manifest records that external
check. Incremental batches are rejected, because overwrite would delete unchanged rows.

The inventory key mismatch was confirmed and corrected in the notebook's early
check: `(inventory_item_id, location_id)` is now consistent with its final model,
the cleaning module, and SQL. The saved upload notebook shows a successful PUT
and N-row test load on November 10 (Chicago time); no saved DNS error remains
in the workspace. This is historical evidence, not a current connectivity check.
Its missing-script repository locator was also repaired.

Local verification:

```sh
venv/bin/python -m unittest discover -s tests -v
```

Two November 10 local runs produced identical CSV hashes: N customers, N
products, N orders, N variants, N inventory items, N inventory levels,
N order lines, and N fulfillments. No live load was run during implementation.
Future work: verify a complete live batch, then add dbt models/tests, orchestration,
and CI/CD around these contracts.
