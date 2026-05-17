# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

- Placeholder for upcoming changes.

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
