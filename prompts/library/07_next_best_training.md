Fetch the current data from intervals.icu via prepare_week_data and recommend the
next best training session for today. Do not ask follow-up questions; decide based
on the available data.
If current-week data from prepare_week_data is already present in this chat and
still relevant, reuse it and do not call prepare_week_data again.

If a session has already been completed today, give a recommendation for the
next day instead and mark it as preliminary, because tomorrow's sleep and HRV
are not yet available (re-check in the morning).

Take the following into account:

**Starting point**
- Training readiness (`week_summary.training_readiness`): traffic light, score, and reasons
- CTL/ATL/TSB and the load of the last 48-72 hours (last hard session?)
- Wellness: sleep, HRV, resting heart rate - only if available

**Plan context**
- Current phase (Base/Build/Peak) and weekly target (`weekly_load_target` or time target)
- Weekly TSS completed so far vs. remaining budget for the remaining days
- Today's planned workout from the calendar (if any) - does it still fit?
- Upcoming races (RACE_A/B/C) and day constraints (Sick/Travel)

**Gaps in the week**
- Which stimulus is still missing (VO2max, threshold, base, recovery)? Use the activity tags.
- Fueling pattern of the recent sessions

If readiness is "Unknown" or key data is missing, state this explicitly and
recommend conservatively instead of asking.

**Output: short recommendation + upload JSON**
Treat this as workout generation, not an analysis. Output exactly two parts:
1. At most 100 words of prose in total: target date (mark tomorrow as preliminary),
   session type, duration, target zone, TSS, and carbs/h; ONE short sentence explaining
   the decision; ONE sentence with an easier alternative and a downgrade/stop criterion.
   Do not output a separate analysis, metrics table, or reasoning per decision factor.
2. The main recommendation as valid upload JSON in the existing week-plan format:
   an object with a `workouts` array containing exactly one workout. Do not include
   the alternative. Enclose a fenced json block between BEGIN_UPLOAD_JSON and
   END_UPLOAD_JSON, each on its own line; nothing may follow the closing marker.
   Do not call upload_week_plan or upload anything automatically.

Use the athlete data's `current_date` for today; if already trained today, add one
calendar day and evaluate that day's plan, week target, and constraints instead.
Do not treat today's readiness as tomorrow's measured readiness.
Each workout must contain `date` (YYYY-MM-DD), `name`, `duration_minutes`,
`activity_type`, `description`, integer `tss`, non-empty canonical `tags`, and
non-empty `steps` with integer `duration_seconds` > 0 and `power_pct_ftp`.
Use the existing training zones and tags; default to Ride only for cycling.
Put warmup, main set, and cooldown in steps; their total duration must equal
`duration_minutes` * 60. Recompute TSS from the final steps:
round(sum((duration_seconds / 3600) * (power_pct_ftp / 100)^2 * 100)).
Include that same TSS and fueling guidance in the short `description`.
For non-power activities, omit power steps and do not invent FTP or TSS; omit
unavailable `tss` and use duration, HR/RPE guidance, and the correct `activity_type`.
If rest is the main recommendation or essential data for a safe, executable workout
is missing, return {"workouts": []} instead of inventing a workout or a zero-duration
rest event. Briefly explain this within the prose limit.
Before output, silently check JSON validity, field types, target date, constraints,
step durations, and TSS. Do not print the checks or any additional commentary.
