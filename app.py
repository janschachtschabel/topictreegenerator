import os
import streamlit as st
import json
from openai import OpenAI
from openai import RateLimitError, APIError
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, Field, parse_obj_as
from typing import List, Optional
import backoff
from datetime import datetime

# Laden der Umgebungsvariablen aus einer .env-Datei (optional)
load_dotenv()

# Setze die Seitenkonfiguration
st.set_page_config(page_title="Themenbaum Generator", layout="wide")

# Funktion zum Laden des OpenAI API-Schlüssels aus den Umgebungsvariablen
def get_openai_key():
    return os.getenv('OPENAI_API_KEY', '')

# Pydantic-Modelle für Structured Outputs
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
        alias_generator = lambda string: string.replace("_", ":")

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
        if not self.subcollections:
            return {
                "title": self.title,
                "shorttitle": self.shorttitle,
                "properties": self.properties.to_dict()
            }
        else:
            return {
                "title": self.title,
                "shorttitle": self.shorttitle,
                "properties": self.properties.to_dict(),
                "subcollections": [sub.to_dict() for sub in self.subcollections]
            }

class TopicTree(BaseModel):
    collection: List[Collection]  # Liste der Hauptthemen
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
            "collection": [main_theme.to_dict() for main_theme in self.collection]
        }

# Aktualisieren der Referenzen für rekursive Modelle
Collection.update_forward_refs()

# Mappings für Fachbereiche und Bildungsstufen
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
    "Frühkindlich": "early_childhood",
    "Allgemeinbildend": "general",
    "Berufsbildend": "vocational",
    "Akademisch": "academic"
}

# Prompt Templates als Konstanten
MAIN_PROMPT_TEMPLATE = """Erstelle eine Liste von {num_main} Hauptthemen für einen Themenbaum zum Thema '{themenbaumthema}'{discipline_info}{context_info}{sector_info}. 

Beachte dabei folgende VERPFLICHTENDE Regeln:

1. TITEL-REGELN:
   - Verwende Langformen statt Abkürzungen (z.B. "Allgemeine Relativitätstheorie" statt "ART")
   - Nutze "vs." für Gegenüberstellungen (z.B. "Perfecto vs. Indefinido")
   - Verbinde verwandte Begriffe mit "und" (z.B. "Elektrizität und Magnetismus")
   - Vermeide Sonderzeichen (kein Kaufmanns-und, kein Schrägstrich)
   - Verwende Substantive (z.B. "Begrüßung und Verabschiedung")
   - Kennzeichne Homonyme mit runden Klammern (z.B. "Lösung (Mathematik)")
   - Vermeide Artikel und schreibe Adjektive klein

2. KURZTITEL-REGELN:
   - Maximal 20 Zeichen
   - Prägnant und eindeutig
   - Keine Sonderzeichen
   - Bevorzugt ein Hauptbegriff

3. BESCHREIBUNGS-REGELN:
   - Beginne mit präziser Definition des Themas
   - Erkläre die Relevanz im Bildungskontext
   - Beschreibe die wesentlichen Merkmale
   - Verwende maximal 5 prägnante Sätze
   - Nutze klare, zielgruppengerechte Sprache
   - Vermeide direkte Zielgruppeneinordnungen
   - Verwende aktive Formulierungen
   - Baue logisch auf: Definition → Relevanz → Merkmale → Anwendung

4. KATEGORISIERUNG:
Jede Sammlung MUSS einer dieser Kategorien entsprechen:
   a) Thema (Substantiv, für Lehrplanthemen)
   b) Kompetenz (Verb, für Fähigkeiten und Fertigkeiten)
   c) Vermittlung (für Didaktik/Methodik)
   d) Redaktionelle Sammlung (für spezielle Themen)

Formatiere die Antwort als JSON-Array mit genau diesem Format:
[
  {{
    "title": "Name des Hauptthemas",
    "shorttitle": "Kurzer, prägnanter Titel (max. 20 Zeichen)",
    "description": "Ausführliche Beschreibung des Hauptthemas",
    "keywords": ["Schlagwort1", "Schlagwort2"]
  }}
]"""

SUB_PROMPT_TEMPLATE = """Erstelle eine Liste von {num_sub} Unterthemen für das Hauptthema '{main_theme}' im Kontext von '{themenbaumthema}'{discipline_info}{context_info}{sector_info}. 

Beachte dabei folgende VERPFLICHTENDE Regeln:

1. TITEL-REGELN:
   - Verwende Langformen statt Abkürzungen (z.B. "Allgemeine Relativitätstheorie" statt "ART")
   - Nutze "vs." für Gegenüberstellungen (z.B. "Perfecto vs. Indefinido")
   - Verbinde verwandte Begriffe mit "und" (z.B. "Elektrizität und Magnetismus")
   - Vermeide Sonderzeichen (kein Kaufmanns-und, kein Schrägstrich)
   - Verwende Substantive (z.B. "Begrüßung und Verabschiedung")
   - Kennzeichne Homonyme mit runden Klammern (z.B. "Lösung (Mathematik)")
   - Vermeide Artikel und schreibe Adjektive klein

2. KURZTITEL-REGELN:
   - Maximal 20 Zeichen
   - Prägnant und eindeutig
   - Keine Sonderzeichen
   - Bevorzugt ein Hauptbegriff

3. BESCHREIBUNGS-REGELN:
   - Beginne mit präziser Definition des Themas
   - Erkläre die Relevanz im Bildungskontext
   - Beschreibe die wesentlichen Merkmale
   - Verwende maximal 5 prägnante Sätze
   - Nutze klare, zielgruppengerechte Sprache
   - Vermeide direkte Zielgruppeneinordnungen
   - Verwende aktive Formulierungen
   - Baue logisch auf: Definition → Relevanz → Merkmale → Anwendung

4. KATEGORISIERUNG:
Jede Sammlung MUSS einer dieser Kategorien entsprechen:
   a) Thema (Substantiv, für Lehrplanthemen)
   b) Kompetenz (Verb, für Fähigkeiten und Fertigkeiten)
   c) Vermittlung (für Didaktik/Methodik)
   d) Redaktionelle Sammlung (für spezielle Themen)

Formatiere die Antwort als JSON-Array mit genau diesem Format:
[
  {{
    "title": "Name des Unterthemas",
    "shorttitle": "Kurzer, prägnanter Titel (max. 20 Zeichen)",
    "description": "Ausführliche Beschreibung des Unterthemas",
    "keywords": ["Schlagwort1", "Schlagwort2"]
  }}
]"""

LP_PROMPT_TEMPLATE = """Erstelle eine Liste von {num_lp} Lehrplanthemen für das Unterthema '{sub_theme}' im Kontext von '{themenbaumthema}'{discipline_info}{context_info}{sector_info}. 

Beachte dabei folgende VERPFLICHTENDE Regeln:

1. TITEL-REGELN:
   - Verwende Langformen statt Abkürzungen (z.B. "Allgemeine Relativitätstheorie" statt "ART")
   - Nutze "vs." für Gegenüberstellungen (z.B. "Perfecto vs. Indefinido")
   - Verbinde verwandte Begriffe mit "und" (z.B. "Elektrizität und Magnetismus")
   - Vermeide Sonderzeichen (kein Kaufmanns-und, kein Schrägstrich)
   - Verwende Substantive (z.B. "Begrüßung und Verabschiedung")
   - Kennzeichne Homonyme mit runden Klammern (z.B. "Lösung (Mathematik)")
   - Vermeide Artikel und schreibe Adjektive klein

2. KURZTITEL-REGELN:
   - Maximal 20 Zeichen
   - Prägnant und eindeutig
   - Keine Sonderzeichen
   - Bevorzugt ein Hauptbegriff

3. BESCHREIBUNGS-REGELN:
   - Beginne mit präziser Definition des Themas
   - Erkläre die Relevanz im Bildungskontext
   - Beschreibe die wesentlichen Merkmale
   - Verwende maximal 5 prägnante Sätze
   - Nutze klare, zielgruppengerechte Sprache
   - Vermeide direkte Zielgruppeneinordnungen
   - Verwende aktive Formulierungen
   - Baue logisch auf: Definition → Relevanz → Merkmale → Anwendung

4. KATEGORISIERUNG:
Jede Sammlung MUSS einer dieser Kategorien entsprechen:
   a) Thema (Substantiv, für Lehrplanthemen)
   b) Kompetenz (Verb, für Fähigkeiten und Fertigkeiten)
   c) Vermittlung (für Didaktik/Methodik)
   d) Redaktionelle Sammlung (für spezielle Themen)

Formatiere die Antwort als JSON-Array mit genau diesem Format:
[
  {{
    "title": "Name des Lehrplanthemas",
    "shorttitle": "Kurzer, prägnanter Titel (max. 20 Zeichen)",
    "description": "Ausführliche Beschreibung mit Lernzielen",
    "keywords": ["Schlagwort1", "Schlagwort2"]
  }}
]"""

# Funktion zum Erstellen der Properties
def create_properties(title: str, shorttitle: str, description: str, keywords: List[str], discipline_uri: str = "", educational_context_uri: str = "") -> Properties:
    return Properties(
        ccm_collectionshorttitle=[shorttitle],
        ccm_taxonid=[discipline_uri] if discipline_uri else ["http://w3id.org/openeduhub/vocabs/discipline/460"],
        cm_title=[title],
        ccm_educationalintendedenduserrole=["http://w3id.org/openeduhub/vocabs/intendedEndUserRole/teacher"],
        ccm_educationalcontext=[educational_context_uri] if educational_context_uri else ["http://w3id.org/openeduhub/vocabs/educationalContext/sekundarstufe_1"],
        cm_description=[description],
        cclom_general_keyword=keywords
    )

# Funktion zum Anfragen der OpenAI API mit Structured Outputs
@backoff.on_exception(
    backoff.expo,
    (RateLimitError, APIError),
    max_tries=5,
    jitter=backoff.full_jitter
)
def generate_structured_text(client: OpenAI, prompt: str, model: str, schema):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": base_instructions},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.7,
        )
        # Extrahiere den Inhalt der Antwort
        content = response.choices[0].message.content.strip()

        if not content:
            st.error("Die Antwort von OpenAI ist leer.")
            return None

        try:
            # Versuche, den Inhalt als JSON zu laden
            data = json.loads(content)
            
            # Wenn data kein Array ist, packe es in eines
            if not isinstance(data, list):
                data = [data]
            
            # Konvertiere die Properties in das richtige Format
            for item in data:
                if "properties" in item:
                    props = item["properties"]
                    # Stelle sicher, dass alle erforderlichen Felder vorhanden sind
                    if "cm:title" not in props:
                        props["cm:title"] = [item.get("title", "")]
                    if "cm:description" not in props:
                        props["cm:description"] = [item.get("description", "")]
                    if "cclom:general_keyword" not in props:
                        props["cclom:general_keyword"] = item.get("keywords", [])
                else:
                    # Erstelle Properties wenn sie fehlen
                    item["properties"] = {
                        "cm:title": [item.get("title", "")],
                        "cm:description": [item.get("description", "")],
                        "cclom:general_keyword": item.get("keywords", []),
                        "ccm:collectionshorttitle": [""],
                        "ccm:taxonid": ["http://w3id.org/openeduhub/vocabs/discipline/460"],
                        "ccm:educationalintendedenduserrole": ["http://w3id.org/openeduhub/vocabs/intendedEndUserRole/teacher"],
                        "ccm:educationalcontext": ["http://w3id.org/openeduhub/vocabs/educationalContext/sekundarstufe_1"]
                    }
                
            # Parst die Daten mit Pydantic
            parsed_data = []
            for item in data:
                collection = Collection(
                    title=item["title"],
                    shorttitle=item["shorttitle"],
                    properties=create_properties(
                        title=item["title"],
                        shorttitle=item["shorttitle"],
                        description=item["description"],
                        keywords=item["keywords"],
                        discipline_uri=discipline_uri,
                        educational_context_uri=educational_context_uri
                    )
                )
                parsed_data.append(collection)
            return parsed_data
            
        except json.JSONDecodeError as jde:
            st.error(f"JSON Decode Error: {jde}")
            st.text(f"Rohdaten: {content}")
            return None
        except ValidationError as ve:
            st.error(f"Strukturierungsfehler: {ve}")
            st.text(f"Rohdaten: {content}")
            return None
            
    except Exception as e:
        st.error(f"Fehler bei der Anfrage an OpenAI: {e}")
        return None

# Allgemeine Anweisungen zur Verbesserung der Qualität für Bildung
base_instructions = (
    "Du bist ein hilfreicher KI-Assistent für Lehr- und Lernsituationen, der sachlich korrekte und verständliche Antworten gibt, "
    "um Lernenden und Lehrenden komplexe Themen näherzubringen. Deine Antworten sind relevant, aktuell und fachlich fundiert, "
    "basieren auf vertrauenswürdigen Quellen und enthalten keine falschen oder spekulativen Aussagen. Du passt deine Sprache an die Zielgruppe an, "
    "bleibst klar und fachlich präzise, um den Lernerfolg zu fördern.\n\n"
    "Du achtest darauf, dass deine Antworten rechtlich unbedenklich sind, insbesondere in Bezug auf Urheberrecht, Datenschutz, "
    "Persönlichkeitsrechte und Jugendschutz. Die Herkunft der Informationen wird bei Bedarf transparent gemacht. Du orientierst dich an anerkannten didaktischen Prinzipien, "
    "lieferst praxisorientierte Erklärungen und vermeidest unnötige Komplexität.\n\n"
    "Neutralität und Objektivität stehen im Fokus. Persönliche Meinungen oder parteiische Bewertungen sind ausgeschlossen. Deine Inhalte werden regelmäßig überprüft, "
    "um den höchsten Qualitätsstandards zu genügen, unter anderem durch den Einsatz von LLM-gestützter Analyse. Dein Ziel ist es, sachliche, aktuelle und rechtlich wie didaktisch einwandfreie Informationen bereitzustellen.\n\n"
    "Bitte antworte ausschließlich im JSON-Format ohne zusätzliche Erklärungen, Codeblöcke oder Text."
)

# Sidebar Einstellungen
with st.sidebar:
    st.header("Einstellungen")

    # LLM Einstellungen
    with st.expander("LLM Einstellungen", expanded=False):
        model = st.selectbox(
            "Sprachmodell",
            options=["gpt-4o-mini", "gpt-4o"],
            index=0  # "gpt-4o-mini" als Standard
        )
        # OpenAI Key wird automatisch aus den Umgebungsvariablen geladen und als Standardwert gesetzt
        default_openai_key = get_openai_key()
        openai_key = st.text_input(
            "OpenAI API Key",
            value=default_openai_key,
            type="password",
            placeholder="Geben Sie Ihren OpenAI API Key ein",
            help="Ihr OpenAI API Schlüssel wird verwendet, um die Themenbäume zu generieren. Sie können den Standardwert aus den Umgebungsvariablen überschreiben."
        )

    # Themenbaum Einstellungen
    with st.expander("Themenbaum Einstellungen", expanded=False):
        num_main = st.number_input("Anzahl Hauptthemen", min_value=1, max_value=20, value=5, step=1)
        num_sub = st.number_input("Anzahl Fachthemen pro Hauptthema", min_value=1, max_value=20, value=3, step=1)
        num_lehrplan = st.number_input("Anzahl Lehrplanthemen pro Fachthema", min_value=1, max_value=20, value=2, step=1)

    # Prompts bearbeiten
    with st.expander("Prompts bearbeiten", expanded=False):
        st.text_area(
            "Prompt für Hauptthemen",
            value=MAIN_PROMPT_TEMPLATE,
            height=150,
            disabled=True
        )

        st.text_area(
            "Prompt für Fachthemen",
            value=SUB_PROMPT_TEMPLATE,
            height=150,
            disabled=True
        )

        st.text_area(
            "Prompt für Lehrplanthemen",
            value=LP_PROMPT_TEMPLATE,
            height=150,
            disabled=True
        )

# Hauptbereich
st.title("Themenbaum Generator für Bildungsinhalte")

# Eingabefelder für das Themenbaumthema und die Zielgruppe
themenbaumthema = st.text_area(
    "Themenbaumthema",
    value="Stell Dir vor, Du bist ein Physiklehrer und sollst Lehrmaterialien für das Fach Physik in einer Systematik ordnen.",
    height=100
)

# Finde den Index für die Standardwerte
discipline_default_index = list(DISCIPLINE_MAPPING.keys()).index("Physik")
context_default_index = list(EDUCATIONAL_CONTEXT_MAPPING.keys()).index("Sekundarstufe II")
sector_default_index = list(EDUCATION_SECTOR_MAPPING.keys()).index("Allgemeinbildend")

selected_discipline = st.selectbox(
    "Fachbereich",
    options=list(DISCIPLINE_MAPPING.keys()),
    index=discipline_default_index
)
discipline_uri = DISCIPLINE_MAPPING[selected_discipline]

selected_context = st.selectbox(
    "Bildungsstufe",
    options=list(EDUCATIONAL_CONTEXT_MAPPING.keys()),
    index=context_default_index
)
educational_context_uri = EDUCATIONAL_CONTEXT_MAPPING[selected_context]

selected_sector = st.selectbox(
    "Bildungssektor",
    options=list(EDUCATION_SECTOR_MAPPING.keys()),
    index=sector_default_index
)
education_sector = EDUCATION_SECTOR_MAPPING[selected_sector]

# Button zur Generierung
if st.button("Themenbaum generieren"):
    if not openai_key:
        st.error("OpenAI API Key ist nicht verfügbar. Bitte geben Sie Ihren API-Schlüssel ein.")
    elif not themenbaumthema.strip():
        st.error("Bitte geben Sie ein Themenbaumthema ein.")
    else:
        # Fortschrittsbalken
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Prompt-Informationen basierend auf Auswahl
        discipline_info = f" im Fach {selected_discipline}" if selected_discipline != "Keine Vorgabe" else ""
        context_info = f" für die {selected_context}" if selected_context != "Keine Vorgabe" else ""
        sector_info = f" im {selected_sector.lower()}en Bildungssektor" if selected_sector != "Keine Vorgabe" else ""

        # Generiere Hauptthemen
        status_text.text("Generiere Hauptthemen...")
        main_prompt = MAIN_PROMPT_TEMPLATE.format(
            num_main=num_main,
            themenbaumthema=themenbaumthema,
            discipline_info=discipline_info,
            context_info=context_info,
            sector_info=sector_info
        )

        # Rest des Codes für die Generierung...
        # Instanziieren des OpenAI-Clients
        try:
            status_text.text("Initialisiere OpenAI Client...")
            client = OpenAI(api_key=openai_key)
            
            # Berechne Gesamtanzahl der zu generierenden Themen
            total_steps = 1  # Hauptthemen-Generation
            total_steps += num_main  # Für jedes Hauptthema Fachthemen
            total_steps += num_main * num_sub  # Für jedes Fachthema Lehrplanthemen
            steps_done = 0
            
            progress_bar.progress(0.0)
        except Exception as e:
            st.error(f"Fehler beim Initialisieren des OpenAI-Clients: {e}")
            st.stop()

        # Generiere Hauptthemen
        main_collections = generate_structured_text(client, main_prompt, model, List[Collection])
        if not main_collections:
            st.error("Fehler bei der Generierung der Hauptthemen")
            st.stop()
            
        steps_done += 1
        progress_bar.progress(steps_done / total_steps)

        # Generiere Fachthemen für jedes Hauptthema
        status_text.text("Generiere Fachthemen...")
        for main_collection in main_collections:
            sub_prompt = SUB_PROMPT_TEMPLATE.format(
                num_sub=num_sub,
                main_theme=main_collection.title,
                themenbaumthema=themenbaumthema,
                discipline_info=discipline_info,
                context_info=context_info,
                sector_info=sector_info
            )
            sub_collections = generate_structured_text(client, sub_prompt, model, List[Collection])
            if sub_collections:
                main_collection.subcollections = sub_collections
            steps_done += 1
            progress_bar.progress(steps_done / total_steps)
            status_text.text(f"Generiere Fachthemen für {main_collection.title}...")

        # Generiere Lehrplanthemen für jedes Fachthema
        for main_collection in main_collections:
            for sub_collection in main_collection.subcollections or []:
                status_text.text(f"Generiere Lehrplanthemen für {sub_collection.title}...")
                lehrplan_prompt = LP_PROMPT_TEMPLATE.format(
                    num_lp=num_lehrplan,
                    sub_theme=sub_collection.title,
                    themenbaumthema=themenbaumthema,
                    discipline_info=discipline_info,
                    context_info=context_info,
                    sector_info=sector_info
                )
                lehrplan_collections = generate_structured_text(client, lehrplan_prompt, model, List[Collection])
                if lehrplan_collections:
                    sub_collection.subcollections = lehrplan_collections
                steps_done += 1
                progress_bar.progress(steps_done / total_steps)

        progress_bar.progress(1.0)
        status_text.text("Themenbaum erfolgreich generiert!")

        # Aktualisiere die Properties aller Collections
        def update_collection_properties(collection: Collection):
            if not collection.properties.ccm_taxonid and discipline_uri:
                collection.properties.ccm_taxonid = [discipline_uri]
            if not collection.properties.ccm_educationalcontext and educational_context_uri:
                collection.properties.ccm_educationalcontext = [educational_context_uri]
            for subcoll in collection.subcollections:
                update_collection_properties(subcoll)

        # Update properties for all collections
        for collection in main_collections:
            update_collection_properties(collection)

        # Erstelle den Themenbaum
        topic_tree = TopicTree(
            collection=main_collections,
            metadata={
                "title": themenbaumthema,
                "description": f"Themenbaum für {themenbaumthema}",
                "target_audience": "Lehrkräfte und Bildungseinrichtungen",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "author": "Themenbaum Generator"
            }
        )
        
        # Konvertiere den Themenbaum in ein Dictionary
        themes_tree = topic_tree.to_dict()

        # Zeige den Themenbaum an
        st.json(themes_tree)

        # Option zum Herunterladen des JSON
        json_str = json.dumps(themes_tree, indent=4, ensure_ascii=False)
        st.download_button("JSON herunterladen", data=json_str, file_name="themenbaum.json", mime="application/json")

        # Option zur Bearbeitung des JSON
        st.subheader("JSON bearbeiten")
        edited_json = st.text_area("Bearbeite das JSON hier:", value=json_str, height=300)
        if st.button("JSON aktualisieren"):
            try:
                edited_tree = json.loads(edited_json)
                st.success("JSON erfolgreich aktualisiert.")
                st.json(edited_tree)
            except json.JSONDecodeError:
                st.error("Das JSON ist ungültig. Bitte korrigiere die Fehler.")
