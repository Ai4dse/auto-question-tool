from fastapi import FastAPI, Request, Query, HTTPException
from mongoengine import connect
from fastapi.middleware.cors import CORSMiddleware
from .generator_loader import load_question_generators
import os
from app.routes.auth import router as auth_router
from .config import QUESTION_CONFIG

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
def get_question_by_type(type_name: str, seed: int = Query(None), difficulty: str = "easy"):
    if type_name not in question_generators:
        return {"error": "Question type not found."}
    
    base_config = question_generators[type_name]
    QuestionClass = base_config["class"]

    args = {}
    if seed is not None:
        args["seed"] = seed
    args["difficulty"] = difficulty

    question = QuestionClass(**args)

    layout = question.generate()

    return {
        "type": type_name,
        "seed": question.seed,
        "difficulty": difficulty,
        "metadata": base_config.get("metadata", {}),
        "layout": serialize(layout)
    }

@app.post("/question/{type_name}/evaluate")
async def evaluate_question(
    type_name: str,
    request: Request,
    seed: int = Query(...),
    difficulty: str = Query("easy")
):
    if type_name not in question_generators:
        return {"error": "Question type not found."}

    base_config = question_generators[type_name]
    QuestionClass = base_config["class"]

    user_input = await request.json()

    q = QuestionClass(seed=seed, difficulty=difficulty)

    try:
        result = q.evaluate(user_input)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "seed": seed,
        "difficulty": difficulty,
        "results": result
    }

@app.post("/question/{type_name}/preview")
async def preview_question(
    type_name: str,
    request: Request,
    seed: int = Query(...),
    difficulty: str = Query("easy")
):
    if type_name not in question_generators:
        raise HTTPException(status_code=404, detail="Question type not found")

    base_config = question_generators[type_name]
    QuestionClass = base_config["class"]

    payload = await request.json()
    # e.g. { "statement": "..." } or more general later
    statement = payload.get("statement", "")

    q = QuestionClass(seed=seed, difficulty=difficulty)

    if not hasattr(q, "preview"):
        # not all question types must support preview
        return {"columns": [], "rows": [], "error": "Preview not supported"}

    return q.preview(statement)