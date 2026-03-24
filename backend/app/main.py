import os
import inspect
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from mongoengine import connect, disconnect
from mongoengine.connection import get_db

from app.errors import DependencyUnavailableError
from app.routes.auth import router as auth_router

from .config import QUESTION_CONFIG, WEEK_CONFIG
from .generator_loader import load_question_generators
from .question_types.sql_query_helper import ping_sql_database


def _setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


_setup_logging()
logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent
APP_ENV = os.getenv("APP_ENV", "development").lower()
STRICT_GENERATOR_LOADING = os.getenv("STRICT_GENERATOR_LOADING", "false").lower() == "true"


@asynccontextmanager
async def lifespan(_: FastAPI):
    global question_generators

    try:
        connect(host=MONGO_URL)
    except Exception:
        logger.exception("Failed to connect to MongoDB during startup")
        if APP_ENV == "production":
            raise

    question_generators = load_question_generators(strict=STRICT_GENERATOR_LOADING)
    yield

    try:
        disconnect()
    except Exception:
        logger.exception("Failed to disconnect MongoDB cleanly")


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.mount("/resources", StaticFiles(directory=str(APP_DIR / "resources")), name="resources")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/user_data")
RELEASE_TIMEZONE = ZoneInfo("Europe/Berlin")
question_generators: Dict[str, Dict[str, Any]] = {}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    details = {
        "mongo": _mongo_is_ready(),
        "sql": _sql_is_ready(),
        "generators_loaded": bool(question_generators),
    }
    if not all(details.values()):
        raise HTTPException(status_code=503, detail={"status": "degraded", "details": details})
    return {"status": "ok", "details": details}


def _mongo_is_ready() -> bool:
    try:
        db = get_db()
        db.command("ping")
        return True
    except Exception:
        logger.warning("Mongo readiness check failed")
        return False


def _sql_is_ready() -> bool:
    try:
        return ping_sql_database()
    except Exception:
        logger.warning("SQL readiness check failed")
        return False

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8440",
        "http://127.0.0.1:8440",
        "http://frontend:8440",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_current_date_in_release_timezone() -> date:
    return datetime.now(RELEASE_TIMEZONE).date()


def _get_release_date_for_week(week_number: int) -> date:
    week_cfg = WEEK_CONFIG.get(week_number)
    if not week_cfg:
        raise HTTPException(status_code=404, detail="Question type not found")

    start_date = week_cfg.get("start_date")
    try:
        return date.fromisoformat(str(start_date))
    except ValueError:
        raise HTTPException(status_code=404, detail="Question type not found")


def is_question_released(metadata: Dict[str, Any]) -> bool:
    try:
        release_week = int(metadata.get("week", 1))
    except (TypeError, ValueError):
        return False

    if release_week < 1:
        return False

    release_date = _get_release_date_for_week(release_week)
    return get_current_date_in_release_timezone() >= release_date


def ensure_question_is_released(type_name: str) -> None:
    metadata = QUESTION_CONFIG.get(type_name, {}).get("metadata", {})
    if not is_question_released(metadata):
        raise HTTPException(status_code=404, detail="Question type not found")

def query_params_to_kwargs(request: Request) -> Dict[str, Any]:

    kwargs: Dict[str, Any] = {}
    for k, v in request.query_params.items():
        if v is None:
            continue
        v_str = str(v)
        if v_str.isdigit():
            kwargs[k] = int(v_str)
        else:
            kwargs[k] = v_str
    return kwargs

def filter_kwargs_for_class(cls, kwargs: Dict[str, Any]) -> Dict[str, Any]:

    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        # If signature isn't available, safest is pass nothing
        return {}

    params = sig.parameters
    has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

    if has_var_kw:
        return kwargs

    allowed = {name for name in params.keys() if name != "self"}
    return {k: v for k, v in kwargs.items() if k in allowed}


def serialize(obj):
    if hasattr(obj, '__dict__'):
        return {
            k: serialize(v)
            for k, v in obj.__dict__.items()
            if not callable(v) and not k.startswith('_')
        }
    elif isinstance(obj, list):
        return [serialize(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    else:
        return obj

@app.get("/questions")
def get_questions():
    return [
        {
            "id": qid,
            **cfg["metadata"],
            "week_title": WEEK_CONFIG.get(int(cfg["metadata"].get("week", 1)), {}).get("title"),
            "week_start_date": WEEK_CONFIG.get(int(cfg["metadata"].get("week", 1)), {}).get("start_date"),
        }
        for qid, cfg in QUESTION_CONFIG.items()
        if is_question_released(cfg.get("metadata", {}))
    ]


@app.get("/question/{type_name}")
def get_question_by_type(type_name: str, request: Request):
    if type_name not in question_generators:
        raise HTTPException(status_code=404, detail="Question type not found")

    ensure_question_is_released(type_name)

    base_config = question_generators[type_name]
    QuestionClass = base_config["class"]

    raw_kwargs = query_params_to_kwargs(request)
    kwargs = filter_kwargs_for_class(QuestionClass, raw_kwargs)

    question = _build_question_instance(QuestionClass, kwargs)

    layout = question.generate()

    # difficulty may or may not exist; include if present
    difficulty = getattr(question, "difficulty", None)

    return {
        "type": type_name,
        "seed": getattr(question, "seed", None),
        "difficulty": difficulty,
        "exercise_name": getattr(question, "exercise", {}).get("name") if hasattr(question, "exercise") else None,
        "metadata": base_config.get("metadata", {}),
        "layout": serialize(layout),
    }


@app.post("/question/{type_name}/evaluate")
async def evaluate_question(type_name: str, request: Request):
    if type_name not in question_generators:
        raise HTTPException(status_code=404, detail="Question type not found")

    ensure_question_is_released(type_name)

    base_config = question_generators[type_name]
    QuestionClass = base_config["class"]

    try:
        user_input = await request.json()
    except (JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    raw_kwargs = query_params_to_kwargs(request)
    kwargs = filter_kwargs_for_class(QuestionClass, raw_kwargs)

    q = await run_in_threadpool(_build_question_instance, QuestionClass, kwargs)

    try:
        result = await run_in_threadpool(q.evaluate, user_input)
    except DependencyUnavailableError as e:
        logger.exception("Dependency unavailable while evaluating question", extra={"type_name": type_name})
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "seed": getattr(q, "seed", None),
        "difficulty": getattr(q, "difficulty", None),
        "exercise_name": getattr(q, "exercise", {}).get("name") if hasattr(q, "exercise") else None,
        "results": result,
    }

@app.post("/question/{type_name}/preview")
async def preview_question(type_name: str, request: Request):
    if type_name not in question_generators:
        raise HTTPException(status_code=404, detail="Question type not found")

    ensure_question_is_released(type_name)

    base_config = question_generators[type_name]
    QuestionClass = base_config["class"]

    try:
        payload = await request.json()
    except (JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    statement = payload.get("statement", "")

    raw_kwargs = query_params_to_kwargs(request)
    kwargs = filter_kwargs_for_class(QuestionClass, raw_kwargs)

    q = await run_in_threadpool(_build_question_instance, QuestionClass, kwargs)

    if not hasattr(q, "preview"):
        return {"columns": [], "rows": [], "error": "Preview not supported"}

    try:
        return await run_in_threadpool(q.preview, statement)
    except DependencyUnavailableError as e:
        logger.exception("Dependency unavailable while previewing question", extra={"type_name": type_name})
        raise HTTPException(status_code=503, detail=str(e))


def _build_question_instance(cls, kwargs: Dict[str, Any]):
    try:
        return cls(**kwargs)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
