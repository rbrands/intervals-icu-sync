# Prompt Library — intervals.icu GenAI Coach

Eine Sammlung von Copy-Paste-Prompts für den Einsatz mit ChatGPT, Claude & Co.  
A collection of copy-paste prompts for use with ChatGPT, Claude & Co.

---

## 1. Einzel-Workout-Analyse / Single Workout Analysis

### Deutsch

```
Analysiere die aktuellste Trainingseinheit und lese dazu von intervals.icu per perpare_week_data.

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

### Deutsch

```
Erstelle mir basierend auf der Wochen-Analyse einen Trainingsplan für die kommende Woche.

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

### English

```
Based on the weekly analysis, create a training plan for the coming week.

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

## 4. Fueling-Analyse / Fueling Analysis

### Deutsch

```
Analysiere meine Fueling-Strategie anhand der vorliegenden Trainingsdaten.

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
Analyze my fueling strategy based on the provided training data.

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

## Hinweise zur Verwendung / Usage Notes

### Deutsch

- **Mit MCP-Integration:** Die Prompts gehen davon aus, dass der MCP-Server eingerichtet ist und darüber die Daten gelesen werden können.
- **Ohne MCP:** JSON-Daten aus `prepare_week_for_coach.py` zuerst einfügen, dann den gewünschten Prompt darunter kopieren.
- **System-Prompt:** Für optimale Ergebnisse den vollständigen System-Prompt aus `prompts/system_prompt.md` mit dem passenden Disziplin-Block vorab setzen.

### English

- **With MCP integration:** The prompts assume that the MCP server is set up and data can be fetched through it.
- **Without MCP:** Paste JSON data from `prepare_week_for_coach.py` first, then copy the desired prompt below it.
- **System prompt:** For best results, set the full system prompt from `prompts/system_prompt.md` with the matching discipline block beforehand.
