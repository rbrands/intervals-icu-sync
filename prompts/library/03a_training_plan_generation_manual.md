Fetch the current data from intervals.icu via prepare_week_data. Based on the weekly analysis, create a training plan for the coming week.
If current-week data from prepare_week_data is already present in this chat and still relevant, reuse it and do not call prepare_week_data again.

Constraints:
- Consider current form (TSB) and fatigue (ATL)
- Adjust load to the primary limiter
- Maximum [X] hours Ride volume (strength and running excluded)
- Available days: [enter days, e.g. Mon, Wed, Thu, Sat, Sun]
- Planned events or races: [enter if applicable]

Planning logic:
1. Place key sessions first (VO2max, threshold, long ride)
2. Calculate TSS strictly per the TSS Calculation rules from the system prompt:
	computed from steps for generated workouts, library TSS for selected library
	workouts, and the stated TSS for anchored planned workouts. Show estimated
	TSS per session.
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
2. Verify Ride duration does not exceed the manually specified Ride hours;
   LIMITED-day caps include all sessions. Check strength placement and contract.
If a check fails, correct steps or plan composition first, then re-verify.
