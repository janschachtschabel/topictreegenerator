"""
Wikipedia service module for the Entity Extractor.

This module provides functions for interacting with the Wikipedia API
and extracting information from Wikipedia pages.
"""

import logging
import re
import requests
from bs4 import BeautifulSoup
import urllib.parse
# import wptools
import os
import json
import hashlib
from entityextractor.services.wikidata_service import generate_entity_synonyms
from entityextractor.utils.cache_utils import get_cache_path, load_cache, save_cache
from entityextractor.utils.rate_limiter import RateLimiter
from entityextractor.config.settings import get_config, DEFAULT_CONFIG
from entityextractor.utils.text_utils import is_valid_wikipedia_url
from entityextractor.utils.wiki_url_utils import sanitize_wikipedia_url

_config = get_config()
_rate_limiter = RateLimiter(_config["RATE_LIMIT_MAX_CALLS"], _config["RATE_LIMIT_PERIOD"], _config["RATE_LIMIT_BACKOFF_BASE"], _config["RATE_LIMIT_BACKOFF_MAX"])

@_rate_limiter
def _limited_get(url, **kwargs):
    return requests.get(url, **kwargs)

def get_wikipedia_title_in_language(title, from_lang="de", to_lang="en", config=None):
    """
    Convert a Wikipedia title from one language to another using interlanguage links.
    
    Args:
        title: The Wikipedia article title
        from_lang: Source language of the title
        to_lang: Target language for the title
        config: Configuration dictionary with timeout settings
        
    Returns:
        The corresponding title in the target language or None if no translation is found
    """
    if from_lang == to_lang:
        return title
        
    if config is None:
        config = DEFAULT_CONFIG
        
    api_url = f"https://{from_lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "langlinks",
        "titles": title,
        "lllang": to_lang,
        "format": "json",
        "maxlag": config.get("WIKIPEDIA_MAXLAG")
    }
    
    headers = {"User-Agent": config.get("USER_AGENT")}
    
    try:
        logging.info(f"Searching translation from {from_lang}:{title} to {to_lang}")
        r = _limited_get(api_url, params=params, headers=headers, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        r.raise_for_status()
        data = r.json()
        
        pages = data.get("query", {}).get("pages", {})
        target_title = None
        
        for page_id, page in pages.items():
            langlinks = page.get("langlinks", [])
            if langlinks:
                # Take the first entry - this should be the target language version
                target_title = langlinks[0].get("*")
                break
                
        if target_title:
            logging.info(f"Translation found: {from_lang}:{title} -> {to_lang}:{target_title}")
            return target_title
        else:
            logging.info(f"No translation found from {from_lang}:{title} to {to_lang}")
            return None
            
    except Exception as e:
        logging.error(f"Error retrieving translation for {title}: {e}")
        return None

def convert_to_de_wikipedia_url(wikipedia_url):
    wikipedia_url = sanitize_wikipedia_url(wikipedia_url)
    """
    Convert a Wikipedia URL (e.g., from en.wikipedia.org) to the German Wikipedia URL if available.
    
    Args:
        wikipedia_url: The original Wikipedia URL
        
    Returns:
        Tuple of (German Wikipedia URL or original URL, updated entity name or None)
    """
    # If the URL is already German, don't change it
    if "de.wikipedia.org" in wikipedia_url:
        return wikipedia_url, None

    try:
        # Extract the title from the original URL
        splitted = wikipedia_url.split("/wiki/")
        if len(splitted) < 2:
            logging.warning("Wikipedia URL has unexpected format: %s", wikipedia_url)
            return wikipedia_url, None
        original_title = splitted[1].split("#")[0]
    except Exception as e:
        logging.error("Error extracting title from URL %s: %s", wikipedia_url, e)
        return wikipedia_url, None
        
    try:
        # Determine the source language from the domain
        if "://" in wikipedia_url:
            domain = wikipedia_url.split("://")[1].split("/")[0]
            from_lang = domain.split('.')[0]
        else:
            from_lang = "en"
            
        # Get the German title using interlanguage links
        de_title = get_wikipedia_title_in_language(original_title, from_lang=from_lang, to_lang="de")
        
        if de_title:
            # Create the German Wikipedia URL
            de_title_encoded = urllib.parse.quote(de_title.replace(" ", "_"))
            de_url = f"https://de.wikipedia.org/wiki/{de_title_encoded}"
            logging.info("Conversion: '%s' converted to '%s'", wikipedia_url, de_url)
            return de_url, de_title  # de_title as optional updated entity name
        else:
            logging.info("No German version found for URL: %s", wikipedia_url)
            return wikipedia_url, None
    except Exception as e:
        logging.error("Error querying German langlinks for %s: %s", wikipedia_url, e)
        return wikipedia_url, None

def fallback_wikipedia_url(query, langs=None, language="de", config=None):
    # Decode any percent-encoded characters to get proper Unicode query
    try:
        query = urllib.parse.unquote(query)
        # Normalize query: replace underscores and remove parentheses for better search
        query = query.replace('_', ' ')
        query = re.sub(r'[()]', '', query)
    except Exception as e:
        logging.warning(f"Error decoding query for fallback: {e}")
    """
    Search for a Wikipedia article for an entity and return a valid URL.
    
    Args:
        query: The search term (entity name)
        langs: Optional list of languages to try in sequence
               (overridden if language="en" is set)
        language: Language configuration ("de" or "en")
        config: Configuration dictionary with timeout settings
        
    Returns:
        A valid Wikipedia URL or None if none was found
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # If no languages are specified, choose based on language parameter
    if not langs:
        if language == "en":
            langs = ["en", "de"]
        else:
            langs = ["de", "en"]
    
    # Try each language in sequence
    for lang in langs:
        try:
            # URL-encode the query
            encoded_query = urllib.parse.quote(query)
            
            # Use the opensearch API to find matching articles
            api_url = f"https://{lang}.wikipedia.org/w/api.php"
            params = {
                "action": "opensearch",
                "search": query,
                "limit": 1,
                "namespace": 0,
                "format": "json",
                "maxlag": config.get("WIKIPEDIA_MAXLAG")
            }
            
            headers = {"User-Agent": config.get("USER_AGENT")}
            
            logging.info(f"Fallback ({lang}): Searching Wikipedia URL for '{query}'...")
            
            response = _limited_get(api_url, params=params, headers=headers, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 3 and data[3] and len(data[3]) > 0:
                url = data[3][0]
                if is_valid_wikipedia_url(url):
                    logging.info(f"Fallback ({lang}) successful: Found URL '{url}' for '{query}'.")
                    return url
        except Exception as e:
            logging.error(f"Error searching Wikipedia for {query} in {lang}: {e}")
            
    logging.warning(f"Fallback failed: No Wikipedia URL found for '{query}'.")
    return None

def follow_wikipedia_redirect(url, entity_name):
    url = sanitize_wikipedia_url(url)
    """
    Follow Wikipedia redirects and extract the actual page title.
    
    1. Directly check the provided URL for redirects via HTTP request.
    2. Extract the real Wikipedia title from <title> of the target page.
    3. Return final URL and title.
    
    Args:
        url: Initial Wikipedia URL
        entity_name: Original entity name
        
    Returns:
        Tuple of (final URL, page title)
    """
    if not url:
        logging.warning(f"No URL provided for '{entity_name}'")
        return None, None
        
    try:
        # Follow redirects and get the final URL
        response = requests.get(url, allow_redirects=True)
        final_url = response.url
        html = response.text
        
        # Check for soft redirect via canonical link
        canonical_match = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        if canonical_match:
            canonical_url = canonical_match.group(1)
            if canonical_url != final_url:
                logging.info(f"Wikipedia-Soft-Redirect (canonical) detected: {final_url} -> {canonical_url}")
                # Extract title from canonical URL
                title_match = re.search(r'/wiki/([^#]+)', canonical_url)
                if title_match:
                    canonical_title = urllib.parse.unquote(title_match.group(1)).replace('_', ' ')
                    logging.info(f"Entity corrected: '{entity_name}' -> '{canonical_title}'")
                    return canonical_url, canonical_title
                return canonical_url, entity_name
        
        # Extract page title from HTML
        title_match = re.search(r'<title>([^<]+)</title>', html)
        if title_match:
            page_title = title_match.group(1)
            # Remove " - Wikipedia" oder " – Wikipedia" suffix (berücksichtigt sowohl Bindestrich als auch Gedankenstrich)
            page_title = re.sub(r'[\s]*[–-][\s]*Wikipedia.*$', '', page_title)
            
            if page_title.lower() != entity_name.lower():
                logging.info(f"Wikipedia-Title-Correction: '{entity_name}' -> '{page_title}'")
            else:
                logging.info(f"Wikipedia-Opensearch: '{entity_name}' -> {final_url} | Official title: '{page_title}'")
            return final_url, page_title
        else:
            logging.info(f"Wikipedia-Opensearch: '{entity_name}' -> {final_url} | Official title: '{page_title}'")
            return final_url, page_title
    except Exception as e:
        logging.warning(f"Wikipedia-Redirect/Title-Check failed: {e}")
        splitted = url.split("/wiki/")
        title = splitted[1].split("#")[0].replace('_', ' ') if len(splitted) >= 2 else entity_name
        return url, title

def get_wikipedia_extract(wikipedia_url, config=None):
    # Für API-Parameter: Klartext-Titel verwenden
    wikipedia_url = sanitize_wikipedia_url(wikipedia_url)

    """
    Retrieve the extract (summary) of a Wikipedia article.
    
    Args:
        wikipedia_url: URL of the Wikipedia article
        config: Configuration dictionary with timeout settings
        
    Returns:
        The article extract or None if not found
    """
    if config is None:
        config = DEFAULT_CONFIG
    # === Wikipedia extract caching ===
    if config.get("CACHE_ENABLED") and config.get("CACHE_WIKIPEDIA_ENABLED"):
        cache_path = get_cache_path(config.get("CACHE_DIR", "cache"), "wikipedia", wikipedia_url)
        cached = load_cache(cache_path)
        if cached is not None:
            logging.info(f"Loaded Wikipedia extract from cache for {wikipedia_url}")
            return cached.get("extract"), cached.get("wikidata_id")
        else:
            logging.info(f"No Wikipedia extract cache found for {wikipedia_url}, fetching from API")
        
    try:
        splitted = wikipedia_url.split("/wiki/")
        if len(splitted) < 2:
            logging.warning("Wikipedia URL has unexpected format (Extract): %s", wikipedia_url)
            return None, None
        title = splitted[1].split("#")[0]
        title_plain = urllib.parse.unquote(title)
    except Exception as e:
        logging.error("Error extracting title for extract: %s", e)
        return None, None

    try:
        if "://" in wikipedia_url:
            domain = wikipedia_url.split("://")[1].split("/")[0]
            lang = domain.split('.')[0]
        else:
            domain = "de.wikipedia.org"
            lang = "de"
    except Exception as e:
        logging.error("Error determining language for extract: %s", e)
        lang = "de"

    try:
        # 1. Versuch: Wikipedia API für Extract (LLM-URL)
        api_url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "prop": "extracts|pageprops",
            "ppprop": "wikibase_item",
            "exintro": True,
            "explaintext": True,
            "format": "json",
            "titles": title_plain,
            "maxlag": config.get("WIKIPEDIA_MAXLAG")
        }
        headers = {"User-Agent": config.get("USER_AGENT")}
        
        r = _limited_get(api_url, params=params, headers=headers, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            extract_text = page.get("extract", "")
            wikidata_id = page.get("pageprops", {}).get("wikibase_item")
            if extract_text:
                logging.info(f"Wikipedia extract for URL {wikipedia_url} successfully loaded.")
                # Save cache
                if config.get("CACHE_ENABLED") and config.get("CACHE_WIKIPEDIA_ENABLED"):
                    save_cache(cache_path, {"extract": extract_text, "wikidata_id": wikidata_id})
                    logging.info(f"Saved Wikipedia extract cache for {wikipedia_url}")
                return extract_text, wikidata_id
        # Kein Extract gefunden: Prüfe Softredirect vor Opensearch
        logging.warning(f"No Wikipedia extract found for URL {wikipedia_url}. Checking softredirect first...")
        # Fragment entfernen
        base_url = wikipedia_url.split('#')[0]
        # Softredirect prüfen
        final_url, final_title = follow_wikipedia_redirect(base_url, title_plain)
        if final_url and final_url != base_url:
            logging.info(f"Softredirect erkannt: {base_url} -> {final_url} | Versuche Extrakt erneut.")
            try:
                sr_spl = final_url.split("/wiki/")
                if len(sr_spl) >= 2:
                    sr_title_plain = urllib.parse.unquote(sr_spl[1].split("#")[0])
                    srv_api = f"https://{lang}.wikipedia.org/w/api.php"
                    srv_params = params.copy()
                    srv_params["titles"] = sr_title_plain
                    r_sr = _limited_get(srv_api, params=srv_params, headers=headers, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
                    r_sr.raise_for_status()
                    srv_pages = r_sr.json().get("query", {}).get("pages", {})
                    for srv_page in srv_pages.values():
                        srv_extract = srv_page.get("extract", "")
                        if srv_extract:
                            logging.info(f"Wikipedia extract nach Softredirect für URL {final_url} erfolgreich geladen.")
                            return srv_extract, None
            except Exception as e:
                logging.error(f"Error during redirect extract for {final_url}: {e}")
        # Softredirect nicht angewendet oder kein Inhalt, nun Opensearch-Fallback
        logging.warning(f"No Wikipedia extract found; trying fallback URL via Opensearch.")
        # Single Opensearch fallback with prioritized languages
        priority_langs = [lang] if lang == 'en' else [lang, 'en']
        fallback_url = fallback_wikipedia_url(title_plain, langs=priority_langs)
        if fallback_url and fallback_url != base_url:
            try:
                fb_spl = fallback_url.split("/wiki/")
                if len(fb_spl) >= 2:
                    fb_title_plain = urllib.parse.unquote(fb_spl[1].split("#")[0])
                    parsed_fb = urllib.parse.urlparse(fallback_url)
                    fb_lang = parsed_fb.netloc.split('.')[0]
                    fb_api_url = f"https://{fb_lang}.wikipedia.org/w/api.php"
                    fb_params = params.copy()
                    fb_params["titles"] = fb_title_plain
                    r_fb = _limited_get(fb_api_url, params=fb_params, headers=headers, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
                    r_fb.raise_for_status()
                    fb_pages = r_fb.json().get("query", {}).get("pages", {})
                    for fb_page in fb_pages.values():
                        fb_extract = fb_page.get("extract", "")
                        if fb_extract:
                            logging.info(f"Wikipedia extract for fallback URL {fallback_url} erfolgreich geladen.")
                            return fb_extract, None
            except Exception as e:
                logging.error(f"Error retrieving Wikipedia extract for fallback URL {fallback_url}: {e}")
        logging.warning(f"No Wikipedia extract found via API for both URL {wikipedia_url} and fallback. Trying BeautifulSoup...")
        try:
            response = requests.get(wikipedia_url, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            content = None
            main_content = soup.select_one('#mw-content-text > .mw-parser-output')
            if main_content:
                paragraphs = []
                for p in main_content.find_all('p'):
                    if p.text.strip() and not p.find_parent(class_='infobox'):
                        paragraphs.append(p.text.strip())
                if paragraphs:
                    content = ' '.join(paragraphs[:3])
            if not content:
                first_heading = soup.select_one('.mw-headline')
                if first_heading and first_heading.parent:
                    section = first_heading.parent.find_next_sibling()
                    section_text = []
                    while section and section.name != 'h2' and section.name != 'h3':
                        if section.name == 'p' and section.text.strip():
                            section_text.append(section.text.strip())
                        section = section.find_next_sibling()
                    if section_text:
                        content = ' '.join(section_text[:3])
            if not content:
                all_paragraphs = soup.select('#bodyContent p')
                paragraphs = [p.text.strip() for p in all_paragraphs if p.text.strip() and not p.find_parent(class_='infobox')]
                if paragraphs:
                    content = ' '.join(paragraphs[:3])
            if content:
                logging.info(f"BeautifulSoup: Extract successfully extracted for {wikipedia_url}.")
                return content, None
            else:
                logging.warning(f"BeautifulSoup: No paragraphs found in content for {wikipedia_url}.")
                # continue to LLM-synonym fallback
        except Exception as bs_error:
            logging.error(f"Error in BeautifulSoup fallback for {wikipedia_url}: {bs_error}")
            # continue to LLM-synonym fallback
    except Exception as e:
        logging.error(f"Error during Wikipedia API and fallback flow for URL {wikipedia_url}: {e}")
        # continue to LLM-synonym fallback

    # LLM-Synonym-Fallback nach BeautifulSoup
    logging.warning(f"No extract via BeautifulSoup; trying LLM-generated synonyms for '{title_plain}'...")
    synonyms = generate_entity_synonyms(title_plain, language=lang, config=config)
    for syn in synonyms:
        try:
            logging.info(f"Trying fallback for synonym '{syn}'..." )
            # Single fallback call with priority languages
            priority_langs = [lang] if lang == 'en' else [lang, 'en']
            syn_url = fallback_wikipedia_url(syn, langs=priority_langs)
            if syn_url:
                parsed_syn = urllib.parse.urlparse(syn_url)
                syn_lang = parsed_syn.netloc.split('.')[0]
                syn_title = urllib.parse.unquote(parsed_syn.path.split('/wiki/')[1].split('#')[0])
                syn_api = f"https://{syn_lang}.wikipedia.org/w/api.php"
                syn_params = params.copy()
                syn_params['titles'] = syn_title
                r_syn = _limited_get(syn_api, params=syn_params, headers=headers, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
                r_syn.raise_for_status()
                pages_syn = r_syn.json().get('query', {}).get('pages', {})
                for page in pages_syn.values():
                    syn_ext = page.get('extract', '')
                    if syn_ext:
                        logging.info(f"Extract for synonym '{syn}' successful.")
                        return syn_ext, None
        except Exception as se:
            logging.error(f"Error retrieving extract for synonym '{syn}': {se}")
    logging.warning(f"No extract found using LLM-generated synonyms for '{title_plain}'.")
    return None, None

def get_wikipedia_categories(wikipedia_url, config=None):
    wikipedia_url = sanitize_wikipedia_url(wikipedia_url)

    """
    Retrieve Wikipedia categories via MediaWiki API.
    Returns a list of category names (without 'Category:' prefix).
    """
    if config is None:
        config = DEFAULT_CONFIG
    try:
        # Parse title and language
        splitted = wikipedia_url.split("/wiki/")
        if len(splitted) < 2:
            logging.warning("Invalid Wikipedia URL for categories: %s", wikipedia_url)
            return []
        title = splitted[1].split("#")[0]
        title_plain = urllib.parse.unquote(title)
        domain = wikipedia_url.split("://")[1].split("/")[0] if "://" in wikipedia_url else "de.wikipedia.org"
        lang = domain.split(".")[0]
        api_url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "prop": "categories",
            "titles": title_plain,
            "cllimit": "max",
            "format": "json",
            "maxlag": config.get("WIKIPEDIA_MAXLAG")
        }
        headers = {"User-Agent": config.get("USER_AGENT")}
        
        r = _limited_get(api_url, params=params, headers=headers, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        r.raise_for_status()
        data = r.json()
        cats = []
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            for c in page.get("categories", []):
                name = c.get("title", "")
                if name.startswith("Category:"):
                    name = name.split("Category:", 1)[1]
                cats.append(name)
        return list(dict.fromkeys(cats))
    except Exception as e:
        logging.error("Error retrieving Wikipedia categories for %s: %s", wikipedia_url, e)
        return []

def get_wikipedia_details(wikipedia_url, config=None):
    wikipedia_url = sanitize_wikipedia_url(wikipedia_url)

    """
    Retrieve additional details from a Wikipedia page using direct API calls: infobox, see-also links, image.
    """
    if config is None:
        config = DEFAULT_CONFIG
    # parse title and language
    try:
        parts = wikipedia_url.split('/wiki/')
        if len(parts) < 2:
            logging.warning("Invalid Wikipedia URL for details: %s", wikipedia_url)
            return {}
        title = parts[1].split('#')[0]
    except Exception as e:
        logging.error("Error parsing title for details: %s", e)
        return {}
    try:
        domain = wikipedia_url.split('://')[1].split('/')[0]
        lang = domain.split('.')[0]
    except Exception as e:
        logging.error("Error parsing language for details: %s", e)
        lang = 'de'
    endpoint = f"https://{lang}.wikipedia.org/w/api.php"
    result = {}
    # 1. Infobox via parse/text
    try:
        params = {
            'action': 'parse',
            'page': title,
            'prop': 'text',
            'format': 'json',
            'section': 0,
            "maxlag": config.get("WIKIPEDIA_MAXLAG")
        }
        headers = {"User-Agent": config.get("USER_AGENT")}
        
        r = _limited_get(endpoint, params=params, headers=headers, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        r.raise_for_status()
        html = r.json().get('parse', {}).get('text', {}).get('*', '')
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='infobox')
        if table:
            info = {}
            for tr in table.find_all('tr'):
                th = tr.find('th')
                td = tr.find('td')
                if th and td:
                    key = th.get_text(' ', strip=True)
                    value = td.get_text(' ', strip=True)
                    info[key] = value
            if info:
                result['infobox'] = info
    except Exception as e:
        logging.error("Error parsing infobox for %s: %s", wikipedia_url, e)
    # 2. See also links via parse/links
    try:
        sec_params = {'action': 'parse', 'page': title, 'prop': 'sections', 'format': 'json'}
        rsec = _limited_get(endpoint, params=sec_params, headers=headers, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        rsec.raise_for_status()
        secs = rsec.json().get('parse', {}).get('sections', [])
        idx = next((s['index'] for s in secs if s.get('line', '').lower() in ('see also', 'siehe auch')), None)
        if idx:
            link_params = {'action': 'parse', 'page': title, 'prop': 'links', 'format': 'json', 'section': idx}
            rlink = _limited_get(endpoint, params=link_params, headers=headers, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
            rlink.raise_for_status()
            links = rlink.json().get('parse', {}).get('links', [])
            see = []
            for l in links:
                link_title = l.get('title') or l.get('*')
                slug = urllib.parse.quote(link_title.replace(' ', '_'))
                see.append(f"https://{lang}.wikipedia.org/wiki/{slug}")
            if see:
                result['see_also'] = see
    except Exception as e:
        logging.error("Error fetching see_also for %s: %s", wikipedia_url, e)
    # 3. Main image via pageimages
    try:
        img_params = {'action': 'query', 'prop': 'pageimages', 'piprop': 'original', 'titles': title, 'format': 'json'}
        rimg = _limited_get(endpoint, params=img_params, headers=headers, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        rimg.raise_for_status()
        pages = rimg.json().get('query', {}).get('pages', {})
        page_data = next(iter(pages.values()))
        img = page_data.get('original', {}).get('source') or page_data.get('thumbnail', {}).get('source')
        if img:
            result['image'] = img
    except Exception as e:
        logging.error("Error fetching image for %s: %s", wikipedia_url, e)
    return result

def get_wikipedia_summary_and_categories_props(wikipedia_url, config=None):
    wikipedia_url = sanitize_wikipedia_url(wikipedia_url)

    """
    Retrieve title, extract, categories and Wikidata ID/URL in a single MediaWiki API call.

    Args:
        wikipedia_url: URL of the Wikipedia article
        config: Configuration dict with TIMEOUT_THIRD_PARTY

    Returns:
        A dict with keys 'title', 'extract', 'categories', 'wikidata_id', 'wikidata_url'
    """
    if config is None:
        config = DEFAULT_CONFIG
    # === Wikipedia summary caching ===
    if config.get("CACHE_ENABLED") and config.get("CACHE_WIKIPEDIA_ENABLED"):
        cache_path = get_cache_path(config.get("CACHE_DIR", "cache"), "wikipedia", wikipedia_url, suffix="_summary.json")
        cached = load_cache(cache_path)
        if cached is not None:
            logging.debug(f"Loaded Wikipedia summary cache for {wikipedia_url}")
            return cached
        
    try:
        parts = wikipedia_url.split('/wiki/')
        if len(parts) < 2:
            logging.warning("Invalid Wikipedia URL: %s", wikipedia_url)
            return {}
        title = parts[1].split('#')[0]
    except Exception as e:
        logging.error("Error parsing title from URL: %s", e)
        return {}
    try:
        domain = wikipedia_url.split('://')[1].split('/')[0]
        lang = domain.split('.')[0]
    except Exception as e:
        logging.error("Error parsing language from URL: %s", e)
        lang = 'de'
    endpoint = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'format': 'json',
        'prop': 'extracts|categories|pageprops',
        'ppprop': 'wikibase_item',
        'titles': title,
        'exintro': 1,
        'explaintext': 1,
        'cllimit': 'max',
        'clshow': '!hidden',
        "maxlag": config.get("WIKIPEDIA_MAXLAG")
    }
    headers = {"User-Agent": config.get("USER_AGENT")}
    
    try:
        r = _limited_get(endpoint, params=params, headers=headers, timeout=config.get("TIMEOUT_THIRD_PARTY", 15))
        r.raise_for_status()
        pages = r.json().get('query', {}).get('pages', {})
        page = next(iter(pages.values()))
        result = {
            'title': page.get('title'),
            'extract': page.get('extract', ''),
            'categories': [c.get('title','').split('Category:',1)[-1] for c in page.get('categories', [])],
            'wikidata_id': page.get('pageprops', {}).get('wikibase_item')
        }
        wid = result['wikidata_id']
        result['wikidata_url'] = f"https://www.wikidata.org/wiki/{wid}" if wid else None
        # Save summary cache
        if config.get("CACHE_ENABLED") and config.get("CACHE_WIKIPEDIA_ENABLED"):
            save_cache(cache_path, result)
            logging.debug(f"Saved Wikipedia summary cache for {wikipedia_url}")
        return result
    except Exception as e:
        logging.error("Error fetching wiki summary and categories: %s", e)
        return {}
