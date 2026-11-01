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
   - high fatigue → reduce intensity, prioritize recovery, keep frequency if possible
6. **Apply phase** (if no phase is provided, apply Base)
   - Base → volume, limit high intensity
   - Build → VO2max + threshold, moderate–high intensity
   - Peak → reduce volume, maintain intensity, increase specificity
   - Transition → recovery, maintain basic fitness

---

## Session Decision Rules

### Training readiness
- Green permits the planned hard session when subjective readiness is also good;
   it does not by itself justify adding another hard session.
- Yellow requires checking subjective recovery and reducing, moving, or replacing
   intensity when concerns remain.
- Red excludes hard training; prioritize recovery or an easy session.
- Unknown requires a manual assessment before prescribing intensity.
- Low-confidence readiness must never be presented as a definitive clearance.

### VO2max (CRITICAL — age rule)
- Athletes 50+: exactly 1 VO2max session per week, in ALL phases, unless
  replaced by an equivalent high-intensity stimulus (race/event), or
  already completed/planned (then do NOT duplicate).
- Dose by form_pct (value from interpretation-rules.md):
  - form_pct < -20%        → vo2max-low      (30/15, 6–8×1 min)
  - -20% ≤ form_pct ≤ -10% → vo2max-moderate (5×2 min)
  - form_pct > -10%        → vo2max-high     (4×4, 5×3 min)

### Threshold
When FTP is the limiter, in Build phase, or when fatigue allows sustained
efforts. Typical: 2×12, 3×8, over/unders.

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

1. An explicit athlete statement in the chat ("start max strength", "skip gym
   this week") wins for the target week, subject to safety and recovery.
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
4. No history (`current_phase: null`) and Base: start with adaptation.
   A gap of at least 21 days since the last strength session resets phase
   state; use the supplied summary, not a reconstructed raw history.

### Frequency

- AA / MT / MS: 2 sessions per week; 1 when
  `week_summary.training_readiness.status` is yellow; 0 when red.
  Maintain the MS counter across a reduced week: it counts sessions, not weeks.
- SM: 1 session per week; red readiness excludes strength.
- RECOVERY week: at most 1 strength session, never maximum.
- RACE week: maintenance only, not within 3 days before the race.
- Apply the most restrictive readiness/week rule. Unknown or low-confidence
  readiness requires the existing manual recovery assessment.
- Count completed and anchored planned strength sessions toward the frequency;
  do not duplicate them. Use `sessions_this_week` for the current week and
  `sessions_per_week_last_4` as context, not as missed sessions to make up.

### Placement

- At most one ride and at most one WeightTraining entry per calendar day.
  Never two rides; one ride plus one strength session is allowed.
- Preferred: strength after an easy/aerobic ride or on a ride-rest day.
  Allowed: after a threshold session on the same day.
- During maximum, never place strength on the day of or the day before a
  VO2max session or a long ride.
- Never two strength sessions on consecutive days.
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

### Untagged-session reminder

- In plan text, mention tagging once only when
  `week_summary.strength.tagging_reminder_needed` is true: the current or
  previous ISO week has completed strength sessions with `phase_source: "none"`
  and no planned WeightTraining event existed in that same week. These are
  sessions the coach did not plan. Otherwise never mention tagging in plan text;
  an absent Boolean in an older payload is not evidence for a reminder.
- Same-date planned tags take precedence over the nearest same-ISO-week
  planned tags; both resolve the phase and avoid an untagged-session reminder.
  Do not infer a reminder from the 16-week untagged count or phase age.
- For analysis requests with `current_phase` null and
  `week_summary.strength_sessions > 0`, name adaptation as a working assumption,
  not a finding. Inside the Strength bullet, add one neutral sentence:
  "Tag sessions or let the coach plan strength so the phase can be tracked."
  This is analysis context, not a warning or a separate tagging reminder.
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
