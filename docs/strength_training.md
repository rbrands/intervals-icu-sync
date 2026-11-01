# Strength Training (Joe Friel Muscular Force Model)

Specification for integrating off-bike strength training into intervals-icu-sync (data preparation, coach logic, plan upload) and the training-architect frontend. Based on Joe Friel, *The Cyclist's Training Bible* (5th ed.), summarized in https://joefrieltraining.com/muscular-force-training-for-cycling/.

Status: draft, decisions resolved (see "Decisions" at the end).

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

Friel prescribes 2–3 sessions per week in AA/MT/MS; this project caps at 2 (decision D2) and reduces to 1 on yellow readiness.

Exercise selection per session (3–4 exercises):

1. One or two of: double-leg squat, single-leg squat, deadlift, step-up (optionally explosive "power" step-ups with lighter load), lunge, leg press.
2. Leg curl (muscle balance) — always.
3. Core: front plank, side plank, front plank with rows — some combination every session.
4. Power clean may replace a #1 exercise for experienced lifters only; the coach never prescribes it unless the athlete asks.

1RM estimation (for the description text): perform a set with a load that allows only 4–10 reps and divide by the factor 4→0.90, 5→0.875, 6→0.85, 7→0.825, 8→0.80, 9→0.775, 10→0.75.

### Files to update for the taxonomy

- `coach-logic/interpretation-rules.md` — "Tag taxonomy (canonical source)": add domain `strength` with its own level set; add mapping `strength-* → strength` to "Tag → ride_type mapping" (ride_type `strength` is excluded from all ride-domain counts).
- `foundry-agent/agent.yaml` — tag enumeration: add the four strength tags.
- `src/TrainingArchitect/Prompts/plan_week.md`, `plan_next_training.md`, `plan_correction.md` and the system prompt — wherever canonical domains are listed.
- `contracts/week-plan/week-plan.schema.json` — if tags are enumerated there.
- Library filter tooling (`list_library_workouts`) — accept the new prefix.
- Legacy free-text tag `strength` is ignored (decision D4): it is neither a canonical tag nor counted in the strength history.

---

## 3. Data preparation (intervals-icu-sync)

### 3.1 Activities export

- `scripts/get_activities.py`: include activity type `WeightTraining`.
  Keep such activities whenever intervals.icu supplies `icu_training_load` (same rule as runs; no 20-TSS threshold).
- `scripts/prepare_activities_for_coach.py`: for `WeightTraining` omit all power-, zone-, decoupling-, W'bal-, power-curve-, DFA- and fueling fields.
  Export `id`, `type`, `date`, `name`, `tags`, `duration_hours`, `rpe`, `notes`, `training_load`, `ctl`, `atl`, `form_absolute` and the deltas.
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
4. No resolved tag → `tags: []` and `phase_source: "none"`; the session does not advance any phase counter.

Each internal history row carries `phase_source` (`activity` | `planned` | `planned_week` | `none`) and whether any planned WeightTraining event existed in its week. Only `none` contributes to `untagged_sessions_last_16_weeks`. The coach receives only the derived compact summary, including `tagging_reminder_needed`.

### 3.3 `week_summary.strength`

Derived from `strength_history` (and the current week's activities):

```json
"strength": {
  "current_phase": "maximum",
  "phase_started": "2026-10-13",
  "phase_session_count": 5,
  "phase_target_sessions": "8-12",
  "sessions_this_week": 1,
  "days_since_last_strength": 3,
  "last_session_tags": ["strength-maximum"],
  "weekly_strength_load": 38,
  "sessions_per_week_last_4": [2, 2, 2, 2],
  "untagged_sessions_last_16_weeks": 0,
  "tagging_reminder_needed": false
}
```

- `current_phase`: phase of the most recent tagged session; `null` when the history is empty.
- `phase_session_count`: number of consecutive most-recent sessions carrying the same phase tag (a different phase tag resets the count).
- `phase_started`: date of the first session in that run.
- A gap of ≥ 21 days since the last session resets `current_phase` to `null` (the coach then restarts with AA, see 4.2).
- `sessions_per_week_last_4`: all completed sessions per last four completed ISO weeks, oldest first and aligned with `training_load_history`.
- `untagged_sessions_last_16_weeks`: only sessions whose internal `phase_source` is `none`.
- `tagging_reminder_needed`: true when the current or previous ISO week contains unresolved strength sessions and no planned WeightTraining event existed in that same week. An untagged planned event also suppresses the reminder. Plan text mentions tagging only when this Boolean is true.
- For analysis with `current_phase: null` and `strength_sessions > 0`, describe adaptation as a working assumption, not a finding, and add inside the Strength bullet: "Tag sessions or let the coach plan strength so the phase can be tracked." Never issue a separate warning or missing-RPE reminder.

### 3.4 Load accounting

Current behaviour: `training_load_history` carries the Ride-only sum per sport category from the athlete summary; `week_summary` carries the total of
all exported activities. These two are not directly comparable today, and strength would make the gap visible.

- `week_summary`: keep `total_training_load` (sport-agnostic, CTL-relevant). Add `ride_load`, `run_load`, `strength_load` and matching `ride_time_hours` / `run_time_hours` / `strength_time_hours` and session counts, computed from `activities[]`.
- `achievement_pct` in `week_summary` is computed from `ride_load`, so the current week matches `training_load_history`.
- `training_load_history`: unchanged.
- `check_plan_tss` (local and MCP): sum only entries whose `activity_type` is a ride type (`Ride`, `VirtualRide`, `MountainBikeRide`, `GravelRide`
  or absent). `Run*` and `WeightTraining` entries are listed in the result but excluded from `week.total_tss`.
- `coach-logic/input-schema.md`: correct the `week_summary` description (total of exported activities, not Ride-only) and document the new fields.

---

## 4. Coach logic

### 4.1 `coach-logic/workout-library.md` — new section "Strength (off-bike)"

Four entries, one per phase, with the table from section 2 as the "structure" column, the exercise selection rules, and a fixed description template:

```
Phase: <AA|MT|MS|SM> (session <n> of <target>)
Exercises: <1–2 primary> + leg curl + core
Sets × reps @ % 1RM: <from table>
Rest: <from table>
Notes: <progression hint, e.g. "add 2.5 kg if all sets completed">
```

No `steps`; `activity_type: WeightTraining`; `tss` = planned RPE-based load as intervals.icu will compute it (duration × RPE model), stated for
information only.

### 4.2 `coach-logic/decision-process.md` — new section "Strength"

Phase selection, in priority order:

1. Explicit athlete statement in the chat ("start max strength", "skip gym this week") wins for the target week.
2. `week_summary.strength.current_phase` with its counter:
   - `adaptation` and count ≥ 4 → may advance to `transition` (must at 6).
   - `transition` and count ≥ 2 → may advance to `maximum` (must at 3).
   - `maximum` and count ≥ 8 → may advance to `maintenance` (must at 12).
   - `maintenance` → stays.
3. Cycling-phase guard (from `training_plan[].phase`):
   - `Base` → any phase allowed; `maximum` only here.
   - `Build`, `Peak` → `maintenance` only; an unfinished `maximum` run is cut short and the coach says so in the plan text.
   - `Transition` → no strength, or restart with `adaptation` if the athlete asks.
   - No phase supplied → treat as Base (existing rule).
4. No history (`current_phase: null`) and Base → start with `adaptation`.

Frequency (decision D2):

- AA / MT / MS: 2 sessions per week; 1 when `training_readiness` is yellow; 0 when red. Maintain the MS counter across a reduced week (it counts sessions, not weeks).
- SM: 1 session per week.
- RECOVERY week type: at most 1 session, never `maximum`.
- RACE week: SM only, not within 3 days before the race.

Placement:

- Strength may share a day with a ride (exception to the one-workout-per-day rule, see 4.3). Preferred: after an easy/aerobic ride or on the rest day. Allowed: after a threshold session (same day). Never on the day of or the day before a VO2max session during `maximum`; never the day before the long ride during `maximum`.
- Never two strength sessions on consecutive days.
- `maximum` counts as a hard session for the "never two hard days in a row" rule; `adaptation`, `transition`, `maintenance` do not.

Fatigue inference: the existing rule in `prompts/discipline_fitness.md` ("assume unseen off-bike load") is removed; strength load is now visible.

### 4.3 Plan prompts

- `plan_week.md`, `plan_correction.md`, system prompt: change "at most one workout per calendar day" to "at most one ride and at most one `WeightTraining` entry per calendar day"; never two rides.
- Weekly load guardrail: compare the sum of ride entries only against `weekly_load_target`; strength entries never count toward it and are never added to reach it.
- Upload JSON: strength entries use `activity_type: "WeightTraining"`, no `steps`, exactly one `strength-<phase>` tag, description from the template in 4.1.
- `prompts/discipline_fitness.md`: replace "recommend 2 strength sessions per week in prose; never emit them in the upload JSON" with "emit strength sessions per decision-process.md, Strength".
- `prompts/library/02_weekly_analysis.md`: add a "Strength" bullet (phase, sessions done vs. planned, placement quality relative to key sessions).

### 4.4 Validation

- `validate_week_plan`: `WeightTraining` entries require `tags` with exactly one `strength-*` tag, `duration_minutes` 30–75, no `steps`.
- Reject two `WeightTraining` entries on the same day and `WeightTraining` on a `training_allowed: false` day (existing rule applies).

---

## 5. training-architect (frontend, decision D3)

- `TrainingArchitect.Core/Models/TrainingPlan.cs`: add `WorkoutType.Strength` and an optional `StrengthPhase` (enum `Adaptation, Transition, Maximum, Maintenance`) on `PlannedWorkout`.
- Plan card: own icon, phase label, sets/reps line from the description; TSS shown but excluded from the weekly Ride TSS indicator.
- `PlanTssCheckResult` consumer: strength rows displayed, not summed.
- Week overview: a small "Strength: MS 5/8–12" badge fed by `week_summary.strength`.
- DTO/schema regeneration for the new `week_summary.strength` and `strength_history` fields.

---

## 6. Affected files (checklist)

intervals-icu-sync

- [ ] `scripts/get_activities.py` — include `WeightTraining`
- [ ] `scripts/prepare_activities_for_coach.py` — strength field set,
      `is_hard_session`, `strength_history`, `week_summary.strength`,
      per-sport load breakdown, `achievement_pct` on `ride_load`
- [ ] `src/intervals_icu/client.py` — events fetch with type filter for the
      16-week strength history
- [ ] `src/intervals_icu/week_data_schema.py` — new models
- [ ] `scripts/check_plan_tss.py` / MCP `check_plan_tss` — ride-only sum
- [ ] `scripts/validate_week_plan.py` + `contracts/week-plan/*.schema.json`
- [ ] `coach-logic/interpretation-rules.md` — taxonomy, mapping
- [ ] `coach-logic/workout-library.md` — Strength section
- [ ] `coach-logic/decision-process.md` — Strength section
- [ ] `coach-logic/input-schema.md` — new fields, corrected `week_summary` text
- [ ] `coach-logic/coaching-principles.md` — one paragraph on muscular force
- [ ] `prompts/discipline_fitness.md` (and other discipline files) — strength rule
- [ ] `prompts/system_prompt.md`, `foundry-agent/agent.yaml` — tags, one-per-day rule
- [ ] `prompts/library/02_weekly_analysis.md` — Strength bullet
- [ ] `README.md`, `CHANGELOG.md`, tests (`tests/`)

training-architect

- [ ] `Core/Models/TrainingPlan.cs` — `WorkoutType.Strength`, `StrengthPhase`
- [ ] `Prompts/plan_week.md`, `plan_next_training.md`, `plan_correction.md`
- [ ] plan card / week overview components, DTOs

Suggested order: taxonomy + schema → data preparation → check/validate →
coach-logic docs → prompts → frontend. Each step is independently testable.

---

## 7. Decisions

- **D1 — Phase source**: strength history (16 weeks of tagged
  `WeightTraining` events) exported by `prepare_week_data`; chat statement overrides; no calendar-based fallback.
- **D2 — Frequency**: max 2 sessions/week in AA/MT/MS, 1 on yellow readiness, 0 on red; 1/week in SM.
- **D3 — Frontend**: `WorkoutType.Strength` with phase, own card, excluded from the Ride TSS indicator.
- **D4 — Legacy tag `strength`**: ignored.
- **D5 — Tag fallback**: canonical completed tags win; otherwise inherit canonical tags from a same-date planned WeightTraining event (`planned`), then the closest planned WeightTraining event in the same ISO year/week (`planned_week`). Equal-distance ties prefer the earlier date; no cross-week fallback. Without a match use `none`. The coach tags planned events; manual tagging of completed sessions is optional.