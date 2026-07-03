import json


def _int_or_default(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _children(node):
    if not isinstance(node, dict):
        return []
    if isinstance(node.get("children"), list):
        return node["children"]
    # Accept the common typo defensively, but export/use "children" in the frontend.
    if isinstance(node.get("childreen"), list):
        return node["childreen"]
    return []


def normalize_fp_tree(node, *, is_root=True):
    """Normalize frontend tree payload to {id, name, count, children}."""
    if not isinstance(node, dict):
        node = {}

    name = "root" if is_root else str(node.get("name") or node.get("label") or "").strip()
    count_default = 0 if is_root else 1

    return {
        "id": str(node.get("id") or ("root" if is_root else "")),
        "name": name,
        "count": _int_or_default(node.get("count", node.get("value")), count_default),
        "children": [normalize_fp_tree(child, is_root=False) for child in _children(node)],
    }


def _set_root_count_from_children(tree):
    """Set root count to the sum of its direct child counts.

    In an FP-tree, the root count is not a normal item support. For this
    exercise component, the root count is evaluated as the total count of
    all branches starting at the root. This is the sum of the immediate
    child-node counts.
    """
    if not isinstance(tree, dict):
        return tree
    children = tree.get("children") if isinstance(tree.get("children"), list) else []
    tree["count"] = sum(_int_or_default(child.get("count"), 0) for child in children if isinstance(child, dict))
    return tree


def tree_from_path_count_rows(rows):
    """Build expected tree from rows like {path: ('A','B'), count: 2}."""
    root = {"id": "root", "name": "root", "count": 0, "children": []}

    for row in rows or []:
        raw_path = row.get("path", [])
        if isinstance(raw_path, str):
            path = tuple(part.strip() for part in raw_path.split(",") if part.strip() and part.strip() != "-")
        else:
            path = tuple(raw_path or [])

        if not path:
            continue

        count = _int_or_default(row.get("count"), 0)
        current = root
        for index, item in enumerate(path):
            child = next((c for c in current["children"] if c["name"] == item), None)
            if child is None:
                child = {"id": "", "name": item, "count": 0, "children": []}
                current["children"].append(child)
            if index == len(path) - 1:
                child["count"] = count
            current = child

    return _set_root_count_from_children(root)


def parse_fp_tree_payload(raw):
    """Accept new nested tree payload and old {rows:[...]} payload."""
    if raw is None:
        return normalize_fp_tree({"id": "root", "name": "root", "count": 0, "children": []})

    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return normalize_fp_tree({"id": "root", "name": "root", "count": 0, "children": []})
        data = json.loads(raw)
    else:
        data = raw

    if isinstance(data, dict) and isinstance(data.get("tree"), dict):
        return normalize_fp_tree(data["tree"])

    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return normalize_fp_tree(tree_from_path_count_rows(data["rows"]))

    return normalize_fp_tree(data)


def evaluate_fp_tree(actual_tree, expected_tree):
    """
    Compare actual tree against expected tree.

    Matching is done by child name under the same parent. This fits FP-trees because
    a parent has at most one child with a given item name after path compression.
    """
    node_results = {}
    missing = []
    extra = []

    def mark_actual(actual, *, correct, name_correct, count_correct, expected_name=None,
                    expected_count=None, expected_path=None, message=None):
        node_id = actual.get("id") or expected_path or actual.get("name") or ""
        if not node_id:
            return
        node_results[node_id] = {
            "correct": bool(correct),
            "name_correct": bool(name_correct),
            "count_correct": bool(count_correct),
            "expected_name": expected_name,
            "expected_count": expected_count,
            "expected_path": expected_path,
            "message": message,
        }

    def walk(actual, expected, path):
        ok = True

        # Root name is fixed, but the root count is now graded as well.
        is_root = path == []
        name_correct = is_root or actual["name"] == expected["name"]
        count_correct = actual["count"] == expected["count"]
        current_path = ", ".join(path) if path else "root"

        mark_actual(
            actual,
            correct=name_correct and count_correct,
            name_correct=name_correct,
            count_correct=count_correct,
            expected_name=expected["name"],
            expected_count=expected["count"],
            expected_path=current_path,
        )

        if not name_correct or not count_correct:
            ok = False

        expected_children_by_name = {child["name"]: child for child in expected["children"]}
        seen_child_names = set()

        for actual_child in actual["children"]:
            child_name = actual_child["name"]
            child_path = path + [child_name]

            if child_name in seen_child_names:
                mark_actual(
                    actual_child,
                    correct=False,
                    name_correct=False,
                    count_correct=False,
                    expected_name=None,
                    expected_count=None,
                    expected_path=", ".join(child_path),
                    message="Duplicate child item under the same parent.",
                )
                extra.append({
                    "path": ", ".join(child_path),
                    "count": actual_child["count"],
                    "message": "duplicate child item",
                })
                ok = False
                continue

            expected_child = expected_children_by_name.get(child_name)

            if expected_child is None:
                mark_actual(
                    actual_child,
                    correct=False,
                    name_correct=False,
                    count_correct=False,
                    expected_name=None,
                    expected_count=None,
                    expected_path=", ".join(child_path),
                    message="Extra node or wrong branch.",
                )
                extra.append({"path": ", ".join(child_path), "count": actual_child["count"]})
                ok = False
                continue

            seen_child_names.add(child_name)
            if not walk(actual_child, expected_child, child_path):
                ok = False

        for expected_child in expected["children"]:
            if expected_child["name"] in seen_child_names:
                continue
            missing_path = path + [expected_child["name"]]
            missing.append({
                "path": ", ".join(missing_path),
                "count": expected_child["count"],
            })
            ok = False

        return ok

    correct = walk(actual_tree, expected_tree, [])
    if missing or extra:
        correct = False

    return {
        "correct": correct,
        "node_results": node_results,
        "missing": missing,
        "extra": extra,
        "expected_tree": expected_tree,
    }
