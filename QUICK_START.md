# Quick Start Summary

## What's New: GitHub Actions Automation

Your options downloader now runs entirely on **GitHub** with **zero local setup**. The cron schedule is defined in a YAML file, not your machine's cron table.

## 3-Step Setup

### 1. Push to GitHub
```bash
git clone https://github.com/YOUR_USERNAME/options_downloader.git
cd options_downloader
git push
```

### 2. Enable GitHub Actions
- Go to **Settings → Actions → General**
- Select "Allow all actions"
- Click **Save**

### 3. (Optional) Customize the schedule
Edit `.github/workflows/download-options.yml`:
```yaml
on:
  schedule:
    - cron: '0 21 * * 1-5'  # ← Change this line
```

That's it. Data downloads automatically every day.

## File Structure

```
options_downloader/
├── .github/workflows/
│   └── download-options.yml      ← GitHub Actions schedule (EDIT THIS for cron)
├── .gitignore
├── download_options_chain.py      ← Main script (pulls yfinance data)
├── check_data.py                  ← Query helper
├── requirements.txt               ← Dependencies
├── options_data.db                ← SQLite (auto-created)
├── csv_backups/                   ← Per-ticker CSVs (auto-created)
├── README.md                      ← Full documentation
├── GITHUB_SETUP.md                ← Step-by-step GitHub guide
└── CRON_SCHEDULE.md               ← Cron timing examples
```

## Key Changes from Local Cron

| Before | Now |
|--------|-----|
| `crontab -e` on your machine | Edit `.github/workflows/download-options.yml` |
| Depends on your computer running 24/7 | GitHub Actions runners (always available) |
| Manual log checking | **Actions** tab shows all runs + logs |
| Data stays local | Data committed to GitHub (version history) |

## Common Cron Schedules

```yaml
# 4 PM ET (EDT)
- cron: '0 20 * * 1-5'

# 4 PM ET (EST)
- cron: '0 21 * * 1-5'

# Right after market close + 30 min (EDT)
- cron: '30 20 * * 1-5'

# Daily at noon UTC
- cron: '0 12 * * *'
```

See `CRON_SCHEDULE.md` for more.

## Monitoring

1. Go to **Actions** tab in your GitHub repo
2. Click "Daily Options Chain Download"
3. See all past runs with ✅ or ❌ status
4. Click a run to see full logs
5. Download `options-downloader-log` artifact to see detailed output

## Data Access

Your data (SQLite + CSVs) is committed to the repo automatically after each run.

```bash
# Pull latest data locally
git pull

# Query it
sqlite3 options_data.db "SELECT * FROM options_chain LIMIT 5"

# Or with Python
python3 check_data.py
```

## Troubleshooting

**Workflow not running?**
- Check **Settings → Actions → General** (must be enabled)
- Manually trigger: **Actions → Run workflow** button

**No data in database?**
- Check the run logs: **Actions → Daily Options Chain Download → (latest run)**
- Look for error messages in the "Run options chain downloader" step

**Want to change the watchlist?**
- Edit `download_options_chain.py` → Edit `INDEX_TICKERS`, `INDEX_ETF_PROXIES`, `MEGA_CAP_TICKERS` sections

## Next Steps

1. **Read `GITHUB_SETUP.md`** for detailed walk-through
2. **Read `README.md`** for full feature documentation
3. **Push to GitHub** and enable Actions
4. **Monitor your first run** in the **Actions** tab
