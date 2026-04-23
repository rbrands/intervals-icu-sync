# Decision Engine

This document defines how the AI coach makes training decisions based on input data.

It translates training data, fatigue state, and athlete goals into concrete weekly training actions.

---

## 1. Decision Hierarchy

All decisions follow this priority:

1. Athlete safety and recovery (fatigue, HRV)
2. Planned workouts (existing structure)
3. Weekly structure requirements
4. Primary performance limiter
5. Training phase (Base, Build, Peak)

---

## 2. Step-by-Step Decision Process

### Step 1: Evaluate Fatigue (Form)

form_absolute = CTL - ATL  
form_pct = (CTL - ATL) / CTL  

#### Interpretation

- form_pct > 0  
  → fresh → can increase load

- -10% to 0  
  → neutral → normal training

- -10% to -30%  
  → optimal training zone

- < -30%  
  → high fatigue → reduce intensity and/or volume

---

### Step 2: Check Recovery Indicators

- HRV low + fatigue high  
  → reduce intensity

- HRV normal + fatigue moderate  
  → proceed with plan

---

### Step 3: Analyze Completed Workouts

Determine:

- which key sessions are already done:
  - VO2max
  - threshold
  - long ride

- intensity distribution (polarization)

- signs of fatigue or failure:
  - high RPE
  - declining power
  - high decoupling

---

### Step 4: Evaluate Planned Workouts (CRITICAL)

- Identify:
  - scheduled key sessions
  - intended training load (TSS)

#### Rules

- planned workouts take precedence
- do NOT duplicate:
  - VO2max
  - threshold
  - long ride

- adjust only if:
  - fatigue too high
  - clear mismatch with athlete condition

---

### Step 5: Check Weekly Requirements

Ensure the week includes:

- exactly 1 VO2max session (if Age Rule applies)
- 1 threshold session
- 1 long aerobic ride

If missing:

- schedule remaining key sessions appropriately

---

### Step 6: Identify Primary Limiter

Use combined signals:

#### VO2max limiter

- low p5min / VO2max
- lack of high intensity work

→ increase VO2max focus

---

#### Threshold limiter

- declining power in sustained efforts
- inability to hold FTP

→ increase threshold work

---

#### Durability limiter

- high decoupling (>8–10%)
- performance drop in long rides

→ increase long rides and pacing control

---

#### Fueling limiter

- low carbs per hour
- low fueling ratio
- high decoupling with low intake

→ improve fueling strategy first

---

### Step 7: Combine Limiter + Fatigue

#### Fresh + clear limiter

→ increase training stimulus in limiter domain

---

#### Optimal fatigue + limiter

→ continue structured progression

---

#### High fatigue

→ reduce intensity  
→ prioritize recovery  
→ maintain frequency if possible

---

### Step 8: Training Phase Adjustment

#### Base

- prioritize volume
- limit high intensity

---

#### Build

- include VO2max and threshold
- moderate to high intensity

---

#### Peak

- reduce volume
- maintain intensity
- increase specificity

---

## 3. VO2max Decision Logic (CRITICAL)

### Mandatory Rule (Age ≥ 50)

- exactly 1 VO2max session per week

---

### Intensity Scaling (based on form_pct)

- form_pct < -20%  
  → vo2max-low  
  → short intervals (30/15, 6–8×1 min)

- -20% ≤ form_pct ≤ -10%  
  → vo2max-moderate  
  → 2–3 min intervals (5×2 min)

- form_pct > -10%  
  → vo2max-high  
  → 3–5 min intervals (4×4 min, 5×3 min)

---

### Special Case

- if VO2max already completed or planned:
  → do NOT add another session

---

## 4. Threshold Decision Logic

Use threshold sessions when:

- FTP is primary limiter
- build phase is active
- fatigue allows sustained efforts

Typical structure:

- 2×12 min
- 3×8 min
- over/under sessions

---

## 5. Long Ride Decision Logic

Schedule long rides when:

- durability is limiter
- weekly structure requires it

Guidelines:

- duration ≥ 2–4 hours
- steady aerobic pacing
- fueling must be correct

---

## 6. Endurance / Recovery Decisions

### Endurance Rides

Use when:

- filling weekly volume
- maintaining aerobic base

---

### Recovery Rides

Use when:

- fatigue high
- HRV low
- after key sessions

---

## 7. Fueling Integration

Fueling modifies decisions:

- low fueling detected:
  → prioritize nutrition before increasing load

- good fueling:
  → allows higher training stimulus

- long ride without fueling:
  → correct before interpreting performance

---

## 8. Weekly Planning Logic

### Early Week (Mon–Wed)

- focus on executing key sessions
- schedule VO2max / threshold

---

### Mid Week (Thu–Fri)

- adjust based on fatigue
- avoid overload

---

### Late Week (Sat–Sun)

- long ride or event
- prioritize quality and fueling

---

### End of Week

- begin planning next week:
  - based on fatigue
  - based on training phase

---

## 9. Load Management

- increase load only if:
  - fatigue is low or optimal
  - fueling is adequate

- reduce load if:
  - fatigue high
  - HRV low
  - performance declining

---

## 10. Key Principle

All decisions must balance:

- training stimulus
- recovery capacity

The goal is to maximize adaptation  
while avoiding excessive fatigue or under-recovery.
