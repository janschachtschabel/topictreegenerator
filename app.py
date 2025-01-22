import os
import json
import time
import backoff
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
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
    additional_data: dict = Field(default_factory=dict)  
    # Hier speichern wir Kompendiumstext, später auch andere Entitäten etc.

    def to_dict(self) -> dict:
        result = {
            "title": self.title,
            "shorttitle": self.shorttitle,
            "properties": self.properties.to_dict()
        }
        if self.additional_data:
            result["additional_data"] = self.additional_data
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
für das Thema "{themenbaumthema}"{discipline_info}{context_info}{sector_info}.

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
im Kontext "{themenbaumthema}"{discipline_info}{context_info}{sector_info}.

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
im Kontext "{themenbaumthema}"{discipline_info}{context_info}{sector_info}.

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

ENTITY_EXTRACTION_PROMPT = """\
Bilde zu nachfolgendem Text eine Liste der wichtigsten Entitäten, deren Beschreibungen man auch bei Wikipedia finden könnte.
Gib diese mit Name, Klasse, Wikipediaurl aus.

TEXT:
{text}

Keine Code-Fences, kein Markdown, nur reines JSON-Array.

Liefere ein JSON-Array dieser Form:
[
  {{
    "entity-name": "Reflexion",
    "entity-class": "Physikalisches Phänomen",
    "wikipediaurl": "https://de.wikipedia.org/wiki/Reflexion_(Physik)"
  }}
]
"""

COMPENDIUM_PROMPT = """\
Hier ist der komplette Themenbaum (als JSON):
{full_tree}

Du sollst einen **kompakten** Text (ca. 2 A4-Seiten) für dieses einzelne Thema des genannten Themenbaums verfassen:
{topic_data}

Fasse das Wissen kurz, präzise und aktiv zusammen. Achte darauf, das die Metadaten des Themenbaums (Bildungsstufe, Disziplin, Bildungssektor)
für die Erstellung des Textes berücksichtigt werden, um Zielgruppe und Thema korrekt zu treffen.

Keine Code-Fences, kein Markdown, nur reines JSON-Array.

Liefere **nur** JSON, z.B.:
{{
  "compendium_text": "..."
}}
"""

QA_PROMPT_TEMPLATE = """\
Erstelle {total_questions} Frage-Antwort-Paare zur Sammlung '{title}'.
Beziehe dabei die Informationen zur Sammlung der Bildungsinhalte mit ein:
{collection}

Berücksichtige die Kontext-Metadaten des Themenbaums bei der Generierung:
{metadata_topictree}

Optional: {compendium}

Optional: {background_info_entity}

Verwende verschiedene Fragetypen die an den Bedürfnissen von Bildung orientieren wie z.B.:
- Faktische Fragen
- Verständnisfragen
- Interpretative Fragen
- Anwendungsbezogene Fragen
- Reflexionsfragen
- Vergleichsfragen
- Evaluative Fragen
- Hypothetische Fragen
- Metakognitive Fragen
- Entitäten-bezogene Fragen
- Didaktische Planungsfragen
- Differenzierung und Inklusion
- Fragen zur Lernmotivation und -entwicklung
- Fragen zur Nutzung digitaler Medien und kollaborativem Lernen
- Reflexions- und Weiterentwicklungsfragen für Lehrende
- Prüfungs- und Leistungsbewertungsfragen
- Lernzielorientierte Fragen
- Pädagogische Flexibilität und Zeitmanagement
- Kollaborative Lehrfragen
- Selbstreflexions- und Selbstevaluationsfragen für Lehrende
- Zugänglichkeit und Barrierefreiheit im Unterricht

Qualitätskriterien:
- Sachliche Korrektheit: Stelle sicher, dass alle Antworten korrekt und aktuell sind
- Verständlichkeit: Formuliere Fragen und Antworten klar und einfach, ohne die fachliche Genauigkeit zu beeinträchtigen
- Vertrauenswürdige Quellen: Die Antworten basieren auf vertrauenswürdigen Quellen
- Bedürfnisse der Lernenden: Richte die Fragen und Antworten auf die Bedürfnisse der Lernenden aus
- Rechtliche Unbedenklichkeit: Achte darauf, dass Inhalte rechtlich unbedenklich sind
- Didaktische Prinzipien: Folge anerkannten didaktischen Prinzipien
- Barrierefreiheit: Stelle sicher, dass die Inhalte barrierefrei sind
- Durchschnittliche Länge: Die Antworten sollten durchschnittlich {average_qa_length} Zeichen lang sein
- Variabilität: Verwende verschiedene Fragetypen gemäß den Anforderungen
- Schwierigkeit: Variiere den Schwierigkeitsgrad der Fragen

Keine Code-Fences, kein Markdown, nur reines JSON-Array.

Output Format:
[
  {{
    "question": "Frage 1",
    "answer": "Antwort 1"
  }},
  {{
    "question": "Frage 2",
    "answer": "Antwort 2"
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

@st.cache_resource
def load_embedding_model() -> SentenceTransformer:
    """Lädt das Embedding-Modell."""
    return SentenceTransformer('all-MiniLM-L6-v2')

def wikidata_fetch(params: dict) -> Optional[dict]:
    """
    Führt einen GET-Request an die Wikidata API aus.
    """
    url = "https://www.wikidata.org/w/api.php"
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Wikidata API Fehler: {e}")
        return None

def wikidata_search(query: str, entity_type: str = "", lang: str = "de") -> List[Dict[str, Any]]:
    """
    Sucht nach Wikidata-Einträgen für einen Begriff und filtert nach Entitätstyp.
    Kombiniert den Suchbegriff mit der Entitätsklasse für bessere Ergebnisse.
    """
    # Kombiniere Name und Typ für bessere Suche
    search_query = f"{query} {entity_type}".strip()
    
    params = {
        'action': 'wbsearchentities',
        'format': 'json',
        'search': search_query,
        'language': lang,
        'limit': 20  # Erhöhe Limit für bessere Trefferquote
    }
    
    # Versuche zuerst mit Original-Titel
    response = requests.get("https://www.wikidata.org/w/api.php", params=params)
    data = response.json()
    pages = data["query"]["pages"]
    page = next(iter(pages.values()))
    
    content = page.get("extract", "").strip()
    if content:
        return content
            
    # Wenn kein Inhalt, versuche mit URL-decodiertem Titel
    decoded_title = urllib.parse.unquote(title)
    if decoded_title != title:  # Nur wenn sich der Titel unterscheidet
        params["titles"] = decoded_title
        response = requests.get("https://www.wikidata.org/w/api.php", params=params)
        data = response.json()
        pages = data["query"]["pages"]
        page = next(iter(pages.values()))
        content = page.get("extract", "").strip()
        if content:
            return content
                
    return None
        
def fetch_wikidata_details(entity_id: str, lang: str = "de") -> dict:
    """
    Ruft Details eines Wikidata-Eintrags ab.
    """
    params = {
        'action': 'wbgetentities',
        'ids': entity_id,
        'props': 'labels|descriptions',
        'languages': lang,
        'format': 'json'
    }
    response = wikidata_fetch(params)
    if response and "entities" in response:
        return response["entities"].get(entity_id, {})
    return {}

def get_wikidata_type(entity_id: str, lang: str = "de") -> Dict[str, str]:
    """
    Holt den Entitätstyp (P31 = "instance of") für einen Wikidata-Eintrag.
    """
    params = {
        'action': 'wbgetentities',
        'ids': entity_id,
        'props': 'claims',
        'languages': lang,
        'format': 'json'
    }
    
    response = wikidata_fetch(params)
    if not response or "entities" not in response:
        return {"type": "", "type_id": ""}
        
    entity = response["entities"].get(entity_id, {})
    claims = entity.get("claims", {})
    
    # P31 ist die Property für "instance of"
    instance_of = claims.get("P31", [])
    if not instance_of:
        return {"type": "", "type_id": ""}
        
    # Hole die erste "instance of" Angabe
    type_id = instance_of[0].get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id", "")
    if not type_id:
        return {"type": "", "type_id": ""}
        
    # Hole den Label für den Typ
    type_params = {
        'action': 'wbgetentities',
        'ids': type_id,
        'props': 'labels',
        'languages': lang,
        'format': 'json'
    }
    
    type_response = wikidata_fetch(type_params)
    if not type_response or "entities" not in type_response:
        return {"type": "", "type_id": type_id}
        
    type_label = type_response["entities"].get(type_id, {}).get("labels", {}).get(lang, {}).get("value", "")
    return {"type": type_label, "type_id": type_id}

def find_best_wikidata_match(client: OpenAI, entity_name: str, entity_class: str, entity_description: str = "") -> Optional[dict]:
    """
    Findet den besten Wikidata-Match für eine Entität mittels LLM.
    """
    # Hole Wikidata-Kandidaten
    candidates = get_wikidata_candidates(entity_name)
    if not candidates:
        return None
        
    # Erstelle Prompt für LLM
    prompt = f"""
    Finde den besten Wikidata-Match für folgende Entität:
    Name: {entity_name}
    Klasse: {entity_class}
    Beschreibung: {entity_description}

    Wikidata-Kandidaten:
    {json.dumps(candidates, indent=2, ensure_ascii=False)}

    Antworte mit einem JSON-Objekt im Format:
    {{
        "wikidata_id": "Q...",  # Wikidata ID des besten Matches oder null wenn kein Match
        "wikidata_label": "...", # Label des Matches oder null
        "wikidata_description": "..." # Beschreibung des Matches oder null
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        # Parse JSON response
        result = json.loads(response.choices[0].message.content)
        
        # Wenn kein Match gefunden wurde
        if not result["wikidata_id"]:
            return None
            
        return result
        
    except Exception as e:
        st.error(f"Fehler beim LLM-Matching: {str(e)}")
        return None

def count_nodes(node):
    """Zählt rekursiv die Gesamtanzahl der Knoten im Baum."""
    if not isinstance(node, dict):
        return 0
        
    count = 1  # Zähle aktuellen Knoten
    
    # Zähle Untersammlungen
    if "subcollections" in node and isinstance(node["subcollections"], list):
        for subnode in node["subcollections"]:
            count += count_nodes(subnode)
            
    return count

def count_entities_in_tree(node_list: List[dict]) -> int:
    """
    Zählt die Gesamtanzahl der Entitäten im Baum.
    """
    total = 0
    for node in node_list:
        if "additional_data" in node and "entities" in node["additional_data"]:
            total += len(node["additional_data"]["entities"])
        if "subcollections" in node:
            total += count_entities_in_tree(node["subcollections"])
    return total

def traverse_and_compendium(
    client: OpenAI,
    model: str,
    node_list: List[dict],
    full_tree_str: str,
    steps_done: int,
    total_steps: int,
    progress_bar,
    status_msg,
    include_wikipedia: bool = False
):
    """
    Durchläuft Rekursiv alle Knoten, generiert erweiterten kompendialen Text und optional Wikipedia-Entitäten.
    """
    for node in node_list:
        status_msg.text(f"Generiere Kompendium für '{node['title']}'...")
        
        # Generiere Kompendium
        compendium = generate_compendium_for_topic(
            client=client,
            model=model,
            prompt=COMPENDIUM_PROMPT.format(
                full_tree=full_tree_str,
                topic_data=json.dumps(node, ensure_ascii=False)
            )
        )
        
        if compendium and "compendium_text" in compendium:
            if "additional_data" not in node:
                node["additional_data"] = {}
            node["additional_data"]["compendium_text"] = compendium["compendium_text"]
            
            # Optional: Verarbeite Wikipedia-Entitäten
            if include_wikipedia:
                node = process_entities_for_topic(
                    client=client,
                    model=model,
                    topic_data=node,
                    compendium_text=compendium["compendium_text"]
                )

        steps_done += 1
        progress_bar.progress(steps_done / total_steps)

        if "subcollections" in node:
            steps_done = traverse_and_compendium(
                client, model, node["subcollections"],
                full_tree_str, steps_done, total_steps,
                progress_bar, status_msg, include_wikipedia
            )

    return steps_done

def process_entities_for_topic(client: OpenAI, model: str, topic_data: dict, compendium_text: str) -> dict:
    """
    Verarbeitet Entitäten für ein Thema und reichert sie mit Wikipedia-Inhalten an.
    """
    # Extrahiere Entitäten
    entities = extract_entities(client, compendium_text, model)
    
    if not entities:
        return topic_data
        
    # Hole Wikipedia Inhalte für jede Entität
    enriched_entities = []
    for entity in entities:
        wiki_content = get_wikipedia_content(entity["wikipediaurl"])
        if wiki_content:
            entity["wikipedia_content"] = wiki_content
        enriched_entities.append(entity)
    
    # Füge die angereicherten Entitäten zu additional_data hinzu
    if "additional_data" not in topic_data:
        topic_data["additional_data"] = {}
    
    topic_data["additional_data"]["entities"] = enriched_entities
    return topic_data

@backoff.on_exception(backoff.expo, (RateLimitError, APIError), max_tries=5, jitter=backoff.full_jitter)
def generate_compendium_for_topic(client: OpenAI, model: str, prompt: str) -> Optional[dict]:
    """Fragt das Modell => JSON-Objekt {'compendium_text': '...'}."""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Du bist ein KI-Assistent. Antworte nur in JSON, kein Markdown."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=4000,
        temperature=0.7
    )
    content = resp.choices[0].message.content.strip()
    raw = content.strip("```").strip("```json").strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        return None
    except json.JSONDecodeError:
        return None

def extract_entities(client: OpenAI, text: str, model: str) -> Optional[List[dict]]:
    """
    Extrahiert wichtige Entitäten aus einem Text, die bei Wikipedia gefunden werden können.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": base_instructions},
                {"role": "user", "content": ENTITY_EXTRACTION_PROMPT.format(text=text)}
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        content = response.choices[0].message.content

        if not content or not content.strip():
            st.error("Keine Entitäten gefunden.")
            return None

        content = content.strip().strip('```').strip('```json').strip()
        data = json.loads(content)
        
        if not isinstance(data, list):
            data = [data]
            
        return data

    except json.JSONDecodeError as jde:
        st.error(f"JSON Decode Error bei Entitäten: {jde}")
        return None
    except Exception as e:
        st.error(f"Fehler bei der Entitätsextraktion: {e}")
        return None

def find_wikipedia_url(term: str, entity_class: str = None, language: str = "de") -> Optional[str]:
    """
    Sucht die korrekte Wikipedia-URL für einen Begriff.
    Berücksichtigt optional die Entitätsklasse für bessere Suchtreffer.
    """
    # Kombiniere Begriff und Klasse für bessere Suche
    search_term = term
    if entity_class and entity_class.lower() not in ["unbekannt", "unknown", "none", ""]:
        search_term = f"{term} {entity_class}"
        
    endpoint = f"https://{language}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": search_term,
        "format": "json",
    }
    
    try:
        response = requests.get(endpoint, params=params).json()
        if response["query"]["search"]:
            page_title = response["query"]["search"][0]["title"]
            return f"https://{language}.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
    except Exception as e:
        # Fehler leise unterdrücken und None zurückgeben
        pass
    return None

def correct_wikipedia_urls(entities: List[dict]) -> List[dict]:
    """
    Korrigiert fehlerhafte Wikipedia-URLs und holt fehlende Inhalte.
    Berücksichtigt die Entitätsklasse für bessere Suchtreffer.
    """
    for entity in entities:
        # Überspringe Entitäten die bereits Content haben
        if entity.get("wikipedia_content"):
            continue
            
        # Versuche URL-Korrektur mit Entitätsname und -klasse
        entity_name = entity.get("entity-name", "")
        entity_class = entity.get("entity-class", "")
        
        corrected_url = find_wikipedia_url(entity_name, entity_class)
        if corrected_url:
            entity["wikipediaurl"] = corrected_url
            # Hole Inhalt mit korrigierter URL
            content = get_wikipedia_content(corrected_url)
            if content:
                entity["wikipedia_content"] = content
                
    return entities

def get_wikipedia_content(url: str) -> Optional[str]:
    """
    Holt den Inhalt einer Wikipedia-Seite.
    Folgt Redirects und versucht verschiedene URL-Varianten.
    """
    try:
        # Extrahiere Titel aus URL und decodiere
        title = url.split("/wiki/")[-1]
        title = urllib.parse.unquote(title).replace("_", " ")
        
        # API-Parameter
        api_url = "https://de.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "prop": "extracts|info",
            "exintro": 1,
            "explaintext": 1,
            "redirects": 1,  # Folge Redirects
            "titles": title
        }
        
        response = requests.get(api_url, params=params)
        data = response.json()
        pages = data["query"]["pages"]
        
        # Hole erste Seite
        page = next(iter(pages.values()))
        
        # Prüfe auf Inhalt
        if "extract" in page:
            content = page["extract"].strip()
            if content:
                return content
                
    except Exception as e:
        # Fehler leise unterdrücken
        pass
        
    return None

def get_wikidata_candidates(query: str, lang: str = "de") -> List[dict]:
    """
    Sucht nach passenden Wikidata-Einträgen für einen Suchbegriff.
    """
    endpoint = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": lang,
        "search": query,
        "limit": 5  # Begrenzt auf 5 Kandidaten
    }
    
    try:
        response = requests.get(endpoint, params=params)
        data = response.json()
        
        if "search" in data:
            return [{
                "id": item["id"],
                "label": item.get("label", ""),
                "description": item.get("description", "")
            } for item in data["search"]]
            
        return []
        
    except Exception as e:
        st.error(f"Fehler bei Wikidata-Suche: {str(e)}")
        return []

def process_node_urls(node: dict, progress_bar: st.progress, progress_text: st.empty, 
                     current: int, total: int, start_percent: float, end_percent: float) -> int:
    """
    Verarbeitet URLs in einem Node und aktualisiert den Fortschritt.
    """
    if "additional_data" in node and "entities" in node["additional_data"]:
        entities_count = len(node["additional_data"]["entities"])
        if entities_count > 0:
            progress = start_percent + (end_percent - start_percent) * (current / total)
            progress_bar.progress(progress)
            progress_text.text(f"Korrigiere Wikipedia-URLs für Node {current}/{total}")
            
            node["additional_data"]["entities"] = correct_wikipedia_urls(
                node["additional_data"]["entities"]
            )
        current += 1
        
    if "subcollections" in node:
        for subnode in node["subcollections"]:
            current = process_node_urls(subnode, progress_bar, progress_text, 
                                     current, total, start_percent, end_percent)
    
    return current

def process_node_wikidata(node: dict, model: SentenceTransformer, 
                         progress_bar: st.progress, progress_text: st.empty,
                         current: int, total: int, 
                         start_percent: float, end_percent: float) -> int:
    """
    Verarbeitet Wikidata-Informationen in einem Node und aktualisiert den Fortschritt.
    """
    if "additional_data" in node and "entities" in node["additional_data"]:
        entities = node["additional_data"]["entities"]
        if entities:
            node_progress_start = start_percent + (end_percent - start_percent) * (current / total)
            node_progress_end = start_percent + (end_percent - start_percent) * ((current + 1) / total)
            
            node["additional_data"]["entities"] = process_entities_with_wikidata(
                entities, model, progress_bar, progress_text,
                node_progress_start, node_progress_end
            )
        current += 1
        
    if "subcollections" in node:
        for subnode in node["subcollections"]:
            current = process_node_wikidata(subnode, model, progress_bar, progress_text,
                                         current, total, start_percent, end_percent)
    
    return current

def process_entities_with_wikidata(entities: List[dict], model: SentenceTransformer, 
                                 progress_bar: st.progress, progress_text: st.empty,
                                 start_percent: float, end_percent: float) -> List[dict]:
    """
    Verarbeitet eine Liste von Entitäten und ergänzt Wikidata-Informationen.
    """
    total_entities = len(entities)
    for idx, entity in enumerate(entities):
        # Aktualisiere Fortschritt
        progress = start_percent + (end_percent - start_percent) * (idx / total_entities)
        progress_bar.progress(progress)
        progress_text.text(f"Verarbeite Wikidata für Entität {idx + 1}/{total_entities}: {entity['entity-name']}")
        
        try:
            wikidata_match = find_best_wikidata_match(
                client=OpenAI(api_key=get_openai_key()),
                entity_name=entity["entity-name"],
                entity_class=entity["entity-class"],
                entity_description=entity.get("description", "")
            )
            
            if wikidata_match:
                # Füge Wikidata-Informationen zur Entität hinzu
                entity.update({
                    "wikidata_id": wikidata_match["wikidata_id"],
                    "wikidata_label": wikidata_match["wikidata_label"],
                    "wikidata_description": wikidata_match["wikidata_description"]
                })
                
        except Exception as e:
            # Fehler bei einzelner Entität überspringen
            continue
    
    return entities

def get_json_files() -> List[Path]:
    """
    Gibt eine Liste aller JSON-Dateien im data Ordner zurück, sortiert nach Änderungsdatum.
    """
    return sorted(DATA_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)

def load_json_file(filepath: Path) -> dict:
    """
    Lädt eine JSON-Datei.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

###############################################################################
# 8) Streamlit UI mit 2 "Seiten" per Session-State
###############################################################################
def main():
    if "page_mode" not in st.session_state:
        st.session_state["page_mode"] = "tree"

    st.title("🌳 Themenbaum Generator (Mehrstufig)")

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

    # Initialize session state for page mode if not exists
    if "page_mode" not in st.session_state:
        st.session_state.page_mode = "tree"

    # Show the appropriate page based on mode
    if st.session_state.page_mode == "tree":
        show_tree_page(openai_key, model)
    elif st.session_state.page_mode == "preview":
        show_preview_page()
    elif st.session_state.page_mode == "qa":
        show_qa_page(openai_key, model)
    else:
        show_compendium_page(openai_key, model)


def show_tree_page(openai_key: str, model: str):
    """
    Mehrstufige Themenbaum-Generierung
    """
    st.write("Erstelle Hauptthemen, Fachthemen und Lehrplanthemen...")

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
            num_main = st.number_input("📌 Anzahl Hauptthemen", min_value=1, max_value=20, value=5, step=1)
        with col2:
            num_sub = st.number_input("📎 Anzahl Fachthemen pro Hauptthema", min_value=1, max_value=20, value=3, step=1)
        with col3:
            num_lehrplan = st.number_input("📑 Anzahl Lehrplanthemen pro Fachthema", min_value=1, max_value=20, value=2, step=1)

        col4, col5 = st.columns(2)
        with col4:
            include_general = st.checkbox("📋 Hauptthema 'Allgemeines' an erster Stelle?")
        with col5:
            include_methodik = st.checkbox("📝 Hauptthema 'Methodik und Didaktik' an letzter Stelle?")

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

        try:
            client = OpenAI(api_key=openai_key)
        except Exception as e:
            st.error(f"Fehler beim Initialisieren: {e}")
            return

        discipline_info = f" im Fach {selected_discipline}" if selected_discipline != "Keine Vorgabe" else ""
        context_info = f" für die {selected_context}" if selected_context != "Keine Vorgabe" else ""
        sector_info = f" im {selected_sector}en Bildungssektor" if selected_sector != "Keine Vorgabe" else ""

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
            sector_info=sector_info,
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
                sector_info=sector_info,
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
                    sector_info=sector_info,
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
                    "bildungssektor": selected_sector,
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
        st.download_button("💾 JSON herunterladen", data=js_str, 
                         file_name=f"themenbaum_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                         mime="application/json")


def show_preview_page():
    """
    Seite für die JSON-Dateivorschau.
    """
    st.title("🔍 Dateivorschau")
    st.write("Wähle eine JSON-Datei aus dem data Ordner zur Vorschau.")

    json_files = get_json_files()
    if not json_files:
        st.warning("Keine JSON-Dateien im data Ordner gefunden.")
        return

    selected_file = st.selectbox(
        "🗂 Wähle eine JSON-Datei",
        options=json_files,
        format_func=lambda x: x.name
    )

    if selected_file:
        try:
            json_data = load_json_file(selected_file)
            st.json(json_data)
        except Exception as e:
            st.error(f"Fehler beim Laden der JSON-Datei: {e}")


def show_qa_page(openai_key: str, model: str):
    """
    Seite für die Q&A-Generierung.
    """
    st.title("❓ Frage & Antwort Generierung")
    st.write("Generiere Frage-Antwort-Paare für jede Sammlung im Themenbaum.")

    json_files = get_json_files()
    if not json_files:
        st.warning("Keine JSON-Dateien im data Ordner gefunden.")
        return

    selected_file = st.selectbox(
        "🗂 Wähle einen Themenbaum",
        options=json_files,
        format_func=lambda x: x.name
    )

    # Einstellungen für Q&A-Generierung
    col1, col2 = st.columns(2)
    with col1:
        num_questions = st.number_input(
            "📝 Anzahl Fragen pro Sammlung",
            min_value=1,
            max_value=100,
            value=20,
            step=1
        )
    with col2:
        average_length = st.number_input(
            "📏 Durchschnittliche Antwortlänge (Zeichen)",
            min_value=100,
            max_value=2000,
            value=300,
            step=100
        )

    # Optionen für zusätzliche Informationen
    include_compendium = st.checkbox(
        "📚 Kompendiale Texte einbeziehen",
        value=True,
        help="Bezieht die generierten Kompendium-Texte in die Q&A-Generierung ein"
    )
    include_entities = st.checkbox(
        "🔍 Entitäten-Informationen einbeziehen",
        value=True,
        help="Bezieht Wikipedia- und Wikidata-Informationen der Entitäten ein"
    )

    if st.button("🚀 Starte Q&A-Generierung", type="primary", use_container_width=True):
        if not selected_file:
            st.error("Bitte wähle eine JSON-Datei aus.")
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

        st.info("Berechne Gesamtanzahl der Knoten...")
        total_nodes = 0
        if "collection" in tree_data and isinstance(tree_data["collection"], list):
            st.write("Analysiere Themenbaum:")
            for root_node in tree_data["collection"]:
                nodes_in_root = count_nodes(root_node)
                total_nodes += nodes_in_root
                st.write(f"- {root_node.get('title', 'Unbekannt')}: {nodes_in_root} Knoten")
                
        st.write(f"\nGesamtanzahl der Knoten: {total_nodes}")
                
        # Initialisiere Fortschrittsanzeige
        progress_bar = st.progress(0)
        progress_text = st.empty()
                
        # Verarbeite jeden Root-Knoten
        current = 0
        if "collection" in tree_data and isinstance(tree_data["collection"], list):
            root_nodes = tree_data["collection"]
            num_roots = len(root_nodes)
                    
            for i, root_node in enumerate(root_nodes):
                st.write(f"\nVerarbeite Hauptthema ({i+1}/{num_roots}): {root_node.get('title', 'Unbekannt')}")
                        
                # Berechne Fortschrittsbereich für diesen Root
                start_percent = i / num_roots
                end_percent = (i + 1) / num_roots
                        
                # Verarbeite Root und seine Unterknoten
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
                    include_entities=include_entities
                )
                        
                st.write(f"Hauptthema {i+1} abgeschlossen: {current}/{total_nodes} Knoten verarbeitet")

        # Speichere erweiterte JSON
        try:
            filepath = save_json_with_timestamp(tree_data, prefix="themenbaum", suffix="_qa")
            st.success(f"Q&A-Version gespeichert unter: {filepath}")
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")

        st.success("Q&A-Generierung abgeschlossen!")
        
        # Download Button
        final_qa = json.dumps(tree_data, indent=2, ensure_ascii=False)
        st.download_button(
            "💾 JSON mit Q&A herunterladen",
            data=final_qa,
            file_name=f"themenbaum_qa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )


def show_compendium_page(openai_key: str, model: str):
    """
    Seite für Kompendiale Texte.
    """
    st.title("📚 Kompendiale Texte generieren")
    st.write("Füge zu jedem Themen einen 2-seitigen kompakten Text hinzu. Bilde auf Basis des Textes Entitäten und rufe Wissen ab.")

    json_files = get_json_files()
    if not json_files:
        st.warning("Keine JSON-Dateien im data Ordner gefunden.")
        return

    selected_file = st.selectbox(
        "🗂 Wähle einen Themenbaum",
        options=json_files,
        format_func=lambda x: x.name
    )

    # Wikipedia und Wikidata Optionen
    col1, col2, col3 = st.columns(3)
    with col1:
        include_wikipedia = st.checkbox(
            "🌐 Texte erweitern und Entitäten extrahieren",
            value=False,
            help="Generiert kompendiale Texte und extrahiert wichtige Begriffe und deren Wikipedia-URLs."
        )
    with col2:
        auto_correct_urls = st.checkbox(
            "🔄 Wikipedia-URLs korrigieren",
            value=True,
            help="Versucht fehlerhafte Wikipedia-URLs mit Hilfe einer Suchfunktion zu korrigiere.",
            disabled=not include_wikipedia
        )
    with col3:
        include_wikidata = st.checkbox(
            "🔍 Wikidata-Verlinkung",
            value=True,
            help="Verlinkt Entitäten mit Wikidata-Einträgen",
            disabled=not include_wikipedia
        )

    if st.button("🚀 Starte Kompendium-Erstellung", type="primary", use_container_width=True):
        if not selected_file:
            st.error("Bitte wähle eine JSON-Datei aus.")
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

        # Lade Embedding Model wenn Wikidata aktiviert
        embedding_model = None
        if include_wikipedia and include_wikidata:
            with st.spinner("Lade Embedding-Modell..."):
                embedding_model = load_embedding_model()

        st.info("Berechne Gesamtanzahl der Knoten (Prompt-Aufrufe)...")
        total_nodes = 0
        if "collection" in tree_data and isinstance(tree_data["collection"], list):
            st.write("Analysiere Themenbaum:")
            for root_node in tree_data["collection"]:
                nodes_in_root = count_nodes(root_node)
                total_nodes += nodes_in_root
                st.write(f"- {root_node.get('title', 'Unbekannt')}: {nodes_in_root} Knoten")
                
        st.write(f"\nGesamtanzahl der Knoten: {total_nodes}")

        full_tree_str = json.dumps(tree_data, ensure_ascii=False, indent=2)

        # Rekursiv durch alle collection-Knoten
        steps_done = traverse_and_compendium(
            client=client,
            model=model,
            node_list=tree_data["collection"],
            full_tree_str=full_tree_str,
            steps_done=0,
            total_steps=total_nodes,
            progress_bar=st.progress(0.0),
            status_msg=st.empty(),
            include_wikipedia=include_wikipedia
        )

        # Optional: Korrigiere Wikipedia-URLs
        if include_wikipedia and auto_correct_urls:
            url_status = st.empty()
            url_status.text("Zähle Nodes für URL-Korrektur...")
            total_nodes = 0
            if "collection" in tree_data and isinstance(tree_data["collection"], list):
                for root_node in tree_data["collection"]:
                    total_nodes += count_nodes(root_node)
                    
            url_progress = st.progress(0.0)
            url_status.text("Korrigiere fehlerhafte Wikipedia-URLs...")
            
            process_node_urls(tree_data["collection"][0], url_progress, url_status,
                            0, total_nodes, 0.0, 1.0)
            
            url_progress.empty()
            url_status.empty()

        # Optional: Wikidata Verlinkung
        if include_wikipedia and include_wikidata and embedding_model:
            wikidata_status = st.empty()
            wikidata_status.text("Zähle Nodes für Wikidata-Verlinkung...")
            total_nodes = 0
            if "collection" in tree_data and isinstance(tree_data["collection"], list):
                for root_node in tree_data["collection"]:
                    total_nodes += count_nodes(root_node)
                    
            wikidata_progress = st.progress(0.0)
            wikidata_status.text("Verlinke Entitäten mit Wikidata...")
            
            process_node_wikidata(tree_data["collection"][0], embedding_model,
                                wikidata_progress, wikidata_status,
                                0, total_nodes, 0.0, 1.0)
            
            wikidata_progress.empty()
            wikidata_status.empty()

        # Speichere erweiterte JSON in data Ordner
        try:
            filepath = save_json_with_timestamp(tree_data, prefix="themenbaum", suffix="_kompendium")
            st.success(f"Erweiterte Version gespeichert unter: {filepath}")
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")

        st.success("Kompendiale Texte hinzugefügt!")
        
        # Download Button für manuelle Speicherung
        final_comp = json.dumps(tree_data, indent=2, ensure_ascii=False)
        st.download_button(
            "💾 JSON mit Kompendium herunterladen",
            data=final_comp,
            file_name=f"themenbaum_kompendium_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

def generate_qa_pairs(client: OpenAI, collection: dict, metadata: dict, 
                    num_questions: int = 20, include_compendium: bool = False,
                    include_entities: bool = False, average_qa_length: int = 300) -> List[dict]:
    """
    Generiert Frage-Antwort-Paare für eine Sammlung.
    """
    # Sammle Kontext-Informationen
    title = collection.get("title", "")
    description = collection.get("description", "")
    keywords = collection.get("keywords", [])
    
    collection_info = {
        "title": title,
        "description": description,
        "keywords": keywords
    }
    
    # Optional: Füge Kompendium hinzu
    compendium_text = ""
    if include_compendium and "compendium_text" in collection:
        compendium_text = collection["compendium_text"]
        
    # Optional: Füge Entitäten-Informationen hinzu
    entities_info = ""
    if include_entities and "additional_data" in collection and "entities" in collection["additional_data"]:
        entities = collection["additional_data"]["entities"]
        entities_info = "\n".join([
            f"Entity: {e['entity-name']}\n"
            f"Class: {e['entity-class']}\n"
            f"Description: {e.get('description', '')}\n"
            f"Wikipedia: {e.get('wikipedia_content', '')}\n"
            for e in entities
        ])
    
    # Erstelle Prompt
    prompt = QA_PROMPT_TEMPLATE.format(
        total_questions=num_questions,
        title=title,
        collection=json.dumps(collection_info, ensure_ascii=False),
        metadata_topictree=json.dumps(metadata, ensure_ascii=False),
        compendium=compendium_text if include_compendium else "",
        background_info_entity=entities_info if include_entities else "",
        average_qa_length=average_qa_length
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        # Parse JSON response
        qa_pairs = json.loads(response.choices[0].message.content)
        return qa_pairs
        
    except Exception as e:
        st.error(f"Fehler bei QA-Generierung für '{title}': {str(e)}")
        return []

def process_node_qa(client: OpenAI, node: dict, metadata: dict,
                   progress_bar: st.progress, progress_text: st.empty,
                   current: int, total: int, start_percent: float, end_percent: float,
                   num_questions: int = 20, include_compendium: bool = False,
                   include_entities: bool = False) -> int:
    """
    Verarbeitet QA-Generierung für einen Node und seine Unterknoten.
    Verarbeitet rekursiv alle Ebenen des Themenbaums.
    """
    if not isinstance(node, dict) or "title" not in node:
        return current

    # Aktualisiere Fortschritt für aktuellen Node
    progress = start_percent + ((end_percent - start_percent) * (current / max(1, total)))
    progress_bar.progress(progress)
    progress_text.text(f"Generiere Q&A für {current}/{total}: {node['title']}")
    
    try:
        # Generiere QA-Paare für aktuellen Node
        qa_pairs = generate_qa_pairs(
            client=client,
            collection=node,
            metadata=metadata,
            num_questions=num_questions,
            include_compendium=include_compendium,
            include_entities=include_entities
        )
        
        # Speichere QA-Paare
        if qa_pairs:
            if "additional_data" not in node:
                node["additional_data"] = {}
            node["additional_data"]["qa_pairs"] = qa_pairs
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
            
            for i, subnode in enumerate(subcollections):
                if isinstance(subnode, dict):
                    sub_start = start_percent + (i * sub_range)
                    sub_end = sub_start + sub_range
                    
                    # Rekursiver Aufruf für Untersammlung
                    current = process_node_qa(
                        client=client,
                        node=subnode,
                        metadata=metadata,
                        progress_bar=progress_bar,
                        progress_text=progress_text,
                        current=current,
                        total=total,
                        start_percent=sub_start,
                        end_percent=sub_end,
                        num_questions=num_questions,
                        include_compendium=include_compendium,
                        include_entities=include_entities
                    )
                else:
                    st.warning(f"Überspringe ungültigen Unterknoten in '{node['title']}'")
    
    return current

if __name__ == "__main__":
    main()
