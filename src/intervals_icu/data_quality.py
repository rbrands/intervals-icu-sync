"""Deterministic completeness and consistency checks, without coaching advice."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


Status = Literal["OK", "Warning", "Missing"]
Number = int | float


class _InputModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore", allow_inf_nan=False)


class _Point(_InputModel):
    watts: Number | None = None


class _Profile(_InputModel):
    p20min: _Point | None = None
    period_days: int | None = None


class _Metrics(_InputModel):
    ftp: Number | None = None
    rolling_ftp: Number | None = None
    eftp: Number | None = None
    w_prime: Number | None = None
    rolling_w_prime: Number | None = None
    resting_hr: Number | None = None
    hrv: Number | None = None
    sleep_secs: Number | None = None
    power_profile: _Profile | None = None


def _iso_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("Expected an ISO date in YYYY-MM-DD format") from None
    if parsed.isoformat() != value:
        raise ValueError("Expected an ISO date in YYYY-MM-DD format")
    return value


class _PlanEntry(_InputModel):
    week: str | None = None

    @field_validator("week")
    @classmethod
    def validate_week(cls, value: str | None) -> str | None:
        return _iso_date(value) if value is not None else None


class _Summary(_InputModel):
    training_plan: list[_PlanEntry] | None = None


class _Activity(_InputModel):
    date: str
    rpe: Number | None = None
    carbs_ingested_g: Number | None = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        return _iso_date(value)


class _HistoryEntry(_InputModel):
    weekly_load_target: Number | None = None


class _AthleteData(_InputModel):
    current_date: str
    week_starting: str
    lookback_days: int = Field(ge=1)
    metrics: _Metrics | None = None
    week_summary: _Summary | None = None
    activities: list[_Activity] | None = None
    training_load_history: list[_HistoryEntry] | None = None

    @field_validator("current_date", "week_starting")
    @classmethod
    def validate_date(cls, value: str) -> str:
        return _iso_date(value)


class QualityCheck(TypedDict):
    area: str
    status: Status
    explanation: str
    evidence: dict[str, Any]
    context: list[str]


class QualityReport(TypedDict):
    current_date: str
    week_starting: str
    lookback_days: int
    checks: list[QualityCheck]
    overall: Literal["Good", "Partial", "Limited"]
    non_ok_count: int
    suggested_fix: str
    report_text: str


def _check(
    area: str, status: Status, explanation: str, **evidence: Any
) -> QualityCheck:
    return {
        "area": area,
        "status": status,
        "explanation": explanation,
        "evidence": evidence,
        "context": [],
    }


def _comparison(
    area: str, baseline: Number | None, estimates: dict[str, Number | None]
) -> QualityCheck:
    unavailable = []
    differences: dict[str, float] = {}
    statuses: list[Status] = []
    for name, value in estimates.items():
        if baseline is None or baseline <= 0 or value is None or value <= 0:
            unavailable.append(name)
            statuses.append("Missing")
            continue
        delta = abs(Decimal(str(value)) - Decimal(str(baseline))) * 100 / Decimal(str(baseline))
        differences[name] = float(delta)
        statuses.append("Missing" if delta > 20 else "Warning" if delta >= 10 else "OK")
    status: Status = (
        "Missing" if "Missing" in statuses else "Warning" if "Warning" in statuses else "OK"
    )
    details = [f"{name} differs by {delta:.2f}%" for name, delta in differences.items()]
    if unavailable:
        details.append("missing or non-positive comparison values: " + ", ".join(unavailable))
    if any(delta > 20 for delta in differences.values()):
        details.append("inconsistent (>20%)")
    impact = (
        "FTP-based zones and load assessments lack a reliable reference."
        if area == "ftp_consistency"
        else "Anaerobic capacity and W' depletion assessments lack a reliable reference."
    )
    explanation = "; ".join(details) + "."
    if status != "OK":
        explanation += " " + impact
    return _check(
        area, status, explanation,
        baseline=baseline, estimates=estimates, difference_pct=differences,
        unavailable_comparisons=unavailable,
    )


_LABELS = {
    "season_plan": "Season plan / macrocycle",
    "ftp_consistency": "FTP consistency",
    "w_prime_consistency": "W' consistency",
    "wellness_tracking": "Wellness tracking",
    "recent_activity_density": "Recent activity density",
    "activity_feedback": "Activity feedback tracking",
    "load_target_history": "Load target history",
}

_FIXES = {
    "season_plan": "Set up or update the season plan in intervals.icu for the current week.",
    "wellness_tracking": "Connect a wellness tracker or record recovery signals.",
    "ftp_consistency": "Verify the configured FTP and the availability of its comparison estimates.",
    "w_prime_consistency": "Verify the configured W' and the availability of its rolling estimate.",
    "activity_feedback": "Record RPE and carbohydrate intake for recent activities.",
    "recent_activity_density": "Check that recent activities are synced and included in the export.",
    "load_target_history": "Add weekly load targets to the season plan for historical comparisons.",
}


def check_athlete_data(athlete_data: dict[str, Any]) -> QualityReport:
    """Check supplied data; malformed structure raises ValueError, not a quality status."""
    try:
        data = _AthleteData.model_validate(athlete_data)
    except ValidationError as exc:
        errors = "; ".join(
            f"{'.'.join(map(str, error['loc']))}: {error['msg']}"
            for error in exc.errors(include_input=False, include_context=False, include_url=False)
        )
        raise ValueError(f"Invalid athlete_data: {errors}") from None

    today = date.fromisoformat(data.current_date)
    monday = today - timedelta(days=today.weekday())
    if data.week_starting != monday.isoformat():
        raise ValueError("Invalid athlete_data: week_starting must be the Monday of current_date")
    try:
        lower = today - timedelta(days=data.lookback_days)
    except OverflowError:
        raise ValueError("Invalid athlete_data: lookback_days exceeds the supported date range") from None
    activities = [
        activity for activity in data.activities or []
        if lower <= date.fromisoformat(activity.date) <= today
    ]
    metrics = data.metrics or _Metrics()
    plan = data.week_summary.training_plan if data.week_summary else None
    has_current_plan = any(entry.week == data.week_starting for entry in plan or [])
    checks = [_check(
        "season_plan", "OK" if has_current_plan else "Missing",
        "A season-plan entry is available for the current week." if has_current_plan else
        "No current-week season-plan entry is available; phase, target and day constraints "
        "cannot be taken from it, so planning falls back to readiness without a season target.",
        entries=len(plan or []), current_week_present=has_current_plan,
    )]
    ftp = _comparison(
        "ftp_consistency", metrics.ftp,
        {"rolling_ftp": metrics.rolling_ftp, "eftp": metrics.eftp},
    )
    profile = metrics.power_profile
    watts = profile.p20min.watts if profile and profile.p20min else None
    if metrics.ftp is not None and metrics.ftp > 0 and watts is not None and watts > 0:
        implied = Decimal(str(watts)) * Decimal("0.95")
        lower_pct = (Decimal(str(metrics.ftp)) - implied) * 100 / Decimal(str(metrics.ftp))
        ftp["evidence"]["p20min_implied_ftp"] = float(implied)
        ftp["evidence"]["p20min_period_days"] = profile.period_days if profile else None
        if lower_pct > 20:
            window = f"{profile.period_days}-day" if profile and profile.period_days else "available"
            ftp["context"].append(
                f"95% of best 20-minute power in the {window} window is {float(lower_pct):.2f}% "
                "below FTP; this may reflect no sustained maximal effort in the window "
                "(especially for sprint/puncheur riders), not a data error."
            )
    checks.append(ftp)
    checks.append(_comparison(
        "w_prime_consistency", metrics.w_prime, {"rolling_w_prime": metrics.rolling_w_prime},
    ))
    wellness_fields = [
        name for name in ("resting_hr", "hrv", "sleep_secs")
        if getattr(metrics, name) is not None
    ]
    checks.append(_check(
        "wellness_tracking", "OK" if wellness_fields else "Missing",
        "At least one recovery signal is recorded." if wellness_fields else
        "No resting HR, HRV or sleep is recorded; recovery-signal input is unavailable "
        "and load-based CTL/ATL/TSB assessments must carry that limitation.",
        recorded_fields=wellness_fields,
    ))
    count = len(activities)
    checks.append(_check(
        "recent_activity_density", "OK" if count >= 3 else "Warning" if count else "Missing",
        f"{count} activities are present in the lookback window." + (
            " Recent-load and intensity-distribution assessments have low confidence."
            if count < 3 else ""
        ),
        activity_count=count, window_start=lower.isoformat(), window_end=today.isoformat(),
    ))
    rpe_count = sum(activity.rpe is not None for activity in activities)
    carbs_count = sum(activity.carbs_ingested_g is not None for activity in activities)
    feedback_status: Status = (
        "Missing" if not count or not rpe_count or not carbs_count else
        "OK" if rpe_count == carbs_count == count else "Warning"
    )
    checks.append(_check(
        "activity_feedback", feedback_status,
        f"RPE is recorded for {rpe_count}/{count} and carbohydrate intake for "
        f"{carbs_count}/{count} activities." + (
            " Subjective exertion and actual fueling cannot be reliably compared with load."
            if feedback_status != "OK" else ""
        ),
        activity_count=count, rpe_recorded=rpe_count, carbs_recorded=carbs_count,
    ))
    target_count = sum(
        entry.weekly_load_target is not None for entry in data.training_load_history or []
    )
    checks.append(_check(
        "load_target_history", "OK" if target_count else "Missing",
        "At least one historical weekly load target is available." if target_count else
        "No historical weekly load target is available; target-versus-achievement trends "
        "cannot be assessed, as is expected when a season plan is missing.",
        recorded_targets=target_count,
    ))
    non_ok = [check for check in checks if check["status"] != "OK"]
    overall: Literal["Good", "Partial", "Limited"] = (
        "Good" if not non_ok else "Partial" if len(non_ok) <= 2 else "Limited"
    )
    # Prefer missing/inconsistent data, then a fixed priority headed by the season
    # plan, which can also restore historical targets.
    priority = list(_FIXES)
    first = min(
        non_ok, key=lambda check: (check["status"] != "Missing", priority.index(check["area"])),
        default=None,
    )
    fix = _FIXES[first["area"]] if first else "No data-quality fix is required."
    lines = [
        f"{_LABELS[check['area']]}: {check['status']} - {check['explanation']}"
        + (" Context: " + " ".join(check["context"]) if check["context"] else "")
        for check in checks
    ]
    lines.append(f"Overall data completeness: {overall}. {fix}")
    return {
        "current_date": data.current_date, "week_starting": data.week_starting,
        "lookback_days": data.lookback_days, "checks": checks, "overall": overall,
        "non_ok_count": len(non_ok), "suggested_fix": fix, "report_text": "\n".join(lines),
    }


def check_athlete_data_payload(athlete_data: str) -> QualityReport:
    """Parse existing JSON and return a native structured report."""
    try:
        payload = json.loads(athlete_data)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid athlete_data JSON at line {exc.lineno}, column {exc.colno}") from None
    if not isinstance(payload, dict):
        raise ValueError("Invalid athlete_data: expected a JSON object")
    return check_athlete_data(payload)


def check_athlete_data_json(athlete_data: str) -> str:
    """Accept existing JSON and serialize the report for console/file output."""
    return json.dumps(check_athlete_data_payload(athlete_data), ensure_ascii=False, allow_nan=False)
