"""DFA alpha 1 – short-term detrended fluctuation analysis of R-R intervals.

Shared module used by prepare_activities_for_coach.py to derive an in-ride
autonomic intensity marker from the ``hrv`` activity stream that intervals.icu
stores when HRV logging is enabled on the head unit.

Method reference:
    Peng et al. (1995) – detrended fluctuation analysis
    Gronwald, Rogers & Hoos (2020) – DFA a1 ≈ 0.75 as aerobic threshold (LT1/VT1)
    Rogers et al. (2021) – DFA a1 ≈ 0.50 discussed as anaerobic threshold (LT2)

The ``hrv`` stream has one entry per second: ``None`` when no beat was
recorded, otherwise a list of R-R intervals (ms) that ended in that second.

DFA a1 is NOT the resting / nightly HRV (RMSSD) reported in ``metrics.hrv``;
it is a dimensionless scaling exponent that *falls* with rising intensity.
"""

from __future__ import annotations

import math
from bisect import bisect_left

DFA_A1_AEROBIC_THRESHOLD = 0.75
DFA_A1_ANAEROBIC_THRESHOLD = 0.50

DEFAULT_WINDOW_SECONDS = 120
DEFAULT_STEP_SECONDS = 30
WARMUP_SECONDS = 600
SHORT_TERM_SCALES = tuple(range(4, 17))

# Beat-to-beat change above this fraction of the previous interval is an artifact.
ARTIFACT_JUMP_FRACTION = 0.20
MAX_WINDOW_ARTIFACT_PCT = 5.0
MAX_ACTIVITY_ARTIFACT_PCT = 10.0
MIN_COVERAGE_PCT = 50.0
MIN_BEATS_PER_WINDOW = 60
MIN_WINDOW_COVERAGE_PCT = 80.0
MAX_WINDOW_GAP_SECONDS = 5
MIN_VALID_WINDOWS = 10

THRESHOLD_BAND = (0.65, 0.85)
MIN_THRESHOLD_WINDOWS = 3

Beat = tuple[float, float]


# ---------------------------------------------------------------------------
# Stream parsing and artifact detection
# ---------------------------------------------------------------------------

def parse_rr_stream(hrv_data: list, time_data: list | None = None) -> list[Beat]:
    """Flatten the per-second ``hrv`` stream into ``(time_s, rr_ms)`` beats.

    ``time_data`` supplies the per-sample timestamps; when omitted the list
    index is used as seconds from start.
    """
    beats: list[Beat] = []
    for index, entry in enumerate(hrv_data or []):
        if entry is None:
            continue
        if time_data is not None and index < len(time_data) and time_data[index] is not None:
            second = float(time_data[index])
        else:
            second = float(index)
        values = entry if isinstance(entry, (list, tuple)) else [entry]
        for raw in values:
            try:
                rr = float(raw)
            except (TypeError, ValueError):
                continue
            if rr > 0:
                beats.append((second, rr))
    return beats


def flag_artifacts(rr_values: list[float], jump_fraction: float = ARTIFACT_JUMP_FRACTION) -> list[bool]:
    """Return a per-beat validity mask; a beat is invalid when it deviates
    from its predecessor by more than ``jump_fraction``."""
    valid: list[bool] = []
    previous: float | None = None
    for rr in rr_values:
        if previous is None or previous <= 0:
            valid.append(True)
        else:
            valid.append(abs(rr - previous) / previous <= jump_fraction)
        previous = rr
    return valid


# ---------------------------------------------------------------------------
# Core DFA computation
# ---------------------------------------------------------------------------

def _linear_fit_rms(segment: list[float]) -> float:
    """Mean squared residual of a least-squares line through ``segment``."""
    n = len(segment)
    xs = range(n)
    x_mean = (n - 1) / 2.0
    y_mean = sum(segment) / n
    sxx = sum((x - x_mean) ** 2 for x in xs)
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, segment))
    slope = sxy / sxx if sxx else 0.0
    intercept = y_mean - slope * x_mean
    return sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, segment)) / n


def dfa_alpha1(rr_values: list[float], scales: tuple[int, ...] = SHORT_TERM_SCALES) -> float | None:
    """Compute the short-term scaling exponent alpha 1 for a beat series.

    Returns None when the series is too short for the largest box size.
    """
    n_beats = len(rr_values)
    if n_beats < 2 * max(scales):
        return None
    mean = sum(rr_values) / n_beats
    profile: list[float] = []
    running = 0.0
    for rr in rr_values:
        running += rr - mean
        profile.append(running)

    log_n: list[float] = []
    log_f: list[float] = []
    for box in scales:
        boxes = n_beats // box
        if boxes < 2:
            continue
        residuals = [
            _linear_fit_rms(profile[i * box:(i + 1) * box])
            for i in range(boxes)
        ]
        fluctuation = math.sqrt(sum(residuals) / boxes)
        if fluctuation <= 0:
            continue
        log_n.append(math.log(box))
        log_f.append(math.log(fluctuation))

    if len(log_n) < 3:
        return None
    x_mean = sum(log_n) / len(log_n)
    y_mean = sum(log_f) / len(log_f)
    sxx = sum((x - x_mean) ** 2 for x in log_n)
    if sxx == 0:
        return None
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(log_n, log_f))
    return sxy / sxx


# ---------------------------------------------------------------------------
# Windowed time series
# ---------------------------------------------------------------------------

def _window_mean(series: list | None, time_data: list[float], start: float, end: float) -> float | None:
    """Mean of ``series`` over samples with ``start <= time < end``, ignoring None."""
    if not series:
        return None
    lo = bisect_left(time_data, start)
    hi = bisect_left(time_data, end)
    values = [
        float(series[i])
        for i in range(lo, min(hi, len(series)))
        if series[i] is not None
    ]
    return sum(values) / len(values) if values else None


def compute_dfa_a1_windows(
    beats: list[Beat],
    valid: list[bool],
    time_data: list[float],
    watts: list | None = None,
    heartrate: list | None = None,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    step_seconds: int = DEFAULT_STEP_SECONDS,
) -> list[dict]:
    """Slide a window over the beats and compute alpha 1 per window.

    Each entry contains ``start_s``, ``alpha1`` (None when not computable),
    ``artifact_pct``, ``beats``, ``avg_power`` and ``avg_hr``.
    """
    if not beats or not time_data:
        return []
    beat_times = [b[0] for b in beats]
    last_second = float(time_data[-1])
    windows: list[dict] = []
    start = 0.0
    while start + window_seconds <= last_second:
        end = start + window_seconds
        lo = bisect_left(beat_times, start)
        hi = bisect_left(beat_times, end)
        n_all = hi - lo
        if n_all >= MIN_BEATS_PER_WINDOW:
            recorded_seconds = sorted({int(beats[i][0]) for i in range(lo, hi)})
            coverage_pct = len(recorded_seconds) / window_seconds * 100.0
            gaps = [
                recorded_seconds[0] - int(start),
                int(end) - 1 - recorded_seconds[-1],
                *(later - earlier - 1 for earlier, later in zip(recorded_seconds, recorded_seconds[1:])),
            ]
            max_gap_seconds = max(gaps)
            invalid = sum(1 for i in range(lo, hi) if not valid[i])
            clean = [beats[i][1] for i in range(lo, hi) if valid[i]]
            windows.append({
                "start_s": start,
                "alpha1": (
                    dfa_alpha1(clean)
                    if coverage_pct >= MIN_WINDOW_COVERAGE_PCT
                    and max_gap_seconds <= MAX_WINDOW_GAP_SECONDS
                    else None
                ),
                "artifact_pct": invalid / n_all * 100.0,
                "beats": n_all,
                "coverage_pct": coverage_pct,
                "max_gap_seconds": max_gap_seconds,
                "avg_power": _window_mean(watts, time_data, start, end),
                "avg_hr": _window_mean(heartrate, time_data, start, end),
            })
        start += step_seconds
    return windows


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _round(value: float | None, digits: int) -> float | int | None:
    if value is None:
        return None
    return round(value) if digits == 0 else round(value, digits)


def _threshold_estimate(windows: list[dict]) -> tuple[float | None, float | None, int]:
    """Average power/HR of windows whose alpha 1 sits in the threshold band."""
    low, high = THRESHOLD_BAND
    band = [w for w in windows if w["alpha1"] is not None and low <= w["alpha1"] <= high]
    if len(band) < MIN_THRESHOLD_WINDOWS:
        return None, None, len(band)
    power = _mean([w["avg_power"] for w in band if w["avg_power"] is not None])
    hr = _mean([w["avg_hr"] for w in band if w["avg_hr"] is not None])
    return power, hr, len(band)


def summarize_dfa_a1(streams: dict[str, list]) -> dict | None:
    """Build the compact ``dfa_a1_summary`` for an activity.

    ``streams`` maps stream type to data list and must contain ``hrv`` and
    ``time``; ``watts`` and ``heartrate`` are optional. Returns None when the
    activity has no usable ``hrv`` stream at all. Returns ``{"valid": False, …}``
    when the data exists but fails the quality gate, so the coach can explain
    why no threshold estimate is available.
    """
    hrv = streams.get("hrv")
    time_data = streams.get("time")
    if not hrv or not time_data:
        return None
    time_values = [float(t) if t is not None else float(i) for i, t in enumerate(time_data)]

    beats = parse_rr_stream(hrv, time_values)
    if not beats:
        return None
    seconds_with_beats = sum(1 for entry in hrv if entry)
    coverage_pct = seconds_with_beats / len(hrv) * 100.0

    valid = flag_artifacts([b[1] for b in beats])
    artifact_pct = (len(valid) - sum(valid)) / len(valid) * 100.0

    base = {
        "valid": False,
        "artifact_pct": round(artifact_pct, 1),
        "coverage_pct": round(coverage_pct, 1),
    }
    if coverage_pct < MIN_COVERAGE_PCT:
        return {**base, "reason": f"R-R coverage {coverage_pct:.0f}% below {MIN_COVERAGE_PCT:.0f}%"}
    if artifact_pct > MAX_ACTIVITY_ARTIFACT_PCT:
        return {**base, "reason": f"artifact rate {artifact_pct:.1f}% above {MAX_ACTIVITY_ARTIFACT_PCT:.0f}%"}

    windows = compute_dfa_a1_windows(
        beats, valid, time_values,
        watts=streams.get("watts"),
        heartrate=streams.get("heartrate"),
    )
    usable = [
        w for w in windows
        if w["alpha1"] is not None
        and w["artifact_pct"] <= MAX_WINDOW_ARTIFACT_PCT
        and w["start_s"] >= WARMUP_SECONDS
    ]
    if len(usable) < MIN_VALID_WINDOWS:
        return {
            **base,
            "windows_total": len(windows),
            "windows_valid": len(usable),
            "reason": f"only {len(usable)} valid windows after warm-up",
        }

    alphas = [w["alpha1"] for w in usable]
    power_at, hr_at, band_windows = _threshold_estimate(usable)

    return {
        "valid": True,
        "artifact_pct": base["artifact_pct"],
        "coverage_pct": base["coverage_pct"],
        "windows_total": len(windows),
        "windows_valid": len(usable),
        "avg": _round(_mean(alphas), 2),
        "time_above_0_75_pct": _round(
            sum(1 for a in alphas if a > DFA_A1_AEROBIC_THRESHOLD) / len(alphas) * 100.0, 0
        ),
        "time_below_0_5_pct": _round(
            sum(1 for a in alphas if a < DFA_A1_ANAEROBIC_THRESHOLD) / len(alphas) * 100.0, 0
        ),
        "power_at_0_75": _round(power_at, 0),
        "hr_at_0_75": _round(hr_at, 0),
        "threshold_windows": band_windows,
    }
