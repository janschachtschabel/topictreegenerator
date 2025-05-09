import logging
import os
import time
from openai import OpenAI
from entityextractor.config.settings import get_config
import logging
from entityextractor.prompts.compendium_prompts import get_system_prompt_compendium_de, get_system_prompt_compendium_en

def generate_compendium(topic, entities, relationships, user_config=None):
    config = get_config(user_config)
    api_key = config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key, base_url=config.get("LLM_BASE_URL"))
    length = config.get("COMPENDIUM_LENGTH", 8000)
    temperature = config.get("TEMPERATURE", 0.2)

    # Build knowledge context from extracted entities and relationships
    knowledge_parts = []
    for e in entities:
        parts = []
        src = e.get("sources", {})
        wp = src.get("wikipedia", {})
        if wp.get("extract"):
            parts.append(f"Wikipedia-Extract für {e.get('entity')}: {wp.get('extract')}")
        if wp.get("url"):
            parts.append(f"Wikipedia-URL für {e.get('entity')}: {wp.get('url')}")
        if wp.get("categories"):
            parts.append(f"Kategorien für {e.get('entity')}: {', '.join(wp.get('categories', []))}")
        wd = src.get("wikidata", {})
        if wd.get("id"):
            parts.append(f"Wikidata-ID für {e.get('entity')}: {wd.get('id')}")
        if wd.get("description"):
            parts.append(f"Wikidata-Beschreibung für {e.get('entity')}: {wd.get('description')}")
        if wd.get("types"):
            parts.append(f"Wikidata-Typen für {e.get('entity')}: {', '.join(wd.get('types', []))}")
        db = src.get("dbpedia", {})
        if db.get("abstract"):
            parts.append(f"DBpedia-Abstract für {e.get('entity')}: {db.get('abstract')}")
        if db.get("resource_uri"):
            parts.append(f"DBpedia-URI für {e.get('entity')}: {db.get('resource_uri')}")
        # relationship fields already in relationships list
        if parts:
            knowledge_parts.append("\n".join(parts))
    knowledge = "\n\n".join(knowledge_parts)

    # Build references list for prompt
    refs = []
    for e in entities:
        src = e.get("sources", {})
        # Wikipedia URLs
        wp = src.get("wikipedia", {})
        if wp.get("url"):
            refs.append(wp["url"])
        # Wikidata URLs or IDs
        wd = src.get("wikidata", {})
        if wd.get("url"):
            refs.append(wd["url"])
        elif wd.get("id"):
            refs.append(f"https://www.wikidata.org/wiki/{wd['id']}")
        # DBpedia URIs
        db = src.get("dbpedia", {})
        if db.get("resource_uri"):
            refs.append(db["resource_uri"])
    refs = list(dict.fromkeys(refs))

    lang = config.get("LANGUAGE", "de").lower()
    # Use compendium prompts with educational flag
    educational = config.get("COMPENDIUM_EDUCATIONAL_MODE", False)
    if lang.startswith("en"):
        prompt = get_system_prompt_compendium_en(topic, length, refs, educational)
    else:
        prompt = get_system_prompt_compendium_de(topic, length, refs, educational)
    prompt += "\n### Wissen aus Quellen:\n" + knowledge

    try:
        logging.info("[compendium_service] Generating compendium...")
        start = time.time()
        response = client.chat.completions.create(
            model=config.get("MODEL"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=length,
            temperature=temperature
        )
        comp_text = response.choices[0].message.content.strip()
        elapsed = time.time() - start
        logging.info(f"[compendium_service] Generated compendium in {elapsed:.2f}s")
        return comp_text, refs
    except Exception as e:
        logging.error(f"Error generating compendium: {e}")
        return "", []
