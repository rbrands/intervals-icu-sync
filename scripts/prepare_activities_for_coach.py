"""Read latest activities JSON from data/raw and output a simplified JSON for coach analysis."""

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


def load_data() -> list:
    json_files = sorted(DATA_DIR.glob("*.json"))
    if not json_files:
        print("Error: No JSON files found in data/raw/.")
        sys.exit(1)
    latest = json_files[-1]
    print(f"Loading {latest.name}")
    return json.loads(latest.read_text())


def filter_activities(activities: list) -> list:
    return [
        a for a in activities
        if a.get("type") == "Ride"
        and a.get("source") != "STRAVA"
        and a.get("icu_training_load", 0) > 30
    ]


def _zone_distribution(zone_times: list) -> dict:
    """Compute Z1+2 / Z3+4 / Z5+ percentage breakdown from icu_zone_times."""
    if not zone_times:
        return {"z1_z2_pct": None, "z3_z4_pct": None, "z5_plus_pct": None}
    secs_by_id = {z["id"]: z["secs"] for z in zone_times if "id" in z and "secs" in z}
    total = sum(secs_by_id.values())
    if total == 0:
        return {"z1_z2_pct": None, "z3_z4_pct": None, "z5_plus_pct": None}
    z1_z2 = secs_by_id.get("Z1", 0) + secs_by_id.get("Z2", 0)
    z3_z4 = secs_by_id.get("Z3", 0) + secs_by_id.get("Z4", 0)
    z5_plus = sum(v for k, v in secs_by_id.items() if k in ("Z5", "Z6", "Z7"))
    return {
        "z1_z2_pct": round(z1_z2 / total * 100, 1),
        "z3_z4_pct": round(z3_z4 / total * 100, 1),
        "z5_plus_pct": round(z5_plus / total * 100, 1),
    }


def extract_fields(activity: dict) -> dict:
    zone_dist = _zone_distribution(activity.get("icu_zone_times") or [])
    return {
        "date": (activity.get("start_date_local") or "")[:10],
        "name": activity.get("name"),
        "duration_hours": round((activity.get("moving_time") or 0) / 3600, 2),
        "training_load": activity.get("icu_training_load"),
        "avg_power": activity.get("icu_average_watts"),
        "norm_power": activity.get("icu_weighted_avg_watts"),
        "polarization_index": activity.get("polarization_index"),
        "z1_z2_pct": zone_dist["z1_z2_pct"],
        "z3_z4_pct": zone_dist["z3_z4_pct"],
        "z5_plus_pct": zone_dist["z5_plus_pct"],
        "interval_summary": activity.get("interval_summary"),
        "decoupling": activity.get("decoupling"),
        "rpe": activity.get("icu_rpe"),
        "carbs_used_g": activity.get("carbs_used"),
        "carbs_ingested_g": activity.get("carbs_ingested"),
    }


def main() -> None:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    output_file = OUTPUT_DIR / f"coach_input_{monday.isoformat()}.json"
    activities = load_data()
    rides = filter_activities(activities)
    rides.sort(key=lambda a: (a.get("start_date_local") or ""))
    output = [extract_fields(a) for a in rides]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(output, indent=2))

    total_load = sum(a["training_load"] or 0 for a in output)
    print(f"Rides:       {len(output)}")
    print(f"Total load:  {total_load}")
    print(f"Saved to:    {output_file}")

    analyze_script = Path(__file__).resolve().parent / "analyze_week.py"
    result = subprocess.run([sys.executable, str(analyze_script)], check=False)
    if result.returncode != 0:
        print(f"Warning: analyze_week.py exited with code {result.returncode}.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
