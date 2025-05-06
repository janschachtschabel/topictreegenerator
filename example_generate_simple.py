#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Minimalbeispiel für die Generierung von Entitäten zu einem Thema
from entityextractor.core.api import process_entities
import json
import sys
import logging

sys.stdout.reconfigure(encoding='utf-8')

# Thema zu dem Entitäten generiert werden
topic = "Quantenphysik"

config = {
    # === LLM Provider Parameters ===
    "LLM_BASE_URL": "https://api.openai.com/v1",  # Base URL für LLM API
    "MODEL": "gpt-4.1-mini",   # LLM-Modell
    "OPENAI_API_KEY": None,    # API-Key aus Umgebungsvariable (None) oder Angabe
    "MAX_TOKENS": 16000,       # Maximale Tokenanzahl pro Anfrage
    "TEMPERATURE": 0.2,        # Sampling-Temperature

    # === DATA SOURCE PARAMETERS ===
    "USE_WIKIPEDIA": True,     # Wikipedia-Verknüpfung aktivieren
    "USE_WIKIDATA": True,     # Wikidata-Verknüpfung aktivieren
    "USE_DBPEDIA": True,      # DBpedia-Verknüpfung aktivieren
    "DBPEDIA_USE_DE": False,   # Deutsche DBpedia nutzen
    "DBPEDIA_LOOKUP_API": True, # DBPedia Lookup API als Backup bei Verbindungsproblemen mit den Endpunkten
    "DBPEDIA_SKIP_SPARQL": False, # Skip DBPedia SPARQL
    "DBPEDIA_LOOKUP_FORMAT": "xml", # xml, json oder both
    "ADDITIONAL_DETAILS": False,  # Zusätzliche Entitätsdetails abrufen
    "TIMEOUT_THIRD_PARTY": 20,  # HTTP-Timeout für Drittanbieter

    # === ENTITY EXTRACTION PARAMETERS ===
    "MAX_ENTITIES": 10,         # Max. Anzahl Entitäten
    "ALLOWED_ENTITY_TYPES": "auto", # Entitätstypen automatisch filtern
    "MODE": "compendium",     # Modus (extract, generate, compendium)
    "LANGUAGE": "de",         # Sprache (de, en)
    "SHOW_STATUS": True,       # Statusmeldungen anzeigen
    "ENABLE_ENTITY_INFERENCE": False, # Entity-Inferenz aktivieren

    # === RELATION PARAMETERS ===
    "RELATION_EXTRACTION": True,  # Relationsextraktion aktivieren
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
    "ENABLE_GRAPH_VISUALIZATION": True    # Graph-Visualisierung aktivieren
}

result = process_entities(topic, config)
if isinstance(result, dict) and "entities" in result:
    entities = result["entities"]
else:
    entities = result

logging.info("Gebe finale Ergebnisse aus...")
print(json.dumps(entities, indent=2, ensure_ascii=False))

print("\nBeziehungen zwischen Entitäten:")
if isinstance(result, dict) and "relationships" in result:
    print(json.dumps(result["relationships"], indent=2, ensure_ascii=False))
else:
    print("Keine Beziehungen gefunden.")
