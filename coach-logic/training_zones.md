# Training Zones

This document defines the athlete’s training zones and how they are used by the AI coach.

Zones are primarily based on **% of FTP (Functional Threshold Power)**.  
Heart rate and RPE are secondary indicators.

---

## Overview

| Zone | Name                  | FTP %       | RPE | Description |
|------|----------------------|-------------|-----|-------------|
| Z1   | Recovery             | < 55%       | 1   | Active recovery |
| Z2   | Aerobic Endurance    | 56–75%      | 2–3 | Base endurance |
| Z3   | Tempo                | 76–90%      | 4–5 | Moderate steady work |
| Z4   | Threshold            | 91–105%     | 7–8 | Sustained hard efforts |
| Z5   | VO2max               | 106–120%    | 9–10| Max aerobic power |
| Z6   | Anaerobic Capacity   | 121–150%    | 10  | Short high-intensity |
| Z7   | Sprint               | >150%       | 10  | Maximal efforts |

---

## Zone Details

### Z1 – Recovery

- **Intensity:** <55% FTP  
- **Heart Rate:** <70% LTHR  
- **Duration:** 30–90 min  

**Purpose:**
- promote recovery
- increase circulation
- reduce fatigue

**Feeling:**
- very easy
- full conversation possible

---

### Z2 – Aerobic Endurance

- **Intensity:** 56–75% FTP  
- **Heart Rate:** 70–85% LTHR  
- **Duration:** 60–300+ min  

**Purpose:**
- build aerobic base
- improve fat metabolism
- develop durability

**Upper Z2 (Aerobic Threshold / AeT):**
- transition to Z3
- approximate FATmax zone
- RPE: 3–4  

**Key Use Cases:**
- long rides
- endurance rides
- base training
- climbing pacing (long efforts)

---

### Z3 – Tempo

- **Intensity:** 76–90% FTP  
- **Heart Rate:** 85–95% LTHR  
- **Duration:** up to ~2 hours  

**Purpose:**
- muscular endurance
- fatigue resistance
- sub-threshold climbing ability

**Feeling:**
- controlled but demanding
- conversation becomes limited

**Key Use Cases:**
- long climbs below threshold
- steady endurance under load

---

### Z4 – Threshold

- **Intensity:** 91–105% FTP  
- **Heart Rate:** 95–100% LTHR  

#### Subdivision

- **Sweet Spot:** 88–94% FTP  
- **Threshold:** 95–100% FTP  
- **Over:** 100–105% FTP  

**Purpose:**
- increase FTP
- improve sustained power

**Feeling:**
- hard but steady
- speaking limited to short phrases

**Key Use Cases:**
- structured intervals (e.g. 2×12, 3×8)
- over/under sessions

---

### Z5 – VO2max

- **Intensity:** 106–120% FTP  
- **Alternative Target:** 90–95% of VO2max power  
- **Heart Rate:** >100% LTHR / 90–100% HRmax  
- **Duration:** up to ~8 minutes  

**Purpose:**
- increase maximal aerobic capacity
- support FTP development

**Feeling:**
- very hard
- no conversation possible

**Key Use Cases:**
- structured intervals (e.g. 4×4, 5×3)
- short climbing efforts

---

### Z6 – Anaerobic Capacity

- **Intensity:** 121–150% FTP  
- **Duration:** up to ~2 minutes  

**Purpose:**
- increase anaerobic power
- improve repeatability of hard efforts

---

### Z7 – Sprint

- **Intensity:** >150% FTP  
- **Duration:** <30 seconds  

**Purpose:**
- neuromuscular power
- sprint ability

---

## Operational Rules (CRITICAL)

These rules define how zones are used in training decisions.

---

### 1. Long Rides

- primarily Z2
- upper Z2 preferred for performance gains
- avoid early Z3 spikes to protect durability

---

### 2. Endurance Rides

- Z2 dominant
- occasional Z3 allowed depending on fatigue

---

### 3. Threshold Sessions

- 88–95% FTP (sweet spot / threshold)
- over/unders include brief Z5 spikes

---

### 4. VO2max Sessions

- target:
  - 106–120% FTP  
  OR
  - 90–95% VO2max power  

- interval duration:
  - 1–5 minutes depending on fatigue

---

### 5. Climbing Performance (KEY GOAL)

For long climbs (60–90 min):

- primary zone:
  → upper Z2 to low Z4

- pacing strategy:
  - start in upper Z2 / low Z3
  - stabilize near threshold
  - avoid early anaerobic spikes

---

### 6. Fatigue Adjustments

- high fatigue:
  → shift sessions down by one zone

- fresh state:
  → allow upper range of target zones

---

## Integration with Coaching System

This zone model is used by:

- workout generation (interval intensity)
- limiter detection (VO2max vs threshold vs durability)
- pacing recommendations
- fatigue-based adjustments

Zones must always be interpreted in context of:

- FTP
- fatigue (CTL/ATL/form)
- fueling status
- training phase