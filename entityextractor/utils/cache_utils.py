import os
import json
import hashlib
import logging


def get_cache_path(cache_dir, namespace, key, suffix=".json"):
    """
    Compute the cache path for a given key under a namespace.

    Args:
        cache_dir: Base cache directory
        namespace: Sub-directory under cache_dir
        key: Cache key (e.g., URL or resource URI)
        suffix: File suffix, e.g. ".json" or "_summary.json"

    Returns:
        Full path for the cache file, ensuring the directory exists.
    """
    namespace_dir = os.path.join(cache_dir, namespace)
    os.makedirs(namespace_dir, exist_ok=True)
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return os.path.join(namespace_dir, f"{key_hash}{suffix}")


def load_cache(cache_path):
    """
    Load JSON data from cache_path if it exists.
    Returns None if not present or on failure.
    """
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logging.debug(f"Loaded cache from {cache_path}")
            return data
        except Exception as e:
            logging.warning(f"Failed to load cache {cache_path}: {e}")
    return None


def save_cache(cache_path, data):
    """
    Save JSON-serializable data to cache_path.
    """
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        logging.debug(f"Saved cache to {cache_path}")
    except Exception as e:
        logging.warning(f"Failed to save cache {cache_path}: {e}")
