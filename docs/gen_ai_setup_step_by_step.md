# Setup GenAI tools as Coach with intervals 

# Section 01 - Prepare Coach Logic

*System prompt, athlete profiles, and coaching domain knowledge.*

## Coaching Logic – two directories

The coaching system is split across two directories that you assemble before talking to your AI coach.

**`prompts/system_prompt.md`**
The base system prompt for the LLM. Contains a placeholder block where you insert the matching athlete profile.

**`coach-logic/`**
Modular documentation of the coaching domain knowledge — training philosophy, decision logic, fueling rules, zones, schema and example workouts.

---

## System prompt – swap in the athlete profile

The base prompt `prompts/system_prompt.md` contains a placeholder:

```
## Athlete Profile
<<INSERT ATHLETE / DISCIPLINE BLOCK HERE>>
```

Before passing the prompt to the coach, copy the contents of the matching `discipline_*.md` file into that block:

| File | Athlete type |
|------|--------------|
| `discipline_climber.md` | Climber / FTP-focused athlete |
| `discipline_criterium.md` | Criterium racer / W' and repeatability focus |
| `discipline_roadrace.md` | Road racer / aerobic durability and FTP focus |
| `discipline_marathon.md` | Mountain marathon rider / aerobic durability + climbing endurance focus |

---

## `coach-logic/` – domain knowledge modules

Modular markdown files describing the coaching domain knowledge — share them with your AI coach alongside the system prompt.

[Download all files as ZIP](https://download-directory.github.io/?url=https%3A%2F%2Fgithub.com%2Frbrands%2Fintervals-icu-sync%2Ftree%2Fmain%2Fcoach-logic)

| File | Content |
|------|---------|
| `coaching-principles.md` | Training philosophy and foundational coaching principles based on Joe Friel |
| `interpretation-rules.md` | Data interpretation thresholds and classifier rules (form, fueling, limiter detection) |
| `decision-process.md` | How interpreted data is turned into concrete weekly planning actions |
| `training-zones.md` | Power, HR and RPE zone definitions used by the coach |
| `input-schema.md` | Description of the JSON input schema passed to the coach |
| `workout-library.md` | Workout catalog by domain and dose level, including canonical tags |

> **Note:** Feel free to adapt the system prompt and the coach-logic files to your own training philosophy and preferences. However, keep `input-schema.md` and the plan JSON output contract in `system_prompt.md` **compatible** with `upload_plan.py` / `upload_week_plan` (required per workout: `date`, `name`, `duration_minutes`; optional: `description`, `tag`/`tags`, `steps`).

> **Keep your files up to date:** Check the [CHANGELOG](https://github.com/rbrands/intervals-icu-sync/blob/main/CHANGELOG.md) periodically for updates to the prompt and coach-logic files, and replace your uploaded copies when relevant changes are listed.

---

## Where to put it – ChatGPT, Claude, Mistral AI and Microsoft Copilot

### ChatGPT

**Create a Project**

- Sidebar → **Projects → New project**
- Open the project

**Instructions**
Paste the contents of `system_prompt.md` (with the discipline block already inserted).

**Files**
Upload all files from `coach-logic/` here. Easy to update. ([Download as ZIP](https://download-directory.github.io/?url=https%3A%2F%2Fgithub.com%2Frbrands%2Fintervals-icu-sync%2Ftree%2Fmain%2Fcoach-logic))

### Claude

**Create a Project**

- Sidebar → **Projects → New project**
- Open the project settings

**Custom instructions**
Paste the contents of `system_prompt.md` (with the discipline block already inserted).

**Project knowledge**
Upload all files from `coach-logic/` here. ([Download as ZIP](https://download-directory.github.io/?url=https%3A%2F%2Fgithub.com%2Frbrands%2Fintervals-icu-sync%2Ftree%2Fmain%2Fcoach-logic))

### Mistral AI

**Open Mistral AI**

Go to [https://chat.mistral.ai](https://chat.mistral.ai) and sign in.

**Create a project**

- Create a new project
- Open the project settings

**System prompt**

Paste the contents of `system_prompt.md` (with the discipline block already inserted).

**Project files / knowledge**

Upload all files from `coach-logic/` to the project knowledge/files area. ([Download as ZIP](https://download-directory.github.io/?url=https%3A%2F%2Fgithub.com%2Frbrands%2Fintervals-icu-sync%2Ftree%2Fmain%2Fcoach-logic))

### Microsoft Copilot

**Open Copilot Studio**

Go to [https://copilotstudio.microsoft.com](https://copilotstudio.microsoft.com) and sign in.

**Create a new agent**

Select **"Agent → Create agent from scratch"**, enter a name (e.g. *Intervals.icu Coach*) and a short description.

**Add the system prompt**

Under **"Instructions"**, paste the contents of `system_prompt.md` with the matching discipline block already inserted (see Section 01).

**Add coaching knowledge**

Under **"Knowledge"**, upload all files from the `coach-logic/` directory. ([Download as ZIP](https://download-directory.github.io/?url=https%3A%2F%2Fgithub.com%2Frbrands%2Fintervals-icu-sync%2Ftree%2Fmain%2Fcoach-logic))


---
# Section 02 – Using the Managed MCP Server

*No local Python installation needed — your AI tool fetches your data and uploads the plan directly via MCP.*

The public MCP server at [https://intervals-mcp.training-architect.com](https://intervals-mcp.training-architect.com) exposes the same tools as the local setup:

| Tool | What it does |
|------|--------------|
| `prepare_week_data` | Fetches and consolidates all training data from intervals.icu and returns it as JSON — no file needed |
| `get_latest_activities` | Returns a compact latest-first list of activities (useful when full outputs are too long/truncated) |
| `list_library_workouts` | Lists workouts from your own intervals.icu workout library (including tags/folders) to reuse matching sessions in the plan |
| `list_standard_library_workouts` | Lists workouts from the shared standard library to suggest proven sessions by tag/domain |
| `upload_week_plan` | Uploads a JSON training plan to your intervals.icu calendar as planned workout events |

> **Important:** Tag your workouts consistently in intervals.icu so library filtering and workout suggestions work reliably. Use the same tag scheme as in `coach-logic/workout-library.md` (for example `vo2max-high`, `lactate-threshold-moderate`, `aerobic-threshold-low`).

In MCP-capable chat tools, you can call tools directly (depending on client UX), e.g. `prepare_week_data` or `get_latest_activities`.

---

## One-time setup – Claude.ai

**1 — Open Settings**

Go to **claude.ai → Customize → Connectors → + Add Connector → Add custom connector** and add a new MCP server.

**2 — Enter the server URL**
Name e.g. "intervals-icu-sync"

URL:

```
https://intervals-mcp.training-architect.com/mcp
```

**3 — Authenticate**

Claude and other MCP-capable AI tools open the login form automatically. Enter your intervals.icu **Athlete ID** and **API Key** (found under *Settings → Developer Settings* in intervals.icu). 

---

## One-time setup – ChatGPT

**1 — Enable Developer Mode**

Go to **Settings → Apps → Advanced Settings** and enable **Developer Mode**.

**2 — Create a connector**

Select **"Create App"**, then fill in the fields:

| Field | Value |
|-------|-------|
| Name | e.g. `intervals-icu-sync` |
| URL | `https://intervals-mcp.training-architect.com/mcp` |
| Authentication | OAuth 2.0 |

**3 — Authenticate**

ChatGPT opens the login form automatically. Enter your intervals.icu **Athlete ID** and **API Key** (found under *Settings → Developer Settings* in intervals.icu).

---

## One-time setup – Mistral AI

**1 — Open the connector settings in your project**

In your Mistral project, open:

- **Context**
- **Connectors**
- **Add connector**

**2 — Add the MCP connector**

Configure the connector with this server URL:

```
https://intervals-mcp.training-architect.com/mcp
```

Use a recognizable name, e.g. `intervals-icu-sync`.

**3 — Authenticate**

When prompted, sign in with your intervals.icu **Athlete ID** and **API Key** (found under *Settings → Developer Settings* in intervals.icu).

**Important for daily use**

For each new chat inside the project, add the connector again via **+** before asking for tool calls.

---

## One-time setup – Microsoft Copilot Studio

**1 — Connect the MCP server**

Under **"Tools"**, select **"Add tools → Add new → MCP"**.

Fill in the fields:

| Field | Value |
|-------|-------|
| Server name | e.g. `intervals-icu-sync` |
| Description | `Reads and writes training data from/to intervals.icu` |
| Server URL | `https://intervals-mcp.training-architect.com/mcp` |
| Authentication | OAuth 2.0 — **"Dynamic discovery"** |

**2 — Create a connection**

Select **"Create new connection"** and enter your intervals.icu **Athlete ID** and **API Key** (found under *Settings → Developer Settings* in intervals.icu).

**3 — Publish**

Select **Publish** to make the agent available.

---


# Section 03 – Set Up Phase Planning in intervals.icu

*Define season phases and weekly TSS targets so the coach can evaluate plan adherence correctly.*

Before running weekly coaching via MCP, set up your phase plan in intervals.icu.
This enables `prepare_week_data` to include the active phase and weekly load targets
in the `training_plan` section of the coach input.

## Why this matters

- The coach can compare your completed week against a planned weekly TSS target.
- Recommendations become phase-aware (Base vs Build vs Peak vs Transition).
- Weekly guidance is more realistic when target load and availability are known.

## Step-by-step in intervals.icu

1. Open the **Activities** page and go to **Plan Builder** (Targets Generator).
2. Set your A-event / season goal date.
3. Click **Targets Generator**.
4. Set your available **hours per week** in the generator.
5. Keep **Target Types = Load** enabled so your weekly time budget is translated into weekly TSS targets.
6. Create your phases (typically **Base**, **Build**, **Peak**, **Transition**).
7. Review and adjust the generated weekly TSS targets per phase if needed.
8. Place the generated targets on the calendar and save.

## Minimum setup recommendation

- At least one active phase for the current period.
- Weekly TSS targets for the current week and next week.
- Optional: set `week_type` (e.g. NORMAL / RECOVERY / RACE) if you use it.

> **Tip:** Re-open Targets Generator whenever your availability or race goals change.
> Keeping phase blocks and weekly targets up to date significantly improves coaching quality.

---

# Section 04 – Typical Workflow

*How you use the tool every week/daily with your AI coach.*

## After every ride – log in intervals.icu

For the coaching assessment to be meaningful, enter the following in intervals.icu after each ride:

- **RPE** (Rate of Perceived Exertion, scale 1–10) — required for session quality analysis
- **Carbohydrates consumed** (grams) — required for fueling analysis
- **Description / Notes** *(optional but recommended)* — a short comment on how the ride felt, any issues, or context the coach should know about

The more consistently you log these, the better the coaching output.

---

## Step 1 – Prepare the week and share with your coach

**Claude shortcut (direct tool call)**

Type this in Claude to run the data fetch immediately:

```
/prepare_week_data
```

Then ask for the interpretation/assessment in a second message.

If you only want a quick latest-ride check (compact output):

```
/get_latest_activities
```

Optional with explicit limit (if supported by your client UI):

```
/get_latest_activities {"limit": 5}
```

**Example prompt – weekly assessment via MCP**

> Today is {{TODAY}}, current week started {{WEEK_STARTING}}.
> Please use the `prepare_week_data` tool to fetch my training data for this week, then give me a coaching assessment covering:
>
> - **Training load and quality** — total load, session types (VO2max / Threshold / Endurance), aerobic decoupling
> - **Athlete metrics** — FTP, CTL/ATL, Form (%), HRV, weight
> - **Fueling quality** — carbohydrate intake per session, fueling ratio, any underfueled rides
> - **Training plan progress** — how the week aligns with the active plan and weekly TSS target
> - **Key observations and recommendations** — what went well, what needs attention
>
> Please hold off on creating next week's training plan for now — I'd like to discuss the assessment first.
> **Note:** `prepare_week_data` fetches all data live from intervals.icu — the call may take up to a minute depending on your data volume.


## Step 2 – Get the plan back and upload it

After discussing the assessment, ask Claude to create the plan and upload it:

> Based on our discussion, please create a training plan for next week and upload it directly to my intervals.icu calendar using the `upload_week_plan` tool. Show me the plan first and wait for my confirmation before uploading.

---

