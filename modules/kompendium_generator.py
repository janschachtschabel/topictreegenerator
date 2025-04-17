"""
Funktionen zur Generierung von kompendialen Texten und Entitätsextraktion.
"""
import json
import backoff
import streamlit as st
from datetime import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI, RateLimitError, APIError

from entityextractor.nernel import link_entities
from .utils import save_json_with_timestamp, count_nodes, load_json_file, get_json_files, get_entity_extractor_config

# Prompts für Textgenerierung
EXTENDED_TEXT_PROMPT = """\
**Befolgen Sie diese Anweisungen und erstellen Sie einen kompendialen Text über:**
{title}

## Kontextinformationen
Die folgenden Informationen sollten bei der Erstellung berücksichtigt werden:
- Thema: {title}
- Beschreibung: {description}
- Hierarchische Position im Themenbaum: {tree_context}
- Metadaten zum Themenbaum: {metadata}
- Erstellungsdatum: {current_date}

## Inhalt
- Erstellen Sie einen Übersichtstext, der das Thema umfassend darstellt
- Verwenden Sie akkurate, wissenschaftlich fundierte Informationen
- Passen Sie die Detailtiefe an das Thema an
- Berücksichtigen Sie die hierarchische Position im Themenbaum (z.B. ist es ein Hauptthema oder ein spezialisiertes Unterthema?)

## Dokumentstruktur
- **Verwenden Sie Markdown-Überschriften:**  
  - Eine einzelne #-Überschrift für den Titel  
  - Hauptabschnitte mit ##  
  - Unterabschnitte mit ###  
  - Möglichst sparsame Verwendung von #### für Spezialthemen  
- **Vermeiden Sie Überspringen von Überschriftenebenen**  
- **Fügen Sie vor den Hauptabschnitten** einen einleitenden Absatz mit den wichtigsten Erkenntnissen ein  
- Gliedern Sie Ihren kompendialen Text in mindestens fünf Hauptabschnitte  
- Schreiben Sie mehrere Absätze pro Abschnitt und Unterabschnitt (jeweils 4–5 Sätze oder mehr pro Absatz)  
- Verwenden Sie NIEMALS Listen im Textteil, sondern ausschließlich Fließtext oder Tabellen  

## Stilrichtlinien
- Verwenden Sie eine formelle, akademische Schreibweise  
- Setzen Sie **Fettdruck** nur für zentrale Fachbegriffe oder besonders wichtige Aussagen ein  
- Konvertieren Sie jegliche Listen-Informationen in ausformulierte Absätze  
- Fassen Sie vergleichende Daten in Tabellen zusammen  
- Zitieren Sie Quellen inline und nicht als URLs  
- Halten Sie einen durchgehenden narrativen Fluss bei  

## Besondere Formate
- **Code-Snippets:** Als Markdown-Codeblöcke mit passendem Sprachidentifikator einfügen  
- **Mathematische Ausdrücke:** IMMER in LaTeX-Befehlsform  
- **Zitate:** Als Blockzitate einfügen  
- **Hervorhebungen:** Fettdruck sparsam einsetzen, Kursivschrift für leichte Betonungen  

## Planungsregeln
- Achten Sie auf Vollständigkeit und Genauigkeit  
- Bedenken Sie das aktuelle Datum ({current_date})
- Denken Sie so lange über die Struktur nach, bis Sie bereit sind, mindestens **4 Seiten** zu verfassen  

## Ausgabe
- Erstellen Sie einen fachlich fundierten, gut lesbaren kompendialen Text  
- Kein Einsatz von Listen, sondern ausschließlich Fließtext oder Tabellen  
- Achten Sie auf mindestens **4 Seiten** Umfang  
- Fügen Sie Inline-Zitate ein, wo relevant, und einen Referenzen-Abschnitt nach APA-Standard am Schluss
"""

FINAL_COMPENDIUM_PROMPT = """\
**Befolgen Sie diese Anweisungen und erstellen Sie einen kompendialen Text über:**
{title}

## Kontextinformationen
Die folgenden Informationen sollten bei der Erstellung berücksichtigt werden:
- Bereits erstellter erweiterter Text: {extended_text}
- Extrahierte Entitäten mit Details: {entities_info}
- Erstellungsdatum: {current_date}

## Inhalt
- Überarbeiten und integrieren Sie den bereits erstellten erweiterten Text
- Reichern Sie ihn mit den Informationen aus den extrahierten Entitäten an
- Stellen Sie sicher, dass das Wissen aus beiden Quellen harmonisch kombiniert wird
- Fügen Sie neue Perspektiven oder Aspekte hinzu, die durch die Entitäten erschlossen wurden

## Dokumentstruktur
- **Verwenden Sie Markdown-Überschriften:**  
  - Eine einzelne #-Überschrift für den Titel  
  - Hauptabschnitte mit ##  
  - Unterabschnitte mit ###  
  - Möglichst sparsame Verwendung von #### für Spezialthemen  
- **Vermeiden Sie Überspringen von Überschriftenebenen**  
- **Fügen Sie vor den Hauptabschnitten** einen einleitenden Absatz mit den wichtigsten Erkenntnissen ein  
- Gliedern Sie Ihren kompendialen Text in mindestens fünf Hauptabschnitte  
- Schreiben Sie mehrere Absätze pro Abschnitt und Unterabschnitt (jeweils 4–5 Sätze oder mehr pro Absatz)  
- Verwenden Sie NIEMALS Listen im Textteil, sondern ausschließlich Fließtext oder Tabellen  

## Stilrichtlinien
- Verwenden Sie eine formelle, akademische Schreibweise  
- Setzen Sie **Fettdruck** nur für zentrale Fachbegriffe oder besonders wichtige Aussagen ein  
- Konvertieren Sie jegliche Listen-Informationen in ausformulierte Absätze  
- Fassen Sie vergleichende Daten in Tabellen zusammen  
- Zitieren Sie Quellen inline und nicht als URLs  
- Halten Sie einen durchgehenden narrativen Fluss bei  

## Besondere Formate
- **Code-Snippets:** Als Markdown-Codeblöcke mit passendem Sprachidentifikator einfügen  
- **Mathematische Ausdrücke:** IMMER in LaTeX-Befehlsform  
- **Zitate:** Als Blockzitate einfügen  
- **Hervorhebungen:** Fettdruck sparsam einsetzen, Kursivschrift für leichte Betonungen  

## Planungsregeln
- Achten Sie auf Vollständigkeit und Genauigkeit  
- Bedenken Sie das aktuelle Datum ({current_date})
- Bauen Sie insbesondere das verfügbare Wissen aus den extrahierten Entitäten ein
- Denken Sie so lange über die Struktur nach, bis Sie bereit sind, mindestens **4 Seiten** zu verfassen  

## Ausgabe
- Erstellen Sie einen fachlich fundierten, gut lesbaren kompendialen Text  
- Kein Einsatz von Listen, sondern ausschließlich Fließtext oder Tabellen  
- Achten Sie auf mindestens **4 Seiten** Umfang  
- Fügen Sie Inline-Zitate ein, wo relevant, und einen Referenzen-Abschnitt nach APA-Standard am Schluss
"""

def process_node(node: dict, client: OpenAI, config: dict, 
                progress_bar: st.progress, status_text: st.empty,
                nodes_processed: int, total_nodes: int,
                generate_extended_text: bool = True,
                extract_entities: bool = True,
                generate_final_compendium: bool = True,
                model: str = "gpt-4.1-mini",
                parent_path: str = "", node_path: List[str] = None) -> int:
    """
    Verarbeitet einen Knoten im Themenbaum für die Kompendiumsgenerierung.
    
    Args:
        node: Der zu verarbeitende Knoten
        client: OpenAI-Client
        config: Konfiguration für den Entitätsextraktor
        progress_bar: Streamlit Fortschrittsbalken
        status_text: Streamlit Status-Text-Element
        nodes_processed: Bisher verarbeitete Knoten
        total_nodes: Gesamtanzahl der Knoten
        generate_extended_text: Ob erweiterte Texte generiert werden sollen
        extract_entities: Ob Entitäten extrahiert werden sollen
        generate_final_compendium: Ob der finale kompendiale Text generiert werden soll
        model: Zu verwendendes LLM-Modell
        parent_path: Pfad zu diesem Knoten (für Anzeige)
        node_path: Liste der Knoten im aktuellen Pfad
        
    Returns:
        int: Anzahl der verarbeiteten Knoten
    """
    if not isinstance(node, dict) or "title" not in node:
        return nodes_processed
    
    # Pfad für Statusanzeige
    current_path = f"{parent_path}/{node['title']}" if parent_path else node['title']
    status_text.text(f"Verarbeite: {current_path}")
    
    # Pfad im Themenbaum für Kontextinformationen aufbauen
    if node_path is None:
        node_path = []
    current_node_path = node_path + [node['title']]
    
    # Hierarchie als String für den Prompt aufbauen
    tree_context = " > ".join(current_node_path)
    
    # Initialisiere additional_data wenn nicht vorhanden
    if "additional_data" not in node:
        node["additional_data"] = {}
    
    # 1. Schritt: Generiere erweiterten Text, wenn gewünscht
    if generate_extended_text:
        # Aktuelle Zeit für den Prompt
        current_date = datetime.now().strftime("%d.%m.%Y")
        description = node.get("properties", {}).get("cm:description", [""])[0]
        
        # Bereite Prompt für die Textgenerierung vor
        prompt = EXTENDED_TEXT_PROMPT.format(
            title=node.get("title", ""),
            description=description,
            tree_context=tree_context,
            metadata=json.dumps(node.get("metadata", {}), ensure_ascii=False),
            current_date=current_date
        )
        
        try:
            status_text.text(f"Generiere erweiterten Text für: {current_path}")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Du bist ein Experte für die Erstellung von umfassenden Texten zu Bildungsthemen."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            # Speichere den generierten erweiterten Text
            extended_text = response.choices[0].message.content
            node["additional_data"]["extended_text"] = extended_text
            
        except Exception as e:
            st.error(f"Fehler bei der Textgenerierung für '{current_path}': {str(e)}")
    
    # 2. Schritt: Extrahiere Entitäten wenn gewünscht und ein erweiterter Text vorhanden ist
    entities = []
    if extract_entities and node["additional_data"].get("extended_text"):
        try:
            status_text.text(f"Extrahiere Entitäten für: {current_path}")
            
            # Verwende den Entity Extractor aus dem entityextractor Modul
            entities = link_entities(node["additional_data"]["extended_text"], config=config)
            
            # Speichere die extrahierten Entitäten
            node["additional_data"]["entities"] = entities
            
        except Exception as e:
            st.error(f"Fehler bei der Entitätsextraktion für '{current_path}': {str(e)}")
    
    # 3. Schritt: Erstelle den finalen kompendialen Text, wenn gewünscht und Voraussetzungen erfüllt
    if generate_final_compendium and node["additional_data"].get("extended_text") and node["additional_data"].get("entities"):
        try:
            status_text.text(f"Erstelle kompendialen Text für: {current_path}")
            
            # Extrahiere relevante Informationen aus den Entitäten
            entities_info = []
            for entity in node["additional_data"]["entities"]:
                entity_info = f"Entität: {entity['entity']}\n"
                entity_info += f"Typ: {entity['details'].get('typ', 'Unbekannt')}\n"
                
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
                
                entities_info.append(entity_info)
            
            # Aktuelle Zeit für den Prompt
            current_date = datetime.now().strftime("%d.%m.%Y")
            
            # Erstelle den Prompt für den finalen kompendialen Text
            final_prompt = FINAL_COMPENDIUM_PROMPT.format(
                title=node.get("title", ""),
                extended_text=node["additional_data"]["extended_text"],
                entities_info="\n\n".join(entities_info),
                current_date=current_date
            )
            
            # Erstelle den finalen kompendialen Text
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Du bist ein Experte für die Integration von Fachwissen in bildungsrelevante Texte."},
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.7
            )
            
            # Speichere den finalen kompendialen Text
            compendium_text = response.choices[0].message.content
            node["additional_data"]["compendium_text"] = compendium_text
            
        except Exception as e:
            st.error(f"Fehler bei der Erstellung des kompendialen Texts für '{current_path}': {str(e)}")
    
    # Aktualisiere Fortschritt für aktuellen Node
    nodes_processed += 1
    progress_bar.progress(min(nodes_processed / total_nodes, 1.0))
    
    # Verarbeite rekursiv alle Unterknoten
    if "subcollections" in node and node["subcollections"]:
        for subnode in node["subcollections"]:
            nodes_processed = process_node(
                subnode, client, config, progress_bar, status_text, 
                nodes_processed, total_nodes, 
                generate_extended_text, extract_entities, generate_final_compendium,
                model, current_path, current_node_path
            )
    
    return nodes_processed

def show_compendium_page(openai_key: str, model: str):
    """
    Seite für die Kompendiengenerierung.
    
    Args:
        openai_key: OpenAI API-Key
        model: Zu verwendendes LLM-Modell
    """
    st.title("📚 Kompendiale Texte generieren")
    st.write("Füge zu jeder (Unter-)Kategorie eine erweiterte Beschreibung hinzu. Bilde auf Basis der Texte Entitäten und rufe Wissen ab.")

    json_files = get_json_files()
    if not json_files:
        st.warning("Keine JSON-Dateien im data Ordner gefunden.")
        return

    # Dateiauswahl und Optionen
    selected_file = st.selectbox("🗂 Wähle einen Themenbaum", options=json_files, format_func=lambda x: x.name)
    
    # Optionen für die Textgenerierung
    col1, col2, col3 = st.columns(3)
    with col1:
        generate_extended_text = st.checkbox(
            "📝 Erweiterte Texte generieren",
            value=True,
            help="Generiert erweiterte Texte für die Kategorien/Themen (ca. 4 A4-Seiten)."
        )
    with col2:
        extract_entities = st.checkbox(
            "🔍 Entitäten extrahieren",
            value=True,
            help="Extrahiert wichtige Entitäten und reichert sie mit Wikipedia-Informationen an."
        )
    with col3:
        generate_final_compendium = st.checkbox(
            "📚 Kompendium erstellen",
            value=True,
            help="Erstellt einen finalen kompendialen Text mit integriertem Entitywissen."
        )
    
    # Spracheinstellung für die Entitätsextraktion
    language = st.selectbox(
        "🌐 Sprache",
        options=["de", "en"],
        index=1,
        help="Sprache für die Entitätsextraktion und Wissenquellen"
    )
    
    # Erweiterte Einstellungen
    with st.expander("⚙️ Erweiterte Einstellungen"):
        col1, col2 = st.columns(2)
        with col1:
            use_wikidata = st.checkbox("Wikidata verwenden", value=False)
            use_dbpedia = st.checkbox("DBpedia verwenden", value=False)
        with col2:
            show_status = st.checkbox("Status-Meldungen anzeigen", value=True)
            dbpedia_use_de = st.checkbox("Deutsche DBpedia verwenden", value=False, disabled=not use_dbpedia)

    if st.button("🚀 Starte Kompendium-Erstellung", type="primary", use_container_width=True):
        if not selected_file:
            st.error("Bitte eine Datei auswählen.")
            return
        if not openai_key:
            st.error("Kein OpenAI API-Key angegeben.")
            return

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

        # Konfiguriere den Entity Extractor
        config = get_entity_extractor_config(
            openai_key=openai_key,
            model=model,
            language=language,
            use_wikidata=use_wikidata,
            use_dbpedia=use_dbpedia,
            dbpedia_use_de=dbpedia_use_de,
            show_status=show_status
        )

        # Zähle Knoten für den Fortschrittsbalken
        st.info("Berechne Gesamtanzahl der Knoten...")
        total_nodes = 0
        if "collection" in tree_data and isinstance(tree_data["collection"], list):
            st.write("Analysiere Themenbaum:")
            for root_node in tree_data["collection"]:
                nodes_in_root = count_nodes(root_node)
                total_nodes += nodes_in_root
                st.write(f"- {root_node.get('title', 'Unbekannt')}: {nodes_in_root} Knoten")
        
        st.write(f"**Gesamtanzahl Knoten:** {total_nodes}")
        
        # Erstelle Progress Bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Nodes verarbeiten
        nodes_processed = 0
        
        # Verarbeite alle Root-Knoten
        for root_node in tree_data["collection"]:
            nodes_processed = process_node(
                node=root_node,
                client=client,
                config=config,
                progress_bar=progress_bar,
                status_text=status_text,
                nodes_processed=nodes_processed,
                total_nodes=total_nodes,
                generate_extended_text=generate_extended_text,
                extract_entities=extract_entities,
                generate_final_compendium=generate_final_compendium,
                model=model
            )
        
        # Speichere erweiterte JSON in data Ordner
        try:
            filepath = save_json_with_timestamp(tree_data, prefix="themenbaum", suffix="_kompendium")
            st.success(f"Erweiterte Version gespeichert unter: {filepath}")
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")

        st.success("Kompendiale Texte und Entitäten hinzugefügt!")
        
        # Download Button für manuelle Speicherung
        final_comp = json.dumps(tree_data, indent=2, ensure_ascii=False)
        st.download_button(
            "💾 JSON mit Kompendium herunterladen",
            data=final_comp,
            file_name=f"themenbaum_kompendium_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
