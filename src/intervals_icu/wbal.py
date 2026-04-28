"""W'bal computation – Skiba differential model.

Shared module used by both wbal_analysis.py and prepare_activities_for_coach.py.

Model reference:
    Skiba et al. (2012) – differential reconstitution model
    Depletion  (P >= CP): W'bal -= P - CP  (floor 0)
    Recovery   (P < CP):  W'bal += (W' - W'bal) * (1 - exp(-1/tau))
    where tau = W' / (CP - P_mean_below_cp)  [fallback: 546 s]
"""

import math


def _tau_w(w_prime: float, cp: float, power_below_cp: list[float]) -> float:
    """Estimate tau (reconstitution time constant) in seconds."""
    if not power_below_cp:
        return 546.0
    p_mean = sum(power_below_cp) / len(power_below_cp)
    denominator = cp - p_mean
    if denominator <= 0:
        return 546.0
    return w_prime / denominator


def compute_wbal(watts: list[float | None], w_prime: float, cp: float) -> list[float]:
    """Return W'bal in joules for every second of the activity.

    Missing / None power samples are treated as 0 W.
    """
    sub_cp = [p for p in watts if p is not None and p < cp and p > 0]
    tau = _tau_w(w_prime, cp, sub_cp)
    decay = math.exp(-1.0 / tau)

    wbal = w_prime
    result: list[float] = []
    for raw in watts:
        p = raw if raw is not None else 0.0
        if p >= cp:
            wbal -= p - cp
            wbal = max(0.0, wbal)
        else:
            wbal += (w_prime - wbal) * (1.0 - decay)
        result.append(round(wbal, 1))
    return result


def summarize_wbal(wbal: list[float], w_prime: float) -> dict:
    """Compute summary statistics for a W'bal time series.

    Returns a dict suitable for embedding in JSON output.
    Does NOT include cp_w – callers should add that if needed.
    """
    min_wbal = min(wbal)
    max_depletion = w_prime - min_wbal
    usage_pct = round(max_depletion / w_prime * 100, 1) if w_prime else None

    below_30 = sum(1 for v in wbal if v < 0.30 * w_prime)
    below_10 = sum(1 for v in wbal if v < 0.10 * w_prime)
    min_idx = wbal.index(min_wbal)

    # ---------------------------------------------------------------------------
    # Depletion event state machine
    #
    # Event starts when wbal_pct crosses below 40% (from >= 40%).
    # Recovery confirmed when wbal_pct rises back above 50%.
    # Each event tracks: (pre_drop_level, event_minimum, post_recovery_maximum).
    # ---------------------------------------------------------------------------
    _NORMAL, _DEPLETING, _RECOVERING = "normal", "depleting", "recovering"

    events: list[tuple[float, float, float | None]] = []
    state = _NORMAL
    last_above_40 = w_prime
    cur_pre_drop = 0.0
    cur_min = 0.0
    cur_rec_max = 0.0

    for v in wbal:
        pct = v / w_prime if w_prime else 1.0

        if state == _NORMAL:
            if pct >= 0.40:
                last_above_40 = v
            if pct < 0.40:
                cur_pre_drop = last_above_40
                cur_min = v
                state = _DEPLETING

        elif state == _DEPLETING:
            cur_min = min(cur_min, v)
            if pct > 0.50:
                cur_rec_max = v
                state = _RECOVERING

        elif state == _RECOVERING:
            cur_rec_max = max(cur_rec_max, v)
            if pct >= 0.40:
                last_above_40 = v
            if pct < 0.40:
                events.append((cur_pre_drop, cur_min, cur_rec_max))
                cur_pre_drop = last_above_40
                cur_min = v
                state = _DEPLETING

    if state == _DEPLETING:
        events.append((cur_pre_drop, cur_min, None))
    elif state == _RECOVERING:
        events.append((cur_pre_drop, cur_min, cur_rec_max))

    depletion_events = len(events)

    ratios: list[float] = []
    for pre_drop, ev_min, rec_max in events:
        depleted = pre_drop - ev_min
        if depleted <= 0 or rec_max is None:
            continue
        recovered = rec_max - ev_min
        ratios.append(min(recovered / depleted, 1.0))

    wbal_recovery_ratio = round(sum(ratios) / len(ratios), 3) if ratios else None

    return {
        "w_prime_j": w_prime,
        "wbal_min_j": round(min_wbal, 1),
        "wbal_max_depletion_j": round(max_depletion, 1),
        "wbal_usage_pct": usage_pct,
        "seconds_below_30pct": below_30,
        "seconds_below_10pct": below_10,
        "min_wbal_at_second": min_idx,
        "wbal_depletion_events": depletion_events,
        "wbal_recovery_ratio": wbal_recovery_ratio,
    }
