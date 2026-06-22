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
2. Fueling-Strategie für intensive Einheiten berücksichtigen
3. Regenerationstage explizit einplanen
4. Keine Dopplung bereits absolvierter Schlüsselreize

Format: Tageweise mit Einheit, Dauer, Intensität (Zone), Ziel der Einheit und Fueling-Empfehlung.
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
2. Account for fueling strategy for intense sessions
3. Explicitly schedule recovery days
4. Do not duplicate already-completed key stimuli

Format: Day-by-day with session type, duration, intensity (zone), session goal, and fueling recommendation.
```

---

### 3b. Automatisch (Verfügbarkeit und Ziele aus intervals.icu) / Automatic (availability and targets from intervals.icu)

#### Deutsch

```
Hole die aktuellen Daten von intervals.icu per prepare_week_data. Erstelle mir basierend auf der Wochen-Analyse einen Trainingsplan für die kommende Woche.

Entnimm die Planungsgrundlage direkt aus den intervals.icu-Daten:
- Trainingsphase und Wochentyp: aus `next_week_active_phases` und `next_week_load_targets.week_type` (NORMAL / RECOVERY / RACE)
- Wöchentliches Belastungsziel: aus `next_week_load_targets.load_target` (TSS)
- Verfügbare Tage: aus `next_week_day_constraints` – Tage mit `training_allowed: false` entfallen, Tage mit `training_allowed: true` und Typ LIMITED nur für kurze, lockere Einheiten
- Bereits geplante Einheiten: aus den `planned_workouts` der nächsten Woche – diese als Ankerpunkte übernehmen, nicht ersetzen
- Berücksichtige aktuelle Form (TSB) und Ermüdung (ATL)

Planungslogik:
1. Schlüsseleinheiten passend zur Trainingsphase zuerst platzieren (VO2max, Schwelle, Lange Ausfahrt)
2. Gesamtbelastung auf das TSS-Ziel ausrichten – je Einheit geschätzten TSS ausweisen
3. Fueling-Strategie für intensive Einheiten berücksichtigen
4. Regenerationstage explizit einplanen
5. Keine Dopplung bereits absolvierter Schlüsselreize

Format: Tageweise mit Einheit, Dauer, Intensität (Zone), Ziel der Einheit, geschätztem TSS und Fueling-Empfehlung.
```

#### English

```
Fetch the current data from intervals.icu via prepare_week_data. Based on the weekly analysis, create a training plan for the coming week.

Derive the planning parameters directly from the intervals.icu data:
- Training phase and week type: from `next_week_active_phases` and `next_week_load_targets.week_type` (NORMAL / RECOVERY / RACE)
- Weekly load target: from `next_week_load_targets.load_target` (TSS)
- Available days: from `next_week_day_constraints` — days with `training_allowed: false` are unavailable, days with `training_allowed: true` and type LIMITED only get short, easy sessions
- Already planned sessions: from `planned_workouts` for next week — treat as anchors, do not replace
- Consider current form (TSB) and fatigue (ATL)

Planning logic:
1. Place key sessions matched to the training phase first (VO2max, threshold, long ride)
2. Align total load to the TSS target — show estimated TSS per session
3. Account for fueling strategy for intense sessions
4. Explicitly schedule recovery days
5. Do not duplicate already-completed key stimuli

Format: Day-by-day with session type, duration, intensity (zone), session goal, estimated TSS, and fueling recommendation.
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
| Generischer Einstieg / Generic entry point | `coach_prompt` with `prompt_name` = `single_workout_analysis`, `weekly_analysis`, `training_plan_generation_manual`, `training_plan_generation_automatic`, `fueling_analysis`, or `metrics_wellness_summary` |

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
