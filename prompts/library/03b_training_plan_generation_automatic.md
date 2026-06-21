Fetch the current data from intervals.icu via prepare_week_data. Based on the weekly analysis, create a training plan for the coming week.
If current-week data from prepare_week_data is already present in this chat and still relevant, reuse it and do not call prepare_week_data again.

Derive the planning parameters directly from the intervals.icu data:
- Training phase and week type: from `next_week_active_phases` and `next_week_load_targets.week_type` (NORMAL / RECOVERY / RACE)
- Weekly load target: from `next_week_load_targets.load_target` (TSS)
- Available days: from `next_week_day_constraints` — days with `training_allowed: false` are unavailable, days with `training_allowed: true` and type LIMITED only get short, easy sessions
- Already planned sessions: from `planned_workouts` for next week — treat as anchors, do not replace
- Consider current form (TSB) and fatigue (ATL)

Planning logic:
1. Place key sessions matched to the training phase first (VO2max, threshold, long ride)
2. Align total load to the TSS target — show estimated TSS per session
3. Account for fueling strategy for intense sessions
4. Explicitly schedule recovery days
5. Do not duplicate already-completed key stimuli

Format: Day-by-day with session type, duration, intensity (zone), session goal, estimated TSS, and fueling recommendation.
