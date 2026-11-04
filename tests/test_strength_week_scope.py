import importlib.util
import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


analyze_week = _load_module("analyze_week_strength_scope_script", "scripts/analyze_week.py")
fueling_analysis = _load_module(
    "fueling_analysis_strength_scope_script", "scripts/fueling_analysis.py"
)
prepare_week = _load_module(
    "prepare_week_strength_scope_script", "scripts/prepare_week_for_coach.py"
)
prepare_activities = _load_module(
    "prepare_activities_strength_scope_script", "scripts/prepare_activities_for_coach.py"
)
from intervals_icu import week_data_schema
client = _load_module("intervals_icu_client_strength_scope", "src/intervals_icu/client.py")


def _raw_activity(activity_type: str, load: int, moving_time: int, **overrides) -> dict:
    activity = {
        "id": activity_type,
        "type": activity_type,
        "source": "GARMIN",
        "start_date_local": date.today().isoformat() + "T09:00:00",
        "icu_training_load": load,
        "moving_time": moving_time,
        "tags": [],
    }
    activity.update(overrides)
    return activity


class StrengthReadinessPromptTests(unittest.TestCase):
    def test_readiness_only_limits_session_not_weekly_strength_frequency(self):
        for relative_path in (
            "coach-logic/decision-process.md",
            "prompts/system_prompt.md",
            "foundry-agent/agent.yaml",
        ):
            with self.subTest(path=relative_path):
                text = " ".join((REPO_ROOT / relative_path).read_text(encoding="utf-8").split())
                if relative_path == "foundry-agent/agent.yaml":
                    self.assertIn("readiness never reduces weekly strength frequency", text)
                    self.assertIn(
                        "Same-day readiness: yellow → no `strength-maximum` today, "
                        "red → no strength today",
                        text,
                    )
                else:
                    self.assertIn(
                        "Yellow/red readiness never reduces weekly strength frequency "
                        'or makes "one session is enough".',
                        text,
                    )
                    self.assertIn(
                        "yellow readiness excludes a `strength-maximum` session on that date "
                        "and red excludes strength on that date.",
                        text,
                    )
                self.assertNotIn("reduced to one for RECOVERY", text)
                # Current-week readiness applies to today's date only.
                self.assertNotIn("today and tomorrow", text)
                self.assertNotIn("today/tomorrow", text)
                if relative_path != "foundry-agent/agent.yaml":
                    self.assertIn("Never exclude tomorrow because of today's readiness.", text)

    def test_race_event_in_normal_week_does_not_disable_strength(self):
        """Only week_type RACE limits strength; a planned race event alone
        (e.g. a weekly Zwift club race) must not drop weekly strength."""
        for relative_path in (
            "coach-logic/decision-process.md",
            "prompts/system_prompt.md",
            "foundry-agent/agent.yaml",
        ):
            with self.subTest(path=relative_path):
                text = " ".join((REPO_ROOT / relative_path).read_text(encoding="utf-8").split())
                self.assertIn("`week_type: RACE`", text)
                if relative_path == "foundry-agent/agent.yaml":
                    self.assertIn(
                        "a race event in a NORMAL week only blocks the race day",
                        text,
                    )
                else:
                    self.assertIn("excludes only the race day itself", text)
                self.assertIn("never reduces weekly strength frequency", text)
                self.assertNotIn("RACE week: plan strength", text)


class StrengthFuelingScopeTests(unittest.TestCase):
    def test_strength_is_excluded_from_fueling_analysis_and_weekly_averages(self):
        ride = {
            "type": "Ride",
            "date": date.today().isoformat(),
            "name": "Long ride",
            "duration_hours": 3,
            "carbs_ingested_g": 30,
            "carbs_used_g": 100,
            "decoupling": 11,
            "rpe": 8,
            "tags": [],
        }
        strength = {
            "type": "WeightTraining",
            "date": date.today().isoformat(),
            "name": "Strength",
            "duration_hours": 2,
            "carbs_ingested_g": 200,
            "carbs_used_g": 200,
            "tags": ["strength-maximum"],
        }
        ride_only = fueling_analysis._filter_by_lookback([ride])
        ride_and_strength = fueling_analysis._filter_by_lookback([ride, strength])
        ride_summary = fueling_analysis.summarize_week(
            [fueling_analysis.analyze_activity(activity) for activity in ride_only]
        )
        combined_summary = fueling_analysis.summarize_week(
            [fueling_analysis.analyze_activity(activity) for activity in ride_and_strength]
        )

        self.assertEqual(len(ride_and_strength), 1)
        self.assertEqual(combined_summary, ride_summary)
        self.assertIsNone(fueling_analysis.classify_ride(strength))
        self.assertIsNone(
            fueling_analysis.classify_ride(
                {"type": "Ride", "tags": ["strength-maintenance"]}
            )
        )

    def test_strength_does_not_change_fueling_form_analysis(self):
        fueling_data = {
            "weekly_summary": {
                "avg_carbs_per_hour": 55,
                "number_of_underfueled_sessions": 0,
                "number_of_long_rides": 1,
                "avg_fueling_ratio": 0.6,
            },
            "activities": [{"name": "Long ride", "carbs_per_hour": 45}],
        }
        ride = {
            "name": "Long ride",
            "type": "Ride",
            "moving_time": 3 * 3600,
            "training_distribution": "Base",
            "decoupling": 9.2,
        }
        strength = {
            "name": "Strength",
            "type": "WeightTraining",
            "moving_time": 3 * 3600,
            "training_distribution": "Base",
            "decoupling": 12,
            "tags": ["strength-maximum"],
        }

        ride_result = analyze_week.analyse_fueling_form(-0.35, fueling_data, [ride])
        combined_result = analyze_week.analyse_fueling_form(
            -0.35, fueling_data, [ride, strength]
        )

        self.assertEqual(combined_result, ride_result)

    def test_consolidation_does_not_attach_fueling_to_strength(self):
        activities = [
            {"type": "WeightTraining", "date": "2026-11-01", "name": "Strength"},
            {"type": "Ride", "date": "2026-11-01", "name": "Ride"},
        ]
        fueling = {
            "activities": [
                {
                    "date": "2026-11-01",
                    "name": "Ride",
                    "fueling_status": "fueling required",
                }
            ],
            "weekly_summary": {"avg_carbs_per_hour": 60},
        }

        merged, cleaned = prepare_week._merge_fueling_into_activities(activities, fueling)

        self.assertNotIn("fueling", merged[0])
        self.assertEqual(merged[1]["fueling"], {"fueling_status": "fueling required"})
        self.assertNotIn("activities", cleaned)


class StrengthWeekSummaryTests(unittest.TestCase):
    def test_strength_without_load_counts_toward_phase_week_and_hard_recency(self):
        for load in (None, 0):
            with self.subTest(load=load):
                activity = _raw_activity(
                    "WeightTraining", load, 3600, tags=["strength-maximum"],
                )
                kept = analyze_week.filter_activities([activity])
                week = analyze_week.compute_metrics(kept)
                history = prepare_week.build_strength_history([activity], [])
                strength = prepare_week.build_strength_week_summary(history, date.today(), week)
                self.assertEqual(history[0]["training_load"], load)
                self.assertEqual(strength["phase_session_count"], 1)
                self.assertEqual(strength["sessions_this_week"], 1)
                self.assertEqual(week["strength_load"], 0)
                self.assertEqual(strength["weekly_strength_load"], 0)
                exported = prepare_activities.extract_fields(
                    prepare_activities.filter_activities([activity])[0]
                )
                self.assertEqual(exported["training_load"], load)
                annotated = prepare_week.annotate_hard_sessions([exported])
                self.assertTrue(annotated[0]["is_hard_session"])
                self.assertEqual(week["days_since_last_hard_session"], 0)

    def test_sample_strength_activity_does_not_change_ride_run_totals(self):
        rides = [
            _raw_activity("Ride", 100, 3600),
            _raw_activity("VirtualRide", 80, 7200),
            _raw_activity("MountainBikeRide", 55, 5400),
            _raw_activity("GravelRide", 50, 1800),
        ]
        strength = _raw_activity(
            "WeightTraining",
            9,
            3600,
            tags=["strength-maximum"],
            decoupling=12,
            icu_zone_times=[{"id": "Z5", "secs": 3600}],
        )

        without_strength = analyze_week.compute_metrics(rides)
        with_strength = analyze_week.compute_metrics(rides + [strength])

        self.assertEqual(analyze_week.filter_activities([strength]), [strength])
        self.assertEqual(with_strength["total_training_load"], 285)
        self.assertEqual(with_strength["total_training_load"], without_strength["total_training_load"])
        self.assertEqual(with_strength["number_of_activities"], 4)
        self.assertEqual(with_strength["total_time_hours"], without_strength["total_time_hours"])
        self.assertEqual(with_strength["longest_activity_hours"], without_strength["longest_activity_hours"])
        self.assertEqual(with_strength["ride_load"], 285)
        self.assertEqual(with_strength["strength_load"], 9)
        self.assertEqual(with_strength["strength_sessions"], 1)
        self.assertEqual(with_strength["strength_time_hours"], 1)
        self.assertEqual(with_strength["ride_sessions"], 4)
        self.assertEqual(with_strength["ride_time_hours"], 5)
        self.assertEqual(with_strength["vo2_sessions"], without_strength["vo2_sessions"])
        self.assertEqual(with_strength["threshold_sessions"], without_strength["threshold_sessions"])
        self.assertEqual(with_strength["endurance_sessions"], without_strength["endurance_sessions"])
        self.assertEqual(with_strength["avg_decoupling"], without_strength["avg_decoupling"])
        self.assertEqual(
            with_strength["high_decoupling_rides"],
            without_strength["high_decoupling_rides"],
        )
        self.assertEqual(
            with_strength["days_since_last_hiit"],
            without_strength["days_since_last_hiit"],
        )
        self.assertEqual(
            with_strength["days_since_last_polarized"],
            without_strength["days_since_last_polarized"],
        )
        self.assertEqual(with_strength["days_since_last_hard_session"], 0)
        self.assertIsNone(
            analyze_week.compute_aerobic_threshold_estimate(
                [
                    {
                        "type": "WeightTraining",
                        "dfa_a1_summary": {
                            "valid": True,
                            "power_at_0_75": 200,
                            "hr_at_0_75": 140,
                            "threshold_windows": 4,
                        },
                    }
                ],
                250,
                [55, 75, 90],
            )
        )

    def test_run_remains_in_combined_totals_and_has_separate_totals(self):
        ride = _raw_activity("Ride", 100, 3600)
        run = _raw_activity("Run", 20, 1800)
        strength = _raw_activity("WeightTraining", 9, 900)

        summary = analyze_week.compute_metrics([ride, run, strength])

        self.assertEqual(summary["total_training_load"], 120)
        self.assertEqual(summary["number_of_activities"], 2)
        self.assertEqual(summary["total_time_hours"], 1.5)
        self.assertEqual(summary["run_load"], 20)
        self.assertEqual(summary["run_sessions"], 1)
        self.assertEqual(summary["run_time_hours"], 0.5)

    def test_week_summary_schema_accepts_per_sport_totals(self):
        fields = week_data_schema.WeekSummary.model_fields

        self.assertTrue(
            {
                "ride_load",
                "run_load",
                "strength_load",
                "ride_sessions",
                "run_sessions",
                "strength_sessions",
                "ride_time_hours",
                "run_time_hours",
                "strength_time_hours",
            }.issubset(fields)
        )

    def test_strength_maximum_is_hard_but_other_strength_tags_ignore_tss_threshold(self):
        maximum = _raw_activity(
            "WeightTraining",
            100,
            3600,
            tags=["strength-maximum"],
        )
        adaptation = _raw_activity(
            "WeightTraining",
            100,
            3600,
            tags=["strength-adaptation"],
        )
        maximum_with_low_load = dict(maximum, icu_training_load=1)
        ride = _raw_activity("Ride", 100, 3600)

        self.assertTrue(analyze_week.is_hard_session(maximum_with_low_load, current_ctl=100))
        self.assertFalse(analyze_week.is_hard_session(adaptation, current_ctl=10))
        self.assertTrue(analyze_week.is_hard_session(ride, current_ctl=60))

    def test_hard_strength_updates_recency_and_readiness_veto(self):
        maximum_today = _raw_activity(
            "WeightTraining",
            8,
            3600,
            tags=["strength-maximum"],
        )

        summary = analyze_week.compute_metrics([maximum_today], current_ctl=100)
        readiness = prepare_week.compute_training_readiness(
            {},
            {
                "ctl": 100,
                "atl": 80,
                "form_zone": "fresh",
                "days_since_last_hard_session": summary["days_since_last_hard_session"],
            },
        )

        self.assertEqual(summary["days_since_last_hard_session"], 0)
        self.assertEqual(readiness["status"], "red")
        self.assertIn("A hard session was completed today.", readiness["safety_vetoes"])

    def test_adaptation_strength_does_not_update_hard_session_recency(self):
        adaptation_today = _raw_activity(
            "WeightTraining",
            100,
            3600,
            tags=["strength-adaptation"],
        )

        summary = analyze_week.compute_metrics([adaptation_today], current_ctl=10)

        self.assertIsNone(summary["days_since_last_hard_session"])


from intervals_icu.strength import resolve_strength_week_phase


def _sessions(start: date, phase: str | None, count: int, step_days: int = 3):
    return [(start + timedelta(days=i * step_days), phase) for i in range(count)]


def _row(day: date, phase: str | None, **extra) -> dict:
    row = {
        "date": day.isoformat(),
        "tags": [f"strength-{phase}"] if phase else [],
        "phase_source": "activity" if phase else "none",
    }
    row.update(extra)
    return row


class StrengthWeekPhaseResolverTests(unittest.TestCase):
    MONDAY = date(2026, 11, 2)

    def _recent(self, phase, count):
        return _sessions(self.MONDAY - timedelta(days=3 * count), phase, count)

    def _resolve(self, sessions, cycling_phase=None):
        return resolve_strength_week_phase(sessions, self.MONDAY, cycling_phase)

    def test_no_history_starts_adaptation(self):
        self.assertEqual(self._resolve([]), ("adaptation", 2, "no_history"))
        self.assertEqual(
            self._resolve([(date(2026, 10, 30), None)]), ("adaptation", 2, "no_history")
        )

    def test_gap_of_21_days_resets_to_adaptation(self):
        sessions = _sessions(date(2026, 9, 1), "maximum", 5)
        sessions.append((self.MONDAY - timedelta(days=21), "maximum"))
        self.assertEqual(self._resolve(sessions), ("adaptation", 2, "gap_reset"))
        sessions[-1] = (self.MONDAY - timedelta(days=20), "maximum")
        self.assertEqual(self._resolve(sessions)[2], "continue")

    def test_continue_below_phase_minimum(self):
        for phase, minimum in (("adaptation", 4), ("transition", 2), ("maximum", 8)):
            with self.subTest(phase=phase):
                sessions = self._recent(phase, minimum - 1)
                self.assertEqual(self._resolve(sessions), (phase, 2, "continue"))

    def test_advance_when_phase_minimum_is_reached(self):
        for phase, minimum, next_phase, recommended in (
            ("adaptation", 4, "transition", 2),
            ("transition", 2, "maximum", 2),
            ("maximum", 8, "maintenance", 1),
        ):
            with self.subTest(phase=phase):
                sessions = self._recent(phase, minimum)
                self.assertEqual(
                    self._resolve(sessions), (next_phase, recommended, "advance_min_reached")
                )

    def test_maintenance_stays_with_one_session(self):
        sessions = self._recent("maintenance", 6)
        self.assertEqual(self._resolve(sessions), ("maintenance", 1, "continue"))

    def test_run_count_stops_at_phase_change_and_skips_untagged(self):
        sessions = _sessions(date(2026, 10, 1), "adaptation", 6)
        sessions += [(date(2026, 10, 20), "transition"), (date(2026, 10, 25), None)]
        self.assertEqual(self._resolve(sessions), ("transition", 2, "continue"))

    def test_base_and_transition_cycling_phase_use_run_rules(self):
        sessions = self._recent("adaptation", 4)
        for cycling_phase in (None, "Base", "Transition", "unknown"):
            with self.subTest(cycling_phase=cycling_phase):
                self.assertEqual(
                    self._resolve(sessions, cycling_phase),
                    ("transition", 2, "advance_min_reached"),
                )

    def test_build_with_prior_adaptation_run_switches_to_maintenance(self):
        sessions = _sessions(date(2026, 9, 1), "adaptation", 4)
        self.assertEqual(self._resolve(sessions, "Build"), ("maintenance", 1, "build_guard"))

    def test_build_without_prior_adaptation_run_is_beginner_build(self):
        self.assertEqual(self._resolve([], "Build"), ("adaptation", 1, "beginner_build"))
        sessions = _sessions(date(2026, 10, 10), "adaptation", 3)
        self.assertEqual(self._resolve(sessions, "build"), ("adaptation", 1, "beginner_build"))

    def test_later_phase_history_counts_as_prior_adaptation(self):
        sessions = [(date(2026, 10, 20), "transition")]
        self.assertEqual(self._resolve(sessions, "Build"), ("maintenance", 1, "build_guard"))

    def test_build_cuts_running_maximum_run(self):
        sessions = _sessions(date(2026, 10, 1), "maximum", 5)
        self.assertEqual(self._resolve(sessions), ("maximum", 2, "continue"))
        self.assertEqual(self._resolve(sessions, "Build"), ("maintenance", 1, "build_guard"))

    def test_peak_behaves_like_build(self):
        self.assertEqual(self._resolve([], "Peak"), ("adaptation", 1, "beginner_build"))
        sessions = _sessions(date(2026, 10, 1), "maximum", 5)
        self.assertEqual(self._resolve(sessions, "PEAK"), ("maintenance", 1, "build_guard"))

    def test_sessions_on_or_after_week_monday_are_ignored(self):
        sessions = _sessions(self.MONDAY, "adaptation", 4, step_days=1)
        self.assertEqual(self._resolve(sessions), ("adaptation", 2, "no_history"))


class StrengthWeekPhaseSummaryTests(unittest.TestCase):
    TODAY = date(2026, 11, 4)  # Wednesday; current Monday 2026-11-02

    def _summary(self, history, training_plan=None):
        return prepare_week.build_strength_week_summary(
            history,
            self.TODAY,
            {"strength_sessions": 0, "strength_load": 0},
            training_plan=training_plan,
        )

    def test_summary_contains_week_phase_fields(self):
        summary = self._summary([])
        self.assertEqual(summary["phase_current_week"], "adaptation")
        self.assertEqual(summary["phase_next_week"], "adaptation")
        self.assertEqual(summary["recommended_sessions_current_week"], 2)
        self.assertEqual(summary["recommended_sessions_next_week"], 2)
        self.assertEqual(summary["phase_reason_current_week"], "no_history")
        self.assertEqual(summary["phase_reason_next_week"], "no_history")
        self.assertIsNone(summary["current_phase"])
        self.assertIsNone(summary["phase_min_sessions"])
        self.assertIsNone(summary["phase_max_sessions"])

    def test_phase_min_max_sessions_follow_current_phase(self):
        for phase, minimum, maximum, target in (
            ("adaptation", 4, 6, "4-6"),
            ("transition", 2, 3, "2-3"),
            ("maximum", 8, 12, "8-12"),
            ("maintenance", None, None, "ongoing"),
        ):
            with self.subTest(phase=phase):
                summary = self._summary([_row(date(2026, 11, 2), phase)])
                self.assertEqual(summary["current_phase"], phase)
                self.assertEqual(summary["phase_target_sessions"], target)
                self.assertEqual(summary["phase_min_sessions"], minimum)
                self.assertEqual(summary["phase_max_sessions"], maximum)

    def test_current_week_uses_state_before_monday_and_next_week_counts_this_week(self):
        history = [
            _row(date(2026, 10, 27), "adaptation"),
            _row(date(2026, 10, 29), "adaptation"),
            _row(date(2026, 11, 2), "adaptation"),
        ]
        summary = self._summary(history)
        self.assertEqual(summary["phase_current_week"], "adaptation")
        self.assertEqual(summary["phase_reason_current_week"], "continue")
        self.assertEqual(summary["phase_next_week"], "adaptation")
        self.assertEqual(summary["phase_reason_next_week"], "continue")

    def test_planned_events_later_this_week_count_for_next_week(self):
        history = [
            _row(date(2026, 10, 27), "adaptation"),
            _row(date(2026, 10, 29), "adaptation"),
            _row(date(2026, 11, 2), "adaptation"),
            {
                "id": None,
                "date": "2026-11-06",
                "tags": ["strength-adaptation"],
                "phase_source": "planned_event",
                "planned": True,
            },
        ]
        summary = self._summary(history)
        self.assertEqual(summary["phase_current_week"], "adaptation")
        self.assertEqual(summary["phase_next_week"], "transition")
        self.assertEqual(summary["phase_reason_next_week"], "advance_min_reached")
        # Planned rows never count as completed sessions.
        self.assertEqual(summary["phase_session_count"], 3)

    def test_untagged_rows_this_week_default_to_current_week_phase(self):
        history = [
            _row(date(2026, 10, 27), "transition"),
            _row(date(2026, 11, 3), None),
            {
                "id": None,
                "date": "2026-11-07",
                "tags": [],
                "phase_source": "planned_event",
                "planned": True,
            },
        ]
        summary = self._summary(history)
        self.assertEqual(summary["phase_current_week"], "transition")
        self.assertEqual(summary["phase_next_week"], "maximum")
        self.assertEqual(summary["phase_reason_next_week"], "advance_min_reached")

    def test_training_plan_phase_applies_per_week(self):
        history = [_row(date(2026, 10, 1) + timedelta(days=3 * i), "adaptation") for i in range(4)]
        history.append(_row(date(2026, 10, 27), "transition"))
        training_plan = [
            {"week": "2026-11-02", "phase": "Base"},
            {"week": "2026-11-09", "phase": "Build"},
        ]
        summary = self._summary(history, training_plan)
        self.assertEqual(summary["phase_current_week"], "transition")
        self.assertEqual(summary["recommended_sessions_current_week"], 2)
        self.assertEqual(summary["phase_next_week"], "maintenance")
        self.assertEqual(summary["recommended_sessions_next_week"], 1)
        self.assertEqual(summary["phase_reason_next_week"], "build_guard")

    def test_gap_reset_in_summary(self):
        summary = self._summary([_row(date(2026, 10, 1), "maximum")])
        self.assertEqual(summary["phase_current_week"], "adaptation")
        self.assertEqual(summary["phase_reason_current_week"], "gap_reset")


class StrengthHistoryTests(unittest.TestCase):
    def test_history_fetch_keeps_null_and_zero_load_without_load_query_filter(self):
        response = unittest.mock.Mock()
        response.json.return_value = [
            _raw_activity("WeightTraining", load, 3600, tags=["strength-maximum"])
            for load in (None, 0)
        ]
        with patch.object(client.requests, "get", return_value=response) as request:
            completed = client.get_strength_history_activities(
                "test-key", "test-athlete", "2026-07-12", "2026-11-01",
            )
        self.assertEqual([row["icu_training_load"] for row in completed], [None, 0])
        self.assertEqual(set(request.call_args.kwargs["params"]), {"oldest", "newest", "fields"})
        history = prepare_week.build_strength_history(completed, [])
        self.assertEqual(len(history), 2)
        self.assertEqual([row["training_load"] for row in history], [None, 0])

    def test_activity_planned_and_missing_tag_resolution_excludes_strava_duplicate(self):
        completed = [
            {
                "id": 1,
                "type": "WeightTraining",
                "source": "GARMIN",
                "start_date_local": "2026-10-10T09:00:00",
                "tags": ["strength-transition", "legacy"],
                "moving_time": 3000,
                "icu_training_load": 35,
                "icu_rpe": 8,
            },
            {
                "id": 2,
                "type": "WeightTraining",
                "source": "GARMIN",
                "start_date_local": "2026-10-11T09:00:00",
                "tags": ["strength"],
                "moving_time": 2400,
                "icu_training_load": 25,
                "icu_rpe": 6,
            },
            {
                "id": 3,
                "type": "WeightTraining",
                "source": "GARMIN",
                "start_date_local": "2026-10-09T09:00:00",
                "tags": ["strength"],
                "moving_time": 1800,
                "icu_training_load": 10,
                "icu_rpe": 4,
            },
            {
                "id": 4,
                "type": "WeightTraining",
                "source": "GARMIN",
                "start_date_local": "2026-10-12T09:00:00",
                "tags": ["legacy"],
                "moving_time": 1800,
                "icu_training_load": None,
                "icu_rpe": None,
            },
            {
                "id": 5,
                "type": "WeightTraining",
                "source": "STRAVA",
                "start_date_local": "2026-10-13T09:00:00",
                "tags": ["strength-maximum"],
                "moving_time": 1800,
            },
        ]
        planned = [
            {
                "type": "WeightTraining",
                "start_date_local": "2026-10-11T08:00:00",
                "tags": ["strength-transition"],
            },
            {
                "type": "WeightTraining",
                "start_date_local": "2026-10-12T08:00:00",
                "tags": ["strength-maintenance"],
            },
            {
                "type": "Ride",
                "start_date_local": "2026-10-12T08:00:00",
                "tags": ["strength-transition"],
            },
        ]

        history = prepare_week.build_strength_history(completed, planned)

        self.assertEqual(
            history,
            [
                {
                    "id": 4,
                    "date": "2026-10-12",
                    "tags": ["strength-maintenance"],
                    "phase_source": "planned",
                    "planned_week_exists": True,
                    "duration_minutes": 30,
                    "training_load": None,
                    "rpe": None,
                },
                {
                    "id": 2,
                    "date": "2026-10-11",
                    "tags": ["strength-transition"],
                    "phase_source": "planned",
                    "planned_week_exists": True,
                    "duration_minutes": 40,
                    "training_load": 25,
                    "rpe": 6,
                },
                {
                    "id": 1,
                    "date": "2026-10-10",
                    "tags": ["strength-transition"],
                    "phase_source": "activity",
                    "planned_week_exists": True,
                    "duration_minutes": 50,
                    "training_load": 35,
                    "rpe": 8,
                },
                {
                    "id": 3,
                    "date": "2026-10-09",
                    "tags": ["strength-transition"],
                    "phase_source": "planned_week",
                    "planned_week_exists": True,
                    "duration_minutes": 30,
                    "training_load": 10,
                    "rpe": 4,
                },
            ],
        )

    def test_activity_tag_takes_precedence_over_planned_tag(self):
        history = prepare_week.build_strength_history(
            [
                {
                    "type": "WeightTraining",
                    "start_date_local": "2026-10-10T09:00:00",
                    "tags": ["strength-maximum"],
                    "moving_time": 3600,
                }
            ],
            [
                {
                    "type": "WeightTraining",
                    "start_date_local": "2026-10-10T08:00:00",
                    "tags": ["strength-adaptation"],
                }
            ],
        )

        self.assertEqual(history[0]["tags"], ["strength-maximum"])
        self.assertEqual(history[0]["phase_source"], "activity")

    def test_inferred_session_continues_adaptation_run(self):
        completed = [
            _raw_activity(
                "WeightTraining", None, 1800, id=day,
                start_date_local=day + "T09:00:00",
                tags=["strength-adaptation"] if day != "2026-11-02" else [],
            )
            for day in ("2026-10-24", "2026-10-27", "2026-10-30", "2026-11-02")
        ]
        history = prepare_week.build_strength_history(list(reversed(completed)), [])
        self.assertEqual(history[0]["phase_source"], "inferred")
        self.assertEqual(history[0]["tags"], ["strength-adaptation"])
        summary = prepare_week.build_strength_week_summary(history, date(2026, 11, 2), {})
        self.assertEqual(summary["current_phase"], "adaptation")
        self.assertEqual(summary["phase_session_count"], 4)
        self.assertEqual(summary["phase_started"], "2026-10-24")
        self.assertEqual(summary["untagged_sessions_last_16_weeks"], 0)
        self.assertEqual(summary["inferred_sessions_last_16_weeks"], 1)
        self.assertTrue(summary["tagging_reminder_needed"])
        self.assertFalse(summary["phase_overdue"])

    def test_untagged_sessions_before_first_resolved_phase_remain_none(self):
        history = prepare_week.build_strength_history([
            _raw_activity("WeightTraining", None, 1800, id=day,
                          start_date_local=day + "T09:00:00",
                          tags=["strength-adaptation"] if day == "2026-10-30" else [])
            for day in ("2026-10-24", "2026-10-27", "2026-10-30")
        ], [])
        self.assertEqual([row["phase_source"] for row in history], ["activity", "none", "none"])
        summary = prepare_week.build_strength_week_summary(history, date(2026, 11, 2), {})
        self.assertEqual(summary["phase_session_count"], 1)
        self.assertEqual(summary["untagged_sessions_last_16_weeks"], 2)
        self.assertEqual(summary["inferred_sessions_last_16_weeks"], 0)

    def test_inference_gap_boundary_and_no_chained_inference(self):
        for gap in (20, 21, 22):
            with self.subTest(gap=gap):
                anchor = date(2026, 10, 1)
                latest = anchor + timedelta(days=gap)
                history = prepare_week.build_strength_history([
                    _raw_activity("WeightTraining", None, 1800, id=day.isoformat(),
                                  start_date_local=day.isoformat() + "T09:00:00",
                                  tags=["strength-adaptation"] if day == anchor else [])
                    for day in (anchor, latest)
                ], [])
                inferred = gap < 21
                self.assertEqual(history[0]["phase_source"], "inferred" if inferred else "none")
                summary = prepare_week.build_strength_week_summary(history, latest, {})
                self.assertEqual(summary["current_phase"], "adaptation" if inferred else None)
                self.assertEqual(summary["phase_session_count"], 2 if inferred else 0)
                self.assertEqual(summary["phase_started"], anchor.isoformat() if inferred else None)
        history = prepare_week.build_strength_history([
            _raw_activity("WeightTraining", None, 1800, id=day,
                          start_date_local=day + "T09:00:00",
                          tags=["strength-adaptation"] if day == "2026-10-01" else [])
            for day in ("2026-10-01", "2026-10-20", "2026-10-22")
        ], [])
        self.assertEqual([row["phase_source"] for row in history], ["none", "inferred", "activity"])

    def test_inference_uses_latest_resolved_source_and_never_overrides_plan(self):
        for source in ("activity", "planned", "planned_week"):
            with self.subTest(source=source):
                plans = [] if source == "activity" else [{
                    "date": "2026-10-30" if source == "planned" else "2026-10-29",
                    "tags": ["strength-transition"],
                }]
                completed = [
                    _raw_activity("WeightTraining", None, 1800, id="older",
                                  start_date_local="2026-10-20T09:00:00",
                                  tags=["strength-adaptation"]),
                    _raw_activity("WeightTraining", None, 1800, id="anchor",
                                  start_date_local="2026-10-30T09:00:00",
                                  tags=["strength-transition"] if source == "activity" else []),
                    _raw_activity("WeightTraining", None, 1800, id="new",
                                  start_date_local="2026-11-02T09:00:00"),
                ]
                history = prepare_week.build_strength_history(completed, plans)
                self.assertEqual(history[1]["phase_source"], source)
                self.assertEqual(history[0]["phase_source"], "inferred")
                self.assertEqual(history[0]["tags"], ["strength-transition"])
                planned = prepare_week.build_strength_history(
                    completed, plans + [{"date": "2026-11-03", "tags": ["strength-maximum"]}],
                )
                self.assertEqual(planned[0]["phase_source"], "planned_week")
                self.assertEqual(planned[0]["tags"], ["strength-maximum"])

    def test_inference_and_phase_run_follow_session_time_within_same_date(self):
        sessions = [
            ("early", "2026-10-30T08:00:00", []),
            ("first", "2026-10-30T09:00:00", ["strength-adaptation"]),
            ("second", "2026-10-30T10:00:00", ["strength-maximum"]),
            ("last", "2026-10-30T11:00:00", []),
        ]
        history = prepare_week.build_strength_history([
            _raw_activity("WeightTraining", None, 1800, id=activity_id,
                          start_date_local=timestamp, tags=tags)
            for activity_id, timestamp, tags in sessions
        ], [])
        self.assertEqual([row["id"] for row in history], ["last", "second", "first", "early"])
        self.assertEqual(history[-1]["phase_source"], "none")
        self.assertEqual(history[0]["phase_source"], "inferred")
        self.assertEqual(history[0]["tags"], ["strength-maximum"])
        summary = prepare_week.build_strength_week_summary(history, date(2026, 11, 2), {})
        self.assertEqual(summary["current_phase"], "maximum")
        self.assertEqual(summary["phase_session_count"], 2)

    def test_phase_overdue_exceeds_maximum_without_switching_phase(self):
        maxima = {"adaptation": 6, "transition": 3, "maximum": 12, "maintenance": None}
        for phase, maximum in maxima.items():
            for count in (maximum or 12, (maximum or 12) + 1):
                with self.subTest(phase=phase, count=count):
                    today = date(2026, 11, 2)
                    history = [
                        {"date": (today - timedelta(days=offset)).isoformat(),
                         "tags": [f"strength-{phase}"], "phase_source": "activity"}
                        for offset in range(count)
                    ]
                    summary = prepare_week.build_strength_week_summary(history, today, {})
                    self.assertEqual(summary["current_phase"], phase)
                    self.assertEqual(summary["phase_session_count"], count)
                    self.assertEqual(summary["phase_overdue"], maximum is not None and count > maximum)

    def test_inferred_reminder_is_suppressed_by_untagged_plan_in_same_week(self):
        completed = [
            _raw_activity("WeightTraining", None, 1800, id=day,
                          start_date_local=day + "T09:00:00",
                          tags=["strength-adaptation"] if day == "2026-10-30" else [])
            for day in ("2026-10-30", "2026-11-02")
        ]
        history = prepare_week.build_strength_history(
            completed, [{"date": "2026-11-03", "tags": []}],
        )
        self.assertEqual(history[0]["phase_source"], "inferred")
        summary = prepare_week.build_strength_week_summary(history, date(2026, 11, 2), {})
        self.assertFalse(summary["tagging_reminder_needed"])
        self.assertEqual(summary["inferred_sessions_last_16_weeks"], 1)

    def test_new_tagged_session_after_long_gap_starts_new_run(self):
        history = [
            {"date": "2026-11-02", "tags": ["strength-adaptation"], "phase_source": "activity"},
            {"date": "2026-10-12", "tags": ["strength-adaptation"], "phase_source": "activity"},
        ]
        summary = prepare_week.build_strength_week_summary(history, date(2026, 11, 2), {})
        self.assertEqual(summary["current_phase"], "adaptation")
        self.assertEqual(summary["phase_session_count"], 1)
        self.assertFalse(summary["phase_overdue"])

    def test_annotation_preserves_tags_and_matches_by_id_not_date(self):
        activities = [
            {"id": 1, "date": "2026-11-02", "type": "WeightTraining", "tags": []},
            {"id": 2, "date": "2026-11-02", "type": "WeightTraining", "tags": []},
            {"id": 3, "date": "2026-11-02", "type": "Ride", "tags": []},
        ]
        history = [
            {"id": "1", "date": "2026-11-02", "tags": ["strength-adaptation"],
             "phase_source": "inferred", "planned_week_exists": False},
            {"id": "2", "date": "2026-11-02", "tags": ["strength-maximum"],
             "phase_source": "planned", "planned_week_exists": True},
        ]
        annotated = prepare_week.annotate_strength_phases(activities, history)
        self.assertEqual(annotated[0]["strength_phase"], "adaptation")
        self.assertEqual(annotated[0]["strength_phase_source"], "inferred")
        self.assertTrue(annotated[0]["strength_tagging_reminder_needed"])
        self.assertEqual(annotated[1]["strength_phase"], "maximum")
        self.assertFalse(annotated[1]["strength_tagging_reminder_needed"])
        self.assertEqual(annotated[2], activities[2])
        self.assertEqual(annotated[0]["tags"], [])
        self.assertNotIn("strength_phase", activities[0])

    def test_week_fallback_uses_nearest_plan_without_crossing_iso_weeks(self):
        cases = [
            ("2026-10-26", [("2026-10-27", "strength-maximum")],
             ["strength-maximum"], "planned_week"),
            ("2026-11-01", [("2026-11-02", "strength-maximum")], [], "none"),
            ("2026-10-30", [("2026-10-27", "strength-adaptation"),
                            ("2026-10-31", "strength-maximum")],
             ["strength-maximum"], "planned_week"),
            ("2026-10-29", [("2026-10-27", "strength-adaptation"),
                            ("2026-10-31", "strength-maximum")],
             ["strength-adaptation"], "planned_week"),
            ("2026-10-30", [("2026-10-30", "strength-adaptation"),
                            ("2026-10-31", "strength-maximum")],
             ["strength-adaptation"], "planned"),
            ("2025-12-29", [("2026-01-02", "strength-maximum")],
             ["strength-maximum"], "planned_week"),
        ]
        for day, planned, tags, source in cases:
            with self.subTest(day=day, planned=planned):
                history = prepare_week.build_strength_history(
                    [_raw_activity("WeightTraining", None, 3600,
                                   start_date_local=day + "T09:00:00")],
                    [{"type": "WeightTraining", "date": event_day, "tags": [tag]}
                     for event_day, tag in planned],
                )
                self.assertEqual(history[0]["tags"], tags)
                self.assertEqual(history[0]["phase_source"], source)
                summary = prepare_week.build_strength_week_summary(
                    history, date.fromisoformat(day), {},
                )
                self.assertEqual(summary["untagged_sessions_last_16_weeks"],
                                 int(source == "none"))
                self.assertEqual(summary["phase_session_count"], int(source != "none"))

    def test_reminder_requires_recent_unresolved_session_in_unplanned_week(self):
        today = date(2026, 11, 1)
        for day, plans, expected in [
            ("2026-10-26", [], True),
            ("2026-10-19", [], True),
            ("2026-10-18", [], False),
            ("2026-10-26", [{"date": "2026-10-27", "tags": []}], False),
            ("2026-10-26", [{"date": "2026-10-27",
                             "tags": ["strength-maximum"]}], False),
            ("2026-10-26", [{"date": "2026-11-02",
                             "tags": ["strength-maximum"]}], True),
        ]:
            with self.subTest(day=day, plans=plans):
                history = prepare_week.build_strength_history(
                    [_raw_activity("WeightTraining", None, 3600,
                                   start_date_local=day + "T09:00:00")], plans,
                )
                summary = prepare_week.build_strength_week_summary(history, today, {})
                self.assertEqual(summary["tagging_reminder_needed"], expected)

    def test_plan_in_current_week_does_not_suppress_previous_week_reminder(self):
        history = prepare_week.build_strength_history(
            [
                _raw_activity("WeightTraining", None, 3600,
                              start_date_local=day + "T09:00:00")
                for day in ("2026-10-20", "2026-10-27")
            ],
            [{"date": "2026-10-28", "tags": ["strength-maximum"]}],
        )
        summary = prepare_week.build_strength_week_summary(
            history, date(2026, 11, 1), {},
        )
        self.assertEqual(summary["current_phase"], "maximum")
        self.assertEqual(summary["untagged_sessions_last_16_weeks"], 1)
        self.assertTrue(summary["tagging_reminder_needed"])

    def test_fetch_includes_full_iso_weeks_for_planned_events_only(self):
        with (
            patch.object(prepare_week, "_strength_history_weeks", return_value=16),
            patch("intervals_icu.client.get_strength_history_activities",
                  return_value=[]) as completed,
            patch("intervals_icu.client.get_planned_strength_events",
                  return_value=[]) as planned,
        ):
            prepare_week.fetch_strength_history(
                date(2026, 10, 28), api_key="key", athlete_id="athlete",
            )
        completed.assert_called_once_with("key", "athlete", "2026-07-08", "2026-10-28")
        planned.assert_called_once_with("key", "athlete", "2026-07-06", "2026-11-01")

    def test_phase_count_skips_untagged_rows_and_stops_at_phase_change(self):
        history = [
            {"date": "2026-10-31", "tags": ["strength-maximum"], "phase_source": "activity"},
            {"date": "2026-10-29", "tags": ["strength-maximum"], "phase_source": "planned"},
            {"date": "2026-10-27", "tags": [], "phase_source": "none"},
            {"date": "2026-10-25", "tags": ["strength-maximum"], "phase_source": "activity"},
            {"date": "2026-10-23", "tags": ["strength-transition"], "phase_source": "activity"},
        ]

        summary = prepare_week.build_strength_week_summary(
            history,
            date.fromisoformat("2026-11-01"),
            {"strength_sessions": 1, "strength_load": 9},
        )

        self.assertEqual(summary["current_phase"], "maximum")
        self.assertEqual(summary["phase_session_count"], 3)
        self.assertEqual(summary["phase_started"], "2026-10-25")
        self.assertEqual(summary["phase_target_sessions"], "8-12")
        self.assertEqual(summary["sessions_this_week"], 1)
        self.assertEqual(summary["weekly_strength_load"], 9)

    def test_phase_state_resets_after_21_days(self):
        summary = prepare_week.build_strength_week_summary(
            [
                {
                    "date": "2026-10-11",
                    "tags": ["strength-maximum"],
                    "phase_source": "activity",
                }
            ],
            date.fromisoformat("2026-11-01"),
            {"strength_sessions": 0, "strength_load": 0},
        )

        self.assertEqual(summary["days_since_last_strength"], 21)
        self.assertIsNone(summary["current_phase"])
        self.assertEqual(summary["phase_session_count"], 0)
        self.assertIsNone(summary["phase_started"])

    def test_activity_fetch_uses_small_projection_then_filters_type_and_strava(self):
        with patch.object(
            client,
            "get_activities",
            return_value=[
                {"id": 1, "type": "WeightTraining", "source": "GARMIN"},
                {"id": 2, "type": "WeightTraining", "source": "STRAVA"},
                {"id": 3, "type": "Ride", "source": "GARMIN"},
            ],
        ) as get_activities:
            result = client.get_strength_history_activities("key", "athlete", "old", "new")

        self.assertEqual(
            result,
            [
                {
                    "id": 1,
                    "start_date_local": None,
                    "type": "WeightTraining",
                    "tags": None,
                    "moving_time": None,
                    "icu_training_load": None,
                    "icu_rpe": None,
                }
            ],
        )
        self.assertEqual(
            get_activities.call_args.kwargs["fields"],
            (
                "id",
                "start_date_local",
                "type",
                "tags",
                "moving_time",
                "icu_training_load",
                "icu_rpe",
                "source",
            ),
        )

    def test_planned_events_use_projection_and_filter_weight_training(self):
        with patch.object(
            client,
            "get_events",
            return_value=[
                {
                    "id": 1,
                    "type": "WeightTraining",
                    "start_date_local": "2026-10-10T09:00:00",
                    "tags": ["strength-maximum"],
                },
                {
                    "id": 2,
                    "type": "Ride",
                    "start_date_local": "2026-10-11T09:00:00",
                    "tags": ["strength-transition"],
                },
            ],
        ) as get_events:
            result = client.get_planned_strength_events("key", "athlete", "old", "new")

        self.assertEqual(
            result,
            [
                {
                    "date": "2026-10-10",
                    "tags": ["strength-maximum"],
                }
            ],
        )
        self.assertIn("tags", get_events.call_args.kwargs["fields"])

    def test_only_strength_summary_is_typed_in_week_data_schema(self):
        self.assertNotIn("strength_history", week_data_schema.WeekData.model_fields)
        self.assertIn("strength", week_data_schema.WeekSummary.model_fields)
        self.assertIn("current_phase", week_data_schema.StrengthSummary.model_fields)
        schema = week_data_schema.WeekData.model_json_schema()
        self.assertNotIn("StrengthHistoryEntry", schema["$defs"])
        fields = schema["$defs"]["StrengthSummary"]["properties"]
        self.assertEqual(fields["sessions_per_week_last_4"]["minItems"], 4)
        self.assertEqual(fields["sessions_per_week_last_4"]["maxItems"], 4)
        self.assertIn("untagged_sessions_last_16_weeks", fields)
        self.assertEqual(fields["inferred_sessions_last_16_weeks"]["type"], "integer")
        self.assertEqual(fields["phase_overdue"]["type"], "boolean")
        self.assertEqual(fields["tagging_reminder_needed"]["type"], "boolean")

    def test_compact_counts_include_untagged_sessions_and_completed_iso_weeks(self):
        today = date(2026, 11, 1)
        monday = today - timedelta(days=today.weekday())
        history = []
        for weeks_ago in range(4, 0, -1):
            week_start = monday - timedelta(weeks=weeks_ago)
            for offset, source in ((0, "activity"), (6, "none")):
                history.append({
                    "date": (week_start + timedelta(days=offset)).isoformat(),
                    "tags": ["strength-maximum"] if source == "activity" else [],
                    "phase_source": source,
                })
        history.extend([
            {"date": today.isoformat(), "tags": [], "phase_source": "none"},
            {
                "date": (monday - timedelta(weeks=5)).isoformat(),
                "tags": [],
                "phase_source": "none",
            },
        ])
        summary = prepare_week.build_strength_week_summary(history, today, {})
        self.assertEqual(summary["sessions_per_week_last_4"], [2, 2, 2, 2])
        self.assertEqual(summary["untagged_sessions_last_16_weeks"], 6)

    def test_completed_week_counts_are_oldest_first_across_iso_year_boundary(self):
        summary = prepare_week.build_strength_week_summary(
            [
                {"date": day, "tags": [], "phase_source": "none"}
                for day in ("2025-12-08", "2025-12-15", "2025-12-21",
                            "2025-12-29", "2026-01-04", "2026-01-05")
            ],
            date(2026, 1, 7),
            {},
        )
        self.assertEqual(summary["sessions_per_week_last_4"], [1, 2, 0, 2])
        self.assertEqual(summary["untagged_sessions_last_16_weeks"], 6)

    def test_empty_history_has_zero_compact_counts(self):
        summary = prepare_week.build_strength_week_summary([], date(2026, 11, 1), {})
        self.assertEqual(summary["sessions_per_week_last_4"], [0, 0, 0, 0])
        self.assertEqual(summary["untagged_sessions_last_16_weeks"], 0)

    def test_consolidation_exports_strength_summary_without_history(self):
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        activity = {
            "id": 10,
            "type": "WeightTraining",
            "date": today.isoformat(),
            "name": "Heavy strength",
            "duration_hours": 1,
            "training_load": 9,
            "tags": ["strength-maximum"],
        }
        source_data = {
            f"coach_input_{monday.isoformat()}.json": [activity],
            f"fueling_analysis_{monday.isoformat()}.json": {"activities": []},
            f"week_summary_{monday.isoformat()}.json": {
                "strength_sessions": 1,
                "strength_load": 9,
                "days_since_last_hard_session": 0,
            },
            f"training_plan_{today.isoformat()}.json": None,
            f"planned_workouts_{monday.isoformat()}.json": None,
        }
        history = [
            {
                "id": 10,
                "date": today.isoformat(),
                "tags": ["strength-maximum"],
                "phase_source": "activity",
                "duration_minutes": 60,
                "training_load": 9,
                "rpe": 8,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            processed = Path(tmpdir)
            (processed / f"metrics_{today.isoformat()}.json").write_text("{}")
            with (
                patch.object(prepare_week, "PROCESSED_DIR", processed),
                patch.object(
                    prepare_week,
                    "_load_json",
                    side_effect=lambda path: source_data.get(path.name),
                ),
                patch.object(prepare_week, "fetch_strength_history", return_value=history),
            ):
                prepare_week.consolidate()

            payload = json.loads(
                (processed / f"coach_input_{monday.isoformat()}.json").read_text()
            )

        self.assertNotIn("strength_history", payload)
        self.assertNotIn("planned_week_exists", json.dumps(payload))
        self.assertEqual(payload["week_summary"]["strength"]["current_phase"], "maximum")
        self.assertEqual(payload["week_summary"]["strength"]["sessions_this_week"], 1)
        self.assertEqual(payload["week_summary"]["strength"]["sessions_per_week_last_4"], [0, 0, 0, 0])
        self.assertEqual(payload["week_summary"]["strength"]["untagged_sessions_last_16_weeks"], 0)
        self.assertEqual(payload["activities"][0]["strength_phase"], "maximum")
        self.assertEqual(payload["activities"][0]["strength_phase_source"], "activity")
        self.assertTrue(payload["activities"][0]["is_hard_session"])


class StrengthMcpPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {"INTERVALS_API_KEY": "test-key", "ATHLETE_ID": "test-athlete"}):
            cls.local = _load_module("strength_local_mcp", "scripts/mcp_server.py")
        from webservice import mcp_server

        cls.hosted = mcp_server

    def test_local_and_hosted_mcp_export_compact_summary_and_activity_phase(self):
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        history = [{
            "id": "gym",
            "date": today.isoformat(),
            "tags": ["strength-adaptation"],
            "phase_source": "inferred",
        }]
        activity = {
            "id": "gym", "date": today.isoformat(), "name": "Gym",
            "type": "WeightTraining", "tags": [],
        }
        expected = prepare_week.build_strength_week_summary(history, today, {})
        for server in (self.local, self.hosted):
            with self.subTest(server=server.__name__), tempfile.TemporaryDirectory() as tmpdir:
                processed = Path(tmpdir)
                with (
                    patch.object(server, "PROCESSED_DIR", processed),
                    patch.object(
                        server, "_load_json_file",
                        side_effect=lambda path: [activity] if path.name.startswith("coach_input_") else None,
                    ),
                    patch.object(server, "fetch_strength_history", return_value=history) as fetch,
                    patch.object(
                        server,
                        "_run_script",
                        return_value=(True, "", 0) if server is self.hosted else (True, ""),
                    ),
                ):
                    if server is self.local:
                        server.prepare_week_data()
                        payload = json.loads(
                            (processed / f"coach_input_{monday.isoformat()}.json").read_text()
                        )
                        credentials = {"api_key": server.API_KEY, "athlete_id": server.ATHLETE_ID}
                    else:
                        payload = json.loads(server._run_week_pipeline(
                            7, "request-athlete", "request-key", server._NoOpSpan(),
                        ))
                        credentials = {"api_key": "request-key", "athlete_id": "request-athlete"}
                fetch.assert_called_once_with(today, **credentials)
                self.assertNotIn("strength_history", payload)
                self.assertNotIn("planned_week_exists", json.dumps(payload))
                self.assertEqual(payload["week_summary"]["strength"], expected)
                self.assertEqual(payload["activities"][0]["strength_phase"], "adaptation")
                self.assertEqual(payload["activities"][0]["strength_phase_source"], "inferred")
                self.assertTrue(payload["activities"][0]["strength_tagging_reminder_needed"])
                report = server.check_athlete_data(json.dumps(payload))
                warning = next(check for check in report["checks"] if check["area"] == "strength_untagged")
                self.assertEqual(warning["status"], "Warning")
                self.assertIn("counted as adaptation", warning["explanation"])


if __name__ == "__main__":
    unittest.main()
