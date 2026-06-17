# Cron Schedule Quick Reference

## GitHub Actions Cron Syntax

File: `.github/workflows/download-options.yml`

```yaml
on:
  schedule:
    - cron: 'MINUTE HOUR * * DAY_OF_WEEK'
```

| Component | Values | Example |
|---|---|---|
| MINUTE | 0–59 | `0` = top of the hour |
| HOUR | 0–23 (UTC) | `21` = 9 PM UTC |
| DAY_OF_WEEK | 0–6 (0=Sun, 6=Sat) or 1–5 | `1-5` = Mon–Fri |

## Common Schedule Examples

### US Market Close (4 PM ET)

**During EDT (Mar–Nov)**: 4 PM ET = 20:00 UTC
```yaml
- cron: '0 20 * * 1-5'
```

**During EST (Nov–Mar)**: 4 PM ET = 21:00 UTC
```yaml
- cron: '0 21 * * 1-5'
```

**Auto-adjust (single cron works both)**: Use 21:00 UTC, triggers ~1 hour
after actual close during EDT, ~at close during EST:
```yaml
- cron: '0 21 * * 1-5'
```

### 30 minutes after market close (4:30 PM ET)

**EDT**: `0 20 * * 1-5` → 20:30 UTC
```yaml
- cron: '30 20 * * 1-5'
```

**EST**: `0 21 * * 1-5` → 21:30 UTC
```yaml
- cron: '30 21 * * 1-5'
```

### 1 hour after market close (5 PM ET)

**EDT**:
```yaml
- cron: '0 21 * * 1-5'
```

**EST**:
```yaml
- cron: '0 22 * * 1-5'
```

### Daily at midnight UTC
```yaml
- cron: '0 0 * * *'
```

### Weekdays only at 3 PM UTC
```yaml
- cron: '0 15 * * 1-5'
```

## Timezone Reference (UTC offsets)

| Region | Standard | Daylight |
|---|---|---|
| US/Eastern | EST = UTC-5 | EDT = UTC-4 |
| US/Central | CST = UTC-6 | CDT = UTC-5 |
| US/Mountain | MST = UTC-7 | MDT = UTC-6 |
| US/Pacific | PST = UTC-8 | PDT = UTC-7 |

**Example**: US market close at 4 PM ET
- During EDT (Mar–Nov): 4 PM + 4 hours = 20:00 UTC → `0 20 * * 1-5`
- During EST (Nov–Mar): 4 PM + 5 hours = 21:00 UTC → `0 21 * * 1-5`

## Verify your cron timing

Use [crontab.guru](https://crontab.guru) to double-check:
1. Enter your cron expression
2. Check "Next 5 occurrences"
3. Verify it matches your desired time

## Setting schedule via GitHub UI (Manual)

If you prefer not to edit YAML:
1. Go to **Actions** tab → **Daily Options Chain Download**
2. Click "..." (three dots) → **Edit workflow**
3. Find the `schedule` section and modify the cron value
4. Click "Start commit" to save

## Multiple schedules (optional)

Run at two different times:

```yaml
on:
  schedule:
    - cron: '0 20 * * 1-5'  # Early run
    - cron: '30 21 * * 1-5' # Late run
```

This creates two jobs per run. Use this if you want to capture data at multiple
points (e.g., right after close + 1 hour later).
