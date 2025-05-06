import difflib

def filter_semantically_similar_relationships(relationships, similarity_threshold=0.85):
    """
    Entfernt Beziehungen zwischen denselben Entitäten (unabhängig von Reihenfolge),
    deren Prädikat semantisch/fuzzy sehr ähnlich ist.
    Nur das Triple mit dem "prägnantesten" Prädikat (kürzester String) bleibt erhalten.
    """
    from collections import defaultdict
    grouped = defaultdict(list)
    for rel in relationships:
        # Gruppieren nach Entity-Paar unabhängig von Richtung
        key = frozenset([rel["subject"], rel["object"]])
        grouped[key].append(rel)
    result = []
    for (subj, obj), rels in grouped.items():
        kept = []
        used = set()
        for i, r1 in enumerate(rels):
            if i in used:
                continue
            similar = [r1]
            for j, r2 in enumerate(rels):
                if j <= i or j in used:
                    continue
                ratio = difflib.SequenceMatcher(None, r1["predicate"], r2["predicate"]).ratio()
                if ratio >= similarity_threshold:
                    similar.append(r2)
                    used.add(j)
            # Behalte das kürzeste Prädikat (prägnanteste Formulierung)
            shortest = min(similar, key=lambda r: len(r["predicate"]))
            kept.append(shortest)
            used.add(i)
        result.extend(kept)
    return result
