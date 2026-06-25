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
   durability, fueling status. Do not re-derive thresholds.
2. **Inventory completed workouts** — which key sessions are done
   (VO2max, threshold, long ride)? Note high RPE, declining power, high decoupling.
3. **Evaluate planned workouts (CRITICAL)** — they take precedence.
   Do NOT duplicate a key session already planned or completed. Adjust a
   planned session only if fatigue is too high or it clearly mismatches state.
4. **Determine weekly requirements** — from goal/discipline emphasis and
   the primary limiter, decide which key sessions are still missing.
   Schedule only those.
5. **Combine limiter + fatigue → stimulus**
   - fresh + clear limiter → add stimulus in the limiter domain
   - optimal fatigue + limiter → continue structured progression
   - high fatigue → reduce intensity, prioritize recovery, keep frequency if possible
6. **Apply phase**
   - Base → volume, limit high intensity
   - Build → VO2max + threshold, moderate–high intensity
   - Peak → reduce volume, maintain intensity, increase specificity
   - Transition → recovery, maintain basic fitness

---

## Session Decision Rules

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

### Race-specific
For criterium / road-race goals (discipline block). Hard anaerobic effort
(Z6) + threshold consolidation (Z4), full recovery between sets.
Produces ride_type "race", tags include "race-specific-<level>".

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

---

## Workout Modeling

- Structured indoor → detailed steps (warmup, intervals, recovery, cooldown)
- Outdoor → simplified, max 3–5 steps (warmup, main, optional key effort, cooldown)
- Event → exactly one key effort; may replace a structured session
- Prefer physiological accuracy over fragmentation
- Select concrete structures from workout-library.md; all intensities use
  training-zones.md

---

## Key Principle

Every decision balances training stimulus against recovery capacity:
enough stress to drive adaptation, without exceeding the ability to recover.
