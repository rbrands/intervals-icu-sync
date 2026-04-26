"""Analyze the latest week of cycling training data from data/raw/."""

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
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
            entry["weekly_load_target"] = t.get("load_target")
            entry["week_type"] = t.get("week_type", "NORMAL")
            entry["training_availability"] = t.get("training_availability", "NORMAL")
            if t.get("week_note"):
                entry["week_note"] = t["week_note"]
        return entry

    result: list[dict] = []
    current = _build_entry("weekly_load_targets", monday, phases)
    if current:
        result.append(current)
    next_week = _build_entry("next_week_load_targets", monday + timedelta(weeks=1), next_week_phases or phases)
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


def filter_activities(activities: list) -> list:
    monday, sunday = _current_week_range()
    result = []
    for a in activities:
        if (
            a.get("type") in ("Ride", "VirtualRide")
            and a.get("source") != "STRAVA"
            and (a.get("icu_training_load", 0) > 20 or bool(a.get("tags")))
        ):
            start = a.get("start_date_local", "")[:10]
            try:
                activity_date = date.fromisoformat(start)
            except ValueError:
                continue
            if monday <= activity_date <= sunday:
                result.append(a)
    return result


def _z5_plus_pct(activity: dict) -> float:
    zone_times = activity.get("icu_zone_times") or []
    secs_by_id = {z["id"]: z["secs"] for z in zone_times if "id" in z and "secs" in z}
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


def _classify_ride(activity: dict) -> str:
    raw = activity.get("interval_summary") or ""
    summary = " ".join(raw) if isinstance(raw, list) else raw
    z5_plus = _z5_plus_pct(activity)
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
    load_target = current_week.get("weekly_load_target")
    if week_type == "RECOVERY":
        interpretation = "Recovery week — reduced load is intentional"
        recommendation = (
            f"Stick to the recovery week plan (target: {load_target} TSS). "
            "Avoid adding load; focus on regeneration."
            if load_target
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
        "form_absolute": round(form_absolute, 1),
        "form_pct": round(form_pct, 4),
        "form_percent_display": round(form_pct * 100, 1),
        "form_zone": form_zone,
    }


def compute_metrics(activities: list) -> dict:
    total_load = sum(a.get("icu_training_load", 0) for a in activities)
    times = [a.get("moving_time", 0) / 3600 for a in activities]
    total_time = sum(times)
    longest = max(times, default=0.0)

    vo2_sessions = 0
    threshold_sessions = 0
    long_ride_sessions = 0
    endurance_sessions = 0
    for a in activities:
        category = _classify_ride(a)
        if category == "vo2max":
            vo2_sessions += 1
        elif category == "threshold":
            threshold_sessions += 1
        elif category == "long_ride":
            long_ride_sessions += 1
        else:
            endurance_sessions += 1

    decouplings = [
        float(a["decoupling"])
        for a in activities
        if a.get("decoupling") is not None
    ]
    avg_decoupling = sum(decouplings) / len(decouplings) if decouplings else 0.0
    high_decoupling = sum(1 for d in decouplings if d >= 8)

    return {
        "total_training_load": total_load,
        "number_of_rides": len(activities),
        "total_time_hours": total_time,
        "longest_ride_hours": longest,
        "vo2_sessions": vo2_sessions,
        "threshold_sessions": threshold_sessions,
        "long_ride_sessions": long_ride_sessions,
        "endurance_sessions": endurance_sessions,
        "avg_decoupling": avg_decoupling,
        "avg_decoupling_label": _classify_decoupling(avg_decoupling),
        "high_decoupling_rides": high_decoupling,
    }


def print_report(metrics: dict, athlete_metrics: dict | None = None, fueling_form: dict | None = None, training_plan: list[dict] | None = None) -> None:
    m = metrics
    if training_plan:
        current = training_plan[0]
        plan_name = current.get("plan_name") or "Training Plan"
        phase = current.get("phase")
        load_target = current.get("weekly_load_target")
        phase_str = f"#{phase}" if phase else "(no phase)"
        target_str = f"{load_target} TSS" if load_target is not None else "(none)"
        next_str = ""
        if len(training_plan) > 1:
            next_load = training_plan[1].get("weekly_load_target")
            if next_load is not None:
                next_str = f"  |  Next week: {next_load} TSS"
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
    print(f"  Long ride sessions:  {m['long_ride_sessions']}")
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
        if training_plan:
            save_json({}, None, monday, training_plan)
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
