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

Use the athlete data's `current_date` for today; if already trained today, add one
calendar day and evaluate that day's plan, week target, and constraints instead.
Do not treat today's readiness as tomorrow's measured readiness.

**Recommendation and upload**
Use the same workout-generation output contract and upload workflow as the weekly
plan, but for exactly one workout:
- At most 100 words of prose: date, session type, duration, target zone, TSS and
  carbs/h, one short reason, and an easier alternative with a downgrade/stop criterion.
  No separate analysis or metrics table.
- Then generate upload JSON for the main recommendation using the system prompt's
  existing schema, markers, and TSS rules. The alternative stays in prose only.
- Let the user review the recommendation. Upload only after the user explicitly
  requests it, using the existing weekly-plan workflow:
  local MCP: save_week_plan(plan_json=...), then validate_week_plan(), then
  upload_week_plan(); hosted MCP: validate_week_plan(plan_json=...), then
  upload_week_plan(plan_json=...) with the same JSON (no save tool).
  Upload only if validation succeeds.
  Do not upload automatically or ask for confirmation now.

If rest is recommended or essential workout data is missing, explain briefly
instead of inventing a workout. Follow the system prompt's prose-only rule when
no workout is created.
