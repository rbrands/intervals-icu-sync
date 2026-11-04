# Strength Training (Joe Friel Muscular Force Model)

Specification for integrating off-bike strength training into intervals-icu-sync (data preparation, coach logic, plan upload) and the training-architect frontend. Based on Joe Friel, *The Cyclist's Training Bible* (5th ed.), summarized in https://joefrieltraining.com/muscular-force-training-for-cycling/.

Status: implemented on staging (intervals-icu-sync MCP dev slot, staging agent, training-architect local). Open items in section 8.

This file is the master copy. The copy in the training-architect repository mirrors it; edit here and copy there.

---

## 1. Goals

1. Strength sessions recorded in intervals.icu (`WeightTraining`) become visible to the coach and are classified by Friel phase via tags.
2. The coach plans strength sessions as part of the weekly plan and uploads them as `WeightTraining` events, phase-aware and readiness-aware.
3. Strength load is accounted separately from the Ride load target so that it never fills the weekly Ride TSS budget.

---

## 2. Tag taxonomy

New canonical domain `strength`. Unlike the other domains it does not use the `low / moderate / high` level set; the second part is the Friel phase, because the phase determines load, reps and frequency together.

| Tag                    | Friel phase                | Cycling period            | Sessions total | Sessions / week | Load (% 1RM)        | Sets × reps              | Recovery   |
|------------------------|----------------------------|---------------------------|----------------|-----------------|---------------------|--------------------------|------------|
| `strength-adaptation`  | Anatomical Adaptation (AA) | Prep / early Base         | 4–6            | 2 (max)         | 40–60               | 3–5 × 15–20              | 1–1.5 min  |
| `strength-transition`  | Max Transition (MT)        | Prep / Base               | 2–3            | 2 (max)         | 70–80               | 3–5 × 8–12               | 2–3 min    |
| `strength-maximum`     | Max Strength (MS)          | Base (early)              | 8–12           | 2 (max)         | 85–95               | 3–4 × 3–6                | 3–4 min    |
| `strength-maintenance` | Strength Maintenance (SM)  | late Base, Build, Peak    | indefinite     | 1               | set 1: 60, set 2: 85 | 2 sets: 12 reps / 6 reps | 1–2 min    |

Friel prescribes 2–3 sessions per week in AA/MT/MS; this project caps at 2 (decision D2). Weekly frequency may reduce to 1 only for high-risk form (or clearly negative TSB at plan start), a consistent one-session completion pattern, or when the placement rules leave no further valid day in the target week, not for a RECOVERY week. RECOVERY reduces endurance load only: keep normal strength frequency, phase, and dose; schedule strength only from day 4 onward. Same-day yellow/red readiness limits today's session only, within the applicable planning-mode window.

Exercise selection per session (3–4 exercises):

1. One or two of: double-leg squat, single-leg squat, deadlift, step-up (optionally explosive "power" step-ups with lighter load), lunge, leg press.
2. Leg curl (muscle balance) — always.
3. Core: front plank, side plank, front plank with rows — some combination every session.
4. Power clean may replace a #1 exercise for experienced lifters only; the coach never prescribes it unless the athlete asks.

1RM estimation (for the description text): perform a set with a load that allows only 4–10 reps and divide by the factor 4→0.90, 5→0.875, 6→0.85, 7→0.825, 8→0.80, 9→0.775, 10→0.75.

### Files to update for the taxonomy

- `coach-logic/interpretation-rules.md` — "Tag taxonomy (canonical source)": add domain `strength` with its own level set; add mapping `strength-* → strength` to "Tag → ride_type mapping" (ride_type `strength` is excluded from all ride-domain counts).
- `foundry-agent/agent.yaml` — tag enumeration: add the four strength tags.
- `prompts/system_prompt.md` — canonical tag list.
- training-architect: `src/TrainingArchitect/Prompts/plan_week.md`, `plan_next_training.md`, `plan_correction.md` — wherever canonical domains are listed (updated in that repository).
- `contracts/week-plan/week-plan.schema.json` — if tags are enumerated there.
- Library filter tooling (`list_library_workouts`) — accept the new prefix.
- Legacy free-text tag `strength` is ignored (decision D4): it is neither a canonical tag nor counted in the strength history.

---

## 3. Data preparation (intervals-icu-sync)

### 3.1 Activities export

- `scripts/get_activities.py`: include activity type `WeightTraining`.
  WeightTraining activities are always kept (only the STRAVA-duplicate exclusion applies); `icu_training_load` is optional and may be null when no HR watch was worn and no RPE was logged. RPE is optional for strength and never triggers a reminder.
- `scripts/prepare_activities_for_coach.py`: for `WeightTraining` omit all power-, zone-, decoupling-, W'bal-, power-curve-, DFA- and fueling fields.
  Export `id`, `type`, `date`, `name`, `tags`, `duration_hours`, `rpe`, `notes`, `training_load`, `ctl`, `atl`, `form_absolute` and the deltas.
- Consolidation in `scripts/prepare_week_for_coach.py` and both MCP pipelines adds `strength_phase`, `strength_phase_source`, and `strength_tagging_reminder_needed` to exported WeightTraining activities by activity ID. These describe resolved/inferred phases without changing the original `tags` or exporting the history. Reminder listings stay limited to the exported activity window.
- `is_hard_session`: `true` for `strength-maximum`, `false` for the other three strength tags. (The generic "TSS ≥ 150 % of CTL" rule stays.)
  Rationale: MS sessions produce DOMS and reduce next-day ride quality; the readiness model and the "never two hard days in a row" rule must see them.

### 3.2 Strength history (decision D1)

The 7-day activity window cannot track a phase that spans 4–6 weeks, and `training_load_history` is aggregated. `prepare_week_data` therefore fetches projected completed WeightTraining activities for the last 16 weeks and planned WeightTraining WORKOUT events. Completed sessions end at today; planned events cover complete ISO weeks, from the Monday containing the history start through the Sunday of the current week. No streams or per-activity analysis are fetched. The list is an internal intermediate, never exported to the coach or MCP client:

```json
"strength_history": [
  { "date": "2026-10-28", "tags": ["strength-maximum"], "phase_source": "planned_week", "duration_minutes": 50, "training_load": 38 }
]
```

Tag resolution per completed `WeightTraining` activity:

1. A canonical `strength-*` tag on the activity itself wins.
2. Otherwise fall back to canonical tags of a planned WeightTraining WORKOUT on the same calendar date, with `phase_source: "planned"`.
3. Otherwise use canonical tags of the closest planned WeightTraining WORKOUT in the same ISO year/week (Monday–Sunday), with `phase_source: "planned_week"`. For a mid-week phase change, the closest date wins; equal-distance ties prefer the earlier date. Never use an event in the following or previous ISO week.
4. Without an activity or planned match, inherit the phase of the most recent earlier session resolved by `activity`, `planned`, or `planned_week`, provided the gap is **less than 21 days**. Use `phase_source: "inferred"` and the inherited canonical phase tag internally. Inferred rows count toward `phase_session_count` and continue the run, but do not become inference anchors themselves. This inference may cross ISO-week boundaries.
5. Before the first resolved session, or when the gap to that anchor is at least 21 days, use `tags: []` and `phase_source: "none"`; the session does not advance any phase counter. No automatic phase switch occurs.

Each internal history row carries the activity `id`, `phase_source` (`activity` | `planned` | `planned_week` | `inferred` | `none`) and whether any planned WeightTraining event existed in its week. Only `none` contributes to `untagged_sessions_last_16_weeks`; `inferred` contributes to `inferred_sessions_last_16_weeks`. The coach receives the derived compact summary and phase/source/reminder metadata on the already-exported activities, never the raw history.

### 3.3 `week_summary.strength`

Derived from `strength_history` (and the current week's activities):

```json
"strength": {
  "current_phase": "maximum",
  "phase_started": "2026-10-13",
  "phase_session_count": 5,
  "phase_target_sessions": "8-12",
  "phase_overdue": false,
  "sessions_this_week": 1,
  "days_since_last_strength": 3,
  "last_session_tags": ["strength-maximum"],
  "weekly_strength_load": 38,
  "sessions_per_week_last_4": [2, 2, 2, 2],
  "untagged_sessions_last_16_weeks": 0,
  "inferred_sessions_last_16_weeks": 0,
  "tagging_reminder_needed": false,
  "phase_min_sessions": 8,
  "phase_max_sessions": 12,
  "phase_current_week": "maximum",
  "phase_next_week": "maximum",
  "recommended_sessions_current_week": 2,
  "recommended_sessions_next_week": 2,
  "phase_reason_current_week": "continue",
  "phase_reason_next_week": "continue"
}
```

- `current_phase`: phase of the most recent resolved session, including inference; `null` when there is no recent resolved phase.
- `phase_session_count`: number of consecutive most-recent resolved sessions carrying the same phase, including `inferred` rows. Only `none` rows are skipped; a different phase or a gap of at least 21 days between sessions ends the run.
- `phase_overdue`: true when `phase_session_count` **exceeds** the phase maximum (6 adaptation, 3 transition, 12 maximum); false for maintenance or an unset phase. The data pipeline never switches phase automatically.
- `phase_started`: date of the first session in that run.
- A gap of ≥ 21 days since the last session resets `current_phase` to `null` (the coach then restarts with AA, see 4.2).
- `sessions_per_week_last_4`: all completed sessions per last four completed ISO weeks, oldest first and aligned with `training_load_history`.
- `untagged_sessions_last_16_weeks`: only sessions whose internal `phase_source` is `none`.
- `inferred_sessions_last_16_weeks`: only sessions whose internal `phase_source` is `inferred`.
- `phase_min_sessions` / `phase_max_sessions`: integer bounds of `current_phase` (adaptation 4/6, transition 2/3, maximum 8/12, maintenance null/null). `phase_target_sessions` stays as the human-readable range.
- `phase_current_week` / `phase_next_week`: the deterministic phase for all strength sessions of the current / next ISO week (see 4.2, "Phase determination"). `phase_current_week` uses the run state before this Monday; `phase_next_week` adds this week's completed sessions and later planned WeightTraining events.
- `recommended_sessions_current_week` / `recommended_sessions_next_week`: 2, or 1 for maintenance and `beginner_build`.
- `phase_reason_current_week` / `phase_reason_next_week`: `continue`, `advance_min_reached`, `no_history`, `gap_reset`, `build_guard`, `beginner_build`.
- `tagging_reminder_needed`: true when the current or previous ISO week contains strength sessions with source `none` **or** `inferred` and no planned WeightTraining event existed in that same week. An untagged planned event also suppresses it. The flag is surfaced by the data quality check (`src/intervals_icu/data_quality.py`, MCP `check_athlete_data`, `scripts/check_athlete_data.py`) as the `strength_untagged` area: a `Warning` (never `Missing`) listing eligible exported WeightTraining activities of the current and previous ISO week (date, name, id, plus phase/source metadata). For `none`, keep the unresolved-phase wording and suggest `strength-<current_phase>` (`strength-adaptation` when `current_phase` is null). For `inferred`, say "counted as <phase> - tag the session if it was a different phase", using that session's phase, not necessarily the latest summary phase. Planned sessions and inferred sessions in planned weeks are not listed. Sessions outside the exported activity window cannot be listed; the flag can still trigger a warning. The coach does not mention tagging in plans or analyses.
- The data quality `activity_feedback` area excludes WeightTraining from both the RPE and the carbohydrate completeness checks (decision D6); rides and runs are unchanged.
- When strength tagging is the suggested fix, the summary is: "Untagged strength sessions are counted as the current phase. Tag a session only if it was a different phase." For `none` sessions, use "Tag the session with a strength-<phase> tag so it counts toward the phase." Mixed findings include both instructions; per-session inferred phases remain in the activity listing and evidence.
- For analysis with `current_phase: null` and `strength_sessions > 0`, describe adaptation as a working assumption, not a finding. Never issue a tagging sentence, a separate warning or a missing-RPE reminder.

### 3.4 Load accounting

Current behaviour: `training_load_history` carries the Ride-only sum per sport category from the athlete summary; `week_summary` carries the total of
all exported activities. These two are not directly comparable today, and strength would make the gap visible.

- `week_summary`: keep `total_training_load` (sport-agnostic, CTL-relevant). Add `ride_load`, `run_load`, `strength_load` and matching `ride_time_hours` / `run_time_hours` / `strength_time_hours` and session counts, computed from `activities[]`.
- `achievement_pct` in `week_summary` is computed from `ride_load`, so the current week matches `training_load_history`.
- `training_load_history`: unchanged.
- `check_plan_tss` (local and MCP): sum only entries whose `activity_type` is a ride type (`Ride`, `VirtualRide`, `MountainBikeRide`, `GravelRide`
  or absent). `Run*` and `WeightTraining` entries are listed in the result but excluded from `week.total_tss`.
- `coach-logic/input-schema.md`: correct the `week_summary` description (total of exported activities, not Ride-only) and document the new fields.
- `strength_load` is informational (HR- or RPE-derived, null treated as 0 when summing); phase and frequency come from tags and dates only.

Time accounting follows the same split:

- `weekly_time_target_hours` is a Ride target (intervals.icu Targets Generator, "hours per week"). The athlete enters the time available for cycling; strength time comes on top. Only ride entries count toward it; strength time is reported separately as `strength_time_hours`.
- `max_training_time_hours` on a LIMITED day is an availability limit, not a sport target: the sum of ALL entries on that date, `WeightTraining` included, must not exceed it.
- `check_plan_tss` reports `planned_ride_tss` / `planned_other_tss` and `planned_ride_hours` / `planned_other_hours`; non-ride rows carry `counted: false`.

---

## 4. Coach logic

### 4.1 `coach-logic/workout-library.md` — new section "Strength (off-bike)"

Four entries, one per phase, with the table from section 2 as the "structure" column, the exercise selection rules, and a fixed description template:

```
Phase: <phase name> — Einheit <n> von <target> der Phase
Übungen: <1–2 Hauptübungen> + Beinbeuger + Rumpf
Sätze × Wiederholungen @ % 1RM: <aus der Tabelle>
Pause: <aus der Tabelle>
Hinweise: <Progression>
```

The whole description, labels included, is written in `response_language`;
translate the phase name and prose, but keep the canonical tag in English.
`n = phase_session_count + position in the target week`; `<target>` is the
total phase target, not sessions per week. When n reaches the phase maximum
(6 adaptation, 3 transition, 12 maximum), append one sentence in the response
language stating that the phase is complete and the next phase starts with the
following session.

No `steps`; `activity_type: WeightTraining`; `tss` is always `0` (strength load is not planned; intervals.icu derives it after the session).

Session duration is not an athlete target; it follows from the phase structure: AA / MT ≈ 45–60 min (high reps, short rests), MS ≈ 50–75 min (long rests), SM ≈ 30–45 min (two sets). The 30–75 min bounds in 4.4 are plausibility limits only.

### 4.2 `coach-logic/decision-process.md` — new section "Strength"

Phase determination (deterministic, computed in Python, decision D8). The coach never chooses the phase itself. Rules, applied at the start of the respective ISO week:

1. No history or a gap ≥ 21 days → `adaptation`.
2. Advance when `phase_session_count` ≥ phase minimum: `adaptation` (4) → `transition`, `transition` (2) → `maximum`, `maximum` (8) → `maintenance`; `maintenance` stays. At 2 sessions per week this always lands within Friel's range (4, 2 and 8 sessions).
3. Cycling phase of that week (`training_plan[].phase`):
   - `Base`, `Transition` or none: rules 1 and 2.
   - `Build`, `Peak`: with at least one completed adaptation run (≥ 4 adaptation sessions in history) → `maintenance` (a running maximum run is cut); otherwise `adaptation` with 1 recommended session (`beginner_build`) until the next Base phase. Never start with maintenance or maximum without prior adaptation.

Phase used for a plan, in priority order:

1. The phase given in the request ("Strength phase for this plan: <phase>|none"), set by the training-architect selector (manual phase or Automatic → data field).
2. An explicit chat statement ("ohne Krafttraining", "Maximalkraft starten").
3. `phase_current_week` / `phase_next_week` for the target week.

Strength planning is on by default (D7). `none` → no strength sessions and no mention of strength in the plan. Every WeightTraining entry carries exactly the chosen phase tag. Analysis responses show the Strength block only when strength sessions exist.

Training readiness is a same-day signal, not a multi-day forecast: next-best-training applies it fully to today's session; a current-week plan applies it only to today and tomorrow; a next-week plan ignores it entirely. Later current-week days and next-week intensity/frequency follow form zone, ramp, `week_type`, and `training_load_history`. Today's readiness must not reduce a later planned VO2max or threshold dose; retain same-day safety vetoes.

Frequency (decision D2):

Next training: one main session, optionally plus one strength session on the
same day; readiness applies fully.

- The recommended number from `week_summary.strength` (2, or 1 for maintenance / `beginner_build`) is the default and the upper limit. Reduce by one only when form zone is high-risk (or TSB is clearly negative at plan start), when `sessions_per_week_last_4` shows the athlete consistently completes only one, or when the placement rules leave no further valid day in the target week; state the reason in one sentence. Phase progression counts sessions, not weeks, so a reduced week only delays the next phase.
- For next-best-training today and dates today/tomorrow in a current-week plan only, yellow readiness means no `maximum` strength session on that date and red means no strength on that date. This same-day limit does not reduce weekly frequency. Next-week plans ignore readiness entirely.
- RECOVERY weeks reduce endurance load only; maintain normal strength frequency and current phase dose/tag (2 sessions in adaptation/transition/maximum; 1 in maintenance). Sessions count toward phase progression and phase advance follows the usual thresholds. Schedule strength only from day 4 onward.
- RACE week (`week_type: RACE`): SM only, not within 3 days before the race. A planned race event alone (for example a weekly Zwift club race) does not make a `NORMAL` week a RACE week; it only excludes the race day itself and never reduces weekly strength frequency.

Placement:

- Place each strength session on the first feasible slot in this order:
  1. A day with no ride (rest day).
  2. A day with an easy aerobic or recovery ride, after the ride.
  3. A day with a threshold session, after the ride.
- Never on the long-ride day, VO2max day, or race day. Never schedule strength
  on consecutive days; leave at least two calendar days between sessions.
- An athlete preference naming strength days overrides this ranking only, not
  the exclusions, spacing, safety rules, or calendar availability.
- Name the chosen days and the reason in one sentence. Build the day-by-day
  list from final upload JSON, one line per entry, with matching dates and
  strength sessions included.
- `maximum` counts as a hard session for the "never two hard days in a row"
  rule; `adaptation`, `transition`, `maintenance` do not.

Fatigue inference: the existing rule in `prompts/discipline_fitness.md` ("assume unseen off-bike load") is removed; strength load is now visible.

### 4.3 Plan prompts

- `prompts/system_prompt.md`, `foundry-agent/agent.yaml`, `foundry-agent/agent-staging.yaml`, and in training-architect `Prompts/plan_week.md`, `plan_correction.md`: "at most one ride and at most one `WeightTraining` entry per calendar day"; never two rides.
- Weekly load guardrail: compare the sum of ride entries only against `weekly_load_target`; strength entries never count toward it and are never added to reach it.
- Weekly time guardrail: compare the planned duration of ride entries only against `weekly_time_target_hours`. On a LIMITED day, ride plus strength duration together must stay within `max_training_time_hours`.
- Upload JSON: strength entries use `activity_type: "WeightTraining"`, no `steps`, exactly one `strength-<phase>` tag, description from the template in 4.1.
- `prompts/discipline_fitness.md`: replace "recommend 2 strength sessions per week in prose; never emit them in the upload JSON" with "emit strength sessions per decision-process.md, Strength".
- `prompts/library/02_weekly_analysis.md`: add a "Strength" bullet (phase, sessions done vs. planned, placement quality relative to key sessions).

### 4.4 Validation

- Schema (`contracts/week-plan/week-plan.schema.json`, if/then on `activity_type: WeightTraining`): exactly one tag matching `^strength-(adaptation|transition|maximum|maintenance)$`, no `steps`, no `library_workout_id`, `duration_minutes` 30–75. Legacy `tag` stays tolerated but cannot replace `tags`.
- MCP `validate_week_plan` semantic checks: at most one ride and at most one `WeightTraining` entry per date; no entry on a `training_allowed: false` day; LIMITED-day cap over all entries. Availability checks are skipped when no day constraints are supplied.
- training-architect `TssPlanValidator` mirrors these rules client-side (`plan.duplicate_date`, `plan.strength_entry_invalid`), uses `ride_load` / `ride_time_hours` for completed load and time, and never raises a finding for rows with `counted: false`.

---

## 5. training-architect (frontend, decision D3)

- `TrainingArchitect.Core/Models/TrainingPlan.cs`: `WorkoutType.Strength` and optional `StrengthPhase` (`Adaptation, Transition, Maximum, Maintenance`) on `PlannedWorkout`; tag parsing via a strength-phase helper; ride/strength/run classification via a shared activity-type helper.
- Plan editor (`Coach.razor`): strength rows get their own badge and phase label, no TSS chip; one ride plus one strength entry on a date is not a "Same day" conflict.
- `PlanTssCheckResult` DTOs: additive optional fields (`counted`, `planned_ride_tss`, `planned_other_tss`, `planned_ride_hours`, `planned_other_hours`); strength rows displayed, not summed.
- Strength selector in the planning tiles (plan week, next training), one shared value: "Automatic (→ <phase>)", "Adaptation", "Transition", "Maximum", "Maintenance", "No strength training". Automatic shows `phase_current_week` for current-week plans and next training, `phase_next_week` for next-week plans. Stored client-side in `StoredCredential` with the same durability as language and profile goal; no server-side storage. Absent value → Automatic. The resolved phase is sent as `PlanRequest.StrengthPhase` (plus `StrengthPhaseIsManual`) and rendered into the plan prompts; `TssPlanValidator` checks every WeightTraining tag against it (`plan.strength_phase_mismatch`, `plan.strength_not_requested`).
- Dashboard (`MetricsSnapshot.razor`): a Strength card next to Training Readiness, fed by `week_summary.strength`: the phase that applies this week (manual selection or `phase_current_week`, marked "manually selected" when manual), progress bar with the minimum marked (from `phase_min_sessions` / `phase_max_sessions`), "Switches to <phase> next week" under Automatic, this week, last session, last four weeks. Manual selection: no overdue state, only a grey "Data suggests: <phase>" line when it differs; a one-time hint when Maintenance is chosen without a completed adaptation run. The weekly load chart labels the current week "Ride load · Strength".
- `strength_history` is internal and has no DTO.

---

## 6. Affected files (checklist)

intervals-icu-sync

- [x] `scripts/get_activities.py` — include `WeightTraining`
- [x] `scripts/prepare_activities_for_coach.py` — strength field set,
      `is_hard_session`, `strength_history`, `week_summary.strength`,
      per-sport load breakdown, `achievement_pct` on `ride_load`
- [x] `src/intervals_icu/client.py` — events fetch with type filter for the
      16-week strength history
- [x] `src/intervals_icu/week_data_schema.py` — new models
- [x] `scripts/check_plan_tss.py` / MCP `check_plan_tss` — ride-only sum
- [x] `src/intervals_icu/data_quality.py`, MCP `check_athlete_data`,
      `scripts/check_athlete_data.py` — strength excluded from RPE/carbs
      feedback, `strength_untagged` warning
- [x] `scripts/validate_plan.py`, MCP `validate_week_plan` (`scripts/mcp_server.py`) + `contracts/week-plan/week-plan.schema.json`
- [x] `coach-logic/interpretation-rules.md` — taxonomy, mapping
- [x] `coach-logic/workout-library.md` — Strength section
- [x] `coach-logic/decision-process.md` — Strength section
- [x] `coach-logic/input-schema.md` — new fields, corrected `week_summary` text
- [x] `coach-logic/coaching-principles.md` — one paragraph on muscular force
- [x] `prompts/discipline_fitness.md` (and other discipline files) — strength rule
- [x] `prompts/system_prompt.md`, `foundry-agent/agent.yaml`, `foundry-agent/agent-staging.yaml` — tags, one-per-day rule
- [x] `prompts/library/02_weekly_analysis.md` — Strength bullet
- [x] `README.md`, `CHANGELOG.md`, tests (`tests/`)

training-architect

- [x] `Core/Models/TrainingPlan.cs` — `WorkoutType.Strength`, `StrengthPhase`
- [x] `Services/TssPlanValidator.cs`, `Core/Models/PlanTssCheckResult.cs`
- [x] `Prompts/plan_week.md`, `plan_next_training.md`, `plan_correction.md`, `assess_week.md`
- [x] `Client/Pages/Coach.razor` (plan editor), `Client/Components/MetricsSnapshot.razor` (Strength card)

Suggested order: taxonomy + schema → data preparation → check/validate →
coach-logic docs → prompts → frontend. Each step is independently testable.

---

## 7. Decisions

- **D1 — Phase source**: 16-week strength history built internally by `prepare_week_data` and exported only as the derived `week_summary.strength` plus metadata on activities already in the export window; a canonical tag on the completed activity always wins, so athletes can override the phase by tagging; a chat statement overrides for the target week; no calendar-based fallback.
- **D2 — Frequency and readiness scope**: AA/MT/MS target 2 sessions/week, reduced to 1 only for high-risk form/clearly negative starting TSB or a consistent one-session completion pattern; RECOVERY weeks do not reduce strength frequency or phase dose. SM remains 1/week. Same-day readiness limits sessions only for next-best-training today and current-week plan dates today/tomorrow (yellow: no maximum; red: no strength). Next-week plans ignore readiness. In RECOVERY weeks, schedule strength only from day 4 onward.
- **D3 — Frontend**: `WorkoutType.Strength` with phase, own card, excluded from the Ride TSS indicator.
- **D4 — Legacy tag `strength`**: ignored.
- **D5 — Tag fallback**: canonical completed tags win; otherwise inherit canonical tags from a same-date planned WeightTraining event (`planned`), then the closest planned WeightTraining event in the same ISO year/week (`planned_week`). Equal-distance ties prefer the earlier date; planned-event matching never crosses weeks. Without a planned match, inherit the phase of the latest earlier `activity`/`planned`/`planned_week` session if the gap is < 21 days (`inferred`, including across weeks). Inferred sessions count toward the run but never anchor further inference. Before the first resolved session or at a gap ≥ 21 days use `none`. `phase_overdue` flags counts above 6/3/12 without changing phase. The coach tags planned events; manual tagging of completed sessions is optional.
- **D6 — RPE for strength**: optional; no reminder when missing. The data quality check excludes WeightTraining from the RPE and carbohydrate completeness checks.
- **D7 — Strength planning on by default**: disabled only by the selector value "No strength training" or a chat statement. Athletes without history start with adaptation (Build/Peak: 1 session per week until the next Base phase).
- **D8 — Deterministic phase**: the phase per week is computed in Python (advance at the phase minimum, cycling-phase guard) and supplied to the coach; the coach only decides frequency (within the recommended number) and placement. A manual phase in the selector overrides it and stays until changed back to Automatic. Athletes with external programs (e.g. EGYM) select the matching phase manually or tag completed sessions.

---

## 8. Open items

- Program presets (e.g. EGYM Muskelaufbau with 6 sessions per phase) were considered and dropped: few users would need them, and the manual phase selection (D8) covers the case. Mapping for reference: Robustheit → `strength-adaptation`, Muskelaufbau → `strength-transition`, Maximalkraft → `strength-maximum`, second Muskelaufbau → `strength-transition` (https://kraftradar.de/training/egym-muskelaufbauprogramm-phasen/).
- Settings stay client-side only (no per-athlete server storage); users on several devices set the selector per device.