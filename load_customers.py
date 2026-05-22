"""
load_customers.py
-----------------
Loads the latest Shopify Customers CSV export from Downloads,
cleans and transforms it for Python-based analysis.

No database connections — pure pandas for local analysis.

Usage:
    Run directly, or import load_customers() into a notebook:
    from setup.load_customers import load_customers
    df = load_customers()
"""

import os
import pandas as pd
from pathlib import Path


# ─── CONFIG ───────────────────────────────────────────────────────────────────

DOWNLOADS = Path.home() / "Downloads"
CLEAN_DIR = Path("data/clean")
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────


def find_latest_export(folder: Path, suffix: str) -> Path:
    """Find the most recently modified file matching the given suffix."""
    matches = [f for f in folder.iterdir() if f.name.endswith(suffix)]
    if not matches:
        raise FileNotFoundError(f"No file ending in '{suffix}' found in {folder}")
    return max(matches, key=lambda f: f.stat().st_mtime)


def load_customers(save_clean: bool = True) -> pd.DataFrame:
    """
    Load, clean, and return the Shopify customers export as a DataFrame.

    Parameters
    ----------
    save_clean : bool
        If True, saves the cleaned DataFrame to data/clean/customers.csv

    Returns
    -------
    pd.DataFrame
        Cleaned customers DataFrame ready for analysis.
    """

    # ── Load ──────────────────────────────────────────────────────────────────
    csv_file = find_latest_export(DOWNLOADS, "_Customers.csv")
    print(f"Loading: {csv_file.name}")

    df = pd.read_csv(csv_file)
    print(f"  Raw rows: {len(df):,}")

    # ── Extract customer_id from Shopify GID ──────────────────────────────────
    df['customer_id'] = (
        df['ID']
        .str.extract(r'Customer/(\d+)', expand=False)
        .astype('Int64')   # nullable int — handles any missing extractions
    )

    # ── Rename columns ────────────────────────────────────────────────────────
    df.rename(columns={
        'First name':           'first_name',
        'Last name':            'last_name',
        'Email':                'email',
        'Phone':                'phone',
        'Created at':           'created_at',
        'Amount spent':         'total_spent',
        'Number of orders':     'orders_count',
        'Tags':                 'tags',
        'Addresses: City':      'city',
        'Addresses: Province':  'state',
    }, inplace=True)

    # ── Select analysis columns ───────────────────────────────────────────────
    columns_needed = [
        'customer_id', 'first_name', 'last_name', 'email', 'phone',
        'created_at', 'total_spent', 'orders_count', 'tags', 'city', 'state'
    ]

    # Only keep columns that actually exist (guards against export variations)
    columns_present = [c for c in columns_needed if c in df.columns]
    missing = set(columns_needed) - set(columns_present)
    if missing:
        print(f"  ⚠ Columns not found in export (skipped): {missing}")

    df = df[columns_present]

    # ── Clean types ───────────────────────────────────────────────────────────
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce', utc=True)
    df['total_spent'] = pd.to_numeric(df['total_spent'], errors='coerce')
    df['orders_count'] = pd.to_numeric(df['orders_count'], errors='coerce').astype('Int64')

    # String fields — strip whitespace, normalize blanks to NaN
    str_cols = ['first_name', 'last_name', 'email', 'phone', 'tags', 'city', 'state']
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype('string').str.strip()
            df[col] = df[col].replace({'': pd.NA, 'nan': pd.NA})

    # ── Deduplicate ───────────────────────────────────────────────────────────
    before = len(df)
    df.drop_duplicates(subset='customer_id', keep='last', inplace=True)
    dupes_removed = before - len(df)
    if dupes_removed:
        print(f"  Removed {dupes_removed} duplicate customer_id rows")

    # ── Drop rows with no customer_id (unparseable IDs) ───────────────────────
    df.dropna(subset=['customer_id'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    print(f"  Clean rows: {len(df):,}")

    # ── Save clean copy ───────────────────────────────────────────────────────
    if save_clean:
        out = CLEAN_DIR / "customers.csv"
        df.to_csv(out, index=False)
        print(f"  Saved → {out}")

    return df


# ── Quick summary when run directly ───────────────────────────────────────────
if __name__ == "__main__":
    df = load_customers()

    print("\n─── Preview ───────────────────────────────")
    print(df.head())

    print("\n─── Data Types ────────────────────────────")
    print(df.dtypes)

    print("\n─── Nulls ─────────────────────────────────")
    print(df.isnull().sum())

    print("\n─── Quick Stats ────────────────────────────")
    print(f"  Total customers:     {len(df):,}")
    print(f"  Avg total spent:    ${df['total_spent'].mean():,.2f}")
    print(f"  Avg orders/customer: {df['orders_count'].mean():.1f}")
    if 'state' in df.columns:
        print(f"\n  Top 5 states:")
        print(df['state'].value_counts().head())