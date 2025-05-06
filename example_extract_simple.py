#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from entityextractor.core.api import process_entities
import json
import sys
import logging
sys.stdout.reconfigure(encoding='utf-8')

# Entitäten extrahieren und ausgeben
text = "Albert Einstein entwickelte die Relativitätstheorie."

# Vollständige JSON-Ausgabe
entities = process_entities(
    text,
    {
        # === LLM Provider Parameters ===
        "LLM_BASE_URL": "https://api.openai.com/v1",  # Base URL für LLM API
        "MODEL": "gpt-4.1-mini",   # LLM-Modell
        "OPENAI_API_KEY": None,    # API-Key aus Umgebungsvariable (None) oder Angabe
        "MAX_TOKENS": 16000,       # Maximale Tokenanzahl pro Anfrage
        "TEMPERATURE": 0.2,        # Sampling-Temperature

        # === Data Source Parameters ===
        "USE_WIKIPEDIA": True,     # Wikipedia-Verknüpfung aktivieren
        "USE_WIKIDATA": True,     # Wikidata-Verknüpfung aktivieren
        "USE_DBPEDIA": True,      # DBpedia-Verknüpfung aktivieren
        "DBPEDIA_USE_DE": False,   # Deutsche DBpedia nutzen
        "DBPEDIA_LOOKUP_API": True, # DBPedia Lookup API als Backup bei Verbindungsproblemen mit den Endpunkten
        "DBPEDIA_SKIP_SPARQL": False, # Skip DBPedia SPARQL
        "DBPEDIA_LOOKUP_FORMAT": "xml", # xml, json oder both
        "ADDITIONAL_DETAILS": False,  # Zusätzliche Entitätsdetails aus den Wissensquellen abrufen
        "TIMEOUT_THIRD_PARTY": 20,  # HTTP-Timeout für Drittanbieter

        # === ENTITY EXTRACTION PARAMETERS ===
        "MAX_ENTITIES": 10,         # Max. Anzahl Entitäten
        "ALLOWED_ENTITY_TYPES": "auto", # Entitätstypen automatisch filtern
        "MODE": "extract",         # Modus (extract, generate, compendium)
        "LANGUAGE": "de",          # Sprache (de, en)
        "SHOW_STATUS": True,       # Statusmeldungen anzeigen
        "ENABLE_ENTITY_INFERENCE": False, # Entity-Inferenz aktivieren

        # === RELATION PARAMETERS ===
        "RELATION_EXTRACTION": False,  # Relationsextraktion aktivieren
        "ENABLE_RELATIONS_INFERENCE": False,  # Implizite Relationen aktivieren

        # === OTHER SETTINGS ===
        "SUPPRESS_TLS_WARNINGS": True, # TLS-Warnungen unterdrücken
        "COLLECT_TRAINING_DATA": False, # Trainingsdaten sammeln

        # === TEXT CHUNKING FÜR LANGE TEXTE ===
        "TEXT_CHUNKING": False,    # Text-Chunking aktivieren
        "TEXT_CHUNK_SIZE": 2000,   # Chunk-Größe
        "TEXT_CHUNK_OVERLAP": 50,  # Chunk-Überlappung

        # === KNOWLEDGE GRAPH COMPLETION ===
        "ENABLE_KGC": False,       # Knowledge Graph Completion aktivieren
        "KGC_ROUNDS": 3,           # Anzahl KGC-Runden

        # === GRAPH-VISUALISIERUNG ===
        "ENABLE_GRAPH_VISUALIZATION": False    # Graph-Visualisierung aktivieren
    }
)

logging.info("Gebe finale Ergebnisse aus...")
print(json.dumps(entities, indent=2, ensure_ascii=False))
