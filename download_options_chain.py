#!/usr/bin/env python3
"""
Daily Options Chain Downloader
===============================
Downloads options chain data (calls + puts, all available expirations, up to
a configurable cap) for major US index tickers / ETF proxies and mega-cap
stocks using yfinance. Saves results into a local SQLite database, with a
per-ticker CSV backup. Designed to be run once per day via cron, after market
close.

Free tools used: Python, yfinance, pandas, sqlite3 (all free / no signup).

Usage:
    python download_options_chain.py
    python download_options_chain.py --tickers SPY,AAPL,NVDA
    python download_options_chain.py --max-expirations 3
    python download_options_chain.py --skip-existing false   # force re-download
"""

import argparse
import logging
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Configuration  (edit this section to fit your watchlist)
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "options_data.db"
CSV_BACKUP_DIR = BASE_DIR / "csv_backups"
LOG_PATH = BASE_DIR / "options_downloader.log"

# True index options (cash-settled, European-style). Yahoo/yfinance does
# expose these, but data can occasionally be sparse or missing on some days.
INDEX_TICKERS = ["^SPX", "^NDX", "^RUT", "^DJI"]

# Liquid ETF proxies for the same indices (American-style, physically
# settled). These are generally the most reliable source via yfinance and
# what most retail options trackers actually use day to day.
INDEX_ETF_PROXIES = ["SPY", "QQQ", "IWM", "DIA"]

# Mega-cap stocks (edit freely)
MEGA_CAP_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "TSLA", "BRK-B", "AVGO", "LLY",
]

DEFAULT_TICKERS = INDEX_TICKERS + INDEX_ETF_PROXIES + MEGA_CAP_TICKERS

# How many upcoming expirations to pull per ticker (None = pull all of them,
# which for SPX-style weeklies can be 30+ and slow). 6 is generally enough to
# cover roughly two months of weekly/monthly contracts.
MAX_EXPIRATIONS = 6

# Seconds to sleep between tickers to avoid hammering Yahoo's endpoint
REQUEST_DELAY_SECONDS = 1.5

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

TABLE_COLUMNS = [
    "snapshot_date", "ticker", "category", "expiration", "option_type",
    "contract_symbol", "strike", "last_price", "bid", "ask",
    "change", "percent_change", "volume", "open_interest",
    "implied_vol", "in_the_money", "underlying_price",
]


def categorize(ticker: str) -> str:
    if ticker in INDEX_TICKERS:
        return "index"
    if ticker in INDEX_ETF_PROXIES:
        return "etf_proxy"
    return "stock"


def init_db(conn: sqlite3.Connection) -> None:
    # Legacy helper left in place; callers should create per-run tables via
    # `create_run_table(conn, table_name)` below.
    return None


def get_table_name(snapshot_date: str) -> str:
    """Return a safe per-run table name for the given snapshot_date.

    Example: snapshot_date '2026-06-18' -> 'options_chain_20260618'
    """
    return f"options_chain_{snapshot_date.replace('-', '')}"


def create_master_index(conn: sqlite3.Connection) -> None:
    """Create a small master index table mapping snapshot_date -> table_name."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs_index (
            snapshot_date TEXT PRIMARY KEY,
            table_name    TEXT UNIQUE,
            created_at    TEXT
        )
        """
    )
    conn.commit()


def register_run(conn: sqlite3.Connection, snapshot_date: str, table_name: str) -> None:
    """Register the run in `runs_index` if not already present."""
    from datetime import datetime

    conn.execute(
        "INSERT OR IGNORE INTO runs_index (snapshot_date, table_name, created_at) VALUES (?, ?, ?)",
        (snapshot_date, table_name, datetime.utcnow().isoformat()),
    )
    conn.commit()


def list_runs(conn: sqlite3.Connection):
    """Return list of (snapshot_date, table_name, created_at) rows from runs_index."""
    cur = conn.execute("SELECT snapshot_date, table_name, created_at FROM runs_index ORDER BY snapshot_date DESC")
    return cur.fetchall()


def create_run_table(conn: sqlite3.Connection, table_name: str) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            snapshot_date     TEXT NOT NULL,
            ticker            TEXT NOT NULL,
            category          TEXT,
            expiration        TEXT NOT NULL,
            option_type       TEXT NOT NULL,
            contract_symbol   TEXT,
            strike            REAL,
            last_price        REAL,
            bid               REAL,
            ask               REAL,
            change            REAL,
            percent_change    REAL,
            volume            REAL,
            open_interest     REAL,
            implied_vol       REAL,
            in_the_money      INTEGER,
            underlying_price  REAL,
            PRIMARY KEY (snapshot_date, contract_symbol)
        )
        """
    )
    # create a lookup index for the per-run table
    idx_name = f"idx_{table_name}_lookup"
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS {idx_name} "
        f"ON {table_name} (ticker, snapshot_date, expiration)"
    )
    conn.commit()


def already_downloaded(conn: sqlite3.Connection, ticker: str, snapshot_date: str) -> bool:
    """Return True if the given ticker already has rows in the per-run table."""
    table_name = get_table_name(snapshot_date)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    if cur.fetchone() is None:
        return False

    cur = conn.execute(
        f"SELECT 1 FROM {table_name} WHERE ticker = ? LIMIT 1",
        (ticker,),
    )
    return cur.fetchone() is not None


def fetch_ticker_chain(ticker: str, snapshot_date: str, max_expirations) -> pd.DataFrame:
    """Pull calls + puts across expirations for one ticker."""
    tk = yf.Ticker(ticker)

    try:
        expirations = tk.options
    except Exception as exc:
        log.warning("Could not get expirations for %s: %s", ticker, exc)
        return pd.DataFrame()

    if not expirations:
        log.warning("No options listed for %s", ticker)
        return pd.DataFrame()

    if max_expirations:
        expirations = expirations[:max_expirations]

    try:
        underlying_price = tk.fast_info.get("lastPrice")
    except Exception:
        underlying_price = None

    frames = []
    for exp in expirations:
        try:
            chain = tk.option_chain(exp)
        except Exception as exc:
            log.warning("Failed expiration %s for %s: %s", exp, ticker, exc)
            continue

        for option_type, df in (("call", chain.calls), ("put", chain.puts)):
            if df.empty:
                continue
            df = df.copy()
            df["snapshot_date"] = snapshot_date
            df["ticker"] = ticker
            df["category"] = categorize(ticker)
            df["expiration"] = exp
            df["option_type"] = option_type
            df["underlying_price"] = underlying_price
            frames.append(df)

        time.sleep(0.3)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.rename(
        columns={
            "contractSymbol": "contract_symbol",
            "lastPrice": "last_price",
            "percentChange": "percent_change",
            "openInterest": "open_interest",
            "impliedVolatility": "implied_vol",
            "inTheMoney": "in_the_money",
        }
    )

    for col in TABLE_COLUMNS:
        if col not in combined.columns:
            combined[col] = None

    combined["in_the_money"] = combined["in_the_money"].fillna(False).astype(bool).astype(int)
    return combined[TABLE_COLUMNS]


def parse_args():
    parser = argparse.ArgumentParser(description="Download daily options chain data into SQLite + CSV")
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated ticker override, e.g. SPY,AAPL,NVDA. Defaults to the built-in watchlist.",
    )
    parser.add_argument(
        "--max-expirations",
        type=int,
        default=MAX_EXPIRATIONS,
        help="Cap on expirations pulled per ticker (default: %(default)s). Use 0 for no cap.",
    )
    parser.add_argument(
        "--skip-existing",
        type=str,
        default="true",
        choices=["true", "false"],
        help="Skip tickers already downloaded for today's date (default: true). "
             "Set to false to force re-download / overwrite-by-append.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = [t.strip() for t in args.tickers.split(",")] if args.tickers else DEFAULT_TICKERS
    max_expirations = args.max_expirations or None
    skip_existing = args.skip_existing == "true"

    snapshot_date = date.today().isoformat()
    log.info("=== Starting options chain download for %s (%d tickers) ===", snapshot_date, len(tickers))

    CSV_BACKUP_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # create the master index and the per-run table for this snapshot
    create_master_index(conn)
    table_name = get_table_name(snapshot_date)
    create_run_table(conn, table_name)
    register_run(conn, snapshot_date, table_name)

    total_rows = 0
    failures = []

    for ticker in tickers:
        if skip_existing and already_downloaded(conn, ticker, snapshot_date):
            log.info("%s: already have today's data, skipping", ticker)
            continue

        log.info("Fetching %s ...", ticker)
        df = fetch_ticker_chain(ticker, snapshot_date, max_expirations)

        if df.empty:
            log.warning("%s: no data returned", ticker)
            failures.append(ticker)
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        try:
            df.to_sql(table_name, conn, if_exists="append", index=False)
        except sqlite3.IntegrityError as exc:
            log.warning("%s: some rows already existed, partial insert skipped (%s)", ticker, exc)

        csv_path = CSV_BACKUP_DIR / f"{ticker.replace('^', '')}_{snapshot_date}.csv"
        df.to_csv(csv_path, index=False)

        total_rows += len(df)
        log.info("%s: %d rows saved (%d expirations)", ticker, len(df), df["expiration"].nunique())

        time.sleep(REQUEST_DELAY_SECONDS)

    conn.close()
    log.info(
        "=== Done. %d total rows saved. Failures: %s ===",
        total_rows, ", ".join(failures) if failures else "none",
    )


if __name__ == "__main__":
    main()
