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
| `training_philosophy.md` | Underlying training principles based on Joe Friel |
| `coach_logic.md` | Coaching logic, data interpretation and decision framework |
| `decision_engine.md` | How the coach makes training decisions based on input data |
| `fueling_rules.md` | Fueling evaluation rules and their coaching impact |
| `training_zones.md` | Power, HR and RPE zone definitions used by the coach |
| `input_schema.md` | Description of the JSON input schema passed to the coach |
| `workouts.md` | Example workouts (VO2max, threshold, endurance) with dose levels and tags |

> **Note:** Feel free to adapt the system prompt and the coach-logic files to your own training philosophy and preferences. However, `input_schema.md` and the section in `system_prompt.md` that defines the output format for the training plan must remain unchanged — they ensure the AI interprets the data correctly and produces a plan that `upload_plan.py` (and the MCP server's `upload_week_plan` tool) can parse and upload correctly.

> **Keep your files up to date:** Check the [CHANGELOG](https://github.com/rbrands/intervals-icu-sync/blob/main/CHANGELOG.md) periodically for updates to the prompt and coach-logic files, and replace your uploaded copies when relevant changes are listed.

---

## Where to put it – ChatGPT, Claude and Microsoft Copilot

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

*No local Python installation needed — Claude fetches your data and uploads the plan directly.*

The public MCP server at [https://intervals-mcp.training-architect.com](https://intervals-mcp.training-architect.com) exposes the same two tools as the local setup:

| Tool | What it does |
|------|--------------|
| `prepare_week_data` | Fetches and consolidates all training data from intervals.icu and returns it as JSON — no file needed |
| `upload_week_plan` | Uploads a JSON training plan to your intervals.icu calendar as planned workout events |

In Claude, you can call tools directly via slash commands, e.g. `/prepare_week_data`.

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


# Section 03 – Typical Workflow

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

