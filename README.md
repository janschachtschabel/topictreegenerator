# Topic Generator

Eine modulare Streamlit-Anwendung zur Generierung und Anreicherung von hierarchischen Themenbäumen mit Metadaten, Entitäten und Frage-Antwort-Paaren. Die App nutzt OpenAI-Sprachmodelle, um didaktisch wertvolle Inhalte für den Bildungsbereich zu erstellen.

## Features

- **Modulare Architektur**: Klar strukturierte Codebasis für bessere Wartbarkeit und Erweiterbarkeit
- **Themenbaum-Generierung**: Erstellt hierarchische Themenbäume mit zwei Methoden:
  - **Einmal-Generierung**: Schnelle Erstellung des gesamten Baums in einem Durchgang
  - **Iterative Generierung**: Schrittweise Erstellung mit detaillierteren Ergebnissen
- **Kompendien-Generierung**: Erzeugt ausführliche Lehrtexte für jeden Knoten im Themenbaum
- **Entitäten-Extraktion**: Automatische Identifikation und Verlinkung von Entitäten mit Wikipedia/Wikidata
- **Q&A-Generierung**: Erstellt kontextbezogene Frage-Antwort-Paare für jeden Themenbaumknoten
- **Fortgeschrittene LLM-Integration**: Unterstützung für moderne OpenAI-Modelle (gpt-4o, gpt-4o-mini, gpt-4.1, gpt-4.1-mini)
- **Intuitive Benutzeroberfläche**: Streamlit-basiertes UI mit Fortschrittsanzeigen, Vorschaufunktionen und Exportmöglichkeiten

## Inhaltsverzeichnis
- [Installation](#installation)
- [Projektstruktur](#projektstruktur)
- [Benutzung](#benutzung)
- [Module im Detail](#module-im-detail)
- [Datenstruktur](#datenstruktur)
- [Abhängigkeiten](#abhängigkeiten)
- [Anpassung und Erweiterung](#anpassung-und-erweiterung)

## Installation

1. **Repository klonen**:
```bash
git clone https://github.com/janschachtschabel/topictreegenerator
cd topictreegenerator
```

2. **Python-Umgebung einrichten** (Python 3.9+ empfohlen):
```bash
python -m venv venv
source venv/bin/activate  # Unter Windows: venv\Scripts\activate
```

3. **Abhängigkeiten installieren**:
```bash
pip install -r requirements.txt
```

4. **API-Key konfigurieren**:
   - Erstelle eine `.env`-Datei im Projektverzeichnis
   - Füge `OPENAI_API_KEY=dein_api_key` hinzu

5. **Anwendung starten**:
```bash
streamlit run app.py
```

## Projektstruktur

Die App verwendet eine modulare Architektur für bessere Wartbarkeit:

```
themenbaum-generator/
├── app.py                  # Hauptanwendung und UI
├── modules/                # Funktionsmodule
│   ├── models.py           # Pydantic-Datenmodelle
│   ├── utils.py            # Hilfsfunktionen und -klassen
│   ├── themenbaum_generator.py  # Themenbaum-Erzeugung
│   ├── kompendium_generator.py  # Kompendium-Erzeugung
│   └── qa_generator.py     # Q&A-Paar-Erzeugung
├── entityextractor/        # Entitäten-Extraktionsmodul
├── data/                   # Speicherort für generierte JSON-Dateien
└── requirements.txt        # Projektabhängigkeiten
```

## Benutzung

### 1. Themenbaum erstellen

1. Öffne die Anwendung im Browser (http://localhost:8501)
2. Gib ein Themenbaumthema ein (z.B. "Physik in Anlehnung an die Lehrpläne der Sekundarstufe 2")
3. Konfiguriere die Parameter:
   - Anzahl Hauptthemen, Fachthemen und Lehrplanthemen
   - Optionale Spezialthemen ("Allgemeines", "Methodik und Didaktik")
   - Fachbereich, Bildungsstufe und Bildungssektor
   - Generierungsmodus (Einmal vs. Iterativ)
4. Klicke auf "Themenbaum generieren"

### 2. Kompendium generieren

1. Wähle "Kompendium generieren" im Menü
2. Wähle einen erstellten Themenbaum aus
3. Definiere Optionen für die Kompendiumserstellung:
   - Knoten auswählen
   - Entitäten extrahieren (aktivieren/deaktivieren)
   - KI-Modell auswählen
4. Starte die Generierung und überwache den Fortschritt

### 3. Q&A-Paare erstellen

1. Wähle "Q&A generieren" im Menü
2. Wähle einen vorhandenen Themenbaum aus
3. Konfiguriere Optionen:
   - Anzahl der Fragen pro Knoten
   - Kompendium einbeziehen (falls verfügbar)
   - Entitäten berücksichtigen (falls extrahiert)
4. Starte die Generierung

### 4. Dateivorschau

- Nutze die "Dateivorschau"-Funktion, um erstellte Themenbäume zu inspizieren
- Wähle zwischen verschiedenen Ansichtsmodi:
  - Strukturierte Ansicht
  - JSON-Rohdaten
  - Entitäten-Details

## Module im Detail

### models.py
Enthält die Pydantic-Datenmodelle für die strukturierte Datenhaltung:
- `Properties`: Metadaten-Container für Sammlungen
- `Collection`: Repräsentiert einen Knoten im Themenbaum
- `TopicTree`: Hauptcontainer für den gesamten Themenbaum
- `QAPair` und `QACollection`: Strukturen für Frage-Antwort-Paare

### themenbaum_generator.py
Funktionen zur Erstellung von Themenbäumen:
- `generate_topic_tree`: Einmalige Generierung des gesamten Baums
- `generate_topic_tree_iterative`: Schrittweise Generierung mit Zwischenfeedback
- `create_properties`: Hilfsfunktion zur Eigenschaftenerstellung

### kompendium_generator.py
Funktionen zur Erstellung von kompendialen Texten:
- `generate_extended_text`: Erstellt ausführliche Texte zu jedem Knoten
- `extract_entities`: Identifiziert relevante Entitäten im Text
- `generate_compendium_text`: Erstellt strukturierte Kompendien

### qa_generator.py
Funktionen zur Erstellung von Frage-Antwort-Paaren:
- `generate_qa_pairs`: Erstellt kontextbezogene Fragen und Antworten
- `process_node_qa`: Verarbeitet QA-Generierung für einen Knoten und seine Unterknoten

### utils.py
Hilfsfunktionen für die gesamte Anwendung:
- JSON-Verarbeitung
- OpenAI-API-Konfiguration
- Datei-Management

## Datenstruktur

```json
{
  "metadata": {
    "title": "Hauptthema",
    "description": "Beschreibung",
    "target_audience": "Zielgruppe",
    "created_at": "Timestamp",
    "version": "1.0",
    "settings": {
      "struktur": {
        "hauptthemen": 3,
        "unterthemen_pro_hauptthema": 2,
        "lehrplanthemen_pro_unterthema": 2
      }
    }
  },
  "collection": [
    {
      "title": "Hauptthema 1",
      "properties": {
        "ccm:collectionshorttitle": ["Kurztitel"],
        "cm:description": ["Beschreibung"],
        "cclom:general_keyword": ["Schlagworte"]
      },
      "additional_data": {
        "compendium_text": "Ausführlicher Text",
        "entities": [
          {
            "entity-name": "Name",
            "entity-class": "Klasse",
            "wikipediaurl": "URL",
            "wikipedia_content": "Inhalt"
          }
        ],
        "qa_pairs": [
          {
            "question": "Frage",
            "answer": "Antwort"
          }
        ]
      },
      "subcollections": []
    }
  ]
}
```

## Abhängigkeiten

Hauptabhängigkeiten:
- **streamlit**: Für die Benutzeroberfläche
- **openai**: API-Client für OpenAI-Modelle (GPT-4o, GPT-4.1, etc.)
- **pydantic**: Datenvalidierung und -struktur
- **python-dotenv**: Umgebungsvariablen-Management
- **urllib3**: HTTP-Client für den Entityextractor
- **backoff**: Robust gegenüber API-Ratenlimits

Die vollständige Liste der Abhängigkeiten finden Sie in `requirements.txt`.

## Anpassung und Erweiterung

### Anpassung der Prompts

Die Anwendung verwendet verschiedene Prompt-Templates für die Generierung. Diese können in den jeweiligen Modulen angepasst werden:
- `themenbaum_generator.py`: Templates für Themenbaum-Generierung
- `kompendium_generator.py`: Templates für Kompendium-Erstellung
- `qa_generator.py`: Templates für Frage-Antwort-Paare

### Hinzufügen neuer LLM-Modelle

Neue OpenAI-Modelle können leicht hinzugefügt werden:
1. Erweitern Sie die Modellliste in der Seitenleiste von `app.py`
2. Die Modellauswahl wird automatisch auf alle Module angewendet

### Integration weiterer Wissensdatenbanken

Der Entityextractor kann um weitere Wissensdatenbanken erweitert werden:
1. Implementieren Sie einen neuen Connector im `entityextractor`-Modul
2. Registrieren Sie die neue Datenquelle in der Konfiguration

## Lizenz

Apache 2.0
