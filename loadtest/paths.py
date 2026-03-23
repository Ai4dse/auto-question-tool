import random
from collections.abc import Callable

from loadtest.config import PATH_WEIGHTS
from loadtest.payload_factory import (
    evaluate_payload_for_type,
    preview_payload_for_type,
    random_difficulty,
    random_mode,
    random_seed,
)


PATH_NAMES = list(PATH_WEIGHTS.keys())


def choose_weighted_path() -> str:
    return random.choices(PATH_NAMES, weights=[PATH_WEIGHTS[name] for name in PATH_NAMES], k=1)[0]


def run_path(user, path_name: str) -> None:
    handlers: dict[str, Callable] = {
        "health_check": _path_health_check,
        "library_browse": _path_library_browse,
        "question_open_randomized": _path_question_open_randomized,
        "relalg_preview_then_submit": _path_relalg_preview_then_submit,
        "sql_preview_then_submit": _path_sql_preview_then_submit,
        "generic_evaluate": _path_generic_evaluate,
        "resubmit_pattern": _path_resubmit_pattern,
        "external_types_navigation": _path_external_types_navigation,
        "auth_login_success": _path_auth_login_success,
        "negative_resilience": _path_negative_resilience,
    }
    handler = handlers.get(path_name)
    if handler is None:
        return
    handler(user)


def _path_health_check(user) -> None:
    user.api_get("/health", name="01 health")


def _path_library_browse(user) -> None:
    questions = user.get_questions(force_refresh=True)
    choice = user.choose_question(questions)
    if not choice:
        return
    params = user.build_random_question_params(choice)
    user.open_question(choice["id"], params=params, name="02 library -> open")


def _path_question_open_randomized(user) -> None:
    choice = user.choose_question(user.get_questions())
    if not choice:
        return
    params = user.build_random_question_params(choice)
    user.open_question(choice["id"], params=params, name="03 open randomized")


def _path_relalg_preview_then_submit(user) -> None:
    params = {"difficulty": random_difficulty(["easy", "medium", "hard"]), "seed": random_seed()}
    layout = user.open_question("relational_algebra", params=params, name="04 relalg open")
    preview_payload = preview_payload_for_type("relational_algebra")
    user.post_preview("relational_algebra", preview_payload, params=params, name="04 relalg preview")
    evaluate_payload = evaluate_payload_for_type("relational_algebra", layout=layout)
    user.post_evaluate("relational_algebra", evaluate_payload, params=params, name="04 relalg evaluate")


def _path_sql_preview_then_submit(user) -> None:
    params = {
        "mode": random_mode(["steps", "exam"]),
        "difficulty": random_difficulty(["easy", "medium", "hard"]),
        "seed": random_seed(),
    }
    layout = user.open_question("sql_query", params=params, name="05 sql open")
    preview_payload = preview_payload_for_type("sql_query")
    user.post_preview("sql_query", preview_payload, params=params, name="05 sql preview")
    evaluate_payload = evaluate_payload_for_type("sql_query", layout=layout)
    user.post_evaluate("sql_query", evaluate_payload, params=params, name="05 sql evaluate")


def _path_generic_evaluate(user) -> None:
    choice = user.choose_question(
        user.get_questions(),
        exclude={"sql_query", "relational_algebra", "regex", "xpath_xquery"},
    )
    if not choice:
        return
    params = user.build_random_question_params(choice)
    layout = user.open_question(choice["id"], params=params, name="06 generic open")
    payload = evaluate_payload_for_type(choice["id"], layout=layout)
    user.post_evaluate(choice["id"], payload, params=params, name="06 generic evaluate")


def _path_resubmit_pattern(user) -> None:
    choice = user.choose_question(user.get_questions())
    if not choice:
        return
    params = user.build_random_question_params(choice)
    layout = user.open_question(choice["id"], params=params, name="07 resubmit open")
    for attempt in (1, 2, 3):
        payload = evaluate_payload_for_type(choice["id"], layout=layout, attempt=attempt)
        user.post_evaluate(choice["id"], payload, params=params, name="07 resubmit evaluate")


def _path_external_types_navigation(user) -> None:
    regex_params = {"difficulty": random_difficulty(["easy", "medium", "hard"]), "seed": random_seed()}
    user.open_question("regex", params=regex_params, name="08 external regex")

    xpath_params = {
        "mode": random_mode(["xpath", "xquery"]),
        "difficulty": random_difficulty(["easy", "medium", "hard"]),
        "seed": random_seed(),
    }
    user.open_question("xpath_xquery", params=xpath_params, name="08 external xpath")


def _path_auth_login_success(user) -> None:
    user.login(name="09 auth login")


def _path_negative_resilience(user) -> None:
    user.api_get("/question/not_a_real_type", expected_statuses=(404,), name="10 negative unknown type")

    user.post_preview(
        "sql_query",
        payload={"bad_key": "oops"},
        params={"difficulty": "easy", "seed": random_seed()},
        expected_statuses=(200, 400),
        name="10 negative sql malformed preview",
    )

    user.post_evaluate(
        "relational_algebra",
        payload={"0": ""},
        params={"difficulty": "easy", "seed": random_seed()},
        expected_statuses=(200, 400),
        name="10 negative relalg invalid evaluate",
    )
