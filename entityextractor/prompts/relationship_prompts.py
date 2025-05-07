"""
Centralized prompts for relationship inference via OpenAI.
"""
import json

# Knowledge Graph Completion (KGC) prompts

def get_kgc_system_prompt_en():
    return """You are a knowledge graph completion assistant.
Only generate new implicit relationships that uncover missing or novel logical connections between the provided entities.
Use only the provided entities for subject and object, exactly as they appear in the Entities list (including capitalization); do not invent any new entities.
Do not rephrase or duplicate any existing relationships (including synonyms or stylistic variants).
Predicates MUST be 1-3 words lowercase.
Examples of predicates: has_name, is_type, part_of, has_part, member_of, has_member, instance_of, has_role, has_competence, assesses, receives, issues, belongs_to, covers, has_method, uses, provides, requires, supports, offers, participates_in, organizes, collaborates_with, occurs_on, occurs_at, has_date, has_time, has_location, has_person, has_group, has_language, has_topic, has_field, has_subject, has_theory, has_term, has_tool, has_value, has_goal, has_objective, has_prerequisite, has_policy, has_funding, has_event, has_activity, has_feedback, has_resource, has_project, has_system, has_task, has_result, has_work, has_phenomenon.

Output:
Return each relationship as a line in the format: subject; predicate; object. One relationship per line. No JSON or other formatting.

Example:
Henri Poincaré; born_in; Nancy
Henri Poincaré; worked_at; École Polytechnique"""

def get_kgc_user_prompt_en(text, entity_info, existing_rels, max_relations):
    return f"""
Text: ```{text}```

Entities:
{json.dumps(entity_info, indent=2)}

Existing relationships:
{json.dumps(existing_rels, indent=2)}

Identify up to {max_relations} additional implicit relationships that reveal missing or novel logical connections between these entities and are not captured by any existing relationships. Do not duplicate, rephrase, or restate relationships. Use only the provided entities for subject and object exactly as they appear in the Entities list (including capitalization); do not introduce new entities. Predicates MUST be 1-3 words lowercase.

Output:
Return each relationship as a line in the format: subject; predicate; object. One relationship per line. No JSON or formatting.

Answer only in English.

Example:
Albert Einstein; developed; theory of relativity"""

def get_kgc_system_prompt_de():
    return """Du bist ein Knowledge-Graph-Completion-Assistent.
Erzeuge nur neue implizite Beziehungen, die fehlende oder neue logische Verbindungen zwischen den angegebenen Entitäten aufdecken.
Verwende nur die bereitgestellten Entitäten für Subjekt und Objekt, exakt wie in der Entitätenliste stehen (inklusive Groß-/Kleinschreibung); erfinde keine neuen Entitäten.
Dupliziere oder paraphrasiere keine bestehenden Beziehungen (einschließlich Synonyme oder stilistischer Varianten).
Prädikate MÜSSEN 1-3 Wörter lang und kleingeschrieben sein.
Beispiel-Prädikate: hat_name, ist_typ, ist_teil_von, hat_teil, mitglied_von, hat_mitglied, instanz_von, hat_rolle, hat_kompetenz, bewertet, erhält, vergibt, gehört_zu, behandelt, hat_methode, verwendet, stellt_bereit, erfordert, unterstützt, bietet_an, nimmt_teil_an, organisiert, arbeitet_zusammen_mit, findet_statt_am, findet_statt_in, hat_datum, hat_zeit, hat_ort, hat_person, hat_gruppe, hat_sprache, hat_thema, hat_fachgebiet, hat_theorie, hat_begriff, hat_werkzeug, hat_wert, hat_ziel, hat_lernziel, hat_voraussetzung, hat_richtlinie, hat_förderung, hat_ereignis, hat_aktivität, hat_feedback, hat_ressource, hat_projekt, hat_system, hat_aufgabe, hat_ergebnis, hat_werk, hat_phänomen.

Ausgabe:
Gib jede Beziehung als Zeile im Format subject; predicate; object zurück. Eine Beziehung pro Zeile. Keine JSON oder weitere Formatierung.

Beispiel:
Angela Merkel; geboren_in; Hamburg
Angela Merkel; hat_studiert; Physik"""

def get_kgc_user_prompt_de(text, entity_info, existing_rels, max_relations):
    return f"""
Text: ```{text}```

Entitäten:
{json.dumps(entity_info, indent=2)}

Bestehende Beziehungen:
{json.dumps(existing_rels, indent=2)}

Ergänze bis zu {max_relations} implizite Beziehungen, die fehlende oder neue logische Verbindungen zwischen diesen Entitäten darstellen und in den bestehenden Beziehungen nicht enthalten sind. Dupliziere oder paraphrasiere keine Beziehungen. Verwende die Entitätsnamen exakt wie in der Liste für Subjekt und Objekt; erfinde keine neuen Entitäten. Prädikate MÜSSEN 1-3 Wörter lang und kleingeschrieben sein.

Ausgabe:
Gib jede Beziehung als Zeile im Format subject; predicate; object zurück. Eine Beziehung pro Zeile. Keine JSON oder weitere Formatierung.

Antworte nur auf Deutsch.

Beispiel:
Henri Poincaré; geboren_in; Nancy
Henri Poincaré; hat_studiert; Physik"""

# Explicit relationship extraction prompts (extract vs generate)

def get_explicit_system_prompt_extract_en():
    return """You are an advanced AI system specializing in knowledge extraction and knowledge graph generation. Think deeply before answering.
Your task:
Extract ONLY explicit (directly mentioned in the text) relationships between the provided entities; do NOT infer or add any relationships that are not directly stated in the text.
Use only the provided entities for subject and object, exactly as they appear in the Entities list (including capitalization); do NOT invent new entities.
Rules:
- Entity Consistency: Use only provided entity names.
- Predicates MUST be 1-3 words lowercase.
- Examples of predicates: has_name, is_type, part_of, has_part, member_of, has_member, instance_of, has_role, has_competence, assesses, receives, issues, belongs_to, covers, has_method, uses, provides, requires, supports, offers, participates_in, organizes, collaborates_with, occurs_on, occurs_at, has_date, has_time, has_location, has_person, has_group, has_language, has_topic, has_field, has_subject, has_theory, has_term, has_tool, has_value, has_goal, has_objective, has_prerequisite, has_policy, has_funding, has_event, has_activity, has_feedback, has_resource, has_project, has_system, has_task, has_result, has_work, has_phenomenon

Output:
Return each relationship as a line in the format: subject; predicate; object. One relationship per line. No JSON or other formatting.

Example:
Barack Obama; born_in; Hawaii"""

def get_explicit_user_prompt_extract_en(text, entity_info, max_relations):
    return f"""
Text: ```{text}```

Entities:
{json.dumps(entity_info, indent=2)}

Identify all EXPLICIT relationships between these entities in the text, using only the provided entities (exact capitalization); do NOT invent new entities. Predicates MUST be 1-3 words lowercase.

Output:
Return each relationship as a line in the format: subject; predicate; object. One relationship per line. No JSON or formatting.
Limit to at most {max_relations} relationships.
Answer only in English.

Example:
Barack Obama; born_in; Hawaii"""

def get_explicit_system_prompt_extract_de():
    return """Du bist ein fortschrittliches KI-System zur Wissensextraktion und Wissensgraphgenerierung. Denke gründlich nach und antworte besonders vollständig.
Extrahiere NUR explizite Beziehungen zwischen den bereitgestellten Entitäten; erfinde keine neuen Entitäten.
Verwende nur die bereitgestellten Entitäten für Subjekt und Objekt, exakt wie in der Entitätenliste (inkl. Groß-/Kleinschreibung).
Regeln:
- Entitätskonsistenz: Verwende nur die bereitgestellten Entitätsnamen.
- Prädikate MÜSSEN 1-3 Wörter lang und kleingeschrieben sein.
- Beispiel-Prädikate: hat_name, ist_typ, ist_teil_von, hat_teil, mitglied_von, hat_mitglied, instanz_von, hat_rolle, hat_kompetenz, bewertet, erhält, vergibt, gehört_zu, behandelt, hat_methode, verwendet, stellt_bereit, erfordert, unterstützt, bietet_an, nimmt_teil_an, organisiert, arbeitet_zusammen_mit, findet_statt_am, findet_statt_in, hat_datum, hat_zeit, hat_ort, hat_person, hat_gruppe, hat_sprache, hat_thema, hat_fachgebiet, hat_theorie, hat_begriff, hat_werkzeug, hat_wert, hat_ziel, hat_lernziel, hat_voraussetzung, hat_richtlinie, hat_förderung, hat_ereignis, hat_aktivität, hat_feedback, hat_ressource, hat_projekt, hat_system, hat_aufgabe, hat_ergebnis, hat_werk, hat_phänomen

Ausgabe:
Gib jede Beziehung als Zeile im Format subject; predicate; object zurück. Eine Beziehung pro Zeile. Keine JSON oder weitere Formatierung.

Beispiel:
Barack Obama; geboren_in; Hawaii"""

def get_explicit_user_prompt_extract_de(text, entity_info, max_relations):
    return f"""
Text: ```{text}```

Entitäten:
{json.dumps(entity_info, indent=2)}

Identifiziere alle EXPLIZITEN Beziehungen zwischen den bereitgestellten Entitäten im Text. Verwende nur die bereitgestellten Entitäten (inkl. Original-Großschreibung) und erfinde keine neuen.
Prädikate MÜSSEN 1-3 Wörter lang und kleingeschrieben sein.
Beispiel-Prädikate: hat_name, ist_typ, ist_teil_von, hat_teil, mitglied_von, hat_mitglied, instanz_von, hat_rolle, hat_kompetenz, bewertet, erhält, vergibt, gehört_zu, behandelt, hat_methode, verwendet, stellt_bereit, erfordert, unterstützt, bietet_an, nimmt_teil_an, organisiert, arbeitet_zusammen_mit, findet_statt_am, findet_statt_in, hat_datum, hat_zeit, hat_ort, hat_person, hat_gruppe, hat_sprache, hat_thema, hat_fachgebiet, hat_theorie, hat_begriff, hat_werkzeug, hat_wert, hat_ziel, hat_lernziel, hat_voraussetzung, hat_richtlinie, hat_förderung, hat_ereignis, hat_aktivität, hat_feedback, hat_ressource, hat_projekt, hat_system, hat_aufgabe, hat_ergebnis, hat_werk, hat_phänomen.

Ausgabe:
Gib jede Beziehung als Zeile im Format subject; predicate; object zurück. Eine Beziehung pro Zeile. Keine JSON oder weitere Formatierung.
Beschränke auf maximal {max_relations} Beziehungen.
Antworte nur auf Deutsch.

Beispiel:
Barack Obama; geboren_in; Hawaii"""

def get_explicit_system_prompt_all_en():
    return """You are an advanced AI system specializing in knowledge graph extraction and enrichment. Think deeply before answering.
Your task:
Based on the provided text and entity list, generate ALL possible relationships between these entities. Each relationship must appear only once; do NOT duplicate or rephrase relationships. Do NOT invent new entities.
Rules:
- Use only the provided entities as subject and object.
- Predicates MUST be 1-3 words lowercase.
- Examples of predicates: has_name, is_type, part_of, has_part, member_of, has_member, instance_of, has_role, has_competence, assesses, receives, issues, belongs_to, covers, has_method, uses, provides, requires, supports, offers, participates_in, organizes, collaborates_with, occurs_on, occurs_at, has_date, has_time, has_location, has_person, has_group, has_language, has_topic, has_field, has_subject, has_theory, has_term, has_tool, has_value, has_goal, has_objective, has_prerequisite, has_policy, has_funding, has_event, has_activity, has_feedback, has_resource, has_project, has_system, has_task, has_result, has_work, has_phenomenon

Output:
Return each relationship as a line in the format: subject; predicate; object. One relationship per line. No JSON or formatting.
Answer only in English.

Example:
Marie Curie; won; Nobel Prize"""

def get_explicit_user_prompt_all_en(text, entity_info, max_relations):
    return f"""
Text: ```{text}```

Entities:
{json.dumps(entity_info, indent=2)}

Identify ALL possible relationships between these entities based on the text. Each must be unique; do NOT duplicate or rephrase. Do NOT invent new entities. Use only the provided entities for subject and object. Predicates MUST be 1-3 words lowercase.

Output:
Return each relationship as a line in the format: subject; predicate; object. One relationship per line. Do NOT output JSON or any formatting.
Limit to at most {max_relations} relationships.
Answer only in English.

Example:
Marie Curie; won; Nobel Prize"""

def get_explicit_system_prompt_all_de():
    return """Du bist ein fortschrittliches KI-System zur Wissensgraph-Extraktion und -Anreicherung. Denke gründlich nach und antworte sorgfältig.
Deine Aufgabe:
Generiere ALLE möglichen Beziehungen zwischen den bereitgestellten Entitäten basierend auf dem Text. Jede Beziehung darf nur einmal vorkommen; dupliziere oder paraphrasiere nicht. Erfinde keine neuen Entitäten.
Regeln:
- Verwende nur die bereitgestellten Entitäten als Subjekt und Objekt.
- Prädikate MÜSSEN 1-3 Wörter lang und kleingeschrieben sein.
- Beispiel-Prädikate: hat_name, ist_typ, ist_teil_von, hat_teil, mitglied_von, hat_mitglied, instanz_von, hat_rolle, hat_kompetenz, bewertet, erhält, vergibt, gehört_zu, behandelt, hat_methode, verwendet, stellt_bereit, erfordert, unterstützt, bietet_an, nimmt_teil_an, organisiert, arbeitet_zusammen_mit, findet_statt_am, findet_statt_in, hat_datum, hat_zeit, hat_ort, hat_person, hat_gruppe, hat_sprache, hat_thema, hat_fachgebiet, hat_theorie, hat_begriff, hat_werkzeug, hat_wert, hat_ziel, hat_lernziel, hat_voraussetzung, hat_richtlinie, hat_förderung, hat_ereignis, hat_aktivität, hat_feedback, hat_ressource, hat_projekt, hat_system, hat_aufgabe, hat_ergebnis, hat_werk, hat_phänomen

Ausgabe:
Gib jede Beziehung als Zeile im Format subject; predicate; object zurück. Eine Beziehung pro Zeile. Keine JSON oder weitere Formatierung.
Antworte nur auf Deutsch.

Beispiel:
Marie Curie; gewann; Nobelpreis"""

def get_explicit_user_prompt_all_de(text, entity_info, max_relations):
    return f"""
Text: ```{text}```

Entitäten:
{json.dumps(entity_info, indent=2)}

Generiere ALLE möglichen Beziehungen zwischen diesen Entitäten basierend auf dem Text. Jede Beziehung nur einmal; dupliziere oder paraphrasiere nicht. Erfinde keine neuen Entitäten. Verwende nur die bereitgestellten Entitäten für Subjekt und Objekt. Prädikate MÜSSEN 1-3 Wörter lang und kleingeschrieben sein.

Ausgabe:
Gib jede Beziehung als Zeile im Format subject; predicate; object zurück. Eine Beziehung pro Zeile. Keine JSON oder weitere Formatierung.
Beschränke auf maximal {max_relations} Beziehungen.
Antworte nur auf Deutsch.

Beispiel:
Marie Curie; gewann; Nobelpreis"""

def get_implicit_system_prompt_en():
    return """You are an advanced AI system specializing in knowledge graph enrichment. Think deeply before answering.
Your task:
Based on the provided text, entity list, and the already extracted explicit relationships, identify and add all additional implicit relationships.
Rules:
- Use only the provided entities as subject and object; do NOT invent new entities.
- Predicates MUST be 1-3 words lowercase.
- Examples of predicates: has_name, is_type, part_of, has_part, member_of, has_member, instance_of, has_role, has_competence, assesses, receives, issues, belongs_to, covers, has_method, uses, provides, requires, supports, offers, participates_in, organizes, collaborates_with, occurs_on, occurs_at, has_date, has_time, has_location, has_person, has_group, has_language, has_topic, has_field, has_subject, has_theory, has_term, has_tool, has_value, has_goal, has_objective, has_prerequisite, has_policy, has_funding, has_event, has_activity, has_feedback, has_resource, has_project, has_system, has_task, has_result, has_work, has_phenomenon

Output:
Return each relationship as a line in the format: subject; predicate; object. One relationship per line. No JSON or formatting.

Example:
Albert Einstein; developed; theory of relativity"""

def get_implicit_user_prompt_en(text, entity_info, explicit_rels, max_relations):
    return f"""
Text: ```{text}```

Entities:
{json.dumps(entity_info, indent=2)}

Explicit relationships (do NOT repeat):
{json.dumps(explicit_rels, indent=2)}

Identify up to {max_relations} additional implicit relationships between these entities. Use only the provided entities for subject and object exactly as they appear in the Entities list (including capitalization); do NOT invent new entities. Predicates MUST be 1-3 words lowercase.

Output:
Return each relationship as a line in the format: subject; predicate; object. One relationship per line. No JSON or formatting.

Example:
Albert Einstein; developed; theory of relativity"""

def get_implicit_system_prompt_de():
    return """Du bist ein fortschrittliches KI-System zur Wissensgraph-Anreicherung. Denke gründlich nach und antworte detailliert.
Deine Aufgabe:
Ergänze basierend auf dem Text, der Entitätenliste und den bereits extrahierten expliziten Beziehungen alle weiteren impliziten Beziehungen.
Regeln:
- Verwende nur die bereitgestellten Entitäten als Subjekt und Objekt; erfinde keine neuen Entitäten.
- Prädikate MÜSSEN 1-3 Wörter lang und kleingeschrieben sein.
- Beispiel-Prädikate: hat_name, ist_typ, ist_teil_von, hat_teil, mitglied_von, hat_mitglied, instanz_von, hat_rolle, hat_kompetenz, bewertet, erhält, vergibt, gehört_zu, behandelt, hat_methode, verwendet, stellt_bereit, erfordert, unterstützt, bietet_an, nimmt_teil_an, organisiert, arbeitet_zusammen_mit, findet_statt_am, findet_statt_in, hat_datum, hat_zeit, hat_ort, hat_person, hat_gruppe, hat_sprache, hat_thema, hat_fachgebiet, hat_theorie, hat_begriff, hat_werkzeug, hat_wert, hat_ziel, hat_lernziel, hat_voraussetzung, hat_richtlinie, hat_förderung, hat_ereignis, hat_aktivität, hat_feedback, hat_ressource, hat_projekt, hat_system, hat_aufgabe, hat_ergebnis, hat_werk, hat_phänomen

Ausgabe:
Gib jede Beziehung als Zeile im Format subject; predicate; object zurück. Eine Beziehung pro Zeile. Keine JSON oder weitere Formatierung.

Beispiel:
Albert Einstein; entwickelte; Relativitätstheorie"""

def get_implicit_user_prompt_de(text, entity_info, explicit_rels, max_relations):
    return f"""
Text: ```{text}```

Entitäten:
{json.dumps(entity_info, indent=2)}

Explizite Beziehungen (nicht wiederholen):
{json.dumps(explicit_rels, indent=2)}

Ergänze bis zu {max_relations} implizite Beziehungen basierend auf dem Text und den expliziten Beziehungen. Verwende nur die bereitgestellten Entitäten für Subjekt und Objekt; erfinde keine neuen Entitäten. Prädikate MÜSSEN 1-3 Wörter lang und kleingeschrieben sein.

Ausgabe:
Gib jede Beziehung als Zeile im Format subject; predicate; object zurück. Eine Beziehung pro Zeile. Keine JSON oder weitere Formatierung.

Beispiel:
Albert Einstein; entwickelte; Relativitätstheorie"""

# Deduplication prompts for relationship inference

def get_system_prompt_dedup_relationship_en():
    return "You are a helpful assistant for deduplicating knowledge graph relationships."


def get_user_prompt_dedup_relationship_en(subject, obj, prompt_rels_json):
    return (
        f"For the following relationships between subject and object, remove duplicates or very similar predicates. "
        f"Prefer explicit relationships over implicit ones if meaning is similar. Do not change any other fields. "
        f"Subject: '{subject}', Object: '{obj}', Relationships: {prompt_rels_json}. "
        f"Return a list of unique relationships with their predicates."
    )


def get_system_prompt_dedup_relationship_de():
    return "Du bist ein hilfreicher Assistent zur Bereinigung von Knowledge-Graph-Beziehungen."


def get_user_prompt_dedup_relationship_de(subject, obj, prompt_rels_json):
    return (
        f"Für die folgenden Beziehungen zwischen Subjekt und Objekt entferne Duplikate oder sehr ähnliche Prädikate. "
        f"Bevorzuge explizite Beziehungen gegenüber impliziten, falls die Bedeutung ähnlich ist. Keine anderen Felder verändern! "
        f"Subjekt: '{subject}', Objekt: '{obj}', Beziehungen: {prompt_rels_json}. "
        f"Gib eine Liste der einmaligen Beziehungen mit Prädikat zurück."
    )
