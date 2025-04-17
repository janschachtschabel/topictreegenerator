"""
Hilfsfunktionen für den Themenbaum Generator.
"""
import json
import os
import time
import requests
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

import streamlit as st
from openai import OpenAI

# Konstanten
DATA_DIR = Path("data")

def get_openai_key() -> str:
    """Liest den OpenAI-API-Key aus den Umgebungsvariablen."""
    return os.getenv("OPENAI_API_KEY", "")

def save_json_with_timestamp(data: dict, prefix: str, suffix: str = "") -> str:
    """
    Speichert JSON-Daten mit Zeitstempel im data Ordner.
    
    Args:
        data: Zu speichernde JSON-Daten
        prefix: Prefix für den Dateinamen
        suffix: Suffix für den Dateinamen
        
    Returns: 
        str: Gespeicherter Dateipfad
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}{suffix}.json"
    filepath = DATA_DIR / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, ensure_ascii=False, indent=2, fp=f)
    
    return str(filepath)

def load_json_file(file_path: Path) -> dict:
    """
    Lädt eine JSON-Datei.
    
    Args:
        file_path: Pfad zur JSON-Datei
        
    Returns:
        dict: Geladene JSON-Daten
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_json_files() -> List[Path]:
    """
    Gibt eine Liste aller JSON-Dateien im data-Verzeichnis zurück.
    
    Returns:
        List[Path]: Liste der JSON-Dateien
    """
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(exist_ok=True)
        return []
    
    return sorted(
        [f for f in DATA_DIR.glob("*.json") if f.is_file()],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

def count_nodes(node: dict) -> int:
    """
    Zählt rekursiv alle Knoten in einem Baum.
    
    Args:
        node: Der zu zählende Knoten
        
    Returns:
        int: Anzahl der Knoten inklusive Unterknoten
    """
    if not isinstance(node, dict):
        return 0
    
    count = 1  # Aktueller Knoten
    
    if "subcollections" in node and isinstance(node["subcollections"], list):
        for subcollection in node["subcollections"]:
            count += count_nodes(subcollection)
    
    return count

def get_entity_extractor_config(openai_key: str, model: str = "gpt-4.1-mini", language: str = "de", 
                               use_wikidata: bool = True, use_dbpedia: bool = True, 
                               dbpedia_use_de: bool = True, show_status: bool = False) -> dict:
    """
    Erstellt eine Standardkonfiguration für den EntityExtractor basierend auf den UI-Einstellungen.
    
    Args:
        openai_key: OpenAI API-Key aus den Einstellungen
        model: LLM-Modell für die Entitätsextraktion
        language: Sprache für die Ergebnisse (de/en)
        use_wikidata: Wikidata API verwenden
        use_dbpedia: DBpedia API verwenden
        dbpedia_use_de: Deutsche DBpedia verwenden
        show_status: Status-Nachrichten anzeigen
        
    Returns:
        dict: Konfigurationsobjekt für den EntityExtractor
    """
    return {
        "USE_WIKIPEDIA": True,     # Immer True, Wikipedia ist Pflicht
        "USE_WIKIDATA": use_wikidata,
        "USE_DBPEDIA": use_dbpedia,
        "DBPEDIA_USE_DE": dbpedia_use_de,
        "DBPEDIA_TIMEOUT": 15,
        "MODEL": model,
        "OPENAI_API_KEY": openai_key,
        "LANGUAGE": language,
        "SHOW_STATUS": show_status,
        "SUPPRESS_TLS_WARNINGS": True,
        "COLLECT_TRAINING_DATA": False
    }
