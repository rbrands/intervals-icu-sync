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
activities, fueling_analysis, planned_workouts

- `week_starting` / `current_date` (YYYY-MM-DD) are the ONLY authoritative
dates. Derive all dates from these (see system prompt, Date Handling).

- `lookback_days`: sliding activity/fueling window size used during data
  preparation. `week_summary` remains calendar-week based.

---

## Units & Conventions (CRITICAL)

- Durations: activities → hours; planned steps → minutes; output → seconds.
- Power: always relative to FTP (%).
- Tags override interval detection and automatic classification.
- Planned workouts take precedence over new planning.
- Activities are ordered newest-first.

---

## metrics — non-obvious fields

- `ftp` / `rolling_ftp` / `eftp`: set FTP (W), 42-day rolling estimate,
  and effective FTP from recent rides. Use `ftp` for zones unless told
  otherwise.
- `ftp_classification`: age- and sex-adjusted FTP category based on FTP
  W/kg, including `w_per_kg`, `category`, `category_range`,
  `next_category`, and `delta_to_next`.
- `w_prime` / `rolling_w_prime`: set W' (J) and 42-day rolling estimate.
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

---

## week_summary — non-obvious fields

- `form_absolute` / `form_pct` / `form_zone`: CTL−ATL, its ratio, the zone
  label (thresholds in interpretation-rules.md).
- `training_plan[].week_type`: from an intervals.icu NOTE event
  (NORMAL | RECOVERY | RACE); defaults to NORMAL.
- `training_plan[].day_constraints`: day-level constraints extracted from NOTE
  and non-NORMAL availability events in the calendar (e.g. Sick/Travel/
  Unavailable). Each entry includes `date`, `type`, `training_allowed`,
  optional `max_training_time_hours`, `source_category` and `source_name`.

---

## activities — non-obvious fields

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
- `interval_hr_analysis`: compact WORK-interval HR durability summary;
  null if no suitable structured intervals are available.
  Suitable means: WORK intervals with at least 120 seconds duration and at
  least 95% FTP intensity.
  - `hr_start_avg`: avg HR of first half of WORK intervals.
  - `hr_end_avg`: avg HR of second half of WORK intervals.
  - `hr_drift_pct`: HR drift from first to second half in %.
  - `hr_power_decoupling`: HR drift (%) minus power drop (%) across WORK reps.

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
