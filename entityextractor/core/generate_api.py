"""
generate_api.py

Provides unified function to generate entities and link them to knowledge bases.
"""

import logging
from entityextractor.core.generator import generate_entities
from entityextractor.core.linker import link_entities


def generate_and_link(topic: str, config: dict) -> list:
    """
    Generate entities for a given topic and link them to knowledge bases.

    Args:
        topic: The subject/topic to generate entities for
        config: Configuration dict

    Returns:
        List of linked entities
    """
    logging.info(f"[generate_api] Starting generation for topic: {topic}")
    entities = generate_entities(topic, config)
    logging.info(f"[generate_api] Generated {len(entities)} entities")
    linked = link_entities(entities, topic, config)
    logging.info(f"[generate_api] Linked {len(linked)} entities")
    return linked
