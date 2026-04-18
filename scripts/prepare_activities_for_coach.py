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
        if a.get("type") in ("Ride", "VirtualRide")
        and a.get("source") != "STRAVA"
        and a.get("icu_training_load", 0) > 20
    ]


def _classify_decoupling(value: float) -> str:
    if value < 3:
        return "excellent durability"
    if value < 5:
        return "very good"
    if value < 8:
        return "moderate drift"
    if value <= 10:
        return "high drift"
    return "significant limitation"


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


def classify_ride(
    z1_z2_pct: float | None,
    z3_z4_pct: float | None,
    z5_plus_pct: float | None,
) -> dict | None:
    """Classify a ride by time-in-zone distribution (Seiler/Laursen model).

    Rules are evaluated in strict priority order; the first match wins.
    Returns a dict with 'label' and 'reason', or None if any input is None.

    Priority order: HIIT → Polarized → Threshold → Pyramidal → Base → Unique

    Examples:
        classify_ride(92, 5, 1)   -> {"label": "Base",      "reason": ...}
        classify_ride(75, 10, 12) -> {"label": "Polarized", "reason": ...}
        classify_ride(65, 30, 3)  -> {"label": "Threshold", "reason": ...}
        classify_ride(50, 20, 25) -> {"label": "HIIT",      "reason": ...}
        classify_ride(72, 20, 5)  -> {"label": "Pyramidal", "reason": ...}
        classify_ride(60, 20, 8)  -> {"label": "Unique",    "reason": ...}
    """
    if z1_z2_pct is None or z3_z4_pct is None or z5_plus_pct is None:
        return None

    # 1. HIIT: dominant high-intensity work regardless of low-zone share
    if z5_plus_pct >= 20:
        return {"label": "HIIT", "reason": f"Z5+ {z5_plus_pct}% >= 20%"}

    # 2. Polarized: mostly easy + significant high-intensity, little middle
    if z1_z2_pct >= 70 and z5_plus_pct >= 10:
        return {"label": "Polarized", "reason": f"Z1+2 {z1_z2_pct}% >= 70% and Z5+ {z5_plus_pct}% >= 10%"}

    # 3. Threshold: heavy middle-zone load
    if z3_z4_pct >= 25:
        return {"label": "Threshold", "reason": f"Z3+4 {z3_z4_pct}% >= 25%"}

    # 4. Pyramidal: mostly easy with moderate middle zone, low Z5+
    if z1_z2_pct >= 70 and z3_z4_pct >= 10 and z5_plus_pct < 10:
        return {"label": "Pyramidal", "reason": f"Z1+2 {z1_z2_pct}% >= 70%, Z3+4 {z3_z4_pct}% >= 10%, Z5+ {z5_plus_pct}% < 10%"}

    # 5. Base: almost entirely low-intensity recovery/aerobic
    if z1_z2_pct >= 85 and z3_z4_pct < 10 and z5_plus_pct < 5:
        return {"label": "Base", "reason": f"Z1+2 {z1_z2_pct}% >= 85%, Z3+4 {z3_z4_pct}% < 10%, Z5+ {z5_plus_pct}% < 5%"}

    # 6. Unique: distribution doesn't fit any known pattern
    return {"label": "Unique", "reason": f"No pattern matched (Z1+2={z1_z2_pct}%, Z3+4={z3_z4_pct}%, Z5+={z5_plus_pct}%)"}


def extract_fields(activity: dict) -> dict:
    zone_dist = _zone_distribution(activity.get("icu_zone_times") or [])
    ride_class = classify_ride(
        zone_dist["z1_z2_pct"], zone_dist["z3_z4_pct"], zone_dist["z5_plus_pct"]
    )
    return {
        "date": (activity.get("start_date_local") or "")[:10],
        "name": activity.get("name"),
        "duration_hours": round((activity.get("moving_time") or 0) / 3600, 2),
        "training_load": activity.get("icu_training_load"),
        "avg_power": activity.get("icu_average_watts"),
        "norm_power": activity.get("icu_weighted_avg_watts"),
        "polarization_index": activity.get("polarization_index"),
        "training_distribution": ride_class["label"] if ride_class else None,
        "training_distribution_reason": ride_class["reason"] if ride_class else None,
        "z1_z2_pct": zone_dist["z1_z2_pct"],
        "z3_z4_pct": zone_dist["z3_z4_pct"],
        "z5_plus_pct": zone_dist["z5_plus_pct"],
        "interval_summary": activity.get("interval_summary"),
        "decoupling": activity.get("decoupling"),
        "decoupling_label": _classify_decoupling(float(activity["decoupling"])) if activity.get("decoupling") is not None else None,
        "rpe": activity.get("icu_rpe"),
        "carbs_used_g": activity.get("carbs_used"),
        "carbs_ingested_g": activity.get("carbs_ingested"),
        "tags": activity.get("tags") or [],
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
