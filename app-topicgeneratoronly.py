import os
import json
import time
import backoff
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import numpy as np
import requests
import urllib.parse

# Falls du bereits Pydantic V2 nutzt:
from pydantic import BaseModel, ValidationError, Field
from openai import OpenAI, RateLimitError, APIError
from dotenv import load_dotenv

###############################################################################
# 1) Laden der Umgebungsvariablen und Streamlit-Konfiguration
###############################################################################
load_dotenv()

# Ensure data directory exists
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

import streamlit as st
st.set_page_config(page_title="Themenbaum Generator", layout="wide")

def get_openai_key():
    """Liest den OpenAI-API-Key aus den Umgebungsvariablen."""
    return os.getenv("OPENAI_API_KEY", "")

def save_json_with_timestamp(data: dict, prefix: str, suffix: str = "") -> str:
    """
    Speichert JSON-Daten mit Zeitstempel im data Ordner.
    Returns: Gespeicherter Dateipfad
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}{suffix}.json"
    filepath = DATA_DIR / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, ensure_ascii=False, indent=2, fp=f)
    
    return str(filepath)

###############################################################################
# 2) Pydantic-Modelle: Properties, Collection, TopicTree
###############################################################################
class Properties(BaseModel):
    ccm_collectionshorttitle: List[str] = Field(default_factory=lambda: [""])
    ccm_taxonid: List[str] = Field(default_factory=lambda: ["http://w3id.org/openeduhub/vocabs/discipline/460"])
    cm_title: List[str]
    ccm_educationalintendedenduserrole: List[str] = Field(
        default_factory=lambda: ["http://w3id.org/openeduhub/vocabs/intendedEndUserRole/teacher"]
    )
    ccm_educationalcontext: List[str] = Field(
        default_factory=lambda: ["http://w3id.org/openeduhub/vocabs/educationalContext/sekundarstufe_1"]
    )
    cm_description: List[str]
    cclom_general_keyword: List[str] = Field(alias="cclom:general_keyword")

    class Config:
        populate_by_name = True
        alias_generator = lambda s: s.replace("_", ":")

    def to_dict(self) -> dict:
        return {
            "ccm:collectionshorttitle": self.ccm_collectionshorttitle,
            "ccm:taxonid": self.ccm_taxonid,
            "cm:title": self.cm_title,
            "ccm:educationalintendedenduserrole": self.ccm_educationalintendedenduserrole,
            "ccm:educationalcontext": self.ccm_educationalcontext,
            "cm:description": self.cm_description,
            "cclom:general_keyword": self.cclom_general_keyword
        }

class Collection(BaseModel):
    title: str
    shorttitle: str
    properties: Properties
    subcollections: Optional[List['Collection']] = Field(default_factory=list)

    def to_dict(self) -> dict:
        result = {
            "title": self.title,
            "shorttitle": self.shorttitle,
            "properties": self.properties.to_dict()
        }
        if self.subcollections:
            result["subcollections"] = [sub.to_dict() for sub in self.subcollections]
        return result

Collection.model_rebuild()

class TopicTree(BaseModel):
    collection: List[Collection]
    metadata: dict = Field(default_factory=lambda: {
        "title": "",
        "description": "",
        "target_audience": "",
        "created_at": "",
        "version": "1.0",
        "author": "Themenbaum Generator"
    })

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata,
            "collection": [c.to_dict() for c in self.collection]
        }

###############################################################################
# 3) Mappings für Fachbereiche & Co.
###############################################################################
DISCIPLINE_MAPPING = {
    "Keine Vorgabe": "",
    "Allgemein": "http://w3id.org/openeduhub/vocabs/discipline/720",
    "Alt-Griechisch": "http://w3id.org/openeduhub/vocabs/discipline/20003",
    "Agrarwirtschaft": "http://w3id.org/openeduhub/vocabs/discipline/04001",
    "Arbeit, Ernährung, Soziales": "http://w3id.org/openeduhub/vocabs/discipline/oeh01",
    "Arbeitslehre": "http://w3id.org/openeduhub/vocabs/discipline/020",
    "Arbeitssicherheit": "http://w3id.org/openeduhub/vocabs/discipline/04014",
    "Astronomie": "http://w3id.org/openeduhub/vocabs/discipline/46014",
    "Bautechnik": "http://w3id.org/openeduhub/vocabs/discipline/04002",
    "Berufliche Bildung": "http://w3id.org/openeduhub/vocabs/discipline/040",
    "Biologie": "http://w3id.org/openeduhub/vocabs/discipline/080",
    "Chemie": "http://w3id.org/openeduhub/vocabs/discipline/100",
    "Chinesisch": "http://w3id.org/openeduhub/vocabs/discipline/20041",
    "Darstellendes Spiel": "http://w3id.org/openeduhub/vocabs/discipline/12002",
    "Deutsch": "http://w3id.org/openeduhub/vocabs/discipline/120",
    "Deutsch als Zweitsprache": "http://w3id.org/openeduhub/vocabs/discipline/28002",
    "Elektrotechnik": "http://w3id.org/openeduhub/vocabs/discipline/04005",
    "Ernährung und Hauswirtschaft": "http://w3id.org/openeduhub/vocabs/discipline/04006",
    "Englisch": "http://w3id.org/openeduhub/vocabs/discipline/20001",
    "Pädagogik": "http://w3id.org/openeduhub/vocabs/discipline/440",
    "Esperanto": "http://w3id.org/openeduhub/vocabs/discipline/20090",
    "Ethik": "http://w3id.org/openeduhub/vocabs/discipline/160",
    "Farbtechnik und Raumgestaltung": "http://w3id.org/openeduhub/vocabs/discipline/04007",
    "Französisch": "http://w3id.org/openeduhub/vocabs/discipline/20002",
    "Geografie": "http://w3id.org/openeduhub/vocabs/discipline/220",
    "Geschichte": "http://w3id.org/openeduhub/vocabs/discipline/240",
    "Gesellschaftskunde": "http://w3id.org/openeduhub/vocabs/discipline/48005",
    "Gesundheit": "http://w3id.org/openeduhub/vocabs/discipline/260",
    "Hauswirtschaft": "http://w3id.org/openeduhub/vocabs/discipline/50001",
    "Holztechnik": "http://w3id.org/openeduhub/vocabs/discipline/04009",
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

###############################################################################
# 4) Konsolidierte Allgemeine Formatierungsregeln (Base Instructions)
###############################################################################

base_instructions = (
    "Du bist ein hilfreicher KI-Assistent für Lehr- und Lernsituationen. "
    "Antworte immer ausschließlich mit purem JSON (keine Code-Fences, kein Markdown). "
    "Falls du nicht antworten kannst, liefere ein leeres JSON-Objekt.\n\n"

    "FORMATIERUNGSREGELN:\n"
    "1) TITEL-REGELN:\n"
    "   - Verwende Langformen statt Abkürzungen\n"
    "   - Nutze 'vs.' für Gegenüberstellungen\n"
    "   - Verbinde verwandte Begriffe mit 'und'\n"
    "   - Vermeide Sonderzeichen\n"
    "   - Verwende Substantive\n"
    "   - Kennzeichne Homonyme mit runden Klammern\n"
    "   - Vermeide Artikel, Adjektive klein\n\n"
    "2) KURZTITEL-REGELN:\n"
    "   - Max. 20 Zeichen\n"
    "   - Keine Sonderzeichen\n"
    "   - Eindeutig und kurz\n\n"
    "3) BESCHREIBUNGS-REGELN:\n"
    "   - Max. 5 prägnante Sätze\n"
    "   - Definition → Relevanz → Merkmale → Anwendung\n"
    "   - Aktive Sprache\n\n"
    "4) KATEGORISIERUNG:\n"
    "   - Thema, Kompetenz, Vermittlung oder Redaktionelle Sammlung\n\n"
    "5) EINDEUTIGKEITS-REGEL:\n"
    "   - Keine doppelten Titel\n"
    "   - Existierende Titel NICHT erneut verwenden\n"
)

###############################################################################
# 5) Prompt-Templates (Mehrschritt)
###############################################################################

MAIN_PROMPT_TEMPLATE = """\
Erstelle eine Liste von {num_main} Hauptthemen 
für das Thema "{themenbaumthema}"{discipline_info}{context_info}.

Keine Code-Fences, kein Markdown, nur reines JSON-Array.

Folgende Titel sind bereits vergeben: {existing_titles}

{special_instructions}

Erwarte ein JSON-Array dieser Form:
[
  {{
    "title": "Name des Hauptthemas",
    "shorttitle": "Kurzer Titel",
    "description": "Beschreibung",
    "keywords": ["Schlagwort1", "Schlagwort2"]
  }}
]
"""

SUB_PROMPT_TEMPLATE = """\
Erstelle eine Liste von {num_sub} Unterthemen für das Hauptthema "{main_theme}"
im Kontext "{themenbaumthema}"{discipline_info}{context_info}.

Keine Code-Fences, kein Markdown, nur reines JSON-Array.

Folgende Titel sind bereits vergeben: {existing_titles}

Erwarte ein JSON-Array dieser Form:
[
  {{
    "title": "Name des Unterthemas",
    "shorttitle": "Kurzer Titel",
    "description": "Beschreibung",
    "keywords": ["Schlagwort1", "Schlagwort2"]
  }}
]
"""

LP_PROMPT_TEMPLATE = """\
Erstelle eine Liste von {num_lp} Lehrplanthemen für das Unterthema "{sub_theme}"
im Kontext "{themenbaumthema}"{discipline_info}{context_info}.

Keine Code-Fences, kein Markdown, nur reines JSON-Array.

Folgende Titel sind bereits vergeben: {existing_titles}

Erwarte ein JSON-Array dieser Form:
[
  {{
    "title": "Name des Lehrplanthemas",
    "shorttitle": "Kurzer Titel",
    "description": "Beschreibung",
    "keywords": ["Schlagwort1", "Schlagwort2"]
  }}
]
"""

###############################################################################
# 6) Hilfsfunktionen
###############################################################################
import math
import requests

def create_properties(
    title: str,
    shorttitle: str,
    description: str,
    keywords: List[str],
    discipline_uri: str = "",
    educational_context_uri: str = ""
) -> Properties:
    return Properties(
        ccm_collectionshorttitle=[shorttitle],
        ccm_taxonid=[discipline_uri] if discipline_uri else ["http://w3id.org/openeduhub/vocabs/discipline/460"],
        cm_title=[title],
        ccm_educationalintendedenduserrole=["http://w3id.org/openeduhub/vocabs/intendedEndUserRole/teacher"],
        ccm_educationalcontext=[educational_context_uri] if educational_context_uri else ["http://w3id.org/openeduhub/vocabs/educationalContext/sekundarstufe_1"],
        cm_description=[description],
        cclom_general_keyword=keywords
    )

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
            st.error("Antwort vom Modell ist leer.")
            return None

        raw = content.strip().strip("```").strip("```json").strip()
        data = json.loads(raw)
        if not isinstance(data, list):
            data = [data]

        results = []
        for item in data:
            title = item.get("title", "")
            shorttitle = item.get("shorttitle", "")
            desc = item.get("description", "")
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
            )
            results.append(c)

        return results
    except json.JSONDecodeError as jde:
        st.error(f"JSON Decode Error: {jde}")
        st.text(f"Rohdaten:\n{content}")
        return None
    except ValidationError as ve:
        st.error(f"Strukturfehler: {ve}")
        return None
    except Exception as e:
        st.error(f"Fehler bei der Anfrage: {e}")
        return None

def update_collection_properties(coll: Collection, discipline_uri: str, educational_context_uri: str):
    """Setzt Disziplin/Bildungsstufe rekursiv."""
    if not coll.properties.ccm_taxonid and discipline_uri:
        coll.properties.ccm_taxonid = [discipline_uri]
    if not coll.properties.ccm_educationalcontext and educational_context_uri:
        coll.properties.ccm_educationalcontext = [educational_context_uri]

    for subc in coll.subcollections:
        update_collection_properties(subc, discipline_uri, educational_context_uri)

###############################################################################
# 7) Streamlit UI mit 2 "Seiten" per Session-State
###############################################################################
def main():
    """
    Hauptfunktion der Streamlit-App.
    Initialisiert Session State und zeigt entsprechende Seite.
    """
    st.title("Themenbaum Generator")
    
    if "page" not in st.session_state:
        st.session_state.page = "tree"

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Einstellungen")

        # LLM Settings at top
        with st.expander("🤖 LLM Einstellungen", expanded=False):
            model = st.selectbox(
                "🔧 Sprachmodell",
                options=["gpt-4o-mini", "gpt-4o"],
                index=0
            )
            default_key = get_openai_key()
            openai_key = st.text_input("🔑 OpenAI API Key", value=default_key, type="password")

        # Navigation
        st.markdown("---")
        pages = {
            "Themenbaum erstellen": "tree",
            "JSON Vorschau": "preview"
        }
        page = st.radio("Navigation", pages.keys())
        st.session_state.page = pages[page]

    if not openai_key:
        st.error("Kein OpenAI API Key gefunden. Bitte setze die Umgebungsvariable OPENAI_API_KEY.")
        return
        
    if st.session_state.page == "tree":
        show_tree_page(openai_key, model)
    elif st.session_state.page == "preview":
        show_preview_page()

###############################################################################
# 8) Streamlit UI Funktionen
###############################################################################
def show_tree_page(openai_key: str, model: str):
    """
    Seite für die Themenbaum-Generierung.
    """
    st.write("Erstelle Hauptthemen, Fachthemen und Lehrplanthemen...")
    
    # Haupteingabefeld für das Thema
    themenbaumthema = st.text_area(
        "Themenbaumthema",
        value="Physik in Anlehnung an die Lehrpläne der Sekundarstufe 2",
        height=80
    )

    # Settings in collapsible sections
    with st.expander("Themenbaum Einstellungen", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            num_main = st.number_input("Anzahl Hauptthemen", min_value=1, max_value=20, value=5, step=1)
        with col2:
            num_sub = st.number_input("Anzahl Fachthemen pro Hauptthema", min_value=1, max_value=20, value=3, step=1)
        with col3:
            num_lehrplan = st.number_input("Anzahl Lehrplanthemen pro Fachthema", min_value=1, max_value=20, value=2, step=1)

        col4, col5 = st.columns(2)
        with col4:
            include_general = st.checkbox("Hauptthema 'Allgemeines' an erster Stelle?")
        with col5:
            include_methodik = st.checkbox("Hauptthema 'Methodik und Didaktik' an letzter Stelle?")

    with st.expander("Fachbereich & Stufe", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            discipline_options = list(DISCIPLINE_MAPPING.keys())
            discipline_default_index = discipline_options.index("Physik")
            selected_discipline = st.selectbox("Fachbereich", discipline_options, index=discipline_default_index)
            discipline_uri = DISCIPLINE_MAPPING[selected_discipline]

        with col2:
            context_options = list(EDUCATIONAL_CONTEXT_MAPPING.keys())
            context_default_index = context_options.index("Sekundarstufe II")
            selected_context = st.selectbox("Bildungsstufe", context_options, index=context_default_index)
            educational_context_uri = EDUCATIONAL_CONTEXT_MAPPING[selected_context]

    # Generation button
    if st.button("Themenbaum generieren", type="primary", use_container_width=True):
        if not openai_key:
            st.error("Kein OpenAI API-Key angegeben.")
            return

        try:
            client = OpenAI(api_key=openai_key)
        except Exception as e:
            st.error(f"OpenAI-Init-Fehler: {e}")
            return

        discipline_info = f" im Fach {selected_discipline}" if selected_discipline != "Keine Vorgabe" else ""
        context_info = f" für die {selected_context}" if selected_context != "Keine Vorgabe" else ""

        # Spezialanweisungen
        special_instructions = ""
        if include_general:
            special_instructions += "1) Hauptthema 'Allgemeines' an erster Stelle.\n"
        if include_methodik:
            special_instructions += "2) Hauptthema 'Methodik und Didaktik' an letzter Stelle.\n"
        if not special_instructions:
            special_instructions = "Keine weiteren Spezialanweisungen."

        existing_titles = []
        total_steps = 1 + num_main + (num_main * num_sub)
        steps_done = 0
        pbar = st.progress(0.0)
        info_txt = st.empty()

        # Schritt 1: Hauptthemen
        info_txt.text("Generiere Hauptthemen...")
        main_prompt = MAIN_PROMPT_TEMPLATE.format(
            num_main=num_main,
            themenbaumthema=themenbaumthema,
            discipline_info=discipline_info,
            context_info=context_info,
            existing_titles=json.dumps(existing_titles),
            special_instructions=special_instructions
        )
        main_colls = generate_structured_text(client, main_prompt, model)
        if not main_colls:
            st.error("Fehler bei Hauptthemen-Generierung.")
            return
        steps_done += 1
        pbar.progress(steps_done / total_steps)

        for mc in main_colls:
            existing_titles.append(mc.title)

        # Schritt 2: Fachthemen
        for mc in main_colls:
            info_txt.text(f"Generiere Fachthemen für '{mc.title}'...")
            sub_prompt = SUB_PROMPT_TEMPLATE.format(
                num_sub=num_sub,
                main_theme=mc.title,
                themenbaumthema=themenbaumthema,
                discipline_info=discipline_info,
                context_info=context_info,
                existing_titles=json.dumps(existing_titles)
            )
            sub_colls = generate_structured_text(client, sub_prompt, model)
            if sub_colls:
                mc.subcollections = sub_colls
                for sc in sub_colls:
                    existing_titles.append(sc.title)

            steps_done += 1
            pbar.progress(steps_done / total_steps)

            # Schritt 3: Lehrplanthemen
            for sc in mc.subcollections:
                info_txt.text(f"Generiere Lehrplanthemen für '{sc.title}'...")
                lp_prompt = LP_PROMPT_TEMPLATE.format(
                    num_lp=num_lehrplan,
                    sub_theme=sc.title,
                    themenbaumthema=themenbaumthema,
                    discipline_info=discipline_info,
                    context_info=context_info,
                    existing_titles=json.dumps(existing_titles)
                )
                lp_colls = generate_structured_text(client, lp_prompt, model)
                if lp_colls:
                    sc.subcollections = lp_colls
                    for lc in lp_colls:
                        existing_titles.append(lc.title)

                steps_done += 1
                pbar.progress(steps_done / total_steps)

        # Schritt 4: Properties
        for cobj in main_colls:
            update_collection_properties(cobj, discipline_uri, educational_context_uri)

        # Schritt 5: Endgültiger Themenbaum
        info_txt.text("Erstelle finalen Themenbaum...")
        topic_tree = TopicTree(
            collection=main_colls,
            metadata={
                "title": themenbaumthema,
                "description": f"Themenbaum für {themenbaumthema}",
                "target_audience": "Lehrkräfte und Bildungseinrichtungen",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "author": "Themenbaum Generator",
                "settings": {
                    "themenbaumthema": themenbaumthema,
                    "bildungsstufe": selected_context,
                    "fachbereich": selected_discipline,
                    "struktur": {
                        "hauptthemen": num_main,
                        "unterthemen_pro_hauptthema": num_sub,
                        "lehrplanthemen_pro_unterthema": num_lehrplan
                    }
                }
            }
        )
        final_data = topic_tree.to_dict()

        # Speichere JSON in data Ordner
        try:
            filepath = save_json_with_timestamp(final_data, prefix="themenbaum")
            st.success(f"Themenbaum gespeichert unter: {filepath}")
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")

        pbar.progress(1.0)
        info_txt.text("Fertig!")

        st.success("Themenbaum erfolgreich generiert!")
        st.json(final_data)
        
        # Download Button für manuelle Speicherung
        js_str = json.dumps(final_data, indent=2, ensure_ascii=False)
        st.download_button("JSON herunterladen", data=js_str, 
                         file_name=f"themenbaum_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                         mime="application/json")

def show_preview_page():
    """
    Seite für die JSON-Dateivorschau.
    """
    st.title("JSON Vorschau")
    st.write("Zeigt die generierten JSON-Dateien im data Ordner an.")
    
    json_files = get_json_files()
    if not json_files:
        st.warning("Keine JSON-Dateien im data Ordner gefunden.")
        return
        
    selected_file = st.selectbox(
        "Wähle eine JSON-Datei",
        options=json_files,
        format_func=lambda x: x.name
    )
    
    if selected_file:
        try:
            data = load_json_file(selected_file)
            st.json(data)
        except Exception as e:
            st.error(f"Fehler beim Laden der JSON-Datei: {e}")

if __name__ == "__main__":
    main()
