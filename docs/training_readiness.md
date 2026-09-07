# How the Training Readiness Traffic Light Works

Training readiness is rarely captured by a single number. Fitness, accumulated fatigue, recent intensity, heart-rate variability, resting heart rate, and sleep each describe a different part of the athlete's current state.

The Training Readiness traffic light combines these signals into one explainable daily assessment:

- **Green**: a planned hard session is acceptable if subjective readiness is also good.
- **Yellow**: adjust the load and verify recovery before adding intensity.
- **Red**: avoid hard training and prioritize recovery.
- **Unknown**: there is not enough usable information; assess readiness manually.

The result is intended for today's or the next training session. It is a decision aid, not a medical diagnosis and not a replacement for the athlete's own perception.

## Design Principles

The model follows four principles:

1. **Use several independent domains.** No single metric determines readiness under normal conditions.
2. **Keep the result explainable.** Every signal includes its score contribution and a human-readable reason.
3. **Treat missing data as unknown, not bad.** Missing wellness data lowers confidence but does not reduce the score.
4. **Let safety rules override arithmetic.** A positive total cannot cancel a clear warning such as high-risk form or several adverse recovery signals.

## The Five Readiness Signals

The traffic light evaluates five domains:

1. Training form
2. Time since the last hard session
3. Heart-rate variability (HRV)
4. Resting heart rate
5. Sleep

CTL, ATL, and TSB/form are treated as one combined **form** signal. Counting them separately would give the same underlying load model too much influence.

## 1. Training Form

Training form compares acute fatigue with longer-term fitness:

$$
\text{Form}_{\text{absolute}} = \text{CTL} - \text{ATL}
$$

$$
\text{Form}_{\%} = \frac{\text{CTL} - \text{ATL}}{\text{CTL}} \times 100
$$

CTL is chronic training load and represents longer-term fitness. ATL is acute training load and represents recent fatigue.

| Form percentage | Zone | Interpretation | Score |
|---:|---|---|---:|
| Above +20% | `transition` | Very fresh, possibly tapering or detraining | +1 |
| +5% to +20% | `fresh` | Recovered, with capacity to add load | +2 |
| -10% to +5% | `grey_zone` | Normal training state | +1 |
| -30% to -10% | `optimal` | Productive training load | 0 |
| Below -30% | `high_risk` | Elevated overreaching risk | -3 |

An `optimal` form score is deliberately neutral rather than positive: productive fatigue is expected during training, but it is not the same as being fully recovered. A `high_risk` value also triggers a safety veto and therefore forces the traffic light to red.

## 2. Time Since the Last Hard Session

Recovery demand depends strongly on how recently the athlete completed meaningful intensity.

| Days since the last hard session | Score | Effect |
|---:|---:|---|
| 0 | -3 | Forces red |
| 1 | -1 | Readiness cannot be greener than yellow |
| 2 | +1 | Some recovery time has passed |
| 3 or more | +2 | Recent intensity is unlikely to limit readiness |

### What Counts as a Hard Session?

A session counts as hard when its intensity distribution is:

- `HIIT`, regardless of TSS
- `Polarized`, regardless of TSS
- `Threshold` with at least 50 TSS **or** RPE 7+

The extra requirement for Threshold sessions prevents short, easy rides with incidental time in zones 3 and 4 from resetting hard-session recency. HIIT and Polarized sessions do not use a TSS floor because a short VO2max workout can create substantial recovery demand despite a modest total training load.

## 3. Heart-Rate Variability

HRV is compared with the athlete's own seven-day average. A higher value is generally favorable; a lower value is adverse.

| HRV versus 7-day average | Base score |
|---:|---:|
| At least 10% below | -2 |
| 5% to 10% below | -1 |
| Within 5% | 0 |
| 5% to 10% above | +1 |
| At least 10% above | +2 |

The seven-day trend can adjust this score by one point:

- An upward HRV trend adds one point.
- A downward HRV trend subtracts one point.
- The final HRV contribution is limited to the range -2 to +2.

This combines today's deviation from baseline with the direction in which recovery has recently been moving.

## 4. Resting Heart Rate

Resting heart rate is also compared with its seven-day average, but the direction is inverted: lower is generally favorable and higher is adverse.

| Resting HR versus 7-day average | Base score |
|---:|---:|
| At least 7% above | -2 |
| 3% to 7% above | -1 |
| Within 3% | 0 |
| 3% to 7% below | +1 |
| At least 7% below | +2 |

The seven-day trend again adjusts the result by one point:

- A downward resting-HR trend adds one point.
- An upward resting-HR trend subtracts one point.
- The final contribution is limited to -2 through +2.

## 5. Sleep

Sleep uses both duration and the quality label supplied by the data source. The checks are evaluated from most adverse to favorable, so a clearly poor duration or quality is not hidden by the other value.

| Condition | Score |
|---|---:|
| Quality is `POOR` or duration is below 6 hours | -2 |
| Quality is `AVG` or duration is below 7 hours | -1 |
| Quality is `GOOD`/`GREAT` or duration is at least 7 hours | +1 |
| Data is present but matches none of the above | 0 |
| No sleep duration and no quality | Unavailable |

For example, five hours of sleep remains adverse even if the quality label says `GOOD`, because the below-six-hour rule is evaluated first.

## From Signal Scores to a Color

All available signal contributions are added:

$$
\text{Readiness Score} = \sum_{i=1}^{n} \text{available signal contribution}_i
$$

The initial color is assigned from the total:

| Total score | Base color |
|---:|---|
| +2 or higher | Green |
| -2 through +1 | Yellow |
| -3 or lower | Red |

This base color is only the first step. Safety rules are applied afterward.

## Safety Vetoes and Caps

The following conditions override the normal score calculation:

- **High-risk form forces red.** A form value below -30% indicates excessive accumulated fatigue.
- **A hard session today forces red.** Recovery from that session takes precedence over other positive signals.
- **Two or more adverse recovery signals force red.** HRV, resting heart rate, and sleep are evaluated as the recovery group.
- **A hard session yesterday caps readiness at yellow.** Even a strongly positive score cannot produce green.

This prevents compensation errors. For example, excellent sleep should not mathematically cancel both suppressed HRV and elevated resting heart rate.

## Confidence

Confidence describes data completeness, not how ready the athlete is.

| Available domains | Confidence |
|---:|---|
| 4-5 | High |
| 2-3 | Medium |
| 0-1 | Low |

A missing signal contributes zero points and is marked `unavailable`. If every signal is unavailable, the status is `unknown` rather than green.

Weight trend is intentionally not scored. Short-term weight changes often reflect hydration, glycogen, or fueling and are therefore too ambiguous for acute readiness.

## Worked Example

Consider this illustrative state:

| Signal | Observation | Contribution |
|---|---|---:|
| Form | `optimal` | 0 |
| Last hard session | One day ago | -1 |
| HRV | 6% above baseline | +1 |
| Resting HR | Near baseline | 0 |
| Sleep | 7.5 hours, `GOOD` | +1 |

The score is:

$$
0 - 1 + 1 + 0 + 1 = 1
$$

A score of +1 is yellow. Even if the wellness signals had raised the score to green territory, the hard session one day ago would still cap the result at yellow.

The practical recommendation is therefore to adjust the planned load and verify subjective recovery before adding intensity.

## Explainable Output

The calculated result is stored under `week_summary.training_readiness`. A simplified example looks like this:

```json
{
  "status": "yellow",
  "score": 1,
  "confidence": "high",
  "recommendation": "Adjust training load and verify recovery before adding intensity.",
  "reasons": [
    "Form is optimal (-16.1%).",
    "The last hard session was 1 day ago."
  ],
  "safety_vetoes": [
    "A hard session was completed one day ago; readiness is capped at yellow."
  ],
  "signals": [
    {
      "name": "form",
      "status": "neutral",
      "contribution": 0,
      "reason": "Form is optimal (-16.1%)."
    }
  ]
}
```

Each signal has one of four states:

- `positive`
- `neutral`
- `adverse`
- `unavailable`

This makes the traffic light auditable: athletes and coaches can see not only the final color, but also why it was assigned.

## How to Use the Result

The traffic light should start a decision, not end one.

- **Green** supports the planned hard session only when subjective readiness is also good.
- **Yellow** calls for a closer look at the adverse or recently stressed domains. Reducing intensity, duration, or both may be appropriate.
- **Red** indicates that recovery should take priority over another hard stimulus.
- **Unknown** means the available data cannot support an automated recommendation.

Illness symptoms, pain, unusual exhaustion, and other athlete-reported concerns always take precedence over a green algorithmic result.

## Limitations

The model uses explicit heuristics rather than claiming to predict performance or injury. Its quality depends on consistent source data, especially accurate sleep, HRV, resting-HR, RPE, and activity-zone information. Individual responses also differ: two athletes with the same score may not tolerate the same session.

For that reason, the traffic light is best viewed as a transparent synthesis of recent training and recovery data. Its main value is not the color alone, but the structured conversation it creates between objective signals, the training plan, and the athlete's lived experience.
