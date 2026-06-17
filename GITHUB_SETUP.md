# GitHub Setup Guide

Complete setup in 10 minutes with zero local configuration.

## Prerequisites
- GitHub account (free)
- This repository forked/cloned to your GitHub account

## Step 1: Fork this repository

1. Click **Fork** button at the top-right of this repo on GitHub
2. This creates your own copy

## Step 2: Enable GitHub Actions

1. Go to your fork
2. Click **Settings** (top menu)
3. Expand **Actions** (left sidebar) → **General**
4. Under **Actions permissions**, select:
   - ☑️ **Allow all actions and reusable workflows**
5. Click **Save**

## Step 3: Customize the cron schedule (optional)

The default schedule runs at **9 PM UTC** on **weekdays** (Monday–Friday).

If you want to change when it runs (e.g., 4 PM ET = 20:00 UTC during EDT):

1. Go to your fork
2. Click **Code** tab
3. Navigate to `.github/workflows/download-options.yml`
4. Click the pencil icon (Edit) in the top-right
5. Find this section:
   ```yaml
   on:
     schedule:
       - cron: '0 21 * * 1-5'
   ```
6. Change the `cron: '0 21 * * 1-5'` value:
   - `0 21 * * 1-5` = 9 PM UTC, weekdays
   - `0 20 * * 1-5` = 8 PM UTC, weekdays (4 PM ET during EDT)
   - `0 22 * * 1-5` = 10 PM UTC, weekdays (5 PM ET)
   - See `CRON_SCHEDULE.md` for more examples
7. Click **Commit changes** (green button)

## Step 4: Wait for first run (or trigger manually)

The workflow will run automatically on your schedule. To test immediately:

1. Go to **Actions** tab
2. Click **Daily Options Chain Download** (left sidebar)
3. Click **Run workflow** (blue button, top-right)
4. Select **Run workflow**

Watch the run in progress:
1. Click the run entry that just appeared
2. Click **download-options** under "Jobs"
3. Watch the live logs

## Step 5: Check your data

After the first run completes:

1. Go to **Code** tab
2. Look for `options_data.db` (SQLite database file) — this contains all your data
3. Look for `csv_backups/` folder — contains one CSV per ticker per date
4. Check **Commits** to see the automated commits after each run

## Step 6: Query your data locally

Once you have data, you can download and query it locally:

```bash
# Clone your fork to your local machine
git clone https://github.com/YOUR_USERNAME/options_downloader.git
cd options_downloader

# Install pandas (optional, for Python queries)
pip install pandas sqlite3

# Query with Python
python3 << 'EOF'
import sqlite3
import pandas as pd

conn = sqlite3.connect("options_data.db")
df = pd.read_sql(
    "SELECT ticker, expiration, COUNT(*) as rows FROM options_chain WHERE snapshot_date='2026-06-17' GROUP BY ticker, expiration",
    conn
)
print(df)
EOF
```

Or use the command line:

```bash
sqlite3 options_data.db
SELECT COUNT(*) FROM options_chain;
SELECT DISTINCT DATE(snapshot_date) FROM options_chain;
SELECT * FROM options_chain WHERE ticker='AAPL' LIMIT 10;
.quit
```

## Customizing your watchlist

Edit the tickers the workflow pulls:

1. Go to **Code** tab
2. Open `download_options_chain.py`
3. Click the pencil icon (Edit)
4. Find the **Configuration** section (near the top):
   ```python
   INDEX_TICKERS = ["^SPX", "^NDX", "^RUT", "^DJI"]
   INDEX_ETF_PROXIES = ["SPY", "QQQ", "IWM", "DIA"]
   MEGA_CAP_TICKERS = [
       "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
       ...
   ]
   ```
5. Edit the lists as desired (comma-separated, quoted)
6. Scroll down and click **Commit changes**

The next scheduled run will use your new watchlist.

## Monitoring runs

**Every time the workflow runs**, it:
1. Downloads options data from yfinance
2. Saves to `options_data.db`
3. Commits changes to your repo
4. Logs any errors to `options_downloader.log` (visible in run artifacts)

### View past runs

1. Click **Actions** tab
2. Click **Daily Options Chain Download**
3. See a list of all past runs with status (✅ success, ❌ failed, ⏳ in progress)
4. Click any run to see detailed logs

### Download logs

1. Go to a completed run
2. Look for **Artifacts** section at the bottom
3. Download `options-downloader-log` (ZIP file with the log)

## Troubleshooting

### Workflow not triggering at scheduled time
- GitHub Actions can have 5–10 minute delays; wait a bit longer
- Manually trigger: **Actions → Daily Options Chain Download → Run workflow**
- Check that Actions are enabled in **Settings → Actions → General**

### Run failed / errors in logs
1. Go to the failed run
2. Click **download-options** job
3. Expand each step to see error messages
4. Common issues:
   - Network timeout (yfinance temporarily unavailable) — will retry next day
   - No internet access (rare) — check runner connectivity
   - Permission denied when committing — check Settings → Actions → Workflow permissions

### Data not updating in repo
1. Check **Code** tab — do you see `options_data.db` and `csv_backups/` changing?
2. Look at **Commits** — do you see new commits from `github-actions[bot]`?
3. If not, check the run logs for errors during the commit step

### Want to stop the workflow?
1. Go to `.github/workflows/download-options.yml`
2. Comment out the entire `schedule` section:
   ```yaml
   #on:
   #  schedule:
   #    - cron: '0 21 * * 1-5'
   ```
3. Commit changes
4. Workflow will no longer run automatically

## Cost
- **Free**: GitHub Actions free tier gives you 2000 minutes/month
- This workflow runs ~5 minutes per day → ~150 minutes/month
- Well within the free tier ✅

## Next steps
- Read `README.md` for full documentation
- See `CRON_SCHEDULE.md` for more cron timing examples
- Check `check_data.py` for example queries
