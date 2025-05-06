"""
Entity linking core functionality.

This module provides the main functions for linking entities to knowledge bases
like Wikipedia, Wikidata, and DBpedia.
"""

import logging
import time
import re
import urllib.parse

from entityextractor.utils.text_utils import is_valid_wikipedia_url

from entityextractor.config.settings import get_config
from entityextractor.services.wikipedia_service import (
    fallback_wikipedia_url,
    get_wikipedia_extract,
    convert_to_de_wikipedia_url,
    follow_wikipedia_redirect,
    get_wikipedia_details,
    get_wikipedia_categories
)
from entityextractor.services.wikidata_service import (
    get_wikidata_id_from_wikipedia_url,
    get_wikidata_details
)
from entityextractor.services.dbpedia_service import get_dbpedia_info_from_wikipedia_url
from entityextractor.utils.logging_utils import configure_logging
from entityextractor.utils.text_utils import strip_trailing_ellipsis

def link_entities(entities, text=None, user_config=None):
    """
    Link extracted entities to Wikipedia, Wikidata, and DBpedia.
    
    Args:
        entities: List of extracted entities
        text: Original text (optional, for context)
        user_config: Optional user configuration to override defaults
        
    Returns:
        A list of entities with knowledge base links
    """
    # Get configuration with user overrides
    config = get_config(user_config)
    
    # Configure logging
    configure_logging(config)
    
    # Link entities
    start_time = time.time()
    logging.info("Starting entity linking...")
    
    linked_entities = []
    
    for entity in entities:
        entity_name = entity.get("name", "")
        if not entity_name:
            continue
            
        linked_entity = entity.copy()
        
        # Step 1: Wikipedia-URL bestimmen
        wikipedia_url = None
        llm_generated_url = entity.get("wikipedia_url", None)

        # 1. LLM-URL direkt nutzen, falls gültig
        if llm_generated_url and is_valid_wikipedia_url(llm_generated_url):
            logging.info(f"Using LLM-generated Wikipedia URL for '{entity_name}': {llm_generated_url}")
            wikipedia_url = llm_generated_url
        else:
            # 2. Fallback nur wenn LLM-URL fehlt/ungültig
            if llm_generated_url:
                logging.info(f"LLM-generated URL invalid or incomplete: '{llm_generated_url}'. Using fallback.")
            wikipedia_url = fallback_wikipedia_url(entity_name, language=config.get("LANGUAGE", "de"))

        if wikipedia_url:
            linked_entity["wikipedia_url"] = wikipedia_url

            # Step 2: Wikipedia-Extract versuchen (ohne Redirect-Check/Opensearch)
            extract, wiki_id = get_wikipedia_extract(wikipedia_url, config)
            if extract:
                linked_entity["wikipedia_extract"] = strip_trailing_ellipsis(extract)
                # Wenn MediaWiki API die Wikidata-ID liefert, setzen und späteren Abruf überspringen
                if wiki_id:
                    linked_entity["wikidata_id"] = wiki_id
                    # Soft-Redirect überspringen, da alle Daten bereits abgerufen wurden
                    linked_entity["wikipedia_title"] = entity_name
            else:
                # 3. Nur wenn kein Extract: Redirect prüfen und Fallback nutzen
                logging.info(f"No extract found for '{entity_name}' (URL: {wikipedia_url}). Trying redirect/fallback...")
                final_url, page_title = follow_wikipedia_redirect(wikipedia_url, entity_name)
                if final_url and final_url != wikipedia_url:
                    logging.info(f"Redirect detected: {wikipedia_url} -> {final_url}")
                    linked_entity["wikipedia_url"] = final_url
                    wikipedia_url = final_url
                if page_title:
                    linked_entity["wikipedia_title"] = page_title
                    entity_name = page_title
                # Nochmals Extract versuchen
                extract, wiki_id = get_wikipedia_extract(wikipedia_url, config)
                if not extract:
                    # 4. Letzter Fallback: Opensearch explizit
                    fallback_url = fallback_wikipedia_url(entity_name, language=config.get("LANGUAGE", "de"))
                    if fallback_url and fallback_url != wikipedia_url:
                        logging.info(f"Using fallback URL from Opensearch: {fallback_url} for '{entity_name}'")
                        linked_entity["wikipedia_url"] = fallback_url
                        wikipedia_url = fallback_url
                        # Update entity_name and wikipedia_title based on fallback URL
                        try:
                            fb_title = urllib.parse.unquote(fallback_url.split("/wiki/")[1].split("#")[0])
                            linked_entity["wikipedia_title"] = fb_title
                            entity_name = fb_title
                        except Exception as e:
                            logging.warning(f"Failed parsing fallback title from URL {fallback_url}: {e}")
                        extract, wiki_id = get_wikipedia_extract(wikipedia_url, config)
                if extract:
                    linked_entity["wikipedia_extract"] = strip_trailing_ellipsis(extract)
                    # Wenn MediaWiki API die Wikidata-ID liefert, setzen und späteren Abruf überspringen
                    if wiki_id:
                        linked_entity["wikidata_id"] = wiki_id

            # Wikipedia-Kategorien nur, wenn ein Extract gefunden wurde
            if linked_entity.get("wikipedia_extract"):
                cats = get_wikipedia_categories(linked_entity["wikipedia_url"], config)
                if cats:
                    linked_entity["wikipedia_categories"] = cats

            # Zusätzliche Details nur, wenn ein Extract gefunden wurde
            if config.get("ADDITIONAL_DETAILS", False) and linked_entity.get("wikipedia_extract"):
                wiki_details = get_wikipedia_details(linked_entity["wikipedia_url"], config)
                if wiki_details:

                    linked_entity["wikipedia_details"] = wiki_details
            
            # Step 5: Wikidata ID und Details (intelligent: Details auch bei Extract-ID, Fallback falls nötig)
            if config.get("USE_WIKIDATA", True):
                # ID aus Extract übernehmen oder per Fallback suchen
                if linked_entity.get("wikidata_id"):
                    wikidata_id = linked_entity["wikidata_id"]
                else:
                    wikidata_id = get_wikidata_id_from_wikipedia_url(
                        linked_entity["wikipedia_url"],
                        entity_name=entity_name,
                        config=config
                    )
                    if wikidata_id:
                        linked_entity["wikidata_id"] = wikidata_id
                # Details nur abrufen, wenn ID vorhanden ist
                if linked_entity.get("wikidata_id"):
                    wikidata_details = get_wikidata_details(
                        linked_entity["wikidata_id"],
                        language=config.get("LANGUAGE", "de"),
                        config=config
                    )
                    if wikidata_details:
                        linked_entity["wikidata_url"] = f"https://www.wikidata.org/wiki/{linked_entity['wikidata_id']}"
                        # Basisfelder
                        for field in ("description","label","types","subclasses"):
                            if field in wikidata_details:
                                linked_entity[f"wikidata_{field}"] = wikidata_details[field]
                        # Relationen P361, P527, P463
                        for rel in ("part_of","has_parts","member_of"):
                            if rel in wikidata_details:
                                linked_entity[rel] = wikidata_details.get(rel, [])
                        # Zusätzliche Details optional
                        if config.get("ADDITIONAL_DETAILS", False):
                            for field in ("image_url","website","coordinates","foundation_date","birth_date","death_date","occupations"):
                                if field in wikidata_details:
                                    linked_entity[field] = wikidata_details[field]
                        linked_entity["wikidata_details"] = wikidata_details
            
            # Step 6: Get DBpedia information
            if config.get("USE_DBPEDIA", False):
                dbpedia_info = get_dbpedia_info_from_wikipedia_url(linked_entity["wikipedia_url"], config)
                if dbpedia_info:
                    # Store the complete DBpedia info object
                    linked_entity["dbpedia_info"] = dbpedia_info
                    
                    # Also store the title if available
                    if "dbpedia_title" in dbpedia_info:
                        linked_entity["dbpedia_title"] = dbpedia_info["dbpedia_title"]
                    elif "title" in dbpedia_info:
                        linked_entity["dbpedia_title"] = dbpedia_info["title"]
                        
                    # For backward compatibility, also store individual fields
                    if "resource_uri" in dbpedia_info:
                        linked_entity["dbpedia_uri"] = dbpedia_info["resource_uri"]
                    elif "uri" in dbpedia_info:
                        linked_entity["dbpedia_uri"] = dbpedia_info["uri"]
                        
                    # Add abstract if available
                    if "abstract" in dbpedia_info:
                        linked_entity["dbpedia_abstract"] = dbpedia_info["abstract"]
                        
                    # Add types if available
                    if "types" in dbpedia_info:
                        linked_entity["dbpedia_types"] = dbpedia_info["types"]
                        
                    # Add DBpedia relations if available
                    if "part_of" in dbpedia_info:
                        linked_entity["dbpedia_part_of"] = dbpedia_info["part_of"]
                    if "has_parts" in dbpedia_info:
                        linked_entity["dbpedia_has_parts"] = dbpedia_info["has_parts"]
                    if "member_of" in dbpedia_info:
                        linked_entity["dbpedia_member_of"] = dbpedia_info["member_of"]
                        
                    # Add language information
                    if "language" in dbpedia_info:
                        linked_entity["dbpedia_language"] = dbpedia_info["language"]
                    
                    # Additional DBpedia details
                    if config.get("ADDITIONAL_DETAILS", False):
                        linked_entity["dbpedia_details"] = dbpedia_info
                else:
                    # Fallback: minimale DBpedia-URI bei Fehlern
                    title = linked_entity["wikipedia_url"].rsplit("/", 1)[-1]
                    if config.get("DBPEDIA_USE_DE", False):
                        prefix = "http://de.dbpedia.org/resource/"
                        lang = "de"
                    else:
                        prefix = "http://dbpedia.org/resource/"
                        lang = "en"
                    linked_entity["dbpedia_uri"] = prefix + title
                    linked_entity["dbpedia_language"] = lang
        
        linked_entities.append(linked_entity)
    
    elapsed_time = time.time() - start_time
    logging.info(f"Entity linking completed in {elapsed_time:.2f} seconds")
    
    return linked_entities
