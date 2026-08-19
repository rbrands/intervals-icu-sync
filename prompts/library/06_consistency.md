Fetch the current data from intervals via prepare_week_data. Check the athlete data for completeness and internal consistency.
This is a data-quality check, not a coaching interpretation — do not give training
recommendations here, only report what is present, missing, or inconsistent
and why it matters for future assessments and plans.
If current-week data from prepare_week_data is already present in this chat and still relevant, reuse it and do not call prepare_week_data again.

Evaluate each area below. For each one, report a status (`OK`, `Warning`, or
`Missing`) and a one-sentence explanation of the practical impact if it is not
`OK`. Use the exact thresholds given; do not invent your own.

**Season plan / macrocycle**
- `OK` if `week_summary.training_plan` is present and contains an entry for
  the current week.
- `Missing` if `week_summary.training_plan` is absent or empty.
- Impact when `Missing`: no phase, weekly load target, or day constraints are
  available; plan generation falls back to a readiness-based plan without a
  target to work toward.

**FTP consistency**
- Compare `ftp` against `rolling_ftp` and `eftp`.
- `OK` if both differ from `ftp` by less than 10%.
- `Warning` if either differs by 10-20%.
- `Missing`/flag as inconsistent if either differs by more than 20%.
- Additionally check `metrics.power_profile.p20min.watts`: if this best
  20-minute power over `period_days` implies a threshold far below `ftp`
  (more than 20% lower after applying a 0.95 factor), note this explicitly,
  but frame it as context (e.g. plausible for sprint/puncheur-type riders who
  did not perform a sustained effort in this window), not as an error.

**W' consistency**
- Compare `w_prime` against `rolling_w_prime`.
- `OK` if they differ by less than 10%.
- `Warning` if they differ by 10-20%.
- Flag as inconsistent if they differ by more than 20%.

**Wellness tracking**
- Check `resting_hr`, `hrv`, and `sleep_secs`.
- `OK` if at least one of these three is non-null.
- `Missing` if all three are null.
- Impact when `Missing`: form/readiness assessments cannot use recovery
  signals and rely on training load metrics (CTL/ATL/TSB) alone.

**Recent activity density**
- Count entries in `activities` within the `lookback_days` window.
- `OK` if 3 or more activities are present.
- `Warning` if 1-2 activities are present.
- `Missing` if 0 activities are present.
- Impact when `Warning` or `Missing`: recent-load and intensity-distribution
  interpretations are based on very little data and have low confidence.

**Load target history**
- Check `weekly_load_target` across all entries in `training_load_history`.
- `OK` if at least one entry has a non-null `weekly_load_target`.
- `Missing` if every entry is null.
- Impact when `Missing`: no historical target-vs-achievement trend is
  available; this is consistent with (and expected alongside) a missing
  season plan above.

**Summary**
End with one line: overall data completeness as `Good` (all areas `OK`),
`Partial` (only `Warning`/`Missing` areas, no more than two), or `Limited`
(three or more `Warning`/`Missing` areas). Follow this with one sentence on
which single fix would improve the data quality most (e.g. "connecting a
wellness tracker" or "setting up a season plan in intervals.icu").

Keep the response compact: one short line per area, not a full paragraph.
