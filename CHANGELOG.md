# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.6.2] - 2026-06-22

### Added

- Added individually exposed MCP prompt endpoints backed by version-controlled files in `prompts/library/` for single workout analysis, weekly analysis, manual and automatic training-plan generation, fueling analysis, and metrics/wellness summary.
- Added Azure Table Storage persistence for OAuth dynamic client registrations in the webservice, using the existing storage account plus dedicated infrastructure wiring for the client registry table and RBAC assignments.

### Changed

- Updated prompt loading so coach prompts are resolved from `prompts/library/`, including deployment packaging for those prompt assets.
- Updated OAuth client handling so registrations survive app restarts and slot swaps via persistent storage, with application-managed cleanup of entries older than 200 days.

## [0.6.1] - 2026-06-13

### Changed

- Simplified wellness trend export in `scripts/get_metrics.py` to `current`, `avg_7d`, `avg_prev_7d`, and `trend_7d` for weight, resting HR, and HRV.
- Updated `notebooks/week_summary.ipynb` to display the simplified wellness trends in the athlete metrics section.
- Updated `coach-logic/input-schema.md` and `README.md` to document the simplified wellness trend fields.
- Added `docs/prompt_library.md` as a curated prompt library with copy-paste example prompts in German and English.
- Removed `training_availability` from coach-facing weekly plan payloads produced by the webservice MCP server and the file-based consolidation; planning now uses `week_type` + `day_constraints` (ensure the local `scripts/mcp_server.py` consolidation matches this schema as well).

## [0.6.0] - 2026-06-08

### Added

- Added version-controlled Foundry agent package (`foundry-agent/`) including `agent.yaml`, deployment/invocation scripts, requirements, and dedicated documentation.
- Added Foundry infrastructure-as-code (`foundry-agent/infra/main.bicep`, `foundry-agent/infra/main.bicepparam`) for account, project, model deployment, and role assignment setup.
- Added GitHub Actions workflows for Foundry agent deployment and Foundry infrastructure deployment (`.github/workflows/deploy-agent.yml`, `.github/workflows/infra-agent.yml`).
- Added runtime structured inputs for agent behavior and per-request auth forwarding: `discipline`, `response_language`, `intervals_athlete_id`, `intervals_api_key`.
- Added root-level deployment helper scripts (`setup.ps1`, `config.example.ps1`) to centralize local parameter generation and GitHub secret setup.
- Added Chainlit web app for testing the Foundry agent via simple chat application.

### Changed

- Updated `foundry-agent/agent.yaml` prompt behavior for deterministic application flow: no proactive "what next" prompts; final statements unless required input is missing.
- Updated MCP connector configuration in Foundry agent deployment to use the hosted Streamable HTTP endpoint and runtime header templating.
- Updated project documentation (`README.md`, `foundry-agent/README.md`, `webservice/README.md`) to reflect new structure, Foundry workflow, and RBAC requirements.
- Consolidated setup/config flow at repo root and removed legacy `webservice/setup.ps1`.

### Fixed

- Fixed workout-tag convention tests to align with renamed/updated workout library source (`coach-logic/workout-library.md`) and current table-based tag definitions.

## [0.5.1] - 2026-06-07

### Changed

- `metrics.sleep_quality` is now exported as a label (`GREAT`, `GOOD`, `AVG`, `POOR`) instead of the raw intervals.icu scale `1–4`, to avoid misinterpretation by the coach (`scripts/get_metrics.py`).
- `coach-logic/input-schema.md` updated to document the new `sleep_quality` label values.

## [0.5.0] - 2026-06-05

### Changed

- `prompts/system_prompt.md` optimized for clearer MCP-first workflow and more robust coaching outputs.
- Entire `coach-logic/` documentation set was refactored to remove redundancies and improve structure/clarity.
- Coach-logic module naming was standardized and updated in documentation references (`README.md`, `docs/gen_ai_setup_step_by_step.md`) to the new file set:
    - `coaching-principles.md`
    - `interpretation-rules.md`
    - `decision-process.md`
    - `training-zones.md`
    - `input-schema.md`
    - `workout-library.md`

## [0.4.0] - 2026-06-02

### Added

- New local script `scripts/list_workouts.py`: lists workout-library entries with key fields (`folder`, `name`, `duration`, `tss`, `tags`).
- New local script `scripts/list_shared_workouts.py`: lists workouts shared by a selected athlete ID (`--athlete-id`) with key fields (`shared_from`, `folder`, `name`, `duration`, `tss`, `tags`).
- New MCP methods `list_library_workouts` and `list_standard_library_workouts` in both `scripts/mcp_server.py` and `webservice/mcp_server.py`.
- Optional workout-tag filtering arguments for both MCP methods: `tag_prefixes`, `match_mode` (`any`/`all`), `include_untagged`, and `limit`.
- New regression test `tests/test_workout_tag_conventions.py` to validate workout tag format, known prefixes, and required dose suffix coverage.

### Changed

- Root and webservice documentation updated for the new workout scripts and MCP methods, including filter arguments and landing-page method descriptions.
- Webservice deployment wiring extended to propagate `STANDARD_LIBRARY_ATHLETE_ID` end-to-end (`webservice/config*.ps1`, `webservice/setup.ps1`, `webservice/infra/main.bicep`, `webservice/infra/modules/appservice.bicep`, `.github/workflows/infra.yml`).
- `coach-logic/workouts.md` now includes a tag naming hint section to document stable tag prefixes and dose suffixes used by prefix-based workout filters.
- `prompts/system_prompt.md` now documents all MCP coach methods: `prepare_week_data`, `get_latest_activities`, `list_library_workouts`, `list_standard_library_workouts`, and `upload_week_plan`.
- `prompts/system_prompt.md` now states that library workouts can be used as suggestions when their tags match the current goal, limiter, or requested session type.

## [0.3.5] - 2026-06-01

### Added

- Per-interval HR data in `coach_input` export: each activity now contains an `interval_segments` list with `avg_hr`, `max_hr`, `avg_power`, `intensity_pct`, `zone`, `type` (WORK/RECOVERY), and timing fields, fetched from the intervals.icu `/activity/{id}/intervals` endpoint.
- New local script `scripts/get_latest_activities.py`: reads the current `coach_input_{monday}.json` and prints a compact JSON summary (8 fields per activity) matching the output format of the webservice MCP tool `get_latest_activities`. Supports `--limit N` argument.
- `interval_segments` added to `coach-logic/input_schema.md` with full field documentation.

### Changed

- `notebooks/week_summary.ipynb`: new cell added to display the full `interval_segments` table and a WORK-only filtered view per activity.
- `README.md` and `coach-logic/input_schema.md` updated to reflect new fields and new script.
- Schema/project version bumped to `0.3.5`.
- Expanded cycling activity type filters to include `MountainBikeRide` and `GravelRide` (in `get_activities.py`, `prepare_activities_for_coach.py`, `analyze_week.py`, and `wbal_analysis.py`) so tagged MTB/gravel sessions are no longer dropped.
- Expanded `notebooks/week_summary.ipynb` with additional section explanations to improve readability and interpretation across key analysis blocks.
- Added repo-level pre-commit configuration (`.pre-commit-config.yaml`) with `nbstripout`, included tooling in `requirements.txt`, and documented setup in `README.md` to avoid notebook output-only diffs and commits.

## [0.3.4] - 2026-05-27

### Added

- New MCP tool `get_latest_activities(limit=10)` in `webservice/mcp_server.py` that returns a compact, latest-first activity list (`date`, `name`, `duration_hours`, `training_load`, `rpe`, `tags`) to reduce client-side truncation risk in long tool outputs.
- Landing page method list (`/`) now includes `get_latest_activities` alongside `prepare_week_data` and `upload_week_plan`.

### Changed

- Schema/project version bumped to `0.3.4` (source of `schema_version` in consolidated coach input payloads).
- Activity export order changed to newest-first in `scripts/prepare_activities_for_coach.py` so recent rides are visible first in truncated client responses.
- Documentation updated in `README.md` and `webservice/README.md` to reflect the new MCP method and activity ordering behavior.

## [0.3.3] - 2026-05-25

### Added

- `docs/gen_ai_setup_step_by_step.md`: new step-by-step guide for setting up GenAI tools as coach — covers coach logic preparation, MCP server setup (Claude.ai, ChatGPT, Microsoft Copilot Studio), and the typical weekly workflow with example prompts.
- Download link for `coach-logic/` directory as ZIP via download-directory.github.io added to the setup guide.

### Changed

- `README.md`: replaced MCP Server section with a structured "How to Use" section describing three usage options (Bits-and-Bytes, Managed MCP Server, Integrated Web App — coming soon).
- `README.md`: introduction updated to reflect that the project includes a publicly hosted MCP server, ready-to-use system prompts, and a coaching logic library.
- `prompts/system_prompt.md`: added "Date Handling (CRITICAL)" section instructing the model to derive all dates exclusively from `current_date` and `week_starting` in the input JSON, preventing date confusion in ChatGPT and Copilot.

## [0.3.2] - 2026-05-23

### Added

- Weather data section in coach input JSON (`prepare_activities_for_coach.py`): each activity now contains a `weather` object with `average_weather_temp`, `average_feels_like`, and `max_rain` from the intervals.icu weather service; `null` for indoor/GPS-less rides.
- Weather fields documented in `coach-logic/input_schema.md`.

### Improved

- MCP server authentication hardened: improved credential handling in the web service.

## [0.3.1] - 2026-05-20

### Added

- Activity notes (`description` field from intervals.icu) are now included in the coach input JSON and documented in `coach-logic/input_schema.md`.

## [0.3.0] - 2026-05-17

### Added

- MCP web service (`webservice/`) deployable as Azure App Service (Linux, Python 3.12).
- ASGI middleware stack: CORS + per-request credential injection via `X-Intervals-Athlete-Id` / `X-Intervals-Api-Key` headers.
- Azure Bicep infrastructure (`webservice/infra/`) with App Service Web App and deployment slots (`staging`, `dev`).
- GitHub Actions workflows: `infra.yml` (Bicep deploy), `preview.yml` (What-If PR comment), `deploy.yml` (selective zip deploy to slots).
- Renamed MCP tools: `prepare_week_data` (was `prepare_week_for_coach`) and `upload_week_plan` (was `upload_plan`).

## [0.2.0] - 2026-05-11

- First public release of the toolkit.
- Added W'bal (anaerobic work capacity) analysis script (`wbal_analysis.py`).
- Refined coaching prompts and coach-logic documentation.
- Added discipline-specific prompts (climber, criterium, marathon, road race).
- Improved MCP server with additional tools for AI assistant workflows.

## [0.1.0] - 2026-05-08

- Added scripts to fetch activities, athlete metrics, and training plans from intervals.icu.
- Added a weekly analysis workflow based on Joe Friel principles.
- Added a coach export pipeline for activities and planned workouts.
- Added fueling analysis and fueling planner workflows.
- Added a plan upload workflow back to intervals.icu.
- Added MCP server integration for AI assistant workflows.
- Added a Jupyter notebook for interactive weekly training review.
- Added coaching prompts and supporting coaching documentation.
