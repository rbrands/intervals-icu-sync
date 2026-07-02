import unittest

from webservice.mcp_server import _summarize_script_failure


class McpServerErrorSummaryTests(unittest.TestCase):
    def test_http_error_traceback_is_collapsed_into_concise_hint(self):
        output = """
Traceback (most recent call last):
  File "/tmp/src/intervals_icu/client.py", line 70, in _raise_for_status_with_context
    response.raise_for_status()
requests.exceptions.HTTPError: get_activities failed with HTTP 404 Not Found for https://intervals.icu/api/v1/athlete/123/activities; response body: {\"message\": \"Not found\"}
"""

        summary = _summarize_script_failure(output)

        self.assertIn("get_activities failed with HTTP 404 Not Found", summary)
        self.assertIn("Check ATHLETE_ID", summary)
        self.assertNotIn("Traceback", summary)

    def test_non_http_exception_returns_last_exception_line(self):
        output = """
Traceback (most recent call last):
  File "/tmp/script.py", line 1, in <module>
    raise ValueError("bad input")
ValueError: bad input
"""

        summary = _summarize_script_failure(output)

        self.assertEqual(summary, "ValueError: bad input")


if __name__ == "__main__":
    unittest.main()