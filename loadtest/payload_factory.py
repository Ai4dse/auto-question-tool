import random
import string
from typing import Any


SQL_PREVIEW_STATEMENTS = [
    "SELECT 1 AS x",
    "SELECT Name FROM city LIMIT 5",
    "SELECT COUNT(*) AS c FROM country",
    "SELECT DISTINCT Continent FROM country",
]

RELALG_STATEMENTS = [
    r"\proj{Studierende.MatrNr}(Studierende)",
    r"\sel{Studierende.Semester > 3}(Studierende)",
    r"hoeren \join{hoeren.MatrNr = Studierende.MatrNr}(Studierende)",
]

GENERIC_TEXT_ANSWERS = [
    "42",
    "test",
    "answer",
    "A",
    "B",
    "SELECT 1",
    "a*b",
]


def random_seed() -> int:
    return random.randint(1, 999_999)


def random_difficulty(options: list[str] | None = None) -> str:
    opts = options or ["easy", "medium", "hard"]
    filtered = [str(o) for o in opts if str(o)]
    return random.choice(filtered or ["easy"])


def random_mode(options: list[str] | None = None) -> str:
    opts = options or ["steps", "exam"]
    filtered = [str(o) for o in opts if str(o)]
    return random.choice(filtered or ["steps"])


def preview_payload_for_type(type_name: str) -> dict[str, Any]:
    if type_name == "sql_query":
        return {"statement": random.choice(SQL_PREVIEW_STATEMENTS)}
    if type_name == "relational_algebra":
        return {"statement": random.choice(RELALG_STATEMENTS)}
    return {"statement": ""}


def evaluate_payload_for_type(type_name: str, layout: dict[str, Any] | None = None, attempt: int = 1) -> dict[str, Any]:
    if type_name == "sql_query":
        return {"0": random.choice(SQL_PREVIEW_STATEMENTS)}
    if type_name == "relational_algebra":
        return {"0": random.choice(RELALG_STATEMENTS)}
    if type_name == "regex":
        return {"0": r"^[A-Za-z0-9_]+$"}
    if type_name == "xpath_xquery":
        return {"0": "//book/title"}

    ids = extract_input_ids(layout or {})
    if not ids:
        return {
            "0": f"attempt_{attempt}",
            "1": random.choice(GENERIC_TEXT_ANSWERS),
            "answer": random.choice(GENERIC_TEXT_ANSWERS),
        }

    payload: dict[str, Any] = {}
    for idx, field_id in enumerate(ids[:8]):
        payload[field_id] = _value_for_id(field_id, idx, attempt)
    return payload


def extract_input_ids(layout: dict[str, Any]) -> list[str]:
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            node_id = node.get("id")
            if node_id is not None and isinstance(node_id, (str, int, float)):
                found.append(str(node_id))
            for value in node.values():
                walk(value)
            return

        if isinstance(node, list):
            for item in node:
                walk(item)

    walk(layout)

    deduped: list[str] = []
    seen: set[str] = set()
    for fid in found:
        if fid in seen:
            continue
        seen.add(fid)
        deduped.append(fid)
    return deduped


def _value_for_id(field_id: str, index: int, attempt: int) -> Any:
    lower = field_id.lower()
    if "check" in lower or "bool" in lower:
        return bool((index + attempt) % 2)
    if "seed" in lower:
        return random_seed()
    if "count" in lower or "num" in lower:
        return str(random.randint(1, 20))
    if "prob" in lower:
        return str(round(random.uniform(0.1, 1.0), 2))
    if "json" in lower or "builder" in lower:
        return "{}"
    if field_id.isdigit():
        if field_id == "0":
            return f"attempt_{attempt}_{random.choice(GENERIC_TEXT_ANSWERS)}"
        return random.choice(GENERIC_TEXT_ANSWERS)

    suffix = "".join(random.choices(string.ascii_lowercase, k=4))
    return f"{field_id}_{attempt}_{suffix}"
