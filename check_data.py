#!/usr/bin/env python3
"""
Quick sanity-check / example queries against options_data.db
Run any time to confirm the cron job is actually populating data.

    python check_data.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "options_data.db"

QUERIES = {
    "Rows per snapshot date": """
        SELECT snapshot_date, COUNT(*) AS rows, COUNT(DISTINCT ticker) AS tickers
        FROM options_chain
        GROUP BY snapshot_date
        ORDER BY snapshot_date DESC
        LIMIT 10
    """,
    "Latest snapshot, rows per ticker": """
        SELECT ticker, category, COUNT(*) AS rows, COUNT(DISTINCT expiration) AS expirations
        FROM options_chain
        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM options_chain)
        GROUP BY ticker, category
        ORDER BY category, ticker
    """,
    "Sample rows (most recent snapshot, SPY calls)": """
        SELECT ticker, expiration, option_type, strike, last_price, bid, ask,
               volume, open_interest, implied_vol
        FROM options_chain
        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM options_chain)
          AND ticker = 'SPY' AND option_type = 'call'
        ORDER BY expiration, strike
        LIMIT 10
    """,
}


def main():
    if not DB_PATH.exists():
        print(f"No database found yet at {DB_PATH}. Run download_options_chain.py first.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    for title, sql in QUERIES.items():
        print(f"\n--- {title} ---")
        rows = conn.execute(sql).fetchall()
        if not rows:
            print("(no rows)")
            continue
        cols = rows[0].keys()
        print(" | ".join(cols))
        for r in rows:
            print(" | ".join(str(r[c]) for c in cols))

    conn.close()


if __name__ == "__main__":
    main()
