# Use Any GenAI Coach with intervals.icu Without MCP

An AI coach does not need a direct tool connection to work with current intervals.icu data. Training Architect can provide the same curated dataset through the clipboard or a conventional HTTP API, while the coaching conversation stays in the GenAI tool of your choice.

This creates a complete workflow for ChatGPT, Claude, Microsoft Copilot, Mistral AI, or another GenAI service even when MCP is unavailable, restricted by licensing, or deliberately not configured.

## The Core Idea

The workflow separates three responsibilities:

1. **Training Architect prepares the data.** It retrieves intervals.icu data and returns the curated dataset used by the coaching logic.
2. **Any GenAI tool performs the coaching.** It assesses the dataset, discusses decisions with the athlete, and generates a structured training plan.
3. **Training Architect validates and uploads the plan.** It checks the generated JSON before anything is written to the intervals.icu calendar.

The GenAI tool never needs the athlete's intervals.icu API key. It only receives the curated dataset that the athlete deliberately copies into the conversation.

## Why Use This Instead of MCP?

MCP provides the most integrated experience because the GenAI tool can fetch data and invoke plan operations directly. It is not always available, however. An organization may block custom connectors, a product tier may not include MCP support, or an athlete may prefer to keep every data transfer visible and manual.

The clipboard and HTTP workflows preserve the important parts of the integrated process:

- Current, consolidated training and wellness data
- The same coach logic and plan JSON contract
- Automatic plan validation
- A review step before calendar changes
- An explicit action that authorizes the upload

The difference is where orchestration happens. With MCP, the GenAI client calls tools. Without MCP, the athlete transfers the dataset and plan between the two systems.

## What Is the Curated Dataset?

The curated dataset is a consolidated JSON representation of the athlete's relevant intervals.icu data. It is designed for coaching rather than as a raw API dump and can include:

- Recent activities and training quality
- CTL, ATL, form, FTP, VO2max, HRV, resting heart rate, weight, and sleep
- Fueling information
- Weekly summaries and training readiness
- Active training phase and weekly targets
- Planned workouts and day-level availability constraints

Its structure follows the coaching input contract in `coach-logic/input-schema.md`. The system prompt and coach-logic files tell the GenAI tool how to interpret these fields and turn them into recommendations.

## Browser Workflow

### 1. Prepare the GenAI Coach

Configure the GenAI tool with the repository's coaching material:

- Use `prompts/system_prompt.md` as the system or project instruction.
- Insert the matching athlete profile from `prompts/discipline_*.md`.
- Add the files from `coach-logic/` as project knowledge or conversation context.

This setup is independent of MCP and only needs to be refreshed when the coaching material changes.

### 2. Copy the Curated Dataset

Open [Training Architect](https://training-architect.com), connect it to intervals.icu with your Athlete ID and API Key, and open **Coach**.

Select the copy icon next to the connection status. Training Architect retrieves the current curated dataset and copies it to the clipboard.

Paste the JSON into the prepared GenAI conversation. The athlete can now request a latest-workout assessment, a weekly review, or another coaching analysis using current data.

### 3. Discuss Before Planning

Treat the initial result as a coaching discussion rather than immediately requesting a calendar upload. Verify assumptions, add subjective context, and resolve questions about readiness, availability, goals, or recent sessions.

When the decisions are clear, ask the GenAI tool to return the final plan as JSON compatible with the plan contract in `prompts/system_prompt.md`.

### 4. Paste and Validate the Plan

In the **Create Plan** area of Training Architect, select the clipboard icon and paste the generated JSON.

Training Architect validates the plan automatically. Invalid JSON or schema violations are reported before upload. Return the validation feedback to the GenAI tool, request a corrected plan, and paste the revised JSON again.

A minimal valid plan can look like this:

```json
{
  "week": "2026-09-14",
  "workouts": [
    {
      "date": "2026-09-15T18:00:00",
      "name": "Aerobic Endurance",
      "duration_minutes": 75,
      "activity_type": "Ride",
      "description": "Steady endurance ride at conversational intensity.",
      "tags": [
        "aerobic-threshold-low"
      ]
    }
  ]
}
```

The full schema is maintained in `contracts/week-plan/week-plan.schema.json`.

### 5. Review and Confirm the Upload

Successful validation does not upload the plan automatically. Review dates, workout types, duration, intensity, and available training time first.

The intervals.icu calendar is changed only after the athlete explicitly confirms the upload in Training Architect. This keeps generated recommendations separate from write access and prevents an unreviewed GenAI response from becoming a scheduled plan.

## HTTP API Workflow

The same process is available to Postman, `curl`, automation scripts, and other HTTP clients. The public API exposes three operations:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `https://training-architect.com/api/dataset` | Return the curated dataset |
| `POST` | `https://training-architect.com/api/validate` | Validate raw plan JSON without uploading it |
| `POST` | `https://training-architect.com/api/upload` | Validate and upload raw plan JSON |

Every request requires the athlete's intervals.icu credentials in these headers:

```text
X-Intervals-Athlete-Id: <your-athlete-id>
X-Intervals-Api-Key: <your-api-key>
```

The validation and upload operations accept the raw plan JSON as the request body. Do not wrap it in another object.

### Retrieve the Dataset

```bash
curl "https://training-architect.com/api/dataset" \
  --header "X-Intervals-Athlete-Id: <your-athlete-id>" \
  --header "X-Intervals-Api-Key: <your-api-key>"
```

### Validate a Plan

```bash
curl --request POST "https://training-architect.com/api/validate" \
  --header "Content-Type: application/json" \
  --header "X-Intervals-Athlete-Id: <your-athlete-id>" \
  --header "X-Intervals-Api-Key: <your-api-key>" \
  --data-binary "@week_plan.json"
```

### Upload a Validated Plan

```bash
curl --request POST "https://training-architect.com/api/upload" \
  --header "Content-Type: application/json" \
  --header "X-Intervals-Athlete-Id: <your-athlete-id>" \
  --header "X-Intervals-Api-Key: <your-api-key>" \
  --data-binary "@week_plan.json"
```

For API clients, sending `POST /api/upload` is itself the explicit upload confirmation. Call it only after inspecting the plan and receiving a successful validation result.

The complete interactive OpenAPI specification is available at [training-architect.com/swagger](https://training-architect.com/swagger).

## Security and Privacy

The curated dataset contains personal training and wellness information. Paste it only into a GenAI service whose data handling and retention policies you accept.

The Athlete ID and API Key belong only in Training Architect or the required HTTP headers. Never paste the API key into a GenAI conversation, system prompt, source file, shared screenshot, or plan JSON.

## Limitations

Without MCP, the GenAI tool cannot independently refresh stale data or invoke validation and upload operations. The athlete or an external client controls each transfer and must ensure that the dataset is current.

Validation guarantees that the JSON follows the upload contract; it does not guarantee that the coaching decision is appropriate. The athlete should still review the plan against subjective readiness, illness, pain, schedule constraints, and real-world goals before uploading it.

This explicit handoff is also the workflow's main advantage: data access, AI reasoning, schema validation, and calendar modification remain visible as separate, reviewable steps.
