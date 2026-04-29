# Input Schema

This document defines the structure of the JSON input data provided to the AI coach.

The goal is to ensure consistent interpretation of training data across all analyses and planning decisions.

---

## Overview

The input JSON consists of the following top-level sections:

- week_starting
- current_date
- metrics
- week_summary
- activities
- fueling_analysis
- planned_workouts

---

## 1. Week and day Identifier

"week_starting": "YYYY-MM-DD"
- Start date of the current training week

"current_date": "YYYY-MM-DD"
- Date of the current day when the input was generated

---

## 2. Metrics (Current Athlete State)

"metrics": {
  "date": "YYYY-MM-DD",
  "ftp": number,
  "rolling_ftp": number,
  "eftp": number,
  "vo2max": number,
  "p5min": number,
  "w_prime": number,
  "weight": number,
  "age": number,
  "sex": "Male | Female",
  "ctl": number,
  "atl": number,
  "resting_hr": number,
  "hrv": number
}

Notes:

- FTP / eFTP define training intensity zones
- CTL = fitness, ATL = fatigue
- VO2max and p5min describe aerobic capacity
- HRV and resting HR indicate recovery state

---

## 3. Weekly Summary

"week_summary": {
  "total_training_load": number,
  "number_of_rides": number,
  "total_time_hours": number,
  "longest_ride_hours": number,

  "vo2_sessions": number,
  "threshold_sessions": number,
  "long_ride_sessions": number,
  "endurance_sessions": number,

  "avg_decoupling": number,
  "avg_decoupling_label": string,

  "form_absolute": number,
  "form_pct": number,
  "form_percent_display": number,
  "form_zone": "fresh | transition | optimal | high_fatigue",

  "fueling_form_analysis": {
    "fatigue_status": string,
    "fueling_status": string,
    "avg_carbs_per_hour": number,
    "avg_fueling_ratio": number,
    "underfueled_sessions": number,
    "number_of_long_rides": number,
    "durability_limited_by_fueling": boolean,
    "interpretation": string,
    "recommendation": string
  },

  "training_plan": [
    {
      "week": "YYYY-MM-DD",
      "plan_name": string,
      "phase": "Base | Build | Peak | Transition",
      "phase_start": "YYYY-MM-DD",
      "phase_end": "YYYY-MM-DD",
      "weekly_load_target": number,
      "week_type": "NORMAL | RECOVERY | RACE | NOTE",
      "training_availability": "NORMAL | LIMITED",
      "week_note": string   // optional, e.g. "Recovery Week"
    }
  ]
}

Notes:

- form = CTL - ATL
- form_pct used for fatigue assessment
- training_plan includes current and next week targets
- week_type is derived from a NOTE event in intervals.icu (e.g. "Recovery Week" → "RECOVERY", "Race Week" → "RACE"); defaults to "NORMAL"
- training_availability reflects the athlete's available training time as set on the weekly TARGET event in intervals.icu (NORMAL = full availability, LIMITED = reduced time e.g. travel or work)
- week_note contains the original note text from intervals.icu if present

---

## 4. Activities

"activities": [
  {
    "date": "YYYY-MM-DD",
    "name": string,
    "duration_hours": number,
    "training_load": number,

    "avg_power": number,
    "norm_power": number,
    "avg_hr": number,
    "max_hr": number,

    "polarization_index": number,
    "training_distribution": string,
    "training_distribution_reason": string,

    "z1_z2_pct": number,
    "z3_z4_pct": number,
    "z5_plus_pct": number,

    "interval_summary": [string],

    "decoupling": number,
    "decoupling_label": string,

    "rpe": number,

    "carbs_used_g": number,
    "carbs_ingested_g": number,

    "w_prime_j": number,
    "w_prime_bal_drop_j": number,
    "w_prime_bal_min_j": number,
    "w_prime_usage_pct": number,

    "tags": [string],

    "wbal_summary": {
      "w_prime_j": number,
      "wbal_min_j": number,
      "wbal_max_depletion_j": number,
      "wbal_usage_pct": number,
      "seconds_below_30pct": number,
      "seconds_below_10pct": number,
      "min_wbal_at_second": number,
      "wbal_depletion_events": number,
      "wbal_recovery_ratio": number | null
    } | null
  }
]

Notes:

- Tags have highest priority for classification
- avg_hr: average heart rate during the activity in bpm
- max_hr: maximum heart rate recorded during the activity in bpm
- w_prime_j: athlete's W' (anaerobic work capacity) in joules, as configured in intervals.icu
- w_prime_bal_drop_j: maximum W'bal depletion during the activity in joules (icu_max_wbal_depletion)
- w_prime_bal_min_j: minimum W'bal reached during the activity in joules (= w_prime_j − w_prime_bal_drop_j); indicates how close the athlete came to full W' exhaustion
- w_prime_usage_pct: percentage of W' depleted during the activity (= w_prime_bal_drop_j / w_prime_j × 100); used for pacing and W' distribution rules
- polarization_index describes intensity balance
- interval_summary provides detected efforts
- decoupling indicates aerobic durability
- fueling fields are critical for performance analysis
- wbal_summary is only present (non-null) for high-intensity activities that meet at least one of these criteria:
  - z5_plus_pct ≥ 8
  - any interval at ≥ 105 % FTP with duration ≥ 2 min
  - tagged as vo2* (e.g. vo2max-high)
  - tagged as event or type == Race
- wbal_summary fields:
  - wbal_min_j: lowest W'bal value reached in the activity (Skiba differential model, second-by-second)
  - wbal_max_depletion_j: total W' depleted at the worst moment (= w_prime_j − wbal_min_j)
  - wbal_usage_pct: depletion as percentage of W'
  - seconds_below_30pct / seconds_below_10pct: time spent in critically low W'bal territory
  - min_wbal_at_second: time index (seconds from start) of the W'bal minimum
  - wbal_depletion_events: number of discrete efforts where W'bal drops below 40 % and recovers above 50 %
  - wbal_recovery_ratio: average ratio of W' recovered vs. W' depleted per event (0–1); null if no complete events with recovery; 1.0 = full recovery between efforts

---

## 5. Fueling Analysis

"fueling_analysis": {
  "activities": [
    {
      "date": "YYYY-MM-DD",
      "name": string,
      "duration_hours": number,

      "ride_type": string,

      "carbs_per_hour": number,
      "fueling_ratio": number,

      "carbs_classification": "low | moderate | good",
      "ratio_classification": string,

      "is_long_ride": boolean,
      "flags": [string]
    }
  ],

  "weekly_summary": {
    "number_of_long_rides": number,
    "avg_carbs_per_hour": number,
    "avg_fueling_ratio": number,
    "number_of_underfueled_sessions": number
  },

  "recommendations": [string]
}

Notes:

- fueling_ratio = carbs ingested vs carbs used
- carbs_per_hour is key for fueling adequacy
- flags may indicate underfueling or issues

---

## 6. Planned Workouts

"planned_workouts": {
  "current_week": {
    "planned_workouts": [
      {
        "date": "YYYY-MM-DD",
        "time": "HH:MM",
        "name": string,
        "duration_hours": number,
        "planned_load": number,
        "description": string,

        "zone_distribution": {
          "z1_z2_pct": number,
          "z3_z4_pct": number,
          "z5_plus_pct": number
        },

        "steps": [
          {
            "duration_min": number,
            "power_pct_ftp": number
          }
        ]
      }
    ]
  },

  "next_week": {
    "planned_workouts": []
  }
}

Notes:

- Planned workouts define intended training structure
- Steps represent interval structure
- Must be considered before generating new workouts

---

## General Interpretation Rules

- Durations:
  - activities → hours
  - planned steps → minutes
  - output workouts → seconds

- Power:
  - always relative to FTP (%)

- Tags override automatic classification

- Planned workouts take precedence over new planning

---

## Purpose

This schema ensures:

- consistent parsing of training data
- reliable limiter detection
- correct integration of planned workouts
- accurate fueling and durability analysis
