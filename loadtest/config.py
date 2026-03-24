import os


API_PREFIX = os.getenv("LOADTEST_API_PREFIX", "/api")

DEFAULT_HOST = os.getenv("LOADTEST_HOST", "http://141.76.47.6:8440")

DEFAULT_USERS = int(os.getenv("LOADTEST_USERS", "50"))
DEFAULT_SPAWN_RATE = float(os.getenv("LOADTEST_SPAWN_RATE", "5"))
DEFAULT_RUN_TIME = os.getenv("LOADTEST_RUN_TIME", "10m")

WAIT_MIN_SECONDS = float(os.getenv("LOADTEST_WAIT_MIN", "1"))
WAIT_MAX_SECONDS = float(os.getenv("LOADTEST_WAIT_MAX", "4"))

AUTH_USERNAME = os.getenv("LOADTEST_USERNAME", "alice")
AUTH_PASSWORD = os.getenv("LOADTEST_PASSWORD", "test")

PATH_WEIGHTS = {
    "health_check": 2,
    "library_browse": 6,
    "question_open_randomized": 8,
    "relalg_preview_then_submit": 7,
    "sql_preview_then_submit": 7,
    "generic_evaluate": 9,
    "resubmit_pattern": 5,
    "external_types_navigation": 4,
    "auth_login_success": 3,
    "negative_resilience": 2,
}


FALLBACK_QUESTION_TYPES = [
    "relational_algebra",
    "sql_query",
    "regex",
    "xpath_xquery",
    "kmeans",
    "agnes",
    "dbscan",
    "stable_marriage",
    "apriori_algorithm",
]
