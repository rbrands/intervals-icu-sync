Fetch the current data from intervals.icu via prepare_week_data. Based on the weekly analysis, create a training plan for the coming week.
If current-week data from prepare_week_data is already present in this chat and still relevant, reuse it and do not call prepare_week_data again.

Derive the planning parameters directly from the intervals.icu data:
- Training phase and week type: from `next_week_active_phases` and `next_week_load_targets.week_type` (NORMAL / RECOVERY / RACE)
- Weekly target: from `next_week_load_targets.load_target` (TSS). If `time_target_hours` is also present, treat it as an upper time cap. Only if `load_target` is `null`, use `time_target_hours` as the weekly target.
- Available days: from `next_week_day_constraints` — days with `training_allowed: false` are unavailable, days with `training_allowed: true` and type LIMITED only get short, easy sessions. If `max_training_time_hours` is present, planned duration on that day must not exceed this value.
- Already planned sessions: from `planned_workouts` for next week — treat as anchors, do not replace
- Consider current form (TSB) and fatigue (ATL)
- Recent load pattern: use `training_load_history` to distinguish isolated from
  repeated target deviations. Treat it as secondary context behind current
  readiness and never add missed historical load to the coming week.

Planning logic:
1. Place key sessions matched to the training phase first (VO2max, threshold, long ride)
2. Align total volume to the weekly target: use TSS when `load_target` is present and treat `time_target_hours` as an additional upper bound. Only if `load_target` is `null`, use total planned time when `time_target_hours` is present. Still show estimated TSS per session. For the weekly total, sum TSS strictly per the TSS Calculation rules from the system prompt: computed from steps for generated workouts, library TSS for selected library workouts, and the stated TSS for anchored `planned_workouts`. The planned weekly total should land within ±10% of `load_target` unless constraints or fatigue clearly justify a deviation. Keep the provided target authoritative unless repeated historical deviation and current readiness together justify a safer reduction.
3. Account for fueling strategy for intense sessions
4. Explicitly schedule recovery days
5. Do not duplicate already-completed key stimuli

Workout library lookup (when `list_library_workouts` is available):
1. Determine all planned sessions and their full canonical tags first.
2. Call `list_library_workouts` exactly once with all distinct tags,
  `match_mode="any"`, `include_untagged=false`, and `limit=100`.
3. Use a result only when its exact workout tag and dose fit the already planned
  session. Prefer the closest duration and TSS as soft ranking criteria; neither
  value needs to equal the planned value. Calendar placement and day constraints
  are not library matching criteria. Preserve its
  `library_workout_id`; do not recreate its steps.
4. If there is no matching workout for a session, generate it normally without
  `library_workout_id`. Do not broaden or repeat the search.

Format: Day-by-day with session type, duration, intensity (zone), session goal, estimated TSS, and fueling recommendation.

Final self-check before returning output:
1. For every generated workout, recompute TSS from the final `steps` and
   verify it matches the value in `description`.
2. Verify the weekly TSS total against `load_target` (±10%).
If a check fails, correct steps or plan composition first, then re-verify.
