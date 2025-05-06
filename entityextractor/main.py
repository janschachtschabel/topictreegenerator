"""
Main module for the Entity Extractor.

This module provides the main entry points for the Entity Extractor application,
including command-line interface and example usage.
"""

import argparse
import json
import logging
import os
import sys
import time

from entityextractor.core.api import extract_and_link_entities
from entityextractor.config.settings import get_config
from entityextractor.utils.logging_utils import configure_logging

def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Extract and link entities from text.")
    parser.add_argument("--text", "-t", help="Text to extract entities from")
    parser.add_argument("--file", "-f", help="File containing text to extract entities from")
    parser.add_argument("--output", "-o", help="Output file for results (JSON format)")
    parser.add_argument("--language", "-l", choices=["de", "en"], default="de", 
                        help="Language for entity extraction (de or en)")
    parser.add_argument("--model", "-m", default="gpt-4o-mini",
                        help="OpenAI model to use for entity extraction")
    parser.add_argument("--max-entities", type=int, default=10,
                        help="Maximum number of entities to extract")
    parser.add_argument("--use-dbpedia", action="store_true",
                        help="Enable DBpedia integration")
    parser.add_argument("--dbpedia-use-de", action="store_true",
                        help="Use German DBpedia (if --use-dbpedia is enabled)")
    parser.add_argument("--timeout", type=int, default=15,
                        help="Timeout in seconds for third-party requests")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress status messages")
    parser.add_argument("--collect-training-data", action="store_true",
                        help="Collect training data for fine-tuning")
    parser.add_argument("--training-data-path", default="entity_extractor_training_data.jsonl",
                        help="Path to JSONL file for training data")
    
    return parser.parse_args()

def main():
    """
    Main entry point for the command-line interface.
    """
    args = parse_arguments()
    
    # Get text from argument or file
    text = None
    if args.text:
        text = args.text
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return 1
    else:
        print("No text provided. Use --text or --file.")
        return 1
    
    # Create configuration from arguments
    config = {
        "LANGUAGE": args.language,
        "MODEL": args.model,
        "MAX_ENTITIES": args.max_entities,
        "USE_DBPEDIA": args.use_dbpedia,
        "DBPEDIA_USE_DE": args.dbpedia_use_de,
        "TIMEOUT_THIRD_PARTY": args.timeout,
        "SHOW_STATUS": not args.quiet,
        "COLLECT_TRAINING_DATA": args.collect_training_data,
        "TRAINING_DATA_PATH": args.training_data_path
    }
    
    # Extract and link entities
    result = extract_and_link_entities(text, config)
    
    # Output results
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Results written to {args.output}")
        except Exception as e:
            print(f"Error writing output file: {e}")
            return 1
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return 0

def example():
    """
    Example usage of the Entity Extractor.
    """
    # Example text
    text = """
    Die Relativitätstheorie ist eine von Albert Einstein entwickelte physikalische Theorie.
    Sie revolutionierte das Verständnis von Raum, Zeit und Gravitation.
    Einstein wurde in Ulm geboren und erhielt 1921 den Nobelpreis für Physik.
    """
    
    # Configuration
    config = {
        "LANGUAGE": "de",
        "MODEL": "gpt-4o-mini",
        "MAX_ENTITIES": 5,
        "USE_WIKIPEDIA": True,
        "USE_WIKIDATA": True,
        "USE_DBPEDIA": False,
        "TIMEOUT_THIRD_PARTY": 15,
        "SHOW_STATUS": True
    }
    
    # Extract and link entities
    result = extract_and_link_entities(text, config)
    
    # Print results
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    sys.exit(main())
