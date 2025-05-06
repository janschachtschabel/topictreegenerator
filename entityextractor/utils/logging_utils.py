"""
Logging utilities for the Entity Extractor.

This module provides functions for configuring and managing logging
throughout the application.
"""

import logging
import urllib3

def configure_logging(config=None):
    """
    Configure logging based on configuration settings.
    
    Args:
        config: Configuration dictionary with logging settings
    """
    from entityextractor.config.settings import DEFAULT_CONFIG
    
    if config is None:
        config = DEFAULT_CONFIG
        
    # Default logging configuration
    logging_level = logging.INFO if config.get("SHOW_STATUS", True) else logging.ERROR
    
    # Reset handlers to avoid duplications
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configure formatting
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # Handler for console output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.root.setLevel(logging_level)
    logging.root.addHandler(console_handler)
    
    # Suppress SSL warnings (if configured)
    if config.get("SUPPRESS_TLS_WARNINGS", True):
        logging.captureWarnings(True)
        urllib3.disable_warnings()
        
    # Suppress JSON parsing messages (limit to critical errors)
    logging.getLogger('json.decoder').setLevel(logging.CRITICAL)
    logging.getLogger('json.scanner').setLevel(logging.CRITICAL)
