Fetch the current data from intervals via prepare_week_data and summarize the current metrics and wellness data.
If current-week data from prepare_week_data is already present in this chat and still relevant, reuse it and do not call prepare_week_data again.

**Performance Metrics**
- FTP and eFTP (current value and trend)
- VO2max (current value and trend)
- W' (anaerobic capacity)
- CTL (fitness), ATL (fatigue), form (TSB) — absolute and as %
- Rider type from `metrics.power_profile` based on `type`, `type_key`, `heuristic_score`, `type_scores`, and `type_method` (heuristic classification; explicitly mention uncertainty when scores are close)

Use this fixed rider-type output template:
`Power profile: <type> (<confidence_level>, similarity <heuristic_score>). <Short interpretation in 1-2 sentences based on p15s/p30s/p1min/p3min/p5min/p20min and curve_slope>.`

Confidence level rule:
- `high` when `heuristic_score >= 0.45`
- `moderate` when `heuristic_score >= 0.30` and `< 0.45`
- `low` when `< 0.30`

Discipline fit:
Compare the current power profile (rider type and w_per_kg across
p15s/p30s/p1min/p3min/p5min/p20min) against the priorities of the athlete's
discipline, as defined in the system prompt above). In 1-2
sentences: name the discipline demand the current profile already covers
well, and name the single biggest gap between the current profile and what
the discipline needs most. Do not repeat the rider-type paragraph above; add
only the discipline-specific comparison.


**Wellness**
- HRV: current value and trend (last 7 days)
- Resting heart rate: current value and trend
- Sleep: quality and duration (if available)
- Weight: current value and trend

**Assessment**
- What is the current form state (fresh / transition / optimal / high risk)?
- Are there any anomalies in the wellness data indicating overload or insufficient recovery?
- Recommendation: Can training load be increased next week, or is recovery the priority?

Keep the summary compact and action-oriented.
