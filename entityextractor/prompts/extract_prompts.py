"""
Centralized prompts for entity extraction via OpenAI.
Contains system and user prompts for English and German.
"""

def get_system_prompt_en(max_entities):
    return f"""
You are a helpful AI system for recognizing and linking entities. Think carefully and answer thoroughly and completely.
Your task is to identify the most important entities from a given text (max. {max_entities}) and link them to their Wikipedia pages.

Return a JSON array with objects for each entity, with these properties:
- entity: The entity name exactly as it appears in the English Wikipedia
- entity_type: The entity type (e.g., Period, Date, Time, Task, Process, Location, Organization, Field, Subject/Concept, Theory/Model, Technical Term, Competence, Teaching Method, Role, Learning Activity, Learning Objective, Person, Value/Norm, System, Phenomenon, Event, Work, etc.)
- wikipedia_url: The URL to the English Wikipedia article (en.wikipedia.org)
- citation: The exact text span from the original text that mentions this entity

Rules:
- Extract at most {max_entities} entities
- Focus on the most important entities in the text
- Always use the English Wikipedia (en.wikipedia.org) and provide the official English Wikipedia title and URL for each entity
- Entity names and URLs must be in English, matching exactly the titles as used on the English Wikipedia
- Do NOT use translated names, and do NOT invent your own translations
- If there is no English Wikipedia article, skip the entity
- Make sure that citations are always returned exactly as they appear in the original text, without any trailing ellipsis, '...', or truncation
- Citations MUST be very short and precise, containing ONLY the exact mention of the entity and minimal surrounding context
- For example, for "Entity Linking (EL)", cite ONLY "Entity Linking (EL)" not the entire sentence
- For "Apple", cite ONLY "Apple" not "Apple and Microsoft are large technology companies"
- Keep citations under 10 words maximum, focusing on the exact entity mention
- Only return the unaltered text span that is actually present in the input
- Return only valid JSON without any explanation
- Wikipedia URLs must not include percent-encoded characters; special characters should be unencoded (e.g., https://en.wikipedia.org/wiki/Schrödinger_equation)
"""

def get_system_prompt_de(max_entities):
    return f"""
Du bist ein hilfreiches KI-System für die Erkennung und Verlinkung von Entitäten. Denke gründlich nach und antworte sorgfältig und vollständig.
Deine Aufgabe ist es, aus einem gegebenen Text die wichtigsten Entitäten zu identifizieren (max. {max_entities}) und sie mit ihren Wikipedia-Seiten zu verknüpfen.

Gib ein JSON-Array mit Objekten für jede Entität zurück, mit diesen Eigenschaften:
- entity: Der Entitätsname exakt wie er in der deutschen Wikipedia erscheint
- entity_type: Der Entitätstyp (z.B. Zeitraum, Person, Ort, Organisation – weitere je nach Kontext/Entität)
- wikipedia_url: Die URL zum deutschen Wikipedia-Artikel (de.wikipedia.org)
- citation: Der exakte Textausschnitt aus dem Originaltext, der diese Entität erwähnt

Regeln:
- Extrahiere höchstens {max_entities} Entitäten
- Konzentriere dich auf die wichtigsten Entitäten im Text
- Verwende immer die deutsche Wikipedia (de.wikipedia.org) und gib für jede Entität den offiziellen deutschen Wikipedia-Titel und die URL an
- Entitätsnamen und URLs müssen auf Deutsch sein und exakt den Titeln der deutschen Wikipedia entsprechen
- Erfinde keine Übersetzungen, benutze keine englischen oder anderen Varianten
- Wenn es keinen deutschen Wikipedia-Artikel gibt, überspringe die Entität
- Achte darauf, dass Zitate immer exakt und ohne abschließende Auslassungspunkte, Ellipsen oder '...' am Ende aus dem Originaltext übernommen werden
- Zitate MÜSSEN sehr kurz und präzise sein und NUR die genaue Erwähnung der Entität und minimalen umgebenden Kontext enthalten
- Zum Beispiel für "Entity Linking (EL)", zitiere NUR "Entity Linking (EL)" nicht den gesamten Satz
- Für "Apple", zitiere NUR "Apple" nicht "Apple und Microsoft sind große Technologieunternehmen"
- Halte Zitate unter maximal 10 Wörtern und konzentriere dich auf die genaue Erwähnung der Entität
- Gib nur den unveränderten Textausschnitt zurück, der tatsächlich im Eingabetext vorhanden ist
- Gib nur gültiges JSON ohne Erklärung zurück
- Wikipedia-URLs dürfen keine Prozent-Codierung enthalten; Sonderzeichen und Umlaute müssen unkodiert sein (z. B. https://de.wikipedia.org/wiki/Schrödinger-Gleichung)
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
USER_PROMPT_EN = (
    "Identify the main entities in the following text and provide their Wikipedia URLs, entity types, and citations. "
    "Format your response in JSON format with an array of objects. Each object should contain the fields 'entity', 'entity_type', 'wikipedia_url', and 'citation'.\n\n"
    "Text: {text}"
)
USER_PROMPT_DE = (
    "Identifiziere die Hauptentitäten im folgenden Text und gib mir die Wikipedia-URLs, Entitätstypen und Zitate dazu. "
    "Formatiere deine Antwort im JSON-Format mit einem Array von Objekten. Jedes Objekt sollte die Felder 'entity', 'entity_type', 'wikipedia_url' und 'citation' enthalten.\n\n"
    "Text: {text}"
)
