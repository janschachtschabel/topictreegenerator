from entityextractor.prompts.extract_prompts import TYPE_RESTRICTION_TEMPLATE_EN, TYPE_RESTRICTION_TEMPLATE_DE


def apply_type_restrictions(system_prompt: str, allowed_entity_types: str, language: str) -> str:
    """
    Append a type restriction to the system prompt if allowed_entity_types is not 'auto'.
    """
    if allowed_entity_types and allowed_entity_types.lower() != "auto":
        types = [t.strip() for t in allowed_entity_types.split(",")]
        types_str = ", ".join(types)
        template = TYPE_RESTRICTION_TEMPLATE_EN if language.lower() == "en" else TYPE_RESTRICTION_TEMPLATE_DE
        system_prompt += template.format(entity_types=types_str)
    return system_prompt
