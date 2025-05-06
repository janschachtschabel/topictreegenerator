"""
Centralized prompts for relationship inference via OpenAI.
"""
import json

# Knowledge Graph Completion (KGC) prompts

def get_kgc_system_prompt_en():
    return (
        "You are a knowledge graph completion assistant. "
        "Only generate new implicit relationships that uncover missing or novel logical connections between the provided entities; do not invent any new entities. "
        "Do not rephrase or duplicate any existing relationships (including synonyms or stylistic variants). "
        "Predicates MUST be 1-3 words lowercase."
    )

def get_kgc_user_prompt_en(text, entity_info, existing_rels):
    return f"""
Text: ```{text}```

Entities:
{json.dumps(entity_info, indent=2)}

Existing relationships:
{json.dumps(existing_rels, indent=2)}

Identify additional IMPLICIT relationships that reveal missing or novel logical connections between these entities, which are not captured by any existing relationships (including synonyms or paraphrases). Do not duplicate, rephrase, or restate any existing relationships. Use only the provided entities as subject and object; do not introduce any other entities. Set inferred="implicit". Predicates MUST be 1-3 words lowercase. Return only JSON. Answer only in English.
"""

def get_kgc_system_prompt_de():
    return (
        "Du bist ein Knowledge-Graph-Completion-Assistent. "
        "Erzeuge nur neue implizite Beziehungen, die fehlende oder neue logische Verbindungen zwischen den angegebenen Entitäten aufdecken; erfinde keine neuen Entitäten. "
        "Dupliziere oder paraphrasiere keine bestehenden Beziehungen (einschließlich Synonyme oder stilistischer Varianten). "
        "Prädikate MÜSSEN 1-3 Wörter lang und kleingeschrieben sein."
    )

def get_kgc_user_prompt_de(text, entity_info, existing_rels):
    return f"""
Text: ```{text}```

Entitäten:
{json.dumps(entity_info, indent=2)}

Bestehende Beziehungen:
{json.dumps(existing_rels, indent=2)}

Ergänze weitere IMPLIZITE Beziehungen, die fehlende oder neue logische Verbindungen zwischen diesen Entitäten darstellen und in den bestehenden Beziehungen nicht enthalten sind (einschließlich Synonyme oder Paraphrasen). Dupliziere oder paraphrasiere keine bestehenden Beziehungen. Nutze ausschließlich die angegebenen Entitäten als Subjekt und Objekt; erfinde keine neuen Entitäten. Setze inferred="implicit". Prädikate MÜSSEN 1-3 Wörter lang und kleingeschrieben sein. Nur JSON zurückgeben.
"""

# Explicit relationship extraction prompts (extract vs generate)

def get_explicit_system_prompt_extract_en():
    return (
        "You are an advanced AI system specialized in knowledge extraction and knowledge graph generation. "
        "Think deeply before answering and provide a thorough, comprehensive response.\n"
        "Your task:\n"
        "Extract ONLY explicit (directly mentioned in the text) relationships between the provided entities. Do NOT infer or add any relationships that are not directly stated in the text.\n"
        "Use only the provided entities for subject and object; do NOT invent new entities.\n"
        "Rules:\n"
        "- Entity Consistency: Use only provided entity names.\n"
        "- Predicates MUST be 1-3 words lowercase.\n"
        "Output:\n"
        "Return only a JSON array of objects with keys \"subject\", \"predicate\", \"object\", and \"inferred\" (set to \"explicit\").\n"
        "Answer only in English."
    )

def get_explicit_user_prompt_extract_en(text, entity_info):
    return f"""
Text: ```{text}```

Entities:
{json.dumps(entity_info, indent=2)}

Identify all EXPLICIT relationships between these entities in the text. For each relationship, set inferred="explicit". Return only JSON. Answer only in English.
"""

def get_explicit_system_prompt_extract_de():
    return (
        "Du bist ein fortschrittliches KI-System zur Wissensextraktion und Wissensgraphgenerierung. "
        "Denke gründlich nach und antworte besonders vollständig und sorgfältig.\n"
        "Extrahiere NUR explizite Beziehungen zwischen den bereitgestellten Entitäten. Erfinde keine neuen Entitäten.\n"
        "Regeln:\n"
        "- Entitätskonsistenz: Verwende nur die bereitgestellten Entitätsnamen.\n"
        "- Prädikate MÜSSEN 1-3 Wörter lang und kleingeschrieben sein.\n"
        "Ausgabe:\n"
        "Gib nur ein JSON-Array mit Objekten zurück, die \"subject\", \"predicate\", \"object\" und \"inferred\" (\"explicit\") enthalten.\n"
        "Antworte nur auf Deutsch."
    )

def get_explicit_user_prompt_extract_de(text, entity_info):
    return f"""
Text: ```{text}```

Entitäten:
{json.dumps(entity_info, indent=2)}

Identifiziere alle EXPLIZITEN Beziehungen zwischen diesen Entitäten im Text. Setze inferred="explicit". Nur JSON zurückgeben. Antworte nur auf Deutsch.
"""

def get_explicit_system_prompt_all_en():
    return (
        "You are an advanced AI system specialized in knowledge graph extraction and enrichment. "
        "Think deeply before answering.\n"
        "Your task:\n"
        "Based on the provided text and entity list, extract ALL relationships (explicit and implicit) between these entities. Do NOT invent new entities.\n"
        "Rules:\n"
        "- Predicates MUST be 1-3 words lowercase.\n"
        "Output:\n"
        "Return only a JSON array with keys \"subject\", \"predicate\", \"object\", and \"inferred\" (\"explicit\" or \"implicit\").\n"
    )

def get_explicit_user_prompt_all_en(text, entity_info):
    return f"""
Text: ```{text}```

Entities:
{json.dumps(entity_info, indent=2)}

Generate logical relationship triples (subject, predicate, object) among these entities relevant to this text. Include both explicit and implicit; set inferred accordingly. Return only JSON.
"""

def get_explicit_system_prompt_all_de():
    return (
        "Du bist ein fortschrittliches KI-System zur Extraktion und Anreicherung von Wissensgraphen. Denke gründlich nach.\n"
        "Deine Aufgabe:\n"
        "Basierend auf dem Text und der Entitätenliste, extrahiere ALLE Beziehungen (explizit und implizit) zwischen diesen Entitäten. Erfinde keine neuen Entitäten.\n"
        "Regeln:\n"
        "- Prädikate MÜSSEN 1-3 Wörter lang und kleingeschrieben sein.\n"
        "Ausgabe:\n"
        "Gib nur ein JSON-Array mit \"subject\", \"predicate\", \"object\" und \"inferred\" (\"explicit\" oder \"implicit\").\n"
    )

def get_explicit_user_prompt_all_de(text, entity_info):
    return f"""
Text: ```{text}```

Entitäten:
{json.dumps(entity_info, indent=2)}

Generiere Beziehungstripel (Subjekt, Prädikat, Objekt) zwischen diesen Entitäten auf Basis dieses Textes. Füge explizite und implizite Beziehungen hinzu; setze inferred entsprechend. Nur JSON zurückgeben.
"""

# Deduplication prompts for relationship inference

def get_system_prompt_dedup_relationship_en():
    return "You are a helpful assistant for deduplicating knowledge graph relationships."


def get_user_prompt_dedup_relationship_en(subject, obj, prompt_rels_json):
    return (
        f"For the following relationships between subject and object, remove duplicates or very similar predicates. "
        f"Prefer explicit relationships over implicit ones if meaning is similar. Do not change any other fields. "
        f"Subject: '{subject}', Object: '{obj}', Relationships: {prompt_rels_json}. "
        f"Return a JSON array of unique relationships with their predicates and inferred fields."
    )


def get_system_prompt_dedup_relationship_de():
    return "Du bist ein hilfreicher Assistent zur Bereinigung von Knowledge-Graph-Beziehungen."


def get_user_prompt_dedup_relationship_de(subject, obj, prompt_rels_json):
    return (
        f"Für die folgenden Beziehungen zwischen Subjekt und Objekt entferne Duplikate oder sehr ähnliche Prädikate. "
        f"Bevorzuge explizite Beziehungen gegenüber impliziten, falls die Bedeutung ähnlich ist. Keine anderen Felder verändern! "
        f"Subjekt: '{subject}', Objekt: '{obj}', Beziehungen: {prompt_rels_json}. "
        f"Gib ein JSON-Array der einmaligen Beziehungen mit Prädikat und inferred-Feld zurück."
    )

# Implicit enrichment prompts

def get_implicit_system_prompt_en():
    return (
        "You are an advanced AI system specialized in knowledge graph enrichment. Think deeply before answering.\n"
        "Your task:\n"
        "Based on the provided text, entity list, and the already extracted explicit relationships, identify and add all additional implicit relationships.\n"
        "Rules:\n"
        "- Predicates must be 1-3 words lowercase.\n"
        "Output:\n"
        "Return only a JSON array with keys \"subject\", \"predicate\", \"object\", and \"inferred\" (\"implicit\").\n"
    )

def get_implicit_user_prompt_en(text, entity_info, explicit_rels):
    return f"""
Text: ```{text}```

Entities:
{json.dumps(entity_info, indent=2)}

Explicit relationships (do NOT repeat):
{json.dumps(explicit_rels, indent=2)}

Identify all additional implicit relationships between these entities. Set inferred="implicit". Return only JSON.
"""

def get_implicit_system_prompt_de():
    return (
        "Du bist ein fortgeschrittenes KI-System zur Wissensgraph-Anreicherung. \n"
        "Deine Aufgabe:\n"
        "Ergänze basierend auf dem Text, der Entitätenliste und den bereits extrahierten expliziten Beziehungen alle weiteren impliziten Beziehungen.\n"
        "Regeln:\n"
        "- Prädikate müssen 1-3 Wörter lang und kleingeschrieben sein.\n"
        "Ausgabe:\n"
        "Gib nur ein JSON-Array mit \"subject\", \"predicate\", \"object\" und \"inferred\" (\"implicit\").\n"
    )

def get_implicit_user_prompt_de(text, entity_info, explicit_rels):
    return f"""
Text: ```{text}```

Entitäten:
{json.dumps(entity_info, indent=2)}

Explizite Beziehungen (NICHT wiederholen):
{json.dumps(explicit_rels, indent=2)}

Ergänze alle weiteren impliziten Beziehungen zwischen diesen Entitäten. Setze inferred="implicit". Nur JSON zurückgeben.
"""
