---
name: training-plan-generation
description: |
  Cycling training plan and workout generation. Use when the user wants to
  create or adjust a weekly plan, select or prescribe workouts, or adapt
  sessions for fatigue, recovery, or race proximity. Includes off-bike
  WeightTraining planning by Friel strength phase. Do NOT use for pure
  analysis, assessment, or summary requests ("how is my current situation",
  "summarize my week").
  Triggers: "plan next week", "create workouts", "Wochenplan", "Plan erstellen".
---

# Training Plan Generation
This skill guides plan generation and workout selection for the training architect agent.

## Scope
Use this skill when the user requests one of the following:

- create a weekly plan
- suggest workouts based on limiter and goals
- adapt sessions for fatigue, recovery, or race proximity

## References
- references/decision-process.md — follow this decision sequence
- references/workout-library.md — read when selecting concrete workouts/tags

## Rules
- Follow the decision sequence from decision-process.md.
- Select workouts and tags from workout-library.md.
- Plan strength per decision-process.md, Strength and the Strength (off-bike)
  library table. At most one ride and at most one WeightTraining entry per calendar day.
- Weekly TSS/hours count rides only; LIMITED-day caps sum all sports.
- WeightTraining uses exactly one canonical strength phase tag, phase-table
  duration and fixed description, no steps or library ID, informational TSS.
- Use the existing compact week_summary.strength fields; mention tagging
  only in the provable cases defined in decision-process.md. Never mention missing RPE.
- Keep output deterministic and aligned with the agent output contract.
- If required inputs are missing, ask only the minimum required question.

The deployment archive creates references/decision-process.md and
references/workout-library.md directly from the canonical coach-logic files;
there are no separately maintained reference copies in this directory.
