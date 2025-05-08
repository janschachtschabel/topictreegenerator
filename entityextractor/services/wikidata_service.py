"""
Wikidata service module for the Entity Extractor.

This module provides functions for interacting with the Wikidata API
and extracting information from Wikidata entities.
"""

import logging
import requests
import hashlib
import json
import os
from openai import OpenAI
from entityextractor.config.settings import get_config, DEFAULT_CONFIG
from entityextractor.utils.text_utils import clean_json_from_markdown
from entityextractor.utils.rate_limiter import RateLimiter

_config = get_config()
_rate_limiter = RateLimiter(_config["RATE_LIMIT_MAX_CALLS"], _config["RATE_LIMIT_PERIOD"], _config["RATE_LIMIT_BACKOFF_BASE"], _config["RATE_LIMIT_BACKOFF_MAX"])

@_rate_limiter
def _limited_get(url, **kwargs):
    return requests.get(url, **kwargs)

def search_wikidata_by_entity_name(entity_name, language="en", config=None, try_english=True):
    """
    Search Wikidata directly by entity name.
    This is used as a fallback when we can't extract a Wikidata ID from Wikipedia.
    
    Args:
        entity_name: Name of the entity to search for
        language: Language code (en, de, etc.)
        config: Configuration dictionary with timeout settings
        try_english: Whether to also try searching in English if the original language fails
        
    Returns:
        The Wikidata ID or None if not found
    """
    if config is None:
        config = DEFAULT_CONFIG
        
    # Wikidata API endpoint for searching entities
    api_url = "https://www.wikidata.org/w/api.php"
    
    # First try with the original language
    params = {
        "action": "wbsearchentities",
        "search": entity_name,
        "language": language,
        "format": "json"
    }
    
    try:
        response = _limited_get(api_url, params=params, headers={"User-Agent": config.get("USER_AGENT")}, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        response.raise_for_status()
        data = response.json()
        
        # Check if we got any search results
        search_results = data.get("search", [])
        if search_results:
            # Return the ID of the first (most relevant) result
            wikidata_id = search_results[0].get("id")
            logging.info(f"Wikidata search found ID {wikidata_id} for entity '{entity_name}' in {language}")
            return wikidata_id
        else:
            logging.warning(f"No Wikidata entities found for '{entity_name}' in {language}")
            
            # If language is not English and try_english is True, try searching in English
            if language != "en" and try_english:
                # Try to translate the term to English using LLM for better results
                english_term = translate_to_english(entity_name, config)
                if english_term and english_term != entity_name:
                    logging.info(f"Trying Wikidata search with English translation: '{english_term}'")
                    return search_wikidata_by_entity_name(english_term, language="en", config=config, try_english=False)
            
            return None
    except Exception as e:
        logging.error(f"Error searching Wikidata for '{entity_name}': {e}")
        return None

def translate_to_english(term, config=None):
    """
    Translate a term to English using OpenAI.
    This is used to improve Wikidata search results for non-English terms.
    
    Args:
        term: The term to translate
        config: Configuration dictionary with API settings
        
    Returns:
        The English translation or None if translation fails
    """
    if config is None:
        config = DEFAULT_CONFIG
        
    api_key = config.get("OPENAI_API_KEY")
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        
    if not api_key:
        logging.error("No OpenAI API key provided. Set OPENAI_API_KEY in config or environment.")
        return None
        
    model = config.get("MODEL", "gpt-4o-mini")
    base_url = config.get("LLM_BASE_URL", "https://api.openai.com/v1")
    
    # Create the OpenAI client
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    # German prompt for translation with Wikidata focus
    system_prompt = "Du bist ein Experte für Übersetzungen wissenschaftlicher Begriffe und die Terminologie in Wikidata. Übersetze präzise ins Englische unter Berücksichtigung der in Wikidata verwendeten Fachbegriffe."
    user_prompt = f"Übersetze den folgenden wissenschaftlichen Begriff ins Englische, wie er in Wikidata verwendet werden würde. Verwende die offizielle englische Fachterminologie, die in Wikidata-Einträgen zu finden ist. Gib NUR den übersetzten Begriff zurück, ohne weitere Erklärungen: '{term}'"
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        # Extract the response content and clean it
        translation = response.choices[0].message.content.strip()
        translation = translation.strip('"').strip("'").strip()
        
        logging.info(f"Translated '{term}' to English: '{translation}'")
        return translation
    except Exception as e:
        logging.error(f"Error translating '{term}' to English: {e}")
        return None

def generate_entity_synonyms(entity_name, language="en", config=None):
    """
    Generate potential synonyms for an entity using OpenAI.
    This is used as a last-resort fallback when direct Wikidata search fails.
    
    Args:
        entity_name: Name of the entity to find synonyms for
        language: Language code (en, de, etc.)
        config: Configuration dictionary with API settings
        
    Returns:
        A list of potential synonyms or an empty list if generation fails
    """
    if config is None:
        config = DEFAULT_CONFIG
        
    api_key = config.get("OPENAI_API_KEY")
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        
    if not api_key:
        logging.error("No OpenAI API key provided. Set OPENAI_API_KEY in config or environment.")
        return []
        
    model = config.get("MODEL", "gpt-4o-mini")
    base_url = config.get("LLM_BASE_URL", "https://api.openai.com/v1")
    
    # Create the OpenAI client
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    # Determine the prompt based on language
    if language == "en":
        system_prompt = "You are an expert in entity recognition and Wikidata knowledge base conventions."
        user_prompt = f"Generate the 3 most likely alternative names or synonyms for '{entity_name}' that would match Wikidata's naming conventions. Ideally, each suggestion should be a single word. Focus on official terminology used in Wikidata entries, not general synonyms. For scientific concepts, prefer standard English academic terminology. Return ONLY a JSON array of strings without any explanation."
    else:
        system_prompt = "Du bist ein Experte für Entitätserkennung und die Namenskonventionen der Wikidata-Wissensdatenbank."
        user_prompt = f"Generiere die 3 wahrscheinlichsten alternativen Namen oder Synonyme für '{entity_name}', die den Namenskonventionen von Wikidata entsprechen würden. Jeder Vorschlag sollte idealerweise nur ein Wort sein. Konzentriere dich auf die offizielle Terminologie, die in Wikidata-Einträgen verwendet wird, nicht auf allgemeine Synonyme. Für wissenschaftliche Konzepte bevorzuge die standardisierte Fachterminologie. Gib NUR ein JSON-Array von Strings zurück, ohne jegliche Erklärung."
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        # Extract the response content
        raw_json = response.choices[0].message.content.strip()
        
        # Clean the JSON if it's wrapped in markdown code blocks
        raw_json = clean_json_from_markdown(raw_json)
        
        # Parse the JSON array
        synonyms = json.loads(raw_json)
        logging.info(f"Generated {len(synonyms)} synonyms for '{entity_name}': {synonyms}")
        return synonyms
    except Exception as e:
        logging.error(f"Error generating synonyms for '{entity_name}': {e}")
        return []

def get_wikidata_id_from_wikipedia_url(wikipedia_url, entity_name=None, config=None):
    """
    Retrieve the Wikidata ID for a Wikipedia article.
    
    Args:
        wikipedia_url: URL of the Wikipedia article
        entity_name: Original entity name (for fallback search)
        config: Configuration dictionary with timeout settings
        
    Returns:
        The Wikidata ID or None if not found
    """
    if config is None:
        config = DEFAULT_CONFIG
        
    try:
        splitted = wikipedia_url.split("/wiki/")
        if len(splitted) < 2:
            logging.warning("Wikipedia URL has unexpected format: %s", wikipedia_url)
            return None
        title = splitted[1].split("#")[0]
    except Exception as e:
        logging.error("Error extracting title from URL %s: %s", wikipedia_url, e)
        return None

    try:
        if "://" in wikipedia_url:
            domain = wikipedia_url.split("://")[1].split("/")[0]
            lang = domain.split('.')[0]
        else:
            lang = "de"
    except Exception as e:
        logging.error("Error determining language from URL %s: %s", wikipedia_url, e)
        lang = "de"
        
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "pageprops",
        "redirects": 1,  # Follow redirects to get canonical pageprops
        "titles": title,
        "format": "json"
    }
    
    try:
        response = _limited_get(api_url, params=params, headers={"User-Agent": config.get("USER_AGENT")}, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        response.raise_for_status()
        data = response.json()
        
        # Normalize and follow redirects to get canonical title
        original_title = title
        norms = data.get("query", {}).get("normalized", [])
        redirects = data.get("query", {}).get("redirects", [])
        new_title = None
        if norms:
            new_title = norms[0].get("to")
        elif redirects:
            new_title = redirects[0].get("to")
        if new_title and new_title != original_title:
            logging.info(f"Canonical title for Wikidata lookup: {original_title} -> {new_title}")
            title = new_title
            # Use canonical name for fallback search
            entity_name = new_title.replace('_', ' ')
            
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            pageprops = page.get("pageprops", {})
            wikidata_id = pageprops.get("wikibase_item")
            if wikidata_id:
                return wikidata_id
        logging.warning("No Wikidata ID found for URL: %s", wikipedia_url)
        
        # Try fallback search by entity name if provided
        if entity_name:
            logging.info(f"Trying fallback Wikidata search for entity: '{entity_name}'")
            lang = "en" if "en.wikipedia.org" in wikipedia_url else "de"
            wikidata_id = search_wikidata_by_entity_name(entity_name, language=lang, config=config)
            
            # If direct search fails, try with LLM-generated synonyms
            if not wikidata_id:
                logging.info(f"Direct Wikidata search failed. Trying with LLM-generated synonyms for '{entity_name}'")
                synonyms = generate_entity_synonyms(entity_name, language=lang, config=config)
                
                # Try each synonym until we find a match
                for synonym in synonyms:
                    logging.info(f"Trying Wikidata search with synonym: '{synonym}'")
                    wikidata_id = search_wikidata_by_entity_name(synonym, language=lang, config=config)
                    if wikidata_id:
                        logging.info(f"Found Wikidata ID {wikidata_id} using synonym '{synonym}'")
                        return wikidata_id
                        
                # If we're using German and all German attempts failed, try English translation
                if lang == "de":
                    logging.info(f"All German attempts failed. Trying English translation for '{entity_name}'")
                    english_term = translate_to_english(entity_name, config=config)
                    if english_term:
                        logging.info(f"Trying Wikidata search with English translation: '{english_term}'")
                        wikidata_id = search_wikidata_by_entity_name(english_term, language="en", config=config)
                        if wikidata_id:
                            logging.info(f"Found Wikidata ID {wikidata_id} using English translation '{english_term}'")
                            return wikidata_id
                        
                logging.warning(f"All fallback attempts failed for '{entity_name}'")
            return wikidata_id
        return None
    except Exception as e:
        logging.error("Error retrieving Wikidata ID for %s: %s", wikipedia_url, e)
        return None

def get_wikidata_description(qid, lang="de", config=None):
    """
    Retrieve the description of a Wikidata entity.
    
    Args:
        qid: The Wikidata entity ID (e.g., Q312 for Apple Inc.)
        lang: Language for the description ("de" or "en")
        config: Configuration dictionary with timeout settings
        
    Returns:
        The entity description or None if not found
    """
    if config is None:
        config = DEFAULT_CONFIG
        
    api_url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    try:
        r = _limited_get(api_url, headers={"User-Agent": config.get("USER_AGENT")}, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        r.raise_for_status()
        data = r.json()
        entities = data.get("entities", {})
        entity = entities.get(qid, {})
        descriptions = entity.get("descriptions", {})
        description = descriptions.get(lang, {}).get("value")
        if not description and descriptions:
            description = list(descriptions.values())[0].get("value")
        return description
    except Exception as e:
        logging.error("Error retrieving Wikidata description for %s: %s", qid, e)
        return None

def get_wikidata_details(entity_id, language="de", config=None):
    """
    Retrieve detailed information about a Wikidata entity.
    
    Args:
        entity_id: The Wikidata entity ID (e.g., Q312 for Apple Inc.)
        language: Language for the labels and descriptions ("de" or "en")
        config: Configuration dictionary with timeout settings
        
    Returns:
        A dictionary with Wikidata information or an empty dictionary if not found
    """
    if not entity_id:
        return {}
        
    if config is None:
        config = DEFAULT_CONFIG
        
    # === Wikidata details caching ===
    if config.get("CACHE_ENABLED") and config.get("CACHE_WIKIDATA_ENABLED") and entity_id:
        cache_dir = config.get("CACHE_DIR", "cache")
        wikidata_cache_dir = os.path.join(cache_dir, "wikidata")
        os.makedirs(wikidata_cache_dir, exist_ok=True)
        cache_key = hashlib.sha256(entity_id.encode("utf-8")).hexdigest()
        cache_path = os.path.join(wikidata_cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_path):
            logging.info(f"Loaded Wikidata cache for {entity_id}")
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load Wikidata cache {cache_path}: {e}")
                
    wikidata_url = f"https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.json"
    
    try:
        r = _limited_get(wikidata_url, headers={"User-Agent": config.get("USER_AGENT")}, timeout=config.get('TIMEOUT_THIRD_PARTY', 15))
        r.raise_for_status()
        data = r.json()
        
        entities = data.get("entities", {})
        entity = entities.get(entity_id, {})
        claims = entity.get("claims", {})
        labels = entity.get("labels", {})
        aliases = entity.get("aliases", {})
        descriptions = entity.get("descriptions", {})
        
        # Initialize result dictionary
        result = {
            "id": entity_id
        }
        
        # Add description
        description = descriptions.get(language, {}).get("value")
        if not description and descriptions:
            # Fallback to first available language
            description = list(descriptions.values())[0].get("value")
        if description:
            result["description"] = description
            
        # Add label/name
        label = labels.get(language, {}).get("value")
        if not label and labels:
            # Fallback to first available language
            label = list(labels.values())[0].get("value")
        if label:
            result["label"] = label
            
        # Add aliases/alternative names
        alias_list = aliases.get(language, [])
        if alias_list:
            result["aliases"] = [alias.get("value") for alias in alias_list if alias.get("value")]
            
        # P31 = instance of
        instance_claims = claims.get("P31", [])
        instances = []
        for claim in instance_claims:
            if "mainsnak" in claim and "datavalue" in claim["mainsnak"]:
                dv = claim["mainsnak"]["datavalue"]
                if dv.get("type") == "wikibase-entityid":
                    iid = dv["value"]["id"]
                    ilabel = get_wikidata_description(iid, lang=language, config=config)
                    if ilabel and ilabel not in instances:
                        instances.append(ilabel)
        if instances:
            result["instance_of"] = instances

        # P279 = subclass of
        subclass_claims = claims.get("P279", [])
        subclasses = []
        for claim in subclass_claims:
            if "mainsnak" in claim and "datavalue" in claim["mainsnak"]:
                dv = claim["mainsnak"]["datavalue"]
                if dv.get("type") == "wikibase-entityid":
                    sid = dv["value"]["id"]
                    slabel = get_wikidata_description(sid, lang=language, config=config)
                    if slabel and slabel not in subclasses:
                        subclasses.append(slabel)
        if subclasses:
            result["subclass_of"] = subclasses
            
        # Get types/classes (P31 = "instance of")
        instance_claims = claims.get("P31", [])
        types = []
        
        for claim in instance_claims:
            if "mainsnak" in claim and "datavalue" in claim["mainsnak"]:
                datavalue = claim["mainsnak"]["datavalue"]
                if datavalue["type"] == "wikibase-entityid":
                    type_id = datavalue["value"]["id"]
                    # Get label for this type in the configured language
                    type_label = get_wikidata_description(type_id, lang=language, config=config)
                    if type_label and type_label not in types:
                        types.append(type_label)
        
        if types:
            result["types"] = types
            
        # Get subclasses (P279 = "subclass of")
        subclass_claims = claims.get("P279", [])
        subclasses = []
        
        for claim in subclass_claims:
            if "mainsnak" in claim and "datavalue" in claim["mainsnak"]:
                datavalue = claim["mainsnak"]["datavalue"]
                if datavalue["type"] == "wikibase-entityid":
                    subclass_id = datavalue["value"]["id"]
                    subclass_label = get_wikidata_description(subclass_id, lang=language, config=config)
                    if subclass_label and subclass_label not in subclasses:
                        subclasses.append(subclass_label)
        
        if subclasses:
            result["subclasses"] = subclasses
            
        # Get image (P18 = "image")
        image_claims = claims.get("P18", [])
        if image_claims and "mainsnak" in image_claims[0] and "datavalue" in image_claims[0]["mainsnak"]:
            image_value = image_claims[0]["mainsnak"]["datavalue"].get("value")
            if image_value:
                # Convert image name to URL
                image_name = image_value.replace(" ", "_")
                # Calculate MD5 hash of image name for Wikimedia Commons URL
                md5_hash = hashlib.md5(image_name.encode('utf-8')).hexdigest()
                image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{image_name}"
                result["image_url"] = image_url
                
        # Get official website (P856 = "official website")
        website_claims = claims.get("P856", [])
        if website_claims and "mainsnak" in website_claims[0] and "datavalue" in website_claims[0]["mainsnak"]:
            website = website_claims[0]["mainsnak"]["datavalue"].get("value")
            if website:
                result["website"] = website
                
        # Get coordinates (P625 = "coordinate location")
        coord_claims = claims.get("P625", [])
        if coord_claims and "mainsnak" in coord_claims[0] and "datavalue" in coord_claims[0]["mainsnak"]:
            coord_value = coord_claims[0]["mainsnak"]["datavalue"].get("value", {})
            if coord_value and "latitude" in coord_value and "longitude" in coord_value:
                result["coordinates"] = {
                    "latitude": coord_value["latitude"],
                    "longitude": coord_value["longitude"]
                }
                
        # Get foundation date (P571 = "inception")
        foundation_claims = claims.get("P571", [])
        if foundation_claims and "mainsnak" in foundation_claims[0] and "datavalue" in foundation_claims[0]["mainsnak"]:
            time_value = foundation_claims[0]["mainsnak"]["datavalue"].get("value", {})
            if time_value and "time" in time_value:
                # Format: +YYYY-MM-DDT00:00:00Z
                time_str = time_value["time"]
                # Remove the + at the beginning and the T00:00:00Z at the end
                if time_str.startswith("+"):
                    time_str = time_str[1:]
                if "T" in time_str:
                    time_str = time_str.split("T")[0]
                result["foundation_date"] = time_str
                
        # For persons: Birth date (P569) and death date (P570)
        birth_claims = claims.get("P569", [])
        if birth_claims and "mainsnak" in birth_claims[0] and "datavalue" in birth_claims[0]["mainsnak"]:
            time_value = birth_claims[0]["mainsnak"]["datavalue"].get("value", {})
            if time_value and "time" in time_value:
                time_str = time_value["time"]
                if time_str.startswith("+"):
                    time_str = time_str[1:]
                if "T" in time_str:
                    time_str = time_str.split("T")[0]
                result["birth_date"] = time_str
                
        death_claims = claims.get("P570", [])
        if death_claims and "mainsnak" in death_claims[0] and "datavalue" in death_claims[0]["mainsnak"]:
            time_value = death_claims[0]["mainsnak"]["datavalue"].get("value", {})
            if time_value and "time" in time_value:
                time_str = time_value["time"]
                if time_str.startswith("+"):
                    time_str = time_str[1:]
                if "T" in time_str:
                    time_str = time_str.split("T")[0]
                result["death_date"] = time_str
                
        # Get occupations for persons (P106 = "occupation")
        occupation_claims = claims.get("P106", [])
        occupations = []
        
        for claim in occupation_claims:
            if "mainsnak" in claim and "datavalue" in claim["mainsnak"]:
                datavalue = claim["mainsnak"]["datavalue"]
                if datavalue["type"] == "wikibase-entityid":
                    occupation_id = datavalue["value"]["id"]
                    occupation_label = get_wikidata_description(occupation_id, lang=language, config=config)
                    if occupation_label and occupation_label not in occupations:
                        occupations.append(occupation_label)
        
        if occupations:
            result["occupations"] = occupations
            
        # Add additional properties that might be useful
        # P27 = country of citizenship
        citizenship_claims = claims.get("P27", [])
        citizenships = []
        
        for claim in citizenship_claims:
            if "mainsnak" in claim and "datavalue" in claim["mainsnak"]:
                datavalue = claim["mainsnak"]["datavalue"]
                if datavalue["type"] == "wikibase-entityid":
                    country_id = datavalue["value"]["id"]
                    country_label = get_wikidata_description(country_id, lang=language, config=config)
                    if country_label and country_label not in citizenships:
                        citizenships.append(country_label)
        
        if citizenships:
            result["citizenships"] = citizenships
            
        # P19 = place of birth
        birth_place_claims = claims.get("P19", [])
        if birth_place_claims and "mainsnak" in birth_place_claims[0] and "datavalue" in birth_place_claims[0]["mainsnak"]:
            datavalue = birth_place_claims[0]["mainsnak"]["datavalue"]
            if datavalue["type"] == "wikibase-entityid":
                place_id = datavalue["value"]["id"]
                place_label = get_wikidata_description(place_id, lang=language, config=config)
                if place_label:
                    result["birth_place"] = place_label
                    
        # P20 = place of death
        death_place_claims = claims.get("P20", [])
        if death_place_claims and "mainsnak" in death_place_claims[0] and "datavalue" in death_place_claims[0]["mainsnak"]:
            datavalue = death_place_claims[0]["mainsnak"]["datavalue"]
            if datavalue["type"] == "wikibase-entityid":
                place_id = datavalue["value"]["id"]
                place_label = get_wikidata_description(place_id, lang=language, config=config)
                if place_label:
                    result["death_place"] = place_label
                    
        # P1448 = official name
        official_name_claims = claims.get("P1448", [])
        if official_name_claims and "mainsnak" in official_name_claims[0] and "datavalue" in official_name_claims[0]["mainsnak"]:
            datavalue = official_name_claims[0]["mainsnak"]["datavalue"]
            if datavalue["type"] == "monolingualtext":
                name_value = datavalue["value"]
                if name_value.get("text"):
                    result["official_name"] = name_value["text"]
                    
        # P1082 = population
        population_claims = claims.get("P1082", [])
        if population_claims and "mainsnak" in population_claims[0] and "datavalue" in population_claims[0]["mainsnak"]:
            datavalue = population_claims[0]["mainsnak"]["datavalue"]
            if datavalue["type"] == "quantity":
                population_value = datavalue["value"]
                if "amount" in population_value:
                    result["population"] = population_value["amount"]
            
        # P361 = part of
        part_claims = claims.get("P361", [])
        parts = []
        for claim in part_claims:
            if "mainsnak" in claim and "datavalue" in claim["mainsnak"]:
                dv = claim["mainsnak"]["datavalue"]
                if dv.get("type") == "wikibase-entityid":
                    pid = dv["value"]["id"]
                    plabel = get_wikidata_description(pid, lang=language, config=config)
                    if plabel and plabel not in parts:
                        parts.append(plabel)
        if parts:
            result["part_of"] = parts
            
        # P527 = has part
        has_part_claims = claims.get("P527", [])
        has_parts = []
        for claim in has_part_claims:
            if "mainsnak" in claim and "datavalue" in claim["mainsnak"]:
                dv = claim["mainsnak"]["datavalue"]
                if dv.get("type") == "wikibase-entityid":
                    hpid = dv["value"]["id"]
                    hplabel = get_wikidata_description(hpid, lang=language, config=config)
                    if hplabel and hplabel not in has_parts:
                        has_parts.append(hplabel)
        if has_parts:
            result["has_parts"] = has_parts
            
        # P463 = member of
        member_claims = claims.get("P463", [])
        members = []
        for claim in member_claims:
            if "mainsnak" in claim and "datavalue" in claim["mainsnak"]:
                dv = claim["mainsnak"]["datavalue"]
                if dv.get("type") == "wikibase-entityid":
                    mid = dv["value"]["id"]
                    mlabel = get_wikidata_description(mid, lang=language, config=config)
                    if mlabel and mlabel not in members:
                        members.append(mlabel)
        if members:
            result["member_of"] = members
            
        # P227 = GND ID
        gnd_claims = claims.get("P227", [])
        if gnd_claims and "mainsnak" in gnd_claims[0] and "datavalue" in gnd_claims[0]["mainsnak"]:
            dv = gnd_claims[0]["mainsnak"]["datavalue"]
            if dv.get("type") == "string" and dv.get("value"):
                result["gnd_id"] = dv["value"]
                
        # P213 = ISNI
        isni_claims = claims.get("P213", [])
        if isni_claims and "mainsnak" in isni_claims[0] and "datavalue" in isni_claims[0]["mainsnak"]:
            dv = isni_claims[0]["mainsnak"]["datavalue"]
            if dv.get("type") == "string" and dv.get("value"):
                result["isni"] = dv["value"]
            
        # Save Wikidata cache
        if config.get("CACHE_ENABLED") and config.get("CACHE_WIKIDATA_ENABLED") and entity_id:
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(result, f)
                logging.info(f"Saved Wikidata cache for {entity_id} to {cache_path}")
            except Exception as e:
                logging.warning(f"Failed to save Wikidata cache {cache_path}: {e}")
        return result
    except Exception as e:
        logging.error("Error retrieving Wikidata details for %s: %s", entity_id, e)
        return {"id": entity_id}

def get_entity_types_from_wikidata(entity_id, language="de", config=None):
    """
    Retrieve the types of a Wikidata entity (compatibility function).
    
    Args:
        entity_id: The Wikidata entity ID (e.g., Q312 for Apple Inc.)
        language: Language for the type labels ("de" or "en")
        config: Configuration dictionary
        
    Returns:
        A list of types or an empty list if not found
    """
    details = get_wikidata_details(entity_id, language=language, config=config)
    return details.get("types", [])
