# Next Level intervals.icu  
## Webinar Notes & Companion Guide

Diese Notizen ergänzen die Slides zum Webinar  
**„Next Level intervals.icu – Vom Datenchaos zur Coaching-Entscheidung“**.

Ziel:  
Dir den Einstieg erleichtern und den Workflow nachvollziehbar machen – auch ohne Live-Demo.

---

## Die Kernidee

intervals.icu liefert hervorragende Trainingsdaten.

Die entscheidende Frage bleibt jedoch:

> **Was sollst du morgen trainieren – und warum?**

Viele lösen das heute so:

- Screenshots erstellen  
- in ChatGPT hochladen  
- Trainingsvorschläge generieren  

Das funktioniert – ist aber:

- manuell  
- unstrukturiert  
- nicht reproduzierbar  

---

## Der Ansatz

Dieses Projekt baut daraus ein **strukturiertes Coaching-System**:

- Daten werden automatisch analysiert  
- Trainingsprinzipien (u. a. nach Joe Friel) werden angewendet  
- Entscheidungen basieren auf klaren Regeln  

Ergebnis:  
Keine generischen Vorschläge, sondern **konkrete Coaching-Entscheidungen**

---

## Der Workflow (Closed Loop)

1. **Daten abrufen**  
   `prepare_week_for_coach.py`  
   → erstellt strukturierte Wochendaten

2. **Analyse im GenAI Tool**  
   → JSON wird in ChatGPT / Claude geladen

3. **Trainingsplan generieren**  
   → basierend auf Coaching-Logik

4. **Plan zurückspielen**  
   `upload_plan.py`  
   → Upload nach intervals.icu

Ergebnis:  
Ein geschlossener Loop zwischen **Daten → Analyse → Planung**

---

## Was das System berücksichtigt

Das System trifft Entscheidungen basierend auf:

### Ermüdung
- CTL / ATL / Form  
- Belastungszustand des Athleten  

### Trainingsverlauf
- bereits absolvierte Schlüssel-Einheiten  
- Intensitätsverteilung  

### Limiter
- VO2max  
- Threshold (FTP)  
- Aerobic Durability  
- Fueling  

### Fueling (kritisch!)
- Kohlenhydrate pro Stunde  
- Verhältnis Aufnahme vs. Verbrauch  

Beispiel-Regel:

- hohe Ermüdung + schlechte Versorgung  
→ **erst Ernährung verbessern, nicht Intensität erhöhen**

---

## Beispiel (typischer Use Case)

Analyse einer intensiven Gruppenausfahrt:

- 171 TSS in 3h  
- hohe W'-Nutzung (~84%)  
- Decoupling > 10%  
- gute, aber nicht optimale Carb-Zufuhr  

Interpretation:

- VO2max-Reiz bereits erfüllt  
- Ermüdung steigt deutlich  
- keine weitere VO2max-Session nötig  

Entscheidung:

- Ruhetag beibehalten  
- Grundlage moderat fahren  
- Threshold nur bei guter Erholung  

---

## Wichtiger Punkt: Fueling

Viele Leistungsprobleme sind **keine Fitnessprobleme**, sondern:

Fueling-Probleme

Typisches Muster:

- hohe Decoupling-Werte  
- gleichzeitig niedrige Carb-Aufnahme  

→ falsch interpretiert als „fehlende Ausdauer“

Das System prüft deshalb immer:

- Carbs pro Stunde  
- Fueling Ratio  
- Zusammenhang mit Leistungseinbruch  

---

## Die Logik dahinter

Das System basiert auf:

- Trainingsprinzipien nach Joe Friel  
- klaren Entscheidungsregeln  
- strukturierter Datenauswertung  

Wichtige Prinzipien:

- Spezifität  
- Progressive Overload  
- Konsistenz  
- Individualisierung  

Ziel:

> Trainingsentscheidungen treffen wie ein Coach –  
> aber reproduzierbar und datenbasiert.

---

## Voraussetzungen

Damit das System sinnvoll funktioniert:

### Pflicht

- Leistungsdaten (Powermeter)  
- saubere Datenquelle (nicht nur Strava)  
- RPE nach jeder Einheit  
- dokumentierte Kohlenhydrate  

### Ideal

- HRV / Wellness-Daten  
- gepflegtes Gewicht  
- Trainingsplan (intervals.icu Target Generator)  

### Optional

- konsistente Tags  
  (z. B. `vo2max-high`, `lactate-treshold-moderate`)  

---

## GenAI Integration

Der „virtuelle Coach“ erhält:

- strukturierte JSON-Daten  
- System-Prompt  
- Coaching-Logik (Markdown-Dateien)

Wichtige Komponenten:

- `training_philosophy.md`  
- `coach_logic.md`  
- `decision_engine.md`  
- `fueling_rules.md`  
- `input_schema.md`  
- `workouts.md`  

Diese definieren:
- wie Daten interpretiert werden  
- wie Entscheidungen entstehen  
- wie Trainingspläne erzeugt werden  

---

## Ziel des Systems

Nicht:

- „ein weiterer AI-Coach“

Sondern:

> Ein System, das:
>
> - deine Daten versteht  
> - Entscheidungen transparent trifft  
> - anpassbar bleibt  

Keine Blackbox.

---

## Nächste Schritte

1. Repository klonen  
2. Setup durchführen (Python, API-Key etc.)  
3. erste Woche analysieren  
4. GenAI-Coach ausprobieren  
5. Trainingsplan zurückspielen  

---

## Feedback & Weiterentwicklung

Das Projekt ist Open Source und lebt von Feedback:

- Was funktioniert gut?  
- Wo sind die Empfehlungen unklar?  
- Welche Logik fehlt?  

Beiträge willkommen über GitHub Issues oder direkt per Nachricht.

---

## Links

- Repository:  
  https://github.com/rbrands/intervals-icu-sync  

- Blog & Updates:  
  https://robert-brands.com/training  

- intervals.icu Gruppe:  
  https://intervals.icu/g/training-club-cologne  

---

## Fazit

Du bekommst:

- kein Tool  
- sondern ein System  

mit klarer Logik, nachvollziehbaren Entscheidungen  
und voller Kontrolle über dein Training.