import os
import pandas as pd
from sqlalchemy import create_engine
import pymysql

# --- Config ---
downloads_dir = os.path.expanduser("~/Downloads")

# find the latest file that ends with "_Customers.csv"
files = [f for f in os.listdir(downloads_dir) if f.endswith("_Customers.csv")]
if not files:
    raise FileNotFoundError("No Customers CSV file found in Downloads.")

latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(downloads_dir, f)))
csv_file = os.path.join(downloads_dir, latest_file)