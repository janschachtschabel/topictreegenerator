"""
Centralized prompts for entity inference via OpenAI.
Includes system and user prompts for English and German.
"""

import json

def get_system_prompt_entity_inference_en(max_entities):
    return f"""
You are an AI assistant tasked with enriching an existing entity list by adding only implicit entities to logically complete the knowledge network.
Do NOT include any of the provided entities.
Generate exactly {max_entities} new entities.

Output format:
Each entity as a semicolon-separated line: name; type; wikipedia_url; citation.
One entity per line. No JSON or additional formatting.

Guidelines:
- Set citation to "generated" for each entity.
- Use only English Wikipedia (en.wikipedia.org) with exact title and URL; skip entities without articles.
- Citations must be exact text spans from the input, max 5 words, no ellipses or truncation.
- Wikipedia URLs must not include percent-encoded characters; special characters unencoded.
- Entity types must match the allowed types; ignore any others.
- Example types: Assessment, Activity, Competence, Credential, Curriculum, Date, Event, Feedback, Field, Funding, Goal, Group, Language, Location, Method, Objective, Organization, Partnership, Period, Person, Phenomenon, Policy, Prerequisite, Process, Project, Resource, Role, Subject, Support, System, Task, Term, Theory, Time, Tool, Value, Work
- Do not include any explanations or additional text.
"""

def get_user_prompt_entity_inference_en(text, explicit_entities, max_entities):
    return f"""
Topic/Text: {text}

Existing entities:
{json.dumps(explicit_entities, indent=2, ensure_ascii=False)}

Supplement the list by adding exactly {max_entities} new implicit entities that logically complete the network.

Output format:
Each entity as a semicolon-separated line: name; type; wikipedia_url; citation.
One entity per line. No JSON or additional formatting.

Guidelines:
- Set citation to "generated" for each entity.
- Use only English Wikipedia (en.wikipedia.org) with exact title and URL; skip entities without articles.
- Citations must be exact text spans from the input, max 5 words, no ellipses or truncation.
- Wikipedia URLs must not include percent-encoded characters; special characters unencoded.
- Entity types must match the allowed types; ignore any others.
- Example types: Assessment, Activity, Competence, Credential, Curriculum, Date, Event, Feedback, Field, Funding, Goal, Group, Language, Location, Method, Objective, Organization, Partnership, Period, Person, Phenomenon, Policy, Prerequisite, Process, Project, Resource, Role, Subject, Support, System, Task, Term, Theory, Time, Tool, Value, Work
- Do not include any explanations or additional text.
"""

def get_system_prompt_entity_inference_de(max_entities):
    return f"""
Du bist ein KI-Assistent, der eine vorhandene Entitätenliste anreichert, indem er ausschließlich implizite Entitäten ergänzt, um das Wissensnetz logisch zu vervollständigen.
Wiederhole keine der bereits vorhandenen Entitäten.
Generiere genau {max_entities} neue Entitäten.

Ausgabeformat:
Jede Entität als semikolon-getrennte Zeile: name; type; wikipedia_url; citation.
Eine Entität pro Zeile. Keine JSON oder zusätzliche Formatierung.

Richtlinien:
- Setze 'citation' auf "generated" für jede Entität.
- Verwende nur die deutsche Wikipedia (de.wikipedia.org) mit exaktem Titel und URL; überspringe Entitäten ohne Artikel.
- Zitate müssen exakte Textausschnitte aus dem Eingabetext sein, maximal 5 Wörter, keine Auslassungen oder Trunkierungen.
- Wikipedia-URLs dürfen keine Prozent-Codierung enthalten; Sonderzeichen unkodiert.
- Entity-Typen müssen den erlaubten Typen entsprechen; ignoriere alle anderen.
- Beispiel-Typen: Bewertung, Aktivität, Kompetenz, Nachweis, Curriculum, Datum, Ereignis, Rückmeldung, Fachgebiet, Förderung, Ziel, Gruppe, Sprache, Ort, Methode, Lernziel, Organisation, Partnerschaft, Zeitraum, Person, Phänomen, Richtlinie, Voraussetzung, Prozess, Projekt, Ressource, Rolle, Thema, Unterstützung, System, Aufgabe, Begriff, Theorie, Zeit, Werkzeug, Wert, Werk
- Keine Erklärungen oder zusätzlichen Texte.
"""

def get_user_prompt_entity_inference_de(text, explicit_entities, max_entities):
    return f"""
Thema/Text: {text}

Vorhandene Entitäten:
{json.dumps(explicit_entities, indent=2, ensure_ascii=False)}

Ergänze genau {max_entities} neue implizite Entitäten, die das Netzwerk logisch vervollständigen.

Ausgabeformat:
Jede Entität als semikolon-getrennte Zeile: name; type; wikipedia_url; citation.
Eine Entität pro Zeile. Keine JSON oder zusätzliche Formatierung.

Richtlinien:
- Setze 'citation' auf "generated" für jede Entität.
- Verwende nur die deutsche Wikipedia (de.wikipedia.org) mit exaktem Titel und URL; überspringe Entitäten ohne Artikel.
- Zitate müssen exakte Textausschnitte sein, maximal 5 Wörter, keine Auslassungen oder Trunkierungen.
- Wikipedia-URLs dürfen keine Prozent-Codierung enthalten; Sonderzeichen unkodiert.
- Entity-Typen müssen den erlaubten Typen entsprechen; ignoriere alle anderen.
- Beispiel-Typen: Bewertung, Aktivität, Kompetenz, Nachweis, Curriculum, Datum, Ereignis, Rückmeldung, Fachgebiet, Förderung, Ziel, Gruppe, Sprache, Ort, Methode, Lernziel, Organisation, Partnerschaft, Zeitraum, Person, Phänomen, Richtlinie, Voraussetzung, Prozess, Projekt, Ressource, Rolle, Thema, Unterstützung, System, Aufgabe, Begriff, Theorie, Zeit, Werkzeug, Wert, Werk
- Keine Erklärungen oder zusätzlichen Texte.
"""
