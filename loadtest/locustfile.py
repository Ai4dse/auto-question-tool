import random
from typing import Any

from locust import HttpUser, between, events, task

from loadtest.config import (
    API_PREFIX,
    AUTH_PASSWORD,
    AUTH_USERNAME,
    DEFAULT_HOST,
    DEFAULT_RUN_TIME,
    DEFAULT_SPAWN_RATE,
    DEFAULT_USERS,
    FALLBACK_QUESTION_TYPES,
    WAIT_MAX_SECONDS,
    WAIT_MIN_SECONDS,
)
from loadtest.paths import choose_weighted_path, run_path
from loadtest.payload_factory import random_difficulty, random_mode, random_seed


class AppUser(HttpUser):
    host = DEFAULT_HOST
    wait_time = between(WAIT_MIN_SECONDS, WAIT_MAX_SECONDS)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._question_cache: list[dict[str, Any]] = []

    def on_start(self) -> None:
        self.login(name="startup auth")
        self.get_questions(force_refresh=True)

    @task
    def run_weighted_path(self) -> None:
        path_name = choose_weighted_path()
        run_path(self, path_name)

    def api_get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        expected_statuses: tuple[int, ...] = (200,),
        name: str | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        full_path = f"{API_PREFIX}{path}"
        with self.client.get(full_path, params=params, name=name or full_path, catch_response=True) as resp:
            if resp.status_code not in expected_statuses:
                resp.failure(f"Unexpected status {resp.status_code}")
                return None
            resp.success()
            return self._safe_json(resp)

    def api_post(
        self,
        path: str,
        payload: dict[str, Any],
        params: dict[str, Any] | None = None,
        expected_statuses: tuple[int, ...] = (200,),
        name: str | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        full_path = f"{API_PREFIX}{path}"
        with self.client.post(
            full_path,
            params=params,
            json=payload,
            name=name or full_path,
            catch_response=True,
        ) as resp:
            if resp.status_code not in expected_statuses:
                resp.failure(f"Unexpected status {resp.status_code}")
                return None
            resp.success()
            return self._safe_json(resp)

    def get_questions(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        if self._question_cache and not force_refresh:
            return self._question_cache

        data = self.api_get("/questions", name="library questions")
        if isinstance(data, list):
            self._question_cache = [q for q in data if isinstance(q, dict)]
            return self._question_cache

        self._question_cache = [{"id": qid, "settings": {}} for qid in FALLBACK_QUESTION_TYPES]
        return self._question_cache

    def choose_question(
        self,
        questions: list[dict[str, Any]],
        exclude: set[str] | None = None,
    ) -> dict[str, Any] | None:
        excluded = exclude or set()
        candidates = [q for q in questions if str(q.get("id")) not in excluded]
        if not candidates:
            return None
        return random.choice(candidates)

    def build_random_question_params(self, question: dict[str, Any]) -> dict[str, Any]:
        settings = question.get("settings") if isinstance(question.get("settings"), dict) else {}

        params: dict[str, Any] = {"seed": random_seed()}

        if "difficulty" in settings:
            options = settings.get("difficulty", {}).get("options")
            params["difficulty"] = random_difficulty(options if isinstance(options, list) else None)

        if "mode" in settings:
            options = settings.get("mode", {}).get("options")
            params["mode"] = random_mode(options if isinstance(options, list) else None)

        if str(question.get("id")) == "xpath_xquery" and "mode" not in params:
            params["mode"] = random_mode(["xpath", "xquery"])

        return params

    def open_question(self, type_name: str, params: dict[str, Any], name: str) -> dict[str, Any] | None:
        data = self.api_get(f"/question/{type_name}", params=params, name=name)
        if not isinstance(data, dict):
            return None
        layout = data.get("layout")
        return layout if isinstance(layout, dict) else None

    def post_preview(
        self,
        type_name: str,
        payload: dict[str, Any],
        params: dict[str, Any],
        expected_statuses: tuple[int, ...] = (200,),
        name: str | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        return self.api_post(
            f"/question/{type_name}/preview",
            payload=payload,
            params=params,
            expected_statuses=expected_statuses,
            name=name,
        )

    def post_evaluate(
        self,
        type_name: str,
        payload: dict[str, Any],
        params: dict[str, Any],
        expected_statuses: tuple[int, ...] = (200,),
        name: str | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        return self.api_post(
            f"/question/{type_name}/evaluate",
            payload=payload,
            params=params,
            expected_statuses=expected_statuses,
            name=name,
        )

    def login(self, name: str | None = None) -> dict[str, Any] | list[Any] | None:
        return self.api_post(
            "/auth/login",
            payload={},
            params={"username": AUTH_USERNAME, "password": AUTH_PASSWORD},
            expected_statuses=(200,),
            name=name,
        )

    @staticmethod
    def _safe_json(response) -> dict[str, Any] | list[Any] | None:
        try:
            data = response.json()
            return data
        except Exception:
            return None


@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--default-users", type=int, default=DEFAULT_USERS, help="Documented default users")
    parser.add_argument(
        "--default-spawn-rate",
        type=float,
        default=DEFAULT_SPAWN_RATE,
        help="Documented default spawn rate",
    )
    parser.add_argument(
        "--default-run-time",
        type=str,
        default=DEFAULT_RUN_TIME,
        help="Documented default run time",
    )
