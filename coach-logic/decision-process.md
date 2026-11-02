# Decision Process

How the coach turns interpreted data into concrete weekly training
actions. Used only when generating or adjusting a plan or workouts.

Builds on (never restates):
- interpretation-rules.md — form, decoupling, fueling, limiter detection
- training-zones.md — zone definitions; all intensities reference these
- the athlete/discipline block — goal-specific session emphasis
- workout-library.md — concrete interval structures to select from

---

## Decision Hierarchy

Resolve conflicts in this order:
1. Athlete safety and recovery (fatigue, HRV)
2. Existing planned workouts
3. Weekly structure requirements (per goal, limiter, phase)
4. Primary performance limiter
5. Training phase

---

## Step-by-Step Process

1. **Read state** — use interpretation-rules.md for form zone, recovery,
   training readiness, durability, and fueling status. Do not re-derive thresholds.
2. **Inventory completed workouts** — which key sessions are done
   (VO2max, threshold, long ride)? Note high RPE, declining power, high decoupling.
3. **Evaluate planned workouts (CRITICAL)** — they take precedence.
   Do NOT duplicate a key session already planned or completed. Adjust a
   planned session only if fatigue is too high or it clearly mismatches state.
4. **Determine weekly requirements** — from goal/discipline emphasis and
   the primary limiter, decide which key sessions are still missing.
   Schedule only those.
   Determine strength requirements alongside ride key sessions per "Strength" below.
5. **Combine limiter + fatigue → stimulus**
   - fresh + clear limiter → add stimulus in the limiter domain
   - optimal fatigue + limiter → continue structured progression
   - persistent high fatigue from form / CTL-ATL / history → reduce intensity,
     prioritize recovery, keep frequency if possible
6. **Apply phase** (if no phase is provided, apply Base)
   - Base → volume, limit high intensity
   - Build → VO2max + threshold, moderate–high intensity
   - Peak → reduce volume, maintain intensity, increase specificity
   - Transition → recovery, maintain basic fitness

---

## Session Decision Rules

### Training readiness
- Readiness (`week_summary.training_readiness`) is a same-day signal, not a
  multi-day forecast. Scope it by planning mode:
  - **Next best training:** apply it fully to today's session.
  - **Current-week plan:** apply it only to today and tomorrow. For later days,
    use form zone, CTL/ATL trend, `week_type`, and `training_load_history`.
  - **Next-week plan:** ignore readiness entirely and never cite today's
    readiness as a reason to choose or reduce a session.
- Within its applicable window, green permits the planned hard session when
  subjective readiness is also good; it does not justify adding another hard
  session. Yellow requires checking subjective recovery and may modify a
  session on a date within the applicable window. Red excludes hard training
  on that date; prioritize recovery or an easy session. Preserve applicable
  same-day safety vetoes.
- Unknown readiness requires manual assessment before prescribing intensity.
  Low-confidence readiness is never definitive clearance. Neither unknown nor
  low confidence should extend readiness influence beyond its planning window.

### Recovery week structure
When `week_type` is `RECOVERY`, use this two-part structure, based on
[Joe Friel's recovery-week design](https://joefrieltraining.com/recovery-week-design/):

- **Days 1–3 (Monday–Wednesday):** Schedule at most two short, low-intensity
  sessions (Z1, `recovery-low`, or `aerobic-threshold-low`) and at least one
  full rest day. Scale "short" to the athlete's weekly volume; at 6 hours per
  week, use about 20–30 minutes. No key sessions.
- **Days 4–6 (Thursday–Saturday):** Schedule two or three short, moderate- to
  high-intensity sessions at or slightly above race intensity, such as short
  intervals, speed skills, or a field test. For athletes 50+, place the
  weekly VO2max session here at low dose (`vo2max-low`). If a benchmark test
  is due per the discipline block (for example FTP or a 5-minute test every
  8–12 weeks), schedule it here instead of an interval session.
- **Day 7:** Rest or a short easy spin before the next load block.
- Use the reduced `weekly_load_target` from intervals.icu as the weekly TSS
  reference; never add volume to reach it. Strength frequency and phase stay
  unchanged, but strength sessions are scheduled only from day 4 onward.
- Name the week as a recovery week in the plan text and explain the two halves
  in one sentence.

### VO2max (CRITICAL — age rule)
- Athletes 50+: exactly 1 VO2max session per week, in ALL phases, unless
  replaced by an equivalent high-intensity stimulus (race/event), or
  already completed/planned (then do NOT duplicate).
- Dose by form_pct (value from interpretation-rules.md):
  - form_pct < -20%        → vo2max-low      (30/15, 6–8×1 min)
  - -20% ≤ form_pct ≤ -10% → vo2max-moderate (5×2 min)
  - form_pct > -10%        → vo2max-high     (4×4, 5×3 min)
- A next-week plan follows form zone, ramp, `week_type`, and
  `training_load_history`; never reduce VO2max dose because of today's
  `training_readiness`.

### Threshold
When FTP is the limiter, in Build phase, or when fatigue allows sustained
efforts. Typical: 2×12, 3×8, over/unders.
For next-week plans, use form zone, ramp, `week_type`, and
`training_load_history`; never reduce threshold dose because of today's
`training_readiness`.

### Long ride
When durability is the limiter or weekly structure needs it. ≥ 2–4 h,
steady aerobic pacing, fueling mandatory (below).

### Endurance / Recovery
- Endurance: fill weekly volume, maintain aerobic base.
- Recovery: when fatigue high, HRV low, or after key sessions.
- Embedded sprints (workout-library.md): may be added to one Z2 ride per
  week in the first hour when the athlete is not in high fatigue. They do
  not count as a key session and do not change the ride's tag.

### Race-specific
For criterium / road-race / cyclocross / Zwift-racing goals (discipline
block). Select breakaway sets (Z6 + Z4), criterium microbursts (Z6 + Z2),
standing starts (Z7), or the Zwift race start (Z6 → Z4) from
workout-library.md.
Breakaway sets use full recovery between sets; microbursts use incomplete
recovery within a block and full recovery between blocks; standing starts
use full recovery between every effort; the Zwift race start has no
recovery between its Z6 opening and the Z4 block.
Use one or more "race-specific-<level>" tags; downstream logic derives the
race classification from those tags.

### Upcoming races
- Inspect `planned_workouts.current_week.race_events` and
   `planned_workouts.next_week.race_events` before placing any session.
- Never schedule another workout on a race date. The race itself is the key
   session and replaces an equivalent high-intensity stimulus.
- `RACE_A`: protect the event with a taper; reduce volume and fatigue while
   retaining only enough short intensity to preserve sharpness.
- `RACE_B`: reduce conflicting fatigue and arrive reasonably fresh without
   overriding the primary season goal.
- `RACE_C`: treat as a supported training race; replace the week's comparable
   intensity rather than adding it on top.
- A completed race without a calendar entry (identified per the discipline
   block, e.g. a Zwift race recognised from the activity name or load) is
   treated as `RACE_C` after the fact: it has already consumed the week's
   comparable hard session. Remove that session from the remaining week.

---

## Strength

### Phase selection (in priority order)

1. Opt in only when the athlete explicitly asks for strength in chat or shows
   strength activity. Activity is indicated by any of:
   `sum(week_summary.strength.sessions_per_week_last_4) > 0`,
   `week_summary.strength.phase_session_count > 0`, or
   `week_summary.strength.untagged_sessions_last_16_weeks > 0`.
   An explicit request to skip strength means do not plan it for the requested
   period. Without an opt-in, do not plan or mention strength; in analysis,
   skip the Strength block entirely.
2. Read `week_summary.strength.current_phase` and `phase_session_count`:
   - `adaptation` and count >= 4: may advance to `transition`; must at 6.
   - `transition` and count >= 2: may advance to `maximum`; must at 3.
   - `maximum` and count >= 8: may advance to `maintenance`; must at 12.
   - `maintenance`: stays.
3. Apply the cycling-phase guard from the target-week entry in
   `week_summary.training_plan[].phase`:
   - Prep / early Base: adaptation or transition; maximum only in Base.
   - Base: any strength phase allowed; maximum only here.
   - Build / Peak: maintenance only. Cut short an unfinished maximum run
     and explain this in the plan text.
   - Transition: no strength, or restart with adaptation if the athlete asks.
   - No cycling phase supplied: treat as Base.
4. With strength activity but `current_phase: null`, use adaptation as a
   working assumption, not a finding. A gap of at least 21 days since the
   last strength session resets phase state; use the supplied summary, not a
   reconstructed raw history.

### Frequency

- AA / MT / MS: target 2 sessions per week. Reduce to 1 only when form zone is
  `high_risk` (or TSB is clearly negative at plan start), or
  `sessions_per_week_last_4` shows the athlete consistently completes only
  one. Maintain the MS counter across a reduced week: it counts sessions, not
  weeks.
- SM: 1 session per week, unchanged.
- Only for next-best-training today and dates today/tomorrow in a current-week
  plan, yellow readiness excludes a `maximum` strength session on that date
  and red excludes strength on that date. This same-day limit does not reduce
  weekly frequency. For next-week plans, ignore readiness entirely.
- RECOVERY weeks reduce endurance load only. Keep the normal strength
  frequency and current phase dose/tag: 2 sessions in adaptation, transition,
  or maximum; 1 in maintenance. Sessions count toward phase progression and
  phase advancement follows the usual thresholds. Do not schedule strength in
  the first three days of a RECOVERY week; schedule it only from day 4 onward.
- RACE week: maintenance only, not within 3 days before the race.
- Apply the most restrictive weekly phase/week/form rule. Assess unknown or
  low-confidence readiness only for decisions within its applicable
  planning-mode window.
- Count completed and anchored planned strength sessions toward the frequency;
  do not duplicate them. Use `sessions_this_week` for the current week and
  `sessions_per_week_last_4` as context, not as missed sessions to make up.

### Placement

- At most one ride and at most one WeightTraining entry per calendar day.
  Never two rides; one ride plus one strength session is allowed.
- Place each strength session on the first feasible slot in this ranked order:
  1. A day with no ride (rest day).
  2. A day with an easy aerobic or recovery ride, after the ride.
  3. A day with a threshold session, after the ride.
- Never place strength on a long-ride day, VO2max day, or race day. Never
  schedule strength on consecutive days; leave at least two calendar days
  between strength sessions.
- An athlete's explicit preference naming strength days overrides the ranked
  order, but not the no-long-ride/VO2max/race-day exclusions, spacing rules,
  safety constraints, or calendar availability.
- Name the chosen strength days and the reason in one sentence. Ensure the
  plan-text daily list is generated from the final upload JSON so the dates
  and strength entries match exactly.
- Maximum counts as hard for the "never two hard days in a row" rule;
  adaptation, transition, and maintenance do not. Preserve full rest days,
  race protection, and `training_allowed: false` constraints.

### Load and time accounting

- Strength load is visible in `week_summary.strength` but is informational
  only, whether HR- or RPE-derived. Phase and frequency come from tags and dates.
- Weekly TSS and hours guardrails compare rides only: Ride, VirtualRide,
  MountainBikeRide, GravelRide; absent or null `activity_type` counts as Ride.
  Use completed `ride_load` and `ride_time_hours`, never Ride+Run combined
  totals. Strength and running never fill the weekly Ride target.
- `weekly_time_target_hours` is a Ride-only upper budget. On LIMITED days,
  `max_training_time_hours` caps the sum of ALL entries on that date,
  including WeightTraining; no entry on unavailable days.
- Emit strength entries using "Strength (off-bike)" in workout-library.md:
  exactly one phase tag, phase-table duration, fixed description, no steps
  or library ID, and numeric informational `tss`.

### Untagged sessions

- `week_summary.strength.tagging_reminder_needed` (true when the current or
  previous ISO week has completed strength sessions with phase source `none` or `inferred`
  and no planned WeightTraining event existed in that same week) is surfaced by
  the data quality check (`check_athlete_data`, area `strength_untagged`), which
  lists the affected exported activities. For unresolved sessions it suggests
  a tag; for inferred sessions it reports the counted phase and asks for a tag
  only if that phase was different. The coach does not read it
  for coaching and never mentions tagging in plans or analyses.
- Same-date planned tags take precedence over the nearest same-ISO-week
  planned tags; both resolve the phase. Do not infer tagging gaps from the
  16-week untagged count or phase age.
- For analysis requests with `current_phase` null and
  `week_summary.strength_sessions > 0`, name adaptation as a working assumption,
  not a finding, inside the Strength bullet. Do not add a tagging sentence or
  a separate warning.
- Never mention missing RPE.

---

## W' Actions

Acting on the W' signals from interpretation-rules.md:
- long ride, W' drop > 20% → prescribe reduced early intensity, protect aerobic base
- aerobic ride, usage > 15% → reduce variability/peaks in the next prescription
- event with key effort upcoming → ride conservatively in the lead-up,
  keep W' drop < 30% before the key effort

---

## Fueling Integration

Decisions modified by fueling status (from interpretation-rules.md):
- low fueling → resolve nutrition before increasing load
- good fueling + optimal form → proceed with key sessions
- low fueling + high fatigue → reduce intensity AND increase carbs
- long ride done without fueling → correct fueling before reading performance

Session fueling strategy (write into the workout description):
- VO2max: optional if < 1.5 h; small intake may improve quality
- Threshold: light fueling improves repeatability
- Long ride: strict — 80–90 g/h, start within 30 min, steady every
  15–30 min, combine liquid + solid

---

## Weekly Planning Logic

- Early week (Mon–Wed): execute key sessions (VO2max / threshold)
- Mid week (Thu–Fri): adjust by fatigue, avoid overload; from Thursday,
  begin planning next week
- Late week (Sat–Sun): long ride or event; prioritize quality and fueling

---

## Load Management

- Increase load only if fatigue is low/optimal AND fueling is adequate.
- Reduce load if fatigue is high, HRV is low, or performance is declining.
- Use `training_load_history` to distinguish a one-week outlier from a repeated
  pattern of over- or under-achieving weekly Ride load targets.
- Treat the four-week history as secondary context. Current form, ATL, HRV,
  recovery, and performance signals take precedence.
- Never compensate for missed historical load by adding it to the current or
  next week.
- The weekly time target (hours) is a Ride-only upper bound: completed plus
  planned ride durations in that week must not exceed it. LIMITED-day caps
  sum ALL sessions on the date, including strength and running.
- The weekly load target (TSS) is the planning reference: completed plus
  planned Ride load in that week should be within ±10% of it (matching the
  `check_plan_tss` default tolerance). Go further below
  only when safety rules (readiness, fatigue) or repeated historical
  over-/under-achievement together with current readiness justify a safer
  week. Never add intensity solely to reach it.
 
---

## Training Environment (indoor / outdoor)

Decide per workout how it will most likely be ridden. This drives the
`activity_type` field and the step model in "Workout Modeling" below.

1. An explicit statement by the athlete in the chat wins and applies to the
   whole plan unless it names specific days.
2. Otherwise read `activities[].type` in the input window (default 7 days):
   - ≥ 2 rides and the majority are `VirtualRide` → indoor default
   - ≥ 2 rides and the majority are `Ride` or other outdoor ride types
     → outdoor default
   - fewer than 2 rides → outdoor default
3. The default applies to every planned ride, including long rides and
   recovery rides; there are no per-type exceptions.

Set `activity_type` accordingly: `VirtualRide` for indoor; omit the field
(= `Ride`) for outdoor. When the default was derived from data rather than
stated by the athlete, name it in one sentence in the plan text so the
athlete can correct it. Do not ask.

---

## Workout Modeling

- `activity_type: VirtualRide` → detailed steps (warmup, intervals,
  recovery, cooldown)
- WeightTraining → no steps; use the Strength (off-bike) description template.
- outdoor (`Ride`) → simplified, max 3–5 steps (warmup, main, optional key
  effort, cooldown); embedded sprints go into the description, not into steps
- Event → exactly one key effort; may replace a structured session
- Prefer physiological accuracy over fragmentation
- Select concrete structures from workout-library.md; all intensities use
  training-zones.md

---

## Key Principle

Every decision balances training stimulus against recovery capacity:
enough stress to drive adaptation, without exceeding the ability to recover.
