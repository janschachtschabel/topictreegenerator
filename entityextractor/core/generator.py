"""
Entity generation core functionality.

This module provides functions for generating entities related to a specific topic
to create a comprehensive knowledge compendium.
"""

import logging
import time
import json

from openai import OpenAI
from entityextractor.config.settings import get_config, DEFAULT_CONFIG
from entityextractor.utils.logging_utils import configure_logging
from entityextractor.utils.text_utils import clean_json_from_markdown
from entityextractor.services.openai_service import save_training_data as save_extraction_training_data
from entityextractor.core.entity_inference import infer_entities
from entityextractor.prompts.generation_prompts import (
    get_system_prompt_compendium_en,
    get_user_prompt_compendium_en,
    get_system_prompt_compendium_de,
    get_user_prompt_compendium_de,
    get_system_prompt_generate_en,
    get_user_prompt_generate_en,
    get_system_prompt_generate_de,
    get_user_prompt_generate_de,
)
from entityextractor.utils.prompt_utils import apply_type_restrictions

def save_training_data(topic, entities, config=None):
    """
    Save training data for future fine-tuning in generation mode.
    
    Args:
        topic: The input topic
        entities: The generated entities
        config: Configuration dictionary with training data path
    """
    if config is None:
        config = DEFAULT_CONFIG
        
    # Gemeinsame JSONL für alle Entity-Modi
    training_data_path = config.get("OPENAI_TRAINING_DATA_PATH", DEFAULT_CONFIG["OPENAI_TRAINING_DATA_PATH"])
    
    try:
        # Determine prompts from centralized generation_prompts module
        language = config.get("LANGUAGE", "de")
        mode = config.get("MODE", "")
        max_entities = config.get("MAX_ENTITIES", 10)
        if mode == "compendium":
            if language == "en":
                system_prompt = get_system_prompt_compendium_en(max_entities, topic)
                user_prompt = get_user_prompt_compendium_en(max_entities, topic)
            else:
                system_prompt = get_system_prompt_compendium_de(max_entities, topic)
                user_prompt = get_user_prompt_compendium_de(max_entities, topic)
        else:
            if language == "en":
                system_prompt = get_system_prompt_generate_en(max_entities, topic)
                user_prompt = get_user_prompt_generate_en(max_entities, topic)
            else:
                system_prompt = get_system_prompt_generate_de(max_entities, topic)
                user_prompt = get_user_prompt_generate_de(max_entities, topic)
        
        # Build semicolon-separated assistant content for training
        assistant_content = "\n".join(
            f"{ent['name']}; {ent['type']}; {ent.get('wikipedia_url','')}; {ent.get('citation','')}" for ent in entities
        )
        example = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate entities for topic '{topic}' as semicolon-separated lines: name; type; wikipedia_url; citation."},
                {"role": "assistant", "content": assistant_content}
            ]
        }
        
        # Ensure each entity has an 'inferred' field
        mode = config.get("MODE", "")
        for ent in entities:
            if "inferred" not in ent:
                ent["inferred"] = "implicit" if mode in ("generate", "compendium") else "explicit"
        
        # Append to the JSONL file
        with open(training_data_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
            
        logging.info(f"Saved generation training example to {training_data_path}")
    except Exception as e:
        logging.error(f"Error saving generation training data: {e}")

def generate_entities(topic, user_config=None):
    """
    Generate entities related to a specific topic.
    
    Args:
        topic: The topic to generate entities for
        user_config: Optional user configuration to override defaults
        
    Returns:
        A list of generated entities
    """
    # Get configuration with user overrides
    config = get_config(user_config)
    
    # Configure logging
    configure_logging(config)
    
    # Start timing
    start_time = time.time()
    logging.info(f"Starting entity generation for topic: {topic}")
    
    # Get OpenAI API key
    api_key = config.get("OPENAI_API_KEY")
    if not api_key:
        import os
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logging.error("No OpenAI API key provided")
            return []
    
    # Create OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Get model and max entities
    model = config.get("MODEL", "gpt-4.1-mini")
    max_entities = config.get("MAX_ENTITIES", 10)
    language = config.get("LANGUAGE", "de")
    
    # Get allowed entity types if specified
    allowed_entity_types = config.get("ALLOWED_ENTITY_TYPES", "auto")
    
    # Prompt preparation using centralized prompt functions
    mode = config.get("MODE", "extract")
    if mode == "compendium":
        if language == "de":
            system_prompt = get_system_prompt_compendium_de(max_entities, topic)
            user_msg = get_user_prompt_compendium_de(max_entities, topic)
        else:
            system_prompt = get_system_prompt_compendium_en(max_entities, topic)
            user_msg = get_user_prompt_compendium_en(max_entities, topic)
    else:
        # Default generate mode
        if language == "de":
            system_prompt = get_system_prompt_generate_de(max_entities, topic)
            user_msg = get_user_prompt_generate_de(max_entities, topic)
        else:
            system_prompt = get_system_prompt_generate_en(max_entities, topic)
            user_msg = get_user_prompt_generate_en(max_entities, topic)
    
    # Apply unified entity type restriction
    system_prompt = apply_type_restrictions(system_prompt, allowed_entity_types, language)
    
    try:
        # Log the model being used
        logging.info(f"Generating entities with OpenAI model {model}...")
        logging.debug(f"[GENERATION] SYSTEM PROMPT:\n{system_prompt}")
        logging.debug(f"[GENERATION] USER MSG:\n{user_msg}")
        generation_start_time = time.time()
        
        # Make the API call
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.7  # Higher temperature for more creative generation
        )
        
        # Log the HTTP response
        generation_time = time.time() - generation_start_time
        logging.info(f"HTTP Request: POST https://api.openai.com/v1/chat/completions \"HTTP/1.1 200 OK\"")
        logging.info(f"Generation API call completed in {generation_time:.2f} seconds")
        
        # Process the response
        if not response.choices or not response.choices[0].message.content:
            logging.error("Empty response from OpenAI API")
            return []
        
        # Parse semicolon-separated entity lines
        raw_output = response.choices[0].message.content.strip()
        lines = raw_output.splitlines()
        processed_entities = []
        for ln in lines:
            parts = [p.strip() for p in ln.split(';')]
            if len(parts) >= 4:
                name, typ, url, citation = parts[:4]
                processed_entities.append({
                    'name': name,
                    'type': typ,
                    'wikipedia_url': url,
                    'citation': citation,
                    'inferred': 'implicit'
                })
        elapsed_time = time.time() - generation_start_time
        logging.info(f"Generated {len(processed_entities)} entities in {elapsed_time:.2f} seconds")
        # Save training data if enabled
        if config.get('COLLECT_TRAINING_DATA', False):
            save_training_data(topic, processed_entities, config)
        # Optional entity inference
        if config.get('ENABLE_ENTITY_INFERENCE', False):
            processed_entities = infer_entities(topic, processed_entities, config)
        # Add 'sources' field
        for pe in processed_entities:
            pe['sources'] = {}
        return processed_entities
    except Exception as e:
        logging.error(f"Error generating entities: {e}")
        return []
