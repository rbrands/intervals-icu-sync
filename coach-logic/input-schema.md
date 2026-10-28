# Input Schema

Reference for reading the coach input JSON. Only NON-OBVIOUS fields are
documented — self-explanatory fields (ftp, weight, avg_power, avg_hr,
duration_hours, etc.) are omitted.

How values are INTERPRETED (thresholds, classifications) is in
interpretation-rules.md. This file only explains what a field IS, its
unit, and how it is derived.

---

## Top-Level Structure

schema_version, week_starting, lookback_days, current_date, metrics, week_summary,
training_load_history, activities, fueling_analysis, planned_workouts

- `week_starting` / `current_date` (YYYY-MM-DD) are the ONLY authoritative
dates. Derive all dates from these (see system prompt, Date Handling).

- `lookback_days`: sliding activity/fueling window size used during data
  preparation. `week_summary` remains calendar-week based.

---

## Units & Conventions (CRITICAL)

- Durations: activities → hours; planned steps → minutes; output → seconds.
- Power: always relative to FTP (%).
- Weight in `metrics.weight` and `metrics.wellness_trends.weight.*` is always kilograms (kg).
- Tags override interval detection and automatic classification.
- Planned workouts take precedence over new planning.
- Activities are ordered newest-first.

---

## metrics — non-obvious fields

- `ftp` / `rolling_ftp` / `eftp`: set FTP (W), 42-day rolling estimate,
  and effective FTP from recent rides. Use `ftp` for zones unless told
  otherwise.
- `ftp_eftp_delta_pct`: percentage difference between `ftp` and `eftp`,
  calculated as `((eftp - ftp) / ftp) * 100`. Positive values mean eFTP is
  above FTP. Read together with
  `week_summary.aerobic_threshold_estimate.delta_pct` when both are present
  (see interpretation rules, *Cross-check with FTP vs. eFTP*).
- `ftp_classification`: age- and sex-adjusted FTP category based on FTP
  W/kg, including `w_per_kg`, `category`, `category_range`,
  `next_category`, and `delta_to_next`.
- `w_prime` / `rolling_w_prime`: W' (J) from the current Ride sport
  settings, and intervals.icu's rolling W' estimate. Activity-level
  `w_prime_j` falls back to the rolling estimate when no W' is set.
- `power_zones_pct`: upper bounds of the athlete's configured Ride power
  zones as % FTP, Z1 first (e.g. `[55, 75, 90, 105, 120, 150, 999]`). The
  second entry is the Zone 2 ceiling used by
  `week_summary.aerobic_threshold_estimate`. Null when no zones are set.
- `hrv`: nightly / resting HRV (RMSSD, ms) from wellness data — a recovery
  signal. It is NOT the in-ride DFA a1 reported in
  `activities[].dfa_a1_summary`; the two must never be mixed.
- `rolling_p_max`: rolling max 1-second power (42-day).
- `power_profile.curve_slope`: slope of the power-duration curve.
  Less negative (≈ −0.45) = anaerobic/puncheur; more negative (≈ −0.70)
  = aerobic/climber.
- `vo2max_classification.ml_per_kg_min`: VO2Max estimated from p5min power and weight (ml/kg/min).
- `vo2max_classification`: age- and sex-adjusted VO2Max category based on VO2Max
  (ml/kg/min), including `ml_per_kg_min`, `age_group`, `sex`, `category`,
  `category_range`, `next_category`, and `delta_to_next`. Age groups:
  teen_13_19, adult_20_29, master_30_39, master_40_49, grand_master_50_59,
  senior_60_plus. Categories: very_poor, poor, average, good, very_good, excellent.
- `sleep_secs`: SECONDS (÷3600 for hours).
- `sleep_quality`: one of `GREAT`, `GOOD`, `AVG`, `POOR` (mapped from intervals.icu scale 1–4; GREAT = best).
- `lthr`: lactate threshold heart rate (bpm).
- `wellness_trends`: keys `weight`, `resting_hr`, `hrv`, each with:
  - `current`: latest available value.
  - `avg_7d`: mean of the last 7 days.
  - `avg_prev_7d`: mean of days 8–14 before the latest point.
  - `trend_7d`: `up`, `down`, or `stable` based on `avg_7d` vs `avg_prev_7d`.
- `ctl`/`atl` are intentionally not part of `metrics` in consolidated
  `coach_input`; they are grouped in `week_summary` with form fields.

Activity-level FTP fields are separate from the current athlete Metrics:
`activities[].activity_ftp` is the FTP value stored with the activity, and
`activities[].activity_eftp` is the activity-specific eFTP from intervals.icu.
`activities[].is_hard_session` marks whether the activity meets the same
CTL-relative load, training-distribution, or RPE rules used by
`week_summary.days_since_last_hard_session`.
`activities[].ctl` / `activities[].atl` / `activities[].form_absolute` are the
fitness, fatigue and form (CTL−ATL) values *after* that activity, as reported
by intervals.icu. Read them in date order to see the CTL/ATL/TSB trajectory;
`week_summary.ctl`/`atl` remain the current (today) snapshot.
`activities[].ctl_delta` / `activities[].atl_delta` /
`activities[].form_absolute_delta` are the current activity's values minus those
of the chronologically previous *exported* activity (the next entry in the
newest-first list). Positive values indicate an increase; negative values a
decrease. Each delta is rounded to one decimal place and is null if either
value is missing or no previous exported activity exists.

---

## week_summary — non-obvious fields

- `ctl` / `atl`: current fitness/fatigue snapshot copied from daily metrics to
  keep readiness (`ctl`, `atl`, `form_*`) together in one section.
- `form_absolute` / `form_pct` / `form_zone`: CTL−ATL, its ratio, the zone
  label (thresholds in interpretation-rules.md).
- `training_readiness`: explainable readiness for today's or the next session,
  derived from form, hard-session recency, HRV, resting HR, and sleep. It contains
  `status` (`green`, `yellow`, `red`, or `unknown`), numeric `score`, `confidence`,
  `recommendation`, `reasons`, `safety_vetoes`, and per-domain `signals` with
  `name`, `status`, `contribution`, and `reason`. Missing domains lower confidence
  but do not count negatively. Weight trend is context only and is not scored.
- `days_since_last_hiit`: integer number of calendar days since the last ride
  whose `training_distribution` is `HIIT`. `0` means the athlete had a HIIT
  session today.
- `days_since_last_polarized`: integer number of calendar days since the last
  ride whose `training_distribution` is `HIIT` or `Polarized`.
- `days_since_last_hard_session`: integer number of calendar days since the
  last session with TSS at least 50% above current CTL, the last `HIIT` or
  `Polarized` ride, or the last `Threshold` ride with at least 50 TSS or RPE 7+.
- `aerobic_threshold_estimate`: week-level aggregate of the per-ride
  `dfa_a1_summary` entries (see activities). Present ONLY when at least one
  ride in the lookback has `dfa_a1_summary.valid = true`; omitted otherwise.
  No multi-week trend is provided — the focus is the current lookback.
  - `rides_with_valid_data` / `rides_with_threshold_crossing`: rides with a
    valid analysis, and the subset in which DFA a1 actually crossed 0.75 so
    that a threshold power could be read.
  - `threshold_windows_total`: sum of `threshold_windows` over the crossing
    rides — the total evidence behind the estimate. Null when no ride crossed.
  - `power_at_0_75` / `hr_at_0_75`: power (W) and HR (bpm) at which DFA a1
    ≈ 0.75, averaged across the crossing rides and weighted by each ride's
    `threshold_windows` (a ride with many threshold windows dominates one
    that barely touched the band) — the current aerobic threshold (LT1/VT1)
    estimate. Null when no ride crossed 0.75.
  - `z2_upper_power` / `z2_upper_source`: the athlete's configured Zone 2
    ceiling in watts (`athlete_zones` = from `metrics.power_zones_pct`,
    `ftp_75pct` = fallback to 75 % FTP when no zones are set).
  - `delta_pct`: `(power_at_0_75 − z2_upper_power) / z2_upper_power × 100`.
    Negative = LT1 estimate below the Z2 ceiling (interpretation in
    interpretation-rules.md).
  - `avg_time_above_0_75_pct`: mean share of valid ride time with DFA a1
    above 0.75 across the valid rides.
- `training_plan`: optional entries for the current and next week. An entry may
  contain a phase, weekly targets, and/or day constraints; a phase is not
  required for targets or constraints to be present.
- `training_plan[].week`: Monday of the represented ISO week (YYYY-MM-DD).
- `training_plan[].phase`: label of the active intervals.icu `PLAN` phase
  (or set by the athlete). Optional; it is supplied by the plan, not
  inferred from the week type or targets.
- `training_plan[].weekly_load_target` / `weekly_time_target_hours`: weekly
  Ride targets in TSS and hours. They are independent and may both be present;
  use the time target as an upper limit, not as a conversion from TSS.
- `training_plan[].week_type` / `week_note`: week classification
  (`NORMAL`, `RECOVERY`, `RACE`) and its note, when present. This is separate
  from the training phase.
- `training_plan[].day_constraints`: date-specific availability or time
  limits. Each entry includes `date`, `type`, `training_allowed`, and may
  include `max_training_time_hours` and source details.

---

## training_load_history

- Top-level array containing the last four completed ISO calendar weeks, oldest first.
- `weekly_load_target`: Ride load target from the intervals.icu TARGET event;
  null when no target exists for that week.
- `total_training_load`: server-side aggregated Ride training load from the
  intervals.icu athlete summary; zero when the week has no Ride load.
- `achievement_pct`: `total_training_load / weekly_load_target * 100`, rounded
  to one decimal; null when no positive target exists.
- `ctl` / `atl`: last available daily fitness and fatigue values in the week.
- `form_absolute` / `form_pct` / `form_percent_display`: form values calculated
  identically to `week_summary`: `ctl - atl`, `(ctl - atl) / ctl`, and the
  percentage display value. They are null when the underlying wellness data is
  unavailable.
- The current, incomplete week is intentionally excluded because its load and
  target are already available in `week_summary`.

---

## activities — non-obvious fields

- `id` identifies the activity in intervals.icu; `type` contains the source
  activity type (for example `Ride`, `Run`, or `VirtualRide`).
- `notes`: free-text athlete description; qualitative context (effort,
  conditions, how legs felt); null if unset.
- `weather`: null for indoor rides (no GPS). `max_rain` > 0 = wet.
- `w_prime_bal_drop_j`: max W'bal depletion during the activity (J).
- `w_prime_bal_min_j`: lowest W'bal reached (= w_prime_j − drop).
- `w_prime_usage_pct`: drop as % of W'.
- `wbal_summary`: present ONLY for high-intensity activities (z5_plus_pct
  ≥ 8, an interval ≥ 105% FTP for ≥ 2 min, a vo2* tag, or a race/event);
  null otherwise. Key field: `wbal_min_j` = lowest W'bal reached.
- `power_curve`: best mean-maximal power per duration; null if no power.
  p3m ≈ VO2max proxy, p5m = gold-standard VO2max effort, p20m ≈ FTP proxy.
- `decoupling`: aerobic decoupling in %, calculated only for activities with
  power data. The field is omitted for activities without power data,
  including HR-only runs.
- `decoupling_label`: classification of `decoupling`; omitted together with
  `decoupling` when power data is unavailable, and null when the ride does
  not meet the decoupling validity conditions.
- `interval_hr_analysis`: compact WORK-interval HR durability summary;
  omitted when power data is unavailable or no suitable structured intervals
  are available.
  Suitable means: WORK intervals with at least 120 seconds duration and at
  least 95% FTP intensity.
  - `hr_start_avg`: avg HR of first half of WORK intervals.
  - `hr_end_avg`: avg HR of second half of WORK intervals.
  - `hr_drift_pct`: HR drift from first to second half in %.
  - `hr_power_decoupling`: HR drift (%) minus power drop (%) across WORK reps.
- `dfa_a1_summary`: in-ride DFA alpha 1 analysis of the recorded R-R
  intervals (`hrv` stream, requires HRV logging on the head unit and a chest
  strap). Present ONLY for longer, predominantly aerobic rides (≥ 60 min,
  HR data, Z5+ < 10 %, no race/vo2*/event tag, at most three newest rides per
  export); the key is omitted entirely when the ride has no `hrv` stream or
  fails this gate. This is NOT the nightly `metrics.hrv`.
  - `valid`: false when the data failed the quality gate; `reason` then says
    why (coverage < 50 %, artifact rate > 10 %, too few valid windows) and
    all other fields are absent. Use this to flag strap/contact problems.
  - `artifact_pct` / `coverage_pct`: share of rejected beats (> 20 % jump to
    the previous interval) and share of ride seconds with R-R data.
  - `windows_total` / `windows_valid`: 120-second analysis windows (30 s
    step) and those kept after the first 10 minutes with ≤ 5 % artifacts.
  - `avg`: mean DFA a1 over valid windows (dimensionless, ~0.3–1.5; falls
    with intensity).
  - `time_above_0_75_pct` / `time_below_0_5_pct`: share of valid windows
    above the aerobic-threshold marker 0.75 and below the 0.5 marker.
  - `power_at_0_75` / `hr_at_0_75` / `threshold_windows`: mean power and HR
    of the windows with DFA a1 in 0.65–0.85 (today's LT1 estimate for this
    ride) and how many windows supported it (≥ 3 required; null otherwise).
  - In-ride durability is NOT derived from DFA a1; use `decoupling` /
    `decoupling_label` for that.

---

## fueling_analysis — non-obvious fields

- `fueling_analysis` now carries aggregate week-level outputs only
  (`weekly_summary`, `recommendations`).
- Per-activity fueling details are nested under `activities[].fueling`.
  - `carbs_classification`: classification of absolute intake rate
    (`carbs_per_hour`).
  - `ratio_classification`: classification of intake adequacy relative to
    estimated carbohydrate use (`fueling_ratio`).
  - `fueling_ratio`: carbs_ingested / carbs_used (classification thresholds
    in interpretation-rules.md).
  - `flags`: may indicate underfueling or other issues.

---

## planned_workouts — non-obvious fields

- `steps[].duration_min`: MINUTES (note the unit difference vs activities
  in hours and output in seconds).
- Planned workouts must be considered BEFORE adding or modifying sessions.
- `current_week.race_events[]` and `next_week.race_events[]`: intervals.icu
  race calendar events. `priority` preserves the source category (`RACE_A`,
  `RACE_B`, or `RACE_C`). Treat these as fixed events, not planned workouts.
