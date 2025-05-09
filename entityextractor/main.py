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
from entityextractor.config.settings import get_config, DEFAULT_CONFIG
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
    parser.add_argument("--language", "-l", choices=["de", "en"], default=DEFAULT_CONFIG["LANGUAGE"],
                        help="Processing language (de or en)")
    parser.add_argument("--model", "-m", default=DEFAULT_CONFIG["MODEL"],
                        help="LLM model to use")
    parser.add_argument("--max-entities", type=int, default=DEFAULT_CONFIG["MAX_ENTITIES"],
                        help="Maximum number of entities to extract")
    parser.add_argument("--use-dbpedia", action="store_true",
                        help="Enable DBpedia integration")
    parser.add_argument("--dbpedia-use-de", action="store_true",
                        help="Use German DBpedia (if --use-dbpedia is enabled)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_CONFIG["TIMEOUT_THIRD_PARTY"],
                        help="Timeout (seconds) for external requests")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress status messages")
    parser.add_argument("--collect-training-data", action="store_true",
                        help="Collect training data for fine-tuning")
    parser.add_argument("--training-data-path", default=DEFAULT_CONFIG["OPENAI_TRAINING_DATA_PATH"],
                        help="Path for entity training data (JSONL)")
    parser.add_argument("--enable-compendium", action="store_true",
                        help="Enable compendium generation")
    parser.add_argument("--compendium-length", type=int, default=DEFAULT_CONFIG["COMPENDIUM_LENGTH"],
                        help="Length of generated compendium (chars)")
    parser.add_argument("--api-key", "-k", help="Override OpenAI API key or use environment variable")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_CONFIG["MAX_TOKENS"], help="Maximum tokens per LLM request")
    parser.add_argument("--temperature", type=float, default=DEFAULT_CONFIG["TEMPERATURE"],
                        help="LLM sampling temperature")
    parser.add_argument("--mode", choices=["extract","generate","compendium"], default="extract", help="Operation mode")
    parser.add_argument("--allowed-entity-types", default="auto", help="Allowed entity types filter")
    parser.add_argument("--enable-entity-inference", action="store_true", help="Enable implicit entity inference")
    parser.add_argument("--relation-extraction", action="store_true", help="Enable relation extraction")
    parser.add_argument("--enable-relations-inference", action="store_true", help="Enable implicit relations inference")
    parser.add_argument("--max-relations", type=int, default=DEFAULT_CONFIG["MAX_RELATIONS"], help="Maximum relations per prompt")
    parser.add_argument("--use-wikipedia", action="store_true", help="Enable Wikipedia linking")
    parser.add_argument("--use-wikidata", action="store_true", help="Enable Wikidata linking")
    parser.add_argument("--additional-details", action="store_true", help="Fetch additional details from knowledge sources")
    parser.add_argument("--text-chunking", action="store_true", help="Enable text chunking")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CONFIG["TEXT_CHUNK_SIZE"],
                        help="Chunk size for text splitting")
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CONFIG["TEXT_CHUNK_OVERLAP"],
                        help="Overlap between text chunks")
    parser.add_argument("--dbpedia-lookup-api", action="store_true", help="Enable DBpedia lookup API fallback")
    parser.add_argument("--dbpedia-skip-sparql", action="store_true", help="Skip DBpedia SPARQL queries")
    parser.add_argument("--dbpedia-lookup-max-hits", type=int, default=DEFAULT_CONFIG["DBPEDIA_LOOKUP_MAX_HITS"],
                        help="Max hits for DBpedia lookup API")
    parser.add_argument("--dbpedia-lookup-class", help="Optional DBpedia ontology class for lookup API")
    parser.add_argument("--dbpedia-lookup-format", choices=["json","xml","both"], default=DEFAULT_CONFIG["DBPEDIA_LOOKUP_FORMAT"],
                        help="DBpedia lookup response format")
    parser.add_argument("--enable-graph-visualization", action="store_true", help="Enable graph visualization")
    parser.add_argument("--enable-kgc", action="store_true", help="Enable knowledge graph completion")
    parser.add_argument("--kgc-rounds", type=int, default=DEFAULT_CONFIG["KGC_ROUNDS"],
                        help="Knowledge graph completion rounds")
    
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
        "OPENAI_TRAINING_DATA_PATH": args.training_data_path,
        "ENABLE_COMPENDIUM": args.enable_compendium,
        "COMPENDIUM_LENGTH": args.compendium_length,
        "OPENAI_API_KEY": args.api_key,
        "MAX_TOKENS": args.max_tokens,
        "TEMPERATURE": args.temperature,
        "MODE": args.mode,
        "ALLOWED_ENTITY_TYPES": args.allowed_entity_types,
        "ENABLE_ENTITY_INFERENCE": args.enable_entity_inference,
        "RELATION_EXTRACTION": args.relation_extraction,
        "ENABLE_RELATIONS_INFERENCE": args.enable_relations_inference,
        "MAX_RELATIONS": args.max_relations,
        "USE_WIKIPEDIA": args.use_wikipedia,
        "USE_WIKIDATA": args.use_wikidata,
        "ADDITIONAL_DETAILS": args.additional_details,
        "TEXT_CHUNKING": args.text_chunking,
        "TEXT_CHUNK_SIZE": args.chunk_size,
        "TEXT_CHUNK_OVERLAP": args.chunk_overlap,
        "DBPEDIA_LOOKUP_API": args.dbpedia_lookup_api,
        "DBPEDIA_SKIP_SPARQL": args.dbpedia_skip_sparql,
        "DBPEDIA_LOOKUP_MAX_HITS": args.dbpedia_lookup_max_hits,
        "DBPEDIA_LOOKUP_CLASS": args.dbpedia_lookup_class,
        "DBPEDIA_LOOKUP_FORMAT": args.dbpedia_lookup_format,
        "ENABLE_GRAPH_VISUALIZATION": args.enable_graph_visualization,
        "ENABLE_KGC": args.enable_kgc,
        "KGC_ROUNDS": args.kgc_rounds,
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
