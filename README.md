# intervals-icu-sync

A Python project for fetching, analyzing, and exporting cycling training data from the [intervals.icu](https://intervals.icu) API.

## Description

`intervals-icu-sync` provides a set of scripts to:

- Fetch raw activity and wellness data from intervals.icu
- Analyze training quality per week using Joe Friel principles
- Export simplified summaries for a coach or ChatGPT
- Evaluate carbohydrate fueling quality per session
- Track performance metrics (FTP, VO2Max, CTL/ATL, HRV)

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
├── notebooks/
│   └── week_summary.ipynb          # Interactive weekly training overview
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
# Edit .env and set API_KEY and ATHLETE_ID
```

- **API_KEY**: found in intervals.icu under **Profile → API**
- **ATHLETE_ID**: your athlete ID, visible in the intervals.icu URL (e.g. `https://intervals.icu/athlete/i12345/...` → `i12345`)

## Data Flow

```
intervals.icu API
    → get_activities.py       → data/raw/activities_{date}.json
    → get_metrics.py          → data/processed/metrics_{date}.json
    → prepare_for_coach.py    → data/processed/coach_input_{monday}.json
    → fueling_analysis.py     → data/processed/fueling_analysis_{monday}.json
    → analyze_week.py         → console output only
```

## Scripts

### `get_activities.py`

Fetches cycling activities from intervals.icu (Monday of previous week → today) and saves them to `data/raw/`.

```bash
python scripts/get_activities.py
```

Output: `data/raw/activities_{date}.json`

---

### `get_metrics.py`

Fetches athlete performance metrics: FTP, eFTP, W', weight, CTL, ATL, resting HR, HRV, best 5-minute power, and calculated VO2Max.

```bash
python scripts/get_metrics.py
```

Output: `data/processed/metrics_{date}.json`

---

### `analyze_week.py`

Analyzes the current calendar week (Mon–Sun) using Joe Friel training principles. Classifies sessions (VO2max / Threshold / Endurance), computes aerobic decoupling, and prints a coaching interpretation.

```bash
python scripts/analyze_week.py
```

Output: console only

---

### `prepare_activities_for_coach.py`

Exports a simplified JSON of this week's rides for sharing with a coach or ChatGPT. Includes duration, training load, power, RPE, interval summary, decoupling, and carbohydrate intake.

```bash
python scripts/prepare_activities_for_coach.py
```

Output: `data/processed/coach_input_{monday}.json`

---

### `fueling_analysis.py`

Analyzes carbohydrate fueling quality per activity and for the week. Classifies fueling based on duration (no fueling needed / optional / required), computes carbs/h and fueling ratio, detects underfueled sessions, and generates coaching recommendations.

```bash
python scripts/fueling_analysis.py
```

Output: console report + `data/processed/fueling_analysis_{monday}.json`

---

### `prepare_week_for_coach.py`

Runs all scripts in the correct order:
`get_activities.py` → `get_metrics.py` → `prepare_activities_for_coach.py` → `fueling_analysis.py` → `analyze_week.py`

Aborts immediately if any script fails.

```bash
python scripts/prepare_week_for_coach.py
```

---

## Notebook

### `notebooks/week_summary.ipynb`

Interactive Jupyter notebook that loads the consolidated `coach_input_{monday}.json` and displays a structured overview of the current training week:

- **Athlete Metrics**: FTP, eFTP, VO2Max, W\', CTL/ATL, HRV, weight
- **Week Summary**: total load, time, ride count, session types (VO2 / Threshold / Endurance), aerobic decoupling
- **Activities Table**: per-ride details including power, RPE, zone distribution, decoupling, and carbohydrate data
- **Zone Distribution Chart**: bar charts per activity showing Z1+2 / Z3+4 / Z5+ split
- **Fueling Analysis**: per-ride fueling status, carbs/h, fueling ratio, and weekly recommendations

Run `prepare_week_for_coach.py` first to generate the input file, then open the notebook:

```bash
python scripts/prepare_week_for_coach.py
jupyter lab notebooks/week_summary.ipynb
```
