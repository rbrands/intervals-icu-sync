"""Fetch the athlete's upcoming planned workouts from intervals.icu.

Retrieves all WORKOUT events in the next 6 weeks, prints a summary including
the active training phase (from PLAN events), and saves the result to
data/processed/training_plan_{date}.json.

Usage:
    python scripts/get_training_plan.py
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import requests

from intervals_icu.config import API_KEY, ATHLETE_ID

BASE_URL = "https://intervals.icu/api/v1"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
LOOKAHEAD_WEEKS = 6
LOOKBACK_WEEKS = 16  # How far back to search for PLAN events that started before today


def fetch_all_events(start: str, end: str) -> list:
    url = f"{BASE_URL}/athlete/{ATHLETE_ID}/events.json"
    response = requests.get(
        url,
        auth=("API_KEY", API_KEY),
        params={"oldest": start, "newest": end},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def find_active_phases(events: list, today: date) -> list:
    """Return all active training phases (PLAN events covering today).

    Each entry: {plan_name, phase, sport_type, start, end}
    Phases that start on 'today' take priority (sorted first).
    """
    result = []
    for ev in events:
        if ev.get("category") != "PLAN":
            continue
        start = ev.get("start_date_local", "")[:10]
        end = ev.get("end_date_local", "")[:10]
        if start <= today.isoformat() <= end:
            tags = ev.get("tags") or []
            result.append({
                "plan_name": ev.get("name") or "Training Plan",
                "phase": tags[0] if tags else None,
                "sport_type": ev.get("type"),
                "start": start,
                "end": end,
            })
    # Prefer phases that start on 'today' (latest start date first)
    result.sort(key=lambda p: p["start"], reverse=True)
    return result


def find_week_note(events: list, monday: date) -> str | None:
    """Return the name of a NOTE event for the given week, if one exists (e.g. 'Recovery Week')."""
    week_start = monday.isoformat()
    week_end = (monday + timedelta(days=6)).isoformat()
    for ev in events:
        if ev.get("category") != "NOTE":
            continue
        ev_date = ev.get("start_date_local", "")[:10]
        if week_start <= ev_date <= week_end:
            return ev.get("name")
    return None


def find_weekly_load_targets(events: list, monday: date) -> list:
    """Return all load targets for the ISO week starting on monday (one per sport type).

    Each entry: {load_target, sport_type, week_type, training_availability, week_note}
    week_type is derived from a NOTE event name (e.g. 'Recovery Week' → 'RECOVERY'),
    falling back to 'NORMAL'. training_availability is the athlete's time availability
    for the week as set on the TARGET event (NORMAL | LIMITED | etc.).
    """
    week_note = find_week_note(events, monday)
    # Map known note names to canonical week_type values
    _NOTE_TYPE_MAP = {
        "recovery week": "RECOVERY",
        "race week": "RACE",
    }
    note_week_type = _NOTE_TYPE_MAP.get(week_note.lower(), "NOTE") if week_note else None

    week_start = monday.isoformat()
    week_end = (monday + timedelta(days=6)).isoformat()
    result = []
    for ev in events:
        if ev.get("category") != "TARGET":
            continue
        ev_date = ev.get("start_date_local", "")[:10]
        if week_start <= ev_date <= week_end:
            load_target = ev.get("load_target")
            if load_target is not None:
                entry = {
                    "load_target": load_target,
                    "sport_type": ev.get("type"),
                    "week_type": note_week_type or "NORMAL",
                    "training_availability": ev.get("training_availability", "NORMAL"),
                }
                if week_note:
                    entry["week_note"] = week_note
                result.append(entry)
    return result


def main() -> None:
    today = date.today()
    end_date = today + timedelta(weeks=LOOKAHEAD_WEEKS)
    # Look back far enough to capture PLAN events that started before today
    phase_start = today - timedelta(weeks=LOOKBACK_WEEKS)

    phase_events = fetch_all_events(phase_start.isoformat(), end_date.isoformat())
    active_phases = find_active_phases(phase_events, today)
    monday = today - timedelta(days=today.weekday())
    next_monday = monday + timedelta(weeks=1)
    next_week_active_phases = find_active_phases(phase_events, next_monday)
    load_targets = find_weekly_load_targets(phase_events, monday)
    next_week_load_targets = find_weekly_load_targets(phase_events, next_monday)

    # Build a lookup: sport_type → (load_target, week_type) for easy merging
    load_by_type = {lt["sport_type"]: lt["load_target"] for lt in load_targets}
    week_type_by_type = {lt["sport_type"]: lt.get("week_type", "NORMAL") for lt in load_targets}

    workouts = [e for e in phase_events if e.get("category") == "WORKOUT"
                and e.get("start_date_local", "")[:10] >= today.isoformat()]

    if active_phases:
        for p in active_phases:
            sport = p["sport_type"] or "All"
            phase_label = f"#{p['phase']}" if p["phase"] else "(no tag)"
            load = load_by_type.get(p["sport_type"]) or load_by_type.get(None)
            load_str = f"{load} TSS" if load is not None else "(none)"
            week_type = week_type_by_type.get(p["sport_type"]) or week_type_by_type.get(None) or "NORMAL"
            print(f"Plan: {p['plan_name']!r:<20}  Sport: {sport:<8}  Phase: {phase_label:<12}  Weekly target: {load_str}  Week type: {week_type}")
    else:
        print("Current phase:      (none found)")
        for lt in load_targets:
            sport = lt["sport_type"] or "All"
            print(f"Weekly load target ({sport}): {lt['load_target']} TSS  Week type: {lt.get('week_type', 'NORMAL')}")

    if not workouts:
        print("No planned workouts found in the next 6 weeks.")
    else:
        print(f"\nUpcoming planned workouts ({today} – {end_date}):")
        print(f"{'Date':<12} {'Name':<45} {'Duration':>10}  {'Load':>6}")
        print("-" * 80)
        for ev in workouts:
            ev_date = ev.get("start_date_local", "")[:10]
            name = ev.get("name") or "(unnamed)"
            duration_s = ev.get("moving_time") or 0
            duration_h = f"{duration_s / 3600:.1f}h" if duration_s else "-"
            load = ev.get("icu_training_load")
            load_str = str(load) if load is not None else "-"
            print(f"{ev_date:<12} {name:<45} {duration_h:>10}  {load_str:>6}")

        print(f"\nTotal: {len(workouts)} workouts")

    output = {
        "fetched_on": today.isoformat(),
        "active_phases": active_phases,
        "next_week_active_phases": next_week_active_phases,
        "weekly_load_targets": load_targets,
        "next_week_load_targets": next_week_load_targets,
        "range_start": today.isoformat(),
        "range_end": end_date.isoformat(),
        "workouts": workouts,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"training_plan_{today.isoformat()}.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved -> {output_path}")


if __name__ == "__main__":
    main()
