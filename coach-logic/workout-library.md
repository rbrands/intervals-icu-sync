# Workout Library

A catalog of concrete interval structures, grouped by training domain and
dose level (high / moderate / low). The coach selects from this library
when generating a plan.

- Selection logic (which domain, which dose, when) is in decision-process.md.
- All intensities reference the zones in training-zones.md — this file
  names zones (Z1–Z7), never FTP percentages.
- Tags follow the canonical taxonomy in interpretation-rules.md.
  Every workout carries exactly one "<domain>-<level>" tag.
- The structures below are MAIN SETS; warmup and cooldown are added per
  the modeling rules in decision-process.md.

Dose levels:
- High → strong stimulus
- Moderate → standard session
- Low → reduced load / fatigue management

---

## VO2max (Z5)

| Dose     | Structure                                     | Tag |
| -------- | --------------------------------------------- | --- |
| High     | 5×2.5 min (2.5 min rec) / 5×3 min (3 min rec) | vo2max-high |
| Moderate | 6×1.5 min (1.5 min rec) / 5×2 min (2 min rec) | vo2max-moderate |
| Low      | 10×30 s (30 s rec) / 7×1 min (1 min rec)      | vo2max-low |

Work in Z5; recovery in Z1.

---

## Threshold (Z4)

| Dose     | Structure                                  | Tag |
| -------- | ------------------------------------------ | --- |
| High     | 3×12 min (3:15 rec) / 2×20 min (5 min rec) | lactate-threshold-high |
| Moderate | 3×8 min (2:30 rec) / 3×10 min (3 min rec)  | lactate-threshold-moderate |
| Low      | 3×5 min (90 s rec) / 3×6 min (2 min rec)   | lactate-threshold-low |

Work in Z4 (sweet spot to threshold); recovery in Z1. Over/unders may add
brief Z5 spikes.

---

## Aerobic Threshold / Long Ride (Z2)

| Dose     | Structure        | Tag |
| -------- | ---------------- | --- |
| High     | 2–4 h continuous | aerobic-threshold-high |
| Moderate | 1–2 h steady     | aerobic-threshold-moderate |
| Low      | 30–60 min easy   | aerobic-threshold-low |

Steady Z2 (upper Z2 preferred for performance gains). Avoid early Z3 spikes
on long rides to protect durability.

---

## Race-Specific / Breakaway (Z6 + Z4)

Simulates sprint / attack / breakaway repeatability for road races and
criteriums. Hard anaerobic effort (Z6) immediately followed by threshold
consolidation (Z4). Full recovery (Z1) between sets, not partial.

| Dose     | Structure                                            | Tag |
| -------- | ---------------------------------------------------- | --- |
| High     | 4×(2 min Z6 + 3 min Z4), 5 min full rec between sets | race-specific-high |
| Moderate | 3×(2 min Z6 + 3 min Z4), 5 min full rec between sets | race-specific-moderate |
| Low      | 2×(2 min Z6 + 3 min Z4), 5 min full rec between sets | race-specific-low |

---

## Recovery (Z1)

| Dose | Structure               | Tag |
| ---- | ----------------------- | --- |
| —    | 30–60 min easy, Z1 only | recovery-low |

---

## Consistency Rules (CRITICAL)

- Every interval maps to a defined zone (training-zones.md). Do not use
  arbitrary %FTP values outside the zone definitions.
- Interval description, intensity, and tag must be consistent within a workout.
- Exactly one tag per workout, from the canonical taxonomy.
