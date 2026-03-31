import os
import re
import threading
from typing import Any, Dict, List, Tuple

import mysql.connector
from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool

SQL_MAX_RESULT_ROWS = int(os.getenv("SQL_MAX_RESULT_ROWS", "10000"))
SQL_MAX_JOINS = int(os.getenv("SQL_MAX_JOINS", "3"))
SQL_READ_TIMEOUT = int(os.getenv("SQL_READ_TIMEOUT_SECONDS", "8"))
SQL_CONNECT_TIMEOUT = int(os.getenv("SQL_CONNECT_TIMEOUT_SECONDS", "5"))
APP_ENV = os.getenv("APP_ENV", "development").lower()
TOO_MANY_ROWS_MESSAGE = "The result set contains too many rows to preview."
TOO_MANY_JOINS_MESSAGE = f"A maximum of {SQL_MAX_JOINS} joins is allowed."
FROM_COMMA_NOT_ALLOWED_MESSAGE = (
    "FROM with multiple comma-separated relations is not allowed due to computational effort. "
    "Please use explicit JOIN syntax."
)

_sql_pool: MySQLConnectionPool | None = None
_sql_pool_lock = threading.Lock()


class SqlDependencyUnavailableError(RuntimeError):
    pass


def _strip_sql_comments_and_strings(sql: str) -> str:
    sql = re.sub(r"--.*?$", " ", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"'(?:''|[^'])*'", "''", sql)
    sql = re.sub(r'"(?:""|[^"])*"', '""', sql)
    return sql


def _validate_sql_limits(sql: str) -> None:
    cleaned = _strip_sql_comments_and_strings(sql)
    join_count = len(re.findall(r"\bjoin\b", cleaned, flags=re.IGNORECASE))
    if join_count > SQL_MAX_JOINS:
        raise ValueError(TOO_MANY_JOINS_MESSAGE)
    if _has_comma_separated_from_relations(cleaned):
        raise ValueError(FROM_COMMA_NOT_ALLOWED_MESSAGE)


def _has_comma_separated_from_relations(sql: str) -> bool:
    lowered = sql.lower()
    match = re.search(r"\bfrom\b", lowered)
    if not match:
        return False

    i = match.end()
    depth = 0
    from_segment_chars = []

    while i < len(lowered):
        ch = lowered[i]
        if ch == "(":
            depth += 1
        elif ch == ")" and depth > 0:
            depth -= 1

        if depth == 0 and re.match(
            r"\b(where|group\s+by|order\s+by|limit|having|union|intersect|except)\b",
            lowered[i:],
        ):
            break

        from_segment_chars.append(ch)
        i += 1

    from_segment = "".join(from_segment_chars)
    depth = 0
    for ch in from_segment:
        if ch == "(":
            depth += 1
        elif ch == ")" and depth > 0:
            depth -= 1
        elif ch == "," and depth == 0:
            return True

    return False


def _sql_settings() -> Dict[str, Any]:
    password = os.getenv("SQL_PASSWORD")
    if APP_ENV == "production" and not password:
        raise SqlDependencyUnavailableError("SQL credentials are not configured")

    return {
        "pool_name": "sql_read_pool",
        "pool_size": int(os.getenv("SQL_POOL_SIZE", "5")),
        "host": os.getenv("SQL_HOST", "localhost"),
        "port": int(os.getenv("SQL_PORT", "3306")),
        "database": os.getenv("SQL_DB", "exercise_db"),
        "user": os.getenv("SQL_USER", "sql_reader"),
        "password": password or "sql_reader_pass",
        "connection_timeout": SQL_CONNECT_TIMEOUT,
        "read_timeout": SQL_READ_TIMEOUT,
        "write_timeout": SQL_READ_TIMEOUT,
    }


def _format_sql_error(error: Error) -> str:
    message = str(error).lower()
    if error.errno in {3024, 1317}:
        return "Die Abfrage hat zu lange gedauert. Bitte passen Sie die SQL-Abfrage an."
    if (
        "maximum statement execution time exceeded" in message
        or "query execution was interrupted" in message
        or "read timeout" in message
    ):
        return "Die Abfrage hat zu lange gedauert. Bitte passen Sie die SQL-Abfrage an."
    if error.errno in {1044, 1045, 1142}:
        return "Nur Leseoperationen sind erlaubt."
    if "command denied" in message or "access denied" in message:
        return "Nur Leseoperationen sind erlaubt."
    return str(error)


def _sql_connection():
    global _sql_pool
    if _sql_pool is None:
        with _sql_pool_lock:
            if _sql_pool is None:
                try:
                    _sql_pool = MySQLConnectionPool(**_sql_settings())
                except Error as error:
                    raise SqlDependencyUnavailableError("SQL backend unavailable") from error
    if _sql_pool is None:
        raise SqlDependencyUnavailableError("SQL backend unavailable")

    try:
        return _sql_pool.get_connection()
    except Error as error:
        raise SqlDependencyUnavailableError("SQL backend unavailable") from error


def ping_sql_database() -> bool:
    conn = None
    cursor = None
    try:
        conn = _sql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        row = cursor.fetchone()
        return bool(row and row[0] == 1)
    except SqlDependencyUnavailableError:
        return False
    except Error:
        return False
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def execute_read_only_query(statement: str) -> Dict[str, Any]:
    sql = (statement or "").strip()
    if not sql:
        raise ValueError("Bitte SQL eingeben.")

    _validate_sql_limits(sql)

    conn = _sql_connection()
    cursor = None
    try:
        cursor = conn.cursor(buffered=True)
        cursor.execute(sql)
        fetched = cursor.fetchmany(SQL_MAX_RESULT_ROWS + 1)
        if len(fetched) > SQL_MAX_RESULT_ROWS:
            raise ValueError(TOO_MANY_ROWS_MESSAGE)
        rows = fetched
        columns = [c[0] for c in cursor.description] if cursor.description else []
        return {
            "columns": columns,
            "rows": [list(row) for row in rows],
            "total_rows": len(rows),
        }
    except Error as error:
        raise ValueError(_format_sql_error(error))
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def execute_for_compare(statement: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    sql = (statement or "").strip()
    if not sql:
        raise ValueError("Bitte SQL eingeben.")

    _validate_sql_limits(sql)

    conn = _sql_connection()
    cursor = None
    try:
        cursor = conn.cursor(buffered=True)
        cursor.execute(sql)
        fetched = cursor.fetchmany(SQL_MAX_RESULT_ROWS + 1)
        if len(fetched) > SQL_MAX_RESULT_ROWS:
            raise ValueError(TOO_MANY_ROWS_MESSAGE)
        rows = fetched
        columns = [c[0] for c in cursor.description] if cursor.description else []
        return columns, rows
    except Error as error:
        raise ValueError(_format_sql_error(error))
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def normalize_result_set(columns: List[str], rows: List[Tuple[Any, ...]]) -> Tuple[List[str], List[Tuple[str, ...]]]:
    normalized_rows = [tuple("" if value is None else str(value) for value in row) for row in rows]
    normalized_rows.sort()
    return list(columns), normalized_rows
