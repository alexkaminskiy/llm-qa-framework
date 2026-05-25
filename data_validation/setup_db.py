from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "supply_chain.db"


def setup_supply_chain_db(db_path: Path = DB_PATH) -> Path:
    """Loads CSV files into SQLite. Returns path to the database file."""
    bom = pd.read_csv(DATA_DIR / "bom.csv")
    suppliers = pd.read_csv(DATA_DIR / "suppliers.csv")

    with sqlite3.connect(str(db_path)) as conn:
        bom.to_sql("bom", conn, if_exists="replace", index=False)
        suppliers.to_sql("suppliers", conn, if_exists="replace", index=False)

    return db_path


if __name__ == "__main__":
    path = setup_supply_chain_db()
    print(f"Database created at {path}")