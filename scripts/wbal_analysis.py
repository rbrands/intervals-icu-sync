"""Compute and display the W'bal time series for one or more activities.

Fetches the power stream from intervals.icu and applies the Skiba differential
model to reconstruct the W'bal curve exactly as shown in the intervals.icu UI.

Usage:
    python scripts/wbal_analysis.py                    # latest week activities
    python scripts/wbal_analysis.py --id i143131711    # single activity by id
    python scripts/wbal_analysis.py --plot             # show matplotlib plot

Output (JSON) is saved to data/processed/wbal_{activity_id}.json.

Model reference:
    Skiba et al. (2012) – Skiba differential model
    W'bal(t) = W' - integral_0^t max(0, P(u) - CP) * exp(-(t-u)/tau_w) du
    where tau_w = W' / (CP - P_mean_below_cp) with a floor of 1 s.

    The discrete update per second:
        if P(t) >= CP:
            W'bal -= P(t) - CP          (depletion)
        else:
            W'bal += (W' - W'bal) * (1 - exp(-1/tau))   (reconstitution)
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from intervals_icu.client import get_activity_streams
from intervals_icu.config import API_KEY, ATHLETE_ID
from intervals_icu.wbal import compute_wbal, summarize_wbal

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


# ---------------------------------------------------------------------------
# W'bal model and summary are provided by intervals_icu.wbal
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Per-activity processing
# ---------------------------------------------------------------------------

def process_activity(activity: dict, plot: bool = False) -> dict | None:
    act_id = activity.get("id")
    name = activity.get("name", act_id)
    w_prime = activity.get("icu_w_prime")
    ftp = activity.get("icu_ftp")

    if not w_prime or not ftp:
        print(f"  Skipping {name}: missing icu_w_prime or icu_ftp")
        return None

    cp = float(ftp)
    w_prime = float(w_prime)

    print(f"  Fetching streams for {name} ({act_id}) …")
    try:
        streams = get_activity_streams(API_KEY, act_id)
    except Exception as exc:
        print(f"  Failed to fetch streams: {exc}")
        return None

    # Extract watts stream
    watts_stream = next((s for s in streams if s.get("type") == "watts"), None)
    if not watts_stream:
        print(f"  No power data for {name} – skipping")
        return None

    watts: list[float | None] = watts_stream.get("data", [])
    if not watts:
        print(f"  Empty watts stream for {name} – skipping")
        return None

    # Extract time stream (for x-axis in output / plot)
    time_stream = next((s for s in streams if s.get("type") == "time"), None)
    times: list[int] = time_stream["data"] if time_stream else list(range(len(watts)))

    wbal = compute_wbal(watts, w_prime, cp)
    summary = {**summarize_wbal(wbal, w_prime), "cp_w": cp}

    print(f"    W'     = {w_prime:.0f} J   CP = {cp:.0f} W")
    print(f"    W'bal min = {summary['wbal_min_j']:.0f} J  ({summary['wbal_usage_pct']} % depleted)")
    print(f"    Time below 30 % W': {summary['seconds_below_30pct']} s")
    print(f"    Time below 10 % W': {summary['seconds_below_10pct']} s")

    result = {
        "activity_id": act_id,
        "name": name,
        "date": (activity.get("start_date_local") or "")[:10],
        "summary": summary,
        "series": [
            {"t": t, "watts": w, "wbal": wb}
            for t, w, wb in zip(times, watts, wbal)
        ],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"wbal_{act_id}.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"    Saved → {out_path.name}")

    if plot:
        _plot(name, times, watts, wbal, w_prime, cp)

    return result


# ---------------------------------------------------------------------------
# Optional matplotlib plot
# ---------------------------------------------------------------------------

def _plot(name: str, times: list[int], watts: list[float | None], wbal: list[float],
          w_prime: float, cp: float) -> None:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except ImportError:
        print("  matplotlib not installed – skipping plot")
        return

    hours = [t / 3600 for t in times]
    watts_clean = [w if w is not None else 0 for w in watts]
    wbal_pct = [v / w_prime * 100 for v in wbal]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
    fig.suptitle(f"W'bal – {name}", fontsize=13)

    ax1.plot(hours, watts_clean, color="#4e9af1", linewidth=0.8, alpha=0.9)
    ax1.axhline(cp, color="orange", linewidth=1.2, linestyle="--", label=f"CP {cp:.0f} W")
    ax1.set_ylabel("Power (W)")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    ax2.fill_between(hours, wbal_pct, alpha=0.35, color="#e05c5c")
    ax2.plot(hours, wbal_pct, color="#e05c5c", linewidth=0.9)
    ax2.axhline(30, color="orange", linewidth=1, linestyle=":", label="30 % W'")
    ax2.axhline(10, color="red",    linewidth=1, linestyle=":", label="10 % W'")
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("W'bal (%)")
    ax2.set_xlabel("Time (h)")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_latest_activities() -> list[dict]:
    files = sorted(DATA_DIR.glob("activities_*.json"))
    if not files:
        print("Error: No activities files found in data/raw/.")
        sys.exit(1)
    return json.loads(files[-1].read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute W'bal time series for activities.")
    parser.add_argument("--id", dest="activity_id", help="Single activity id (e.g. i143131711)")
    parser.add_argument("--plot", action="store_true", help="Show matplotlib plot")
    args = parser.parse_args()

    if args.activity_id:
        # Single activity – fetch just its metadata from latest raw file
        activities = load_latest_activities()
        activity = next((a for a in activities if a.get("id") == args.activity_id), None)
        if not activity:
            # Minimal stub so we can still fetch streams if activity not in current raw file
            activity = {"id": args.activity_id, "name": args.activity_id}
            # Try to resolve w_prime / ftp from the raw file
            print(f"Activity {args.activity_id} not found in latest raw file.")
            sys.exit(1)
        print(f"Processing: {activity.get('name', args.activity_id)}")
        process_activity(activity, plot=args.plot)
    else:
        activities = load_latest_activities()
        qualifying = [
            a for a in activities
            if a.get("type") in ("Ride", "VirtualRide")
            and a.get("source") != "STRAVA"
            and a.get("icu_w_prime")
            and a.get("icu_ftp")
        ]
        if not qualifying:
            print("No qualifying rides found in latest raw file.")
            sys.exit(0)
        print(f"Processing {len(qualifying)} ride(s):\n")
        for act in qualifying:
            process_activity(act, plot=args.plot)


if __name__ == "__main__":
    main()
