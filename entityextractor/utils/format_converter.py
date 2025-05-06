"""
Format converter utilities for the Entity Extractor.

This module provides functions for converting between different output formats.
"""

def convert_to_legacy_format(result):
    """
    Convert the new entity format to the legacy format.
    
    Args:
        result: The result from extract_and_link_entities
        
    Returns:
        A list of entities in the legacy format
    """
    if not result or "entities" not in result:
        return []
        
    legacy_entities = []
    
    for entity in result["entities"]:
        legacy_entity = {
            "entity": entity.get("name", ""),
            "details": {
                "typ": entity.get("type", ""),
                "citation": result.get("text", ""),
                "citation_start": 0,
                "citation_end": len(result.get("text", ""))
            },
            "sources": {}
        }
        
        # Add Wikipedia source if available
        if "wikipedia_url" in entity:
            legacy_entity["sources"]["wikipedia"] = {
                "url": entity.get("wikipedia_url", "")
            }
            if "wikipedia_extract" in entity:
                legacy_entity["sources"]["wikipedia"]["extract"] = entity.get("wikipedia_extract", "")
        
        # Add Wikidata source if available
        if "wikidata_id" in entity:
            legacy_entity["sources"]["wikidata"] = {
                "id": entity.get("wikidata_id", "")
            }
            if "wikidata_description" in entity:
                legacy_entity["sources"]["wikidata"]["description"] = entity.get("wikidata_description", "")
            if "wikidata_types" in entity:
                legacy_entity["sources"]["wikidata"]["types"] = entity.get("wikidata_types", [])
        
        # Add DBpedia source if available
        if "dbpedia_uri" in entity:
            legacy_entity["sources"]["dbpedia"] = {
                "resource_uri": entity.get("dbpedia_uri", "")
            }
            if "dbpedia_language" in entity:
                legacy_entity["sources"]["dbpedia"]["language"] = entity.get("dbpedia_language", "")
            if "dbpedia_abstract" in entity:
                legacy_entity["sources"]["dbpedia"]["abstract"] = entity.get("dbpedia_abstract", "")
            if "dbpedia_types" in entity:
                legacy_entity["sources"]["dbpedia"]["types"] = entity.get("dbpedia_types", [])
        
        legacy_entities.append(legacy_entity)
    
    return legacy_entities
