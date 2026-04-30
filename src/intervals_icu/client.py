import base64
import json as _json
import requests

BASE_URL = "https://intervals.icu/api/v1"

_ASCII_FALLBACKS = {
    '\u2013': '-',    # en dash –
    '\u2014': '-',    # em dash —
    '\u2018': "'",    # left single quote '
    '\u2019': "'",    # right single quote '
    '\u201c': '"',    # left double quote "
    '\u201d': '"',    # right double quote "
    '\u2026': '...',  # ellipsis …
    '\u00b0': 'deg',  # degree °
    '\u00d7': 'x',    # multiplication ×
}


def _ascii_safe(text: str) -> str:
    """Replace common non-ASCII typography with ASCII equivalents."""
    for char, replacement in _ASCII_FALLBACKS.items():
        text = text.replace(char, replacement)
    return text.encode('ascii', errors='replace').decode().replace('?', '_')


def _xml_escape(text: str) -> str:
    """Escape XML special chars; encode non-ASCII as numeric character references."""
    text = (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in text)


def _steps_to_zwo(name: str, description: str, steps: list[dict]) -> str:
    """Convert a list of workout steps to ZWO XML format."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<workout_file>",
        f"  <name>{_xml_escape(name)}</name>",
        f"  <description>{_xml_escape(description)}</description>",
        "  <sportType>bike</sportType>",
        "  <workout>",
    ]
    for step in steps:
        dur = int(step.get("duration") or step.get("duration_seconds") or 0)
        pct = float(step.get("power") or step.get("power_pct_ftp") or 0)
        power = pct / 100.0
        if dur <= 0:
            continue
        lines.append(f'    <SteadyState Duration="{dur}" Power="{power}"/>')
    lines += ["  </workout>", "</workout_file>"]
    return "\n".join(lines)


def get_events(api_key: str, athlete_id: str, oldest: str, newest: str) -> list:
    """Fetch WORKOUT events for the given date range.

    Returns:
        List of event dicts. Each dict contains at least ``id``, ``name``,
        and ``start_date_local``.

    Raises:
        requests.HTTPError: If the response status code is not 2xx.
    """
    url = f"{BASE_URL}/athlete/{athlete_id}/events.json"
    response = requests.get(
        url,
        auth=("API_KEY", api_key),
        params={"oldest": oldest, "newest": newest, "category": "WORKOUT"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def update_event(api_key: str, athlete_id: str, event_id: int, payload: dict) -> dict:
    """Update an existing event via PUT.

    Raises:
        requests.HTTPError: If the response status code is not 2xx.
    """
    url = f"{BASE_URL}/athlete/{athlete_id}/events/{event_id}"
    response = requests.put(
        url,
        auth=("API_KEY", api_key),
        data=_json.dumps(payload, ensure_ascii=True).encode("ascii"),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def delete_events_range(api_key: str, athlete_id: str, oldest: str, newest: str) -> None:
    """Delete all WORKOUT events in the given date range.

    Args:
        api_key: The intervals.icu API key.
        athlete_id: The intervals.icu athlete ID.
        oldest: First date to delete (ISO-8601, e.g. "2026-04-10").
        newest: Last date to delete, inclusive (ISO-8601, e.g. "2026-04-12").

    Raises:
        requests.HTTPError: If the response status code is not 2xx.
    """
    url = f"{BASE_URL}/athlete/{athlete_id}/events"
    response = requests.delete(
        url,
        auth=("API_KEY", api_key),
        params={"oldest": oldest, "newest": newest, "category": "WORKOUT"},
        timeout=30,
    )
    response.raise_for_status()


def get_activities(api_key: str, athlete_id: str, start_date: str, end_date: str) -> list:
    """Fetch activities from intervals.icu for the given date range.

    Args:
        api_key: The intervals.icu API key.
        athlete_id: The intervals.icu athlete ID.
        start_date: The start date in ISO 8601 format (e.g. "2024-01-01").
        end_date: The end date in ISO 8601 format (e.g. "2024-01-07").

    Returns:
        A list of activity dicts as returned by the API.

    Raises:
        requests.HTTPError: If the response status code is not 2xx.
    """
    url = f"{BASE_URL}/athlete/{athlete_id}/activities"

    
    response = requests.get(
        url,
        auth=("API_KEY", api_key),
        params={"oldest": start_date, "newest": end_date},
    )
  
    response.raise_for_status()

    return response.json()


def create_activity(
    api_key: str,
    athlete_id: str,
    name: str,
    start_date_local: str,
    duration: int,
    description: str = "",
    planned: bool = True,
    workout: dict | None = None,
    uid: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Create a planned workout on intervals.icu.

    Args:
        api_key: The intervals.icu API key.
        athlete_id: The intervals.icu athlete ID.
        name: Display name of the activity.
        start_date_local: ISO 8601 datetime string, e.g. "2026-04-12T09:00:00".
        duration: Planned duration in seconds.
        description: Optional notes / fueling plan text.
        planned: When True the activity is created as a planned workout,
                 not as a completed ride.
        workout: Optional structured workout definition.  Each step is a dict
                 with ``duration`` (seconds) and ``power`` (fraction of FTP,
                 e.g. 0.95 = 95 %).  Example::

                     {"steps": [{"duration": 900, "power": 0.95}, ...]}

    Returns:
        The created event dict as returned by the API.

    Raises:
        requests.HTTPError: If the response status code is not 2xx.
    """
    url = f"{BASE_URL}/athlete/{athlete_id}/events"

    payload = {
        "name": name,
        "start_date_local": start_date_local,
        "type": "Ride",
        "category": "WORKOUT",
        "moving_time": duration,
        "description": description,
    }
    if uid is not None:
        payload["uid"] = uid
    if tags:
        payload["tags"] = tags

    if workout is not None and "steps" in workout:
        zwo = _steps_to_zwo(name, _ascii_safe(description), workout["steps"])
        payload["file_contents_base64"] = base64.b64encode(zwo.encode()).decode()
        payload["filename"] = "workout.zwo"

    response = requests.post(
        url,
        auth=("API_KEY", api_key),
        data=_json.dumps(payload, ensure_ascii=True).encode("ascii"),
        headers={"Content-Type": "application/json"},
        params={"upsertOnUid": "true" if uid is not None else "false"},
        timeout=30,
    )
    response.raise_for_status()

    return response.json()


_POWER_CURVE_TARGETS = {5: "p5s", 20: "p20s", 60: "p60s", 180: "p3m", 300: "p5m", 600: "p10m", 720: "p12m", 1200: "p20m"}


def get_activity_power_curve(api_key: str, activity_id: str) -> dict | None:
    """Fetch best-effort power values for key durations from the activity power curve.

    Returns a dict with keys ``p5s``, ``p20s``, ``p60s``, ``p3m``, ``p5m``,
    ``p10m``, ``p12m``, ``p20m`` (watts), or ``None`` if no power curve is
    available for this activity.

    Raises:
        requests.HTTPError: If the response status code is not 2xx.
    """
    url = f"{BASE_URL}/activity/{activity_id}/power-curves"
    response = requests.get(url, auth=("API_KEY", api_key), timeout=30)
    response.raise_for_status()
    body = response.json()
    if not body:
        return None
    curve = body[0]
    secs = curve.get("secs") or []
    watts = curve.get("watts") or []
    result = {}
    for s, w in zip(secs, watts):
        if s in _POWER_CURVE_TARGETS:
            result[_POWER_CURVE_TARGETS[s]] = w
    return result if result else None


def get_activity_streams(api_key: str, activity_id: str) -> list[dict]:
    """Fetch time-series streams for a single activity.

    Returns a list of stream dicts, each with a ``type`` key (e.g. ``"watts"``,
    ``"heartrate"``, ``"time"``) and a ``data`` list of values sampled once per
    second.

    Raises:
        requests.HTTPError: If the response status code is not 2xx.
    """
    url = f"{BASE_URL}/activity/{activity_id}/streams"
    response = requests.get(
        url,
        auth=("API_KEY", api_key),
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def get_training_plan(api_key: str, athlete_id: str) -> dict:
    """Fetch the athlete's current training plan from intervals.icu.

    Returns:
        A dict with the ``AthleteTrainingPlan`` object. Key fields:
        - ``training_plan_id`` – int or None if no plan is assigned
        - ``training_plan_start_date`` – ISO-8601 date string
        - ``training_plan_last_applied`` – ISO-8601 datetime string
        - ``training_plan_alias`` – optional alias name
        - ``training_plan`` – ``Folder`` object with plan details and workouts
          (``children`` list)

    Raises:
        requests.HTTPError: If the response status code is not 2xx.
    """
    url = f"{BASE_URL}/athlete/{athlete_id}/training-plan"
    response = requests.get(
        url,
        auth=("API_KEY", api_key),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
