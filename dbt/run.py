"""Run dbt from the repository root, loading the existing private .env safely."""
import os
from pathlib import Path
import subprocess
import sys
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
key = os.environ.get('SNOWFLAKE_PRIVATE_KEY_PATH')
if key:
    path = Path(key).expanduser()
    os.environ['SNOWFLAKE_PRIVATE_KEY_PATH'] = str(
        path if path.is_absolute() else ROOT / path)
executable = Path(sys.executable).parent / 'dbt'
if not executable.is_file():
    raise SystemExit('Install dbt first: venv/bin/python -m pip install -r requirements-dbt.txt')
raise SystemExit(subprocess.call([
    str(executable), *(sys.argv[1:] or ['--help']),
    '--project-dir', str(ROOT / 'dbt'), '--profiles-dir', str(ROOT / 'dbt')
]))
