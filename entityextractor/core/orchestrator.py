"""
orchestrator.py

Orchestrates the full entity extraction workflow, including chunking,
entity/relationship deduplication, KGC, legacy packaging, and optional visualization.
"""
import logging
import time
import urllib.parse

from entityextractor.config.settings import get_config
from entityextractor.utils.logging_utils import configure_logging
from entityextractor.utils.text_utils import chunk_text
from entityextractor.utils.category_utils import filter_category_counts

from entityextractor.core.extract_api import extract_and_link
from entityextractor.core.generate_api import generate_and_link, compendium_and_link
from entityextractor.core.link_api import link_entities
from entityextractor.core.relationship_api import infer_entity_relationships
from entityextractor.core.visualization_api import visualize_graph
from entityextractor.core.deduplication_utils import deduplicate_relationships_llm
from entityextractor.core.semantic_dedup_utils import filter_semantically_similar_relationships


def process_entities(input_text: str, user_config: dict = None):
    """
    Delegates to extraction/generation, linking, optional relation inference,
    chunking with deduplication, KGC, legacy packaging, and visualization.
    """
    config = get_config(user_config)
    configure_logging(config)
    start = time.time()
    mode = config.get("MODE", "extract")
    logging.info("[orchestrator] Starting process: MODE=%s", mode)

    # chunking path
    if config.get("TEXT_CHUNKING", False):
        size = config.get("TEXT_CHUNK_SIZE", 2000)
        overlap = config.get("TEXT_CHUNK_OVERLAP", 50)
        logging.info("[orchestrator] Chunking: size=%d, overlap=%d", size, overlap)
        chunks = chunk_text(input_text, size, overlap)
        all_ents, all_rels = [], []
        for i, c in enumerate(chunks, 1):
            logging.info("[orchestrator] Chunk %d/%d", i, len(chunks))
            if mode == "compendium":
                ents = compendium_and_link(c, config)
            elif mode == "generate":
                ents = generate_and_link(c, config)
            else:
                ents = extract_and_link(c, config)
            all_ents.extend(ents)
            if config.get("RELATION_EXTRACTION", False):
                r = infer_entity_relationships(c, ents, config)
                all_rels.extend(r)
        # dedup entities
        deduped_ents, seen = [], set()
        for e in all_ents:
            k = e.get("wikipedia_url") or e.get("name")
            if k and k not in seen:
                seen.add(k)
                deduped_ents.append(e)
        # dedup relationships explicit>implicit
        rel_map = {}
        for r in all_rels:
            k = (r.get("subject"), r.get("predicate"), r.get("object"))
            if k in rel_map:
                ex = rel_map[k]
                if ex.get("inferred") == "implicit" and r.get("inferred") == "explicit":
                    rel_map[k] = r
            else:
                rel_map[k] = r
        deduped_rels = list(rel_map.values())
        # LLM dedup
        deduped_rels = deduplicate_relationships_llm(deduped_rels, deduped_ents, config)
        # semantic dedup
        deduped_rels = filter_semantically_similar_relationships(deduped_rels, similarity_threshold=0.85)
        # packaging
        result = {"entities": [], "relationships": deduped_rels}
        for e in deduped_ents:
            cit = e.get("citation", input_text)
            s = input_text.find(cit) if cit != input_text else 0
            t = s + len(cit) if s != -1 else len(input_text)
            leg = {"entity": e.get("name", ""),
                   "details": {"typ": e.get("type", ""),
                                "inferred": e.get("inferred", "explicit"),
                                "citation": cit,
                                "citation_start": s,
                                "citation_end": t},
                   "sources": {}}
            # wikipedia
            if e.get("wikipedia_url"):
                ws = leg["sources"].setdefault("wikipedia", {})
                if e.get("wikipedia_title"):
                    ws["label"] = e.get("wikipedia_title")
                else:
                    # Fallback: derive label from URL
                    from urllib.parse import unquote
                    raw = e.get("wikipedia_url").split("/wiki/")[-1].split("#")[0]
                    title = unquote(raw).replace("_", " ")
                    ws["label"] = title
                ws["url"] = e.get("wikipedia_url")
                if e.get("wikipedia_extract"):
                    ws["extract"] = e.get("wikipedia_extract")
                if e.get("wikipedia_categories"):
                    ws["categories"] = e.get("wikipedia_categories")
                # Zusätzliche Wikipedia-Details bei ADDITIONAL_DETAILS (flatten)
                if config.get("ADDITIONAL_DETAILS", False) and e.get("wikipedia_details"):
                    for key, value in e["wikipedia_details"].items():
                        ws[key] = value
            # wikidata
            if config.get("USE_WIKIDATA", False) and e.get("wikidata_details"):
                wd_src = leg["sources"].setdefault("wikidata", {})
                # Basisfelder
                wd_src["id"] = e["wikidata_details"].get("id", "")
                if "description" in e["wikidata_details"]:
                    wd_src["description"] = e["wikidata_details"]["description"]
                if "types" in e["wikidata_details"]:
                    wd_src["types"] = e["wikidata_details"]["types"]
                if e.get("wikidata_url"):
                    wd_src["url"] = e.get("wikidata_url")
                if "label" in e["wikidata_details"]:
                    wd_src["label"] = e["wikidata_details"]["label"]
                # Zusätzliche Wikidata-Felder bei ADDITIONAL_DETAILS
                if config.get("ADDITIONAL_DETAILS", False):
                    for key in ["aliases","instance_of","subclass_of","part_of","has_parts","member_of","gnd_id","isni","official_name","citizenship","citizenships","image_url","website","coordinates","foundation_date","birth_date","death_date","birth_place","death_place","population","area","country","region","founder","parent_company"]:
                        if key in e["wikidata_details"]:
                            wd_src[key] = e["wikidata_details"][key]
            # dbpedia
            if config.get("USE_DBPEDIA", False):
                if e.get("dbpedia_info"):
                    bd = e["dbpedia_info"]
                    db_src = leg["sources"].setdefault("dbpedia", {})
                    # Basisfelder
                    db_src["resource_uri"] = bd.get("resource_uri", bd.get("uri", ""))
                    if "endpoint" in bd:
                        db_src["endpoint"] = bd["endpoint"]
                    if "language" in bd:
                        db_src["language"] = bd["language"]
                    if "label" in bd:
                        db_src["label"] = bd["label"]
                    if "abstract" in bd:
                        db_src["abstract"] = bd["abstract"]
                    if "types" in bd:
                        db_src["types"] = bd["types"]
                    if "same_as" in bd:
                        db_src["same_as"] = bd["same_as"]
                    if "subject" in bd:
                        db_src["subjects"] = bd["subject"]
                    elif "subjects" in bd:
                        db_src["subjects"] = bd["subjects"]
                    if "part_of" in bd:
                        db_src["part_of"] = bd["part_of"]
                    if "has_parts" in bd:
                        db_src["has_parts"] = bd["has_parts"]
                    if "member_of" in bd:
                        db_src["member_of"] = bd["member_of"]
                    if "category" in bd:
                        db_src["categories"] = bd["category"]
                    elif "categories" in bd:
                        db_src["categories"] = bd["categories"]
                    # Zusätzliche DBpedia-Felder bei ADDITIONAL_DETAILS
                    if config.get("ADDITIONAL_DETAILS", False):
                        for key in ["comment","homepage","thumbnail","depiction","lat","long","birth_date","death_date","birth_place","death_place","population","area","country","region","foundation_date","founder","parent_company","current_member","former_member","dbp_part_of","dbp_member_of"]:
                            if key in bd:
                                if key in ("lat","long"):
                                    if "coordinates" not in db_src:
                                        db_src["coordinates"] = {}
                                    coord_key = "latitude" if key == "lat" else "longitude"
                                    db_src["coordinates"][coord_key] = bd[key]
                                else:
                                    db_src[key] = bd[key]
                elif e.get("dbpedia_uri"):
                    db_src = leg["sources"].setdefault("dbpedia", {})
                    db_src["resource_uri"] = e.get("dbpedia_uri")
                    db_src["language"] = e.get("dbpedia_language")
            result["entities"].append(leg)
        # Knowledge Graph Completion for chunked input
        if config.get("ENABLE_KGC", False):
            rounds = config.get("KGC_ROUNDS", 3)
            logging.info("[orchestrator] KGC for chunked: Rounds=%d", rounds)
            ex_map = {(r["subject"], r["predicate"], r["object"]): r for r in result["relationships"]}
            for rnd in range(1, rounds + 1):
                logging.info("[orchestrator] KGC round %d/%d (chunked)", rnd, rounds)
                cfg = config.copy()
                cfg["existing_relationships"] = list(ex_map.values())
                new_rels = infer_entity_relationships(input_text, deduped_ents, cfg)
                added = 0
                for nr in new_rels:
                    k = (nr.get("subject"), nr.get("predicate"), nr.get("object"))
                    if k not in ex_map:
                        ex_map[k] = nr
                        added += 1
                logging.info("[orchestrator] KGC round %d (chunked): %d new relationships", rnd, added)
            final_rels = list(ex_map.values())
            final_rels = list({(r["subject"], r["predicate"], r["object"]): r for r in final_rels}.values())
            final_rels = deduplicate_relationships_llm(final_rels, deduped_ents, config)
            final_rels = filter_semantically_similar_relationships(final_rels, similarity_threshold=0.85)
            result["relationships"] = final_rels
        # visualization
        if config.get("ENABLE_GRAPH_VISUALIZATION", False):
            if not result.get("relationships"):
                logging.error("[orchestrator] Graph visualization aborted: no relationships available.")
                result["knowledgegraph_visualisation"] = []
            else:
                vis = visualize_graph(result, config)
                result["knowledgegraph_visualisation"] = [{"static": vis.get("png"), "interactive": vis.get("html")}]
        logging.info("[orchestrator] Chunking flow done in %.2f sec", time.time()-start)
        if config.get("COLLECT_TRAINING_DATA", False):
            result["trainingsdata"] = {
                "entity_training_file": config.get("OPENAI_TRAINING_DATA_PATH"),
                "relationship_training_file": config.get("OPENAI_RELATIONSHIP_TRAINING_DATA_PATH"),
            }
        # Statistik-Bereich
        stats = {}
        total = len(result["entities"])
        stats["total_entities"] = total
        # Typverteilung
        type_counts = {}
        for e in result["entities"]:
            t = e.get("details", {}).get("typ", "")
            type_counts[t] = type_counts.get(t, 0) + 1
        stats["types_distribution"] = type_counts
        # Linking-Erfolg
        linked = {}
        if total > 0:
            wiki_count = sum(1 for e in result["entities"] if "wikipedia" in e.get("sources", {}))
            wikidata_count = sum(1 for e in result["entities"] if "wikidata" in e.get("sources", {}))
            dbpedia_count = sum(1 for e in result["entities"] if "dbpedia" in e.get("sources", {}))
            linked["wikipedia"] = {"count": wiki_count, "percent": wiki_count * 100 / total}
            linked["wikidata"] = {"count": wikidata_count, "percent": wikidata_count * 100 / total}
            linked["dbpedia"] = {"count": dbpedia_count, "percent": dbpedia_count * 100 / total}
        else:
            linked["wikipedia"] = {"count": 0, "percent": 0}
            linked["wikidata"] = {"count": 0, "percent": 0}
            linked["dbpedia"] = {"count": 0, "percent": 0}
        stats["linked"] = linked
        # Top-Kategorien
        cat_counts = {}
        for e in result["entities"]:
            cats = e.get("sources", {}).get("wikipedia", {}).get("categories", [])
            for cat in cats:
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
        filtered_cat_counts = filter_category_counts(cat_counts)
        top_cats = sorted(filtered_cat_counts.items(), key=lambda x: -x[1])[:10]
        stats["top_wikipedia_categories"] = [{"category": c, "count": n} for c, n in top_cats]
        # Top-Wikidata-Types
        wd_counts = {}
        for e in result["entities"]:
            types = e.get("sources", {}).get("wikidata", {}).get("types", [])
            for ty in types:
                wd_counts[ty] = wd_counts.get(ty, 0) + 1
        top_wd = sorted(wd_counts.items(), key=lambda x: -x[1])[:10]
        stats["top_wikidata_types"] = [{"type": ty, "count": n} for ty, n in top_wd]
        # Top-Wikidata part_of
        wdpo_counts = {}
        for e in result["entities"]:
            pos = e.get("sources", {}).get("wikidata", {}).get("part_of", [])
            if isinstance(pos, list):
                for po in pos:
                    wdpo_counts[po] = wdpo_counts.get(po, 0) + 1
            elif pos:
                wdpo_counts[pos] = wdpo_counts.get(pos, 0) + 1

        top_wd_po = sorted(wdpo_counts.items(), key=lambda x: -x[1])[:10]
        stats["top_wikidata_part_of"] = [{"part_of": po, "count": n} for po, n in top_wd_po]
        # Top-Wikidata has_parts
        wdhp_counts = {}
        for e in result["entities"]:
            hps = e.get("sources", {}).get("wikidata", {}).get("has_parts", [])
            if isinstance(hps, list):
                for hp in hps:
                    wdhp_counts[hp] = wdhp_counts.get(hp, 0) + 1
            elif hps:
                wdhp_counts[hps] = wdhp_counts.get(hps, 0) + 1

        top_wd_hp = sorted(wdhp_counts.items(), key=lambda x: -x[1])[:10]
        stats["top_wikidata_has_parts"] = [{"has_parts": hp, "count": n} for hp, n in top_wd_hp]
        # Top-DBpedia-Subjects
        sub_counts = {}
        for e in result["entities"]:
            subs = e.get("sources", {}).get("dbpedia", {}).get("subjects", [])
            for sub in subs:
                sub_counts[sub] = sub_counts.get(sub, 0) + 1
        top_sub = sorted(sub_counts.items(), key=lambda x: -x[1])[:10]
        stats["top_dbpedia_subjects"] = [{"subject": s, "count": n} for s, n in top_sub]
        # Top-DBpedia part_of
        dbpo_counts = {}
        for e in result["entities"]:
            pos = e.get("sources", {}).get("dbpedia", {}).get("part_of", [])
            if isinstance(pos, list):
                for po in pos:
                    dbpo_counts[po] = dbpo_counts.get(po, 0) + 1
            elif pos:
                dbpo_counts[pos] = dbpo_counts.get(pos, 0) + 1

        top_dbpo = sorted(dbpo_counts.items(), key=lambda x: -x[1])[:10]
        stats["top_dbpedia_part_of"] = [{"part_of": po, "count": n} for po, n in top_dbpo]
        # Top-DBpedia has_parts
        dbhp_counts = {}
        for e in result["entities"]:
            hps = e.get("sources", {}).get("dbpedia", {}).get("has_parts", [])
            if isinstance(hps, list):
                for hp in hps:
                    dbhp_counts[hp] = dbhp_counts.get(hp, 0) + 1
            elif hps:
                dbhp_counts[hps] = dbhp_counts.get(hps, 0) + 1

        top_dbhp = sorted(dbhp_counts.items(), key=lambda x: -x[1])[:10]
        stats["top_dbpedia_has_parts"] = [{"has_parts": hp, "count": n} for hp, n in top_dbhp]
        # Entity connection counts
        conn_map = {}
        for r in result["relationships"]:
            subj = r.get("subject")
            obj = r.get("object")
            if subj and obj:
                conn_map.setdefault(subj, set()).add(obj)
                conn_map.setdefault(obj, set()).add(subj)
        entity_conn_list = [{"entity": ent, "count": len(neighbors)} for ent, neighbors in conn_map.items()]
        entity_conn_list.sort(key=lambda x: -x["count"])
        stats["entity_connections"] = entity_conn_list
        result["statistics"] = stats
        return result

    # single-pass flow
    if mode == "compendium":
        ents = compendium_and_link(input_text, config)
    elif mode == "generate":
        ents = generate_and_link(input_text, config)
    else:
        ents = extract_and_link(input_text, config)
    rels = []
    if config.get("RELATION_EXTRACTION", False):
        logging.info("[orchestrator] Starting single-pass relation extraction")
        # Build context for relationship inference
        if mode in ("generate", "compendium") and all(e.get("wikipedia_extract") for e in ents):
            rel_context = "\n".join(e.get("wikipedia_extract") for e in ents)
        else:
            rel_context = input_text
        rels = infer_entity_relationships(rel_context, ents, config)
        # LLM dedup
        rels = deduplicate_relationships_llm(rels, ents, config)
        # semantic dedup
        rels = filter_semantically_similar_relationships(rels, similarity_threshold=0.85)
    # package entities and relationships
    result = {"entities": [], "relationships": rels}
    for e in ents:
        cit = e.get("citation", input_text)
        s = input_text.find(cit) if cit != input_text else 0
        t = s + len(cit) if s != -1 else len(input_text)
        leg = {"entity": e.get("name",""),
               "details": {"typ": e.get("type",""),
                            "inferred": e.get("inferred","explicit"),
                            "citation": cit,
                            "citation_start": s,
                            "citation_end": t},
               "sources": {}}
        if e.get("wikipedia_url"):
            ws = leg["sources"].setdefault("wikipedia", {})
            if e.get("wikipedia_title"):
                ws["label"] = e.get("wikipedia_title")
            else:
                # Fallback: derive label from URL
                from urllib.parse import unquote
                raw = e.get("wikipedia_url").split("/wiki/")[-1].split("#")[0]
                title = unquote(raw).replace("_", " ")
                ws["label"] = title
            ws["url"] = e.get("wikipedia_url")
            if e.get("wikipedia_extract"):
                ws["extract"] = e.get("wikipedia_extract")
            if e.get("wikipedia_categories"):
                ws["categories"] = e.get("wikipedia_categories")
            # Zusätzliche Wikipedia-Details bei ADDITIONAL_DETAILS (flatten)
            if config.get("ADDITIONAL_DETAILS", False) and e.get("wikipedia_details"):
                for key, value in e["wikipedia_details"].items():
                    ws[key] = value
        # Wikidata-Quellen auch im Single-Pass
        if config.get("USE_WIKIDATA", False) and e.get("wikidata_details"):
            wd_src = leg["sources"].setdefault("wikidata", {})
            # Basisfelder
            wd_src["id"] = e["wikidata_details"].get("id", "")
            if "description" in e["wikidata_details"]:
                wd_src["description"] = e["wikidata_details"]["description"]
            if "types" in e["wikidata_details"]:
                wd_src["types"] = e["wikidata_details"]["types"]
            if e.get("wikidata_url"):
                wd_src["url"] = e.get("wikidata_url")
            if "label" in e["wikidata_details"]:
                wd_src["label"] = e["wikidata_details"]["label"]
            # Zusätzliche Wikidata-Felder bei ADDITIONAL_DETAILS
            if config.get("ADDITIONAL_DETAILS", False):
                for key in ["aliases","instance_of","subclass_of","part_of","has_parts","member_of","gnd_id","isni","official_name","citizenship","citizenships","image_url","website","coordinates","foundation_date","birth_date","death_date","birth_place","death_place","population","area","country","region","founder","parent_company"]:
                    if key in e["wikidata_details"]:
                        wd_src[key] = e["wikidata_details"][key]
        # DBpedia-Quellen auch im Single-Pass
        if config.get("USE_DBPEDIA", False):
            if e.get("dbpedia_info"):
                bd = e.get("dbpedia_info")
                db_src = leg["sources"].setdefault("dbpedia", {})
                # Basisfelder
                db_src["resource_uri"] = bd.get("resource_uri", bd.get("uri", ""))
                if "endpoint" in bd:
                    db_src["endpoint"] = bd["endpoint"]
                if "language" in bd:
                    db_src["language"] = bd["language"]
                if "label" in bd:
                    db_src["label"] = bd["label"]
                if "abstract" in bd:
                    db_src["abstract"] = bd["abstract"]
                if "types" in bd:
                    db_src["types"] = bd["types"]
                if "same_as" in bd:
                    db_src["same_as"] = bd["same_as"]
                if "subject" in bd:
                    db_src["subjects"] = bd["subject"]
                elif "subjects" in bd:
                    db_src["subjects"] = bd["subjects"]
                if "part_of" in bd:
                    db_src["part_of"] = bd["part_of"]
                if "has_parts" in bd:
                    db_src["has_parts"] = bd["has_parts"]
                if "member_of" in bd:
                    db_src["member_of"] = bd["member_of"]
                if "category" in bd:
                    db_src["categories"] = bd["category"]
                elif "categories" in bd:
                    db_src["categories"] = bd["categories"]
                # Zusätzliche DBpedia-Felder bei ADDITIONAL_DETAILS
                if config.get("ADDITIONAL_DETAILS", False):
                    for key in ["comment","homepage","thumbnail","depiction","lat","long","birth_date","death_date","birth_place","death_place","population","area","country","region","foundation_date","founder","parent_company","current_member","former_member","dbp_part_of","dbp_member_of"]:
                        if key in bd:
                            if key in ("lat","long"):
                                if "coordinates" not in db_src:
                                    db_src["coordinates"] = {}
                                coord_key = "latitude" if key == "lat" else "longitude"
                                db_src["coordinates"][coord_key] = bd[key]
                            else:
                                db_src[key] = bd[key]
            elif e.get("dbpedia_uri"):
                db_src = leg["sources"].setdefault("dbpedia", {})
                db_src["resource_uri"] = e.get("dbpedia_uri")
                db_src["language"] = e.get("dbpedia_language")
        result["entities"].append(leg)
    # Knowledge Graph Completion (KGC) at end
    if config.get("ENABLE_KGC", False):
        rounds = config.get("KGC_ROUNDS", 3)
        logging.info("[orchestrator] KGC final: Rounds=%d", rounds)
        ex_map = {(r["subject"], r["predicate"], r["object"]): r for r in result["relationships"]}
        for rnd in range(1, rounds + 1):
            logging.info("[orchestrator] KGC round %d/%d", rnd, rounds)
            cfg = config.copy()
            cfg["existing_relationships"] = list(ex_map.values())
            new_rels = infer_entity_relationships(input_text, ents, cfg)
            added = 0
            for nr in new_rels:
                k = (nr.get("subject"), nr.get("predicate"), nr.get("object"))
                if k not in ex_map:
                    ex_map[k] = nr
                    added += 1
            logging.info("[orchestrator] KGC round %d: %d new relationships", rnd, added)
        # after all rounds, deduplicate
        final_rels = list(ex_map.values())
        final_rels = list({(r["subject"], r["predicate"], r["object"]): r for r in final_rels}.values())
        final_rels = deduplicate_relationships_llm(final_rels, ents, config)
        final_rels = filter_semantically_similar_relationships(final_rels, similarity_threshold=0.85)
        result["relationships"] = final_rels
    # visualization if enabled
    if config.get("ENABLE_GRAPH_VISUALIZATION", False):
        if not result.get("relationships"):
            logging.error("[orchestrator] Graph visualization aborted: no relationships available.")
            result["knowledgegraph_visualisation"] = []
        else:
            vis = visualize_graph(result, config)
            result["knowledgegraph_visualisation"] = [{"static": vis.get("png"), "interactive": vis.get("html")}]
    logging.info("[orchestrator] Single-pass done in %.2f sec", time.time()-start)
    if config.get("COLLECT_TRAINING_DATA", False):
        result["trainingsdata"] = {
            "entity_training_file": config.get("OPENAI_TRAINING_DATA_PATH"),
            "relationship_training_file": config.get("OPENAI_RELATIONSHIP_TRAINING_DATA_PATH"),
        }
    # Statistik-Bereich
    stats = {}
    total = len(result["entities"])
    stats["total_entities"] = total
    # Typverteilung
    type_counts = {}
    for e in result["entities"]:
        t = e.get("details", {}).get("typ", "")
        type_counts[t] = type_counts.get(t, 0) + 1
    stats["types_distribution"] = type_counts
    # Linking-Erfolg
    linked = {}
    if total > 0:
        wiki_count = sum(1 for e in result["entities"] if "wikipedia" in e.get("sources", {}))
        wikidata_count = sum(1 for e in result["entities"] if "wikidata" in e.get("sources", {}))
        dbpedia_count = sum(1 for e in result["entities"] if "dbpedia" in e.get("sources", {}))
        linked["wikipedia"] = {"count": wiki_count, "percent": wiki_count * 100 / total}
        linked["wikidata"] = {"count": wikidata_count, "percent": wikidata_count * 100 / total}
        linked["dbpedia"] = {"count": dbpedia_count, "percent": dbpedia_count * 100 / total}
    else:
        linked["wikipedia"] = {"count": 0, "percent": 0}
        linked["wikidata"] = {"count": 0, "percent": 0}
        linked["dbpedia"] = {"count": 0, "percent": 0}
    stats["linked"] = linked
    # Top-Kategorien
    cat_counts = {}
    for e in result["entities"]:
        cats = e.get("sources", {}).get("wikipedia", {}).get("categories", [])
        for cat in cats:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
    filtered_cat_counts = filter_category_counts(cat_counts)
    top_cats = sorted(filtered_cat_counts.items(), key=lambda x: -x[1])[:10]
    stats["top_wikipedia_categories"] = [{"category": c, "count": n} for c, n in top_cats]
    # Top-Wikidata-Types
    wd_counts = {}
    for e in result["entities"]:
        types = e.get("sources", {}).get("wikidata", {}).get("types", [])
        for ty in types:
            wd_counts[ty] = wd_counts.get(ty, 0) + 1
    top_wd = sorted(wd_counts.items(), key=lambda x: -x[1])[:10]
    stats["top_wikidata_types"] = [{"type": ty, "count": n} for ty, n in top_wd]
    # Top-Wikidata part_of
    wdpo_counts = {}
    for e in result["entities"]:
        pos = e.get("sources", {}).get("wikidata", {}).get("part_of", [])
        if isinstance(pos, list):
            for po in pos:
                wdpo_counts[po] = wdpo_counts.get(po, 0) + 1
        elif pos:
            wdpo_counts[pos] = wdpo_counts.get(pos, 0) + 1

    top_wd_po = sorted(wdpo_counts.items(), key=lambda x: -x[1])[:10]
    stats["top_wikidata_part_of"] = [{"part_of": po, "count": n} for po, n in top_wd_po]
    # Top-Wikidata has_parts
    wdhp_counts = {}
    for e in result["entities"]:
        hps = e.get("sources", {}).get("wikidata", {}).get("has_parts", [])
        if isinstance(hps, list):
            for hp in hps:
                wdhp_counts[hp] = wdhp_counts.get(hp, 0) + 1
        elif hps:
            wdhp_counts[hps] = wdhp_counts.get(hps, 0) + 1

    top_wd_hp = sorted(wdhp_counts.items(), key=lambda x: -x[1])[:10]
    stats["top_wikidata_has_parts"] = [{"has_parts": hp, "count": n} for hp, n in top_wd_hp]
    # Top-DBpedia-Subjects
    sub_counts = {}
    for e in result["entities"]:
        subs = e.get("sources", {}).get("dbpedia", {}).get("subjects", [])
        for sub in subs:
            sub_counts[sub] = sub_counts.get(sub, 0) + 1
    top_sub = sorted(sub_counts.items(), key=lambda x: -x[1])[:10]
    stats["top_dbpedia_subjects"] = [{"subject": s, "count": n} for s, n in top_sub]
    # Top-DBpedia part_of
    dbpo_counts = {}
    for e in result["entities"]:
        pos = e.get("sources", {}).get("dbpedia", {}).get("part_of", [])
        if isinstance(pos, list):
            for po in pos:
                dbpo_counts[po] = dbpo_counts.get(po, 0) + 1
        elif pos:
            dbpo_counts[pos] = dbpo_counts.get(pos, 0) + 1

    top_dbpo = sorted(dbpo_counts.items(), key=lambda x: -x[1])[:10]
    stats["top_dbpedia_part_of"] = [{"part_of": po, "count": n} for po, n in top_dbpo]
    # Top-DBpedia has_parts
    dbhp_counts = {}
    for e in result["entities"]:
        hps = e.get("sources", {}).get("dbpedia", {}).get("has_parts", [])
        if isinstance(hps, list):
            for hp in hps:
                dbhp_counts[hp] = dbhp_counts.get(hp, 0) + 1
        elif hps:
            dbhp_counts[hps] = dbhp_counts.get(hps, 0) + 1

    top_dbhp = sorted(dbhp_counts.items(), key=lambda x: -x[1])[:10]
    stats["top_dbpedia_has_parts"] = [{"has_parts": hp, "count": n} for hp, n in top_dbhp]
    # Entity connection counts
    conn_map = {}
    for r in result["relationships"]:
        subj = r.get("subject")
        obj = r.get("object")
        if subj and obj:
            conn_map.setdefault(subj, set()).add(obj)
            conn_map.setdefault(obj, set()).add(subj)
    entity_conn_list = [{"entity": ent, "count": len(neighbors)} for ent, neighbors in conn_map.items()]
    entity_conn_list.sort(key=lambda x: -x["count"])
    stats["entity_connections"] = entity_conn_list
    result["statistics"] = stats
    return result
