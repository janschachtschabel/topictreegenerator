"""
Pydantic-Modelle für Datenstrukturen im Themenbaum Generator.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Properties(BaseModel):
    """
    Properties-Modell für Collections im Themenbaum.
    Enthält Metadaten und Eigenschaften einer Collection.
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
    cm_description: List[str]
    cclom_general_keyword: List[str] = Field(alias="cclom:general_keyword")

    class Config:
        populate_by_name = True
        alias_generator = lambda s: s.replace("_", ":")

    def to_dict(self) -> dict:
        """Konvertiert Properties in ein Dictionary."""
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
    """
    Collection-Modell für Themenbaum-Knoten.
    Repräsentiert einen Knoten im Themenbaum mit optionalen Untersammlungen.
    """
    title: str
    shorttitle: str
    properties: Properties
    subcollections: Optional[List['Collection']] = Field(default_factory=list)
    additional_data: dict = Field(default_factory=dict)  
    # Hier speichern wir Kompendiumstext, erweiterten Text, Entitäten etc.

    def to_dict(self) -> dict:
        """Konvertiert Collection in ein Dictionary."""
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

# Collection-Modell muss nach seiner Definition neu gebaut werden,
# da es sich auf sich selbst bezieht (rekursive Struktur)
Collection.model_rebuild()

class TopicTree(BaseModel):
    """
    TopicTree-Modell für den gesamten Themenbaum.
    Enthält Metadaten und eine Liste von Collections.
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
        """Konvertiert TopicTree in ein Dictionary."""
        return {
            "metadata": self.metadata,
            "collection": [c.to_dict() for c in self.collection]
        }

class QAPair(BaseModel):
    """Ein einzelnes Frage-Antwort-Paar."""
    question: str
    answer: str

    def to_dict(self) -> Dict[str, str]:
        """Konvertiert QAPair in ein Dictionary."""
        return {
            "question": self.question,
            "answer": self.answer
        }

class QACollection(BaseModel):
    """Eine Sammlung von Frage-Antwort-Paaren."""
    qa_pairs: List[QAPair]
    topic: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert QACollection in ein Dictionary."""
        return {
            "qa_pairs": [qa.to_dict() for qa in self.qa_pairs],
            "topic": self.topic,
            "metadata": self.metadata
        }
