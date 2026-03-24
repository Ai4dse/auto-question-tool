import os
import threading
from typing import Any, Dict, List, Tuple

import mysql.connector
from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool

MAX_PREVIEW_ROWS = int(os.getenv("SQL_PREVIEW_MAX_ROWS", "200"))
MAX_COMPARE_ROWS = int(os.getenv("SQL_COMPARE_MAX_ROWS", "5000"))
SQL_READ_TIMEOUT = int(os.getenv("SQL_READ_TIMEOUT_SECONDS", "8"))
SQL_CONNECT_TIMEOUT = int(os.getenv("SQL_CONNECT_TIMEOUT_SECONDS", "5"))
APP_ENV = os.getenv("APP_ENV", "development").lower()

_sql_pool: MySQLConnectionPool | None = None
_sql_pool_lock = threading.Lock()


class SqlDependencyUnavailableError(RuntimeError):
    pass


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

    conn = _sql_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        fetched = cursor.fetchmany(MAX_PREVIEW_ROWS + 1)
        rows = fetched[:MAX_PREVIEW_ROWS]
        columns = [c[0] for c in cursor.description] if cursor.description else []
        return {
            "columns": columns,
            "rows": [list(row) for row in rows],
            "total_rows": len(rows),
            "truncated": len(fetched) > MAX_PREVIEW_ROWS,
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

    conn = _sql_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        fetched = cursor.fetchmany(MAX_COMPARE_ROWS + 1)
        if len(fetched) > MAX_COMPARE_ROWS:
            raise ValueError("Abfrageergebnis zu groß für Bewertung.")
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
