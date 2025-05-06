# Utility: LLM-basierte Deduplizierung von Beziehungen
import json
from collections import defaultdict
import logging
from openai import OpenAI
from entityextractor.config.settings import get_config
from entityextractor.utils.logging_utils import configure_logging
from entityextractor.services.openai_service import save_relationship_training_data
from entityextractor.prompts.deduplication_prompts import get_system_prompt_dedup_en, get_user_prompt_dedup_en, get_system_prompt_dedup_de, get_user_prompt_dedup_de
from .relationship_inference import extract_json_relationships

def deduplicate_relationships_llm(relationships, entities, user_config=None):
    """
    Bereinigt eine Liste von Beziehungen (Tripeln) per LLM, sodass pro (Entitätenpaar) nur wirklich unterschiedliche Prädikate übrigbleiben.
    Das LLM bekommt ALLE Triple mit identischem Entitätenpaar als Prompt und gibt eine bereinigte Liste zurück, in der semantisch gleiche/ähnliche Prädikate gruppiert und nur die beste Formulierung behalten wird.
    """
    config = get_config(user_config)
    configure_logging(config)
    if not relationships:
        return []
    api_key = config.get("OPENAI_API_KEY")
    if not api_key:
        import os
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logging.error("Kein OpenAI API-Schlüssel angegeben")
            return relationships
    client = OpenAI(api_key=api_key)
    model = config.get("MODEL", "gpt-4.1-mini")
    language = config.get("LANGUAGE", "de")
    # Gruppieren nach Entity-Paar unabhängig von Richtung (beide Richtungen im gleichen Prompt)
    grouped = defaultdict(list)
    for rel in relationships:
        key = frozenset([rel["subject"], rel["object"]])
        grouped[key].append(rel)
    deduped_result = []
    for pair, rels in grouped.items():
        # Für Prompt benötigen wir Subject und Object im Original (Richtung irrelevant)
        subj, obj = tuple(pair)
        if len(rels) == 1:
            deduped_result.append(rels[0])
            continue
        # Alle Prädikate für dieses Paar in den Prompt
        prompt_rels = [
            {"predicate": r["predicate"], "inferred": r.get("inferred", "explicit")} for r in rels
        ]
        prompt_rels_json = json.dumps(prompt_rels, ensure_ascii=False)
        # Zentrale Prompt-Definition verwenden
        if language == "en":
            system_prompt = get_system_prompt_dedup_en()
            user_prompt = get_user_prompt_dedup_en(subj, obj, prompt_rels_json)
        else:
            system_prompt = get_system_prompt_dedup_de()
            user_prompt = get_user_prompt_dedup_de(subj, obj, prompt_rels_json)
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
            for c in cleaned:
                match = next((r for r in rels if r["predicate"] == c["predicate"] and r.get("inferred", "explicit") == c.get("inferred", "explicit")), None)
                if match:
                    deduped_result.append(match)
                else:
                    deduped_result.append({"subject": subj, "object": obj, **c})
            # Kurzdarstellung: Eingabe-Prädikate vs. verbleibende Prädikate
            logging.info(
                f"LLM-Dedup: ({subj} -> {obj}) | {len(rels)} → {len(cleaned)} Beziehungen. "
                f"Eingabe: {[r['predicate'] for r in rels]}; "
                f"Behalten: {[c['predicate'] for c in cleaned]}"
            )
        except Exception as e:
            logging.error(f"Fehler bei LLM-Deduplizierung für Paar ({subj}, {obj}): {e}")
            deduped_result.extend(rels)
    logging.info(f"LLM-Deduplizierung abgeschlossen: Vorher: {len(relationships)}, Nachher: {len(deduped_result)}")
    return deduped_result
