# intervals-icu-sync

A Python project for experimenting with the [intervals.icu](https://intervals.icu) API.

## Description

`intervals-icu-sync` provides a clean, extensible structure for:

- Fetching training data from intervals.icu
- Storing raw data locally as JSON files
- A foundation for future features like analysis and uploading planned workouts

## Project Structure

```
intervals-icu-sync/
│
├── scripts/
│   └── get_activities.py   # Fetch activities and save to data/raw/
│
├── src/
│   └── intervals_icu/
│       ├── __init__.py
│       ├── client.py       # API client
│       └── config.py       # Environment / configuration helpers
│
├── data/
│   └── raw/                # Downloaded JSON files (git-ignored)
│
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install requirements

```bash
pip install -r requirements.txt
```

### 3. Set your API key

```bash
cp .env.example .env
# Edit .env and replace 'your_api_key_here' with your actual intervals.icu API key
```

You can find your API key in the intervals.icu settings under **Profile → API**.

## How to Run

Fetch activities for the last 7 days and save them to `data/raw/`:

```bash
python scripts/get_activities.py
```

The script will print the path to the saved JSON file, e.g.:

```
Saved 12 activities to data/raw/activities_2024-06-01.json
```
