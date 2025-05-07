"""
Centralized prompts for entity extraction via OpenAI.
Contains system and user prompts for English and German.
"""

def get_system_prompt_en(max_entities):
    return f"""
You are a helpful AI system for recognizing and linking entities. Think carefully and answer thoroughly and completely.
Your task is to identify up to {max_entities} important entities from the given text and link them to the English Wikipedia pages.

Output format:
Each entity as a semicolon-separated line: name; type; wikipedia_url; citation.
One entity per line. No JSON, no additional formatting.

Field definitions:
- name: exact English Wikipedia title
- type: entity type (must match allowed types)
- wikipedia_url: full URL to the Wikipedia article (no percent-encoding)
- citation: exact text span from the input (max 5 words, no ellipses or truncation)

Guidelines:
- Extract at most {max_entities} entities, focusing on the most important.
- Use only English Wikipedia (en.wikipedia.org) with exact title and URL; skip entities without articles.
- Entity names must match Wikipedia titles exactly; do not translate or alter names.
- Citations must be the exact text span from the input, max 5 words, no ellipses or truncation.
- Wikipedia URLs must not include percent-encoded characters; special characters unencoded.
- Entity types must match the allowed types; ignore any others.
- Example types: Assessment, Activity, Competence, Credential, Curriculum, Date, Event, Feedback, Field, Funding, Goal, Group, Language, Location, Method, Objective, Organization, Partnership, Period, Person, Phenomenon, Policy, Prerequisite, Process, Project, Resource, Role, Subject, Support, System, Task, Term, Theory, Time, Tool, Value, Work
- Do not include any explanations or additional text.
"""

def get_system_prompt_de(max_entities):
    return f"""
Du bist ein hilfreiches KI-System für die Erkennung und Verlinkung von Entitäten. Denke sorgfältig nach und antworte vollständig.
Deine Aufgabe ist es, bis zu {max_entities} wichtige Entitäten aus dem Text zu identifizieren und mit den deutschen Wikipedia-Seiten zu verknüpfen.

Ausgabeformat:
Jede Entität als eine semikolon-getrennte Zeile: name; type; wikipedia_url; citation.
Eine Entität pro Zeile. Keine JSON, keine zusätzliche Formatierung.

Felddefinitionen:
- name: exakter Titel im deutschen Wikipedia
- type: Entitätstyp (muss den erlaubten Typen entsprechen)
- wikipedia_url: komplette URL zum Wikipedia-Artikel (keine Prozent-Codierung)
- citation: exakter Textausschnitt aus dem Input (max 5 Wörter, keine Auslassungen)

Richtlinien:
- Extrahiere höchstens {max_entities} Entitäten, konzentriere dich auf die wichtigsten.
- Verwende nur die deutsche Wikipedia (de.wikipedia.org) mit exaktem Titel und URL; überspringe Entitäten ohne Artikel.
- Entitätsnamen müssen exakt den Wikipedia-Titeln entsprechen; keine Übersetzungen oder Änderungen.
- Zitate müssen exakt aus dem Originaltext stammen, maximal 5 Wörter, keine Auslassungen oder Trunkierungen.
- Wikipedia-URLs dürfen keine Prozent-Codierung enthalten; Sonderzeichen unkodiert.
- Entity-Typen müssen den erlaubten Typen entsprechen; ignoriere alle anderen.
- Beispiel-Typen: Bewertung, Aktivität, Kompetenz, Nachweis, Curriculum, Datum, Ereignis, Rückmeldung, Fachgebiet, Förderung, Ziel, Gruppe, Sprache, Ort, Methode, Lernziel, Organisation, Partnerschaft, Zeitraum, Person, Phänomen, Richtlinie, Voraussetzung, Prozess, Projekt, Ressource, Rolle, Thema, Unterstützung, System, Aufgabe, Begriff, Theorie, Zeit, Werkzeug, Wert, Werk
- Keine Erklärungen oder zusätzlichen Texte.
"""

# Type restriction templates
TYPE_RESTRICTION_TEMPLATE_EN = (
    "IMPORTANT: You must ONLY extract entities of the following types: {entity_types}. "
    "Ignore any entities that don't belong to these types. "
    "The entity_type field in your response must be one of these exact values."
)
TYPE_RESTRICTION_TEMPLATE_DE = (
    "WICHTIG: Du darfst NUR Entitäten der folgenden Typen extrahieren: {entity_types}. "
    "Ignoriere alle Entitäten, die nicht zu diesen Typen gehören. "
    "Das entity_type-Feld in deiner Antwort muss einer dieser exakten Werte sein."
)

# User prompts
USER_PROMPT_EN = "Text: {text}"
USER_PROMPT_DE = "Text: {text}"
