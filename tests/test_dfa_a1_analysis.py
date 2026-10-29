import importlib.util
import random
import sys
import unittest
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from intervals_icu import dfa_a1  # noqa: E402


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


prepare_activities = _load_module(
    "prepare_activities_dfa_script", "scripts/prepare_activities_for_coach.py"
)
analyze_week = _load_module("analyze_week_dfa_script", "scripts/analyze_week.py")
get_metrics = _load_module("get_metrics_dfa_script", "scripts/get_metrics.py")


def _white_noise_rr(n: int, seed: int, mean: float = 545.0, sd: float = 20.0) -> list[float]:
    rng = random.Random(seed)
    return [rng.gauss(mean, sd) for _ in range(n)]


def _random_walk_rr(n: int, seed: int, mean: float = 545.0, step: float = 2.0) -> list[float]:
    rng = random.Random(seed)
    value = mean
    series = []
    for _ in range(n):
        value += rng.gauss(0.0, step)
        # Keep the walk inside a physiological band so the artifact filter stays quiet.
        value = min(max(value, mean - 60), mean + 60)
        series.append(value)
    return series


def _hrv_stream(rr_values: list[float]) -> list:
    """One R-R interval per second, mimicking the intervals.icu hrv stream."""
    return [[round(rr)] for rr in rr_values]


def _streams(rr_values: list[float], watts: float | None = 150.0, hr: float | None = 120.0) -> dict:
    seconds = len(rr_values)
    streams = {"hrv": _hrv_stream(rr_values), "time": list(range(seconds))}
    if watts is not None:
        streams["watts"] = [watts] * seconds
    if hr is not None:
        streams["heartrate"] = [hr] * seconds
    return streams


class DfaAlpha1CoreTests(unittest.TestCase):
    def test_white_noise_scales_near_half(self):
        alpha = dfa_a1.dfa_alpha1(_white_noise_rr(2000, seed=1))
        self.assertIsNotNone(alpha)
        self.assertAlmostEqual(alpha, 0.5, delta=0.12)

    def test_random_walk_scales_near_one_and_a_half(self):
        alpha = dfa_a1.dfa_alpha1(_random_walk_rr(2000, seed=2, step=0.5))
        self.assertIsNotNone(alpha)
        self.assertGreater(alpha, 1.2)

    def test_too_short_series_returns_none(self):
        self.assertIsNone(dfa_a1.dfa_alpha1([600.0] * 20))

    def test_parse_rr_stream_flattens_lists_and_skips_gaps(self):
        beats = dfa_a1.parse_rr_stream([None, [662, 635], [736], None, 700], [0, 1, 2, 3, 4])
        self.assertEqual(beats, [(1.0, 662.0), (1.0, 635.0), (2.0, 736.0), (4.0, 700.0)])

    def test_flag_artifacts_marks_large_jumps(self):
        valid = dfa_a1.flag_artifacts([600, 610, 800, 605, 600])
        self.assertEqual(valid, [True, True, False, False, True])


class DfaAlpha1SummaryTests(unittest.TestCase):
    def test_returns_none_without_usable_hrv_stream(self):
        self.assertIsNone(dfa_a1.summarize_dfa_a1({"time": [0, 1, 2]}))
        self.assertIsNone(dfa_a1.summarize_dfa_a1({"hrv": [None] * 50, "time": list(range(50))}))

    def test_low_coverage_is_invalid_with_reason(self):
        streams = {"hrv": [[600]] * 100 + [None] * 300, "time": list(range(400))}
        summary = dfa_a1.summarize_dfa_a1(streams)
        self.assertFalse(summary["valid"])
        self.assertEqual(summary["coverage_pct"], 25.0)
        self.assertIn("coverage", summary["reason"])

    def test_high_artifact_rate_is_invalid_with_reason(self):
        rr = [600.0 if i % 2 == 0 else 900.0 for i in range(1500)]
        summary = dfa_a1.summarize_dfa_a1(_streams(rr))
        self.assertFalse(summary["valid"])
        self.assertGreater(summary["artifact_pct"], 10.0)
        self.assertIn("artifact", summary["reason"])

    def test_correlated_rr_series_is_mostly_above_aerobic_threshold(self):
        rr = _random_walk_rr(2 * 3600, seed=3, step=0.5)
        summary = dfa_a1.summarize_dfa_a1(_streams(rr))
        self.assertTrue(summary["valid"])
        self.assertLessEqual(summary["artifact_pct"], 10.0)
        self.assertGreater(summary["avg"], 0.75)
        self.assertGreaterEqual(summary["time_above_0_75_pct"], 80)
        self.assertEqual(summary["time_below_0_5_pct"], 0)
        self.assertNotIn("durability_label", summary)
        self.assertNotIn("drift", summary)

    def test_uncorrelated_rr_series_sits_around_half(self):
        rr = _white_noise_rr(2 * 3600, seed=4, sd=15.0)
        summary = dfa_a1.summarize_dfa_a1(_streams(rr))
        self.assertTrue(summary["valid"])
        self.assertLess(summary["avg"], 0.75)
        self.assertLessEqual(summary["time_above_0_75_pct"], 20)

    def test_threshold_estimate_needs_enough_band_windows(self):
        windows = [
            {"alpha1": 0.70, "avg_power": 200.0, "avg_hr": 140.0},
            {"alpha1": 0.80, "avg_power": 210.0, "avg_hr": 142.0},
        ]
        self.assertEqual(dfa_a1._threshold_estimate(windows), (None, None, 2))

        windows.append({"alpha1": 0.75, "avg_power": 190.0, "avg_hr": 138.0})
        windows.append({"alpha1": 1.10, "avg_power": 120.0, "avg_hr": 110.0})
        power, hr, count = dfa_a1._threshold_estimate(windows)
        self.assertEqual(count, 3)
        self.assertEqual(power, 200.0)
        self.assertEqual(hr, 140.0)


class PrepareActivitiesDfaGateTests(unittest.TestCase):
    def _ride(self, **overrides) -> dict:
        ride = {
            "id": "i1",
            "type": "Ride",
            "source": "GARMIN_CONNECT",
            "start_date_local": date.today().isoformat() + "T09:00:00",
            "moving_time": 2 * 3600,
            "icu_training_load": 90,
            "average_heartrate": 125,
            "icu_average_watts": 150,
            "stream_types": ["time", "watts", "heartrate", "hrv"],
            "tags": [],
        }
        ride.update(overrides)
        return ride

    def test_gate_accepts_long_aerobic_ride_with_hrv_stream(self):
        self.assertTrue(prepare_activities._needs_dfa_a1(self._ride(), "Base"))
        self.assertTrue(prepare_activities._needs_dfa_a1(self._ride(), "Pyramidal"))

    def test_gate_rejects_rides_without_hrv_stream_or_metadata(self):
        self.assertFalse(prepare_activities._needs_dfa_a1(self._ride(stream_types=["time", "watts"]), "Base"))
        self.assertFalse(prepare_activities._needs_dfa_a1(self._ride(stream_types=None), "Base"))
        ride = self._ride()
        ride.pop("stream_types")
        self.assertFalse(prepare_activities._needs_dfa_a1(ride, "Base"))

    def test_gate_rejects_short_hard_or_hr_less_rides(self):
        self.assertFalse(prepare_activities._needs_dfa_a1(self._ride(moving_time=45 * 60), "Base"))
        self.assertFalse(prepare_activities._needs_dfa_a1(self._ride(average_heartrate=None), "Base"))
        self.assertFalse(prepare_activities._needs_dfa_a1(self._ride(tags=["vo2max-high"]), "Base"))
        self.assertFalse(prepare_activities._needs_dfa_a1(self._ride(type="Race"), "Base"))

    def test_gate_skips_intentional_threshold_and_hard_group_rides(self):
        # 2x20 min at threshold: little Z5+, but classified Threshold -> not analyzed.
        self.assertFalse(prepare_activities._needs_dfa_a1(self._ride(), "Threshold"))
        # Fast group ride with mixed zones -> Unique/HIIT/Polarized -> not analyzed.
        for label in ("Unique", "HIIT", "Polarized", None):
            self.assertFalse(prepare_activities._needs_dfa_a1(self._ride(), label))
        # Tagged threshold/race work is skipped even when the distribution looks aerobic.
        for tag in ("lactate-threshold-moderate", "race-specific-high"):
            self.assertFalse(prepare_activities._needs_dfa_a1(self._ride(tags=[tag]), "Pyramidal"))
        self.assertTrue(prepare_activities._needs_dfa_a1(self._ride(tags=["aerobic-threshold-low"]), "Pyramidal"))

    def test_extract_fields_omits_summary_unless_provided(self):
        exported = prepare_activities.extract_fields(self._ride())
        self.assertNotIn("dfa_a1_summary", exported)

        summary = {"valid": False, "artifact_pct": 12.5, "coverage_pct": 98.0, "reason": "artifact rate"}
        exported = prepare_activities.extract_fields(self._ride(), dfa_a1_summary=summary)
        self.assertEqual(exported["dfa_a1_summary"], summary)

    def test_wbal_gate_uses_canonical_tag_prefixes(self):
        easy = self._ride(icu_zone_times=[{"id": "Z1", "secs": 1000}, {"id": "Z2", "secs": 3000}])
        self.assertFalse(prepare_activities._needs_wbal(easy, 0.0))
        self.assertTrue(prepare_activities._needs_wbal(self._ride(tags=["vo2max-high"]), 0.0))
        self.assertTrue(prepare_activities._needs_wbal(self._ride(tags=["race-specific-moderate"]), 0.0))
        self.assertTrue(prepare_activities._needs_wbal(self._ride(type="Race"), 0.0))
        # Undefined free-text tags such as "event" are no longer special.
        self.assertFalse(prepare_activities._needs_wbal(self._ride(tags=["event"]), 0.0))
        self.assertFalse(prepare_activities._needs_wbal(self._ride(tags=["aerobic-threshold-low"]), 0.0))

    def test_compute_wbal_summary_uses_prefetched_streams(self):
        ride = self._ride(icu_ftp=250, icu_w_prime=20000)
        streams = {"watts": [300.0] * 60 + [100.0] * 600, "time": list(range(660))}
        summary = prepare_activities._compute_wbal_summary(ride, streams)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["w_prime_j"], 20000.0)
        self.assertIsNone(prepare_activities._compute_wbal_summary(ride, None))
        self.assertIsNone(prepare_activities._compute_wbal_summary(self._ride(), streams))


class AerobicThresholdEstimateTests(unittest.TestCase):
    def test_returns_none_without_valid_summaries(self):
        activities = [
            {"id": "a"},
            {"id": "b", "dfa_a1_summary": {"valid": False, "artifact_pct": 15.0}},
        ]
        self.assertIsNone(analyze_week.compute_aerobic_threshold_estimate(activities, 265, [55, 75]))

    def test_returns_none_when_no_valid_ride_crossed_the_threshold(self):
        # Valid but entirely easy ride: per-ride summary exists, week aggregate is omitted.
        activities = [{"dfa_a1_summary": {"valid": True, "power_at_0_75": None, "time_above_0_75_pct": 100}}]
        self.assertIsNone(analyze_week.compute_aerobic_threshold_estimate(activities, 265, [55, 75]))

    def test_aggregates_crossing_rides_against_athlete_zone(self):
        activities = [
            {"dfa_a1_summary": {"valid": True, "power_at_0_75": 170, "hr_at_0_75": 125, "time_above_0_75_pct": 92}},
            {"dfa_a1_summary": {"valid": True, "power_at_0_75": 190, "hr_at_0_75": 131, "time_above_0_75_pct": 70}},
            {"dfa_a1_summary": {"valid": True, "power_at_0_75": None, "hr_at_0_75": None, "time_above_0_75_pct": 100}},
        ]
        estimate = analyze_week.compute_aerobic_threshold_estimate(activities, 265, [55, 75, 90])
        self.assertEqual(
            list(estimate),
            ["rides_used", "threshold_windows_total", "power_at_0_75", "hr_at_0_75",
             "z2_upper_power", "z2_upper_source", "delta_pct"],
        )
        self.assertEqual(estimate["rides_used"], 2)
        self.assertEqual(estimate["threshold_windows_total"], 2)
        self.assertEqual(estimate["power_at_0_75"], 180)
        self.assertEqual(estimate["hr_at_0_75"], 128)
        self.assertEqual(estimate["z2_upper_power"], 199)
        self.assertEqual(estimate["z2_upper_source"], "athlete_zones")
        self.assertEqual(estimate["delta_pct"], -9.5)

    def test_weights_rides_by_threshold_windows(self):
        activities = [
            {"dfa_a1_summary": {"valid": True, "power_at_0_75": 195, "hr_at_0_75": 140, "threshold_windows": 41, "time_above_0_75_pct": 42}},
            {"dfa_a1_summary": {"valid": True, "power_at_0_75": 170, "hr_at_0_75": 125, "threshold_windows": 18, "time_above_0_75_pct": 92}},
        ]
        estimate = analyze_week.compute_aerobic_threshold_estimate(activities, 265, [55, 75, 90])
        self.assertEqual(estimate["rides_used"], 2)
        self.assertEqual(estimate["threshold_windows_total"], 59)
        # (195*41 + 170*18) / 59 = 187.4 -> the firmer estimate dominates the plain mean of 182.5
        self.assertEqual(estimate["power_at_0_75"], 187)
        self.assertEqual(estimate["hr_at_0_75"], 135)
        self.assertEqual(estimate["delta_pct"], -6.0)

    def test_missing_threshold_windows_defaults_to_unit_weight(self):
        activities = [
            {"dfa_a1_summary": {"valid": True, "power_at_0_75": 200, "threshold_windows": 3}},
            {"dfa_a1_summary": {"valid": True, "power_at_0_75": 100, "threshold_windows": None}},
            {"dfa_a1_summary": {"valid": True, "power_at_0_75": 100, "threshold_windows": "bad"}},
        ]
        estimate = analyze_week.compute_aerobic_threshold_estimate(activities, None, None)
        self.assertEqual(estimate["threshold_windows_total"], 5)
        self.assertEqual(estimate["power_at_0_75"], 160)
        self.assertIsNone(estimate["hr_at_0_75"])

    def test_falls_back_to_75_percent_ftp_without_zones(self):
        activities = [{"dfa_a1_summary": {"valid": True, "power_at_0_75": 200, "time_above_0_75_pct": 80}}]
        estimate = analyze_week.compute_aerobic_threshold_estimate(activities, 300, None)
        self.assertEqual(estimate["z2_upper_power"], 225)
        self.assertEqual(estimate["z2_upper_source"], "ftp_75pct")
        self.assertEqual(estimate["delta_pct"], -11.1)

        estimate = analyze_week.compute_aerobic_threshold_estimate(activities, None, None)
        self.assertIsNone(estimate["z2_upper_power"])
        self.assertIsNone(estimate["delta_pct"])


class PowerZonesMetricTests(unittest.TestCase):
    def test_power_zones_pct_validates_input(self):
        self.assertEqual(get_metrics._power_zones_pct([55, 75, "90", None]), [55.0, 75.0, 90.0])
        self.assertIsNone(get_metrics._power_zones_pct(None))
        self.assertIsNone(get_metrics._power_zones_pct([]))
        self.assertIsNone(get_metrics._power_zones_pct("55,75"))


if __name__ == "__main__":
    unittest.main()
