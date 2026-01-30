from fastapi import FastAPI, Request, Query, HTTPException
from mongoengine import connect
from fastapi.middleware.cors import CORSMiddleware
from .generator_loader import load_question_generators
import os
from app.routes.auth import router as auth_router
from .config import QUESTION_CONFIG
import inspect
from typing import Any, Dict

app = FastAPI()

app.include_router(auth_router)

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/user_data")

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
        {"id": qid, **cfg["metadata"]}
        for qid, cfg in QUESTION_CONFIG.items()
    ]


@app.get("/question/{type_name}")
def get_question_by_type(type_name: str, request: Request):
    if type_name not in question_generators:
        return {"error": "Question type not found."}

    base_config = question_generators[type_name]
    QuestionClass = base_config["class"]

    raw_kwargs = query_params_to_kwargs(request)
    kwargs = filter_kwargs_for_class(QuestionClass, raw_kwargs)

    try:
        question = QuestionClass(**kwargs)
    except TypeError as e:
        # This is NOT "missing settings" handling; it’s just surfacing constructor errors.
        raise HTTPException(status_code=400, detail=str(e))

    layout = question.generate()

    # difficulty may or may not exist; include if present
    difficulty = getattr(question, "difficulty", None)

    return {
        "type": type_name,
        "seed": getattr(question, "seed", None),
        "difficulty": difficulty,
        "metadata": base_config.get("metadata", {}),
        "layout": serialize(layout),
    }


@app.post("/question/{type_name}/evaluate")
async def evaluate_question(type_name: str, request: Request):
    if type_name not in question_generators:
        return {"error": "Question type not found."}

    base_config = question_generators[type_name]
    QuestionClass = base_config["class"]

    user_input = await request.json()

    raw_kwargs = query_params_to_kwargs(request)
    kwargs = filter_kwargs_for_class(QuestionClass, raw_kwargs)

    try:
        q = QuestionClass(**kwargs)
    except TypeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = q.evaluate(user_input)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "seed": getattr(q, "seed", None),
        "difficulty": getattr(q, "difficulty", None),
        "results": result,
    }

@app.post("/question/{type_name}/preview")
async def preview_question(type_name: str, request: Request):
    if type_name not in question_generators:
        raise HTTPException(status_code=404, detail="Question type not found")

    base_config = question_generators[type_name]
    QuestionClass = base_config["class"]

    payload = await request.json()
    statement = payload.get("statement", "")

    raw_kwargs = query_params_to_kwargs(request)
    kwargs = filter_kwargs_for_class(QuestionClass, raw_kwargs)

    try:
        q = QuestionClass(**kwargs)
    except TypeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not hasattr(q, "preview"):
        return {"columns": [], "rows": [], "error": "Preview not supported"}

    return q.preview(statement)