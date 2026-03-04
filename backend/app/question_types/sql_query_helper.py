import os
from typing import Any, Dict, List, Tuple

import mysql.connector
from mysql.connector import Error


def _format_sql_error(error: Error) -> str:
    message = str(error).lower()
    if error.errno in {1044, 1045, 1142}:
        return "Nur Leseoperationen sind erlaubt."
    if "command denied" in message or "access denied" in message:
        return "Nur Leseoperationen sind erlaubt."
    return str(error)


def _sql_connection():
    return mysql.connector.connect(
        host=os.getenv("SQL_HOST", "localhost"),
        port=int(os.getenv("SQL_PORT", "3306")),
        database=os.getenv("SQL_DB", "exercise_db"),
        user=os.getenv("SQL_USER", "sql_reader"),
        password=os.getenv("SQL_PASSWORD", "sql_reader_pass"),
        connection_timeout=5,
    )


def execute_read_only_query(statement: str) -> Dict[str, Any]:
    sql = (statement or "").strip()
    if not sql:
        raise ValueError("Bitte SQL eingeben.")

    conn = _sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [c[0] for c in cursor.description] if cursor.description else []
        return {
            "columns": columns,
            "rows": [list(row) for row in rows],
            "total_rows": len(rows),
        }
    except Error as error:
        raise ValueError(_format_sql_error(error))
    finally:
        conn.close()


def execute_for_compare(statement: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    sql = (statement or "").strip()
    if not sql:
        raise ValueError("Bitte SQL eingeben.")

    conn = _sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [c[0] for c in cursor.description] if cursor.description else []
        return columns, rows
    except Error as error:
        raise ValueError(_format_sql_error(error))
    finally:
        conn.close()


def normalize_result_set(columns: List[str], rows: List[Tuple[Any, ...]]) -> Tuple[List[str], List[Tuple[str, ...]]]:
    normalized_rows = [tuple("" if value is None else str(value) for value in row) for row in rows]
    normalized_rows.sort()
    return list(columns), normalized_rows
