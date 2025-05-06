"""
Centralized prompts for entity generation via OpenAI.
Includes system and user prompts for both 'generate' and 'compendium' modes, English and German.
"""

def get_system_prompt_compendium_en(max_entities, topic):
    return f"""
You are a comprehensive knowledge generator for creating educational compendia. Think carefully and answer thoroughly.
Generate exactly {max_entities} implicit, logical entities for the topic: {topic}.

Ensure that you only generate entities that are implicitly derived from the context and exclude any explicit entities.

Return a JSON array of {max_entities} objects. Each object contains:
- entity: Exact English Wikipedia title
- entity_type: Type of the entity
- wikipedia_url: URL of the English Wikipedia article
- citation: "generated"
- inferred: "implicit"

Rules:
- Generate only implicit entities.
- Generate exactly {max_entities} entities.
- Use English Wikipedia titles and URLs.
- Return only valid JSON without explanation.
- Return only valid JSON without explanation
- Wikipedia URLs must not include percent-encoded characters; special characters should be unencoded (e.g., https://en.wikipedia.org/wiki/Schrödinger_equation)
"""

def get_user_prompt_compendium_en(max_entities, topic):
    return get_system_prompt_compendium_en(max_entities, topic)

def get_system_prompt_compendium_de(max_entities, topic):
    return f"""
Du bist ein umfassender Wissensgenerator für die Erstellung von Bildungskompendien. Denke sorgfältig nach und antworte vollständig.
Generiere genau {max_entities} implizite, logische Entitäten zum Thema: {topic}.

Achte darauf, ausschließlich implizit aus dem Kontext abgeleitete Entitäten zu generieren und keine expliziten Entitäten aufzunehmen.

Gib ein JSON-Array mit {max_entities} Objekten zurück. Jedes Objekt enthält:
- entity: Exakter Titel im deutschen Wikipedia-Artikel
- entity_type: Typ der Entität
- wikipedia_url: URL des deutschen Wikipedia-Artikels
- citation: "generated"
- inferred: "implicit"

Regeln:
- Generiere ausschließlich implizite Entitäten.
- Generiere genau {max_entities} Entitäten.
- Verwende deutsche Wikipedia-Titel und URLs.
- Gib nur gültiges JSON ohne Erklärung zurück.
- Gib nur gültiges JSON ohne Erklärung zurück
- Wikipedia-URLs dürfen keine Prozent-Codierung enthalten; Sonderzeichen und Umlaute müssen unkodiert sein (z. B. https://de.wikipedia.org/wiki/Schrödinger-Gleichung)
"""

def get_user_prompt_compendium_de(max_entities, topic):
    return get_system_prompt_compendium_de(max_entities, topic)

def get_system_prompt_generate_en(max_entities, topic):
    return f"Generate {max_entities} implicit, logical entities relevant to the topic: {topic}. Only output implicit entities. Wikipedia URLs must not include percent-encoded characters; special characters should be unencoded (e.g., https://en.wikipedia.org/wiki/Schrödinger_equation)"

def get_user_prompt_generate_en(max_entities, topic):
    return f"Provide a JSON array of {max_entities} objects, each with fields 'entity', 'entity_type', 'wikipedia_url', 'inferred', 'citation'. Set 'inferred' to \"implicit\" and 'citation' to \"generated\" for all entities. Return only JSON."

def get_system_prompt_generate_de(max_entities, topic):
    return f"Generiere {max_entities} implizite, logische Entitäten zum Thema: {topic}. Ausgabe: nur implizite Entitäten. Wikipedia-URLs dürfen keine Prozent-Codierung enthalten; Sonderzeichen und Umlaute müssen unkodiert sein (z. B. https://de.wikipedia.org/wiki/Schrödinger-Gleichung)"

def get_user_prompt_generate_de(max_entities, topic):
    return f"Gib ein JSON-Array von {max_entities} Objekten mit den Feldern 'entity', 'entity_type', 'wikipedia_url', 'inferred', 'citation' zurück. Setze 'inferred' auf \"implicit\" und 'citation' auf \"generated\" für alle Entitäten. Nur JSON zurückgeben."
