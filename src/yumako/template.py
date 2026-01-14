import re as __re
from typing import Any

__all__ = ["replace"]


def replace(
    text: str, mapping: dict[str, Any], raise_on_unresolved_vars: bool = True, raise_on_unused_vars: bool = False
) -> str:
    # Validate paired braces
    open_count = text.count("{{")
    close_count = text.count("}}")
    if open_count != close_count:
        raise ValueError(f"Mismatched braces: found {open_count} '{{{{' and {close_count} '}}}}' in template")

    unused_vars = set(mapping.keys())
    for k, v in mapping.items():
        new_text = text.replace("{{" + k + "}}", str(v))
        if new_text != text:
            text = new_text
            unused_vars.remove(k)

    if raise_on_unresolved_vars:
        unresolved_vars = __re.findall(r"\{\{([^}]+)\}\}", text)
        if unresolved_vars:
            raise ValueError(f"Strict mode: template variables unresolved: {unresolved_vars}")

    if raise_on_unused_vars:
        if unused_vars:
            raise ValueError(f"Strict mode: var specified but not in template: {unused_vars}")

    return text
