"""
api.py

Stub that delegates the main entry point to orchestrator.process_entities.
"""

from entityextractor.core.orchestrator import process_entities

extract_and_link_entities = process_entities

__all__ = ["process_entities", "extract_and_link_entities"]
