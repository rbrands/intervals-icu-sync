"""Shared strength-training tag definitions and phase rules."""

from datetime import date

STRENGTH_ADAPTATION_TAG = "strength-adaptation"
STRENGTH_TRANSITION_TAG = "strength-transition"
STRENGTH_MAXIMUM_TAG = "strength-maximum"
STRENGTH_MAINTENANCE_TAG = "strength-maintenance"

CANONICAL_STRENGTH_TAGS = {
    STRENGTH_ADAPTATION_TAG,
    STRENGTH_TRANSITION_TAG,
    STRENGTH_MAXIMUM_TAG,
    STRENGTH_MAINTENANCE_TAG,
}

STRENGTH_PHASE_BY_TAG = {
    STRENGTH_ADAPTATION_TAG: "adaptation",
    STRENGTH_TRANSITION_TAG: "transition",
    STRENGTH_MAXIMUM_TAG: "maximum",
    STRENGTH_MAINTENANCE_TAG: "maintenance",
}

STRENGTH_PHASE_MAX_SESSIONS = {
    "adaptation": 6,
    "transition": 3,
    "maximum": 12,
}

STRENGTH_PHASE_MIN_SESSIONS = {
    "adaptation": 4,
    "transition": 2,
    "maximum": 8,
}

STRENGTH_NEXT_PHASE = {
    "adaptation": "transition",
    "transition": "maximum",
    "maximum": "maintenance",
    "maintenance": "maintenance",
}

STRENGTH_GAP_RESET_DAYS = 21

# Cycling phases in which a new adaptation/maximum block is not started.
STRENGTH_RACE_CYCLING_PHASES = {"build", "peak"}


def resolve_strength_week_phase(
    sessions: list[tuple[date, str | None]],
    week_monday: date,
    cycling_phase: str | None,
) -> tuple[str, int, str]:
    """Return (phase, recommended_sessions, reason) for the week starting at week_monday.

    `sessions` are (date, phase) pairs strictly before `week_monday`; a phase of None
    marks an untagged session that counts for the gap rule but not for phase counts.
    """
    ordered = sorted(
        (entry for entry in sessions if entry[0] < week_monday),
        key=lambda entry: entry[0],
        reverse=True,
    )

    if isinstance(cycling_phase, str) and cycling_phase.strip().lower() in STRENGTH_RACE_CYCLING_PHASES:
        # Later phases presuppose a completed adaptation run that may already have
        # dropped out of the history window.
        adaptation_total = sum(phase == "adaptation" for _, phase in ordered)
        later_phase_seen = any(
            phase in ("transition", "maximum", "maintenance") for _, phase in ordered
        )
        if adaptation_total >= STRENGTH_PHASE_MIN_SESSIONS["adaptation"] or later_phase_seen:
            return "maintenance", 1, "build_guard"
        return "adaptation", 1, "beginner_build"

    if not ordered:
        return "adaptation", 2, "no_history"
    if (week_monday - ordered[0][0]).days >= STRENGTH_GAP_RESET_DAYS:
        return "adaptation", 2, "gap_reset"

    run_phase = None
    run_count = 0
    previous_day = ordered[0][0]
    for session_day, phase in ordered:
        if (previous_day - session_day).days >= STRENGTH_GAP_RESET_DAYS:
            break
        previous_day = session_day
        if phase is None:
            continue
        if run_phase is None:
            run_phase = phase
        if phase != run_phase:
            break
        run_count += 1

    if run_phase is None:
        return "adaptation", 2, "no_history"

    minimum = STRENGTH_PHASE_MIN_SESSIONS.get(run_phase)
    if minimum is not None and run_count >= minimum:
        phase, reason = STRENGTH_NEXT_PHASE[run_phase], "advance_min_reached"
    else:
        phase, reason = run_phase, "continue"
    return phase, (1 if phase == "maintenance" else 2), reason
