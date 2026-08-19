# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [1.2.5] - 2026-08-19

### Added

- Added a new prompt, `06_consistency.md`, for data-quality checks of athlete completeness and internal consistency.
- Added the new consistency prompt to the MCP registration and prompt loader so it is available like the other library prompts.
- Added the new prompt section to the prompt library documentation in both German and English.

### Changed

- Updated the prompt library to include the new data-consistency workflow alongside the weekly analysis, planning, fueling, and metrics summary prompts.
- Kept the consistency prompt aligned with the MCP data-fetch pattern by loading data via `prepare_week_data` instead of a manual placeholder.
- Extended the metrics summary prompt to assess whether the athlete's discipline goal fits the current power profile and to highlight the main gap between the current profile and the target discipline demands.

## [1.2.4] - 2026-08-17

### Changed

- Updated automatic training-plan prompts to derive phase, week type, day constraints, and the authoritative weekly TSS target from the target-week entry in `week_summary.training_plan` instead of the legacy next-week fields.
- Updated German and English prompt-library examples to prohibit falling back to another week's target or using a time target as a replacement for the weekly TSS target.

## [1.2.3] - 2026-08-16

### Added

- Added MCP tool `check_plan_tss` plus the local CLI `scripts/check_plan_tss.py` to validate per-workout TSS against deterministic step-based math and weekly load against a target tolerance.
- Added the tool to the MCP landing-page method list so it is visible on the server homepage.
- Added regression coverage to assert the checker catches mismatched workout TSS and weekly target deviations.

### Changed

- Updated the README usage and script list to include the new TSS-check workflow.

## [1.2.2] - 2026-08-16

### Fixed

- Fixed planned library workouts that omit `workout_doc`/`steps` so the stored library TSS is preserved instead of being dropped from the weekly load total.
- Added regression coverage to ensure a library-backed workout without explicit steps still carries its `icu_training_load` value into the uploaded planned event.

### Added

- Added a new MCP tool, `get_activity_streams_sampled`, to fetch compact, down-sampled activity streams for a single activity without returning the full raw payload.
- Added the matching local entrypoint `scripts/get_activity_streams_sampled.py`, which follows the repo's normal `python scripts/...py` workflow and accepts the same single-activity filters (`--id`, `--streams`, `--max-points`, `--start-time-s`, `--end-time-s`, `--start-distance-m`, `--end-distance-m`).
- Added the `id` field to the compact activity list returned by `scripts/get_latest_activities.py`, so the output can be used directly as the input for the stream-sampling script.
- The new tool supports filtering by `stream_types`, `max_points`, `start_time_s`, `end_time_s`, `start_distance_m`, and `end_distance_m`, which makes it practical to inspect sub-km variations in time, distance, altitude, heart rate, and velocity.
- Documented the tool in both MCP server entry points and the webservice README so the parameters and intended usage are clear to clients.

## [1.2.0] - 2026-08-15

### Added

- Added `library_workout_id` to MCP workout-library results and week-plan uploads so the agent can select a tagged library workout and copy its stored structure to the calendar.
- Added a deterministic workflow to the concrete planning prompts that queries the workout library once per plan after deriving all required tags, validates exact tag suitability, and falls back to generated workout steps when no match exists.

### Changed

- Updated manual and automatic planning prompts to calculate TSS consistently from generated workout steps, selected library workout TSS, and anchored planned workouts.
- Added final planning self-checks for per-workout TSS consistency, manual duration limits, and automatic weekly load targets within ±10% unless constraints or fatigue justify a deviation.
- Synchronized the executable planning prompts and all German/English examples in `docs/prompt_library.md`, while keeping workout-library orchestration out of the system prompts.

### Removed

- Removed the unsupported shared workout library script and MCP tool because intervals.icu does not expose shared folder workouts through its public API.
- Removed the corresponding Foundry agent tool registration, prompts, deployment configuration, and documentation.

## [1.1.0] - 2026-08-10

### Added

- Added top-level `training_load_history` to coach input payloads with target load, actual Ride load, and achievement percentage for the last four completed calendar weeks.
- Added server-side weekly load aggregation through the intervals.icu athlete-summary API, without relying on historical local exports.

### Changed

- Updated weekly analysis and automatic planning guidance to use the four-week load history as secondary context, identify repeated target deviations, and never compensate for missed historical load.

## [1.0.1] - 2026-08-03

### Changed

- Updated `scripts/get_metrics.py` to normalize athlete weight to kilograms (kg) when intervals.icu reports `weight_pref_lb=true`.
- Updated `scripts/get_metrics.py` to apply the same lbs→kg normalization to `metrics.wellness_trends.weight` values (`current`, `avg_7d`, `avg_prev_7d`).
- Updated `README.md` and `coach-logic/input-schema.md` to document that exported weight values are always in kg.

## [1.0.0] - 2026-08-02

### Added

- Added optional `day_constraints[].max_training_time_hours` export derived from intervals.icu `max_training_time` for constrained days.
- Added regression test `tests/test_week_summary_readiness_fields.py` to enforce that consolidated `coach_input` keeps `ctl`/`atl` under `week_summary` (and not under `metrics`).
- Added regression coverage in `tests/test_training_plan_phase_regressions.py` to ensure NOTE constraints prefer explicit availability over label keyword inference.

### Changed

- Updated `scripts/get_training_plan.py` so day constraints include the per-day training time cap when provided by intervals.icu.
- Fixed day-constraint derivation in `scripts/get_training_plan.py`: for `NOTE` events, explicit `training_availability` (for example `LIMITED`) now takes precedence over keyword-based label classification (for example `Reisetag`/`Abreise`).
- Updated planning docs/prompts to enforce `max_training_time_hours` as a hard daily duration cap on constrained days.
- Updated `README.md` to document the precedence rule for NOTE-based day constraints.
- Removed `metrics.w_prime_wellness` from exported week data (`scripts/get_metrics.py`) and aligned schema/contracts/docs accordingly.
- Moved readiness snapshot fields `ctl` and `atl` from top-level `metrics` to `week_summary` in consolidated `coach_input` payloads (no duplicated values); aligned generation scripts, schema/contracts, notebook, and docs.
- Pinned `mcp[cli]` to `<2` in dependency files to keep compatibility with `from mcp.server.fastmcp import FastMCP` used by the MCP server entrypoints.

## [0.6.9] - 2026-07-24

### Changed

- Updated `scripts/get_metrics.py` so `metrics.w_prime` falls back to `icu_rolling_w_prime` when `icu_w_prime` is missing or `0`.
- Updated `scripts/prepare_activities_for_coach.py` to apply the same fallback for ride-level W' fields (`w_prime_j`, `w_prime_bal_min_j`, `w_prime_usage_pct`) and for W'bal computation.
- Updated `README.md` to document the ride-level W' fallback behavior.

## [0.6.8] - 2026-07-20

### Changed

- Fixed week phase inheritance in the webservice MCP path so next-week planning no longer reuses the previous week's phase when intervals.icu has no active phase for the current week.

## [0.6.7] - 2026-07-19

### Changed

- Updated weekly training-plan target handling so TSS remains the primary goal when present, while time targets act as an upper cap and time-only targets use `weekly_time_target_hours`.
- Clarified the phase summary so boundary-week phases are not inherited into the next week when no active next-week phase exists.

## [0.6.6] - 2026-07-11

### Changed

- Removed `ride_type` from the generated training-plan JSON contract in `prompts/system_prompt.md` and `foundry-agent/agent.yaml`; ride intent is now derived from workout tags downstream.
- Simplified the generated plan contract to require only a non-empty `tags` array; a single tag must now also be emitted as a one-item `tags` list.
- Updated `scripts/fueling_planner.py` to derive the primary fueling ride type from workout tags when `ride_type` is absent, while still honoring legacy payloads that include `ride_type`.
- Updated documentation (`README.md`, `docs/gen_ai_setup_step_by_step.md`, `coach-logic/decision-process.md`) to match the tag-only plan format and the tag-derived ride-type behavior.
- Updated decoupling (aerobic durability) classification to be zone-distribution aware instead of duration/ride-type based: only classifies durability for rides with Z1+Z2 ≥ 80% (full validity); shows `"limited durability signal"` for rides with Z1+Z2 60–80% (marginal endurance); returns `null` for rides with Z1+Z2 < 60% (not applicable).
- Updated `scripts/prepare_activities_for_coach.py` to pass `z1_z2_pct` to `_classify_decoupling()` and use zone distribution instead of duration/ride classification.
- Updated `scripts/analyze_week.py` to filter decoupling values to only include rides with Z1+Z2 ≥ 80% when computing weekly average; shows `"no durability data"` if no eligible rides exist.
- Updated documentation (`README.md`, `coach-logic/interpretation-rules.md`) to reflect zone-based decoupling validity thresholds.
- Added `metrics.ftp_classification` in `scripts/get_metrics.py` based on FTP W/kg, age group, and sex (including `w_per_kg`, `category_range`, `next_category`, and `delta_to_next`).
- Updated week-data contracts and schema models (`src/intervals_icu/week_data_schema.py`, `contracts/week-data/week-data.schema.json`, `contracts/week-data/WeekDataDto.cs`) to include `metrics.ftp_classification` and keep FTP W/kg only inside `ftp_classification.w_per_kg`.
- Updated documentation (`README.md`, `coach-logic/input-schema.md`) to describe FTP W/kg as part of `ftp_classification`.
- Added regression coverage in `tests/test_get_metrics_ftp_classification.py` for FTP classification mapping.

### Added

- Added regression coverage in `tests/test_workout_tag_conventions.py` for tag-based fueling-plan inference, including multi-tag sessions.
- Added upload-plan JSON Schema at `contracts/week-plan/week-plan.schema.json`, covering both accepted input shapes (`[...]` and `{ "week": "...", "workouts": [...] }`) and workout/step fields used by `scripts/upload_plan.py`.
- Added `scripts/validate_plan.py` to validate plan JSON files against `contracts/week-plan/week-plan.schema.json` before running `upload_plan.py`.
- Documented the validation step and new script usage in `README.md`.
- Added MCP tool `validate_week_plan` in both local and webservice MCP servers to validate plan JSON against the upload schema before `upload_week_plan`.
- Added `metrics.vo2max_classification` in `scripts/get_metrics.py` based on VO2Max (ml/kg/min), age group (teen 13–19, adult 20–29, master 30–39, 40–49, grand master 50–59, senior 60+), and sex (male/female). Classification categories: *very poor*, *poor*, *average*, *good*, *very good*, *excellent*. Includes `ml_per_kg_min`, `age_group`, `sex`, `category`, `category_range` (min/max), `next_category`, and `delta_to_next`.
- Updated week-data contracts and schema models (`src/intervals_icu/week_data_schema.py`, `contracts/week-data/week-data.schema.json`, `contracts/week-data/WeekDataDto.cs`) to include `metrics.vo2max_classification`.
- Updated documentation (`README.md`, `coach-logic/input-schema.md`) to describe VO2Max classification.
- Added regression coverage in `tests/test_get_metrics_vo2max_classification.py` for VO2Max classification mapping across all age groups and sex combinations.

## [0.6.5] - 2026-07-05

### Changed

- Updated `prepare_week_data` outputs (local and webservice MCP tools) to merge per-activity fueling details from `fueling_analysis.activities` into each `activities[]` item as nested `fueling`, matched by `date`.
- Removed `fueling_analysis.activities` from consolidated `coach_input` output; kept `fueling_analysis.weekly_summary` and `fueling_analysis.recommendations`.
- Updated local consolidation script `scripts/prepare_week_for_coach.py` to apply the same merge/removal behavior for file-based `coach_input` generation.
- Updated schema models/contracts to reflect the new shape: added `FuelingDetail`, added `activities[].fueling`, and removed `FuelingAnalysis.activities`.
- Updated `scripts/fueling_planner.py` to use `activities[].fueling` (with backward-compatible fallback to legacy `fueling_analysis.activities`).
- Replaced per-segment activity export field `interval_segments` with compact `interval_hr_analysis` in `scripts/prepare_activities_for_coach.py`, including `hr_start_avg`, `hr_end_avg`, `hr_drift_pct`, and `hr_power_decoupling`.
- Added eligibility thresholds for interval HR analysis so only WORK intervals with at least 120 seconds and at least 95% FTP intensity are considered.
- Added optional `lookback_days` parameter (default `7`) to MCP tool `prepare_week_data` in both local and webservice servers.
- Switched activity/fueling preparation windows to a sliding lookback filter (`activity.date >= current_date - timedelta(days=lookback_days)`) in `prepare_activities_for_coach.py` and `fueling_analysis.py` (without changing calendar-week `week_summary` aggregation).
- Updated the week-data contracts and schema models (`src/intervals_icu/week_data_schema.py`, `contracts/week-data/week-data.schema.json`, `contracts/week-data/WeekDataDto.cs`) to use `interval_hr_analysis`.
- Updated documentation (`README.md`, `coach-logic/input-schema.md`) to describe the new interval HR summary fields and their thresholds.
- Updated `notebooks/week_summary.ipynb` to display `interval_hr_analysis` instead of `interval_segments`.

### Fixed

- Fixed notebook loading in `notebooks/week_summary.ipynb` to support both consolidated `coach_input` payloads (dict) and activities-only exports (list), preventing `TypeError: list indices must be integers or slices, not str`.

## [0.6.3] - 2026-06-26

### Changed

- Clarified tag usage rules in `prompts/system_prompt.md` and `foundry-agent/agent.yaml`: workouts may use multiple tags, each tag maps independently to ride intent, and plan outputs must include at least one valid canonical tag.
- Updated coach-logic guidance (`coach-logic/interpretation-rules.md`, `coach-logic/decision-process.md`, `coach-logic/workout-library.md`) to align limiter detection and workout selection with the canonical tag scheme (`<domain>-<level>`).
- Refined documentation in `README.md` and `docs/gen_ai_setup_step_by_step.md` to make tag-driven prompt behavior and practical tag usage clearer for manual and MCP-based workflows.

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
