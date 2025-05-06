"""
Entity Inference Module

Dieses Modul ergänzt implizite Entitäten durch einen zweiten Prompt, wenn ENABLE_ENTITY_INFERENCE aktiviert ist.
"""
import json
import logging
import time
from openai import OpenAI
from entityextractor.config.settings import get_config, DEFAULT_CONFIG
from entityextractor.utils.logging_utils import configure_logging
from entityextractor.prompts.entity_inference_prompts import (
    get_system_prompt_entity_inference_en,
    get_user_prompt_entity_inference_en,
    get_system_prompt_entity_inference_de,
    get_user_prompt_entity_inference_de,
)

# Default-Konfiguration
DEFAULT_CONFIG = {
    "MODEL": "gpt-4.1-mini",
    "LANGUAGE": "de",
    "TEMPERATURE": 0.2,
}

def infer_entities(text, entities, user_config=None):
    """
    Ergänzt implizite Entitäten via LLM, wenn ENABLE_ENTITY_INFERENCE=True.

    Args:
        text: Originaltext oder Topic
        entities: Liste expliziter Entitäten (dicts mit Feldern 'entity'/'name', 'entity_type'/'type', optional 'wikipedia_url')
        user_config: Benutzerkonfiguration

    Returns:
        Liste vereinheitlichter Entitäten mit Feldern:
        'name', 'type', 'wikipedia_url', 'inferred', 'citation'
    """
    config = get_config(user_config)
    configure_logging(config)
    # Einheitliche Abbildung expliziter Entitäten
    explicit = []
    for e in entities:
        name = e.get("entity") or e.get("name", "")
        typ = (e.get("entity_type") or e.get("type") or
               (e.get("details", {}).get("typ") if isinstance(e.get("details"), dict) else None) or "")
        url = e.get("wikipedia_url", "")
        # Preserve original 'inferred' flag (default to explicit if missing)
        inferred_flag = e.get("inferred", "explicit")
        explicit.append({"name": name, "type": typ, "wikipedia_url": url, "inferred": inferred_flag})
    # Logging: Anzahl expliziter Entitäten
    logging.info(f"Vorhandene explizite Entitäten: {len(explicit)}")
    # Wenn nicht aktiviert, zurückgeben
    if not config.get("ENABLE_ENTITY_INFERENCE", False):
        logging.info("Entity Inference deaktiviert.")
        return explicit
    # Entity Inference aktiviert: Erzeuge implizite Entitäten via LLM...
    logging.info("Entity Inference aktiviert: Erzeuge implizite Entitäten via LLM...")
    # Vorbereitung Prompt
    language = config.get("LANGUAGE", DEFAULT_CONFIG["LANGUAGE"])
    max_entities = config.get("MAX_ENTITIES", len(explicit))
    if language == "de":
        system_prompt = get_system_prompt_entity_inference_de(max_entities)
        user_msg = get_user_prompt_entity_inference_de(text, explicit, max_entities)
    else:
        system_prompt = get_system_prompt_entity_inference_en(max_entities)
        user_msg = get_user_prompt_entity_inference_en(text, explicit, max_entities)
    # API-Aufruf
    logging.info(f"Rufe OpenAI API für implizite Entitäten auf (Modell {config.get('MODEL', DEFAULT_CONFIG['MODEL'])})...")
    client = OpenAI(api_key=config.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=config.get("MODEL", DEFAULT_CONFIG["MODEL"]),
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}],
        temperature=config.get("TEMPERATURE", DEFAULT_CONFIG["TEMPERATURE"]),
        max_tokens=1500,
    )
    raw = response.choices[0].message.content
    # JSON parsen
    try:
        new_list = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        new_list = json.loads(raw[start:end])
    # Vereinheitlichung neuer Entities
    implicit = []
    for e in new_list:
        name = e.get("entity") or e.get("name", "")
        typ = e.get("entity_type") or e.get("type", "")
        url = e.get("wikipedia_url", "")
        inferred = e.get("inferred", "implicit")
        # Set citation for implicit entities
        citation = e.get("citation", "generated")
        if name and typ:
            implicit.append({
                "name": name,
                "type": typ,
                "wikipedia_url": url,
                "inferred": inferred,
                "citation": citation
            })
    # Logging: Anzahl impliziter Entitäten
    logging.info(f"Extrahierte implizite Entitäten: {len(implicit)}")
    # Merge (explicit überschreibt implicit bei Duplikaten)
    merged = { (e["name"], e["type"]): e for e in implicit }
    for e in explicit:
        merged[(e["name"], e["type"])] = e
    return list(merged.values())
