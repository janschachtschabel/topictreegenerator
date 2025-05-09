"""
Centralized prompts for entity generation via OpenAI.
Includes system and user prompts for 'generate' mode, English and German.
"""

def get_system_prompt_generate_en(max_entities, topic):
    return f"""
Generate exactly {max_entities} implicit, logical entities relevant to the topic: {topic}.

Output format:
Each entity as a semicolon-separated line: name; type; wikipedia_url; citation.
One entity per line. No JSON or additional formatting.

Guidelines:
- Set 'citation' to "generated" for each entity.
- Use only English Wikipedia (en.wikipedia.org) with exact title and URL; skip entities without articles.
- Citations must be exact text spans, max 5 words, no ellipses or truncation.
- Wikipedia URLs must not include percent-encoded characters; special characters unencoded.
- Example types: Assessment, Activity, Competence, Credential, Curriculum, Date, Event, Feedback, Field, Funding, Goal, Group, Language, Location, Method, Objective, Organization, Partnership, Period, Person, Phenomenon, Policy, Prerequisite, Process, Project, Resource, Role, Subject, Support, System, Task, Term, Theory, Time, Tool, Value, Work
- Do not include any explanations or additional text.
"""

def get_user_prompt_generate_en(max_entities, topic):
    return (
        f"Provide exactly {max_entities} implicit entities as semicolon-separated lines: name; type; wikipedia_url; citation. "
        f"Ensure Wikipedia URLs are from en.wikipedia.org with exact title and URL. "
        "One entity per line. No JSON."
    )

def get_system_prompt_generate_de(max_entities, topic):
    return f"""
Generiere genau {max_entities} implizite, logische Entitäten zum Thema: {topic}.

Ausgabeformat:
Jede Entität als semikolon-getrennte Zeile: name; type; wikipedia_url; citation.
Eine Entität pro Zeile. Keine JSON oder zusätzliche Formatierung.

Richtlinien:
- Setze 'citation' auf "generated" für jede Entität.
- Verwende nur die deutsche Wikipedia (de.wikipedia.org) mit exaktem Titel und URL; überspringe Entitäten ohne Artikel.
- Zitate müssen exakte Textausschnitte sein, maximal 5 Wörter, keine Auslassungen.
- Wikipedia-URLs dürfen keine Prozent-Codierung enthalten; Sonderzeichen unkodiert.
- Beispiel-Typen: Bewertung, Aktivität, Kompetenz, Nachweis, Curriculum, Datum, Ereignis, Rückmeldung, Fachgebiet, Förderung, Ziel, Gruppe, Sprache, Ort, Methode, Lernziel, Organisation, Partnerschaft, Zeitraum, Person, Phänomen, Richtlinie, Voraussetzung, Prozess, Projekt, Ressource, Rolle, Thema, Unterstützung, System, Aufgabe, Begriff, Theorie, Zeit, Werkzeug, Wert, Werk
- Keine Erklärungen oder zusätzlichen Texte.
"""

def get_user_prompt_generate_de(max_entities, topic):
    return (
        f"Gib genau {max_entities} implizite Entitäten als semikolon-getrennte Zeilen zurück: name; type; wikipedia_url; citation. "
        f"Stelle sicher, dass die Wikipedia-URLs von de.wikipedia.org stammen und exakten Titel und URL verwenden. "
        "Eine Entität pro Zeile. Keine JSON."
    )
