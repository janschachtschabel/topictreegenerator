"""
OpenAI service module for the Entity Extractor.

This module provides functions for interacting with the OpenAI API
to extract entities from text.
"""

import json
import logging
import os
import time
from openai import OpenAI

from entityextractor.config.settings import DEFAULT_CONFIG
from entityextractor.utils.text_utils import clean_json_from_markdown
from entityextractor.prompts.extract_prompts import (
    get_system_prompt_en, get_system_prompt_de,
    USER_PROMPT_EN, USER_PROMPT_DE,
    TYPE_RESTRICTION_TEMPLATE_EN, TYPE_RESTRICTION_TEMPLATE_DE
)
from entityextractor.utils.prompt_utils import apply_type_restrictions

def extract_entities_with_openai(text, config=None):
    """
    Extract entities from text using OpenAI's API.
    
    Args:
        text: The text to extract entities from
        config: Configuration dictionary with API key and model settings
        
    Returns:
        A list of extracted entities or an empty list if extraction failed
    """
    if config is None:
        config = DEFAULT_CONFIG
        
    api_key = config.get("OPENAI_API_KEY")
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        
    if not api_key:
        logging.error("No OpenAI API key provided. Set OPENAI_API_KEY in config or environment.")
        return []
        
    model = config.get("MODEL", "gpt-4o-mini")
    language = config.get("LANGUAGE", "de")
    max_entities = config.get("MAX_ENTITIES", 10)
    allowed_entity_types = config.get("ALLOWED_ENTITY_TYPES", "auto")
    
    # LLM-Konfigurationsmerkmale
    base_url = config.get("LLM_BASE_URL", "https://api.openai.com/v1")
    max_tokens = config.get("MAX_TOKENS", 12000)
    temperature = config.get("TEMPERATURE", None)

    # Create the OpenAI client
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    # Prüfe den Modus (extract oder generate)
    mode = config.get("MODE", "extract")
    
    # Wenn der Modus explizit auf "extract" gesetzt ist, stellen wir sicher, dass wir im Extraktionsmodus sind
    if mode != "extract" and mode != "generate":
        logging.warning(f"Unknown MODE '{mode}' specified. Defaulting to 'extract'.")
        mode = "extract"
    
    # Build system prompt and user message
    system_prompt = get_system_prompt_en(max_entities) if language == "en" else get_system_prompt_de(max_entities)
    system_prompt = apply_type_restrictions(system_prompt, allowed_entity_types, language)
    user_msg = USER_PROMPT_EN.format(text=text) if language == "en" else USER_PROMPT_DE.format(text=text)

    try:
        start_time = time.time()
        logging.info(f"Extracting entities with OpenAI model {model}...")
        
        # Messages for OpenAI request
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ]
        # LLM-Request: max_tokens und base_url immer setzen, temperature nur wenn angegeben
        # Nur Modelle mit JSON-Mode erlauben response_format
        json_mode_models = [
            "gpt-3.5-turbo-1106", "gpt-3.5-turbo-0125", "gpt-4-1106-preview", "gpt-4-turbo-preview", "gpt-4-0125-preview", "gpt-4o", "gpt-4o-2024-05-13"
        ]
        openai_kwargs = dict(
            model=model,
            messages=messages,
            stream=False,
            stop=None,
            timeout=60,
            max_tokens=max_tokens
        )
        if model in json_mode_models:
            openai_kwargs["response_format"] = {"type": "json_object"}

        if temperature is not None:
            openai_kwargs["temperature"] = temperature
        response = client.chat.completions.create(**openai_kwargs)
        
        # Parse semicolon-separated entity lines
        raw_output = response.choices[0].message.content.strip()
        lines = raw_output.splitlines()
        processed_entities = []
        for ln in lines:
            parts = [p.strip() for p in ln.split(";")]
            if len(parts) >= 4:
                name, typ, url, citation = parts[:4]
                inferred_flag = "explicit" if mode == "extract" else "implicit"
                processed_entities.append({
                    "name": name,
                    "type": typ,
                    "wikipedia_url": url,
                    "citation": citation,
                    "inferred": inferred_flag
                })
        elapsed_time = time.time() - start_time
        logging.info(f"Extracted {len(processed_entities)} entities in {elapsed_time:.2f} seconds")
        # Save training data if enabled
        if config.get("COLLECT_TRAINING_DATA", False):
            save_training_data(text, processed_entities, config)
        return processed_entities
    except Exception as e:
        logging.error(f"Error calling OpenAI API: {e}")
        return []

def save_training_data(text, entities, config=None):
    """
    Save training data for future fine-tuning.
    
    Args:
        text: The input text
        entities: The extracted entities
        config: Configuration dictionary with training data path
    """
    if config is None:
        from entityextractor.config.settings import DEFAULT_CONFIG
        config = DEFAULT_CONFIG
        
    training_data_path = config.get("TRAINING_DATA_PATH", "entity_extractor_training_data.jsonl")
    
    try:
        # Get system prompt based on language
        language = config.get("LANGUAGE", "de")
        system_prompt = ""
        
        if language == "en":
            system_prompt = "You are a helpful AI system for recognizing and linking entities. Your task is to identify the most important entities from a given text and link them to their Wikipedia pages."
        else:
            system_prompt = "Du bist ein hilfreiches KI-System zur Erkennung und Verknüpfung von Entitäten. Deine Aufgabe ist es, die wichtigsten Entitäten aus einem gegebenen Text zu identifizieren und mit ihren Wikipedia-Seiten zu verknüpfen."
        
        # Build semicolon-separated assistant content
        assistant_content = "\n".join(
            f"{ent['name']}; {ent['type']}; {ent.get('wikipedia_url','')}; {ent.get('citation','')}" for ent in entities
        )
        example = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Identify the main entities in the following text as semicolon-separated lines: name; type; wikipedia_url; citation. Text: {text}"},
                {"role": "assistant", "content": assistant_content}
            ]
        }
        
        # Speichere nur im OpenAI-Format
        training_data_path = config.get("OPENAI_TRAINING_DATA_PATH", "entity_extractor_openai_format.jsonl")  # Path to JSONL file for training data
        with open(training_data_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
            
        logging.info(f"Saved training example to {training_data_path}")
    except Exception as e:
        logging.error(f"Error saving training data: {e}")

def save_relationship_training_data(system_prompt, user_prompt, relationships, config=None):
    """
    Save training data for relationship inference.

    Args:
        system_prompt: The system prompt used for relation inference
        user_prompt: The user prompt used for relation inference
        relationships: List of relationship dicts
        config: Configuration dictionary
    """
    if config is None:
        from entityextractor.config.settings import DEFAULT_CONFIG
        config = DEFAULT_CONFIG
    training_data_path = config.get("OPENAI_RELATIONSHIP_TRAINING_DATA_PATH", "entity_relationship_training_data.jsonl")
    try:
        # Build semicolon-separated assistant content for relationships
        assistant_content = "\n".join(
            f"{rel['subject']}; {rel['predicate']}; {rel['object']}" for rel in relationships
        )
        example = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_content}
            ]
        }
        with open(training_data_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
        logging.info(f"Saved relationship training example to {training_data_path}")
    except Exception as e:
        logging.error(f"Error saving relationship training data: {e}")
