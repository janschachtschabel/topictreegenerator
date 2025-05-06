"""
extract_api.py

Provides a unified function to extract entities and link them to knowledge bases.
"""

import logging
from entityextractor.core.extractor import extract_entities
from entityextractor.core.linker import link_entities


def extract_and_link(text: str, config: dict) -> list:
    """
    Extract entities from text and link them to knowledge bases.

    Args:
        text: The input text to process
        config: Configuration dict

    Returns:
        List of linked entities
    """
    logging.info("[extract_api] Starting extraction and linking...")
    entities = extract_entities(text, config)
    logging.info(f"[extract_api] Extracted {len(entities)} entities")
    linked = link_entities(entities, text, config)
    logging.info(f"[extract_api] Linked {len(linked)} entities")
    return linked
