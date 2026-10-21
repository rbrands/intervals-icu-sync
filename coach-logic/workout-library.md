# Workout Library

A catalog of concrete interval structures, grouped by training domain and
dose level (high / moderate / low). The coach selects from this library
when generating a plan.

- Selection logic (which domain, which dose, when) is in decision-process.md.
- All intensities reference the zones in training-zones.md — this file
  names zones (Z1–Z7), never FTP percentages.
- Tags follow the canonical taxonomy in interpretation-rules.md.
  Every workout carries one or more "`<domain>-<level>`" tags.
- The structures below are MAIN SETS; warmup and cooldown are added per
  the modeling rules in decision-process.md.

Dose levels:

- High → strong stimulus
- Moderate → standard session
- Low → reduced load / fatigue management


## VO2max (Z5)

| Dose     | Structure                                     | Tag |
| -------- | --------------------------------------------- | --- |
| High     | 5×2.5 min (2.5 min rec) / 5×3 min (3 min rec) | vo2max-high |
| Moderate | 6×1.5 min (1.5 min rec) / 5×2 min (2 min rec) | vo2max-moderate |
| Low      | 10×30 s (30 s rec) / 7×1 min (1 min rec)      | vo2max-low |

Work in Z5; recovery in Z1.


## Threshold (Z4)

| Dose     | Structure                                  | Tag |
| -------- | ------------------------------------------ | --- |
| High     | 3×12 min (3:15 rec) / 2×20 min (5 min rec) | lactate-threshold-high |
| Moderate | 3×8 min (2:30 rec) / 3×10 min (3 min rec)  | lactate-threshold-moderate |
| Low      | 3×5 min (90 s rec) / 3×6 min (2 min rec)   | lactate-threshold-low |

Work in Z4 (sweet spot to threshold); recovery in Z1. Over/unders may add
brief Z5 spikes.


## Aerobic Threshold / Long Ride (Z2)

| Dose     | Structure        | Tag |
| -------- | ---------------- | --- |
| High     | 2–4 h continuous | aerobic-threshold-high |
| Moderate | 1–2 h steady     | aerobic-threshold-moderate |
| Low      | 30–60 min easy   | aerobic-threshold-low |

Steady Z2 (upper Z2 preferred for performance gains). Avoid early Z3 spikes
on long rides to protect durability.

### Embedded Neuromuscular Sprints (Z7, within a Z2 ride)

Short maximal sprints placed in the first hour of an endurance ride.
Not a separate session: the ride keeps its aerobic-threshold tag and its
Z2 character, the sprints are a small neuromuscular stimulus that also
breaks the monotony of a base ride. Two variants:

| Variant | Effort | Energy system | Recovery between | When |
| ------- | ------ | ------------- | ---------------- | ---- |
| K1 | 6 s, standing or flying start, maximal cadence | alactic (ATP-CP) | 3 min Z2 | year-round |
| K2 | 20 s, standing or flying start, maximal cadence | lactic | 4–5 min Z2 | late Base, Build, race season |

| Dose     | K1          | K2          |
| -------- | ----------- | ----------- |
| High     | 8×6 s       | 6×20 s      |
| Moderate | 6×6 s       | 4×20 s      |
| Low      | 4×6 s       | 3×20 s      |

Rules:
- Tag stays `aerobic-threshold-<level>` of the host ride; the dose above
  is independent of the tag level, which is set by ride duration.
- Vary gearing between sprints (heavy / light); seated and standing.
- Place after at least 15 min of Z2 warmup; stop the set when peak power
  or cadence drops noticeably — quality over quantity.
- Z7 steps use the nominal power value defined in training-zones.md and the
  description must say "maximal effort". The TSS contribution is small
  (well under 10 TSS per set); this is intended and no reason to add load.
- Indoor (`VirtualRide`): model the sprints as explicit steps. Outdoor: keep
  the simplified step model and describe the sprint set in the description so
  the athlete can pick safe, suitable road sections.



## Race-Specific / Breakaway (Z6 + Z4)

Simulates sprint / attack / breakaway repeatability for road races and
criteriums. Hard anaerobic effort (Z6) immediately followed by threshold
consolidation (Z4). Full recovery (Z1) between sets, not partial.

| Dose     | Structure                                            | Tag |
| -------- | ---------------------------------------------------- | --- |
| High     | 4×(2 min Z6 + 3 min Z4), 5 min full rec between sets | race-specific-high |
| Moderate | 3×(2 min Z6 + 3 min Z4), 5 min full rec between sets | race-specific-moderate |
| Low      | 2×(2 min Z6 + 3 min Z4), 5 min full rec between sets | race-specific-low |


## Race-Specific / Criterium Microbursts (Z6 + Z2)

An alternative to the breakaway sets above for repeated short attacks and
accelerations out of corners. Each repetition pairs 15 s in Z6 with 45 s
in Z2: incomplete recovery within a block, full recovery in Z1 between
blocks.

| Dose     | Structure                                             | Tag |
| -------- | ----------------------------------------------------- | --- |
| High     | 3×8×(15 s Z6 + 45 s Z2), 5 min Z1 between blocks | race-specific-high |
| Moderate | 2×8×(15 s Z6 + 45 s Z2), 5 min Z1 between blocks | race-specific-moderate |
| Low      | 2×5×(15 s Z6 + 45 s Z2), 5 min Z1 between blocks | race-specific-low |

These are controlled anaerobic efforts, not all-out Z7 sprints. Preserve
repeatable power and technique; reduce the number of repetitions or stop
the block if either deteriorates.

Select this structure for criterium attack repeatability, not as an
additional mandatory session. Dose and placement follow decision-process.md.
A short work/recovery format alone does not determine the training domain:
Z5 intervals targeting aerobic capacity use vo2max-<level> tags; these Z6
attack-repeatability blocks use race-specific-<level> tags. Do not assume
they replace the required VO2max session solely because they are microbursts.

For cyclocross, ride the bursts from low cadence / low speed to mimic
accelerations out of corners and after obstacles.


## Race-Specific / Standing Starts (Z7)

Simulates the race start in cyclocross and criterium: a maximal effort
from a standing or near-standing start. Z7 is neuromuscular; quality
collapses quickly, so recovery between efforts is full (Z1) and the
set ends as soon as peak power drops noticeably.

| Dose     | Structure                        | Tag |
| -------- | -------------------------------- | --- |
| High     | 8×30 s Z7, 5 min Z1 between      | race-specific-high |
| Moderate | 6×20 s Z7, 4 min Z1 between      | race-specific-moderate |
| Low      | 4×15 s Z7, 4 min Z1 between      | race-specific-low |

Place after a thorough warmup with 2–3 short Z5 primers. Not a VO2max
substitute: the total work time is too short for an aerobic stimulus.
Z7 steps use the nominal power value defined in training-zones.md.
For the embedded, non-race variant of short sprints see "Embedded
Neuromuscular Sprints" above.


## Race-Specific / Zwift Race Start (Z6 → Z4)

Simulates the opening of a Zwift race: the group sorts itself in the
first 1–3 minutes at Z6 from rolling speed, then the pace settles just
below or at threshold with no coasting. The Z4 block follows the Z6
opening immediately, without recovery; recovery (Z1) comes only between
repetitions.

| Dose     | Structure                                        | Tag |
| -------- | ------------------------------------------------ | --- |
| High     | 2×(2 min Z6 + 15 min Z4), 8 min Z1 between       | race-specific-high |
| Moderate | 2×(90 s Z6 + 10 min Z4), 8 min Z1 between        | race-specific-moderate |
| Low      | 1×(90 s Z6 + 10 min Z4)                          | race-specific-low |

Z4 block at threshold (95–100% FTP), not sweet spot. Ride the Z6 opening
from rolling speed at high cadence — this is not a standing start.
Always `activity_type: VirtualRide` with detailed steps. Description
includes cooling and a pre-race carbohydrate note.



## Recovery (Z1)

| Dose | Structure               | Tag |
| ---- | ----------------------- | --- |
| —    | 30–60 min easy, Z1 only | recovery-low |



## Consistency Rules (CRITICAL)

- Every interval maps to a defined zone (training-zones.md). Do not use
  arbitrary %FTP values outside the zone definitions.
- Interval description, intensity, and tag must be consistent within a workout.
- At least one tag per workout, from the canonical taxonomy.
