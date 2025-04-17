"""
Themenbaum Generator

Eine Streamlit-Anwendung zur Generierung strukturierter Themenbäume,
kompendialer Texte mit Entitätsextraktion und Frage-Antwort-Paaren.
"""
import os
import streamlit as st
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Importiere die Module der Anwendung
from modules.models import TopicTree, Collection, Properties, QACollection, QAPair
from modules.utils import get_openai_key, get_json_files, save_json_with_timestamp, load_json_file
from modules.themenbaum_generator import show_tree_generation_page
from modules.kompendium_generator import show_compendium_page
from modules.qa_generator import show_qa_page

# Lade Umgebungsvariablen und konfiguriere Streamlit
load_dotenv()

# Ensure data directory exists
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="Themenbaum Generator", layout="wide")

def main():
    """
    Hauptfunktion der Anwendung.
    Verwaltet das Menü, Einstellungen und die verschiedenen Seiten.
    """
    # Speichere die aktuelle Seite im Session State
    if "page_mode" not in st.session_state:
        st.session_state.page_mode = "main"
    
    # Definiere das Seitenmenü
    menu_options = {
        "main": "🏠 Hauptmenü",
        "tree": "🌳 Themenbaum erstellen",
        "compendium": "📚 Kompendium generieren",
        "qa": "❓ Q&A generieren",
        "preview": "🔍 Dateivorschau"
    }
    
    # Seitenleiste mit Einstellungen und Navigation
    with st.sidebar:
        st.header("⚙️ Einstellungen")

        # LLM Settings at top
        with st.expander("🤖 LLM Einstellungen", expanded=False):
            model = st.selectbox(
                "🔧 Sprachmodell",
                options=["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"],
                index=3,
                help="Auswahl des AI-Modells. gpt-4.1-mini bietet ein gutes Verhältnis aus Geschwindigkeit und Qualität."
            )
            default_key = get_openai_key()
            openai_key = st.text_input("🔑 OpenAI API Key", value=default_key, type="password")

        # Navigation buttons
        st.markdown("---")
        if st.button("🎯 Themenbaum erstellen", use_container_width=True):
            st.session_state.page_mode = "tree"
        if st.button("📚 Kompendium generieren", use_container_width=True):
            st.session_state.page_mode = "compendium"
        if st.button("❓ Q&A generieren", use_container_width=True):
            st.session_state.page_mode = "qa"
        if st.button("🔍 Dateivorschau", use_container_width=True):
            st.session_state.page_mode = "preview"
    
    # Hauptbereich des Streamlit Interface
    if st.session_state.page_mode == "main":
        show_main_page()
    elif st.session_state.page_mode == "tree":
        show_tree_generation_page(openai_key, model)
    elif st.session_state.page_mode == "compendium":
        show_compendium_page(openai_key, model)
    elif st.session_state.page_mode == "qa":
        show_qa_page(openai_key, model)
    elif st.session_state.page_mode == "preview":
        show_preview_page()

def show_main_page():
    """
    Zeigt die Hauptseite mit einer Einführung und Übersicht über die Funktionen.
    """
    st.title("🎓 Themenbaum Generator")
    st.write("Willkommen beim Themenbaum Generator! Mit dieser Anwendung können Sie strukturierte Themenbäume erstellen und mit zusätzlichen Informationen anreichern.")
    
    # Übersicht über die Funktionen
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🌳 Themenbaum erstellen")
        st.markdown("""
        - Generieren Sie hierarchische Themenbäume
        - Definieren Sie Fachbereiche und Bildungsstufen
        - Exportieren Sie Ergebnisse als JSON
        """)
        if st.button("🎯 Jetzt starten", key="start_tree"):
            st.session_state.page_mode = "tree"
            st.rerun()
    
    with col2:
        st.markdown("### 📚 Kompendium generieren")
        st.markdown("""
        - Erstellen Sie ausführliche Texte für jeden Knoten
        - Extrahieren Sie relevante Entitäten und Wissen
        - Kombinieren Sie Informationen zu kompendialen Texten
        """)
        if st.button("📚 Jetzt starten", key="start_comp"):
            st.session_state.page_mode = "compendium"
            st.rerun()
    
    with col3:
        st.markdown("### ❓ Q&A generieren")
        st.markdown("""
        - Erstellen Sie Frage-Antwort-Paare zu jedem Thema
        - Nutzen Sie kompendiale Texte als Informationsquelle
        - Exportieren Sie Fragesets für Lernkontexte
        """)
        if st.button("❓ Jetzt starten", key="start_qa"):
            st.session_state.page_mode = "qa"
            st.rerun()
    
    # Anzeige der generierten Dateien
    st.markdown("---")
    st.markdown("### 📂 Generierte Dateien")
    json_files = get_json_files()
    
    if json_files:
        table_data = []
        for file in json_files[:5]:  # Zeige nur die letzten 5 Dateien
            file_stat = file.stat()
            size_kb = file_stat.st_size / 1024
            mod_time = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            table_data.append({
                "Dateiname": file.name,
                "Größe (KB)": f"{size_kb:.2f}",
                "Geändert": mod_time,
                "Pfad": str(file)
            })
        
        st.table(table_data)
        
        if len(json_files) > 5:
            st.info(f"Es werden nur die 5 neuesten Dateien angezeigt. Insgesamt sind {len(json_files)} Dateien vorhanden.")
        
        if st.button("🔍 Alle Dateien anzeigen", key="show_all"):
            st.session_state.page_mode = "preview"
            st.rerun()
    else:
        st.info("Keine generierten Dateien gefunden. Erstellen Sie einen Themenbaum, um loszulegen!")

def show_preview_page():
    """
    Zeigt eine Vorschau der generierten JSON-Dateien.
    """
    st.title("🔍 Dateivorschau")
    st.write("Vorschau und Download der generierten JSON-Dateien.")
    
    json_files = get_json_files()
    if not json_files:
        st.warning("Keine JSON-Dateien im data Ordner gefunden.")
        return
    
    selected_file = st.selectbox(
        "🗂 Wähle eine Datei",
        options=json_files,
        format_func=lambda x: x.name
    )
    
    if selected_file:
        try:
            file_content = load_json_file(selected_file)
            
            # Zeige Metadaten und Downloadbutton
            if "metadata" in file_content:
                metadata = file_content["metadata"]
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Metadaten")
                    st.markdown(f"**Titel:** {metadata.get('title', 'N/A')}")
                    st.markdown(f"**Beschreibung:** {metadata.get('description', 'N/A')}")
                    st.markdown(f"**Erstellt:** {metadata.get('created_at', 'N/A')}")
                    
                with col2:
                    file_stat = selected_file.stat()
                    size_kb = file_stat.st_size / 1024
                    mod_time = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    
                    st.subheader("Dateiinformationen")
                    st.markdown(f"**Dateiname:** {selected_file.name}")
                    st.markdown(f"**Größe:** {size_kb:.2f} KB")
                    st.markdown(f"**Letzte Änderung:** {mod_time}")
                    
                    # Download-Button
                    with open(selected_file, "r", encoding="utf-8") as f:
                        file_content_str = f.read()
                        
                    st.download_button(
                        "💾 Datei herunterladen",
                        data=file_content_str,
                        file_name=selected_file.name,
                        mime="application/json"
                    )
            
            # Ansichtsmodi für die Datei
            view_mode = st.radio(
                "Ansichtsmodus",
                options=["Strukturierte Ansicht", "JSON-Rohdaten", "Entitäten-Details"],
                horizontal=True
            )
            
            if view_mode == "JSON-Rohdaten":
                # Zeige die gesamten JSON-Daten
                st.subheader("JSON-Daten")
                st.json(file_content)
                
            elif view_mode == "Entitäten-Details":
                # Zeige detaillierte Ansicht von Entitäten
                st.subheader("Entitäten-Details")
                
                # Wähle einen Knoten aus, falls Entitäten vorhanden sind
                nodes_with_entities = []
                
                if "collection" in file_content:
                    # Baue eine flache Liste aller Knoten mit Entitäten auf
                    def collect_nodes_with_entities(node, path=""):
                        current_path = f"{path} > {node['title']}" if path else node['title']
                        has_entities = "additional_data" in node and "entities" in node["additional_data"]
                        
                        if has_entities:
                            nodes_with_entities.append({
                                "path": current_path,
                                "node": node
                            })
                        
                        if "subcollections" in node:
                            for subcoll in node["subcollections"]:
                                collect_nodes_with_entities(subcoll, current_path)
                    
                    # Sammle Knoten mit Entitäten
                    for collection in file_content["collection"]:
                        collect_nodes_with_entities(collection)
                
                if nodes_with_entities:
                    selected_node_idx = st.selectbox(
                        "Wähle einen Knoten mit Entitäten",
                        options=range(len(nodes_with_entities)),
                        format_func=lambda i: nodes_with_entities[i]["path"]
                    )
                    
                    selected_node = nodes_with_entities[selected_node_idx]["node"]
                    entities = selected_node["additional_data"]["entities"]
                    
                    st.write(f"**{len(entities)} Entitäten gefunden für '{nodes_with_entities[selected_node_idx]['path']}'**")
                    
                    # Entity-Typ-Filter
                    entity_types = list(set([entity.get("details", {}).get("typ", "Unbekannt") for entity in entities]))
                    selected_type = st.selectbox("Nach Typ filtern", ["Alle"] + entity_types)
                    
                    # Entitäten anzeigen - ohne verschachtelte Expander
                    filtered_entities = entities if selected_type == "Alle" else [
                        e for e in entities if e.get("details", {}).get("typ", "Unbekannt") == selected_type
                    ]
                    
                    for i, entity in enumerate(filtered_entities):
                        entity_name = entity.get('entity', 'Unbekannt')
                        entity_type = entity.get('details', {}).get('typ', 'Unbekannt')
                        
                        with st.expander(f"{i+1}. {entity_name} ({entity_type})", expanded=i==0):
                            # Tabs für verschiedene Ansichten
                            tab1, tab2 = st.tabs(["Strukturierte Ansicht", "JSON-Daten"])
                            
                            with tab1:
                                # Wikipedia
                                if "sources" in entity and "wikipedia" in entity["sources"]:
                                    wiki = entity["sources"]["wikipedia"]
                                    st.markdown(f"**Wikipedia:** [{wiki.get('title', 'Link')}]({wiki.get('url', '#')})")
                                    if "extract" in wiki:
                                        st.markdown("**Wikipedia-Auszug:**")
                                        st.markdown(wiki["extract"])
                                
                                # Wikidata
                                if "sources" in entity and "wikidata" in entity["sources"]:
                                    wikidata = entity["sources"]["wikidata"]
                                    st.markdown(f"**Wikidata:** ID: {wikidata.get('id', 'N/A')}")
                                    if "description" in wikidata:
                                        st.markdown("**Wikidata-Beschreibung:**")
                                        st.markdown(wikidata["description"])
                                
                                # DBpedia
                                if "sources" in entity and "dbpedia" in entity["sources"]:
                                    dbpedia = entity["sources"]["dbpedia"]
                                    st.markdown(f"**DBpedia:** [{dbpedia.get('label', 'Link')}]({dbpedia.get('uri', '#')})")
                                    if "abstract" in dbpedia:
                                        st.markdown("**DBpedia-Auszug:**")
                                        st.markdown(dbpedia["abstract"])
                            
                            with tab2:
                                # JSON-Ansicht der Entität
                                st.json(entity)
                else:
                    st.info("Keine Entitäten in dieser Datei gefunden.")
            else:
                # Strukturierte Ansicht des Themenbaums
                st.markdown("---")
                st.subheader("Struktur des Themenbaums")
                
                if "collection" in file_content:
                    for i, collection in enumerate(file_content["collection"]):
                        st.markdown(f"### {i+1}. {collection.get('title', 'Unbekannt')}")
                        st.markdown(collection.get("properties", {}).get("cm:description", [""])[0])
                        
                        # Zeige ob kompendiale Texte, Entitäten oder QA vorhanden sind
                        additional = get_additional_data_info(collection)
                        if additional:
                            st.markdown("**Enthält:**")
                            st.markdown(" | ".join(additional))
                        
                        # Zeige Unterkollektionen in einem nicht-verschachtelten Format
                        if "subcollections" in collection and collection["subcollections"]:
                            st.markdown("**Untersammlungen:**")
                            for j, sub in enumerate(collection["subcollections"]):
                                st.markdown(f"**{i+1}.{j+1} {sub.get('title', 'Unbekannt')}**")
                                st.markdown(sub.get("properties", {}).get("cm:description", [""])[0])
                                
                                # Zeige Zusatzdaten für Unterkategorien
                                sub_additional = get_additional_data_info(sub)
                                if sub_additional:
                                    st.markdown("**Enthält:**")
                                    st.markdown(" | ".join(sub_additional))
                                
                                # Zeige Untersammlungen Level 3 - ohne Expander
                                if "subcollections" in sub and sub["subcollections"]:
                                    st.markdown("*Weitere Untersammlungen:*")
                                    for k, subsub in enumerate(sub["subcollections"]):
                                        st.markdown(f"**{i+1}.{j+1}.{k+1} {subsub.get('title', 'Unbekannt')}**")
                                        st.markdown(f"*{subsub.get('properties', {}).get('cm:description', [''])[0]}*")
                                        
                                        # Zeige Zusatzdaten für weitere Unterkategorien
                                        subsub_additional = get_additional_data_info(subsub)
                                        if subsub_additional:
                                            st.markdown("**Enthält:**")
                                            st.markdown(" | ".join(subsub_additional))
                        
                        st.markdown("---")
                
        except Exception as e:
            st.error(f"Fehler beim Laden der Datei: {str(e)}")
            import traceback
            st.error(traceback.format_exc())

def get_additional_data_info(node):
    """Hilfsfunktion, um Informationen über zusätzliche Daten eines Knotens zu erhalten."""
    additional = []
    if "additional_data" in node:
        if "extended_text" in node["additional_data"]:
            additional.append("✅ Erweiterter Text")
        if "entities" in node["additional_data"]:
            additional.append(f"✅ Entitäten ({len(node['additional_data']['entities'])})")
        if "compendium_text" in node["additional_data"]:
            additional.append("✅ Kompendialer Text")
        if "qa_pairs" in node["additional_data"]:
            qa_count = len(node["additional_data"]["qa_pairs"].get("qa_pairs", []))
            additional.append(f"✅ Q&A Paare ({qa_count})")
    return additional

if __name__ == "__main__":
    main()
