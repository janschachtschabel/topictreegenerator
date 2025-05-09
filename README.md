# Topic Tree Generator

Eine modulare Streamlit-Anwendung zur Generierung hierarchischer Themenbäume, angereichert mit Metadaten, kompendialen Texten, Entitäten und Frage-Antwort-Paaren. Die App nutzt OpenAI-Modelle (z.B. GPT-4, GPT-4.1-Mini) und externe Wissensquellen (Wikipedia, optional Wikidata & DBpedia).

## Features

- **Modulare Architektur** für Wartbarkeit und Erweiterbarkeit
- **Themenbaum-Generierung**
  - Single-pass oder iterative Erstellung
- **Kompendiumserstellung**
  - **Extract-Modus**: Extended Text → Entitäten → Kompendium (direkt vom entityextractor)
  - **Generate-Modus**: Direkt Entitäten aus Prompt → Kompendium (direkt vom entityextractor)
  - Einstellbare Seitenzahl im UI (bestimmt die Textlänge des Kompendiums)
  - Live-Statusmeldungen (z.B. ‚Erzeuge Extended Text', ‚Extrahiere Entitäten')
  - Automatische Literaturverzeichnis-Generierung mit Referenzen
- **Entitäten-Extraktion**
  - Standard: Wikipedia
  - Optional: Wikidata, DBpedia (Checkboxen im UI)
- **Q&A-Generierung**
  - Kontextbezogene Frage-Antwort-Paare pro Knoten
- **Export**
  - JSON-Download mit Timestamp
- **UI**
  - Streamlit-Sidebar für Modellwahl, Entity-Quellen, Process-Modus, Seitenzahl
  - Fortschrittsbalken & Statustexte

## Installation

```bash
git clone https://github.com/janschachtschabel/topictreegenerator
cd topictreegenerator
python -m venv venv           # Python 3.9+
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

Erstelle eine `.env` im Projektroot mit:
```
OPENAI_API_KEY=dein_api_key
```

## Anwendung starten

```bash
streamlit run app.py
```

## Usage

### Einstellungen in der Sidebar

1. **OpenAI-Modell** (z.B. `gpt-4.1-mini`)
2. **Wissensquellen**
   - Wikipedia (immer aktiviert)
   - Wikidata (optional)
   - DBpedia (optional, DE/EN)
3. **Process-Modus**
   - *Extraktionsmodus*: Extended Text erstellen, Entitäten extrahieren und Kompendium direkt generieren
   - *Generierungsmodus*: Entitäten und Kompendium direkt aus Prompt generieren
4. **Seitenzahl** für das finale Kompendium
5. **Statusmeldungen** (ein-/ausschalten)

### Arbeitsablauf

1. **Themenbaum generieren** (Startseite)
2. **Kompendium erzeugen** (Kompendium-Seite)
3. **Q&A generieren** (Q&A-Seite)
4. **Export**: JSON-Download im jeweiligen Abschnitt

## Projektstruktur

```
topictreegenerator/
├── app.py                     # UI & Routing
├── modules/
│   ├── themenbaum_generator.py
│   ├── kompendium_generator.py
│   ├── qa_generator.py
│   └── utils.py               # Konfiguration, JSON-Handling
├── entityextractor/           # Externes Entity-Extraction-Modul
├── data/                      # Generierte JSON-Dateien
├── requirements.txt
└── README.md
```

## Abhängigkeiten

Siehe `requirements.txt`. Wichtige Pakete:

- streamlit, openai, pydantic, python-dotenv
- requests, urllib3, beautifulsoup4, SPARQLWrapper
- json5, regex
- matplotlib, networkx, pyvis, pandas, pillow
- tqdm, colorama

## Anpassung & Erweiterung

- **Prompts** anpassen in `modules/kompendium_generator.py` und `modules/qa_generator.py`
- **Neue Entity-Connector**: Implementiere im `entityextractor`-Modul und registriere in `utils.py`
- **Modelle erweitern**: Liste in `app.py` anpassen
- **Kompendium-Einstellungen**: Parameter in `modules/kompendium_generator.py` anpassen:
  - `ENABLE_COMPENDIUM`: Aktiviert die Kompendium-Generierung
  - `COMPENDIUM_LENGTH`: Zeichenanzahl für das Kompendium
  - `COMPENDIUM_EDUCATIONAL_MODE`: Bildungsmodus für das Kompendium

---

Apache 2.0
