import os
import re
import json
import pandas as pd
import ast

def load_schema(schema_folder: str, prefix_attributes: bool = True):
    schema_path = os.path.join(schema_folder, "schema.json")
    with open(schema_path, encoding="utf-8") as f:
        config = json.load(f)

    delimiter = config.get("delimiter", ";")
    relations_cfg = config["relations"]

    dataframes = {}

    for rel_name, rel_info in relations_cfg.items():
        filename = rel_info.get("filename", f"{rel_name}.csv")
        csv_path = os.path.join(schema_folder, filename)

        df = pd.read_csv(csv_path, sep=delimiter)

        if prefix_attributes:
            df.columns = [f"{rel_name}.{col}" for col in df.columns]

        dataframes[rel_name] = df

    return config, dataframes

def parse_predicate(predicate):
    expr = predicate.strip()
    expr = re.sub(r'\bAND\b', '&', expr, flags=re.IGNORECASE)
    expr = re.sub(r'\bOR\b',  r'|', expr, flags=re.IGNORECASE)
    expr = re.sub(r'\bNOT\b', r'~', expr, flags=re.IGNORECASE)

    #'=' zu '==' umwandeln
    expr = re.sub(r'(?<![<>=!])=(?!=)', '==', expr)
    return expr

def prepare_predicate(df, predicate):
    for col in sorted(df.columns, key=len, reverse=True): #col zu df['col']
        pattern = r'\b' + re.escape(col) + r'\b'
        predicate = re.sub(pattern, f'df[{col!r}]', predicate)
    return predicate

def rename_relation(df, new_name):
    new_name = str(new_name).strip()
    if not new_name:
        raise ValueError(
            "Der neue Relationsname darf nicht leer sein."
        )
    new_cols = {}
    for col in df.columns:
        if "." in col:
            _, attr = col.split(".", 1)    
            new_cols[col] = f"{new_name}.{attr}"
    return df.rename(columns=new_cols)

def rename_attribute(df, attribute, new_name):
    if attribute not in df.columns:
        raise ValueError(
            f'Das Attribut "{attribute}" existiert in der Relation nicht und kann daher nicht umbenannt werden.'
        )
    new_cols = {attribute: new_name}
    return df.rename(columns=new_cols)

def join(df1, df2, predicate):
    df = df1.merge(df2, how="cross")
    df = selection(df, predicate)
    return df

def selection(df, predicate):
    predicate = parse_predicate(predicate)
    predicate = prepare_predicate(df, predicate)
    try:
        mask = eval(predicate, {"df": df})
    except Exception as e:
        raise ValueError(
            f'Ungültiges Selektionsprädikat: "{predicate}". Bitte prüfen Sie die Schreibweise und die verwendeten Attribute.'
        ) from e

    if not isinstance(mask, pd.Series) or mask.dtype != bool:
        raise ValueError(
            "Das Selektionsprädikat muss einen booleschen Ausdruck ergeben."
        )

    return df[mask]

def projection(df, attributes):
    missing = [a for a in attributes if a not in df.columns]
    if missing:
        raise ValueError(
            f'Die folgenden Attribute existieren in dieser Relation nicht und können nicht projiziert werden: "{", ".join(missing)}"'
        )
    return df[attributes].drop_duplicates().copy()

def diff(df1, df2):
    a1 = [c.split('.',1)[1] for c in df1.columns] #columns without dots
    a2 = [c.split('.',1)[1] for c in df2.columns]

    if set(a1) != set(a2):
        raise ValueError("Die Relationen einer Differenz müssen dieselben Attribute besitzen.")

    c1 = df1.copy();  c1.columns = a1
    c2 = df2.copy();  c2.columns = a2
    c2 = c2[a1]

    d = c1.merge(c2.drop_duplicates(), how="left", indicator=True)
    out = d[d["_merge"] == "left_only"].drop(columns="_merge")

    out.columns = df1.columns #restore columns
    return out

def get_matching_close_paren(s):
    if not s or s[0] != '(':
        return None

    depth = 0
    for i, ch in enumerate(s):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return s[:i+1]

    return None

def get_matching_open_paren(s):
    balance = 0
    for i in range(len(s) - 1, -1, -1):
        if s[i] == ')':
            balance += 1
        elif s[i] == '(':
            balance -= 1
        if balance < 0: # stop when more '(' than ')' 
            return s[i+1:] # ( Vorlesungen --> returns Vorlesungen 
    return s

def parse_selection(statement):
    pattern = r'\\selection\{([^}]*)\}\('
    while True:
        matches = list(re.finditer(pattern, statement)) #replaces \selection{}() with selection(predicate, df) from right to left
        if not matches:
            break
        m = matches[-1] #begin with last match
        start, end = m.span()
        parentheses_block = get_matching_close_paren(statement[end-1:]) #returns parentheses block, e.g. \selection{...}( A (B)) --> ( A (B))
        if parentheses_block is None:
            raise ValueError("Fehler bei SELECTION: Die Klammern nach \\selection{...} sind nicht korrekt geschlossen.")
        predicate = m.group(1)
        replacement = f'selection({parentheses_block}, "{predicate}")'
        statement = statement[:start] + replacement + statement[end-1+len(parentheses_block):]
    return statement

def parse_projection(statement):
    pattern = r'\\projection\{([^}]*)\}\('
    while True:
        matches = list(re.finditer(pattern, statement))
        if not matches:
            break
        m = matches[-1] #begin with last match
        start, end = m.span()
        parentheses_block = get_matching_close_paren(statement[end-1:])
        if parentheses_block is None:
            raise ValueError("Fehler bei PROJECTION: Die Klammern nach \\projection{...} sind nicht korrekt geschlossen.")
        predicate = m.group(1)
        attrs = [f'{x.strip()}' for x in predicate.split(',')]
        replacement = f'projection({parentheses_block}, {attrs})'
        statement = statement[:start] + replacement + statement[end-1+len(parentheses_block):]
    return statement

def parse_relations(statement, relations):
    elements = "|".join(map(re.escape, relations))
    pattern = rf'\b({elements})\b(?!\.)'#searches for all occurences without a dot, i.e. Prof but not Prof.
    def repl(match):
        relation = match.group(1)
        return f"dfs['{relation}']"

    statement = re.sub(pattern, repl, statement)
    return statement

def parse_join(statement):
    pattern = r'\\join\{([^}]*)\}\('
    while True:
            matches = list(re.finditer(pattern, statement))
            if not matches:
                break
            m = matches[-1] #begin with last match
            start, end = m.span()
            left = get_matching_open_paren(statement[:start])
            right = get_matching_close_paren(statement[end-1:])
            if right is None:
                raise ValueError("Fehler bei JOIN: Die Klammern nach \\join{...} sind nicht korrekt geschlossen.")
            predicate = m.group(1)
            replacement = f'join({left}, {right}, "{predicate}")'
            statement = statement[:start - len(left)] + replacement + statement[end - 1 + len(right):]
    return statement

def parse_rename_relation(statement):
    pattern = r'\\_rename_relation\{([^}]*)\}\('
    while True:
        matches = list(re.finditer(pattern, statement))
        if not matches:
            break
        m = matches[-1] #begin with last match
        start, end = m.span()
        right = get_matching_close_paren(statement[end-1:])
        if right is None:
            raise ValueError("Fehler beim RENAME RELATION: Die Klammern sind nicht korrekt geschlossen.")
        new_name = m.group(1)
        if not new_name:
            raise ValueError("Der Relations-RENAME-Operator erwartet einen neuen Relationsnamen: \\_rename_relation{NeuerName}(Relation).")
        replacement = f'rename_relation({right}, "{new_name}")'
        statement = statement[:start] + replacement + statement[end-1+len(right):]
    return statement

def parse_diff(statement):
    pattern = r'\\diff\{([^}]*)\}\('
    while(True):
        matches = list(re.finditer(pattern, statement))
        if not matches:
            break
        m = matches[-1] #begin with last match
        start, end = m.span()
        left = get_matching_open_paren(statement[:start])
        right = get_matching_close_paren(statement[end-1:])
        if right is None:
            raise ValueError("Fehler bei DIFFERENZ: Die Klammern nach \\diff{...} sind nicht korrekt geschlossen.")
        replacement = f'diff({left}, {right})'
        statement = statement[:start-len(left)] + replacement + statement[end-1+len(right):]
    return statement

def parse_rename_attribute(statement):
    pattern = r'\\_rename_attribute\{([^}]*)\}\('
    while True:
        matches = list(re.finditer(pattern, statement))
        if not matches:
            break
        m = matches[-1] #begin with last match
        start, end = m.span()
        right = get_matching_close_paren(statement[end-1:])
        if right is None:
            raise ValueError("Fehler beim RENAME ATTRIBUTE: Die Klammern sind nicht korrekt geschlossen.")
        predicate = m.group(1)
        attributes = [p.strip() for p in predicate.split(",") if p.strip()]
        if len(attributes) != 2:
            raise ValueError("Der Attribut-RENAME-Operator erwartet genau zwei Attribute: \\rename_attribute{altesAttribut, neuesAttribut}.")
        old_name = attributes[0]
        new_name = attributes[1]
        replacement = f'rename_attribute({right}, "{old_name}", "{new_name}")'
        statement = statement[:start] + replacement + statement[end-1+len(right):]
    return statement

def parse_statement(statement, relations):
    print(statement)
    statement = parse_relations(statement, relations)
    print('parse relations: ', statement)
    statement = parse_rename_relation(statement)
    print('parse rename relation operation: ', statement)
    statement = parse_rename_attribute(statement)
    print('parse rename attribute operation: ', statement)
    statement = parse_selection(statement)
    print('parse select operation: ', statement)
    statement = parse_projection(statement)
    print('parse project operation: ', statement)
    statement = parse_join(statement)
    print('parse join operation: ', statement)
    statement = parse_diff(statement)
    print('parse diff operation: ', statement)
    return statement

RA_FUNCS = {
    "join",
    "projection",
    "selection",
    "diff",
    "rename_attribute",
    "rename_relation",
}

def _unparse(node: ast.AST) -> str:
    return ast.unparse(node)

def _const_str(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return _unparse(node)

def _leaf_name(node: ast.AST) -> str:
    """
    Pretty-print leaves, especially dfs['hoeren'] -> 'hoeren'.
    """
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "dfs"
    ):
        sl = node.slice
        if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
            return sl.value
    return _unparse(node)


def build_tree_from_ast(node: ast.AST) -> dict:
    """
    Returns dicts like:
    { "name": "join (cond)", "children": [...] }
    """
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        else:
            func_name = _unparse(node.func)

        args = list(node.args)

        if func_name not in RA_FUNCS:
            return {
                "name": func_name,
                "children": [build_tree_from_ast(arg) for arg in args],
            }

        # --- join(left, right, cond) ---
        if func_name == "join":
            left = build_tree_from_ast(args[0]) if len(args) > 0 else {"name": "?"}
            right = build_tree_from_ast(args[1]) if len(args) > 1 else {"name": "?"}

            if len(args) > 2:
                cond = _const_str(args[2])
                name = f"join ({cond})"
            else:
                name = "join"

            return {
                "name": name,
                "children": [left, right],
            }

        # --- projection(df, attributes) ---
        if func_name == "projection":
            df_node = build_tree_from_ast(args[0]) if len(args) > 0 else {"name": "?"}
            node_dict = {
                "name": "projection",
                "children": [df_node],
            }
            if len(args) > 1:
                attrs_node = args[1]
                if isinstance(attrs_node, ast.List):
                    attrs = [_const_str(elt) for elt in attrs_node.elts]
                else:
                    attrs = [_const_str(attrs_node)]
                node_dict["name"] = f"projection ({repr(attrs)})"
            return node_dict

        # --- selection(df, condition) ---
        if func_name == "selection":
            df_node = build_tree_from_ast(args[0]) if len(args) > 0 else {"name": "?"}
            if len(args) > 1:
                cond = _const_str(args[1])
                name = f"selection ({cond})"
            else:
                name = "selection"
            return {
                "name": name,
                "children": [df_node],
            }

        # --- diff(df1, df2) ---
        if func_name == "diff":
            left = build_tree_from_ast(args[0]) if len(args) > 0 else {"name": "?"}
            right = build_tree_from_ast(args[1]) if len(args) > 1 else {"name": "?"}
            return {
                "name": "diff",
                "children": [left, right],
            }

        # --- rename_attribute(df, old_attr, new_attr) ---
        if func_name == "rename_attribute":
            df_node = build_tree_from_ast(args[0]) if len(args) > 0 else {"name": "?"}
            old_attr = _const_str(args[1]) if len(args) > 1 else "?"
            new_attr = _const_str(args[2]) if len(args) > 2 else "?"
            return {
                "name": f"rename_attribute ({old_attr} -> {new_attr})",
                "children": [df_node],
            }

        # --- rename_relation(df, new_name) ---
        if func_name == "rename_relation":
            df_node = build_tree_from_ast(args[0]) if len(args) > 0 else {"name": "?"}
            new_name = _const_str(args[1]) if len(args) > 1 else "?"
            return {
                "name": f"rename_relation ({new_name})",
                "children": [df_node],
            }

        # Fallback
        return {
            "name": func_name,
            "children": [build_tree_from_ast(arg) for arg in args],
        }

    # Leaf
    return {"name": _leaf_name(node)}


def build_tree_from_statement(parsed_statement: str) -> dict:
    expr = ast.parse(parsed_statement, mode="eval").body
    return build_tree_from_ast(expr)

def normalize(s):
    s = restore_ops(s)
    s = disambiguate_rename(s)
    return re.sub(r"\s+", "", s)

def restore_ops(s):
    return (
        s.replace("⋈", r"\join")
         .replace("π", r"\projection")
         .replace("σ", r"\selection")
         .replace("−", r"\diff")
         .replace("ρ", r"\_rename")
    )

def disambiguate_rename(s: str) -> str:
    pattern = r'\\_rename(\s*)\{([^}]*)\}'
    def repl(match):
        space = match.group(1)  
        inner = match.group(2)   
        parts = [p.strip() for p in inner.split(",") if p.strip()]
        if len(parts) == 2:
            op = r"\_rename_attribute"
        elif len(parts) ==1:
            op = r"\_rename_relation"
        else:
            raise ValueError("Der RENAME-Operator erwartet entweder ein Argument (Relation umbenennen) oder zwei Argumente (Attribut umbenennen).")
        return f"{op}{space}{{{inner}}}"
    
    return re.sub(pattern, repl, s)

def execute_relational_algebra(dfs, statement):
    relations = list(dfs.keys())

    env = {
        "projection": projection,
        "join": join,
        "selection": selection,
        "rename_relation": rename_relation,
        "diff": diff,
        "rename_attribute": rename_attribute,
        "dfs": dfs,
    }
    try:
        statement = normalize(statement)
        statement = parse_statement(statement, relations)
        tree = build_tree_from_statement(statement)
        result = eval(statement, {"__builtins__": {}}, env)
    except ValueError:
        raise # schon "schöne" Fehler, einfach durchreichen
    except Exception as e:
        raise ValueError("Bei der Auswertung des relationalen Algebra-Ausdrucks ist ein Fehler aufgetreten. Bitte prüfen Sie die Eingabe.") from e

    return result, tree