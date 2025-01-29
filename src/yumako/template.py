import re as __re


def replace(
    text: str, mapping: dict, strict_on_unresolved_vars: bool = True, strict_on_unused_var: bool = False
) -> str:
    unused_vars = set(mapping.keys())
    for k, v in mapping.items():
        new_text = text.replace("{{" + k + "}}", str(v))
        if new_text != text:
            text = new_text
            unused_vars.remove(k)

    if strict_on_unresolved_vars:
        unresolved_vars = __re.findall(r"\{\{([^}]+)\}\}", text)
        if unresolved_vars:
            raise Exception(f"Strict mode: template variables unresolved: {unresolved_vars}")

    if strict_on_unused_var:
        if unused_vars:
            raise Exception(f"Strict mode: var specified but not in template: {unused_vars}")

    return text
