Discipline: Cyclocross

## Athlete Goal
- Perform strongly in cyclocross races (40–60 min, Sep–Feb)
- Win the start and hold position through repeated accelerations
- Sustain near-threshold power for 45 min with constant short surges
- Stay fresh across a long season with weekly (often double) race weekends

## Training Focus Priority
1. VO2max (the race engine; sustained high aerobic power)
2. Repeatability of short accelerations from low speed (Z6–Z7)
3. Threshold (supports the 45 min race average)

## Weekly Emphasis
### Race weekend present in race_events
- the race(s) are the key session: they replace the week's VO2max and
  race-specific stimulus; never add either on top
- mandatory: 1 midweek quality session (VO2max OR start/burst repeats,
  alternating weeks), 1 short opener the day before the first race
- secondary: 1 Z2 ride 1.5–2.5 h with a skills block; 1–2 recovery days
- two races on one weekend: Monday is always recovery; the midweek quality
  session is shortened by one dose level
- surrounding volume follows the current phase (Base volume stays Base)

### No race in race_events
- mandatory: 1 VO2max session, 1 threshold session
- secondary: 1 longer Z2 ride (2–3 h), 1 start/burst session in the
  8 weeks before the first race of the season
(guides the weekly requirements in decision-process.md)

## Discipline-Specific Rules (CRITICAL)
- phase and race category are both deliberate athlete inputs: follow them.
  Races in a Base phase are a valid approach (cross as training for the
  road season); keep Base volume and let the race replace the week's
  VO2max stimulus
- the only inconsistency to flag: RACE_A in a Base phase. Do not taper into
  a Base phase; name the conflict in one sentence and treat the race as RACE_B
- start simulation is a distinct stimulus: 20–30 s all-out from a standing
  start (Z7), full recovery (4–5 min) between efforts, quality over quantity
- accelerations are trained with incomplete recovery: short Z6 bursts with
  Z2 (not Z1) between them, as in criterium microbursts, but from low cadence
- expect large W' usage in races; judge repeatability by late-race power
  decline, not by total W' depletion
- fueling: races are < 1 h — do not flag missing in-race fueling; emphasise
  pre-race carbohydrate intake and post-race recovery nutrition instead
- technique (dismount/remount, cornering, run-ups) is embedded as a skills
  block inside the Z2 ride description, never as workout steps
- running load from races and run-ups is not visible in ride data: when
  fatigue exceeds what ride load explains, assume off-bike load, choose the
  conservative option and state the assumption; do not ask the athlete
- two hard days in a row only when they are the two race days of a weekend
- embed K2 sprints (20 s, workout-library.md) into the Z2 ride during the
  8 weeks before the season and in race weeks without a midweek start/burst
  session; K1 (6 s) year-round

## Discipline Workouts
- standing starts (Z7, full recovery) → tag race-specific-<level>
- low-cadence microbursts (Z6 + Z2) → tag race-specific-<level>
- 30/30, 40/20, 5×3 min → tag vo2max-<level>
- opener (45–60 min Z2 with 3 × 1 min Z5 + 2 × 15 s Z7) → tag race-specific-low
- threshold formats (3×10, 2×20), no-race weeks only → tag lactate-threshold-<level>
