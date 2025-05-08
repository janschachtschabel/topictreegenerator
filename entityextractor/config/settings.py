"""
Default configuration settings for the Entity Extractor.

This module defines the default configuration settings used throughout
the application. These settings can be overridden by providing a custom
configuration dictionary when calling the entity extraction functions.
"""

import os

# Default configuration for entity extraction
DEFAULT_CONFIG = {
    # === LLM PROVIDER SETTINGS ===
    "LLM_BASE_URL": "https://api.openai.com/v1",  # BASE URL FÜR LLM API
    "MODEL": "gpt-4.1-mini",                     # LLM-MODELL
    "OPENAI_API_KEY": None,                      # API-KEY AUS UMGEBUNGSVARIABLE
    "MAX_TOKENS": 16000,                         # MAXIMALE TOKENANZAHL PRO ANFRAGE
    "TEMPERATURE": 0.2,                          # SAMPLING-TEMPERATURE

    # === CORE DATA SOURCE SETTINGS ===
    "USE_WIKIPEDIA": True,      # WIKIPEDIA-VERKNÜPFUNG AKTIVIEREN (IMMER TRUE)
    "USE_WIKIDATA": False,       # WIKIDATA-VERKNÜPFUNG AKTIVIEREN
    "USE_DBPEDIA": False,        # DBPEDIA-VERKNÜPFUNG AKTIVIEREN
    "ADDITIONAL_DETAILS": False,   # Abruf zusätzlicher Details aus den Wissensquellen aktivieren
    "DBPEDIA_USE_DE": False,    # DEUTSCHE DBPEDIA NUTZEN (STANDARD: FALSE = ENGLISCHE DBPEDIA)

    # === DBpedia Lookup API Fallback ===
    "DBPEDIA_LOOKUP_API": True,      # Fallback via DBpedia Lookup API aktivieren
    "DBPEDIA_SKIP_SPARQL": False,      # Skip SPARQL queries and use Lookup API only
    "DBPEDIA_LOOKUP_MAX_HITS": 5,     # Max. Trefferzahl für Lookup API
    "DBPEDIA_LOOKUP_CLASS": None,     # Optionale DBpedia-Ontology-Klasse für Lookup API
    "DBPEDIA_LOOKUP_FORMAT": "xml",   # Response format: "json", "xml", or "both"

    # === LANGUAGE SETTINGS ===
    "LANGUAGE": "en",           # SPRACHE DER VERARBEITUNG (DE ODER EN)

    # === TEXT PROCESSING SETTINGS ===
    "TEXT_CHUNKING": False,     # TEXT-CHUNKING AKTIVIEREN
    "TEXT_CHUNK_SIZE": 2000,    # CHUNK-GRÖSSE IN ZEICHEN
    "TEXT_CHUNK_OVERLAP": 50,   # ÜBERLAPPUNG ZWISCHEN CHUNKS

    # === ENTITY EXTRACTION SETTINGS ===
    "MODE": "extract",               # MODUS: EXTRACT, GENERATE, COMPENDIUM
    "MAX_ENTITIES": 20,              # MAXIMALE ANZAHL EXTRAHIERTER ENTITÄTEN
    "ALLOWED_ENTITY_TYPES": "auto",  # AUTOMATISCHE FILTERUNG ERLAUBTER ENTITÄTSTYPEN
    "ENABLE_ENTITY_INFERENCE": False, # IMPLIZITE ENTITÄTSEKENNUNG AKTIVIEREN

    # === RELATIONSHIP EXTRACTION AND INFERENCE ===
    "RELATION_EXTRACTION": True,         # RELATIONSEXTRACTION AKTIVIEREN
    "ENABLE_RELATIONS_INFERENCE": False,  # IMPLIZITE RELATIONEN AKTIVIEREN
    "MAX_RELATIONS": 20,                  # MAXIMALE ANZAHL BEZIEHUNGEN PRO PROMPT

    # === KNOWLEDGE GRAPH COMPLETION (KGC) ===
    "ENABLE_KGC": False,   # KNOWLEDGE GRAPH COMPLETION AKTIVIEREN
    "KGC_ROUNDS": 3,       # ANZAHL DER KGC-RUNDEN

    # === TRAINING DATA COLLECTION SETTINGS ===
    "COLLECT_TRAINING_DATA": False,  # TRAININGSDATEN FÜR FINE-TUNING SAMMELN
    "OPENAI_TRAINING_DATA_PATH": "entity_extractor_training_openai.jsonl",  # PFAD FÜR ENTITÄTS-TRAININGSDATEN
    "OPENAI_RELATIONSHIP_TRAINING_DATA_PATH": "entity_relationship_training_openai.jsonl",  # PFAD FÜR BEZIEHUNGS-TRAININGSDATEN

    # === API AND TIMEOUT SETTINGS ===
    "TIMEOUT_THIRD_PARTY": 15,  # TIMEOUT FÜR EXTERNE DIENSTE (WIKIPEDIA, WIKIDATA, DBPEDIA)

    # === RATE LIMITER SETTINGS ===
    "RATE_LIMIT_MAX_CALLS": 3,       # Max Aufrufe pro Zeitraum
    "RATE_LIMIT_PERIOD": 1,          # Zeitraum in Sekunden
    "RATE_LIMIT_BACKOFF_BASE": 1,    # Basis für exponentielles Backoff
    "RATE_LIMIT_BACKOFF_MAX": 60,    # Max Wartezeit bei Backoff
    "USER_AGENT": "EntityExtractor/1.0", # HTTP User-Agent Header
    "WIKIPEDIA_MAXLAG": 5,           # maxlag-Parameter für Wikipedia API

    # === LOGGING AND DEBUG SETTINGS ===
    "SHOW_STATUS": True,        # STATUSMELDUNGEN ANZEIGEN
    "SUPPRESS_TLS_WARNINGS": True,  # TLS-WARNUNGEN UNTERDRÜCKEN

    # === GRAPH VISUALIZATION SETTINGS ===
    "ENABLE_GRAPH_VISUALIZATION": False,  # Aktiviert statisches PNG und interaktive HTML-Ansicht (benötigt RELATION_EXTRACTION=True)

    # === STATISCHES GRAPH mit NetworkX-Layouts (PNG) ===
    "GRAPH_LAYOUT_METHOD": "spring",  # Layout: "kamada_kawai" (ohne K-/Iter-Param) oder "spring" (Fruchterman-Reingold)
    "GRAPH_LAYOUT_K": None,                   # (Spring-Layout) ideale Kantenlänge (None=Default)
    "GRAPH_LAYOUT_ITERATIONS": 50,            # (Spring-Layout) Iterationen
    "GRAPH_PHYSICS_PREVENT_OVERLAP": True,    # (Spring-Layout) Überlappungsprävention aktivieren
    "GRAPH_PHYSICS_PREVENT_OVERLAP_DISTANCE": 0.1,  # (Spring-Layout) Mindestabstand zwischen Knoten
    "GRAPH_PHYSICS_PREVENT_OVERLAP_ITERATIONS": 50, # (Spring-Layout) Iterationen Overlap-Prevention
    "GRAPH_PNG_SCALE": 0.30,             # Skalierungsfaktor für statisches PNG-Layout (Standard 0.33)

    # === INTERAKTIVES GRAPH mit PyVis (HTML) ===
    "GRAPH_HTML_INITIAL_SCALE": 10,           # Anfangs-Zoom (network.moveTo scale): >1 rauszoomen, <1 reinzoomen

    # === CACHING SETTINGS ===
    "CACHE_ENABLED": True,   # Enable or disable caching globally
    "CACHE_DIR": os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache"),    # Directory for cache files inside the package (create if missing)
    "CACHE_DBPEDIA_ENABLED": True,              # Enable caching for DBpedia SPARQL queries
    "CACHE_WIKIDATA_ENABLED": True,             # (Optional) Enable caching for Wikidata API
    "CACHE_WIKIPEDIA_ENABLED": True             # (Optional) Enable caching for Wikipedia API requests
}

def get_config(user_config=None):
    """
    Get a configuration dictionary with user overrides applied.
    
    Args:
        user_config: Optional user configuration dictionary to override defaults
        
    Returns:
        A configuration dictionary with user overrides applied to defaults
    """
    config = DEFAULT_CONFIG.copy()
    
    if user_config:
        config.update(user_config)
        
    # If API key is not provided, try to get it from environment
    if not config.get("OPENAI_API_KEY"):
        config["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
        
    return config
