"""
Centralized prompts for relationship deduplication via OpenAI.
Provides system and user prompts for both English and German.
"""

import json


def get_system_prompt_dedup_en():
    return "You are a helpful assistant for deduplicating knowledge graph relationships."


def get_user_prompt_dedup_en(subject, obj, prompt_rels_json):
    return (
        f"For the following relationships between subject and object, select the single most relevant relationship that optimally connects the two entities, "
        f"prioritizing 'explicit' over 'implicit'. Only include additional relationships if they represent completely different aspects. "
        f"Consolidate any synonyms or stylistic variants into the selection. "
        f"Subject: '{subject}', Object: '{obj}', Relationships: {prompt_rels_json}. "
        f"Return a JSON array with the chosen relationship(s), including their predicates and inferred fields."
    )


def get_system_prompt_dedup_de():
    return "Du bist ein hilfreicher Assistent zur Bereinigung von Knowledge-Graph-Beziehungen."


def get_user_prompt_dedup_de(subject, obj, prompt_rels_json):
    return (
        f"Für die folgenden Beziehungen zwischen Subjekt und Objekt wähle genau eine besonders relevante Beziehung, die die beiden Entitäten optimal verbindet, "
        f"wobei 'explicit' über 'implicit' priorisiert wird. Mehr als eine Beziehung soll nur dann zurückgegeben werden, wenn sie vollständig unterschiedliche Aspekte abbildet. "
        f"Synonyme oder stilistische Varianten sollen zusammengeführt und berücksichtigt werden. "
        f"Subjekt: '{subject}', Objekt: '{obj}', Beziehungen: {prompt_rels_json}. "
        f"Gib ein JSON-Array mit der ausgewählten(n) Beziehung(en) inkl. Prädikat und inferred-Feld zurück."
    )
