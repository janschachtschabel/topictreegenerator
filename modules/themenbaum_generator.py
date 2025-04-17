"""
Funktionen zur Generierung eines Themenbaums.
"""
import json
import backoff
import streamlit as st
import urllib.parse
from datetime import datetime
from openai import OpenAI, RateLimitError, APIError
from typing import Dict, List, Optional, Any, Callable

from .models import TopicTree, Collection, Properties
from .utils import save_json_with_timestamp

# Konstanten und Konfiguration
DISCIPLINE_MAPPING = {
    "Keine Vorgabe": "",
    "Allgemein": "http://w3id.org/openeduhub/vocabs/discipline/720",
    "Altenpflege": "http://w3id.org/openeduhub/vocabs/discipline/04002",
    "Astronomie": "http://w3id.org/openeduhub/vocabs/discipline/36003",
    "Bautechnik": "http://w3id.org/openeduhub/vocabs/discipline/04004",
    "Berufliche Bildung": "http://w3id.org/openeduhub/vocabs/discipline/00001",
    "Biologie": "http://w3id.org/openeduhub/vocabs/discipline/080",
    "Chemie": "http://w3id.org/openeduhub/vocabs/discipline/100",
    "Chinesisch": "http://w3id.org/openeduhub/vocabs/discipline/1900",
    "Darstellendes Spiel": "http://w3id.org/openeduhub/vocabs/discipline/120",
    "Deutsch": "http://w3id.org/openeduhub/vocabs/discipline/120",
    "Deutsch als Zweitsprache": "http://w3id.org/openeduhub/vocabs/discipline/140",
    "Elektrotechnik": "http://w3id.org/openeduhub/vocabs/discipline/04005",
    "Englisch": "http://w3id.org/openeduhub/vocabs/discipline/20001",
    "Ethik": "http://w3id.org/openeduhub/vocabs/discipline/160",
    "Fächerübergreifende Bildungsthemen (Sekundarstufe I)": "http://w3id.org/openeduhub/vocabs/discipline/28009",
    "Fächerübergreifende Themen": "http://w3id.org/openeduhub/vocabs/discipline/180",
    "Französisch": "http://w3id.org/openeduhub/vocabs/discipline/20002",
    "Geographie": "http://w3id.org/openeduhub/vocabs/discipline/220",
    "Geschichte": "http://w3id.org/openeduhub/vocabs/discipline/240",
    "Gesundheit und Soziales": "http://w3id.org/openeduhub/vocabs/discipline/04006",
    "Grundschule": "http://w3id.org/openeduhub/vocabs/discipline/00002",
    "Hauswirtschaft": "http://w3id.org/openeduhub/vocabs/discipline/04007",
    "Holztechnik": "http://w3id.org/openeduhub/vocabs/discipline/04008",
    "Informatik": "http://w3id.org/openeduhub/vocabs/discipline/320",
    "Interkulturelle Bildung": "http://w3id.org/openeduhub/vocabs/discipline/340",
    "Italienisch": "http://w3id.org/openeduhub/vocabs/discipline/20004",
    "Kunst": "http://w3id.org/openeduhub/vocabs/discipline/060",
    "Körperpflege": "http://w3id.org/openeduhub/vocabs/discipline/04010",
    "Latein": "http://w3id.org/openeduhub/vocabs/discipline/20005",
    "Mathematik": "http://w3id.org/openeduhub/vocabs/discipline/380",
    "Mechatronik": "http://w3id.org/openeduhub/vocabs/discipline/oeh04010",
    "Medienbildung": "http://w3id.org/openeduhub/vocabs/discipline/900",
    "Mediendidaktik": "http://w3id.org/openeduhub/vocabs/discipline/400",
    "Metalltechnik": "http://w3id.org/openeduhub/vocabs/discipline/04011",
    "MINT": "http://w3id.org/openeduhub/vocabs/discipline/04003",
    "Musik": "http://w3id.org/openeduhub/vocabs/discipline/420",
    "Nachhaltigkeit": "http://w3id.org/openeduhub/vocabs/discipline/64018",
    "Niederdeutsch": "http://w3id.org/openeduhub/vocabs/discipline/niederdeutsch",
    "Open Educational Resources": "http://w3id.org/openeduhub/vocabs/discipline/44099",
    "Philosophie": "http://w3id.org/openeduhub/vocabs/discipline/450",
    "Physik": "http://w3id.org/openeduhub/vocabs/discipline/460",
    "Politik": "http://w3id.org/openeduhub/vocabs/discipline/480",
    "Psychologie": "http://w3id.org/openeduhub/vocabs/discipline/510",
    "Religion": "http://w3id.org/openeduhub/vocabs/discipline/520",
    "Russisch": "http://w3id.org/openeduhub/vocabs/discipline/20006",
    "Sachunterricht": "http://w3id.org/openeduhub/vocabs/discipline/28010",
    "Sexualerziehung": "http://w3id.org/openeduhub/vocabs/discipline/560",
    "Sonderpädagogik": "http://w3id.org/openeduhub/vocabs/discipline/44006",
    "Sorbisch": "http://w3id.org/openeduhub/vocabs/discipline/20009",
    "Sozialpädagogik": "http://w3id.org/openeduhub/vocabs/discipline/44007",
    "Spanisch": "http://w3id.org/openeduhub/vocabs/discipline/20007",
    "Sport": "http://w3id.org/openeduhub/vocabs/discipline/600",
    "Textiltechnik und Bekleidung": "http://w3id.org/openeduhub/vocabs/discipline/04012",
    "Türkisch": "http://w3id.org/openeduhub/vocabs/discipline/20008",
    "Wirtschaft und Verwaltung": "http://w3id.org/openeduhub/vocabs/discipline/04013",
    "Wirtschaftskunde": "http://w3id.org/openeduhub/vocabs/discipline/700",
    "Umweltgefährdung, Umweltschutz": "http://w3id.org/openeduhub/vocabs/discipline/640",
    "Verkehrserziehung": "http://w3id.org/openeduhub/vocabs/discipline/660",
    "Weiterbildung": "http://w3id.org/openeduhub/vocabs/discipline/680",
    "Werken": "http://w3id.org/openeduhub/vocabs/discipline/50005",
    "Zeitgemäße Bildung": "http://w3id.org/openeduhub/vocabs/discipline/72001",
    "Sonstiges": "http://w3id.org/openeduhub/vocabs/discipline/999"
}

EDUCATIONAL_CONTEXT_MAPPING = {
    "Keine Vorgabe": "",
    "Elementarbereich": "http://w3id.org/openeduhub/vocabs/educationalContext/elementarbereich",
    "Primarstufe": "http://w3id.org/openeduhub/vocabs/educationalContext/grundschule",
    "Sekundarstufe I": "http://w3id.org/openeduhub/vocabs/educationalContext/sekundarstufe_1",
    "Sekundarstufe II": "http://w3id.org/openeduhub/vocabs/educationalContext/sekundarstufe_2",
    "Hochschule": "http://w3id.org/openeduhub/vocabs/educationalContext/hochschule",
    "Berufliche Bildung": "http://w3id.org/openeduhub/vocabs/educationalContext/berufliche_bildung",
    "Fortbildung": "http://w3id.org/openeduhub/vocabs/educationalContext/fortbildung",
    "Erwachsenenbildung": "http://w3id.org/openeduhub/vocabs/educationalContext/erwachsenenbildung",
    "Förderschule": "http://w3id.org/openeduhub/vocabs/educationalContext/foerderschule",
    "Fernunterricht": "http://w3id.org/openeduhub/vocabs/educationalContext/fernunterricht"
}

EDUCATION_SECTOR_MAPPING = {
    "Keine Vorgabe": "",
    "Frühkindlich": "Frühkindlich",
    "Allgemeinbildend": "Allgemeinbildend",
    "Berufsbildend": "Berufsbildend",
    "Akademisch": "Akademisch"
}

def create_properties(title: str, shorttitle: str, description: str = "", 
                     discipline_uri: str = "", educational_context_uri: str = "",
                     keywords: List[str] = None) -> Properties:
    """
    Erstellt Properties für eine Collection.
    
    Args:
        title: Titel der Collection
        shorttitle: Kurztitel der Collection
        description: Beschreibung der Collection
        discipline_uri: URI des Fachbereichs
        educational_context_uri: URI des Bildungskontexts
        keywords: Liste von Schlüsselwörtern
        
    Returns:
        Properties: Properties-Objekt
    """
    if keywords is None:
        keywords = []
    
    # Stelle sicher, dass nur Listen übergeben werden
    desc_list = [description] if description else [""]
    title_list = [title] if title else [""]
    
    props = Properties(
        cm_title=title_list,
        ccm_collectionshorttitle=[shorttitle],
        cm_description=desc_list,
        cclom_general_keyword=keywords
    )
    
    # Füge optionale Felder hinzu, wenn sie angegeben sind
    if discipline_uri:
        props.ccm_taxonid = [discipline_uri]
        
    if educational_context_uri:
        props.ccm_educationalcontext = [educational_context_uri]
    
    return props

def update_collection_properties(coll: Collection, discipline_uri: str, educational_context_uri: str):
    """
    Aktualisiert die Properties aller Collections in einem Baum.
    
    Args:
        coll: Die zu aktualisierende Collection
        discipline_uri: URI des Fachbereichs
        educational_context_uri: URI des Bildungskontexts
    """
    if discipline_uri:
        coll.properties.ccm_taxonid = [discipline_uri]
    if educational_context_uri:
        coll.properties.ccm_educationalcontext = [educational_context_uri]
    
    for subc in coll.subcollections:
        update_collection_properties(subc, discipline_uri, educational_context_uri)

@backoff.on_exception(backoff.expo, (RateLimitError, APIError), max_tries=5)
def generate_topic_tree(client: OpenAI, topic: str, num_main: int, num_sub: int, num_lehrplan: int,
                       include_general: bool, include_methodik: bool, discipline_uri: str,
                       educational_context_uri: str, education_sector: str, model: str) -> Optional[Dict]:
    """
    Generiert einen Themenbaum mit OpenAI.
    
    Args:
        client: OpenAI-Client
        topic: Thema des Themenbaums
        num_main: Anzahl der Hauptthemen
        num_sub: Anzahl der Unterthemen pro Hauptthema
        num_lehrplan: Anzahl der Lehrplanthemen pro Unterthema
        include_general: Ob ein Hauptthema "Allgemeines" hinzugefügt werden soll
        include_methodik: Ob ein Hauptthema "Methodik und Didaktik" hinzugefügt werden soll
        discipline_uri: URI des Fachbereichs
        educational_context_uri: URI des Bildungskontexts
        education_sector: Bildungssektor
        model: LLM-Modell für die Generierung
        
    Returns:
        Optional[Dict]: Generierter Themenbaum als Dictionary oder None bei Fehler
    """
    # Prompt vorbereiten
    prompt = f"""
    Erstelle einen mehrstufigen Themenbaum für: {topic}
    
    Der Themenbaum soll folgende Struktur haben:
    - {num_main} Hauptthemen
    - Pro Hauptthema {num_sub} Fachthemen
    - Pro Fachthema {num_lehrplan} Lehrplanthemen
    
    {"- Füge ein Hauptthema 'Allgemeines' an erster Stelle hinzu" if include_general else ""}
    {"- Füge ein Hauptthema 'Methodik und Didaktik' an letzter Stelle hinzu" if include_methodik else ""}
    
    Fachbereich: {next((k for k, v in DISCIPLINE_MAPPING.items() if v == discipline_uri), "")}
    Bildungsstufe: {next((k for k, v in EDUCATIONAL_CONTEXT_MAPPING.items() if v == educational_context_uri), "")}
    Bildungssektor: {education_sector}
    
    Bitte gib für jedes Thema auch eine kurze Beschreibung an.
    
    Format:
    <Hauptthema>: <Kurzbeschreibung>
    - <Fachthema>: <Kurzbeschreibung>
      - <Lehrplanthema>: <Kurzbeschreibung>
    """
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Du bist ein Experte für die Erstellung von strukturierten Themenbäumen für Bildungseinrichtungen."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        # Parse response into collections
        collections = []
        content = response.choices[0].message.content
        
        # Split into lines and parse
        lines = content.split('\n')
        current_main = None
        current_sub = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('- ') and current_main is not None:
                # This is a subtopic
                parts = line[2:].split(':', 1)
                if len(parts) == 2:
                    sub_title = parts[0].strip()
                    sub_desc = parts[1].strip()
                    
                    sub_properties = create_properties(
                        title=sub_title,
                        shorttitle=sub_title[:20] + "..." if len(sub_title) > 20 else sub_title,
                        description=sub_desc,
                        discipline_uri=discipline_uri,
                        educational_context_uri=educational_context_uri
                    )
                    
                    current_sub = Collection(
                        title=sub_title,
                        shorttitle=sub_title[:20] + "..." if len(sub_title) > 20 else sub_title,
                        properties=sub_properties,
                        subcollections=[]
                    )
                    
                    current_main.subcollections.append(current_sub)
            
            elif line.startswith('  - ') and current_sub is not None:
                # This is a lehrplan topic
                parts = line[4:].split(':', 1)
                if len(parts) == 2:
                    lp_title = parts[0].strip()
                    lp_desc = parts[1].strip()
                    
                    lp_properties = create_properties(
                        title=lp_title,
                        shorttitle=lp_title[:20] + "..." if len(lp_title) > 20 else lp_title,
                        description=lp_desc,
                        discipline_uri=discipline_uri,
                        educational_context_uri=educational_context_uri
                    )
                    
                    lp_collection = Collection(
                        title=lp_title,
                        shorttitle=lp_title[:20] + "..." if len(lp_title) > 20 else lp_title,
                        properties=lp_properties
                    )
                    
                    current_sub.subcollections.append(lp_collection)
            
            else:
                # This is a main topic
                parts = line.split(':', 1)
                if len(parts) == 2:
                    main_title = parts[0].strip()
                    main_desc = parts[1].strip()
                    
                    main_properties = create_properties(
                        title=main_title,
                        shorttitle=main_title[:20] + "..." if len(main_title) > 20 else main_title,
                        description=main_desc,
                        discipline_uri=discipline_uri,
                        educational_context_uri=educational_context_uri
                    )
                    
                    current_main = Collection(
                        title=main_title,
                        shorttitle=main_title[:20] + "..." if len(main_title) > 20 else main_title,
                        properties=main_properties,
                        subcollections=[]
                    )
                    
                    collections.append(current_main)
        
        # Create the topic tree
        topic_tree = TopicTree(
            collection=collections,
            metadata={
                "title": topic,
                "description": f"Themenbaum für {topic}",
                "target_audience": "Lehrkräfte",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "author": "Themenbaum Generator",
                "discipline": discipline_uri,
                "educational_context": educational_context_uri,
                "education_sector": education_sector
            }
        )
        
        return topic_tree.to_dict()
        
    except Exception as e:
        st.error(f"Fehler bei der Themenbaum-Generierung: {str(e)}")
        return None

# Basisanweisung für die LLM-Generierung
base_instructions = """Du hilfst mir, einen strukturierten Themenbaum zu erstellen. 
Deine Ausgabe muss als gültiges JSON formatiert sein.
Gib eine Liste von Objekten im folgenden Format zurück:

[
  {
    "title": "Titel des Themas",
    "shorttitle": "Kurztitel (optional)",
    "description": "Ausführliche Beschreibung (1-2 Sätze)"
  }
]
"""

@backoff.on_exception(
    backoff.expo,
    (RateLimitError, APIError),
    max_tries=5,
    jitter=backoff.full_jitter
)
def generate_structured_text(client: OpenAI, prompt: str, model: str) -> Optional[List[Collection]]:
    """Befragt das Modell, parsed reines JSON-Array => Liste[Collection]."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": base_instructions},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        content = resp.choices[0].message.content
        if not content.strip():
            print("Antwort vom Modell ist leer.")
            return []

        # Bereinige die Antwort (entferne Markdown-Code-Blöcke etc.)
        raw = content.strip().strip("```").strip("```json").strip()
        print(f"Bereinigter Text: {raw[:100]}...")
        
        # Finde JSON-Bereich, falls vorhanden
        json_start = raw.find('[')
        json_end = raw.rfind(']') + 1
        
        if json_start >= 0 and json_end > json_start:
            raw = raw[json_start:json_end]
        
        data = json.loads(raw)
        if not isinstance(data, list):
            data = [data]

        results = []
        for item in data:
            title = item.get("title", "")
            shorttitle = item.get("shorttitle", title[:20] + "..." if len(title) > 20 else title)
            
            # Beschreibungsfeld könnte unterschiedlich benannt sein
            desc = ""
            for field in ["description", "desc", "content", "text"]:
                if field in item:
                    desc = item[field]
                    break
            
            keywords = item.get("keywords", [])

            prop = create_properties(
                title=title,
                shorttitle=shorttitle,
                description=desc,
                keywords=keywords
            )
            
            c = Collection(
                title=title,
                shorttitle=shorttitle,
                properties=prop,
                subcollections=[]
            )
            results.append(c)

        return results
    except json.JSONDecodeError as jde:
        print(f"JSON Decode Error: {jde}")
        print(f"Rohdaten:\n{content[:200]}...")
        return []
    except Exception as e:
        print(f"Fehler bei der Anfrage: {e}")
        import traceback
        traceback.print_exc()
        return []

def generate_topic_tree_iterative(
    client: OpenAI, 
    topic: str, 
    num_main: int, 
    num_sub: int, 
    num_lehrplan: int,
    include_general: bool, 
    include_methodik: bool, 
    discipline_uri: str,
    educational_context_uri: str, 
    education_sector: str, 
    model: str,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Optional[Dict]:
    """
    Generiert einen Themenbaum iterativ mit OpenAI (Schritt für Schritt).
    
    Args:
        client: OpenAI-Client
        topic: Thema des Themenbaums
        num_main: Anzahl der Hauptthemen
        num_sub: Anzahl der Unterthemen pro Hauptthema
        num_lehrplan: Anzahl der Lehrplanthemen pro Unterthema
        include_general: Ob ein Hauptthema "Allgemeines" hinzugefügt werden soll
        include_methodik: Ob ein Hauptthema "Methodik und Didaktik" hinzugefügt werden soll
        discipline_uri: URI des Fachbereichs
        educational_context_uri: URI des Bildungskontexts
        education_sector: Bildungssektor
        model: LLM-Modell für die Generierung
        progress_callback: Callback-Funktion für Fortschrittsanzeige (erwartet einen Fortschrittswert zwischen 0-1)
        
    Returns:
        Optional[Dict]: Generierter Themenbaum als Dictionary oder None bei Fehler
    """
    try:
        # Metadaten vorbereiten
        metadata = {
            "title": f"Themenbaum: {topic}",
            "description": f"Automatisch generierter Themenbaum für: {topic}",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "settings": {
                "num_main": num_main,
                "num_sub": num_sub,
                "num_lehrplan": num_lehrplan,
                "include_general": include_general,
                "include_methodik": include_methodik,
                "model": model
            }
        }
        
        # Ermittle Fachbereich und Bildungsstufe als Text
        discipline_info = ""
        for k, v in DISCIPLINE_MAPPING.items():
            if v == discipline_uri:
                discipline_info = k
                break
                
        context_info = ""
        for k, v in EDUCATIONAL_CONTEXT_MAPPING.items():
            if v == educational_context_uri:
                context_info = k
                break
                
        # Liste zum Speichern bereits existierender Titel (zur Vermeidung von Duplikaten)
        existing_titles = []
        
        # Berechne Gesamtschritte für den Fortschrittsbalken
        total_steps = 1 + num_main + (num_main * num_sub)
        steps_done = 0
        
        # Sammlung für den gesamten Themenbaum
        collections = []
        
        # Schritt 1: Hauptthemen generieren
        if progress_callback:
            progress_callback(steps_done / total_steps, "Generiere Hauptthemen...")
            
        # Spezialanweisungen für Hauptthemen
        special_instructions = []
        if include_general:
            special_instructions.append("Füge 'Allgemeines' als erstes Hauptthema hinzu")
        if include_methodik:
            special_instructions.append("Füge 'Methodik und Didaktik' als letztes Hauptthema hinzu")
            
        special_text = ". ".join(special_instructions) if special_instructions else ""
        
        # Prompt für Hauptthemen
        main_prompt = f"""
        Erstelle {num_main} Hauptthemen für das Thema '{topic}'.
        {special_text}
        
        Die Hauptthemen sollten für das Fach {discipline_info} und die Bildungsstufe {context_info} relevant sein.
        Achte auf eine gute Abdeckung des Themas mit klar abgegrenzten Hauptthemen.
        
        Gib für jedes Hauptthema eine kurze Beschreibung an.
        """
        
        # Generiere Hauptthemen
        main_colls = generate_structured_text(client, main_prompt, model)
        if not main_colls or len(main_colls) == 0:
            if progress_callback:
                progress_callback(1.0, "Fehler bei der Hauptthemen-Generierung.")
            print("Fehler: Keine Hauptthemen generiert")
            return None
        
        collections.extend(main_colls)
        steps_done += 1
        
        if progress_callback:
            progress_callback(steps_done / total_steps, f"Hauptthemen erstellt: {len(main_colls)}")
        
        # Speichere Hauptthemen-Titel
        for mc in main_colls:
            existing_titles.append(mc.title)
            
        # Korrigiere Reihenfolge, falls spezielle Themen fehlen
        if include_general and not any(c.title.lower() == "allgemeines" for c in collections):
            prop = create_properties(
                title="Allgemeines", 
                shorttitle="Allgemeines",
                description=f"Grundlegende Aspekte und Überblick zu {topic}"
            )
            general_coll = Collection(
                title="Allgemeines",
                shorttitle="Allgemeines",
                properties=prop,
                subcollections=[]
            )
            collections.insert(0, general_coll)
            
        if include_methodik and not any(c.title.lower() in ["methodik und didaktik", "methodik & didaktik"] for c in collections):
            prop = create_properties(
                title="Methodik und Didaktik", 
                shorttitle="Methodik & Didaktik",
                description=f"Methoden und didaktische Ansätze für {topic}"
            )
            methodik_coll = Collection(
                title="Methodik und Didaktik",
                shorttitle="Methodik & Didaktik",
                properties=prop,
                subcollections=[]
            )
            collections.append(methodik_coll)
        
        # Schritt 2: Fachthemen für jedes Hauptthema generieren
        for i, mc in enumerate(collections):
            if progress_callback:
                progress_callback(steps_done / total_steps, f"Generiere Fachthemen für '{mc.title}'...")
            
            # Hauptthema-Beschreibung aus dem Properties-Objekt extrahieren
            # Direkt auf die cm_description-Liste zugreifen und das erste Element nehmen, wenn vorhanden
            mc_description = mc.properties.cm_description[0] if mc.properties.cm_description else ""
            
            # Prompt für Fachthemen
            sub_prompt = f"""
            Erstelle {num_sub} Fachthemen für das Hauptthema '{mc.title}' im Kontext von '{topic}'.
            
            Hauptthema-Beschreibung: {mc_description}
            Fach: {discipline_info}
            Bildungsstufe: {context_info}
            
            Die Fachthemen sollten spezifische Aspekte des Hauptthemas '{mc.title}' abdecken.
            Gib für jedes Fachthema eine kurze Beschreibung an.
            """
            
            # Generiere Fachthemen
            sub_colls = generate_structured_text(client, sub_prompt, model)
            if sub_colls:
                mc.subcollections = sub_colls
                for sc in sub_colls:
                    existing_titles.append(sc.title)
            
            steps_done += 1
            if progress_callback:
                progress_callback(steps_done / total_steps, f"Fachthemen für '{mc.title}' erstellt: {len(sub_colls)}")
            
            # Schritt 3: Lehrplanthemen für jedes Fachthema generieren
            for j, sc in enumerate(mc.subcollections):
                if progress_callback:
                    progress_callback(steps_done / total_steps, f"Generiere Lehrplanthemen für '{sc.title}'...")
                
                # Fachthema-Beschreibung aus dem Properties-Objekt extrahieren
                sc_description = sc.properties.cm_description[0] if sc.properties.cm_description else ""
                
                # Prompt für Lehrplanthemen
                lp_prompt = f"""
                Erstelle {num_lehrplan} detaillierte Lehrplanthemen für das Fachthema '{sc.title}' 
                im Rahmen des Hauptthemas '{mc.title}' zum Thema '{topic}'.
                
                Fachthema-Beschreibung: {sc_description}
                Fach: {discipline_info}
                Bildungsstufe: {context_info}
                
                Die Lehrplanthemen sollten spezifische Unterrichtsinhalte für '{sc.title}' darstellen.
                Gib für jedes Lehrplanthema eine ausführliche Beschreibung an.
                """
                
                # Generiere Lehrplanthemen
                lp_colls = generate_structured_text(client, lp_prompt, model)
                if lp_colls:
                    sc.subcollections = lp_colls
                    for lc in lp_colls:
                        existing_titles.append(lc.title)
                
                steps_done += 1
                if progress_callback:
                    progress_callback(steps_done / total_steps, f"Lehrplanthemen für '{sc.title}' erstellt: {len(lp_colls)}")
        
        # Aktualisiere Properties in allen Collections
        for coll in collections:
            update_collection_properties(coll, discipline_uri, educational_context_uri)
        
        # Topic Tree erstellen
        topic_tree = TopicTree(
            metadata=metadata,
            collection=collections
        )
        
        if progress_callback:
            progress_callback(1.0, "Themenbaum erfolgreich erstellt!")
            
        return topic_tree.model_dump()
    
    except Exception as e:
        print(f"Fehler bei der iterativen Generierung: {str(e)}")
        import traceback
        traceback.print_exc()
        if progress_callback:
            progress_callback(1.0, f"Fehler: {str(e)}")
        return None

def show_tree_generation_page(openai_key: str, model: str):
    """
    Zeigt die Seite zur Themenbaum-Generierung an.
    
    Args:
        openai_key: OpenAI API-Key
        model: LLM-Modell für die Generierung
    """
    st.title("🌳 Themenbaum Generator")
    st.write("Erstelle Hauptkategorien, Unterkategorien, weitere Unterkategorien ...")

    # Haupteingabefeld für das Thema
    themenbaumthema = st.text_area(
        "📝 Themenbaumthema",
        value="Physik in Anlehnung an die Lehrpläne der Sekundarstufe 2",
        height=80
    )

    # Settings in collapsible sections
    with st.expander("📊 Themenbaum Einstellungen", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            num_main = st.number_input("📌 Anzahl Hauptthemen", min_value=1, max_value=20, value=3, step=1)
        with col2:
            num_sub = st.number_input("📎 Anzahl Fachthemen pro Hauptthema", min_value=1, max_value=20, value=2, step=1)
        with col3:
            num_lehrplan = st.number_input("📑 Anzahl Lehrplanthemen pro Fachthema", min_value=1, max_value=20, value=1, step=1)

        col4, col5 = st.columns(2)
        with col4:
            include_general = st.checkbox("📋 Hauptthema 'Allgemeines' an erster Stelle?")
        with col5:
            include_methodik = st.checkbox("📝 Hauptthema 'Methodik und Didaktik' an letzter Stelle?")
            
        # Generierungsmodus
        generation_mode = st.radio(
            "Generierungsmodus",
            ["Einmal-Generierung", "Iterative Generierung"],
            index=0,
            help="Einmal-Generierung erstellt den gesamten Themenbaum in einem Durchgang. Iterative Generierung baut den Baum schrittweise auf, was mehr Zeit benötigt, aber präzisere Ergebnisse liefern kann."
        )

    with st.expander("🎓 Fachbereich & Stufe", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            discipline_options = list(DISCIPLINE_MAPPING.keys())
            discipline_default_index = discipline_options.index("Physik")
            selected_discipline = st.selectbox("📚 Fachbereich", discipline_options, index=discipline_default_index)
            discipline_uri = DISCIPLINE_MAPPING[selected_discipline]

        with col2:
            context_options = list(EDUCATIONAL_CONTEXT_MAPPING.keys())
            context_default_index = context_options.index("Sekundarstufe II")
            selected_context = st.selectbox("🏫 Bildungsstufe", context_options, index=context_default_index)
            educational_context_uri = EDUCATIONAL_CONTEXT_MAPPING[selected_context]

        with col3:
            sector_options = list(EDUCATION_SECTOR_MAPPING.keys())
            sector_default_index = sector_options.index("Allgemeinbildend")
            selected_sector = st.selectbox("🎯 Bildungssektor", sector_options, index=sector_default_index)
            education_sector = EDUCATION_SECTOR_MAPPING[selected_sector]

    # Generation button
    if st.button("🚀 Themenbaum generieren", type="primary", use_container_width=True):
        if not openai_key:
            st.error("Kein OpenAI API-Key angegeben.")
            return
        if not themenbaumthema.strip():
            st.error("Bitte ein Themenbaumthema eingeben.")
            return

        with st.spinner("Generiere Themenbaum... Dies kann einige Minuten dauern."):
            try:
                # OpenAI client initialisieren
                client = OpenAI(api_key=openai_key)
                
                # Fortschrittsbalken und Statustext
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Callback-Funktion für iterative Generierung
                def update_progress(progress, status):
                    progress_bar.progress(progress)
                    status_text.text(status)
                
                # Themenbaum generieren
                if generation_mode == "Einmal-Generierung":
                    tree_data = generate_topic_tree(
                        client=client,
                        topic=themenbaumthema,
                        num_main=num_main,
                        num_sub=num_sub,
                        num_lehrplan=num_lehrplan,
                        include_general=include_general,
                        include_methodik=include_methodik,
                        discipline_uri=discipline_uri,
                        educational_context_uri=educational_context_uri,
                        education_sector=education_sector,
                        model=model
                    )
                else:
                    tree_data = generate_topic_tree_iterative(
                        client=client,
                        topic=themenbaumthema,
                        num_main=num_main,
                        num_sub=num_sub,
                        num_lehrplan=num_lehrplan,
                        include_general=include_general,
                        include_methodik=include_methodik,
                        discipline_uri=discipline_uri,
                        educational_context_uri=educational_context_uri,
                        education_sector=education_sector,
                        model=model,
                        progress_callback=update_progress
                    )
                
                if tree_data:
                    # Speichere Themenbaum
                    filepath = save_json_with_timestamp(tree_data, prefix="themenbaum")
                    st.success(f"Themenbaum gespeichert unter: {filepath}")
                    
                    # Download Button
                    json_str = json.dumps(tree_data, ensure_ascii=False, indent=2)
                    st.download_button(
                        "💾 Themenbaum herunterladen",
                        data=json_str,
                        file_name=f"themenbaum_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                    
                    # Visualisierung des Themenbaums
                    st.subheader("📊 Themenbaum Übersicht")
                    
                    # Option zum Anzeigen der JSON-Daten
                    if st.checkbox("JSON-Daten anzeigen", value=False):
                        st.json(tree_data)
                    
                    # Visualisierung als Baumstruktur
                    for collection in tree_data.get("collection", []):
                        st.markdown(f"### {collection.get('title', '')}")
                        
                        # Korrekte Feldnamen verwenden (cm_description statt cm:description)
                        description = ""
                        if "properties" in collection:
                            props = collection["properties"]
                            if "cm_description" in props:
                                description = props["cm_description"][0] if props["cm_description"] else ""
                            elif "cm:description" in props:
                                description = props["cm:description"][0] if props["cm:description"] else ""
                        
                        st.markdown(description)
                        
                        for subcoll in collection.get("subcollections", []):
                            st.markdown(f"**└─ {subcoll.get('title', '')}**")
                            
                            # Korrekte Feldnamen für Unterkategorien
                            sub_description = ""
                            if "properties" in subcoll:
                                props = subcoll["properties"]
                                if "cm_description" in props:
                                    sub_description = props["cm_description"][0] if props["cm_description"] else ""
                                elif "cm:description" in props:
                                    sub_description = props["cm:description"][0] if props["cm:description"] else ""
                            
                            st.markdown(sub_description)
                            
                            for lp in subcoll.get("subcollections", []):
                                # Korrekte Feldnamen für Lehrplanthemen
                                lp_description = ""
                                if "properties" in lp:
                                    props = lp["properties"]
                                    if "cm_description" in props:
                                        lp_description = props["cm_description"][0] if props["cm_description"] else ""
                                    elif "cm:description" in props:
                                        lp_description = props["cm:description"][0] if props["cm:description"] else ""
                                
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;└─ *{lp.get('title', '')}*: {lp_description}")
                        
                        st.markdown("---")
                    
            except Exception as e:
                st.error(f"Fehler bei der Generierung: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
