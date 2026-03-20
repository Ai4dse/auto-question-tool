import re

def normalize_list_string(value):
    """
    Normalize both scalar and list-like strings into a comparable form.

    Returns:
        - tuple for list-like values (sorted, normalized tokens)
        - string for scalar values (normalized)
    """
    if value is None:
        return ""

    s = str(value).strip()

    # Treat "-" as empty
    if s == "-" or s == "":
        return ""

    # Detect list-like values (only real delimiters, not spaces)
    if re.search(r"[,\|;]", s):
        parts = re.split(r"[,\|;\s]+", s)
        normalized = sorted(p.strip().lower() for p in parts if p.strip())
        return tuple(normalized)

    # Scalar fallback
    return s.lower()