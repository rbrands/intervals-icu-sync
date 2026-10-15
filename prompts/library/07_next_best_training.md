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

**Recommendation**
Give exactly ONE main recommendation and one alternative for the case that I feel
worse than the data suggests:
- Session type, duration, target zones (power/HR/RPE), interval structure
- Expected TSS and fueling target (g carbs/h)
- One sentence of reasoning per decision factor (readiness, plan, missing stimulus)
- Abort/downgrade criteria during the session (e.g. HR decoupling, RPE)

If readiness is "Unknown" or key data is missing, state this explicitly and
recommend conservatively instead of asking.
