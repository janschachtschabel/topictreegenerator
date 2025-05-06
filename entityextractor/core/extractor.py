"""
Entity extraction core functionality.

This module provides the main functions for extracting entities from text.
"""

import logging
import time

from entityextractor.config.settings import get_config
from entityextractor.services.openai_service import extract_entities_with_openai
from entityextractor.utils.logging_utils import configure_logging
from entityextractor.core.entity_inference import infer_entities

def extract_entities(text, user_config=None):
    """
    Extract entities from text using OpenAI.
    
    Args:
        text: The text to extract entities from
        user_config: Optional user configuration to override defaults
        
    Returns:
        A list of extracted entities
    """
    # Get configuration with user overrides
    config = get_config(user_config)
    
    # Configure logging
    configure_logging(config)
    
    # Extract entities
    start_time = time.time()
    logging.info("Starting entity extraction...")
    
    entities = extract_entities_with_openai(text, config)
    
    # Ergänze implizite Entitäten via ENABLE_ENTITY_INFERENCE
    entities = infer_entities(text, entities, config)
    
    elapsed_time = time.time() - start_time
    logging.info(f"Entity extraction completed in {elapsed_time:.2f} seconds")
    
    return entities
