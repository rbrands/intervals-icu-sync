Discipline: Fitness / Health (no race goal)

## Athlete Goal
- Maintain and slow the age-related decline of VO2max, FTP, and muscle mass
- Build and preserve aerobic fitness for long-term health
- Train consistently year-round without injury or burnout
- No target event; progress is measured by periodic benchmark tests
  (FTP or 5-min test every 8–12 weeks)

## Training Focus Priority
1. VO2max maintenance (declines fastest with age)
2. Aerobic base (steady Z2 volume, metabolic health, durability)
3. Threshold (supporting; keeps FTP from drifting down)

## Weekly Emphasis
- mandatory: 1 VO2max session, 1 longer Z2 ride (1.5–3 h)
- secondary: 1 threshold or sweet-spot session; replace it with an
  additional Z2 ride in weeks with elevated fatigue
- 3–5 ride sessions per week; at least 1 full rest day
- never two hard sessions on consecutive days
(guides the weekly requirements in decision-process.md)

## Discipline-Specific Rules (CRITICAL)
- consistency beats any single session: never compensate a missed
  session by adding it on top of the following week
- keep CTL within a stable maintenance band; do not chase ramp rate
- keep form between grey_zone and optimal; treat high_risk as an error,
  not as a productive overreach
- the long ride is a durability minimum (1.5–3 h), not a volume builder;
  do not extend beyond 3 h unless the athlete explicitly asks
- vary structures across weeks (different VO2max and threshold formats
  from the library, within the dose level set by decision-process.md)
  to avoid monotony and overuse
- treat any RACE_A / RACE_B entry as RACE_C unless the athlete explicitly
  declares it a goal: it replaces the week's comparable intensity and
  never triggers a taper
- recommend 2 strength sessions per week in prose (lower body, core,
  not on VO2max days); never emit them in the upload JSON
- if wellness signals show fatigue not explained by ride load, assume
  unseen off-bike load (strength, running, other sports): choose the more
  conservative option for that week and state this assumption in the
  response; do not ask the athlete

## Phase Interpretation
Overrides the generic phase actions in decision-process.md for this profile:
- Base / Build: apply standard periodization (2 weeks load + 1 recovery)
- Peak: NO taper. Treat as a benchmark week — hold volume, replace one
  key session with an FTP or 5-min test, then return to Base
- Transition: keep short (1–2 weeks); maintain one VO2max stimulus if
  the athlete is 50+
- external plans: follow phase labels and load targets, ignore taper logic

## Discipline Workouts
- VO2max formats rotated across the library (30/30, 5×2, 4×4)
  → tag vo2max-<level>
- sweet spot / threshold formats from the library (3×10, 2×20)
  → tag lactate-threshold-<level>
- steady Z2 1.5–3 h with light fueling practice
  → tag aerobic-threshold-<level>
