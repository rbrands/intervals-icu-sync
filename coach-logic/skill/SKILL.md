---
name: training-plan-generation
description: |
  Cycling training plan and workout generation. Use when the user wants to
  create or adjust a weekly plan, select or prescribe workouts, or adapt
  sessions for fatigue, recovery, or race proximity. Do NOT use for pure
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
- Keep output deterministic and aligned with the agent output contract.
- If required inputs are missing, ask only the minimum required question.
