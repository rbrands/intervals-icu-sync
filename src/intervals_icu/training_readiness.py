"""Compute an explainable daily training-readiness signal."""


def _readiness_signal(name: str, contribution: int | None, reason: str) -> dict:
    if contribution is None:
        status = "unavailable"
        score = 0
    else:
        status = "positive" if contribution > 0 else "adverse" if contribution < 0 else "neutral"
        score = contribution
    return {
        "name": name,
        "status": status,
        "contribution": score,
        "reason": reason,
    }


def _relative_change_pct(current: object, baseline: object) -> float | None:
    try:
        current_value = float(current)
        baseline_value = float(baseline)
    except (TypeError, ValueError):
        return None
    if baseline_value <= 0:
        return None
    return (current_value - baseline_value) / baseline_value * 100.0


def _trend_signal(
    name: str,
    trend: dict | None,
    moderate_threshold: float,
    strong_threshold: float,
    inverse: bool = False,
) -> dict:
    if not isinstance(trend, dict):
        return _readiness_signal(name, None, f"No {name.replace('_', ' ')} trend is available.")

    change_pct = _relative_change_pct(trend.get("current"), trend.get("avg_7d"))
    if change_pct is None:
        return _readiness_signal(name, None, f"No usable {name.replace('_', ' ')} baseline is available.")

    effective_change = -change_pct if inverse else change_pct
    if effective_change <= -strong_threshold:
        contribution = -2
    elif effective_change <= -moderate_threshold:
        contribution = -1
    elif effective_change >= strong_threshold:
        contribution = 2
    elif effective_change >= moderate_threshold:
        contribution = 1
    else:
        contribution = 0

    trend_label = trend.get("trend_7d")
    favorable_trend = "down" if inverse else "up"
    adverse_trend = "up" if inverse else "down"
    if trend_label == favorable_trend:
        contribution = min(2, contribution + 1)
    elif trend_label == adverse_trend:
        contribution = max(-2, contribution - 1)

    direction = "above" if change_pct > 0 else "below" if change_pct < 0 else "at"
    reason = (
        f"{name.replace('_', ' ').title()} is {abs(change_pct):.1f}% {direction} "
        f"its 7-day average and trending {trend_label or 'is unavailable'}."
    )
    return _readiness_signal(name, contribution, reason)


def _sleep_signal(metrics: dict) -> dict:
    sleep_secs = metrics.get("sleep_secs")
    quality = metrics.get("sleep_quality")
    try:
        sleep_hours = float(sleep_secs) / 3600.0 if sleep_secs is not None else None
    except (TypeError, ValueError):
        sleep_hours = None
    quality_label = str(quality).upper() if quality is not None else None

    if sleep_hours is None and quality_label is None:
        return _readiness_signal("sleep", None, "No sleep data is available.")
    if quality_label == "POOR" or (sleep_hours is not None and sleep_hours < 6.0):
        contribution = -2
    elif quality_label == "AVG" or (sleep_hours is not None and sleep_hours < 7.0):
        contribution = -1
    elif quality_label in {"GOOD", "GREAT"} or (sleep_hours is not None and sleep_hours >= 7.0):
        contribution = 1
    else:
        contribution = 0

    duration = f"{sleep_hours:.1f} hours" if sleep_hours is not None else "unknown duration"
    return _readiness_signal(
        "sleep",
        contribution,
        f"Sleep was {duration} with {quality_label or 'unknown'} quality.",
    )


def compute_training_readiness(metrics: dict | None, week_summary: dict | None) -> dict:
    """Combine current form, recovery, and intensity recency into a daily readiness signal."""
    metrics = metrics if isinstance(metrics, dict) else {}
    week_summary = week_summary if isinstance(week_summary, dict) else {}
    signals: list[dict] = []
    hard_vetoes: list[str] = []
    readiness_caps: list[str] = []

    ctl = week_summary.get("ctl")
    atl = week_summary.get("atl")
    form_zone = week_summary.get("form_zone")
    try:
        has_form = float(ctl) > 0 and atl is not None and form_zone is not None
    except (TypeError, ValueError):
        has_form = False
    if has_form:
        form_contributions = {
            "transition": 1,
            "fresh": 2,
            "grey_zone": 1,
            "optimal": 0,
            "high_risk": -3,
        }
        contribution = form_contributions.get(str(form_zone), 0)
        form_pct = week_summary.get("form_percent_display")
        form_display = f" ({form_pct:.1f}%)" if isinstance(form_pct, (int, float)) else ""
        signals.append(_readiness_signal("form", contribution, f"Form is {form_zone}{form_display}."))
        if form_zone == "high_risk":
            hard_vetoes.append("Form is in the high-risk zone.")
    else:
        signals.append(_readiness_signal("form", None, "No usable CTL, ATL, and form data is available."))

    days_since_hard = week_summary.get("days_since_last_hard_session")
    if isinstance(days_since_hard, (int, float)) and days_since_hard >= 0:
        days = int(days_since_hard)
        if days == 0:
            contribution = -3
            hard_vetoes.append("A hard session was completed today.")
        elif days == 1:
            contribution = -1
            readiness_caps.append("A hard session was completed one day ago; readiness is capped at yellow.")
        elif days == 2:
            contribution = 1
        else:
            contribution = 2
        signals.append(
            _readiness_signal(
                "hard_session_recency",
                contribution,
                f"The last hard session was {days} day{'s' if days != 1 else ''} ago.",
            )
        )
    else:
        signals.append(
            _readiness_signal("hard_session_recency", None, "No recent hard-session date is available.")
        )

    wellness = metrics.get("wellness_trends")
    wellness = wellness if isinstance(wellness, dict) else {}
    signals.append(_trend_signal("hrv", wellness.get("hrv"), 5.0, 10.0))
    signals.append(_trend_signal("resting_hr", wellness.get("resting_hr"), 3.0, 7.0, inverse=True))
    signals.append(_sleep_signal(metrics))

    recovery_adverse = sum(
        1
        for signal in signals
        if signal["name"] in {"hrv", "resting_hr", "sleep"} and signal["contribution"] < 0
    )
    if recovery_adverse >= 2:
        hard_vetoes.append("At least two recovery signals are adverse.")

    available_signals = [signal for signal in signals if signal["status"] != "unavailable"]
    score = sum(signal["contribution"] for signal in available_signals)
    available_count = len(available_signals)
    confidence = "high" if available_count >= 4 else "medium" if available_count >= 2 else "low"

    if not available_signals:
        status = "unknown"
    elif hard_vetoes or score <= -3:
        status = "red"
    elif score >= 2:
        status = "green"
    else:
        status = "yellow"
    if readiness_caps and status == "green":
        status = "yellow"

    recommendations = {
        "green": "The planned hard session is acceptable if subjective readiness is also good.",
        "yellow": "Adjust training load and verify recovery before adding intensity.",
        "red": "Avoid hard training and prioritize recovery.",
        "unknown": "Assess readiness manually before prescribing intensity.",
    }
    return {
        "status": status,
        "score": score,
        "confidence": confidence,
        "recommendation": recommendations[status],
        "reasons": [signal["reason"] for signal in available_signals],
        "safety_vetoes": hard_vetoes + readiness_caps,
        "signals": signals,
    }
