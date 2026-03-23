from datetime import date, datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from mongoengine import connect
from fastapi.middleware.cors import CORSMiddleware
from .generator_loader import load_question_generators
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from app.routes.auth import router as auth_router
from .config import QUESTION_CONFIG, WEEK_CONFIG
import inspect
from typing import Any, Dict

app = FastAPI()
APP_DIR = Path(__file__).resolve().parent

app.include_router(auth_router)
app.mount("/resources", StaticFiles(directory=str(APP_DIR / "resources")), name="resources")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/user_data")
RELEASE_TIMEZONE = ZoneInfo("Europe/Berlin")

connect(host=MONGO_URL)

@app.get("/health")
def health():
    return {"status": "ok"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  
        "http://127.0.0.1:5173",
        "http://frontend:5173",  
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

question_generators = load_question_generators()


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

    try:
        question = QuestionClass(**kwargs)
    except (TypeError, ValueError) as e:
        # This is NOT "missing settings" handling; it’s just surfacing constructor errors.
        raise HTTPException(status_code=400, detail=str(e))

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

    user_input = await request.json()

    raw_kwargs = query_params_to_kwargs(request)
    kwargs = filter_kwargs_for_class(QuestionClass, raw_kwargs)

    try:
        q = QuestionClass(**kwargs)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = await run_in_threadpool(q.evaluate, user_input)
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

    payload = await request.json()
    statement = payload.get("statement", "")

    raw_kwargs = query_params_to_kwargs(request)
    kwargs = filter_kwargs_for_class(QuestionClass, raw_kwargs)

    try:
        q = QuestionClass(**kwargs)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not hasattr(q, "preview"):
        return {"columns": [], "rows": [], "error": "Preview not supported"}

    return await run_in_threadpool(q.preview, statement)
