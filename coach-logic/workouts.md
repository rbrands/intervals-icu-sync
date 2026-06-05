# Workouts

This file defines example workouts for key training domains based on Joe Friel principles.

Each workout type is structured into:
- High Dose → strong stimulus
- Moderate Dose → standard session
- Low Dose → reduced load / fatigue management

---
## Intensity Definition (CRITICAL)

All workouts MUST use the predefined training zones.

The system uses the training zones definition provided in the knowledge base.

### Rules

- Power targets MUST align with the defined FTP-based zones
- Do NOT use arbitrary %FTP values outside zone definitions
- All intervals must clearly map to a specific zone

---

### Zone Mapping for Workouts

#### VO2max Workouts
- Zone: Z5
- Intensity:
  → 106–120% FTP  
  OR  
  → 90–95% VO2max power

---

#### Threshold Workouts
- Zone: Z4

Sub-ranges:
- Sweet Spot: 88–94% FTP
- Threshold: 95–100% FTP
- Over intervals: 100–105% FTP

---

#### Endurance / Long Ride
- Zone: Z2 (primary)
- Upper Z2 preferred

---

#### Tempo Work
- Zone: Z3
- Occasionally low Z4 for progression

---

#### Recovery Rides
- Zone: Z1 only

---

#### Race-Specific / Breakaway Intervals
- Zone: Z6 (effort) + Z4 (consolidation)
- Z6 Intensity: >120% FTP (anaerobic / above VO2max)
- Z4 Intensity: 95–100% FTP (threshold consolidation)

---

## Consistency Rule (CRITICAL)

- All example workouts MUST follow these zone definitions
- Interval descriptions, %FTP, and tags must be consistent
- Do NOT mix conflicting intensity targets

## Tag Naming Hint (Library Filters)

- Workout tags are used by tooling for prefix-based filtering.
- Keep these prefixes stable and exact:
  - `vo2max-`
  - `lactate-threshold-`
  - `aerobic-threshold-`
  - `race-specific-`
- Keep dose suffixes consistent: `-high`, `-moderate`, `-low`.
- If tags are renamed, update filter configuration and docs together to avoid missing workouts.

## 1. Aerobic Capacity (VO2max)

**Goal:** Improve maximal aerobic power  
**Intensity:** ~105–120% FTP (VO2max zone)

### High Dose
- 5 × 2.5 min (2.5 min recovery)
- 5 × 3 min (3 min recovery)

**Tag:** vo2max-high

---

### Moderate Dose
- 6 × 1.5 min (1.5 min recovery)
- 5 × 2 min (2 min recovery)

**Tag:** vo2max-moderate

---

### Low Dose
- 10 × 30 sec (30 sec recovery)
- 7 × 1 min (1 min recovery)

**Tag:** vo2max-low

---

## 2. Lactate Threshold (FTP)

**Goal:** Increase sustainable power (FTP)  
**Intensity:** ~88–95% FTP  

### High Dose
- 3 × 12 min (3:15 min recovery)
- 2 × 20 min (5 min recovery)

**Tag:** lactate-threshold-high

---

### Moderate Dose
- 3 × 8 min (2.5 min recovery)
- 3 × 10 min (3 min recovery)

**Tag:** lactate-threshold-moderate

---

### Low Dose
- 3 × 5 min (90 sec recovery)
- 3 × 6 min (2 min recovery)

**Tag:** lactate-threshold-low

---

## 3. Aerobic Threshold (Endurance / Long Ride)

**Goal:** Improve aerobic endurance and durability  
**Intensity:** Z2 steady (aerobic threshold)

### High Dose
- 2–4 hours continuous riding

**Tag:** aerobic-threshold-high

---

### Moderate Dose
- 1–2 hours steady riding

**Tag:** aerobic-threshold-moderate

---

### Low Dose
- 30–60 minutes easy endurance

**Tag:** aerobic-threshold-low

---

## 4. Race-Specific: Breakaway Intervals

**Goal:** Simulate and train sprint, attack, and breakaway repeatability — specific to road races and criteriums  
**Structure:** Hard anaerobic effort (Z6) immediately followed by threshold consolidation (Z4)  
**Recovery:** Full recovery between sets (not partial)

### High Dose
- 4 × (2 min Z6 + 3 min Z4), 5 min full recovery between sets

**Tag:** race-specific-high

---

### Moderate Dose
- 3 × (2 min Z6 + 3 min Z4), 5 min full recovery between sets

**Tag:** race-specific-moderate

---

### Low Dose
- 2 × (2 min Z6 + 3 min Z4), 5 min full recovery between sets

**Tag:** race-specific-low

---

## Notes

- These workouts form the core weekly repertoire, but the actual weekly mix depends on:
  - athlete goal
  - limiter profile
  - training phase
  - age
  - fatigue
  - already planned workouts

- Typical weekly baseline when no stronger constraint exists:
  - 1× VO2max
  - 1× Threshold
  - 1× Long Ride

- Selection of **dose level** depends on:
  - fatigue (form)
  - training phase
  - weekly load target

- For athletes 50+:
  - VO2max must be included every week

- Fueling becomes critical for:
  - threshold sessions
  - long rides (>2h)

---