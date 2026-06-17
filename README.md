# Daily Options Chain Downloader

Free, automated pipeline: **yfinance → SQLite → GitHub Actions**. No paid API,
no local server, no signup required (GitHub account only).

## Quick Start: GitHub Actions (Recommended)
This project uses **GitHub Actions** to automatically download options data on
a schedule and commit it to the repository. No local cron job needed!

### Setup (5 minutes)
1. Fork or clone this repository to your GitHub account
2. Push to GitHub
3. Go to **Settings → Actions → General** and ensure "Allow all actions..." is enabled
4. The workflow runs automatically on the schedule (default: 9 PM UTC weekdays)

That's it. Your data downloads and commits every day.

### Customize the cron schedule
Edit `.github/workflows/download-options.yml`, find the `schedule` section:

```yaml
on:
  schedule:
    - cron: '0 21 * * 1-5'  # ← Change this line
```

| Time | Cron | Notes |
|---|---|---|
| 4 PM ET (market close) | `0 21 * * 1-5` | During EDT (roughly Mar–Nov) |
| 3 PM ET | `0 20 * * 1-5` | During EDT |
| 5 PM ET | `0 22 * * 1-5` | During EDT |
| 4 PM ET (winter) | `0 20 * * 1-5` | During EST (roughly Nov–Mar) |

GitHub Actions runs in **UTC**. US market close = 4 PM ET = 20:00 UTC (EST) or
21:00 UTC (EDT). Use [crontab.guru](https://crontab.guru) to double-check your
desired time.

### Monitor runs
1. Go to your repo → **Actions** tab
2. Click "Daily Options Chain Download" 
3. See past runs, logs, and status

Each run commits the updated database and CSVs to the repo (visible in git
history under "Commits").

---

## Alternative: Local cron (Advanced)
If you prefer running this locally instead, see **Local Cron Setup** below.

## Files
- `download_options_chain.py` — main script, pulls data daily
- `check_data.py` — sanity-check queries against the database
- `requirements.txt` — `yfinance`, `pandas`
- `.github/workflows/download-options.yml` — GitHub Actions schedule
- `options_data.db` — SQLite database (created on first run)
- `csv_backups/` — one CSV per ticker per day (created automatically)
- `options_downloader.log` — log file for debugging failed runs

## Why this stack
- **yfinance**: free, no API key, pulls Yahoo Finance's options chains
  (calls + puts, all strikes, all listed expirations).
- **SQLite**: free, zero setup, no server to run — just a file on disk. If you
  later need multi-user access or outgrow a single file, swap to free options
  like **PostgreSQL** (local) or free-tier **Supabase/Neon**. The script
  isolates all DB logic in `init_db()` / `to_sql()`, so that swap is small.
- **GitHub Actions**: free tier includes 2000 minutes/month, plenty for once-daily
  runs. Data stays in your repo (version control + history). No local server.

---

## Local Cron Setup (Optional / Advanced)

If you prefer running this script on your own machine instead of GitHub Actions:

### 1. One-time setup

```bash
cd /path/to/options_downloader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Test it manually first:

```bash
python3 download_options_chain.py --tickers SPY,AAPL --max-expirations 2
python3 check_data.py
```

### 2. Set up cron
Find your Python path:
```bash
realpath venv/bin/python3
pwd
```

Open crontab:
```bash
crontab -e
```

Add a line (example: 6 PM ET weekdays, adjust for your timezone):
```cron
0 22 * * 1-5 TZ='America/New_York' cd /path/to/options_downloader && /path/to/venv/bin/python3 download_options_chain.py >> cron.log 2>&1
```

**Better approach**: use a wrapper shell script:

```bash
#!/bin/bash
# run_daily.sh
cd "$(dirname "$0")"
source venv/bin/activate
python3 download_options_chain.py >> cron.log 2>&1
```

```bash
chmod +x run_daily.sh
```

Then in crontab:

```cron
0 22 * * 1-5 /path/to/options_downloader/run_daily.sh
```

Verify it registered:

```bash
crontab -l
```

---

## What it downloads
By default, three groups of tickers (edit the lists at the top of
`download_options_chain.py` to change them):

| Group | Tickers | Notes |
|---|---|---|
| True index options | `^SPX ^NDX ^RUT ^DJI` | Cash-settled, European-style. Yahoo/yfinance expose these but data can occasionally be sparse on a given day. |
| Index ETF proxies | `SPY QQQ IWM DIA` | American-style, physically settled. Most reliable source for index-like options data via yfinance. |
| Mega-cap stocks | `AAPL MSFT GOOGL AMZN NVDA META TSLA BRK-B AVGO LLY` | Edit freely. |

Each row saved includes: ticker, category, expiration, option type, strike,
last price, bid/ask, change, volume, open interest, implied volatility,
in-the-money flag, and the underlying's last price at fetch time.

By default it pulls the **nearest 6 expirations** per ticker (configurable
via `MAX_EXPIRATIONS` or `--max-expirations`) to keep daily run time
reasonable — SPX-style tickers can have 30+ listed expirations.

The script is idempotent by default (`--skip-existing true`), so if the workflow
fires twice, or you run it manually the same day, it won't duplicate rows — it
checks the database first and skips tickers already saved for today's date.

---

## Querying Your Data

Once data starts flowing in, query it locally:

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect("options_data.db")

# Get all AAPL options for a specific date
df = pd.read_sql(
    "SELECT * FROM options_chain WHERE ticker='AAPL' AND snapshot_date='2026-06-17'",
    conn
)
print(df[['expiration', 'option_type', 'strike', 'last_price', 'implied_vol']])
```

Or from the command line:

```bash
sqlite3 options_data.db
SELECT COUNT(*) FROM options_chain;
SELECT DISTINCT ticker FROM options_chain;
SELECT * FROM options_chain WHERE ticker='SPY' LIMIT 5;
```

Use `check_data.py` for quick sanity checks:

```bash
python check_data.py
```

---

## Troubleshooting

### GitHub Actions workflow isn't running
- Check that Actions are enabled: **Repo Settings → Actions → General → "Allow all actions..."**
- Manually trigger the workflow: **Actions → Daily Options Chain Download → "Run workflow"**
- Check run logs: **Actions → Daily Options Chain Download → (latest run) → "download-options" job**

### No data in the database
- Run manually to see errors: `python download_options_chain.py`
- Check the log file: `cat options_downloader.log`
- Verify internet connectivity to Yahoo Finance
- Try fetching a single ticker: `python download_options_chain.py --tickers SPY`

### GitHub Actions permission errors when committing
- Verify `GITHUB_TOKEN` is available (it's injected automatically by GitHub)
- Check repo Settings → Actions → General → "Workflow permissions" — ensure
  "Read and write permissions" is selected

### Cron not running (local setup only)
- Verify with `crontab -l` (should list your job)
- Check system logs: `log stream --level=debug` (macOS) or `journalctl` (Linux)
- Manually test the script: `/path/to/venv/bin/python3 /path/to/download_options_chain.py`

---

## Final Notes

### For options traders
- Yahoo Finance data is **delayed/end-of-day**, not real-time. Fine for daily
  IV/volume/OI tracking, not for live execution.
- Index tickers like `^SPX` occasionally return empty chains via yfinance even
  when Yahoo's site shows data. If this happens frequently, rely on ETF proxies
  (`SPY`, `QQQ`) instead — they're far more consistently available.
- Implied Volatility comes directly from Yahoo; no independent Greeks
  calculation is performed here. Volume and OI are also delayed.

### Customizing the watchlist
Edit `.github/workflows/download-options.yml` to run on your schedule, or edit
`download_options_chain.py` to change which tickers/expirations you pull.

### Scaling up
If you need live data, real-time Greeks, or multi-machine access, consider:
- **Live options data**: Upgrade to a paid API (Interactive Brokers, Tastytrade, etc.)
- **Real-time Greek calculations**: Add QuantLib or similar
- **Distributed access**: Migrate from SQLite to PostgreSQL (free, self-hosted or
  free-tier Supabase/Neon)

### License & Contributing
Use freely for personal trading. Contributions welcome!
