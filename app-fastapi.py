import os
import json
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, ValidationError, Field
from openai import OpenAI, RateLimitError, APIError
from dotenv import load_dotenv
import backoff
from fastapi import FastAPI, HTTPException

# ------------------------------------------------------------------------------
# 1) Einlesen von Umgebungsvariablen (OPENAI_API_KEY)
# ------------------------------------------------------------------------------
load_dotenv()

def get_openai_key():
    """Liest den OpenAI-API-Key aus den Umgebungsvariablen."""
    return os.getenv("OPENAI_API_KEY", "")

# ------------------------------------------------------------------------------
# 2) Pydantic-Modelle (Properties, Collection, TopicTree, TopicTreeRequest)
# ------------------------------------------------------------------------------
class Properties(BaseModel):
    """
    Properties-Objekt, das Metadaten wie Titel, Description, Keywords etc. speichert.
    Alle Listenfelder werden defaultmäßig gefüllt, um Probleme zu vermeiden.
    """
    ccm_collectionshorttitle: List[str] = Field(default_factory=lambda: [""])
    ccm_taxonid: List[str] = Field(default_factory=lambda: ["http://w3id.org/openeduhub/vocabs/discipline/460"])
    cm_title: List[str]
    ccm_educationalintendedenduserrole: List[str] = Field(
        default_factory=lambda: ["http://w3id.org/openeduhub/vocabs/intendedEndUserRole/teacher"]
    )
    ccm_educationalcontext: List[str] = Field(
        default_factory=lambda: ["http://w3id.org/openeduhub/vocabs/educationalContext/sekundarstufe_1"]
    )
    cm_description: List[str] = Field(alias="description")
    cclom_general_keyword: List[str] = Field(alias="keywords")

    class Config:
        # Sorgt dafür, dass Aliase automatisch befüllt werden
        populate_by_name = True
        alias_generator = lambda s: s.replace("_", ":")

    def to_dict(self) -> dict:
        """
        Gibt die Properties in einem Dictionary-Format zurück,
        sodass sie später leicht in das JSON integriert werden können.
        """
        return {
            "collectionshorttitle": self.ccm_collectionshorttitle,
            "taxonid": self.ccm_taxonid,
            "title": self.cm_title,
            "educationalintendedenduserrole": self.ccm_educationalintendedenduserrole,
            "educationalcontext": self.ccm_educationalcontext,
            "description": self.cm_description,
            "keywords": self.cclom_general_keyword
        }

class Collection(BaseModel):
    """
    Repräsentiert einen Knoten im Themenbaum mit Titel, Kurztitel,
    Properties und möglichen Unterknoten (subcollections).
    """
    title: str
    shorttitle: str
    properties: Properties
    subcollections: Optional[List['Collection']] = Field(default_factory=list)

    def to_dict(self) -> dict:
        """
        Konvertiert das Collection-Objekt rekursiv in ein Dictionary, 
        das alle Subcollections enthält.
        """
        result = {
            "title": self.title,
            "shorttitle": self.shorttitle,
            "properties": self.properties.to_dict()
        }
        if self.subcollections:
            result["subcollections"] = [sub.to_dict() for sub in self.subcollections]
        return result

# Erlaubt, dass das Collection-Modell sich selbst referenziert (subcollections)
Collection.model_rebuild()

class TopicTree(BaseModel):
    """
    Der komplette Themenbaum mit Metadaten und einer Liste von Collections.
    """
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
        """
        Konvertiert den gesamten Themenbaum (inkl. Metadaten und Collections) in ein Dictionary.
        """
        return {
            "metadata": self.metadata,
            "collection": [c.to_dict() for c in self.collection]
        }

class TopicTreeRequest(BaseModel):
    """
    Request-Modell für die Generierung eines Themenbaums.
    Hierüber kommen Parameter wie Thema, Anzahl an Hauptthemen und gewünschtes Sprachmodell.
    """
    theme: str = Field(
        ...,
        description="Das Hauptthema des Themenbaums",
        example="Physik in Anlehnung an die Lehrpläne der Sekundarstufe 2"
    )
    num_main_topics: int = Field(
        5,
        ge=1,
        le=20,
        description="Anzahl der zu generierenden Hauptthemen",
        example=5
    )
    num_subtopics: int = Field(
        3,
        ge=1,
        le=20,
        description="Anzahl der Unterthemen pro Hauptthema",
        example=3
    )
    num_curriculum_topics: int = Field(
        2,
        ge=1,
        le=20,
        description="Anzahl der Lehrplanthemen pro Unterthema",
        example=2
    )
    include_general_topic: bool = Field(
        False,
        description="Wenn True, wird 'Allgemeines' als erstes Hauptthema eingefügt",
        example=True
    )
    include_methodology_topic: bool = Field(
        False,
        description="Wenn True, wird 'Methodik und Didaktik' als letztes Hauptthema eingefügt",
        example=True
    )
    discipline: str = Field(
        "Physik",
        description="Der Fachbereich für den Themenbaum. Mögliche Werte sind in der Dokumentation aufgeführt.",
        example="Physik"
    )
    educational_context: str = Field(
        "Sekundarstufe II",
        description="Die Bildungsstufe für den Themenbaum. Mögliche Werte sind in der Dokumentation aufgeführt.",
        example="Sekundarstufe II"
    )
    model: str = Field(
        "gpt-4o-mini",
        description="Das zu verwendende OpenAI Sprachmodell",
        example="gpt-4o-mini"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "theme": "Physik in Anlehnung an die Lehrpläne der Sekundarstufe 2",
                "num_main_topics": 5,
                "num_subtopics": 3,
                "num_curriculum_topics": 2,
                "include_general_topic": True,
                "include_methodology_topic": True,
                "discipline": "Physik",
                "educational_context": "Sekundarstufe II",
                "model": "gpt-4o-mini"
            }
        }

# ------------------------------------------------------------------------------
# 3) Mappings für Fachbereiche, Bildungsstufen, etc.
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# 4) Konsolidierte Allgemeine Formatierungsregeln (Base Instructions)
# ------------------------------------------------------------------------------
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
    "   - Keine doppelten Titel"
)

# ------------------------------------------------------------------------------
# 5) Prompt-Templates (Mehrschritt-Generierung)
# ------------------------------------------------------------------------------
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
    "description": "Ausführliche Beschreibung des Themas",
    "keywords": ["Schlagwort1", "Schlagwort2", "Schlagwort3"]
  }}
]

WICHTIG: 
- Die "description" muss eine ausführliche Beschreibung des Themas enthalten
- Die "keywords" Liste muss mindestens 2-3 relevante Schlagworte enthalten
- Keine leeren Felder zurückgeben
"""

SUB_PROMPT_TEMPLATE = """\
Erstelle eine Liste von {num_sub} Unterthemen für das Hauptthema "{main_theme}"
im Kontext "{themenbaumthema}"{discipline_info}{context_info}.

Keine Code-Fences, kein Markdown, nur reines JSON-Array.

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

# ------------------------------------------------------------------------------
# 6) Hilfsfunktionen
# ------------------------------------------------------------------------------
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
    """
    Erstellt ein Properties-Objekt mit den gegebenen Werten.
    Hier werden die Standardwerte für ccm_taxonid und ccm_educationalcontext
    mit den in den Mappings hinterlegten URIs überschrieben (falls angegeben).
    """
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
    """
    Schickt die Prompt-Anfrage an das angegebene OpenAI-Modell
    und parst das zurückgegebene reine JSON-Array in eine Liste von Collection-Objekten.
    """
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
            raise Exception("Antwort vom Modell ist leer.")

        # Entfernt mögliche Triple-Backticks oder JSON-Syntax, die stören könnten
        raw = content.strip().strip("```").strip("```json").strip()
        print(f"Raw response: {raw}")  # Debug-Ausgabe
        data = json.loads(raw)

        # Falls nur ein Dict zurückkam, in eine Liste packen
        if not isinstance(data, list):
            data = [data]

        results = []
        for item in data:
            title = item.get("title", "")
            shorttitle = item.get("shorttitle", "")
            desc = item.get("description", "")
            keywords = item.get("keywords", [])

            # Falls das Modell aus irgendeinem Grund leere Werte geliefert hat
            if not desc:
                desc = f"Beschreibung für {title}"
            if not keywords:
                keywords = [title.lower()]

            # Bau das Properties-Objekt
            prop = Properties(
                ccm_collectionshorttitle=[shorttitle],
                ccm_taxonid=["http://w3id.org/openeduhub/vocabs/discipline/460"],
                cm_title=[title],
                ccm_educationalintendedenduserrole=["http://w3id.org/openeduhub/vocabs/intendedEndUserRole/teacher"],
                ccm_educationalcontext=["http://w3id.org/openeduhub/vocabs/educationalContext/sekundarstufe_2"],
                cm_description=[desc],  
                cclom_general_keyword=keywords  
            )

            # Erstelle das Collection-Objekt
            c = Collection(
                title=title,
                shorttitle=shorttitle,
                properties=prop,
                subcollections=[]
            )
            results.append(c)

        return results
    except json.JSONDecodeError as jde:
        print(f"JSON Decode Error: {jde}")  # Debug-Ausgabe
        raise Exception(f"JSON Decode Error: {jde}")
    except ValidationError as ve:
        print(f"Validation Error: {ve}")  # Debug-Ausgabe
        raise Exception(f"Strukturfehler: {ve}")
    except Exception as e:
        print(f"General Error: {e}")  # Debug-Ausgabe
        raise Exception(f"Fehler bei der Anfrage: {e}")

# ------------------------------------------------------------------------------
# 7) FastAPI App
# ------------------------------------------------------------------------------
app = FastAPI(
    title="Themenbaum Generator API",
    description="""
    ## Themenbaum Generator API

    Diese API ermöglicht die automatische Generierung von strukturierten Themenbäumen für Bildungsinhalte.
    
    ### Hauptfunktionen
    
    - **Themenbaumgenerierung**: Erstellt hierarchisch strukturierte Themenbäume mit Haupt-, Unter- und Lehrplanthemen
    - **Bildungskontext**: Berücksichtigt spezifische Fachbereiche und Bildungsstufen
    - **Metadaten**: Generiert standardisierte Metadaten für jeden Knoten im Themenbaum
    
    ### Verwendung
    
    1. Senden Sie eine POST-Anfrage an den `/generate-topic-tree` Endpunkt
    2. Definieren Sie die gewünschten Parameter wie Thema, Anzahl der Themen und Bildungskontext
    3. Erhalten Sie einen strukturierten Themenbaum im JSON-Format
    
    ### Authentifizierung
    
    Die API verwendet einen OpenAI API-Schlüssel, der über die Umgebungsvariable `OPENAI_API_KEY` bereitgestellt werden muss.
    """,
    version="1.0.0",
    contact={
        "name": "Themenbaum Generator Support",
        "email": "support@example.com"
    },
    license_info={
        "name": "Proprietär",
        "url": "https://example.com/license"
    }
)

@app.post(
    "/generate-topic-tree",
    response_model=dict,
    summary="Generiere einen Themenbaum",
    description="""
    Generiert einen strukturierten Themenbaum basierend auf den übergebenen Parametern.
    
    Der Themenbaum wird in folgender Hierarchie erstellt:
    1. Hauptthemen (z.B. "Mechanik", "Thermodynamik")
    2. Unterthemen (z.B. "Kinematik", "Dynamik")
    3. Lehrplanthemen (z.B. "Gleichförmige Bewegung", "Newtonsche Gesetze")
    
    Jeder Knoten im Themenbaum enthält:
    - Titel und Kurztitel
    - Beschreibung
    - Schlagworte (Keywords)
    - Standardisierte Metadaten (Properties)
    
    Beispielanfrage:
    ```json
    {
        "theme": "Physik in Anlehnung an die Lehrpläne der Sekundarstufe 2",
        "num_main_topics": 5,
        "num_subtopics": 3,
        "num_curriculum_topics": 2,
        "include_general_topic": true,
        "include_methodology_topic": true,
        "discipline": "Physik",
        "educational_context": "Sekundarstufe II",
        "model": "gpt-4o-mini"
    }
    ```
    """,
    responses={
        200: {
            "description": "Erfolgreich generierter Themenbaum",
            "content": {
                "application/json": {
                    "example": {
                        "metadata": {
                            "title": "Physik in Anlehnung an die Lehrpläne der Sekundarstufe 2",
                            "description": "Themenbaum für Physik in der Sekundarstufe II",
                            "created_at": "2025-02-05T11:28:40+01:00",
                            "version": "1.0",
                            "author": "Themenbaum Generator"
                        },
                        "collection": [
                            {
                                "title": "Allgemeines",
                                "shorttitle": "Allg",
                                "properties": {},
                                "subcollections": []
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "description": "Interner Serverfehler",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "OpenAI API Key nicht gefunden"
                    }
                }
            }
        }
    }
)
async def generate_topic_tree(request: TopicTreeRequest):
    """
    Generiert einen strukturierten Themenbaum basierend auf den Eingabeparametern.
    """
    # 1) OpenAI-Key holen
    openai_key = get_openai_key()
    if not openai_key:
        raise HTTPException(status_code=500, detail="OpenAI API Key nicht gefunden")

    try:
        client = OpenAI(api_key=openai_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI-Init-Fehler: {str(e)}")

    # 2) URIs aus den Mappings
    discipline_uri = DISCIPLINE_MAPPING.get(request.discipline, "")
    educational_context_uri = EDUCATIONAL_CONTEXT_MAPPING.get(request.educational_context, "")

    # 3) Strings für Prompt-Infos
    discipline_info = f" im Fach {request.discipline}" if request.discipline != "Keine Vorgabe" else ""
    context_info = f" für die {request.educational_context}" if request.educational_context != "Keine Vorgabe" else ""

    try:
        # 4) Spezialanweisungen für Hauptthemen (z.B. Allgemeines, Methodik etc.)
        special_instructions = []
        if request.include_general_topic:
            special_instructions.append("1) Hauptthema 'Allgemeines' an erster Stelle")
        if request.include_methodology_topic:
            special_instructions.append("2) Hauptthema 'Methodik und Didaktik' an letzter Stelle")
        special_instructions = "\n".join(special_instructions) if special_instructions else "Keine besonderen Anweisungen."

        # 5) Hauptthemen generieren
        main_topics = generate_structured_text(
            client=client,
            prompt=MAIN_PROMPT_TEMPLATE.format(
                themenbaumthema=request.theme,
                num_main=request.num_main_topics,
                discipline_info=discipline_info,
                context_info=context_info,
                existing_titles="",
                special_instructions=special_instructions
            ),
            model=request.model
        )

        if not main_topics:
            raise HTTPException(status_code=500, detail="Fehler bei der Generierung der Hauptthemen")

        # 6) Für jedes Hauptthema die Unterthemen generieren
        for main_topic in main_topics:
            sub_topics = generate_structured_text(
                client=client,
                prompt=SUB_PROMPT_TEMPLATE.format(
                    themenbaumthema=request.theme,
                    main_theme=main_topic.title,
                    num_sub=request.num_subtopics,
                    discipline_info=discipline_info,
                    context_info=context_info
                ),
                model=request.model
            )

            if not sub_topics:
                continue

            main_topic.subcollections = sub_topics

            # 7) Für jedes Unterthema die Lehrplanthemen generieren
            for sub_topic in sub_topics:
                lp_topics = generate_structured_text(
                    client=client,
                    prompt=LP_PROMPT_TEMPLATE.format(
                        themenbaumthema=request.theme,
                        main_theme=main_topic.title,
                        sub_theme=sub_topic.title,
                        num_lp=request.num_curriculum_topics,
                        discipline_info=discipline_info,
                        context_info=context_info
                    ),
                    model=request.model
                )

                if not lp_topics:
                    continue

                sub_topic.subcollections = lp_topics

        # 8) Properties für alle Knoten nochmal updaten mit den richtigen URIs
        #    Statt auf .description bzw. .keywords am Collection-Objekt zuzugreifen,
        #    holen wir hier die Werte direkt aus dem bestehenden Properties-Objekt.
        for main_topic in main_topics:
            main_topic.properties = create_properties(
                title=main_topic.title,
                shorttitle=main_topic.shorttitle,
                description=main_topic.properties.cm_description[0] if main_topic.properties.cm_description else "",
                keywords=main_topic.properties.cclom_general_keyword if main_topic.properties.cclom_general_keyword else [],
                discipline_uri=discipline_uri,
                educational_context_uri=educational_context_uri
            )

            for sub_topic in main_topic.subcollections:
                sub_topic.properties = create_properties(
                    title=sub_topic.title,
                    shorttitle=sub_topic.shorttitle,
                    description=sub_topic.properties.cm_description[0] if sub_topic.properties.cm_description else "",
                    keywords=sub_topic.properties.cclom_general_keyword if sub_topic.properties.cclom_general_keyword else [],
                    discipline_uri=discipline_uri,
                    educational_context_uri=educational_context_uri
                )

                for lp_topic in sub_topic.subcollections:
                    lp_topic.properties = create_properties(
                        title=lp_topic.title,
                        shorttitle=lp_topic.shorttitle,
                        description=lp_topic.properties.cm_description[0] if lp_topic.properties.cm_description else "",
                        keywords=lp_topic.properties.cclom_general_keyword if lp_topic.properties.cclom_general_keyword else [],
                        discipline_uri=discipline_uri,
                        educational_context_uri=educational_context_uri
                    )

        # 9) Finale Daten strukturieren (Metadaten + Collection-Liste)
        final_data = {
            "metadata": {
                "title": request.theme,
                "description": f"Themenbaum für {request.theme}",
                "target_audience": "Lehrkräfte",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "author": "Themenbaum Generator"
            },
            "collection": [topic.to_dict() for topic in main_topics]
        }

        # 10) Erfolg: gebe JSON zurück
        return final_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei der Generierung: {str(e)}")

# Falls du lokal starten willst, kannst du so die App launchen:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
