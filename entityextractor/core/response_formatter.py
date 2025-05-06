"""
response_formatter.py

Formats entities, relationships, and optional visualization into the final API output schema.
"""
import logging
from typing import List, Dict, Any, Optional
from entityextractor.core.visualization_api import visualize_graph


def format_response(
    entities: List[Dict[str, Any]],
    relationships: Optional[List[Dict[str, Any]]],
    config: Dict[str, Any]
) -> Any:
    """
    Assemble and format the final result.

    - If no relationships and visualization disabled: returns List of entities.
    - Otherwise returns Dict with 'entities', optional 'relationships', and 'knowledgegraph_visualisation'.
    """
    # Normalize entity inferred flags
    for ent in entities:
        details = ent.get("details")
        if isinstance(details, dict) and "inferred" in details:
            inf = details["inferred"].lower()
            details["inferred"] = "explicit" if inf in ("explizit", "explicit") else "implicit"

    # If no relationships and no visualization, return flat list
    has_rels = bool(relationships)
    if not has_rels and not config.get("ENABLE_GRAPH_VISUALIZATION", False):
        return entities

    result: Dict[str, Any] = {"entities": entities}
    if has_rels:
        # Normalize relationship inferred flags
        for rel in relationships:
            inf = rel.get("inferred", "").lower()
            rel["inferred"] = "explicit" if inf in ("explizit", "explicit") else "implicit"
            # Normalize subject/object inferred
            if "subject_inferred" in rel:
                si = rel["subject_inferred"].lower()
                rel["subject_inferred"] = "explicit" if si in ("explizit", "explicit") else "implicit"
            if "object_inferred" in rel:
                oi = rel["object_inferred"].lower()
                rel["object_inferred"] = "explicit" if oi in ("explizit", "explicit") else "implicit"
        result["relationships"] = relationships

    if config.get("ENABLE_GRAPH_VISUALIZATION", False):
        logging.info("[response_formatter] Generating graph visualization...")
        vis = visualize_graph({"entities": entities, "relationships": relationships}, config)
        result["knowledgegraph_visualisation"] = [{"static": vis.get("png"), "interactive": vis.get("html")}]

    return result
