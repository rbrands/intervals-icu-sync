# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

- Placeholder for upcoming changes.

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
