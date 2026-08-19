# Prompt Library — intervals.icu GenAI Coach

Eine Sammlung von Copy-Paste-Prompts für den Einsatz mit ChatGPT, Claude & Co.  
A collection of copy-paste prompts for use with ChatGPT, Claude & Co.

---

## 1. Einzel-Workout-Analyse / Single Workout Analysis

### Deutsch

```
Analysiere die aktuellste Trainingseinheit und lese dazu von intervals.icu per prepare_week_data.

Beantworte folgende Fragen:
1. Welche Trainingsqualität hatte diese Einheit (VO2max-Reiz, Schwellenreiz, Grundlage)?
2. Wie war die Belastungssteuerung (Pacing, Herzfrequenz-Entkopplung, W'-Nutzung)?
3. Was sagt das Fueling aus – Carbs pro Stunde im Verhältnis zur Intensität?
4. Welchen Effekt hat diese Einheit auf CTL, ATL und Form?
5. Was leite ich für die nächsten 48–72 Stunden ab (Erholung, nächste Einheit)?

Halte die Antwort strukturiert und auf das Wesentliche konzentriert.
```

### English

```
Analyze the most recent training session and fetch the data from intervals.icu via prepare_week_data.

Answer the following questions:
1. What was the training quality (VO2max stimulus, threshold stimulus, base)?
2. How was load management (pacing, heart rate decoupling, W' usage)?
3. What does the fueling tell us — carbs per hour relative to intensity?
4. What is the effect of this session on CTL, ATL, and form?
5. What do I take away for the next 48–72 hours (recovery, next session)?

Keep the response structured and focused on the essentials.
```

---

## 2. Wochen-Analyse / Weekly Analysis

### Deutsch

```
Lies die aktuellen Daten aus intervals über prepare_week_data. Analysiere die aktuellen Metriken inkl. der Wellness-Daten sofern vorhanden und die Trainingswoche.

Bitte decke folgende Punkte ab:

**Metriken**
Bitte fasse zusammen und bewerte:
- aktuelle Leistungsdaten
- Wellnessdaten Schlaf, HRV, Ruhepuls, Gewicht
- Fahrertyp aus `metrics.power_profile` auf Basis der Felder `type`, `type_key`, `heuristic_score`, `type_scores`, `type_method` (heuristische Einordnung; bei knappen Scores Unsicherheit benennen)

Nutze fuer den Fahrertyp diese feste Ausgabevorlage:
`Powerprofil: <type> (<Sicherheitsgrad>, Aehnlichkeit <heuristic_score>). <Kurzinterpretation in 1-2 Saetzen auf Basis von p15s/p30s/p1min/p3min/p5min/p20min und curve_slope>.`

Regel fuer Sicherheitsgrad:
- `hoch` bei `heuristic_score >= 0.45`
- `moderat` bei `heuristic_score >= 0.30` und `< 0.45`
- `niedrig` bei `< 0.30`

**Belastungsbilanz**
- Gesamtbelastung (TSS, Stunden) im Vergleich zur Vorwoche
- Entwicklung von CTL, ATL und Form (TSB)
- Bewertung: War die Woche zu hoch, angemessen oder zu leicht dosiert?

**Trainingsqualität**
- Welche Schlüsseleinheiten wurden absolviert?
- Wie war die Intensitätsverteilung (Zone 1-2 vs. Zone 4-6)?
- Fehlt ein wichtiger Trainingsreiz?

**Fueling**
- Durchschnittliche Carb-Aufnahme pro Stunde
- Kritische Einheiten mit unzureichender Versorgung
- Zusammenhang zwischen Fueling und Leistungseinbrüchen

**Limiter**
- Was ist der primäre Leistungslimiter dieser Woche?
- Passt der Limiter zur aktuellen Saison-Phase (Aufbau, Peak, Wettkampf)?
- Empfehlung für die Schwerpunkte der kommenden Woche

Gib eine klare Zusammenfassung mit Handlungsempfehlungen.
```

### English

```
Fetch the current data from intervals via prepare_week_data. Analyze the current metrics including wellness data if available and the training week.

Please cover the following points:

**Metrics**
Summarize and assess:
- Current performance data
- Wellness data: sleep, HRV, resting heart rate, weight
- Rider type from `metrics.power_profile` based on `type`, `type_key`, `heuristic_score`, `type_scores`, and `type_method` (heuristic classification; explicitly mention uncertainty when scores are close)

Use this fixed rider-type output template:
`Power profile: <type> (<confidence_level>, similarity <heuristic_score>). <Short interpretation in 1-2 sentences based on p15s/p30s/p1min/p3min/p5min/p20min and curve_slope>.`

Confidence level rule:
- `high` when `heuristic_score >= 0.45`
- `moderate` when `heuristic_score >= 0.30` and `< 0.45`
- `low` when `< 0.30`

**Load Balance**
- Total load (TSS, hours) compared to the previous week
- Development of CTL, ATL, and form (TSB)
- Assessment: Was the week overdone, appropriate, or too light?

**Training Quality**
- Which key sessions were completed?
- How was intensity distribution (Zone 1-2 vs. Zone 4-6)?
- Is an important training stimulus missing?

**Fueling**
- Average carb intake per hour
- Critical sessions with insufficient fueling
- Relationship between fueling and performance drops

**Limiter**
- What is the primary performance limiter this week?
- Does the limiter match the current season phase (base, peak, race)?
- Recommendation for focus areas in the coming week

Provide a clear summary with actionable recommendations.
```

---

## 3. Trainingsplan-Generierung / Training Plan Generation

### 3a. Manuell (Verfügbarkeit selbst eingeben) / Manual (enter availability yourself)

#### Deutsch

```
Hole die aktuellen Daten von intervals.icu per prepare_week_data. Erstelle mir basierend auf der Wochen-Analyse einen Trainingsplan für die kommende Woche.

Rahmenbedingungen:
- Berücksichtige aktuelle Form (TSB) und Ermüdung (ATL)
- Passe die Belastung an den primären Limiter an
- Maximal [X] Stunden Gesamtumfang
- Verfügbare Tage: [Tage eintragen, z. B. Mo, Mi, Do, Sa, So]
- Geplante Events oder Rennen: [ggf. eintragen]

Planungslogik:
1. Schlüsseleinheiten zuerst platzieren (VO2max, Schwelle, Lange Ausfahrt)
2. TSS strikt nach den Regeln zur TSS-Berechnung aus dem System-Prompt bestimmen:
       bei neu erzeugten Workouts aus den Steps berechnen, bei ausgewählten
       Library-Workouts den Library-TSS und bei verankerten geplanten Workouts den
       dort angegebenen TSS verwenden. Den TSS je Einheit ausweisen.
3. Fueling-Strategie für intensive Einheiten berücksichtigen
4. Regenerationstage explizit einplanen
5. Keine Dopplung bereits absolvierter Schlüsselreize

Workout-Library (falls `list_library_workouts` verfügbar ist):
1. Zuerst alle Einheiten und ihre vollständigen kanonischen Tags festlegen.
2. `list_library_workouts` genau einmal mit allen unterschiedlichen Tags,
       `match_mode="any"`, `include_untagged=false` und `limit=100` aufrufen.
3. Nur Workouts mit exakt passendem Tag und passender Dosis verwenden. Dauer
       und TSS sind weiche Vergleichswerte; den jeweils ähnlichsten Kandidaten
       bevorzugen. Bei Auswahl die `library_workout_id` unverändert übernehmen und
       keine eigenen Steps erzeugen.
4. Gibt es kein passend getaggtes Workout, die Einheit normal mit Steps und ohne
       `library_workout_id` erzeugen. Die Suche nicht erweitern oder wiederholen.

Format: Tageweise mit Einheit, Dauer, Intensität (Zone), Ziel der Einheit, geschätztem TSS und Fueling-Empfehlung.

Abschließender Selbstcheck vor der Ausgabe:
1. Für jedes neu erzeugte Workout den TSS aus den finalen `steps` neu berechnen
       und prüfen, dass er mit dem Wert in `description` übereinstimmt.
2. Prüfen, dass die gesamte geplante Dauer den manuell vorgegebenen maximalen
       Gesamtumfang nicht überschreitet.
Falls eine Prüfung fehlschlägt, zuerst Steps oder Planzusammenstellung korrigieren und anschließend erneut prüfen.
```

#### English

```
Fetch the current data from intervals.icu via prepare_week_data. Based on the weekly analysis, create a training plan for the coming week.

Constraints:
- Consider current form (TSB) and fatigue (ATL)
- Adjust load to the primary limiter
- Maximum [X] hours total volume
- Available days: [enter days, e.g. Mon, Wed, Thu, Sat, Sun]
- Planned events or races: [enter if applicable]

Planning logic:
1. Place key sessions first (VO2max, threshold, long ride)
2. Calculate TSS strictly per the TSS Calculation rules from the system prompt:
       computed from steps for generated workouts, library TSS for selected library
       workouts, and the stated TSS for anchored planned workouts. Show estimated
       TSS per session.
3. Account for fueling strategy for intense sessions
4. Explicitly schedule recovery days
5. Do not duplicate already-completed key stimuli

Workout library lookup (when `list_library_workouts` is available):
1. Determine all planned sessions and their full canonical tags first.
2. Call `list_library_workouts` exactly once with all distinct tags,
       `match_mode="any"`, `include_untagged=false`, and `limit=100`.
3. Use a result only when its exact workout tag and dose fit the planned session.
       Treat duration and TSS as soft ranking criteria and prefer the closest
       candidate. Preserve its `library_workout_id` and do not recreate its steps.
4. If there is no matching tagged workout, generate the session normally with
       steps and without `library_workout_id`. Do not broaden or repeat the search.

Format: Day-by-day with session type, duration, intensity (zone), session goal, estimated TSS, and fueling recommendation.

Final self-check before returning output:
1. For every generated workout, recompute TSS from the final `steps` and
       verify it matches the value in `description`.
2. Verify the total planned duration does not exceed the manually specified
       maximum total volume.
If a check fails, correct steps or plan composition first, then re-verify.
```

---

### 3b. Automatisch (Verfügbarkeit und Ziele aus intervals.icu) / Automatic (availability and targets from intervals.icu)

#### Deutsch

```
Hole die aktuellen Daten von intervals.icu per prepare_week_data. Erstelle mir basierend auf der Wochen-Analyse einen Trainingsplan für die kommende Woche.

Entnimm die Planungsgrundlage direkt aus den intervals.icu-Daten. Die Wocheneinträge stehen in `week_summary.training_plan`; verwende den Eintrag, dessen `week` dem Start der Zielwoche entspricht:
- Trainingsphase und Wochentyp: aus `phase` und `week_type` (NORMAL / RECOVERY / RACE) dieses Eintrags. `week_note` berücksichtigen, falls vorhanden.
- Wochenziel: aus `weekly_load_target` (TSS) dieses Eintrags. Niemals ein Ziel erfinden oder auf das Ziel einer anderen Woche zurückfallen.
- Verfügbare Tage: aus `day_constraints` dieses Eintrags – Tage mit `training_allowed: false` entfallen, Tage mit `training_allowed: true` und Typ LIMITED nur für kurze, lockere Einheiten. Falls `max_training_time_hours` gesetzt ist, darf die geplante Dauer an diesem Tag diesen Wert nicht überschreiten.
- Bereits geplante Einheiten: aus den `planned_workouts` der Zielwoche – diese als Ankerpunkte übernehmen, nicht ersetzen
- Berücksichtige aktuelle Form (TSB) und Ermüdung (ATL)
- Verlauf der Trainingsbelastung: `training_load_history` verwenden, um einzelne
       von wiederholten Zielabweichungen zu unterscheiden. Nur als sekundären Kontext
       hinter der aktuellen Trainingsbereitschaft nutzen und versäumte historische
       Belastung niemals zur kommenden Woche addieren.

Planungslogik:
1. Schlüsseleinheiten passend zur Trainingsphase zuerst platzieren (VO2max, Schwelle, Lange Ausfahrt)
2. Gesamtumfang am Wochenziel ausrichten: nach dem TSS aus `weekly_load_target` planen und den geschätzten TSS je Einheit ausweisen. Für die Wochensumme den TSS strikt nach den Regeln zur TSS-Berechnung aus dem System-Prompt summieren: bei neu erzeugten Workouts aus den Steps berechnen, bei ausgewählten Library-Workouts den Library-TSS und bei verankerten `planned_workouts` den dort angegebenen TSS verwenden. Die geplante Wochensumme soll innerhalb von ±10 % des `weekly_load_target` liegen, sofern Einschränkungen oder Ermüdung keine begründete Abweichung erfordern. Das vorgegebene Ziel bleibt maßgeblich, außer wiederholte historische Abweichungen und die aktuelle Trainingsbereitschaft rechtfertigen gemeinsam eine sicherere Reduzierung.
3. Fueling-Strategie für intensive Einheiten berücksichtigen
4. Regenerationstage explizit einplanen
5. Keine Dopplung bereits absolvierter Schlüsselreize

Workout-Library (falls `list_library_workouts` verfügbar ist):
1. Zuerst alle Einheiten und ihre vollständigen kanonischen Tags festlegen.
2. `list_library_workouts` genau einmal mit allen unterschiedlichen Tags,
       `match_mode="any"`, `include_untagged=false` und `limit=100` aufrufen.
3. Nur Workouts mit exakt passendem Tag und passender Dosis verwenden. Dauer
       und TSS sind weiche Vergleichswerte; den jeweils ähnlichsten Kandidaten
       bevorzugen. Bei Auswahl die `library_workout_id` unverändert übernehmen und
       keine eigenen Steps erzeugen.
4. Gibt es kein passend getaggtes Workout, die Einheit normal mit Steps und ohne
       `library_workout_id` erzeugen. Die Suche nicht erweitern oder wiederholen.

Format: Tageweise mit Einheit, Dauer, Intensität (Zone), Ziel der Einheit, geschätztem TSS und Fueling-Empfehlung.

Abschließender Selbstcheck vor der Ausgabe:
1. Für jedes neu erzeugte Workout den TSS aus den finalen `steps` neu berechnen
       und prüfen, dass er mit dem Wert in `description` übereinstimmt.
2. Die wöchentliche TSS-Summe gegen `weekly_load_target` prüfen (±10 %).
Falls eine Prüfung fehlschlägt, zuerst Steps oder Planzusammenstellung korrigieren und anschließend erneut prüfen.
```

#### English

```
Fetch the current data from intervals.icu via prepare_week_data. Based on the weekly analysis, create a training plan for the coming week.

Derive the planning parameters directly from the intervals.icu data. The week entries live in `week_summary.training_plan`; use the entry whose `week` equals the target week start:
- Training phase and week type: from `phase` and `week_type` (NORMAL / RECOVERY / RACE) of that entry. Respect `week_note` when present.
- Weekly target: from `weekly_load_target` (TSS) of that entry. Never invent a target and never fall back to another week's target.
- Available days: from `day_constraints` of that entry — days with `training_allowed: false` are unavailable, days with `training_allowed: true` and type LIMITED only get short, easy sessions. If `max_training_time_hours` is present, planned duration on that day must not exceed this value.
- Already planned sessions: from `planned_workouts` for the target week — treat as anchors, do not replace
- Consider current form (TSB) and fatigue (ATL)
- Recent load pattern: use `training_load_history` to distinguish isolated from
       repeated target deviations. Treat it as secondary context behind current
       readiness and never add missed historical load to the coming week.

Planning logic:
1. Place key sessions matched to the training phase first (VO2max, threshold, long ride)
2. Align total volume to the weekly target: use TSS from `weekly_load_target`. Still show estimated TSS per session. For the weekly total, sum TSS strictly per the TSS Calculation rules from the system prompt: computed from steps for generated workouts, library TSS for selected library workouts, and the stated TSS for anchored `planned_workouts`. The planned weekly total should land within ±10% of `weekly_load_target` unless constraints or fatigue clearly justify a deviation. Keep the provided target authoritative unless repeated historical deviation and current readiness together justify a safer reduction.
3. Account for fueling strategy for intense sessions
4. Explicitly schedule recovery days
5. Do not duplicate already-completed key stimuli

Workout library lookup (when `list_library_workouts` is available):
1. Determine all planned sessions and their full canonical tags first.
2. Call `list_library_workouts` exactly once with all distinct tags,
       `match_mode="any"`, `include_untagged=false`, and `limit=100`.
3. Use a result only when its exact workout tag and dose fit the planned session.
       Treat duration and TSS as soft ranking criteria and prefer the closest
       candidate. Preserve its `library_workout_id` and do not recreate its steps.
4. If there is no matching tagged workout, generate the session normally with
       steps and without `library_workout_id`. Do not broaden or repeat the search.

Format: Day-by-day with session type, duration, intensity (zone), session goal, estimated TSS, and fueling recommendation.

Final self-check before returning output:
1. For every generated workout, recompute TSS from the final `steps` and
       verify it matches the value in `description`.
2. Verify the weekly TSS total against `weekly_load_target` (±10%).
If a check fails, correct steps or plan composition first, then re-verify.
```

---

## 4. Fueling-Analyse / Fueling Analysis

### Deutsch

```
Hole die aktuellen Daten von intervals.icu per prepare_week_data. Analysiere meine Fueling-Strategie anhand der vorliegenden Trainingsdaten.

Fokus der Analyse:

**Quantität**
- Carbs pro Stunde je Einheit
- Verhältnis Aufnahme zu Verbrauch (Fueling Ratio)
- Einheiten mit kritischer Unterversorgung (< 60g/h bei hoher Intensität)

**Muster**
- Gibt es Einheiten mit auffälligem Leistungsabfall nach 60–90 Minuten?
- Korreliert hohe Herzfrequenz-Entkopplung mit niedrigem Fueling?
- Welche Einheiten liefen trotz geringem Fueling gut – warum?

**Bewertung**
- Ist Fueling ein aktueller Leistungslimiter?
- Wo besteht das größte Verbesserungspotenzial?

**Empfehlung**
- Konkrete Zielvorgaben für Carbs/h nach Intensitätszone
- Praktische Umsetzungstipps für die häufigsten Einheitentypen

Halte die Analyse präzise und handlungsorientiert.
```

### English

```
Fetch the current data from intervals.icu via prepare_week_data. Analyze my fueling strategy based on the retrieved training data.

Analysis focus:

**Quantity**
- Carbs per hour per session
- Intake-to-expenditure ratio (fueling ratio)
- Sessions with critical under-fueling (< 60g/h at high intensity)

**Patterns**
- Are there sessions with a notable performance drop after 60–90 minutes?
- Does high heart rate decoupling correlate with low fueling?
- Which sessions went well despite low fueling — and why?

**Assessment**
- Is fueling a current performance limiter?
- Where is the greatest potential for improvement?

**Recommendation**
- Concrete carb/h targets by intensity zone
- Practical tips for the most common session types

Keep the analysis precise and action-oriented.
```

---

## 5. Metriken & Wellness / Metrics & Wellness Summary

### Deutsch

```
Lies die aktuellen Daten aus intervals über prepare_week_data und fasse die aktuellen Metriken und Wellnessdaten zusammen.

**Leistungsmetriken**
- FTP und eFTP (aktuell und Trend)
- VO2max (aktuell und Trend)
- W' (anaerobe Kapazität)
- CTL (Fitness), ATL (Ermüdung), Form (TSB) – absolut und in %
- Fahrertyp aus `metrics.power_profile` auf Basis der Felder `type`, `type_key`, `heuristic_score`, `type_scores`, `type_method` (heuristische Einordnung; bei knappen Scores Unsicherheit benennen)

Nutze fuer den Fahrertyp diese feste Ausgabevorlage:
`Powerprofil: <type> (<Sicherheitsgrad>, Aehnlichkeit <heuristic_score>). <Kurzinterpretation in 1-2 Saetzen auf Basis von p15s/p30s/p1min/p3min/p5min/p20min und curve_slope>.`

Regel fuer Sicherheitsgrad:
- `hoch` bei `heuristic_score >= 0.45`
- `moderat` bei `heuristic_score >= 0.30` und `< 0.45`
- `niedrig` bei `< 0.30`

Discipline fit:
Vergleiche das aktuelle Powerprofil (Rider Type und w_per_kg across
p15s/p30s/p1min/p3min/p5min/p20min) mit den Prioritäten der Disziplin des
Athleten, wie sie im System-Prompt definiert sind. In 1-2 Sätzen: nenne die
Disziplinanforderung, die das aktuelle Profil bereits gut abdeckt, und nenne
die größte Lücke zwischen dem aktuellen Profil und dem, was die Disziplin am
meisten braucht. Wiederhole nicht den Rider-Type-Absatz darüber; füge nur den
disziplin-spezifischen Vergleich hinzu.

**Wellness**
- HRV: aktueller Wert und Trend (letzte 7 Tage)
- Ruhepuls: aktueller Wert und Trend
- Schlaf: Qualität und Dauer (sofern vorhanden)
- Gewicht: aktuell und Trend

**Bewertung**
- Wie ist der aktuelle Formzustand (fresh / transition / optimal / high risk)?
- Gibt es Auffälligkeiten in den Wellness-Daten, die auf Überbelastung oder mangelnde Erholung hindeuten?
- Empfehlung: Kann die Belastung in der kommenden Woche gesteigert werden, oder ist Erholung prioritär?

Halte die Zusammenfassung kompakt und handlungsorientiert.
```

### English

```
Fetch the current data from intervals via prepare_week_data and summarize the current metrics and wellness data.

**Performance Metrics**
- FTP and eFTP (current value and trend)
- VO2max (current value and trend)
- W' (anaerobic capacity)
- CTL (fitness), ATL (fatigue), form (TSB) — absolute and as %
- Rider type from `metrics.power_profile` based on `type`, `type_key`, `heuristic_score`, `type_scores`, and `type_method` (heuristic classification; explicitly mention uncertainty when scores are close)

Use this fixed rider-type output template:
`Power profile: <type> (<confidence_level>, similarity <heuristic_score>). <Short interpretation in 1-2 sentences based on p15s/p30s/p1min/p3min/p5min/p20min and curve_slope>.`

Confidence level rule:
- `high` when `heuristic_score >= 0.45`
- `moderate` when `heuristic_score >= 0.30` and `< 0.45`
- `low` when `< 0.30`

Discipline fit:
Compare the current power profile (rider type and w_per_kg across
p15s/p30s/p1min/p3min/p5min/p20min) against the priorities of the athlete's
discipline, as defined in the system prompt above). In 1-2
sentences: name the discipline demand the current profile already covers
well, and name the single biggest gap between the current profile and what
the discipline needs most. Do not repeat the rider-type paragraph above; add
only the discipline-specific comparison.


**Wellness**
- HRV: current value and trend (last 7 days)
- Resting heart rate: current value and trend
- Sleep: quality and duration (if available)
- Weight: current value and trend

**Assessment**
- What is the current form state (fresh / transition / optimal / high risk)?
- Are there any anomalies in the wellness data indicating overload or insufficient recovery?
- Recommendation: Can training load be increased next week, or is recovery the priority?

Keep the summary compact and action-oriented.
```

---

## 6. Datenkonsistenz / Data Consistency Check

### Deutsch

```
Lies die aktuellen Daten aus intervals über prepare_week_data. Prüfe die Athletendaten auf Vollständigkeit und interne Konsistenz.
Dies ist ein Datenqualitäts-Check, kein Coaching-Interpretation; gib hier keine Trainingsempfehlungen, sondern nur an, was vorhanden, fehlt oder inkonsistent ist und warum das für spätere Bewertungen und Pläne relevant ist.
Wenn die aktuellen Daten aus prepare_week_data bereits im Chat vorhanden sind und noch relevant sind, verwende sie erneut und rufe prepare_week_data nicht noch einmal auf.

Bewerte jede unten genannte Stelle. Für jede Stelle gib einen Status (`OK`, `Warning` oder `Missing`) und eine ein Satz lange Erklärung an, welche praktische Auswirkung das hat, wenn er nicht `OK` ist. Nutze die genauen Schwellenwerte; erfinde keine eigenen.

**Season plan / macrocycle**
- `OK`, wenn `week_summary.training_plan` vorhanden ist und einen Eintrag für die aktuelle Woche enthält.
- `Missing`, wenn `week_summary.training_plan` fehlt oder leer ist.
- Wirkung bei `Missing`: Es stehen keine Phase, kein Wochen-Load-Ziel und keine Tagesbedingungen zur Verfügung; die Planerstellung fällt auf einen readiness-basierten Plan ohne Ziel zurück.

**FTP consistency**
- Vergleiche `ftp` mit `rolling_ftp` und `eftp`.
- `OK`, wenn beide sich von `ftp` um weniger als 10 % unterscheiden.
- `Warning`, wenn sich einer um 10-20 % unterscheidet.
- `Missing`/als inkonsistent markieren, wenn einer sich um mehr als 20 % unterscheidet.
- Prüfe zusätzlich `metrics.power_profile.p20min.watts`: Wenn diese beste 20-Minuten-Leistung über `period_days` auf ein Threshold hindeutet, das deutlich unter `ftp` liegt (mehr als 20 % niedriger nach einem 0,95-Faktor), nenne dies ausdrücklich, aber als Kontext (z. B. plausibel für Sprint-/Puncheur-Typen, die in diesem Fenster keinen ausdauernden Einsatz absolviert haben), nicht als Fehler.

**W' consistency**
- Vergleiche `w_prime` mit `rolling_w_prime`.
- `OK`, wenn sie sich um weniger als 10 % unterscheiden.
- `Warning`, wenn sie sich um 10-20 % unterscheiden.
- Als inkonsistent markieren, wenn sie sich um mehr als 20 % unterscheiden.

**Wellness tracking**
- Prüfe `resting_hr`, `hrv` und `sleep_secs`.
- `OK`, wenn mindestens einer dieser drei Werte nicht null ist.
- `Missing`, wenn alle drei null sind.
- Wirkung bei `Missing`: Form-/Readiness-Bewertungen können keine Erholungssignale nutzen und stützen sich nur auf Trainingslast-Metriken (CTL/ATL/TSB).

**Recent activity density**
- Zähle Einträge in `activities` innerhalb des `lookback_days`-Fensters.
- `OK`, wenn 3 oder mehr Aktivitäten vorhanden sind.
- `Warning`, wenn 1-2 Aktivitäten vorhanden sind.
- `Missing`, wenn 0 Aktivitäten vorhanden sind.
- Wirkung bei `Warning` oder `Missing`: Recent-Load- und Intensitätsverteilungs-Interpretationen basieren auf sehr wenig Daten und haben geringe Sicherheit.

**Load target history**
- Prüfe `weekly_load_target` über alle Einträge in `training_load_history`.
- `OK`, wenn mindestens ein Eintrag einen nicht-null `weekly_load_target` hat.
- `Missing`, wenn alle Einträge null sind.
- Wirkung bei `Missing`: Es gibt keinen historischen Trend von Ziel-vs.-Erreichung; das ist konsistent mit (und erwartet neben) einem fehlenden Saisonplan oben.

**Summary**
Beende mit einer Zeile: Gesamt-Datenvollständigkeit als `Good` (alle Bereiche `OK`), `Partial` (nur `Warning`/`Missing`-Bereiche, höchstens zwei) oder `Limited` (drei oder mehr `Warning`/`Missing`-Bereiche). Danach ein Satz, welche einzelne Maßnahme die Datenqualität am meisten verbessern würde (z. B. „ein Wellness-Tracker anschließen" oder „einen Saisonplan in intervals.icu einrichten").

Halte die Antwort kompakt: eine kurze Zeile pro Bereich, kein ganzer Absatz.
```

### English

```
Fetch the current data from intervals via prepare_week_data. Check the athlete data for completeness and internal consistency.
This is a data-quality check, not a coaching interpretation — do not give training recommendations here, only report what is present, missing, or inconsistent and why it matters for future assessments and plans.
If current-week data from prepare_week_data is already present in this chat and still relevant, reuse it and do not call prepare_week_data again.

Evaluate each area below. For each one, report a status (`OK`, `Warning`, or `Missing`) and a one-sentence explanation of the practical impact if it is not `OK`. Use the exact thresholds given; do not invent your own.

**Season plan / macrocycle**
- `OK` if `week_summary.training_plan` is present and contains an entry for the current week.
- `Missing` if `week_summary.training_plan` is absent or empty.
- Impact when `Missing`: no phase, weekly load target, or day constraints are available; plan generation falls back to a readiness-based plan without a target to work toward.

**FTP consistency**
- Compare `ftp` against `rolling_ftp` and `eftp`.
- `OK` if both differ from `ftp` by less than 10%.
- `Warning` if either differs by 10-20%.
- `Missing`/flag as inconsistent if either differs by more than 20%.
- Additionally check `metrics.power_profile.p20min.watts`: if this best 20-minute power over `period_days` implies a threshold far below `ftp` (more than 20% lower after applying a 0.95 factor), note this explicitly, but frame it as context (e.g. plausible for sprint/puncheur-type riders who did not perform a sustained effort in this window), not as an error.

**W' consistency**
- Compare `w_prime` against `rolling_w_prime`.
- `OK` if they differ by less than 10%.
- `Warning` if they differ by 10-20%.
- Flag as inconsistent if they differ by more than 20%.

**Wellness tracking**
- Check `resting_hr`, `hrv`, and `sleep_secs`.
- `OK` if at least one of these three is non-null.
- `Missing` if all three are null.
- Impact when `Missing`: form/readiness assessments cannot use recovery signals and rely on training load metrics (CTL/ATL/TSB) alone.

**Recent activity density**
- Count entries in `activities` within the `lookback_days` window.
- `OK` if 3 or more activities are present.
- `Warning` if 1-2 activities are present.
- `Missing` if 0 activities are present.
- Impact when `Warning` or `Missing`: recent-load and intensity-distribution interpretations are based on very little data and have low confidence.

**Load target history**
- Check `weekly_load_target` across all entries in `training_load_history`.
- `OK` if at least one entry has a non-null `weekly_load_target`.
- `Missing` if every entry is null.
- Impact when `Missing`: no historical target-vs-achievement trend is available; this is consistent with (and expected alongside) a missing season plan above.

**Summary**
End with one line: overall data completeness as `Good` (all areas `OK`), `Partial` (only `Warning`/`Missing` areas, no more than two), or `Limited` (three or more `Warning`/`Missing` areas). Follow this with one sentence on which single fix would improve the data quality most (e.g. "connecting a wellness tracker" or "setting up a season plan in intervals.icu").

Keep the response compact: one short line per area, not a full paragraph.
```

---

## Hinweise zur Verwendung / Usage Notes

## MCP Prompt-Aufruf je Client / MCP Prompt Invocation by Client

Die Prompts sind im MCP-Server nicht nur als Markdown-Dateien vorhanden, sondern auch als MCP-Prompts verdrahtet. Der direkte Aufruf hängt aber davon ab, ob der jeweilige Client MCP-Prompts nativ anzeigt. Wenn ein Client nur MCP-Tools, aber keine MCP-Prompts exponiert, müssen die Prompt-Texte weiterhin aus `prompts/library/` kopiert werden.

The prompts are not only stored as Markdown files, but also exposed by the MCP server as MCP prompts. Direct invocation still depends on whether the client actually surfaces MCP prompts. If a client exposes MCP tools but not MCP prompts, the prompt text still needs to be copied from `prompts/library/`.

### Verdrahtete MCP-Prompt-Namen / Wired MCP Prompt Names

| Zweck / Purpose | MCP prompt name |
| --- | --- |
| Einzel-Workout-Analyse / Single workout analysis | `coach_prompt_single_workout_analysis` |
| Wochen-Analyse / Weekly analysis | `coach_prompt_weekly_analysis` |
| Trainingsplan manuell / Training plan manual | `coach_prompt_training_plan_generation_manual` |
| Trainingsplan automatisch / Training plan automatic | `coach_prompt_training_plan_generation_automatic` |
| Fueling-Analyse / Fueling analysis | `coach_prompt_fueling_analysis` |
| Metriken & Wellness / Metrics & wellness | `coach_prompt_metrics_wellness_summary` |
| Datenkonsistenz / Data consistency | `coach_prompt_consistency` |
| Generischer Einstieg / Generic entry point | `coach_prompt` with `prompt_name` = `single_workout_analysis`, `weekly_analysis`, `training_plan_generation_manual`, `training_plan_generation_automatic`, `fueling_analysis`, `metrics_wellness_summary`, or `consistency` |

Alle Prompt-Endpunkte akzeptieren zusätzlich `response_language`, zum Beispiel `de` oder `en`.

All prompt endpoints also accept `response_language`, for example `de` or `en`.

### Claude

- In Claude können die verdrahteten MCP-Prompts direkt per Slash-Syntax aufgerufen werden, zum Beispiel `/coach_prompt_weekly_analysis` oder `/coach_prompt_fueling_analysis`, sofern der MCP-Server korrekt verbunden ist.
- Falls ein bestimmter Claude-Client oder Workspace die Prompt-Endpunkte nicht sichtbar macht, ist der pragmatische Fallback: zuerst `prepare_week_data` ausführen und danach den passenden Prompt aus dieser Datei oder aus `prompts/library/` in den Chat kopieren.
- Für flexiblere Aufrufe kann statt des spezifischen Prompt-Endpunkts auch `coach_prompt` mit `prompt_name` verwendet werden.

### ChatGPT

- Wenn die ChatGPT-MCP-Integration Prompt-Endpunkte sichtbar macht, gelten dieselben Prompt-Namen wie oben.
- Wenn ChatGPT nur Tools, aber keine Prompts anzeigt, zuerst `prepare_week_data` ausführen und anschließend den gewünschten Prompt-Text manuell einfügen.
- Für die automatische Wochenplanung ist in diesem Fall meist am klarsten: Tool-Daten holen, dann den Text von `03b_training_plan_generation_automatic.md` einfügen.

### Mistral

- Bei Mistral gilt dieselbe Logik: direkte Verwendung der MCP-Prompt-Namen, falls der Client Prompts unterstützt.
- Falls nur Tools sichtbar sind, Daten per `prepare_week_data` laden und den Prompt-Text aus `prompts/library/` manuell verwenden.
- Die verdrahteten Prompt-Namen bleiben serverseitig identisch; nur die Client-Oberfläche entscheidet, ob sie auswählbar sind.

### Microsoft 365 Copilot

- In Microsoft 365 Copilot scheinen die verdrahteten MCP-Prompts ebenfalls direkt per Slash-Syntax verwendbar zu sein, zum Beispiel `/coach_prompt_fueling_analysis`.
- Ob das verfügbar ist, hängt weiterhin von der konkreten Copilot-MCP-Integration und der Oberfläche ab; falls die Prompt-Endpunkte nicht erscheinen, bleibt der robuste Weg: `prepare_week_data` über den MCP-Server ausführen und danach den gewünschten Prompt-Text aus dieser Bibliothek einfügen.
- Die serverseitigen Namen bleiben identisch mit der Tabelle oben.

### Praktische Empfehlung / Practical Recommendation

- Für Claude und wahrscheinlich auch Microsoft 365 Copilot: die spezifischen Prompt-Namen direkt per Slash verwenden, zum Beispiel `/coach_prompt_weekly_analysis`.
- Für andere Clients mit sichtbaren MCP-Prompts: direkt die spezifischen Prompt-Namen verwenden.
- Für Clients ohne sichtbare MCP-Prompts: `prepare_week_data` als Tool aufrufen und danach den gewünschten Prompt aus `prompts/library/` einfügen.
- Wenn unklar ist, ob ein Client Prompts oder nur Tools unterstützt, zuerst prüfen, ob `coach_prompt_weekly_analysis` oder `coach_prompt` in der UI auswählbar ist.

### Deutsch

- **Mit MCP-Integration:** Die Prompts gehen davon aus, dass der MCP-Server eingerichtet ist und darüber die Daten gelesen werden können.
- **Ohne MCP:** JSON-Daten aus `scripts/prepare_week_for_coach.py` zuerst erzeugen und einfügen (z. B. `data/processed/coach_input_{monday}.json`), dann den gewünschten Prompt darunter kopieren.
- **System-Prompt:** Für optimale Ergebnisse den vollständigen System-Prompt aus `prompts/system_prompt.md` mit dem passenden Disziplin-Block vorab setzen.

### English

- **With MCP integration:** The prompts assume that the MCP server is set up and data can be fetched through it.
- **Without MCP:** First generate and paste JSON data via `scripts/prepare_week_for_coach.py` (e.g. `data/processed/coach_input_{monday}.json`), then copy the desired prompt below it.
- **System prompt:** For best results, set the full system prompt from `prompts/system_prompt.md` with the matching discipline block beforehand.
