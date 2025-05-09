"""
Entity Relationship Inference Module

Dieses Modul ermöglicht die Inferenz von Beziehungen zwischen Entitäten
basierend auf dem Originaltext und den extrahierten Entitäten.
"""

import json
import time
import logging
from openai import OpenAI
from entityextractor.config.settings import get_config
from entityextractor.utils.logging_utils import configure_logging
from entityextractor.services.openai_service import save_relationship_training_data
from entityextractor.prompts.relationship_prompts import (
    get_explicit_system_prompt_extract_en,
    get_explicit_user_prompt_extract_en,
    get_explicit_system_prompt_extract_de,
    get_explicit_user_prompt_extract_de,
    get_explicit_system_prompt_all_en,
    get_explicit_user_prompt_all_en,
    get_explicit_system_prompt_all_de,
    get_explicit_user_prompt_all_de,
    get_implicit_system_prompt_en,
    get_implicit_user_prompt_en,
    get_implicit_system_prompt_de,
    get_implicit_user_prompt_de,
    get_kgc_system_prompt_en,
    get_kgc_user_prompt_en,
    get_kgc_system_prompt_de,
    get_kgc_user_prompt_de,
    get_system_prompt_dedup_relationship_en,
    get_user_prompt_dedup_relationship_en,
    get_system_prompt_dedup_relationship_de,
    get_user_prompt_dedup_relationship_de
)

# Standardkonfiguration
DEFAULT_CONFIG = {
    "MODEL": "gpt-4.1-mini",
    "LANGUAGE": "de",
    "SHOW_STATUS": True,
    "RELATION_EXTRACTION": False
}

def infer_entity_relationships(text, entities, user_config=None):
    """
    Inferiert Beziehungen zwischen Entitäten basierend auf dem Originaltext.
    
    Args:
        text: Der Originaltext, aus dem die Entitäten extrahiert wurden
        entities: Die extrahierten Entitäten
        user_config: Optionale Benutzerkonfiguration
        
    Returns:
        Eine Liste von Tripeln (Subjekt, Prädikat, Objekt, Inferiert)
    
    Erweiterte Logik (ab 2025):
    - Standard: Extrahiere nur explizite Beziehungen (explizit im Text genannt)
    - Falls ENABLE_RELATIONS_INFERENCE=True: Nach Extraktion der expliziten Beziehungen wird ein zweiter Prompt ausgeführt, der zusätzlich implizite Beziehungen (aus dem Kontext abgeleitet) generiert. Dabei werden die bereits gefundenen expliziten Beziehungen übergeben und dürfen nicht erneut erzeugt werden.
    - Die Ergebnisse beider Prompts werden zusammengeführt (keine Duplikate).
    """
    # Konfiguration mit Benutzerüberschreibungen abrufen
    config = get_config(user_config)
    
    # Logging konfigurieren
    configure_logging(config)
    
    # Prüfen, ob Relationship Inference aktiviert ist
    if not config.get("RELATION_EXTRACTION", False):
        logging.info("Entity Relationship Inference ist deaktiviert.")
        return []
    
    # Zeitmessung starten
    start_time = time.time()
    logging.info("Starte Entity Relationship Inference...")
    
    # OpenAI API-Schlüssel abrufen
    api_key = config.get("OPENAI_API_KEY")
    if not api_key:
        import os
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logging.error("Kein OpenAI API-Schlüssel angegeben")
            return []
    
    # OpenAI-Client erstellen
    client = OpenAI(api_key=api_key)
    
    # Modell und Sprache abrufen
    model = config.get("MODEL", "gpt-4.1-mini")
    language = config.get("LANGUAGE", "de")
    
    # Max relations per prompt
    max_relations = config.get("MAX_RELATIONS", 15)
    
    # Entitätsnamen und Typen extrahieren
    entity_info = []
    logging.info(f"Verarbeite {len(entities)} Entitäten für Beziehungsextraktion")
    
    for i, entity in enumerate(entities):
        # Überprüfe die Struktur der Entität für Debugging
        logging.info(f"Verarbeite Entität {i+1}: {entity.keys()}")
        
        # Versuche, den Namen und Typ aus verschiedenen möglichen Strukturen zu extrahieren
        entity_name = ""
        entity_type = ""
        
        # Direkte Felder in der Entität
        if "entity" in entity:
            entity_name = entity["entity"]
        elif "name" in entity:
            entity_name = entity["name"]
            
        if "entity_type" in entity:
            entity_type = entity["entity_type"]
        elif "type" in entity:
            entity_type = entity["type"]
        elif "details" in entity and "typ" in entity["details"]:
            entity_type = entity["details"]["typ"]
        
        # Wikipedia-Label verwenden, falls vorhanden
        if "sources" in entity and "wikipedia" in entity["sources"]:
            if "label" in entity["sources"]["wikipedia"]:
                entity_name = entity["sources"]["wikipedia"]["label"]
        
        # Nur hinzufügen, wenn Name und Typ vorhanden sind
        if entity_name and entity_type:
            entity_info.append({"name": entity_name, "type": entity_type})
            logging.info(f"  - Extrahiert: {entity_name} ({entity_type})")
        else:
            logging.warning(f"  - Konnte keinen Namen oder Typ für Entität {i+1} extrahieren: {entity}")
    
    logging.info(f"Extrahierte {len(entity_info)} Entitäten für Beziehungsextraktion")
    
    # Erstelle ein Dictionary für schnellen Zugriff auf Entitätstypen
    entity_type_map = {entity['name']: entity['type'] for entity in entity_info}
    logging.info(f"Erstellt Entitätstyp-Map mit {len(entity_type_map)} Einträgen")
    
    # Mappt jeden Entitätsnamen auf seinen Inferenzstatus
    entity_inferred_map = {(e.get("entity") or e.get("name", "")): e.get("inferred", "explizit") for e in entities}
    logging.info(f"Erstellt Entität-Inferenz-Map mit {len(entity_inferred_map)} Einträgen")

    # KGC-Modus: nur neue implizite Beziehungen basierend auf bestehenden generieren
    existing_rels = config.get("existing_relationships")
    allowed_entities = {e.get("entity") or e.get("name", "") for e in entities}
    if config.get("ENABLE_KGC", False) and existing_rels is not None:
        logging.info(f"Starte Knowledge Graph Completion-Inferenz: {len(existing_rels)} bestehende Beziehungen")
        if language == "en":
            system_prompt = get_kgc_system_prompt_en()
            user_msg = get_kgc_user_prompt_en(text, entity_info, existing_rels, max_relations)
        else:
            system_prompt = get_kgc_system_prompt_de()
            user_msg = get_kgc_user_prompt_de(text, entity_info, existing_rels, max_relations)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        raw = response.choices[0].message.content.strip()
        new_rels = extract_json_relationships(raw)
        # Nur Beziehungen, die noch nicht vorhanden sind
        existing_keys = {(r["subject"], r["predicate"], r["object"]) for r in existing_rels}
        valid_new = []
        for rel in new_rels:
            subj = rel.get("subject")
            obj = rel.get("object")
            k = (subj, rel.get("predicate"), obj)
            # Nur neue, vollständige Tripel und bekannte Entitäten
            if k not in existing_keys and subj in allowed_entities and obj in allowed_entities \
               and all(key in rel for key in ("subject", "predicate", "object")):
                rel.update({
                    "inferred": "implicit",
                    "subject_type": entity_type_map.get(subj, ""),
                    "object_type": entity_type_map.get(obj, ""),
                    "subject_inferred": entity_inferred_map.get(subj, "explicit"),
                    "object_inferred": entity_inferred_map.get(obj, "explicit")
                })
                valid_new.append(rel)
        return valid_new

    # Prompt-Logik für explizite und ggf. (implizite) Beziehungen
    # Modus des ersten Prompts: extract vs generate
    mode = config.get("MODE", "extract")
    # Implizite Beziehungen aktivieren, wenn ENABLE_RELATIONS_INFERENCE=True
    enable_inference = config.get("ENABLE_RELATIONS_INFERENCE", False)
    
    # Primärer Prompt: extract vs generate
    # Unified extract-first prompt
    if mode == "generate":
        # All relationships mode
        if language == "en":
            system_prompt_explicit = get_explicit_system_prompt_all_en()
            user_msg_explicit = get_explicit_user_prompt_all_en(text, entity_info, max_relations)
        else:
            system_prompt_explicit = get_explicit_system_prompt_all_de()
            user_msg_explicit = get_explicit_user_prompt_all_de(text, entity_info, max_relations)
    else:
        # Explicit-only mode
        if language == "en":
            system_prompt_explicit = get_explicit_system_prompt_extract_en()
            user_msg_explicit = get_explicit_user_prompt_extract_en(text, entity_info, max_relations)
        else:
            system_prompt_explicit = get_explicit_system_prompt_extract_de()
            user_msg_explicit = get_explicit_user_prompt_extract_de(text, entity_info, max_relations)

    # Log the model being used
    rel_type = "implizite" if mode == "generate" else "explizite"
    logging.info(f"Rufe OpenAI API für {rel_type} Beziehungen auf (Modell {model})...")
    logging.debug(f"[REL_EXP] SYSTEM PROMPT:\n{system_prompt_explicit}")
    logging.debug(f"[REL_EXP] USER MSG:\n{user_msg_explicit}")

    try:
        response_explicit = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt_explicit},
                {"role": "user", "content": user_msg_explicit}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        raw_json_explicit = response_explicit.choices[0].message.content.strip()
        logging.info(f"Erhaltene Antwort (explizit): {raw_json_explicit[:200]}...")
        elapsed_time = time.time() - start_time
        logging.info(f"Erster Prompt abgeschlossen in {elapsed_time:.2f} Sekunden")

        relationships_explicit = extract_json_relationships(raw_json_explicit)
        # Normalize entity names case-insensitively to match extracted entities
        lower_to_name = {name.lower(): name for name in entity_type_map.keys()}
        for rel in relationships_explicit:
            subj_lower = rel.get("subject", "").lower()
            if subj_lower in lower_to_name:
                rel["subject"] = lower_to_name[subj_lower]
            obj_lower = rel.get("object", "").lower()
            if obj_lower in lower_to_name:
                rel["object"] = lower_to_name[obj_lower]
        valid_relationships_explicit = []
        for rel in relationships_explicit:
            if all(k in rel for k in ["subject", "predicate", "object"]):
                # In generate mode, mark all as implicit; else explicit
                inferred_status = "implicit" if mode == "generate" else "explicit"
                rel["inferred"] = inferred_status
                rel["subject_type"] = entity_type_map.get(rel["subject"], "")
                rel["object_type"] = entity_type_map.get(rel["object"], "")
                rel["subject_inferred"] = entity_inferred_map.get(rel["subject"], "explicit")
                rel["object_inferred"] = entity_inferred_map.get(rel["object"], "explicit")
                if rel["subject_type"] and rel["object_type"]:
                    valid_relationships_explicit.append(rel)
        logging.info(f"{len(valid_relationships_explicit)} gültige {rel_type} Beziehungen gefunden")

        # Wenn keine Inferenz gewünscht: Nur explizite Beziehungen zurückgeben
        if not enable_inference:
            # Save relationship training data for explicit relationships if enabled
            if config.get("COLLECT_TRAINING_DATA", False):
                save_relationship_training_data(system_prompt_explicit, user_msg_explicit, valid_relationships_explicit, config)
            return valid_relationships_explicit

        # Implizite Beziehungen (falls enabled)
        if enable_inference:
            if language == "en":
                system_prompt_implicit = get_implicit_system_prompt_en()
                user_msg_implicit = get_implicit_user_prompt_en(text, entity_info, valid_relationships_explicit, max_relations)
            else:
                system_prompt_implicit = get_implicit_system_prompt_de()
                user_msg_implicit = get_implicit_user_prompt_de(text, entity_info, valid_relationships_explicit, max_relations)
        else:
            system_prompt_implicit = None
            user_msg_implicit = None

        logging.info(f"Rufe OpenAI API für implizite Beziehungen auf (Modell {model})...")
        response_implicit = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt_implicit},
                {"role": "user", "content": user_msg_implicit}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        raw_json_implicit = response_implicit.choices[0].message.content.strip()
        logging.info(f"Erhaltene Antwort (implizit): {raw_json_implicit[:200]}...")

        relationships_implicit = extract_json_relationships(raw_json_implicit)
        valid_relationships_implicit = []
        for rel in relationships_implicit:
            if all(k in rel for k in ["subject", "predicate", "object"]):
                rel["inferred"] = "implicit"
                rel["subject_type"] = entity_type_map.get(rel["subject"], "")
                rel["object_type"] = entity_type_map.get(rel["object"], "")
                rel["subject_inferred"] = entity_inferred_map.get(rel["subject"], "explicit")
                rel["object_inferred"] = entity_inferred_map.get(rel["object"], "explicit")
                if rel["subject_type"] and rel["object_type"]:
                    valid_relationships_implicit.append(rel)
        logging.info(f"{len(valid_relationships_implicit)} gültige implizite Beziehungen gefunden")

        # --- Zusammenführen (explizit + implizit, keine Duplikate) ---
        def rel_key(rel):
            return (rel["subject"], rel["predicate"], rel["object"])
        all_relationships = {rel_key(rel): rel for rel in valid_relationships_explicit}
        for rel in valid_relationships_implicit:
            if rel_key(rel) not in all_relationships:
                all_relationships[rel_key(rel)] = rel
        result = list(all_relationships.values())
        logging.info(f"Gesamt: {len(result)} Beziehungen")

        # === LLM-basierte Deduplizierung ähnlicher Beziehungen pro (Subjekt, Objekt) ===
        from collections import defaultdict
        pre_dedup_count = len(result)
        grouped = defaultdict(list)
        for rel in result:
            key = (rel["subject"], rel["object"])
            grouped[key].append(rel)
        deduped_result = []
        for (subj, obj), rels in grouped.items():
            if len(rels) == 1:
                deduped_result.append(rels[0])
                continue
            # Prepare deduplication prompts
            prompt_rels = [
                {"predicate": r["predicate"], "inferred": r.get("inferred", "explicit")} for r in rels
            ]
            lang = config.get("LANGUAGE", "de")
            prompt_rels_json = json.dumps(prompt_rels, ensure_ascii=False)
            if lang == "en":
                system_prompt = get_system_prompt_dedup_relationship_en()
                user_prompt = get_user_prompt_dedup_relationship_en(subj, obj, prompt_rels_json)
            else:
                system_prompt = get_system_prompt_dedup_relationship_de()
                user_prompt = get_user_prompt_dedup_relationship_de(subj, obj, prompt_rels_json)
            # LLM-Call
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0,
                    max_tokens=300
                )
                raw_json = response.choices[0].message.content.strip()
                cleaned = extract_json_relationships(raw_json)
                # Rekonstruiere vollständige Relationseinträge
                for c in cleaned:
                    # Finde Originalrelation mit gleichem Prädikat und inferred
                    match = next((r for r in rels if r["predicate"] == c["predicate"] and r.get("inferred", "explicit") == c.get("inferred", "explicit")), None)
                    if match:
                        deduped_result.append(match)
                    else:
                        # Fallback: baue Relation minimal
                        deduped_result.append({"subject": subj, "object": obj, **c})
                logging.info(f"Dedup: ({subj} -> {obj}) | {len(rels)} → {len(cleaned)} Beziehungen nach LLM-Deduplizierung.")
            except Exception as e:
                logging.error(f"Fehler bei LLM-Deduplizierung für Paar ({subj}, {obj}): {e}")
                deduped_result.extend(rels)
        post_dedup_count = len(deduped_result)
        logging.info(f"Interne LLM-Deduplizierung (Relationship-Inference): Vorher: {pre_dedup_count}, Nachher: {post_dedup_count}")

        # Trainingsdaten für Beziehungsextraktion speichern
        if config.get("COLLECT_TRAINING_DATA", False):
            # Explizite Beziehungen
            save_relationship_training_data(system_prompt_explicit, user_msg_explicit, valid_relationships_explicit, config)
            # Implizite Beziehungen, falls aktiviert
            if config.get("ENABLE_RELATIONS_INFERENCE", False):
                save_relationship_training_data(system_prompt_implicit, user_msg_implicit, valid_relationships_implicit, config)
        return deduped_result

    except Exception as e:
        logging.error(f"Fehler beim Aufruf der OpenAI API: {e}")
        return []

def extract_json_relationships(raw_json):
    # Try to parse as JSON array
    json_start = raw_json.find('[')
    json_end = raw_json.rfind(']') + 1
    if json_start >= 0 and json_end > json_start:
        try:
            return json.loads(raw_json[json_start:json_end])
        except Exception:
            pass
    # Fallback: parse semicolon-separated lines 'subject; predicate; object'
    relationships = []
    for line in raw_json.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(';')]
        if len(parts) >= 3:
            subj, pred, obj = parts[0], parts[1], ';'.join(parts[2:])
            relationships.append({"subject": subj, "predicate": pred, "object": obj})
        else:
            logging.warning(f"Cannot parse relationship line: {line}")
    return relationships
