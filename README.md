# Themenbaum Generator

Ein interaktives Tool zur Generierung strukturierter Themenbäume für Bildungsinhalte. Der Generator nutzt KI, um aus einem gegebenen Thema automatisch hierarchische Themenstrukturen zu erstellen, die für Bildungszwecke optimiert sind.

## Features

- Generierung von Hauptthemen, Unterthemen und Lehrplanthemen
- Integration von Fachbereichen und Bildungsstufen
- Automatische Erstellung von Beschreibungen und Schlüsselwörtern
- Dynamische Fortschrittsanzeige während der Generierung
- Anpassbare Anzahl von Themen auf jeder Ebene
- Unterstützung verschiedener Bildungskontexte und Fachbereiche
- Standardisierte Benennungskonventionen für alle Themenebenen
- Qualitätsgeprüfte Beschreibungstexte nach didaktischen Richtlinien

## Formatierungsregeln

### Titel-Konventionen
- Verwendung von Langformen statt Abkürzungen
- Standardisierte Verbindung von Begriffen mit "und" oder "vs."
- Vermeidung von Sonderzeichen
- Substantiv-basierte Benennungen
- Kennzeichnung von Homonymen mit Klammern
- Keine Artikel, klein geschriebene Adjektive

### Kurztitel
- Maximal 20 Zeichen
- Prägnant und eindeutig
- Keine Sonderzeichen
- Bevorzugt ein Hauptbegriff

### Beschreibungen
- Klare Struktur: Definition → Relevanz → Merkmale → Anwendung
- Maximal 5 prägnante Sätze
- Zielgruppengerechte Sprache
- Aktive Formulierungen
- Fokus auf Bildungskontext

### Kategorisierung
Jede Sammlung wird einer der folgenden Kategorien zugeordnet:
- Thema (Substantiv, für Lehrplanthemen)
- Kompetenz (Verb, für Fähigkeiten und Fertigkeiten)
- Vermittlung (für Didaktik/Methodik)
- Redaktionelle Sammlung (für spezielle Themen)

## Installation

1. Klonen Sie das Repository:
```bash
git clone [repository-url]
cd themenbaumgenerator
```

2. Installieren Sie die erforderlichen Abhängigkeiten:
```bash
pip install -r requirements.txt
```

3. Erstellen Sie eine `.env` Datei im Projektverzeichnis und fügen Sie Ihren OpenAI API-Schlüssel hinzu:
```
OPENAI_API_KEY=Ihr-API-Schlüssel
```

## Verwendung

1. Starten Sie die Anwendung:
```bash
streamlit run app.py
```

2. Öffnen Sie einen Webbrowser und navigieren Sie zu der angezeigten URL (standardmäßig http://localhost:8501)

3. Konfigurieren Sie die Einstellungen:
   - Wählen Sie das gewünschte Sprachmodell
   - Geben Sie die Anzahl der gewünschten Themen pro Ebene an
   - Wählen Sie optional einen spezifischen Fachbereich und Bildungskontext

4. Geben Sie Ihr Hauptthema ein und klicken Sie auf "Themenbaum generieren"

## Konfiguration

### LLM Einstellungen
- Wahl zwischen verschiedenen OpenAI Modellen
- Anpassbare API-Schlüssel Einstellung
- Konfigurierbare Generierungsparameter

### Themenbaum Einstellungen
- Anzahl der Hauptthemen (1-20)
- Anzahl der Fachthemen pro Hauptthema (1-20)
- Anzahl der Lehrplanthemen pro Fachthema (1-20)

### Fachbereich und Bildungskontext
- Umfangreiche Auswahl an Fachbereichen
- Verschiedene Bildungskontexte (z.B. Primarstufe, Sekundarstufe, etc.)
- Anpassbare Bildungssektoren

## Technische Details

Der Generator verwendet:
- Streamlit für die Benutzeroberfläche
- OpenAI API für die KI-gestützte Generierung
- Pydantic für die Datenvalidierung
- Backoff für robuste API-Anfragen
- Python-dotenv für die Umgebungsvariablen-Verwaltung

## Lizenz

[Ihre Lizenz hier]

## Beitragen

Beiträge sind willkommen! Bitte lesen Sie die Contribution Guidelines, bevor Sie einen Pull Request erstellen.

## Support

Bei Fragen oder Problemen erstellen Sie bitte ein Issue im GitHub Repository.
