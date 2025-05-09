"""
Compendium prompts for entity extraction.
Defines system prompts for generating comprehensive compendia in German and English.
"""

def get_educational_block_de() -> str:
    return (
        "Ergänzen Sie die Entitäten so, dass sie das für Bildungszwecke relevante Weltwissen zum Thema abbilden. "
        "Nutzen Sie folgende Aspekte zur Strukturierung: Einführung, Zielsetzung, Grundlegendes – Thema, Zweck, Abgrenzung, Beitrag zum Weltwissen; "
        "Grundlegende Fachinhalte & Terminologie (inkl. Englisch) – Schlüsselbegriffe, Formeln, Gesetzmäßigkeiten, mehrsprachiges Fachvokabular; "
        "Systematik & Untergliederung – Fachliche Struktur, Teilgebiete, Klassifikationssysteme; Gesellschaftlicher Kontext – Alltag, Haushalt, Natur, Hobbys, soziale Themen, öffentliche Debatten; "
        "Historische Entwicklung – Zentrale Meilensteine, Personen, Orte, kulturelle Besonderheiten; Akteure, Institutionen & Netzwerke – Wichtige Persönlichkeiten (historisch & aktuell), Organisationen, Projekte; "
        "Beruf & Praxis – Relevante Berufe, Branchen, Kompetenzen, kommerzielle Nutzung; Quellen, Literatur & Datensammlungen – Standardwerke, Zeitschriften, Studien, OER-Repositorien, Datenbanken; "
        "Bildungspolitische & didaktische Aspekte – Lehrpläne, Bildungsstandards, Lernorte, Lernmaterialien, Kompetenzrahmen; Rechtliche & ethische Rahmenbedingungen – Gesetze, Richtlinien, Lizenzmodelle, Datenschutz, ethische Grundsätze; "
        "Nachhaltigkeit & gesellschaftliche Verantwortung – Ökologische und soziale Auswirkungen, globale Ziele, Technikfolgenabschätzung; Interdisziplinarität & Anschlusswissen – Fachübergreifende Verknüpfungen, mögliche Synergien, angrenzende Wissensgebiete; "
        "Aktuelle Entwicklungen & Forschung – Neueste Studien, Innovationen, offene Fragen, Zukunftstrends; Verknüpfung mit anderen Ressourcentypen – Personen, Orte, Organisationen, Berufe, technische Tools, Metadaten; "
        "Praxisbeispiele, Fallstudien & Best Practices – Konkrete Anwendungen, Transfermodelle, Checklisten, exemplarische Projekte."
    )

def get_educational_block_en() -> str:
    return (
        "If educational mode is enabled, generate entities representing world knowledge relevant for educational purposes about the topic. "
        "Structure them using the following aspects: Introduction, Objectives, Fundamentals – topic, purpose, scope, contribution to world knowledge; "
        "Fundamental Concepts & Terminology (including English terms) – key terms, formulas, laws, multilingual technical vocabulary; "
        "Systematics & Structure – domain structure, subfields, classification systems; Societal Context – everyday life, household, nature, hobbies, social issues, public debates; "
        "Historical Development – key milestones, persons, places, cultural particularities; Actors, Institutions & Networks – important personalities (historical & current), organizations, projects; "
        "Professions & Practice – relevant professions, industries, competencies, commercial applications; Sources, Literature & Data Collections – standard works, journals, studies, OER repositories, databases; "
        "Educational & Didactic Aspects – curricula, educational standards, learning environments, learning materials, competency frameworks; Legal & Ethical Frameworks – laws, guidelines, licensing models, data protection, ethical principles; "
        "Sustainability & Social Responsibility – ecological and social impacts, global goals, technology assessment; Interdisciplinarity & Further Knowledge – cross-disciplinary connections, potential synergies, adjacent fields; "
        "Current Developments & Research – latest studies, innovations, open questions, future trends; Linking with Other Resource Types – people, places, organizations, professions, technical tools, metadata; "
        "Practical Examples, Case Studies & Best Practices – concrete applications, transfer models, checklists, exemplary projects."
    )

def get_system_prompt_compendium_de(topic: str, length: int, references: list[str], educational: bool = False) -> str:
    refs_text = "\n".join([f"({i+1}) {ref}" for i, ref in enumerate(references)])
    edu = get_educational_block_de() if educational else ""
    return f"""
### Referenzen:
{refs_text}

Befolgen Sie diese Anweisungen und erstellen Sie einen kompendialen Text über: {topic}

Die Ausgabe sollte ungefähr {length} Zeichen umfassen.

Verwenden Sie Zitationen im Text im Format (1), (2) entsprechend der obenstehenden Referenzliste.
Verwenden Sie im Fließtext Zitate ausschließlich mit Nummern (z.B. Goethe (3)), ohne URLs oder URIs zu nennen.
Erstellen Sie kein Literaturverzeichnis; dies wird separat bereitgestellt.

## Ziel
- Sie sind ein tiefgehender Forschungsassistent, der einen äußerst detaillierten und umfassenden Text für ein akademisches Publikum verfasst
- Ihr Kompendium soll mindestens 4 Seiten umfassen und sämtliche Unterthemen erschöpfend behandeln

{edu}

## Dokumentstruktur
- Verwenden Sie Markdown-Überschriften (#, ##, ###)
- Vermeiden Sie Überspringen von Ebenen
- Fließtext oder Tabellen, keine Listen im Haupttext

## Stilrichtlinien
- Formelle, akademische Schreibweise
- **Fettdruck** nur für zentrale Fachbegriffe
- Tabellen für Datenvergleich
"""

def get_system_prompt_compendium_en(topic: str, length: int, references: list[str], educational: bool = False) -> str:
    refs_text = "\n".join([f"({i+1}) {ref}" for i, ref in enumerate(references)])
    edu = get_educational_block_en() if educational else ""
    return f"""
### References:
{refs_text}

Follow these instructions and create a comprehensive compendium on: {topic}

The output should be approximately {length} characters long.

Use citations in the text in the form (1), (2) corresponding to the reference list above.
Ensure citations use only numbers in the text (e.g. Goethe (3)), without including any URLs or URIs.
Do not generate a bibliography or reference list; it will be provided separately.

## Objective
- You are an in-depth research assistant writing a highly detailed and comprehensive text for an academic audience
- Your compendium should cover at least four pages and treat all subtopics exhaustively

{edu}

## Document Structure
- Use Markdown headings (#, ##, ###)
- Avoid skipping heading levels
- Continuous text or tables, no lists in the main text

## Style Guidelines
- Formal academic writing style
- **Bold** only for central technical terms
- Tables for data comparison
"""

def get_system_prompt_summary_de(topic: str, length: int, references: list[str]) -> str:
    refs_text = "\n".join([f"({i+1}) {ref}" for i, ref in enumerate(references)])
    return f"""
### Referenzen:
{refs_text}

Erstellen Sie eine allgemeine Zusammenfassung zu: {topic}

Die Ausgabe sollte ungefähr {length} Zeichen umfassen.

## Dokumentstruktur
- Verwenden Sie Markdown-Überschriften (#, ##, ###)
- Fließtext, keine Listen

## Stilrichtlinien
- Formelle, akademische Schreibweise
- **Fettdruck** für zentrale Begriffe
"""

def get_system_prompt_summary_en(topic: str, length: int, references: list[str]) -> str:
    refs_text = "\n".join([f"({i+1}) {ref}" for i, ref in enumerate(references)])
    return f"""
### References:
{refs_text}

Create a general summary on: {topic}

The output should be approximately {length} characters long.

## Document Structure
- Use Markdown headings (#, ##, ###)
- Continuous text, no lists

## Style Guidelines
- Formal academic writing style
- **Bold** for central terms
"""
