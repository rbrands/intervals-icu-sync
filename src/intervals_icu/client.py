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
    # German umlauts
    '\u00e4': 'ae',   # ä
    '\u00f6': 'oe',   # ö
    '\u00fc': 'ue',   # ü
    '\u00c4': 'Ae',   # Ä
    '\u00d6': 'Oe',   # Ö
    '\u00dc': 'Ue',   # Ü
    '\u00df': 'ss',   # ß
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


def _raise_for_status_with_context(response: requests.Response, operation: str) -> None:
    """Raise HTTPError enriched with API status and response preview."""
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        request_url = response.request.url if response.request is not None else response.url
        body_preview = (response.text or "").strip().replace("\n", " ")[:400]
        message = (
            f"{operation} failed with HTTP {response.status_code} {response.reason} "
            f"for {request_url}"
        )
        if body_preview:
            message = f"{message}; response body: {body_preview}"
        raise requests.HTTPError(message, response=response, request=response.request) from exc


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
    _raise_for_status_with_context(response, "get_events")
    return response.json()


def get_library_workouts(api_key: str, athlete_id: str) -> list:
    """Fetch all workouts from the athlete's workout library.

    Raises:
        requests.HTTPError: If the response status code is not 2xx.
    """
    url = f"{BASE_URL}/athlete/{athlete_id}/workouts"
    response = requests.get(
        url,
        auth=("API_KEY", api_key),
        timeout=30,
    )
    _raise_for_status_with_context(response, "get_library_workouts")
    return response.json()


def get_library_workout(api_key: str, athlete_id: str, workout_id: int) -> dict:
    """Fetch one workout from the athlete's workout library."""
    url = f"{BASE_URL}/athlete/{athlete_id}/workouts/{workout_id}"
    response = requests.get(
        url,
        auth=("API_KEY", api_key),
        timeout=30,
    )
    _raise_for_status_with_context(response, "get_library_workout")
    return response.json()


def get_library_folders(api_key: str, athlete_id: str) -> list:
    """Fetch all workout folders and plans from the athlete's library.

    Raises:
        requests.HTTPError: If the response status code is not 2xx.
    """
    url = f"{BASE_URL}/athlete/{athlete_id}/folders"
    response = requests.get(
        url,
        auth=("API_KEY", api_key),
        timeout=30,
    )
    _raise_for_status_with_context(response, "get_library_folders")
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
        data=_json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=30,
    )
    _raise_for_status_with_context(response, "update_event")
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
    _raise_for_status_with_context(response, "delete_events_range")


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
        timeout=30,
    )

    _raise_for_status_with_context(response, "get_activities")

    return response.json()


def get_athlete_summary(
    api_key: str,
    athlete_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Fetch the athlete's server-side summary for a date range."""
    url = f"{BASE_URL}/athlete/{athlete_id}/athlete-summary.json"
    response = requests.get(
        url,
        auth=("API_KEY", api_key),
        params={"start": start_date, "end": end_date},
        timeout=30,
    )
    _raise_for_status_with_context(response, "get_athlete_summary")

    summaries = response.json()
    if not isinstance(summaries, list):
        raise ValueError("get_athlete_summary returned a non-list response")
    summary = next(
        (
            summary
            for summary in summaries
            if str(summary.get("athlete_id")) == str(athlete_id)
        ),
        None,
    )
    if summary is None:
        raise ValueError(f"get_athlete_summary returned no data for athlete {athlete_id}")
    return summary


def create_activity(
    api_key: str,
    athlete_id: str,
    name: str,
    start_date_local: str,
    duration: int,
    description: str = "",
    planned: bool = True,
    workout: dict | None = None,
    raw_workout_doc: dict | None = None,
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
        raw_workout_doc: Optional native intervals.icu workout document copied
                         from a library workout. Sent unchanged when provided.

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

    if raw_workout_doc is not None:
        payload["workout_doc"] = raw_workout_doc
    elif workout is not None and "steps" in workout:
        zwo = _steps_to_zwo(name, _ascii_safe(description), workout["steps"])
        payload["file_contents_base64"] = base64.b64encode(zwo.encode()).decode()
        payload["filename"] = "workout.zwo"

    response = requests.post(
        url,
        auth=("API_KEY", api_key),
        data=_json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        params={"upsertOnUid": "true" if uid is not None else "false"},
        timeout=30,
    )
    _raise_for_status_with_context(response, "create_activity")

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
    _raise_for_status_with_context(response, "get_activity_power_curve")
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
    _raise_for_status_with_context(response, "get_activity_streams")
    return response.json()


def _resample_series(values: list[float], max_points: int) -> list[float]:
    """Downsample a numeric series to at most ``max_points`` points."""
    if not values:
        return []
    if max_points < 1:
        raise ValueError("max_points must be >= 1")
    if len(values) <= max_points:
        return values
    if max_points == 1:
        return [values[-1]]

    indices = [round(i * (len(values) - 1) / (max_points - 1)) for i in range(max_points)]
    deduped: list[float] = []
    seen: set[int] = set()
    for idx in indices:
        if idx in seen:
            continue
        seen.add(idx)
        deduped.append(values[idx])
    return deduped


def _apply_stream_filters(
    stream_map: dict[str, list[float]],
    *,
    start_time_s: int | None,
    end_time_s: int | None,
    start_distance_m: float | None,
    end_distance_m: float | None,
) -> set[int] | None:
    """Return the indices to keep for all selected streams, or None when no filtering is requested."""
    if start_time_s is None and end_time_s is None and start_distance_m is None and end_distance_m is None:
        return None

    indices: set[int] | None = None

    if start_time_s is not None or end_time_s is not None:
        time_values = stream_map.get("time") or []
        time_indices = {
            idx
            for idx, value in enumerate(time_values)
            if (start_time_s is None or value >= start_time_s)
            and (end_time_s is None or value <= end_time_s)
        }
        indices = time_indices if indices is None else indices & time_indices

    if start_distance_m is not None or end_distance_m is not None:
        distance_values = stream_map.get("distance") or []
        distance_indices = {
            idx
            for idx, value in enumerate(distance_values)
            if (start_distance_m is None or value >= start_distance_m)
            and (end_distance_m is None or value <= end_distance_m)
        }
        indices = distance_indices if indices is None else indices & distance_indices

    return indices


def get_activity_streams_sampled(
    api_key: str,
    activity_id: str,
    stream_types: list[str] | None = None,
    max_points: int = 300,
    start_time_s: int | None = None,
    end_time_s: int | None = None,
    start_distance_m: float | None = None,
    end_distance_m: float | None = None,
) -> dict:
    """Fetch sampled time-series streams for a single activity.

    This returns a compact subset of the raw stream payload, filtered by optional
    time or distance bounds and down-sampled to a fixed number of points. By
    default it includes the most useful cycling streams: time, distance,
    altitude, heartrate, and velocity.
    """
    if max_points < 1:
        raise ValueError("max_points must be >= 1")

    raw_streams = get_activity_streams(api_key, activity_id)
    stream_map = {
        entry.get("type"): entry.get("data", [])
        for entry in raw_streams
        if isinstance(entry, dict) and isinstance(entry.get("type"), str)
    }

    allowed = {
        "time",
        "distance",
        "altitude",
        "heartrate",
        "velocity",
        "watts",
        "cadence",
        "grade",
        "temp",
    }
    selected = [s.lower() for s in (stream_types or ["time", "distance", "altitude", "heartrate", "velocity"]) if s]
    selected = [s for s in selected if s in allowed]
    if not selected:
        selected = ["time", "distance", "altitude", "heartrate", "velocity"]

    filters = _apply_stream_filters(
        stream_map,
        start_time_s=start_time_s,
        end_time_s=end_time_s,
        start_distance_m=start_distance_m,
        end_distance_m=end_distance_m,
    )

    result = {
        "activity_id": str(activity_id),
        "sampled": True,
        "point_count": max_points,
        "streams": {},
    }

    for stream_type in selected:
        values = list(stream_map.get(stream_type, []) or [])
        if not values:
            continue
        if filters is not None:
            values = [values[idx] for idx in sorted(filters) if idx < len(values)]
        sampled = _resample_series(values, max_points)
        if sampled:
            result["streams"][stream_type] = sampled

    if result["streams"]:
        result["point_count"] = max(len(v) for v in result["streams"].values())

    return result


def get_activity_intervals(api_key: str, activity_id: str) -> dict:
    """Fetch intervals/laps for a single activity.

    Returns a dict with keys such as ``icu_intervals`` and ``icu_groups``.

    Raises:
        requests.HTTPError: If the response status code is not 2xx.
    """
    url = f"{BASE_URL}/activity/{activity_id}/intervals"
    response = requests.get(
        url,
        auth=("API_KEY", api_key),
        timeout=60,
    )
    _raise_for_status_with_context(response, "get_activity_intervals")
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
    _raise_for_status_with_context(response, "get_training_plan")
    return response.json()
