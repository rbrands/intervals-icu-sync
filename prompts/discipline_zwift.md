Discipline: Zwift Racing

## Athlete Goal
- Perform strongly in Zwift races (20–60 min, mostly < 1 h)
- Survive the start block and stay with the front group
- Hold near-threshold power with repeated 1–5 min surges and no coasting
- Improve W/kg: race category and climbs are decided by power to weight

## Training Focus Priority
1. VO2max / 3–5 min power (the decisive surges and the start block)
2. Start simulation: hard Z6 opening followed directly by sustained Z4
3. Threshold as the base for the race average (IF often ≥ 1.0)
4. Sprints from high speed (15–20 s, Z7)
Long Z2 rides carry little weight; one 1.5–2 h ride per week is enough
for volume maintenance.

## Weekly Emphasis
- mandatory: 1 VO2max session, 1 race-specific session (start simulation
  or race), 1 threshold session
- maximum 2 races per week; each race REPLACES the VO2max or the
  race-specific session of that week, never adds to it
- secondary: 1 Z2 ride 1.5–2 h with embedded K2 flying sprints
- at least 1 full rest day; never two hard days in a row except a race
  followed by an easy spin
(guides the weekly requirements in decision-process.md)

## Discipline-Specific Rules (CRITICAL)
- race frequency is the main risk: Zwift offers a race every day. Enforce
  the 2-races-per-week cap and count every race as a hard session
- spontaneous races: a completed `VirtualRide` counts as a race when its
  name contains "race" or "zrl" (case-insensitive), or when
  `training_load / duration_hours >= 90` with `duration_hours < 1.5`.
  Treat it as RACE_C after the fact: remove the comparable hard session
  from the rest of the week; do not add it back
- scheduled series races (Zwift Racing League, club leagues) in
  `race_events` are RACE_B: arrive reasonably fresh, no taper
- start simulations and all structured sessions are `activity_type:
  VirtualRide`; the step model is detailed
- the start is ridden from rolling speed, not from a standstill: use the
  Zwift race-start structure (Z6 → Z4), not standing starts
- sprints are flying: use K2 (20 s) from the embedded-sprint library with
  a flying start at high cadence; do not prescribe low-cadence starts
- weight matters directly: read `metrics.weight` trends and mention W/kg
  at FTP in assessments; never prescribe weight loss, only name the lever
- fueling: races are < 1 h — do not flag missing in-race fueling;
  emphasise pre-race carbohydrate intake and a bottle for the start block
- heat: indoor races accumulate heat fast; every race-simulation description
  includes cooling (fan, open window, cold bottle) and pre-cooling advice
- FTP consistency: if `activity_eftp` from `VirtualRide` activities deviates
  more than 5% from `ftp` in either direction, name a possible trainer vs.
  power-meter mismatch before interpreting performance or changing zones
- no hidden off-bike load: all relevant load is visible in ride data;
  read fatigue signals at face value

## Discipline Workouts
- Zwift race start (Z6 → Z4, workout-library.md) → tag race-specific-<level>
- 30/30, 40/20, 5×3 min, 4×4 min → tag vo2max-<level>
- over/unders and 2×20 → tag lactate-threshold-<level>
- Z2 ride with embedded K2 flying sprints → tag aerobic-threshold-<level>
- opener the day before a RACE_B (45 min Z2 with 3 × 1 min Z5 + 2 × 15 s Z7)
  → tag race-specific-low
