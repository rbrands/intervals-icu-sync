# Intervals.icu Tools

A Python project for fetching, analyzing, exporting cycling training data from and uploading plans to [intervals.icu](https://intervals.icu) API.

## Description

`intervals-icu-sync` provides a set of scripts to:

- Fetch raw activity and wellness data from intervals.icu
- Analyze training quality per week using Joe Friel principles
- Export simplified summaries for a coach or ChatGPT
- Evaluate carbohydrate fueling quality per session
- Track performance metrics (FTP, VO2Max, CTL/ATL, HRV)
- Upload planned rides

## Prerequisites

For the analysis to work properly, the following conditions should be met:

1. **Power meter data**: Activities should contain power data. Without it, zone distribution, normalized power, and training load calculations will be incomplete or unavailable.

2. **Direct sync or upload as activity source (not Strava)**: Activities must be synced directly from a device (e.g. Garmin Connect, Wahoo, Zwift) or uploaded manually — not via Strava. The intervals.icu API does not expose power and detailed metrics for Strava-sourced activities.

3. **Carbohydrate intake logged after each ride**: For fueling analysis to be meaningful, enter the amount of carbohydrates consumed (in grams) in intervals.icu after each session. This is the basis for the fueling ratio and coaching recommendations.

4. **RPE logged after each ride**: Enter your perceived exertion (RPE, scale 1–10) in intervals.icu after each session. It is used alongside training load and power data to assess session quality.

5. **Wellness tracker connected** *(recommended)*: Linking a device such as a Garmin watch provides automatic wellness data (resting HR, HRV, sleep) that enriches the metrics analysis.

6. **Body weight maintained in intervals.icu**: Keep your weight up to date in intervals.icu so that calculated metrics like VO2Max are accurate.

7. **Activity tags set in intervals.icu** *(recommended)*: Tag your completed activities in intervals.icu using the tag scheme described in the [Coaching Logic](#coaching-logic) section (e.g. `vo2max-high`, `lactate-treshold-moderate`). Tags take priority over automatic session classification and lead to more accurate coaching output.

8. **Training plan created in intervals.icu using the Target Generator** *(recommended)*: Create a training plan in intervals.icu via the **Target Generator** (Plans → Target Generator). This places PLAN events (mesocycle blocks, e.g. Base / Build / Peak) and TARGET events (weekly TSS targets) in your calendar. `get_training_plan.py` reads these events and adds the current phase name and weekly load target — as well as the following week's target — to the coach input. Without a plan the training plan section will be empty.

## Coaching Logic

This project uses a structured system prompt based on Joe Friel’s training principles.

The prompt translates training theory into decision rules that allow an LLM to:

- analyze training data
- identify performance limiters
- evaluate fueling
- recommend next training steps

The combination of:
- structured data (intervals.icu)
- domain-specific prompt
- LLM reasoning

creates a lightweight but powerful coaching system:

```md
You are an expert cycling coach following principles from Joe Friel ("The Cyclist’s Training Bible" and "Fast After 50").

Your task is to:
1. Analyze structured training data
2. Identify performance limiters
3. Make coaching decisions
4. Generate a structured training plan

---

## Athlete Context

- Age: provided in metrics
- Sex: provided in metrics
- Weight: provided in metrics
- Goal: Increase FTP and improve long-duration climbing performance
- Event: Long climbs (60–90 minutes, e.g. alpine climbs)
- Training focus: endurance, threshold, durability

---

## Input Data

You receive:

- Weekly training summary
- Individual activities:
  - duration
  - training load
  - power zones
  - interval structure
  - decoupling
  - RPE
  - carbohydrate usage and intake
  - tags (optional)

- Metrics:
  - FTP / eFTP
  - CTL / ATL
  - HRV / resting HR
  - VO2max
  - Age (CRITICAL for planning rules)
  - Sex
  - Weight

- Training plan (if available):
  - Current week: phase (e.g. Base, Build, Peak) and target load (TSS)
  - Next week: phase and target load (TSS)

---

## Training Tags (CRITICAL)

Format:
    "<domain>-<level>"

Domains:
- recovery
- vo2max
- lactate-treshold
- aerobic-treshold

Levels:
- low
- moderate
- high

---

## Tag Priority Rule

tags > interval detection > intervals.icu classification

---

## Tag Mapping

- vo2max-* → ride_type = "vo2"
- lactate-treshold-* → ride_type = "threshold"
- aerobic-treshold-*:
    - duration >= 2h → "long_ride"
    - else → "endurance"
- recovery → "recovery"

---

## Weekly Structure (Friel-based)

Each week should include:

- 1× VO2max session (MANDATORY, see Age Rule)
- 1× threshold session
- 1× long aerobic ride
- remaining sessions: endurance or recovery

---

## VO2Max Age Rule (CRITICAL)

For athletes aged **50 and above**, VO2max training is mandatory year-round.

Rules:

- Each week MUST include **exactly 1 VO2max session**
- Applies to ALL phases:
  - Base
  - Build
  - Peak
  - Transition

- If a VO2max session is already performed in an unstructured ride 
  (e.g. group ride with VO2 efforts), it counts and should NOT be duplicated

---

## VO2Max Intensity Scaling (based on fatigue)

Use form (CTL - ATL) to scale intensity:

- form_pct < -20% → high fatigue
  → vo2max-low
  → short intervals (30/15, 6–8×1 min)

- -20% ≤ form_pct ≤ -10%
  → vo2max-moderate
  → 2–3 min intervals (5×2 min)

- form_pct > -10%
  → vo2max-high
  → 3–5 min intervals (4×4 min, 5×3 min)

---

## Purpose of VO2Max (Age ≥ 50)

- Maintain aerobic capacity
- Slow age-related decline
- Support long-term health and performance

VO2max sessions are NOT optional.

---

## Fatigue / Form Calculation

form_absolute = CTL - ATL  
form_pct = (CTL - ATL) / CTL

Interpretation:

- > 0 → fresh
- -10% to 0 → transition
- -10% to -30% → optimal training zone
- < -30% → high fatigue (reduce load)

---

## Limiter Analysis

Identify primary limiter:

- VO2max
- threshold (FTP)
- aerobic durability (decoupling)
- fueling / energy availability

---

## Decoupling Interpretation

- <5% → very good
- 5–8% → moderate
- 8–10% → high drift
- >10% → significant limitation

Use ONLY for steady efforts.

---

## Fueling Rules

- <1.5h → no fueling required
- 1.5–2h → optional
- >2h → required

Targets:

- moderate rides → 60–80 g/h
- long rides → 80–90 g/h

---

## Fueling Interpretation

- High decoupling + low carbs → fueling issue
- Good carbs + low decoupling → good durability

---

## Coaching Logic

- optimal form + low fueling → increase carbs
- high fatigue + low fueling → reduce intensity + increase carbs
- optimal form + good fueling → proceed with key sessions
- fresh → increase load
- high fatigue + low HRV → reduce intensity

---

## Planning Rules

- respect fatigue (form)
- include required sessions
- do NOT increase load if fatigue is high
- prioritize limiter
- VO2max must always be included (Age Rule)

---

## Tag Usage in Planning

Each workout MUST include exactly one tag

---

## Output Format: Training Plan JSON

You MUST return ONLY a JSON object:

{
  "week": "YYYY-MM-DD",
  "workouts": [
    {
      "date": "YYYY-MM-DDTHH:MM:SS",
      "name": "string",
      "duration_minutes": number,
      "description": "string",
      "ride_type": "vo2 | threshold | long_ride | endurance | recovery",
      "tags": ["<domain>-<level>"],
      "fueling": {
        "carbs_per_hour": number,
        "total_carbs": number
      },
      "workout": {
        "steps": [
          {
            "duration": number,
            "power": number
          }
        ]
      }
    }
  ]
}

---

## Workout Modeling Rules (CRITICAL)

The structure of workouts must reflect the **type of session**:

### 1. Structured Workouts (e.g. indoor trainer, intervals)

Use **detailed step structure**:

- Include warmup, intervals, recovery, cooldown  
- Use multiple short steps to precisely model interval structure  
- Examples:
  - VO2max intervals
  - Threshold intervals
  - Over/Under sessions  

---

### 2. Outdoor Rides and Events (CRITICAL)

Use **simplified step structure**:

- Use **maximum 3–5 steps**
- Do NOT model every interval or terrain change
- Represent only:
  - main ride phase
  - key intensity blocks (if any)

Typical structure:

- Step 1: warmup / early ride  
- Step 2: main ride (Z2 / endurance or mixed terrain)  
- Step 3: key effort (e.g. climb, VO2max effort) — optional  
- Step 4: remaining ride / cooldown  

---

### 3. Key Principle

- Prefer **physiological accuracy over structural detail**  
- Avoid excessive fragmentation of steps  
- Too many short steps will break load calculation and visualization  

---

### 4. Event Ride Exception

For event rides with a key effort:

- Include exactly **one highlighted effort** (e.g. climb, race effort)  
- Do NOT model all climbs individually  
- The event itself replaces structured workouts (e.g. VO2max session)  

---

### 5. Decision Logic

- Indoor / structured session → **detailed modeling**
- Outdoor / group ride / event → **simplified modeling**
- Goal = precise interval execution → **detailed**
- Goal = realistic ride representation → **simplified**

---

## Constraints

- Output ONLY valid JSON
- No explanations outside JSON
- Tags must match workout structure
- Plan must be realistic for fatigue and goals
```

## Project Structure

```
intervals-icu-sync/
├── scripts/                        # Runnable entry-point scripts
│   ├── get_activities.py           # Fetch activities → data/raw/
│   ├── get_metrics.py              # Fetch athlete metrics → data/processed/
│   ├── get_training_plan.py        # Fetch active training plan → data/processed/
│   ├── analyze_week.py             # Analyze current calendar week (Joe Friel)
│   ├── prepare_activities_for_coach.py  # Export simplified JSON for coach/ChatGPT
│   ├── fueling_analysis.py         # Analyze carbohydrate fueling quality
│   ├── fueling_planner.py          # Generate carbohydrate targets per session
│   ├── upload_plan.py              # Upload JSON training plan to intervals.icu
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
│   ├── processed/                  # Derived JSON exports (git-ignored)
│   └── plans/                      # Training plan JSON files
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
# Edit .env and set API_KEY and ATHLETE_ID
```

- **API_KEY**: found in intervals.icu under **Profile → API**
- **ATHLETE_ID**: your athlete ID, visible in the intervals.icu URL (e.g. `https://intervals.icu/athlete/i12345/...` → `i12345`)

## Data Flow

```mermaid
flowchart TD
    API([intervals.icu API])

    API --> GA[get_activities.py]
    API --> GM[get_metrics.py]
    API --> PA[prepare_activities_for_coach.py]
    API --> FA[fueling_analysis.py]
    API --> AW[analyze_week.py]
    API --> FP[fueling_planner.py]

    GA --> RAW[(data/raw/\nactivities_date.json)]
    GM --> METRICS[(data/processed/\nmetrics_date.json)]
    PA --> COACH_A[(data/processed/\ncoach_input_monday.json)]
    FA --> FUELING[(data/processed/\nfueling_analysis_monday.json)]
    AW --> SUMMARY[(data/processed/\nweek_summary_monday.json)]
    FP --> FPLAN[(data/processed/\nfueling_plan_monday.json)]

    RAW & METRICS & COACH_A & FUELING & SUMMARY & FPLAN --> PW[prepare_week_for_coach.py]
    PW --> CONSOLIDATED[(data/processed/\ncoach_input_monday.json\nconsolidated)]

    CONSOLIDATED --> COACH[[Coach\nChatGPT / Claude]]
    COACH --> PLAN[(data/plans/\nweek_plan.json)]
    PLAN --> UP[upload_plan.py]
    UP --> CAL([intervals.icu\ncalendar])
```

`prepare_week_for_coach.py` runs all scripts above in order and then consolidates the results (metrics, week summary, activities, fueling analysis) into a single `coach_input_{monday}.json`.

That means: Run
```
python ./scripts/prepare_week_for_coach.py
```
to get the current version of 
```
data/processed/coach_input_{monday}.json
``` 
for the week. Share this file with your "coach" (ChatGPT, Claude etc ...) and discuss the outcome and the plan for the week.

Ask your "coach" to create a plan for the week as JSON file. The format of the JSON is described in the system prompt above. Copy this JSON into `data/plan/week_plan.json` and run 
```
python ./scripts/upload_plan.py
```
to upload the plan to intervals.icu

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

Also computes **Form %** based on CTL (fitness) and ATL (fatigue):

- `form_absolute = CTL − ATL`
- `form_pct = (CTL − ATL) / CTL` — relative to current fitness level
- Form zones: `fresh` (> 0%) · `transition` (0 to −10%) · `optimal` (−10 to −30%) · `high_risk` (< −30%)
- Coaching recommendations adapt based on form zone (combined with HRV if available)

```bash
python scripts/analyze_week.py
```

Output: console + `data/processed/week_summary_{monday}.json`

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

### `fueling_planner.py`

Generates per-session carbohydrate intake targets based on ride type, duration, and current fatigue (Form %).
Reads from `coach_input_{monday}.json` (specifically the `fueling_analysis.activities` list, which already carries `ride_type`).

Target ranges by ride type:

| Ride Type | Target (g/h) |
|---|---|
| Long Ride | 80–90 |
| Threshold | 50–70 |
| VO2max | 40–60 |
| Endurance ≥ 2 h | 60–80 |
| Endurance < 2 h | 30–50 |
| Recovery | 0–30 |

When Form % < −20% (high fatigue), targets are raised by **+10 g/h** to offset elevated carbohydrate demand.

For each session the plan includes target g/h, total grams, and a practical strategy (gels, bottles, solid food).

```bash
python scripts/fueling_planner.py
```

Output: console plan + `data/processed/fueling_plan_{monday}.json`

---

### `prepare_week_for_coach.py`

Runs all scripts in the correct order:
`get_activities.py` → `get_metrics.py` → `prepare_activities_for_coach.py` → `fueling_analysis.py` → `analyze_week.py`

Aborts immediately if any script fails.

```bash
python scripts/prepare_week_for_coach.py
```

---

### `get_training_plan.py`

Fetches the athlete's currently active training plan from intervals.icu (if one is assigned). Prints a short summary (plan name, start date, duration, number of workouts) and saves the raw API response.

```bash
python scripts/get_training_plan.py
```

Output: `data/processed/training_plan_{date}.json`

---

### `upload_plan.py`

Uploads a JSON training plan to intervals.icu as planned WORKOUT events.

Reads from `data/plans/week_plan.json` by default (or any path passed via `--plan`). The plan file is git-ignored; the `data/plans/` folder is tracked via a `.gitkeep` file.

Each entry in the JSON file must have:
- `date` — ISO 8601 datetime string, e.g. `"2026-04-12T09:00:00"`
- `name` — display name shown in intervals.icu
- `duration_minutes` — planned duration (integer or float)

Optional per entry: `description` (free-text notes), `tags` (list of tag strings, e.g. `["vo2max-moderate"]`), `steps` (structured workout intervals → uploaded as a ZWO file).

Duplicate handling: before creating events, the script fetches existing WORKOUT events for the date range and indexes them by `(name, date)`. If a match is found the existing event is updated (`PUT`); otherwise a new event is created (`POST`). Re-running the script is safe and will never produce duplicates.

```bash
# Preview without making API calls
python scripts/upload_plan.py --dry-run

# Upload the default plan
python scripts/upload_plan.py

# Upload a custom plan file
python scripts/upload_plan.py --plan data/plans/my_plan.json

# Delete all WORKOUT events for the date range, then re-upload
python scripts/upload_plan.py --clear
```

Output: one `Created` or `Updated` line per workout, summary of counts.

---

## Notebook

### `notebooks/week_summary.ipynb`

Interactive Jupyter notebook that loads the consolidated `coach_input_{monday}.json` and displays a structured overview of the current training week:

- **Athlete Metrics**: FTP, eFTP, VO2Max, W\', CTL/ATL, HRV, weight — FTP values shown in W and W/kg
- **Week Summary**: total load, time, ride count, session types (VO2 / Threshold / Endurance), aerobic decoupling
- **Form & Fatigue Analysis**: CTL, ATL, Form (absolute and % relative to fitness), Form Zone, HRV — with coaching interpretation based on form zone
- **Activities Table**: per-ride details including power, RPE, zone distribution, decoupling, and carbohydrate data
- **Zone Distribution Chart**: bar charts per activity showing Z1+2 / Z3+4 / Z5+ split
- **Integrated Fatigue & Fueling Analysis**: combines Form % and weekly fueling quality into a single coaching interpretation with recommendation
- **Fueling Analysis**: per-ride fueling status, carbs/h, fueling ratio, and weekly recommendations

Run `prepare_week_for_coach.py` first to generate the input file, then open the notebook:

```bash
python scripts/prepare_week_for_coach.py
jupyter lab notebooks/week_summary.ipynb
```
