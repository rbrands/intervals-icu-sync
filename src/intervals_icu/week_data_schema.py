"""Pydantic schema models for consolidated week data (coach_input payload)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class _SchemaModel(BaseModel):
    """Base model that tolerates additive fields for forward compatibility."""

    model_config = ConfigDict(extra="allow")


class WellnessTrend(_SchemaModel):
    current: float | int | None = None
    avg_7d: float | int | None = None
    avg_prev_7d: float | int | None = None
    trend_7d: str | None = None


class WellnessTrends(_SchemaModel):
    weight: WellnessTrend | None = None
    resting_hr: WellnessTrend | None = None
    hrv: WellnessTrend | None = None


class PowerProfilePoint(_SchemaModel):
    watts: float | int | None = None
    w_per_kg: float | int | None = None


class PowerProfile(_SchemaModel):
    p15s: PowerProfilePoint | None = None
    p30s: PowerProfilePoint | None = None
    p1min: PowerProfilePoint | None = None
    p3min: PowerProfilePoint | None = None
    p5min: PowerProfilePoint | None = None
    p20min: PowerProfilePoint | None = None
    curve_slope: float | int | None = None
    period_days: int | None = None
    type: str | None = None
    type_key: str | None = None
    heuristic_score: float | int | None = None
    type_scores: dict[str, float | int] | None = None
    type_method: str | None = None


class FtpCategoryRange(_SchemaModel):
    min: float | int | None = None
    max: float | int | None = None


class FtpClassification(_SchemaModel):
    w_per_kg: float | int | None = None
    age_group: str | None = None
    sex: str | None = None
    category: str | None = None
    category_range: FtpCategoryRange | None = None
    next_category: str | None = None
    delta_to_next: float | int | None = None


class Vo2MaxClassification(_SchemaModel):
    ml_per_kg_min: float | int | None = None
    age_group: str | None = None
    sex: str | None = None
    category: str | None = None
    category_range: FtpCategoryRange | None = None
    next_category: str | None = None
    delta_to_next: float | int | None = None


class Metrics(_SchemaModel):
    date: str | None = None
    ftp: float | int | None = None
    rolling_ftp: float | int | None = None
    eftp: float | int | None = None
    ftp_eftp_delta_pct: float | int | None = None
    w_prime: float | int | None = None
    rolling_w_prime: float | int | None = None
    ew_prime: float | int | None = None
    ftp_classification: FtpClassification | None = None
    rolling_p_max: float | int | None = None
    lthr: float | int | None = None
    max_hr: float | int | None = None
    weight: float | int | None = None
    age: int | None = None
    sex: str | None = None
    resting_hr: float | int | None = None
    hrv: float | int | None = None
    sleep_secs: int | None = None
    sleep_quality: str | None = None
    wellness_trends: WellnessTrends | None = None
    power_profile: PowerProfile | None = None
    vo2max_classification: Vo2MaxClassification | None = None


class FuelingFormAnalysis(_SchemaModel):
    fatigue_status: str | None = None
    fueling_status: str | None = None
    avg_carbs_per_hour: float | int | None = None
    avg_fueling_ratio: float | int | None = None
    underfueled_sessions: int | None = None
    number_of_long_rides: int | None = None
    durability_limited_by_fueling: bool | None = None
    interpretation: str | None = None
    recommendation: str | None = None
    long_ride_advice: str | None = None


class DayConstraint(_SchemaModel):
    date: str | None = None
    type: str | None = None
    training_allowed: bool | None = None
    max_training_time_hours: float | int | None = None
    source_category: str | None = None
    source_name: str | None = None


class TrainingPlanEntry(_SchemaModel):
    week: str | None = None
    plan_name: str | None = None
    phase: str | None = None
    start: str | None = None
    end: str | None = None
    phase_start: str | None = None
    phase_end: str | None = None
    weekly_load_target: float | int | None = None
    weekly_time_target_hours: float | int | None = None
    week_type: str | None = None
    week_note: str | None = None
    day_constraints: list[DayConstraint] | None = None


class WeekSummary(_SchemaModel):
    week_starting: str | None = None
    current_date: str | None = None
    ctl: float | int | None = None
    atl: float | int | None = None
    total_training_load: float | int | None = None
    number_of_rides: int | None = None
    total_time_hours: float | int | None = None
    longest_ride_hours: float | int | None = None
    vo2_sessions: int | None = None
    threshold_sessions: int | None = None
    endurance_sessions: int | None = None
    avg_decoupling: float | int | None = None
    avg_decoupling_label: str | None = None
    high_decoupling_rides: int | None = None
    days_since_last_hiit: int | None = None
    days_since_last_polarized: int | None = None
    days_since_last_hard_session: int | None = None
    form_absolute: float | int | None = None
    form_pct: float | int | None = None
    form_percent_display: float | int | None = None
    form_zone: str | None = None
    fueling_form_analysis: FuelingFormAnalysis | None = None
    training_plan: list[TrainingPlanEntry] | None = None


class IntervalHrAnalysis(_SchemaModel):
    hr_start_avg: float | int | None = None
    hr_end_avg: float | int | None = None
    hr_drift_pct: float | int | None = None
    hr_power_decoupling: float | int | None = None


class Weather(_SchemaModel):
    average_weather_temp: float | int | None = None
    average_feels_like: float | int | None = None
    max_rain: float | int | None = None


class ActivityWbalSummary(_SchemaModel):
    wbal_min_j: float | int | None = None
    wbal_usage_pct: float | int | None = None
    seconds_below_30pct: int | None = None
    depletion_events: int | None = None
    recovery_ratio: float | int | None = None


class FuelingDetail(_SchemaModel):
    ride_type: str | None = None
    fueling_status: str | None = None
    carbs_per_hour: float | int | None = None
    fueling_ratio: float | int | None = None
    carbs_classification: str | None = None
    ratio_classification: str | None = None
    is_long_ride: bool | None = None
    flags: list[str] | None = None


class Activity(_SchemaModel):
    date: str | None = None
    name: str | None = None
    duration_hours: float | int | None = None
    activity_ftp: float | int | None = None
    activity_eftp: float | int | None = None
    training_load: float | int | None = None
    avg_power: float | int | None = None
    norm_power: float | int | None = None
    avg_hr: float | int | None = None
    max_hr: float | int | None = None
    polarization_index: float | int | None = None
    training_distribution: str | None = None
    training_distribution_reason: str | None = None
    z1_z2_pct: float | int | None = None
    z3_z4_pct: float | int | None = None
    z5_plus_pct: float | int | None = None
    interval_summary: list[str] | None = None
    interval_hr_analysis: IntervalHrAnalysis | None = None
    decoupling: float | int | None = None
    decoupling_label: str | None = None
    rpe: float | int | None = None
    carbs_used_g: float | int | None = None
    carbs_ingested_g: float | int | None = None
    w_prime_j: float | int | None = None
    w_prime_bal_drop_j: float | int | None = None
    w_prime_bal_min_j: float | int | None = None
    w_prime_usage_pct: float | int | None = None
    tags: list[str] | None = None
    notes: str | None = None
    weather: Weather | None = None
    fueling: FuelingDetail | None = None
    power_curve: dict[str, float | int] | None = None
    wbal_summary: ActivityWbalSummary | None = None


class FuelingWeeklySummary(_SchemaModel):
    number_of_long_rides: int | None = None
    avg_carbs_per_hour: float | int | None = None
    avg_fueling_ratio: float | int | None = None
    number_of_underfueled_sessions: int | None = None


class FuelingAnalysis(_SchemaModel):
    week_starting: str | None = None
    current_date: str | None = None
    weekly_summary: FuelingWeeklySummary | None = None
    recommendations: list[str] | None = None


class PlannedWorkoutStep(_SchemaModel):
    duration_min: float | int | None = None
    power_pct_ftp: float | int | None = None
    power_watts: float | int | None = None


class ZoneDistribution(_SchemaModel):
    z1_z2_pct: float | int | None = None
    z3_z4_pct: float | int | None = None
    z5_plus_pct: float | int | None = None


class PlannedWorkoutEntry(_SchemaModel):
    date: str | None = None
    time: str | None = None
    name: str | None = None
    type: str | None = None
    tags: list[str] | None = None
    duration_hours: float | int | None = None
    planned_load: float | int | None = None
    description: str | None = None
    zone_distribution: ZoneDistribution | None = None
    steps: list[PlannedWorkoutStep] | None = None


class PlannedWorkoutsWeek(_SchemaModel):
    week_starting: str | None = None
    planned_workouts: list[PlannedWorkoutEntry] | None = None


class PlannedWorkouts(_SchemaModel):
    generated_on: str | None = None
    current_week: PlannedWorkoutsWeek | None = None
    next_week: PlannedWorkoutsWeek | None = None


class TrainingLoadHistoryEntry(_SchemaModel):
    week_starting: str
    weekly_load_target: float | int | None = None
    total_training_load: float | int
    achievement_pct: float | int | None = None
    ctl: float | int | None = None
    atl: float | int | None = None
    form_absolute: float | int | None = None
    form_pct: float | int | None = None
    form_percent_display: float | int | None = None


class WeekData(_SchemaModel):
    """Consolidated `prepare_week_data` response model."""

    schema_version: str
    week_starting: str
    lookback_days: int | None = None
    current_date: str
    metrics: Metrics | None = None
    week_summary: WeekSummary | None = None
    training_load_history: list[TrainingLoadHistoryEntry] | None = None
    activities: list[Activity] | None = None
    fueling_analysis: FuelingAnalysis | None = None
    planned_workouts: PlannedWorkouts | dict[str, Any] | None = None
