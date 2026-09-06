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

## Training Readiness

`week_summary.training_readiness` estimates readiness for today's or the next
training session. It combines five independent domains: form, hard-session
recency, HRV, resting heart rate, and sleep. CTL, ATL, and TSB/form are one
combined form signal and must not be counted separately.

Score contributions:

| signal | condition | contribution |
| ------ | --------- | ------------ |
| form | fresh / grey_zone / optimal / transition / high_risk | +2 / +1 / 0 / +1 / -3 |
| hard-session recency | 0 / 1 / 2 / 3+ days | -3 / -1 / +1 / +2 |
| HRV vs 7-day average | ≤ -10% / ≤ -5% / ≥ +5% / ≥ +10% | -2 / -1 / +1 / +2 |
| resting HR vs 7-day average | ≥ +7% / ≥ +3% / ≤ -3% / ≤ -7% | -2 / -1 / +1 / +2 |
| sleep | POOR or < 6h / AVG or < 7h / GOOD or GREAT and ≥ 7h | -2 / -1 / +1 |

The HRV and resting-HR `trend_7d` adjusts the contribution by one point in
the matching direction, bounded to -2 through +2.

Base colors are green for scores ≥ +2, yellow for -2 through +1, and red for
scores ≤ -3. Safety rules override the score:

- `high_risk` form or a hard session today forces red.
- Two or more adverse signals among HRV, resting HR, and sleep force red.
- A hard session one day ago caps readiness at yellow.
- With no usable signal, status is `unknown` rather than green.

Confidence reflects available domains: high for 4–5, medium for 2–3, and low
for 0–1. Missing wellness data is not adverse; it only lowers confidence.
Weight trend remains context and does not affect acute readiness because
short-term weight changes can reflect hydration and fueling.

---

## Decoupling (Aerobic Durability)

Power:HR drift over an effort. Valid **ONLY for endurance-oriented steady efforts**:
- Base / Pyramidal / Threshold rides
- Duration ≥ 90 minutes
- NOT VO2max / short high-intensity sessions
- NOT interval work or variable efforts

For rides outside these conditions, durability signal is limited or not applicable.

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

If a session has multiple canonical tags, all matching tag mappings apply.
Tags do not compete. A single session can classify into multiple ride types
and should be counted in each mapped domain.

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

### Multiple tags on one session (CRITICAL)
- Resolve each tag independently using the mapping above.
- Keep all resolved ride types; do not collapse to a single class.
- Example: tags `aerobic-threshold-high` and `vo2max-moderate` classify
    as both `long_ride` and `vo2` (for duration ≥ 2h), and the session counts
    toward both domains.

---

## Cross-Cutting Principle

Never interpret high decoupling, declining power, or high fatigue as a
purely physiological limitation without first checking fueling and recent
load. Always combine: form + recovery + fueling + recent intensity.
