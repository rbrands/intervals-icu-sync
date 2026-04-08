# Copilot Instructions

## Language

All code, comments, variable names, function names, and documentation must be written in **English**.

## README

- The `README.md` must be kept up to date.
- Whenever a new script is added or an existing script is changed, update the relevant section in `README.md`.
- The project structure section in `README.md` must reflect the actual file layout at all times.
- Usage examples in `README.md` must match the current script behavior (arguments, output filenames, etc.).

## Project Overview

This project fetches, analyzes, and exports cycling training data from the [intervals.icu](https://intervals.icu) API.

- **Language**: Python 3.12+
- **Virtual environment**: `.venv/`
- **Dependencies**: `requirements.txt`
- **Configuration**: `.env` file (never committed); `API_KEY` and `ATHLETE_ID` are loaded via `src/intervals_icu/config.py`

## Project Structure

```
intervals-icu-sync/
├── scripts/                        # Runnable entry-point scripts
│   ├── get_activities.py           # Fetch activities → data/raw/
│   ├── get_metrics.py              # Fetch athlete metrics → data/processed/
│   ├── analyze_week.py             # Analyze current calendar week (Joe Friel)
│   ├── prepare_activities_for_coach.py  # Export simplified JSON for coach/ChatGPT
│   ├── fueling_analysis.py         # Analyze carbohydrate fueling quality
│   └── prepare_week_for_coach.py   # Run all scripts in sequence
├── src/
│   └── intervals_icu/
│       ├── __init__.py
│       ├── client.py               # HTTP client (intervals.icu API)
│       └── config.py               # Loads API_KEY, ATHLETE_ID from .env
├── data/
│   ├── raw/                        # Raw API responses (git-ignored)
│   └── processed/                  # Derived JSON exports (git-ignored)
├── .env.example
├── requirements.txt
└── README.md
```

## Code Conventions

- All scripts are runnable directly: `python scripts/<script>.py`
- Scripts import from `src/` using `sys.path` insertion or the package being installed in editable mode.
- Raw data is always saved to `data/raw/`, processed/derived data to `data/processed/`.
- Output filenames include an ISO date (Monday of the current week or today) for traceability.
- Use `pathlib.Path` for all file path handling — never `os.path`.
- Keep functions small and named clearly. Each script has a `main()` entry point.
- No hardcoded credentials. Always read from environment variables via `config.py`.

## Data Flow

```
intervals.icu API
    → get_activities.py       → data/raw/activities_{date}.json
    → get_metrics.py          → data/processed/metrics_{date}.json
    → prepare_activities_for_coach.py    → data/processed/coach_input_{monday}.json
    → fueling_analysis.py     → data/processed/fueling_analysis_{monday}.json
    → analyze_week.py         → console output only
    (prepare_week_for_coach.py runs all of the above in order)
```

## intervals.icu API

- Base URL: `https://intervals.icu/api/v1`
- Auth: HTTP Basic with `auth=("API_KEY", api_key)` — the username is literally `"API_KEY"`
- Activity source filter: `source != "STRAVA"` (keeps Garmin Connect and manual uploads)
- Date range for activity fetches: Monday of the previous week → today

## Security

- Never commit `.env` or any file containing credentials.
- Never log or print the API key.
- Validate all external data at the boundary (API responses may be `None` or missing fields).
