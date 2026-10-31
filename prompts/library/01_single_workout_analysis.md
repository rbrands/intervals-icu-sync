Analyze the most recent training session and fetch the data from intervals.icu via prepare_week_data.
If current-week data from prepare_week_data is already present in this chat and still relevant, reuse it and do not call prepare_week_data again.

Answer the following questions:
1. What was the training quality (VO2max stimulus, threshold stimulus, base)?
2. How was load management (pacing, heart rate decoupling, W' usage)?
   If the activity has a `dfa_a1_summary`, add the in-ride aerobic reading:
   share of time above DFA a1 = 0.75 (was the easy ride really aerobic?),
   `power_at_0_75` / `hr_at_0_75` and `power_at_0_75_pct_ftp` compared with the
   athlete's Zone 2 ceiling (`metrics.power_zones_pct[1]`, default 75 % FTP),
   and `threshold_windows` as the confidence behind that reading. Treat it as a
   day-form observation, not a zone verdict. If the field is absent, say nothing
   about DFA a1 — hard sessions are not analyzed by design.
3. What does the fueling tell us — carbs per hour relative to intensity?
4. What is the effect of this session on CTL, ATL, and form?
5. What do I take away for the next 48–72 hours (recovery, next session)?

Keep the response structured and focused on the essentials.
