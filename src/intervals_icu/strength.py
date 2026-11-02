"""Shared strength-training tag definitions."""

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
