import asyncio
import contextlib
import copy
import importlib.util
import io
import json
import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from intervals_icu.data_quality import check_athlete_data, check_athlete_data_json
from intervals_icu.prompt_templates import render_coach_prompt


def complete_data():
    return {
        "current_date": "2026-10-11",
        "week_starting": "2026-10-05",
        "lookback_days": 7,
        "metrics": {
            "ftp": 250, "rolling_ftp": 250, "eftp": 250,
            "w_prime": 20000, "rolling_w_prime": 20000,
            "resting_hr": 50, "hrv": None, "sleep_secs": None,
            "power_profile": {"p20min": {"watts": 270}, "period_days": 42},
        },
        "week_summary": {"training_plan": [{"week": "2026-10-05", "phase": "Base"},
                                           {"week": "2026-10-12", "phase": "Build"}]},
        "activities": [
            {"date": day, "rpe": 0, "carbs_ingested_g": 0}
            for day in ("2026-10-04", "2026-10-07", "2026-10-11")
        ],
        "training_load_history": [{"weekly_load_target": 0}],
    }


def area(report, name):
    return next(check for check in report["checks"] if check["area"] == name)


class DataQualityTests(unittest.TestCase):
    def test_complete_report_and_no_mutation(self):
        data = complete_data()
        original = copy.deepcopy(data)
        report = check_athlete_data(data)
        self.assertEqual(data, original)
        self.assertEqual(report["overall"], "Good")
        self.assertEqual(report["non_ok_count"], 0)
        self.assertEqual(len(report["checks"]), 7)
        self.assertTrue(all(check["status"] == "OK" for check in report["checks"]))
        self.assertEqual(len(report["report_text"].splitlines()), 8)
        self.assertEqual(json.loads(check_athlete_data_json(json.dumps(data))), report)

    def test_exact_comparison_thresholds_in_both_directions(self):
        for baseline, estimate_name, check_name in (
            ("ftp", "rolling_ftp", "ftp_consistency"),
            ("ftp", "eftp", "ftp_consistency"),
            ("w_prime", "rolling_w_prime", "w_prime_consistency"),
        ):
            for delta, status in (
                (9.999, "OK"), (10, "Warning"), (20, "Warning"), (20.001, "Missing"),
            ):
                for direction in (-1, 1):
                    with self.subTest(field=estimate_name, delta=delta, direction=direction):
                        data = complete_data()
                        data["metrics"][baseline] = 100
                        if baseline == "ftp":
                            data["metrics"]["rolling_ftp"] = 100
                            data["metrics"]["eftp"] = 100
                        data["metrics"][estimate_name] = 100 + direction * delta
                        check = area(check_athlete_data(data), check_name)
                        self.assertEqual(check["status"], status)
                        if status == "Missing":
                            self.assertIn("inconsistent", check["explanation"])

    def test_missing_and_non_positive_comparison_values(self):
        for field in ("ftp", "rolling_ftp", "eftp", "w_prime", "rolling_w_prime"):
            for value in (None, 0, -1):
                with self.subTest(field=field, value=value):
                    data = complete_data()
                    data["metrics"][field] = value
                    name = "w_prime_consistency" if "w_prime" in field else "ftp_consistency"
                    self.assertEqual(area(check_athlete_data(data), name)["status"], "Missing")

    def test_p20_context_does_not_change_status_or_overall(self):
        data = complete_data()
        data["metrics"]["power_profile"]["p20min"]["watts"] = 200
        report = check_athlete_data(data)
        check = area(report, "ftp_consistency")
        self.assertEqual(report["overall"], "Good")
        self.assertEqual(check["status"], "OK")
        self.assertIn("42-day", check["context"][0])
        self.assertIn("not a data error", check["context"][0])
        self.assertEqual(check["evidence"]["p20min_implied_ftp"], 190)

    def test_p20_exact_twenty_percent_is_not_flagged(self):
        data = complete_data()
        data["metrics"]["ftp"] = 95
        data["metrics"]["rolling_ftp"] = 95
        data["metrics"]["eftp"] = 95
        data["metrics"]["power_profile"]["p20min"]["watts"] = 80
        self.assertEqual(area(check_athlete_data(data), "ftp_consistency")["context"], [])

    def test_absent_power_profile_does_not_affect_ftp_comparison(self):
        data = complete_data()
        del data["metrics"]["power_profile"]
        self.assertEqual(area(check_athlete_data(data), "ftp_consistency")["status"], "OK")

    def test_season_plan_requires_macrocycle_phase_for_both_weeks(self):
        data = complete_data()
        data["week_summary"]["training_plan"] = [
            {"week": "2026-10-05", "day_constraints": [{"type": "LIMITED"}]},
            {"week": "2026-10-12", "day_constraints": [{"type": "UNAVAILABLE"}]},
        ]
        check = area(check_athlete_data(data), "season_plan")
        self.assertEqual(check["status"], "Missing")
        self.assertTrue(check["evidence"]["current_week_present"])
        self.assertTrue(check["evidence"]["next_week_present"])
        self.assertFalse(check["evidence"]["current_week_phase_present"])
        self.assertFalse(check["evidence"]["next_week_phase_present"])

        data["week_summary"]["training_plan"][0]["phase"] = "Base"
        check = area(check_athlete_data(data), "season_plan")
        self.assertEqual(check["status"], "Warning")
        self.assertTrue(check["evidence"]["current_week_phase_present"])
        self.assertFalse(check["evidence"]["next_week_phase_present"])

        data["week_summary"]["training_plan"][1]["phase"] = "Build"
        self.assertEqual(area(check_athlete_data(data), "season_plan")["status"], "OK")

    def test_missing_empty_or_next_week_only_plan(self):
        for summary in (None, {}, {"training_plan": None}, {"training_plan": []},
                        {"training_plan": [{"week": "2026-10-05"}]},
                        {"training_plan": [{"week": "2026-10-12", "phase": "Build"}]}):
            with self.subTest(summary=summary):
                data = complete_data()
                data["week_summary"] = summary
                self.assertNotEqual(area(check_athlete_data(data), "season_plan")["status"], "OK")

    def test_wellness_non_null_rule(self):
        for field in ("resting_hr", "hrv", "sleep_secs"):
            data = complete_data()
            data["metrics"].update(resting_hr=None, hrv=None, sleep_secs=None)
            self.assertEqual(area(check_athlete_data(data), "wellness_tracking")["status"], "Missing")
            data["metrics"][field] = 0
            self.assertEqual(area(check_athlete_data(data), "wellness_tracking")["status"], "OK")

    def test_window_includes_lower_boundary_and_today_but_not_future(self):
        data = complete_data()
        data["activities"] += [
            {"date": "2026-10-03"}, {"date": "2026-10-12"},
        ]
        report = check_athlete_data(data)
        self.assertEqual(area(report, "recent_activity_density")["evidence"]["activity_count"], 3)
        self.assertEqual(area(report, "activity_feedback")["status"], "OK")

    def test_activity_density_and_empty_feedback(self):
        for count, status in ((0, "Missing"), (1, "Warning"), (2, "Warning"), (3, "OK")):
            data = complete_data()
            data["activities"] = data["activities"][:count]
            report = check_athlete_data(data)
            self.assertEqual(area(report, "recent_activity_density")["status"], status)
            self.assertEqual(area(report, "activity_feedback")["status"], "OK" if count else "Missing")

    def test_feedback_partial_and_completely_missing_fields(self):
        for field in ("rpe", "carbs_ingested_g"):
            for missing_count, status in ((1, "Warning"), (2, "Warning"), (3, "Missing")):
                data = complete_data()
                for activity in data["activities"][:missing_count]:
                    activity.pop(field)
                check = area(check_athlete_data(data), "activity_feedback")
                self.assertEqual(check["status"], status)

    def test_feedback_complementary_gaps_are_warning(self):
        data = complete_data()
        data["activities"][0]["rpe"] = None
        data["activities"][1]["carbs_ingested_g"] = None
        self.assertEqual(area(check_athlete_data(data), "activity_feedback")["status"], "Warning")

    def test_history_any_non_null_target_including_zero(self):
        for history, status in (
            (None, "Missing"), ([], "Missing"), ([{}], "Missing"),
            ([{"weekly_load_target": None}, {"weekly_load_target": 0}], "OK"),
        ):
            data = complete_data()
            data["training_load_history"] = history
            self.assertEqual(area(check_athlete_data(data), "load_target_history")["status"], status)

    def test_overall_counts_areas_not_missing_individual_fields(self):
        data = complete_data()
        data["metrics"]["rolling_ftp"] = None
        data["metrics"]["eftp"] = None
        self.assertEqual(check_athlete_data(data)["non_ok_count"], 1)
        self.assertEqual(check_athlete_data(data)["overall"], "Partial")
        data["training_load_history"] = []
        self.assertEqual(check_athlete_data(data)["overall"], "Partial")
        data["week_summary"] = None
        self.assertEqual(check_athlete_data(data)["overall"], "Limited")
        self.assertIn("season plan", check_athlete_data(data)["suggested_fix"])

    def test_absent_sections_are_missing_not_invalid(self):
        data = {key: value for key, value in complete_data().items()
                if key in ("current_date", "week_starting", "lookback_days")}
        report = check_athlete_data(data)
        self.assertEqual(report["non_ok_count"], 7)
        self.assertEqual(report["overall"], "Limited")

    def test_invalid_metadata_and_shapes_raise_explicit_errors(self):
        for update in (
            {"current_date": "not-a-date"}, {"week_starting": "2026-10-06"},
            {"lookback_days": 0}, {"lookback_days": True}, {"lookback_days": "7"},
            {"metrics": []}, {"activities": [{}]}, {"activities": [{"date": "bad"}]},
            {"week_summary": {"training_plan": {}}},
            {"metrics": {"ftp": True}}, {"metrics": {"ftp": float("nan")}},
            {"metrics": {"ftp": float("inf")}},
            {"lookback_days": 999999999999},
        ):
            with self.subTest(update=update):
                data = complete_data()
                data.update(update)
                with self.assertRaisesRegex(ValueError, "Invalid athlete_data"):
                    check_athlete_data(data)
        for field in ("current_date", "week_starting", "lookback_days"):
            data = complete_data()
            del data[field]
            with self.assertRaisesRegex(ValueError, field):
                check_athlete_data(data)

    def test_invalid_json_and_payload_errors_do_not_echo_data(self):
        for payload in ("{secret-key", "[]", "null", '{"metrics": "secret-key"}',
                        '{"current_date": "secret-key", "week_starting": "bad", "lookback_days": 7}'):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError) as caught:
                    check_athlete_data_json(payload)
                self.assertNotIn("secret-key", str(caught.exception))

    def test_consistency_prompt_prefers_tool_and_retains_manual_feedback_rules(self):
        prompt = render_coach_prompt("consistency", "en")
        self.assertIn("check_athlete_data", prompt)
        self.assertIn("carbs_ingested_g", prompt)
        self.assertIn("10-20% (inclusive)", prompt)


class DataQualityMcpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {"INTERVALS_API_KEY": "test-key", "ATHLETE_ID": "test-athlete"}):
            spec = importlib.util.spec_from_file_location(
                "data_quality_local_mcp", REPO_ROOT / "scripts" / "mcp_server.py",
            )
            assert spec and spec.loader
            cls.local = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.local)
        from webservice import mcp_server
        cls.hosted = mcp_server

    def test_both_mcp_tools_return_identical_reports_without_fetching(self):
        payload = json.dumps(complete_data())
        for server in (self.local, self.hosted):
            with patch.object(server, "prepare_week_data", side_effect=AssertionError("No fetch")):
                report = server.check_athlete_data(payload)
                self.assertEqual(report, check_athlete_data(complete_data()))
                tool = server.mcp._tool_manager.get_tool("check_athlete_data")
                self.assertIsNotNone(tool)
                self.assertIn("athlete_data", tool.parameters["properties"])
                self.assertEqual(tool.output_schema["type"], "object")
                self.assertIn("checks", tool.output_schema["properties"])
                self.assertIn("overall", tool.output_schema["properties"])
                content, structured = asyncio.run(server.mcp.call_tool(
                    "check_athlete_data", {"athlete_data": payload},
                ))
                self.assertEqual(json.loads(content[0].text), report)
                self.assertEqual(structured, report)
                self.assertNotIn("result", structured)

    def test_malformed_payload_raises_tool_error_and_hosted_logs(self):
        with self.assertRaises(ValueError):
            self.local.check_athlete_data("[]")
        with patch.object(self.hosted, "_emit_tool_error") as emit:
            with self.assertRaises(ValueError):
                self.hosted.check_athlete_data("[]")
            emit.assert_called_once()


class DataQualityLocalIntegrationTests(unittest.TestCase):
    def run_cli(self, payload, *args):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "coach_input.json"
            input_path.write_text(payload, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts" / "check_athlete_data.py"),
                 "--input", str(input_path), *args],
                cwd=directory, capture_output=True, text=True, check=False,
            )

    def test_cli_text_and_json_match_shared_report_from_any_directory(self):
        data = complete_data()
        expected = check_athlete_data(data)
        text = self.run_cli(json.dumps(data))
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertEqual(text.stdout.strip(), expected["report_text"])
        structured = self.run_cli(json.dumps(data), "--json")
        self.assertEqual(structured.returncode, 0, structured.stderr)
        self.assertEqual(json.loads(structured.stdout), expected)

    def test_cli_limited_report_is_successful_execution(self):
        data = complete_data()
        data["metrics"] = None
        result = self.run_cli(json.dumps(data), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["overall"], "Limited")

    def test_cli_invalid_inputs_exit_one_without_success_report(self):
        for payload in ("{", "[]", "{}"):
            with self.subTest(payload=payload):
                result = self.run_cli(payload)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Error:", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_cli_missing_file_exits_one(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts" / "check_athlete_data.py"),
                 "--input", str(Path(directory) / "missing.json")],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error:", result.stderr)

    def test_cli_default_is_current_week_not_latest_file(self):
        spec = importlib.util.spec_from_file_location(
            "check_data_cli", REPO_ROOT / "scripts" / "check_athlete_data.py",
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            processed = root / "data" / "processed"
            processed.mkdir(parents=True)
            data = complete_data()
            (processed / "coach_input_2026-10-05.json").write_text(json.dumps(data))
            with patch.object(module, "ROOT", root), patch.object(module, "date") as day:
                from datetime import date
                day.today.return_value = date(2026, 10, 11)
                with patch.object(sys, "argv", ["check_athlete_data.py"]), contextlib.redirect_stdout(io.StringIO()) as out:
                    module.main()
                self.assertIn("Overall data completeness: Good", out.getvalue())
                day.today.return_value = date(2026, 10, 12)
                with patch.object(sys, "argv", ["check_athlete_data.py"]), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as caught:
                        module.main()
                self.assertEqual(caught.exception.code, 1)

    def test_notebook_cell_uses_loaded_data_and_handles_legacy_exports(self):
        import pandas as pd
        notebook = json.loads((REPO_ROOT / "notebooks" / "week_summary.ipynb").read_text())
        code = "".join(next(
            cell["source"] for cell in notebook["cells"] if cell["id"] == "data-quality-check"
        ))
        data = complete_data()
        displays = []
        namespace = {
            "loaded": data, "data": data, "pd": pd, "display": displays.append,
            "input_file": REPO_ROOT / "data" / "processed" / "coach_input_2026-10-05.json",
        }
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(code, "data-quality-check", "exec"), namespace)
        self.assertEqual(namespace["quality_report"], check_athlete_data(data))
        self.assertEqual(len(displays[0]), 7)
        namespace["loaded"] = []
        with contextlib.redirect_stdout(io.StringIO()) as out:
            exec(compile(code, "data-quality-check", "exec"), namespace)
        self.assertIsNone(namespace["quality_report"])
        self.assertIn("unavailable", out.getvalue())
        self.assertEqual(len(displays), 1)


if __name__ == "__main__":
    unittest.main()
