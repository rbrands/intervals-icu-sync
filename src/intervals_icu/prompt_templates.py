"""Helpers for loading coaching prompt templates from prompts/library."""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROMPT_FILE_NAMES = {
    "single_workout_analysis": "01_single_workout_analysis.md",
    "weekly_analysis": "02_weekly_analysis.md",
    "training_plan_generation_manual": "03a_training_plan_generation_manual.md",
    "training_plan_generation_automatic": "03b_training_plan_generation_automatic.md",
    "fueling_analysis": "04_fueling_analysis.md",
    "metrics_wellness_summary": "05_metrics_wellness_summary.md",
}

_PROMPT_ALIASES = {
    # Canonical names
    "single_workout_analysis": "single_workout_analysis",
    "weekly_analysis": "weekly_analysis",
    "training_plan_generation_manual": "training_plan_generation_manual",
    "training_plan_generation_automatic": "training_plan_generation_automatic",
    "fueling_analysis": "fueling_analysis",
    "metrics_wellness_summary": "metrics_wellness_summary",
    # Short aliases
    "single": "single_workout_analysis",
    "week": "weekly_analysis",
    "weekly": "weekly_analysis",
    "plan_manual": "training_plan_generation_manual",
    "plan_auto": "training_plan_generation_automatic",
    "fueling": "fueling_analysis",
    "metrics": "metrics_wellness_summary",
}

_DEFAULT_PROMPT = "weekly_analysis"


def _candidate_prompt_dirs() -> list[Path]:
    candidates: list[Path] = []

    # Explicit override for hosted/deployed environments.
    env_dir = os.environ.get("INTERVALS_PROMPTS_LIBRARY_DIR", "").strip()
    if env_dir:
        candidates.append(Path(env_dir).expanduser().resolve())

    # Common local/dev layout from workspace root.
    candidates.append((_REPO_ROOT / "prompts" / "library").resolve())

    # Runtime/layout fallbacks (e.g. packaged or temp execution dirs).
    file_path = Path(__file__).resolve()
    for parent in file_path.parents:
        candidates.append((parent / "prompts" / "library").resolve())

    candidates.append((Path.cwd() / "prompts" / "library").resolve())

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique


def _resolve_prompt_path(prompt_name: str) -> Path:
    file_name = _PROMPT_FILE_NAMES[prompt_name]
    tried: list[str] = []

    for prompt_dir in _candidate_prompt_dirs():
        candidate = prompt_dir / file_name
        tried.append(str(candidate))
        if candidate.exists():
            return candidate

    tried_lines = "\n".join(f"- {path}" for path in tried)
    raise FileNotFoundError(
        "Prompt file not found for "
        f"'{prompt_name}' ({file_name}). Tried:\n{tried_lines}\n"
        "Set INTERVALS_PROMPTS_LIBRARY_DIR to the absolute prompts/library path "
        "if your runtime does not include the repository root layout."
    )


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _normalize_prompt_name(name: str | None) -> str:
    if not name:
        return _DEFAULT_PROMPT
    normalized = name.strip().lower().replace("-", "_").replace(" ", "_")
    return _PROMPT_ALIASES.get(normalized, normalized)


def render_coach_prompt(prompt_name: str | None = None, response_language: str = "de") -> str:
    """Render a coaching prompt loaded from prompts/library.
    """
    normalized_language = (response_language or "en").strip() or "en"
    normalized_prompt_name = _normalize_prompt_name(prompt_name)

    if normalized_prompt_name not in _PROMPT_FILE_NAMES:
        available = ", ".join(sorted(_PROMPT_FILE_NAMES))
        raise ValueError(
            f"Unknown prompt '{prompt_name}'. Available prompts: {available}"
        )

    rendered = _read_text(_resolve_prompt_path(normalized_prompt_name))
    return f"{rendered}\n\nPlease respond in {normalized_language}.".strip()
