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

Output a JSON array of objects with these fields:
- entity
- entity_type
- wikipedia_url
- inferred (set to \"implicit\")
- citation (set to \"generated\")
"""

def get_user_prompt_entity_inference_en(text, explicit_entities, max_entities):
    return f"""
Topic/Text: {text}

Existing entities:
{json.dumps(explicit_entities, indent=2, ensure_ascii=False)}

Supplement the list by adding exactly {max_entities} new implicit entities that logically complete the network.
"""

def get_system_prompt_entity_inference_de(max_entities):
    return f"""
Du bist ein KI-Assistent, der eine vorhandene Entitätenliste anreichert, indem er ausschließlich implizite Entitäten ergänzt, um das Wissensnetz logisch zu vervollständigen.
Wiederhole keine der bereits vorhandenen Entitäten.
Generiere genau {max_entities} neue Entitäten.

Gib ein JSON-Array mit Objekten zurück, die folgende Felder enthalten:
- entity
- entity_type
- wikipedia_url
- inferred (set to \"implicit\")
- citation (setze auf \"generated\")
"""

def get_user_prompt_entity_inference_de(text, explicit_entities, max_entities):
    return f"""
Thema/Text: {text}

Vorhandene Entitäten:
{json.dumps(explicit_entities, indent=2, ensure_ascii=False)}

Ergänze genau {max_entities} neue implizite Entitäten, die das Netzwerk logisch vervollständigen.
"""
