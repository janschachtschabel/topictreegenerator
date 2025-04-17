"""
Funktionen zur Generierung von Frage-Antwort-Paaren.
"""
import json
import backoff
import streamlit as st
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI, RateLimitError, APIError

from .models import QACollection, QAPair
from .utils import get_json_files, load_json_file, save_json_with_timestamp, count_nodes

def generate_qa_pairs(client: OpenAI, collection: dict, metadata: dict, 
                     num_questions: int = 10, include_compendium: bool = False,
                     include_entities: bool = False, average_qa_length: int = 200,
                     model: str = "gpt-4.1-mini") -> QACollection:
    """
    Generiert Frage-Antwort-Paare für eine Sammlung.
    Verwendet Pydantic-Modelle für strukturierte Ausgabe.
    
    Args:
        client: OpenAI Client
        collection: Die zu verarbeitende Sammlung
        metadata: Metadaten des Themenbaums
        num_questions: Anzahl der zu generierenden Fragen
        include_compendium: Ob das Kompendium einbezogen werden soll
        include_entities: Ob Entitäten einbezogen werden sollen
        average_qa_length: Durchschnittliche Länge der Antworten
        model: Das zu verwendende LLM-Modell
        
    Returns:
        QACollection: Eine Sammlung von Frage-Antwort-Paaren
    """
    # Sammle Kontext-Informationen
    title = collection.get("title", "")
    
    # Sammle Beschreibungen aus Properties
    description = ""
    if "properties" in collection and "cm:description" in collection["properties"]:
        description = collection["properties"]["cm:description"][0] if collection["properties"]["cm:description"] else ""
    
    # Sammle Keywords aus Properties
    keywords = []
    if "properties" in collection and "cclom:general_keyword" in collection["properties"]:
        keywords = collection["properties"]["cclom:general_keyword"]
    
    collection_info = {
        "title": title,
        "description": description,
        "keywords": keywords,
        "metadata": metadata
    }
    
    # Texte aus additional_data mit Priorität:
    # 1. Kompendiale Texte, 2. Erweiterte Texte, 3. Basisdaten
    additional_text = ""
    source_description = "Basisdaten (Titel, Beschreibung)"
    
    if "additional_data" in collection:
        if include_compendium and "compendium_text" in collection["additional_data"]:
            # Priorität 1: Verwende kompendialen Text
            additional_text = collection["additional_data"]["compendium_text"]
            source_description = "Kompendialer Text"
        elif "extended_text" in collection["additional_data"]:
            # Priorität 2: Verwende erweiterten Text
            additional_text = collection["additional_data"]["extended_text"]
            source_description = "Erweiterter Text"
    
    # Entitäten-Informationen (nur wenn kein kompendialer Text verwendet wird oder explizit angefordert)
    entities_info = ""
    if include_entities and "additional_data" in collection and "entities" in collection["additional_data"]:
        entities = collection["additional_data"]["entities"]
        entities_descriptions = []
        
        for entity in entities:
            entity_info = f"Entität: {entity.get('entity', '')}\n"
            entity_info += f"Typ: {entity.get('details', {}).get('typ', 'Unbekannt')}\n"
            
            # Füge Informationen aus Quellen hinzu
            sources = entity.get('sources', {})
            
            # Wikipedia-Inhalte
            if "wikipedia" in sources and "extract" in sources["wikipedia"]:
                entity_info += f"Wikipedia: {sources['wikipedia']['extract']}\n"
            
            # Wikidata-Informationen
            if "wikidata" in sources and "description" in sources["wikidata"]:
                entity_info += f"Wikidata: {sources['wikidata']['description']}\n"
            
            # DBpedia-Informationen
            if "dbpedia" in sources and "abstract" in sources["dbpedia"]:
                entity_info += f"DBpedia: {sources['dbpedia']['abstract']}\n"
            
            entities_descriptions.append(entity_info)
        
        entities_info = "\n\n".join(entities_descriptions)
    
    # Wenn kompendiale Texte verwendet werden, ignoriere Entitäten-Informationen
    if source_description == "Kompendialer Text":
        entities_info = ""
    
    # Erstelle Prompt mit klaren Anweisungen für JSON-Format
    prompt = f"""Generiere {num_questions} Frage-Antwort-Paare für das Thema '{title}'.
    
Wichtig: 
- Antworte NUR mit validem JSON
- Vermeide Zeilenumbrüche in Strings
- Escape alle Sonderzeichen korrekt
- Halte die Antworten präzise, etwa {average_qa_length} Zeichen pro Antwort

Kontext zum Thema:
{json.dumps(collection_info, ensure_ascii=False)}

Haupttext ({source_description}):
{additional_text}

"""
    
    # Füge Entitäten-Informationen hinzu, falls vorhanden und relevant
    if entities_info:
        prompt += f"""
Zusätzliche Entitäten-Informationen:
{entities_info}
"""

    @backoff.on_exception(backoff.expo, (RateLimitError, APIError), max_tries=5, jitter=backoff.full_jitter)
    def call_openai():
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Du bist ein Experte für die Generierung von Frage-Antwort-Paaren. Antworte NUR mit validem JSON."},
                {"role": "user", "content": prompt}
            ],
            functions=[{
                "name": "create_qa_pairs",
                "description": "Erstellt eine Sammlung von Frage-Antwort-Paaren",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "qa_pairs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {"type": "string"},
                                    "answer": {"type": "string"}
                                },
                                "required": ["question", "answer"]
                            }
                        }
                    },
                    "required": ["qa_pairs"]
                }
            }],
            function_call={"name": "create_qa_pairs"}
        )
        return response
    
    # Führe Anfrage mit Backoff aus
    try:
        response = call_openai()
        json_response = json.loads(response.choices[0].message.function_call.arguments)
        
        # Erstelle QA-Collection
        qa_pairs = []
        for qa in json_response.get("qa_pairs", []):
            question = qa.get("question", "")
            answer = qa.get("answer", "")
            
            # Ignoriere leere Fragen/Antworten
            if question and answer:
                qa_pairs.append(QAPair(question=question, answer=answer))
                
        return QACollection(
            qa_pairs=qa_pairs,
            topic=title,
            metadata={
                "generation_time": datetime.now().isoformat(),
                "model": model,
                "source": source_description
            }
        )
    except Exception as e:
        print(f"Fehler bei der Q&A-Generierung: {e}")
        # Leere QA-Collection bei Fehler
        return QACollection(qa_pairs=[], topic=title)

def process_node_qa(client: OpenAI, node: dict, metadata: dict,
                   progress_bar: st.progress, progress_text: st.empty,
                   current: int, total: int, start_percent: float, end_percent: float,
                   num_questions: int = 10, include_compendium: bool = False,
                   include_entities: bool = False, model: str = "gpt-4.1-mini") -> int:
    """
    Verarbeitet QA-Generierung für einen Node und seine Unterknoten.
    
    Args:
        client: OpenAI Client
        node: Der zu verarbeitende Knoten
        metadata: Metadaten des Themenbaums
        progress_bar: Streamlit Fortschrittsbalken
        progress_text: Streamlit Textfeld für Status
        current: Aktueller Fortschritt
        total: Gesamtanzahl der Knoten
        start_percent: Startprozent für diesen Knoten
        end_percent: Endprozent für diesen Knoten
        num_questions: Anzahl der Fragen pro Knoten
        include_compendium: Ob das Kompendium einbezogen werden soll
        include_entities: Ob Entitäten einbezogen werden sollen
        model: Das zu verwendende LLM-Modell
        
    Returns:
        int: Aktualisierter Fortschrittszähler
    """
    if not isinstance(node, dict) or "title" not in node:
        return current

    # Aktualisiere Fortschritt für aktuellen Node
    current_percent = start_percent + (current / total) * (end_percent - start_percent)
    progress_bar.progress(current_percent)
    progress_text.text(f"Generiere Fragen für: {node['title']}")
    
    try:
        qa_pairs = generate_qa_pairs(
            client=client,
            collection=node,
            metadata=metadata,
            num_questions=num_questions,
            include_compendium=include_compendium,
            include_entities=include_entities,
            model=model
        )
        
        # Speichere QA-Paare
        if qa_pairs:
            if "additional_data" not in node:
                node["additional_data"] = {}
            node["additional_data"]["qa_pairs"] = qa_pairs.to_dict()
            st.write(f"Q&A generiert für: {node['title']}")
        
        current += 1
        
    except Exception as e:
        st.error(f"Fehler bei QA-Generierung für '{node['title']}': {str(e)}")
    
    # Rekursiv für alle Untersammlungen
    if "subcollections" in node and isinstance(node["subcollections"], list):
        subcollections = node["subcollections"]
        num_subcollections = len(subcollections)
        
        if num_subcollections > 0:
            # Berechne Fortschrittsbereich für Untersammlungen
            remaining_percent = end_percent - start_percent
            sub_range = remaining_percent / num_subcollections
            
            for i, subcoll in enumerate(subcollections):
                sub_start = start_percent + i * sub_range
                sub_end = start_percent + (i + 1) * sub_range
                
                current = process_node_qa(
                    client=client,
                    node=subcoll,
                    metadata=metadata,
                    progress_bar=progress_bar,
                    progress_text=progress_text,
                    current=current,
                    total=total,
                    start_percent=sub_start,
                    end_percent=sub_end,
                    num_questions=num_questions,
                    include_compendium=include_compendium,
                    include_entities=include_entities,
                    model=model
                )
    
    return current

def show_qa_page(openai_key: str, model: str):
    """
    Seite für die Q&A-Generierung.
    
    Args:
        openai_key: OpenAI API-Key
        model: Zu verwendendes LLM-Modell
    """
    st.title("❓ Frage-Antwort-Paare generieren")
    st.write("Erstelle automatisch Fragesets für jeden Knoten des Themenbaums.")
    
    json_files = get_json_files()
    if not json_files:
        st.warning("Keine JSON-Dateien im data Ordner gefunden.")
        return
    
    selected_file = st.selectbox(
        "🗂 Wähle einen Themenbaum",
        options=json_files,
        format_func=lambda x: x.name
    )
    
    # Optionen für die Q&A-Generierung
    col1, col2, col3 = st.columns(3)
    with col1:
        num_questions = st.number_input(
            "Anzahl Fragen pro Thema",
            min_value=3,
            max_value=30,
            value=10,
            step=1,
            help="Wie viele Fragen sollen pro Thema generiert werden?"
        )
    with col2:
        average_length = st.number_input(
            "📏 Durchschnittliche Antwortlänge (Zeichen)",
            min_value=100,
            max_value=2000,
            value=200,
            step=100
        )
    
    # Optionen für zusätzliche Informationen
    include_compendium = st.checkbox(
        "📚 Kompendium einbeziehen",
        value=True,
        help="Bezieht die generierten Kompendium-Texte in die Q&A-Generierung ein"
    )
    include_entities = st.checkbox(
        "🔍 Entitäten einbeziehen",
        value=False,
        help="Bezieht Informationen aus extrahierten Entitäten mit ein (nur relevant, wenn kein Kompendium verwendet wird)"
    )

    if st.button("🚀 Starte Q&A-Generierung", type="primary", use_container_width=True):
        if not selected_file:
            st.error("Bitte wähle eine Datei aus.")
            return
        if not openai_key:
            st.error("Kein OpenAI API-Key angegeben.")
            return
        
        # Lade JSON-Datei
        try:
            tree_data = load_json_file(selected_file)
        except Exception as e:
            st.error(f"Fehler beim Laden der JSON-Datei: {e}")
            return
        
        if "collection" not in tree_data:
            st.error("Fehler: Keine 'collection' im JSON.")
            return
            
        # OpenAI init
        try:
            client = OpenAI(api_key=openai_key)
        except Exception as e:
            st.error(f"OpenAI-Init-Fehler: {e}")
            return
            
        # Berechne Gesamtanzahl der Knoten
        st.info("Berechne Gesamtanzahl der Knoten...")
        total_nodes = 0
        for root_node in tree_data["collection"]:
            nodes_in_root = count_nodes(root_node)
            total_nodes += nodes_in_root
            
        st.write(f"**Gesamtanzahl Knoten:** {total_nodes}")
        
        # Erstelle Progress Bar und Status Text
        progress_bar = st.progress(0)
        progress_text = st.empty()
        
        # Verarbeite jeden Root Node
        current = 0
        for i, root_node in enumerate(tree_data["collection"]):
            start_percent = i / len(tree_data["collection"])
            end_percent = (i + 1) / len(tree_data["collection"])
            
            current = process_node_qa(
                client=client,
                node=root_node,
                metadata=tree_data.get("metadata", {}),
                progress_bar=progress_bar,
                progress_text=progress_text,
                current=current,
                total=total_nodes,
                start_percent=start_percent,
                end_percent=end_percent,
                num_questions=num_questions,
                include_compendium=include_compendium,
                include_entities=include_entities,
                model=model
            )
        
        # Speichere die Q&A-Daten
        try:
            filepath = save_json_with_timestamp(tree_data, prefix="themenbaum", suffix="_qa")
            st.success(f"Themenbaum mit Q&A-Paaren gespeichert unter: {filepath}")
            
            # Download Button für manuelle Speicherung
            final_qa = json.dumps(tree_data, indent=2, ensure_ascii=False)
            st.download_button(
                "💾 Themenbaum mit Q&A herunterladen",
                data=final_qa,
                file_name=f"themenbaum_qa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
            # Zeige Beispiele für generierte Fragen und Antworten
            st.subheader("Beispielfragen aus dem generierten Set:")
            
            if "collection" in tree_data and tree_data["collection"]:
                for root_node in tree_data["collection"]:
                    if "additional_data" in root_node and "qa_pairs" in root_node["additional_data"]:
                        qa_data = root_node["additional_data"]["qa_pairs"]
                        if "qa_pairs" in qa_data and qa_data["qa_pairs"]:
                            with st.expander(f"📘 {root_node['title']} ({len(qa_data['qa_pairs'])} Fragen)"):
                                for i, qa in enumerate(qa_data["qa_pairs"]):
                                    if i < 3:  # Zeige nur die ersten 3 als Beispiel
                                        st.markdown(f"**F: {qa['question']}**")
                                        st.markdown(f"A: {qa['answer']}")
                                        if i < 2:
                                            st.markdown("---")
                                    elif i == 3:
                                        st.markdown("*... und weitere Fragen*")
                                        break
            
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")
