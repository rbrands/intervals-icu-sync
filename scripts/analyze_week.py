"""Analyze the latest week of cycling training data from data/raw/."""

import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

_DEFAULT_RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
_DEFAULT_PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
DATA_DIR = Path(os.environ.get("INTERVALS_RAW_DIR", str(_DEFAULT_RAW_DIR)))
OUTPUT_DIR = Path(os.environ.get("INTERVALS_PROCESSED_DIR", str(_DEFAULT_PROCESSED_DIR)))
METRICS_DIR = OUTPUT_DIR


def load_data() -> list:
    json_files = sorted(DATA_DIR.glob("*.json"))
    if not json_files:
        print("Error: No JSON files found in data/raw/.")
        sys.exit(1)
    latest = json_files[-1]
    print(f"Loading {latest.name}")
    return json.loads(latest.read_text())


def load_metrics() -> dict:
    files = sorted(METRICS_DIR.glob("metrics_*.json"))
    if not files:
        return {}
    return json.loads(files[-1].read_text())


def _copy_target_fields(entry: dict, target: dict) -> None:
    load_target = target.get("load_target")
    time_target_hours = target.get("time_target_hours")
    if load_target is not None:
        entry["weekly_load_target"] = load_target
    if time_target_hours is not None:
        entry["weekly_time_target_hours"] = time_target_hours


def _format_weekly_target(entry: dict | None) -> str | None:
    if not isinstance(entry, dict):
        return None
    load_target = entry.get("weekly_load_target")
    time_target_hours = entry.get("weekly_time_target_hours")
    if load_target is not None:
        if time_target_hours is not None:
            return f"{load_target} TSS, capped at {time_target_hours:.1f} h"
        return f"{load_target} TSS"
    if time_target_hours is not None:
        return f"{time_target_hours:.1f} h"
    return None


def load_training_plan(today: date) -> list[dict] | None:
    path = OUTPUT_DIR / f"training_plan_{today.isoformat()}.json"
    if not path.exists():
        # Fall back to most recent file
        files = sorted(OUTPUT_DIR.glob("training_plan_*.json"))
        if not files:
            return None
        path = files[-1]
    raw = json.loads(path.read_text())
    phases = [p for p in (raw.get("active_phases") or []) if p.get("sport_type") == "Ride"]
    monday = today - timedelta(days=today.weekday())

    next_week_phases = [p for p in (raw.get("next_week_active_phases") or []) if p.get("sport_type") == "Ride"]

    def _build_entry(targets_key: str, week_monday: date, phase_list: list) -> dict | None:
        targets = [t for t in (raw.get(targets_key) or []) if t.get("sport_type") == "Ride"]
        if not phase_list and not targets:
            return None
        entry: dict = {"week": week_monday.isoformat()}
        if phase_list:
            p = phase_list[0]
            entry["plan_name"] = p.get("plan_name")
            entry["phase"] = p.get("phase")
            entry["phase_start"] = p.get("start")
            entry["phase_end"] = p.get("end")
        if targets:
            t = targets[0]
            _copy_target_fields(entry, t)
            entry["week_type"] = t.get("week_type", "NORMAL")
            entry["training_availability"] = t.get("training_availability", "NORMAL")
            if t.get("week_note"):
                entry["week_note"] = t["week_note"]
        return entry

    result: list[dict] = []
    current = _build_entry("weekly_load_targets", monday, phases)
    if current:
        result.append(current)
    next_week = _build_entry("next_week_load_targets", monday + timedelta(weeks=1), next_week_phases)
    if next_week:
        result.append(next_week)
    return result or None


def load_fueling(monday: date) -> dict:
    path = OUTPUT_DIR / f"fueling_analysis_{monday.isoformat()}.json"
    if not path.exists():
        # Fall back to most recent file
        files = sorted(OUTPUT_DIR.glob("fueling_analysis_*.json"))
        if not files:
            return {}
        path = files[-1]
    return json.loads(path.read_text())


def _current_week_range() -> tuple[date, date]:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _as_float(value: object, default: float = 0.0) -> float:
    """Convert API values to float safely (None/invalid -> default)."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


_METRIC_FIELDS = (
    "icu_training_load",
    "icu_average_watts",
    "icu_weighted_avg_watts",
    "average_watts",
    "average_heartrate",
    "avg_hr",
)

_SUPPORTED_ACTIVITY_TYPES = {
    "Ride",
    "VirtualRide",
    "MountainBikeRide",
    "GravelRide",
    "Run",
    "TrailRun",
    "VirtualRun",
}

_RUN_ACTIVITY_TYPES = {"Run", "TrailRun", "VirtualRun"}


def _has_training_load(activity: dict) -> bool:
    """True when intervals.icu supplied a training load value."""
    return activity.get("icu_training_load") is not None


def _passes_load_filter(activity: dict) -> bool:
    """Return True when an activity should be kept by load/metric rules."""
    if activity.get("type") in _RUN_ACTIVITY_TYPES and _has_training_load(activity):
        return True
    return (
        _as_float(activity.get("icu_training_load")) > 20
        or (bool(activity.get("tags")) and _has_usable_metrics(activity))
    )


def _has_usable_metrics(activity: dict) -> bool:
    """True when an activity carries at least one analyzable metric."""
    if any(activity.get(field) is not None for field in _METRIC_FIELDS):
        return True
    return bool(activity.get("icu_zone_times") or activity.get("icu_hr_zone_times"))


def _activity_zone_times(activity: dict) -> list:
    """Return power/primary zone times, falling back to HR zone times."""
    zone_times = activity.get("icu_zone_times")
    if zone_times:
        return zone_times
    hr_zone_times = activity.get("icu_hr_zone_times") or []
    if not isinstance(hr_zone_times, list):
        return []
    return [
        {"id": f"Z{idx}", "secs": secs}
        for idx, secs in enumerate(hr_zone_times, start=1)
    ]


def filter_activities(activities: list) -> list:
    monday, sunday = _current_week_range()
    result = []
    for a in activities:
        if (
            a.get("type") in _SUPPORTED_ACTIVITY_TYPES
            and a.get("source") != "STRAVA"
            and _passes_load_filter(a)
        ):
            start = (a.get("start_date_local") or "")[:10]
            try:
                activity_date = date.fromisoformat(start)
            except ValueError:
                continue
            if monday <= activity_date <= sunday:
                result.append(a)
    return result


def _z5_plus_pct(activity: dict) -> float:
    zone_times = _activity_zone_times(activity)
    secs_by_id = {
        z["id"]: _as_float(z.get("secs"))
        for z in zone_times
        if isinstance(z, dict) and "id" in z
    }
    total = sum(secs_by_id.values())
    if total == 0:
        return 0.0
    z5_plus = sum(v for k, v in secs_by_id.items() if k in ("Z5", "Z6", "Z7"))
    return z5_plus / total * 100


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


def _get_zone_distribution(activity: dict) -> dict:
    """Compute Z1+2 / Z3+4 / Z5+ percentage breakdown from activity zone times."""
    zone_times = _activity_zone_times(activity)
    if not zone_times:
        return {"z1_z2_pct": None, "z3_z4_pct": None, "z5_plus_pct": None}
    secs_by_id = {
        z["id"]: _as_float(z.get("secs"))
        for z in zone_times
        if isinstance(z, dict) and "id" in z
    }
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


def _classify_ride(activity: dict) -> str:
    raw = activity.get("interval_summary") or ""
    summary = " ".join(raw) if isinstance(raw, list) else raw
    tags = [t.lower().replace("treshold", "threshold") for t in (activity.get("tags") or [])]
    z5_plus = _z5_plus_pct(activity)
    # Tag-based override (takes priority over heuristics)
    if any(t.startswith("vo2") for t in tags):
        return "vo2max"
    if any(t.startswith("lactate-threshold") or t.startswith("lactate_threshold") for t in tags):
        return "threshold"
    # Interval-summary heuristics
    if (re.search(r"\b(1m|2m|3m|4m)", summary) or "110%" in summary) and z5_plus > 5:
        return "vo2max"
    if re.search(r"\b([89]m|[1-9][0-9]m)", summary):
        return "threshold"
    duration_h = (activity.get("moving_time") or 0) / 3600
    if duration_h >= 2.5:
        return "long_ride"
    return "endurance"


def analyse_fueling_form(form_pct: float, fueling_data: dict, activities: list, training_plan: list[dict] | None = None) -> dict:
    """Combine Form % with fueling quality into an integrated assessment."""
    weekly = fueling_data.get("weekly_summary", {})
    avg_carbs_per_hour = weekly.get("avg_carbs_per_hour") or 0.0
    underfueled_sessions = weekly.get("number_of_underfueled_sessions") or 0
    number_of_long_rides = weekly.get("number_of_long_rides") or 0
    avg_fueling_ratio = weekly.get("avg_fueling_ratio") or 0.0

    # Fueling quality
    if avg_carbs_per_hour >= 70:
        fueling_status = "good"
    elif avg_carbs_per_hour >= 50:
        fueling_status = "moderate"
    else:
        fueling_status = "low"

    # Durability limited by fueling
    fuel_acts = fueling_data.get("activities", [])
    fuel_by_name = {a.get("name"): a for a in fuel_acts}
    durability_limited = False
    for act in activities:
        decoupling = act.get("decoupling")
        name = act.get("name")
        fa = fuel_by_name.get(name, {})
        carbs_h = fa.get("carbs_per_hour") or 0.0
        if decoupling is not None and float(decoupling) >= 8 and carbs_h < 60:
            durability_limited = True
            break

    # Fatigue status derived from form_pct
    if form_pct < -0.30:
        fatigue_status = "high"
    elif form_pct < -0.10:
        fatigue_status = "optimal"
    else:
        fatigue_status = "low"

    # Interpretation
    if fatigue_status == "optimal" and fueling_status == "low":
        interpretation = "Fatigue is amplified by insufficient fueling"
        recommendation = "Do not increase intensity — improve fueling first"
    elif fatigue_status == "optimal" and fueling_status in ("moderate", "good"):
        interpretation = "Fatigue is appropriate and productive"
        recommendation = "Continue with planned VO2 and threshold sessions"
    elif fatigue_status == "high" and fueling_status == "low":
        interpretation = "High risk: excessive fatigue + underfueling"
        recommendation = "Reduce intensity AND increase fueling immediately"
    elif fatigue_status == "high" and fueling_status in ("moderate", "good"):
        interpretation = "High training load, but fueling is adequate"
        recommendation = "Prioritize recovery; no additional hard sessions"
    elif fatigue_status == "low" and fueling_status == "low":
        interpretation = "Low load but also underfueled (suboptimal adaptation)"
        recommendation = "Increase fueling even on lower-intensity days"
    else:
        interpretation = "Balanced state"
        recommendation = "Consider increasing training load"

    # Override for Recovery Week
    current_week = (training_plan or [{}])[0]
    week_type = current_week.get("week_type", "NORMAL")
    target_label = _format_weekly_target(current_week)
    if week_type == "RECOVERY":
        interpretation = "Recovery week — reduced load is intentional"
        recommendation = (
            f"Stick to the recovery week plan (target: {target_label}). "
            "Avoid adding load; focus on regeneration."
            if target_label
            else "Stick to the recovery week plan. Avoid adding load; focus on regeneration."
        )
    long_ride_advice: str | None = None
    if number_of_long_rides == 0:
        long_ride_advice = "Add a long aerobic ride this week"
    elif durability_limited:
        long_ride_advice = "Focus on fueling during long rides (80–90 g/h)"

    return {
        "fatigue_status": fatigue_status,
        "fueling_status": fueling_status,
        "avg_carbs_per_hour": round(avg_carbs_per_hour, 1),
        "avg_fueling_ratio": round(avg_fueling_ratio, 2),
        "underfueled_sessions": underfueled_sessions,
        "number_of_long_rides": number_of_long_rides,
        "durability_limited_by_fueling": durability_limited,
        "interpretation": interpretation,
        "recommendation": recommendation,
        "long_ride_advice": long_ride_advice,
    }


def compute_form(ctl: float | None, atl: float | None) -> dict:
    ctl = ctl or 0.0
    atl = atl or 0.0
    form_absolute = ctl - atl
    form_pct = (ctl - atl) / ctl if ctl > 0 else 0.0

    # Zones based on form_pct (%), matching intervals.icu definition
    if form_pct > 0.20:
        form_zone = "transition"
    elif form_pct >= 0.05:
        form_zone = "fresh"
    elif form_pct >= -0.10:
        form_zone = "grey_zone"
    elif form_pct >= -0.30:
        form_zone = "optimal"
    else:
        form_zone = "high_risk"

    return {
        "ctl": round(ctl, 1),
        "atl": round(atl, 1),
        "form_absolute": round(form_absolute, 1),
        "form_pct": round(form_pct, 4),
        "form_percent_display": round(form_pct * 100, 1),
        "form_zone": form_zone,
    }


def _infer_distribution_label(activity: dict) -> str | None:
    """Infer ride distribution from raw `icu_zone_times` when no explicit label is present."""
    distribution = activity.get("training_distribution")
    if distribution:
        return str(distribution)

    zone_dist = _get_zone_distribution(activity)
    z1_z2_pct = zone_dist.get("z1_z2_pct")
    z3_z4_pct = zone_dist.get("z3_z4_pct")
    z5_plus_pct = zone_dist.get("z5_plus_pct")
    if z1_z2_pct is None or z3_z4_pct is None or z5_plus_pct is None:
        return None

    if z5_plus_pct >= 20:
        return "HIIT"
    if z1_z2_pct >= 70 and z5_plus_pct >= 10:
        return "Polarized"
    if z3_z4_pct >= 20:
        return "Threshold"
    if z1_z2_pct >= 70 and z3_z4_pct >= 10 and z5_plus_pct < 10:
        return "Pyramidal"
    if z1_z2_pct >= 85 and z3_z4_pct < 10 and z5_plus_pct < 5:
        return "Base"
    return "Unique"


def compute_days_since_last_distribution(activities: list, labels: list[str], as_of: date) -> int | None:
    """Return the number of calendar days since the latest matching ride distribution."""
    if not activities:
        return None

    label_set = {str(label).strip() for label in labels if str(label).strip()}
    if not label_set:
        return None

    for activity in sorted(
        activities,
        key=lambda a: (a.get("start_date_local") or a.get("date") or ""),
        reverse=True,
    ):
        distribution = _infer_distribution_label(activity)
        if distribution in label_set:
            start_value = activity.get("start_date_local") or activity.get("date")
            if not isinstance(start_value, str):
                continue
            try:
                activity_date = date.fromisoformat(start_value[:10])
            except ValueError:
                continue
            return (as_of - activity_date).days
    return None


def compute_metrics(activities: list) -> dict:
    total_load = sum(_as_float(a.get("icu_training_load")) for a in activities)
    times = [_as_float(a.get("moving_time")) / 3600 for a in activities]
    total_time = sum(times)
    longest = max(times, default=0.0)

    vo2_sessions = 0
    threshold_sessions = 0
    endurance_sessions = 0
    for a in activities:
        category = _classify_ride(a)
        if category == "vo2max":
            vo2_sessions += 1
        elif category == "threshold":
            threshold_sessions += 1
        else:
            endurance_sessions += 1

    decouplings = [
        float(a["decoupling"])
        for a in activities
        if a.get("decoupling") is not None and (_get_zone_distribution(a).get("z1_z2_pct") or 0) >= 80
    ]
    avg_decoupling = sum(decouplings) / len(decouplings) if decouplings else 0.0
    avg_decoupling_label = _classify_decoupling(avg_decoupling) if decouplings else "no durability data"
    high_decoupling = sum(1 for d in decouplings if d >= 8)

    return {
        "total_training_load": total_load,
        "number_of_rides": len(activities),
        "total_time_hours": total_time,
        "longest_ride_hours": longest,
        "vo2_sessions": vo2_sessions,
        "threshold_sessions": threshold_sessions,
        "endurance_sessions": endurance_sessions,
        "avg_decoupling": avg_decoupling,
        "avg_decoupling_label": avg_decoupling_label,
        "high_decoupling_rides": high_decoupling,
        "days_since_last_hiit": compute_days_since_last_distribution(activities, ["HIIT"], date.today()),
        "days_since_last_polarized": compute_days_since_last_distribution(activities, ["HIIT", "Polarized"], date.today()),
        "days_since_last_hard_session": compute_days_since_last_distribution(
            activities,
            ["HIIT", "Polarized", "Threshold"],
            date.today(),
        ),
    }


def print_report(metrics: dict, athlete_metrics: dict | None = None, fueling_form: dict | None = None, training_plan: list[dict] | None = None) -> None:
    m = metrics
    if training_plan:
        current = training_plan[0]
        plan_name = current.get("plan_name") or "Training Plan"
        phase = current.get("phase")
        phase_str = f"#{phase}" if phase else "(no phase)"
        target_str = _format_weekly_target(current) or "(none)"
        next_str = ""
        if len(training_plan) > 1:
            next_target = _format_weekly_target(training_plan[1])
            if next_target is not None:
                next_str = f"  |  Next week: {next_target}"
        print(f"Plan:                {plan_name}  |  Phase: {phase_str}  |  Weekly target: {target_str}{next_str}")
    print()
    print("=== Weekly Training Summary ===")
    print(f"Total Load:          {m['total_training_load']}")
    print(f"Number of Rides:     {m['number_of_rides']}")
    print(f"Total Time (h):      {m['total_time_hours']:.1f}")
    print(f"Longest Ride (h):    {m['longest_ride_hours']:.1f}")
    print()
    print("Distribution:")
    print(f"  VO2max sessions:     {m['vo2_sessions']}")
    print(f"  Threshold sessions:  {m['threshold_sessions']}")
    print(f"  Endurance sessions:  {m['endurance_sessions']}")
    print()
    print("Decoupling:")
    print(f"  Average:                    {m['avg_decoupling']:.1f}% ({m['avg_decoupling_label']})")
    print(f"  Rides with high drift or worse (>=8%): {m['high_decoupling_rides']}")

    if "form_absolute" in m:
        _zone_labels = {
            "high_risk":  "High Risk    (< -30%)",
            "optimal":    "Optimal      (-30% to -10%)",
            "grey_zone":  "Grey Zone    (-10% to +5%)",
            "fresh":      "Fresh        (+5% to +20%)",
            "transition": "Transition   (> +20%)",
        }
        zone_label = _zone_labels.get(m["form_zone"], m["form_zone"])
        print()
        print("=== Fatigue / Form Analysis ===")
        print(f"CTL:     {athlete_metrics.get('ctl', 'n/a')}")
        print(f"ATL:     {athlete_metrics.get('atl', 'n/a')}")
        print(f"Form:    {m['form_absolute']}")
        print(f"Form %:  {m['form_percent_display']:.1f}%")
        print(f"Zone:    {zone_label}")

    print()
    print("=== Coaching Interpretation ===")

    load = m["total_training_load"]
    if load < 250:
        print("Load:       Low load week")
    elif load <= 450:
        print("Load:       Moderate load week")
    else:
        print("Load:       High load week")

    if m["vo2_sessions"] == 0:
        print("Intensity:  Missing high intensity work")
    if m["threshold_sessions"] == 0:
        print("Intensity:  Missing threshold work")
    if m["endurance_sessions"] == 0:
        print("Volume:     Missing endurance volume")

    if m["avg_decoupling"] > 8:
        print("Aerobic:    Aerobic endurance or fueling needs improvement")

    if "form_pct" in m:
        form_pct = m["form_pct"]
        hrv = (athlete_metrics or {}).get("hrv")
        print()
        if form_pct < -0.30:
            print("Form:       High fatigue -> reduce intensity and prioritize recovery")
            if hrv is not None and hrv < 50:
                print("HRV:        Strong fatigue signal combined with low HRV -> recommend rest day")
        elif form_pct < -0.10:
            print("Form:       Optimal training zone -> proceed with key sessions")
            if m["vo2_sessions"] == 0 and m["threshold_sessions"] == 0:
                print("Form:       Consider adding a VO2 or threshold session")
        elif form_pct <= 0:
            print("Form:       Balanced state -> maintain structure")
        else:
            print("Form:       Fresh -> consider increasing load or intensity")
    if fueling_form:
        ff = fueling_form
        print()
        print("=== Integrated Fatigue & Fueling Analysis ===")
        print(f"Form %:          {m.get('form_percent_display', 'n/a'):.1f}%")
        print(f"Fatigue Status:  {ff['fatigue_status']}")
        print()
        print(f"Avg Carbs/h:     {ff['avg_carbs_per_hour']} g")
        print(f"Fueling Status:  {ff['fueling_status']}")
        print(f"Underfueled sessions: {ff['underfueled_sessions']}")
        print(f"Durability limited by fueling: {ff['durability_limited_by_fueling']}")
        print()
        print(f"Interpretation:  {ff['interpretation']}")
        print(f"Recommendation:  {ff['recommendation']}")
        if ff.get("long_ride_advice"):
            print(f"Long rides:      {ff['long_ride_advice']}")

def save_json(metrics: dict, fueling_form: dict | None, monday: date, training_plan: list[dict] | None = None) -> None:
    output_file = OUTPUT_DIR / f"week_summary_{monday.isoformat()}.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"week_starting": monday.isoformat(), "current_date": date.today().isoformat(), **metrics}
    if fueling_form:
        payload["fueling_form_analysis"] = fueling_form
    if training_plan:
        payload["training_plan"] = training_plan
    output_file.write_text(json.dumps(payload, indent=2))
    print(f"Saved to: {output_file.name}")


def main() -> None:
    monday, sunday = _current_week_range()
    print(f"Calendar week: {monday.isoformat()} – {sunday.isoformat()}")
    activities = load_data()
    rides = filter_activities(activities)
    training_plan = load_training_plan(date.today())
    if not rides:
        print("No qualifying rides found.")
        athlete_metrics = load_metrics()
        form = compute_form(athlete_metrics.get("ctl"), athlete_metrics.get("atl"))
        if training_plan:
            save_json(form, None, monday, training_plan)
        else:
            save_json(form, None, monday)
        sys.exit(0)
    athlete_metrics = load_metrics()
    fueling_data = load_fueling(monday)
    metrics = compute_metrics(rides)
    form = compute_form(athlete_metrics.get("ctl"), athlete_metrics.get("atl"))
    metrics.update(form)
    fueling_form = analyse_fueling_form(form["form_pct"], fueling_data, rides, training_plan) if fueling_data else None
    print_report(metrics, athlete_metrics, fueling_form, training_plan)
    save_json(metrics, fueling_form, monday, training_plan)


if __name__ == "__main__":
    main()
