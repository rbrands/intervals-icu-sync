# Interpretation Rules

This document defines how the coach READS and CLASSIFIES training data.
It is the single source for all interpretation thresholds.

It does NOT prescribe actions — what to DO with an interpretation
(session selection, load changes, fueling strategy) is defined in
decision-process.md. Zone definitions live in training-zones.md.

---

## Form (Fatigue State)

form_absolute = CTL - ATL
form_pct      = (CTL - ATL) / CTL

| form_pct      | form_zone   | meaning |
| ------------- | ----------- | ------- |
| > +20%        | transition  | very fresh (often taper/detraining) |
| +5% to +20%   | fresh       | recovered, capacity to add load |
| -10% to +5%   | grey_zone   | normal training state |
| -30% to -10%  | optimal     | productive training zone |
| < -30%        | high_risk   | overreaching risk |

Always read form together with recovery indicators (HRV, resting HR,
subjective fatigue) and recent intensity — never in isolation.

---

## Decoupling (Aerobic Durability)

Power:HR drift over an effort. Valid ONLY for steady efforts
(not interval / variable sessions).

| decoupling | label |
| ---------- | ----- |
| < 5%       | excellent durability |
| 5–8%       | moderate drift |
| 8–10%      | high drift |
| > 10%      | significant limitation |

Always interpret decoupling together with fueling (below): high
decoupling alone does not prove a durability limitation.

---

## Anaerobic Capacity (W')

w_prime_drop_pct = w_prime_bal_drop_j / w_prime_j × 100

Diagnostic signals:
- Long ride with w_prime_drop_pct > 20% → pacing too aggressive; durability at risk
- Aerobic/endurance ride with w_prime_usage_pct > 15% → unintended intensity / spiky riding
- Repeated large W' depletions across the week → anaerobic fatigue may be limiting

(Corresponding actions are defined in decision-process.md.)

---

## Fueling

### Requirement by duration
| duration  | fueling |
| --------- | ------- |
| < 1.5h    | not required |
| 1.5–2.0h  | optional |
| > 2.0h    | required |

### Carbohydrate targets
- moderate / endurance rides: 60–80 g/h
- long rides / high load:     80–90 g/h

### Fueling ratio (carbs_ingested / carbs_used)
| ratio    | classification |
| -------- | -------------- |
| < 0.4    | significant deficit |
| 0.4–0.7  | moderate deficit |
| > 0.7    | good |

### Fueling × durability (combined reading)
| decoupling | carbs | interpretation |
| ---------- | ----- | -------------- |
| high       | low   | likely fueling limitation |
| high       | good  | aerobic durability limitation |
| low        | good  | good durability and fueling |
| low        | low   | efficient, but performance may still be limited |

---

## Primary Limiter Detection

Identify the single primary limiter from combined signals:

- VO2max → low p5min / VO2max; little recent high-intensity work
- Threshold (FTP) → declining power in sustained efforts; cannot hold FTP
- Aerobic durability → high decoupling (>8–10%) on steady efforts; power drop in long rides
- Fueling / energy availability → low carbs/h, low fueling ratio, high decoupling with low intake
- Anaerobic / repeatability → repeated W' depletion limiting late efforts (discipline-dependent)

If several signals point to fueling, resolve fueling FIRST — an
underfueled session can mimic a fitness limitation.

(Limiter-based session prescription is defined in decision-process.md.)

---

## Activity Classification by Tag

Tags are the highest-priority classifier and override interval detection
and automatic distribution.

Priority: tags > interval detection > automatic classification

### Tag taxonomy (canonical source)
Format: "<domain>-<level>"
- domains: vo2max, lactate-threshold, aerobic-threshold, recovery, race-specific
- levels:  low, moderate, high

These prefixes are shared with the workout library (decision-process.md)
and with library filter tooling. Do not rename without updating all three.

### Tag → ride_type mapping
- vo2max-*            → vo2
- lactate-threshold-* → threshold
- aerobic-threshold-*:
    - duration ≥ 2h   → long_ride
    - else            → endurance
- recovery-*          → recovery
- race-specific-*     → race

---

## Cross-Cutting Principle

Never interpret high decoupling, declining power, or high fatigue as a
purely physiological limitation without first checking fueling and recent
load. Always combine: form + recovery + fueling + recent intensity.
