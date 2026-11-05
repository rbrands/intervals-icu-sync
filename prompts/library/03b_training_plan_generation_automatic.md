Fetch the current data from intervals.icu via prepare_week_data. Based on the weekly analysis, create a training plan for the coming week.
If current-week data from prepare_week_data is already present in this chat and still relevant, reuse it and do not call prepare_week_data again.

Derive the planning parameters directly from the intervals.icu data. The week entries live in `week_summary.training_plan`; use the entry whose `week` equals the target week start:
- Training phase and week type: from `phase` and `week_type` (NORMAL / RECOVERY / RACE) of that entry. Respect `week_note` when present.
- Weekly Ride target: from `weekly_load_target` (TSS) of that entry, with
  `weekly_time_target_hours` as a Ride-only upper budget when supplied. Never
  invent a target or fall back to another week's target.
- Available days: from `day_constraints` of that entry — days with `training_allowed: false` are unavailable, days with `training_allowed: true` and type LIMITED only get short, easy sessions. If `max_training_time_hours` is present, planned duration on that day must not exceed this value.
- Already planned sessions: from `planned_workouts` for the target week — treat as anchors, do not replace
- Consider current form (TSB) and fatigue (ATL)
- Recent load pattern: use `training_load_history` to distinguish isolated from
  repeated target deviations. Treat it as secondary context behind current
  readiness and never add missed historical load to the coming week.

Planning logic:
1. Place key sessions matched to the training phase first (VO2max, threshold, long ride)
2. Align Ride volume to the weekly target: sum Ride TSS strictly per the system prompt (generated rides from steps, library rides unchanged, anchored rides as stated). Completed plus planned Ride TSS should land within ±10% of `weekly_load_target` unless constraints or fatigue justify a safer reduction. Completed plus planned Ride hours must not exceed `weekly_time_target_hours` when supplied. Never use combined Ride+Run or strength totals.
3. Account for fueling strategy for intense sessions
4. Explicitly schedule recovery days
5. Do not duplicate already-completed key stimuli

Strength and guardrails:
- Plan strength per decision-process.md, Strength and the Strength (off-bike)
  library table; use week_summary.strength, not an exported raw history.
- At most one ride and at most one WeightTraining entry per calendar day.
- Weekly TSS and hours compare rides only (Ride, VirtualRide, MountainBikeRide,
  GravelRide; absent or null activity_type = Ride). LIMITED-day caps sum ALL
  entries on the date, including strength; no entry on unavailable days.
- WeightTraining: exactly one strength-adaptation/transition/maximum/maintenance
  tag, phase-table duration and fixed description, no steps or library ID,
  numeric informational tss (supplied value, otherwise 0). Never mention missing RPE.

Workout library lookup (when `list_library_workouts` is available):
1. Determine all planned sessions and their full canonical tags first.
2. Call `list_library_workouts` exactly once with all distinct ride tags,
  `match_mode="any"`, `include_untagged=false`, and `limit=100`.
3. For rides, use a result only when its exact workout tag and dose fit the already planned
  session. Prefer the closest duration and TSS as soft ranking criteria; neither
  value needs to equal the planned value. Calendar placement and day constraints
  are not library matching criteria. Preserve its
  `library_workout_id`; do not recreate its steps.
4. If there is no matching workout for a session, generate it normally without
  `library_workout_id`. Do not broaden or repeat the search.

Format: Day-by-day with session type, duration, intensity (zone), session goal, estimated TSS, and fueling recommendation.

Final self-check before returning output:
1. For every generated ride, recompute TSS from the final `steps` and
   verify it matches the value in `description`.
2. Verify Ride-only weekly TSS against `weekly_load_target` (±10%) and Ride-only
   hours against `weekly_time_target_hours`. Check all-sport LIMITED-day caps
   and the strength placement/entry contract.
If a check fails, correct steps or plan composition first, then re-verify.
