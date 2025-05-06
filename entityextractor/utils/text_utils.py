"""
Text processing utilities for the Entity Extractor.

This module provides functions for processing and cleaning text data.
"""

import re

def clean_json_from_markdown(raw_text):
    """
    Remove Markdown code block markers from LLM responses.
    
    Args:
        raw_text: The raw text containing potential Markdown formatting
        
    Returns:
        Cleaned text with Markdown code block markers removed
    """
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        # Skip first and last line if they contain Markdown markers
        for i in range(len(lines)):
            if lines[i].startswith("```"):
                if i == 0:
                    lines[i] = ""
                    break
        # Go through lines from bottom to top to find the last Markdown marker
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith("```"):
                lines[i] = ""
                break
                
        raw_text = "\n".join([line for line in lines if line])
    
    # Handle case where only the first line has ```json
    lines = raw_text.splitlines()
    if lines and lines[0].startswith("```"):
        lines[0] = "```"
        raw_text = "\n".join(lines)
    
    # Remove invalid control characters
    # Allowed control characters in JSON: \b, \f, \n, \r, \t
    clean_text = ""
    for char in raw_text:
        # Only keep printable characters and allowed control characters
        if ord(char) >= 32 or char in '\b\f\n\r\t':
            clean_text += char
        else:
            # Replace invalid control characters with spaces
            clean_text += ' '
    
    return clean_text

# Alias for compatibility
clean_json_response = clean_json_from_markdown

def is_valid_wikipedia_url(url):
    """
    Validate if a URL matches the expected Wikipedia URL pattern.
    
    Args:
        url: URL to validate
        
    Returns:
        Boolean indicating if the URL is a valid Wikipedia URL
    """
    pattern = re.compile(r"^https?://[a-z]{2}\.wikipedia\.org/wiki/[\w\-%]+")
    return bool(pattern.match(url))

def strip_trailing_ellipsis(text):
    """
    Remove trailing ellipsis from text.
    
    Args:
        text: Text to process
        
    Returns:
        Text with trailing ellipsis removed
    """
    if text:
        # Remove trailing "..." or "…"
        text = re.sub(r'[.]{3,}$', '', text)
        text = re.sub(r'…$', '', text)
        return text.rstrip()
    return text

# Neue Funktion für Text-Chunking
def chunk_text(text: str, size: int, overlap: int = 0) -> list:
    """
    Teilt einen Text in überlappende Chunks auf.

    Args:
        text: Der vollständige Text.
        size: Maximale Zeichenlänge eines Chunks.
        overlap: Anzahl Zeichen, die sich zwischen Chunks überlappen.

    Returns:
        Liste von Text-Chunks.
    """
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + size, length)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == length:
            break
        start = max(end - overlap, 0)
    return chunks
