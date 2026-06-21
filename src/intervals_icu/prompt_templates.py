"""Helpers for loading coaching prompt templates from prompts/library."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROMPTS_DIR = _REPO_ROOT / "prompts" / "library"
_PROMPT_FILES = {
    "single_workout_analysis": _PROMPTS_DIR / "01_single_workout_analysis.md",
    "weekly_analysis": _PROMPTS_DIR / "02_weekly_analysis.md",
    "training_plan_generation_manual": _PROMPTS_DIR / "03a_training_plan_generation_manual.md",
    "training_plan_generation_automatic": _PROMPTS_DIR / "03b_training_plan_generation_automatic.md",
    "fueling_analysis": _PROMPTS_DIR / "04_fueling_analysis.md",
    "metrics_wellness_summary": _PROMPTS_DIR / "05_metrics_wellness_summary.md",
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

    if normalized_prompt_name not in _PROMPT_FILES:
        available = ", ".join(sorted(_PROMPT_FILES))
        raise ValueError(
            f"Unknown prompt '{prompt_name}'. Available prompts: {available}"
        )

    rendered = _read_text(_PROMPT_FILES[normalized_prompt_name])
    return f"{rendered}\n\nPlease respond in {normalized_language}.".strip()
