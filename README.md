# Topic Generator

Eine Streamlit-Anwendung zur Generierung und Anreicherung von hierarchischen Themenbäumen mit Metadaten, Entitäten und Q&A-Paaren.

## Inhaltsverzeichnis
- [Features](#features)
- [Installation](#installation)
- [Benutzung](#benutzung)
- [Prozesse im Detail](#prozesse-im-detail)
- [Datenstruktur](#datenstruktur)
- [Prompts und Templates](#prompts-und-templates)
- [API-Nutzung](#api-nutzung)

## Features

- **Themenbaum-Generierung**: Erstellt hierarchische Themenbäume basierend auf einem Hauptthema
- **Metadaten-Anreicherung**: Fügt Beschreibungen, Schlagworte und Bildungskontexte hinzu
- **Entitäten-Verlinkung**: Identifiziert und verlinkt Entitäten mit Wikipedia/Wikidata
- **Q&A-Generierung**: Erstellt Frage-Antwort-Paare für jeden Knoten im Themenbaum
- **Compendium-Generierung**: Erzeugt ausführliche Lehrtexte für jeden Knoten
- **Fortschrittsanzeige**: Visualisiert den Generierungsprozess in Echtzeit

## Installation

1. Klone das Repository:
```bash
git clone [repository-url]
cd topicgenerator
```

2. Installiere die Abhängigkeiten:
```bash
pip install -r requirements.txt
```

3. Starte die Anwendung:
```bash
streamlit run app.py
```

## Benutzung

### 1. Themenbaum Generierung

1. Öffne die Anwendung im Browser
2. Wähle "Themenbaum generieren"
3. Gib die folgenden Parameter ein:
   - Hauptthema (z.B. "Physik Sekundarstufe II")
   - Bildungsstufe
   - Bildungssektor
   - Fachbereich
   - Strukturparameter (Anzahl der Haupt-/Unterthemen)
4. Klicke auf "Generieren"

### 2. Metadaten Anreicherung

1. Lade einen generierten Themenbaum
2. Wähle "Metadaten anreichern"
3. Die Anwendung fügt automatisch hinzu:
   - Beschreibungen für jeden Knoten
   - Schlagworte
   - Bildungskontexte
   - Kurztitel

### 3. Entitäten-Verlinkung

1. Wähle "Entitäten verlinken"
2. Die App:
   - Identifiziert wichtige Entitäten
   - Sucht passende Wikipedia-Artikel
   - Verlinkt mit Wikidata
   - Extrahiert relevante Inhalte

### 4. Q&A-Generierung

1. Wähle "Q&A generieren"
2. Konfiguriere:
   - Anzahl der Fragen pro Knoten
   - Einbeziehung von Compendium/Entitäten
3. Starte den Prozess

## Prozesse im Detail

### Themenbaum-Generierung

1. **Initiale Strukturierung**
   - Hauptthemen werden basierend auf dem Fachbereich erstellt
   - Unterthemen folgen didaktischen Prinzipien
   - Lehrplanthemen orientieren sich an Bildungsstandards

2. **Metadaten-Generierung**
   - Beschreibungen werden kontextuell generiert
   - Schlagworte basieren auf Fachinhalten
   - Bildungskontexte werden aus der Struktur abgeleitet

3. **Entitäten-Verarbeitung**
   - Named Entity Recognition für Fachbegriffe
   - Wikipedia-API für Artikelsuche
   - Wikidata-Integration für strukturierte Daten
   - Extraktion relevanter Textpassagen

4. **Q&A-Generierung**
   - Rekursive Verarbeitung aller Knoten
   - Berücksichtigung von Kontext und Metadaten
   - Integration von Compendium-Texten
   - Einbeziehung von Entitäts-Informationen

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

## Prompts und Templates

### Themenbaum-Generierung

#### Hauptprompt
```
Erstelle einen hierarchischen Themenbaum für {themenbaumthema} mit {hauptthemen} Hauptthemen.
Jedes Hauptthema soll {unterthemen_pro_hauptthema} Unterthemen haben.
Jedes Unterthema soll {lehrplanthemen_pro_unterthema} Lehrplanthemen enthalten.

Berücksichtige:
- Bildungsstufe: {bildungsstufe}
- Bildungssektor: {bildungssektor}
- Fachbereich: {fachbereich}

Strukturiere die Themen didaktisch sinnvoll und baue sie aufeinander auf.
Die Themen sollen dem aktuellen Stand der Wissenschaft und den Bildungsstandards entsprechen.
```

#### Metadaten-Prompt
```
Generiere Metadaten für das Thema "{title}".

Erstelle:
1. Eine kurze, prägnante Beschreibung (2-3 Sätze)
2. 3-5 relevante Schlagworte
3. Einen Kurztitel (max. 3 Wörter)

Berücksichtige dabei:
- Bildungskontext: {bildungskontext}
- Zielgruppe: {zielgruppe}
- Fachbereich: {fachbereich}

Die Beschreibung soll:
- Die wichtigsten Aspekte des Themas hervorheben
- Die Relevanz für die Zielgruppe aufzeigen
- Fachlich korrekt und verständlich sein
```

### Compendium-Generierung

#### Compendium-Prompt
```
Erstelle einen ausführlichen Lehrtext zum Thema "{title}".

Der Text soll:
1. Die wichtigsten Konzepte und Prinzipien erklären
2. Fachbegriffe einführen und erläutern
3. Zusammenhänge zu anderen Themen aufzeigen
4. Beispiele und Anwendungen enthalten

Berücksichtige:
- Bildungsstufe: {bildungsstufe}
- Vorwissen: {vorwissen}
- Lernziele: {lernziele}

Strukturiere den Text didaktisch sinnvoll und verwende eine klare, präzise Sprache.
```

### Entitäten-Verarbeitung

#### Entitäten-Prompt
```
Identifiziere die wichtigsten Fachbegriffe und Konzepte im Text:

{text}

Für jeden Begriff:
1. Bestimme die Entitätsklasse (z.B. Physikalisches Gesetz, Mathematisches Konzept)
2. Gib den Wikipedia-Artikel an
3. Extrahiere die relevanten Informationen aus dem Wikipedia-Artikel

Berücksichtige:
- Fachbereich: {fachbereich}
- Bildungsstufe: {bildungsstufe}
```

### Q&A-Generierung

#### Q&A-Prompt
```
Erstelle {num_questions} Frage-Antwort-Paare zum Thema "{title}".

Nutze folgende Informationen:
1. Compendium: {compendium_text}
2. Entitäten: {entities_info}
3. Metadaten: {metadata}

Die Fragen sollen:
- Verschiedene kognitive Niveaus abdecken (Wissen, Verstehen, Anwenden)
- Klar und eindeutig formuliert sein
- Dem Bildungsniveau entsprechen

Die Antworten sollen:
- Präzise und fachlich korrekt sein
- Die wichtigsten Aspekte abdecken
- Verständlich formuliert sein
```

### Verwendung der Prompts

1. **Sequenzielle Verarbeitung**
   - Themenbaum → Metadaten → Compendium → Entitäten → Q&A
   - Jeder Schritt baut auf den vorherigen auf
   - Informationen werden kumulativ genutzt

2. **Kontextuelle Anreicherung**
   - Metadaten fließen in Compendium ein
   - Compendium wird für Entitäten genutzt
   - Alles zusammen für Q&A-Generierung

3. **Qualitätssicherung**
   - Prompts enthalten Qualitätskriterien
   - Bildungskontext wird durchgängig berücksichtigt
   - Fachliche Korrektheit wird priorisiert

4. **Anpassung der Prompts**
   - Templates können angepasst werden
   - Parameter sind konfigurierbar
   - Qualitätskriterien können erweitert werden

## API-Nutzung

### OpenAI API
- Verwendet für:
  - Themenbaum-Generierung
  - Metadaten-Erstellung
  - Q&A-Generierung
- Modell: GPT-4
- Authentifizierung über API-Key

### Wikipedia/Wikidata APIs
- Wikipedia-API für Artikelsuche
- Wikidata-API für strukturierte Daten
- Rate-Limiting beachten
- Caching implementiert

## Best Practices

1. **Themenbaum-Generierung**
   - Wähle präzise Hauptthemen
   - Beachte didaktische Progression
   - Limitiere die Hierarchietiefe

2. **Q&A-Generierung**
   - Nutze Compendium für Kontext
   - Beziehe Entitäten ein
   - Prüfe die Ausgabe

3. **Fehlerbehebung**
   - Überprüfe API-Keys
   - Beachte Rate-Limits
   - Nutze Logging-Informationen

## Lizenz

- Apache 2.0 Lizenz
