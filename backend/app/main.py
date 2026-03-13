from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import database, matching, models, schemas
from .database import SessionLocal, init_db
from .eval_runner import run_eval_cases


app = FastAPI(title="Semantic Auto Mapper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=FRONTEND_DIR, html=True),
        name="static",
    )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


@app.get("/widget", include_in_schema=False)
def serve_widget() -> FileResponse:
    widget_path = FRONTEND_DIR / "widget.html"
    if not widget_path.exists():
        # Fallback to main UI if no dedicated widget
        widget_path = FRONTEND_DIR / "index.html"
    if not widget_path.exists():
        raise HTTPException(status_code=404, detail="widget.html not found")
    return FileResponse(widget_path)


@app.post("/api/map", response_model=schemas.MappingResponse)
def map_terms(
    request: schemas.MappingRequest,
    db: Session = Depends(get_db),
) -> schemas.MappingResponse:
    # Normalise per-run overrides to lowercase so they match the internal
    # tokenisation (which lowercases tokens).
    acr_overrides = {
        k.strip().lower(): v.strip().lower()
        for k, v in (request.acronym_overrides or {}).items()
        if k and v
    }
    syn_overrides = {
        k.strip().lower(): v.strip().lower()
        for k, v in (request.synonym_overrides or {}).items()
        if k and v
    }

    suggestions = matching.suggest_mappings(
        db=db,
        direction=request.direction,
        source_terms=request.source_terms,
        target_terms=request.target_terms,
        transient_acronyms=acr_overrides or None,
        transient_synonyms=syn_overrides or None,
    )
    return schemas.MappingResponse(direction=request.direction, suggestions=suggestions)


@app.post("/api/feedback")
def submit_feedback(
    feedback: schemas.FeedbackRequest,
    db: Session = Depends(get_db),
) -> dict:
    if feedback.chosen_target:
        db.add(
            models.TermPairFeedback(
                source_term=feedback.source_term,
                target_term=feedback.chosen_target,
                direction=feedback.direction.value,
                approved=feedback.approved,
                score_at_time=feedback.candidate_scores.get(feedback.chosen_target),
            )
        )
        if feedback.approved:
            # Use this approved mapping as a signal to learn any new acronyms.
            matching.learn_acronyms_from_feedback(
                db=db,
                source_term=feedback.source_term,
                target_term=feedback.chosen_target,
                approved=True,
            )
            # Persist as canonical mapping
            existing = (
                db.query(models.Mapping)
                .filter_by(
                    source_term=feedback.source_term,
                    target_term=feedback.chosen_target,
                    direction=feedback.direction.value,
                )
                .first()
            )
            if not existing:
                db.add(
                    models.Mapping(
                        source_term=feedback.source_term,
                        target_term=feedback.chosen_target,
                        direction=feedback.direction.value,
                    )
                )

    for rejected in feedback.rejected_targets:
        if rejected == feedback.chosen_target:
            continue
        db.add(
            models.TermPairFeedback(
                source_term=feedback.source_term,
                target_term=rejected,
                direction=feedback.direction.value,
                approved=False,
                score_at_time=feedback.candidate_scores.get(rejected),
            )
        )

    db.commit()
    return {"status": "ok"}


@app.post("/api/eval", response_model=schemas.EvalResult)
def run_eval(
    request: schemas.EvalRequest,
    db: Session = Depends(get_db),
) -> schemas.EvalResult:
    if request.use_builtin:
        try:
            from tests.run_eval import DATASET
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="Built-in eval requires tests package (run from repo with backend on path).",
            )
        result = run_eval_cases(DATASET, db=db)
        return schemas.EvalResult(**result)
    if not request.pairs or not request.target_terms or request.direction is None:
        raise HTTPException(
            status_code=400,
            detail="Custom eval requires direction, pairs, and target_terms.",
        )
    case = _EvalCase(
        name="custom",
        direction=request.direction,
        source_terms=[p.source_term for p in request.pairs],
        target_terms=request.target_terms,
        expected_top1=[p.expected_target for p in request.pairs],
    )
    result = run_eval_cases([case], db=db)
    return schemas.EvalResult(**result)


class _EvalCase:
    def __init__(self, name: str, direction: schemas.MappingDirection, source_terms: List[str], target_terms: List[str], expected_top1: List[str]):
        self.name = name
        self.direction = direction
        self.source_terms = source_terms
        self.target_terms = target_terms
        self.expected_top1 = expected_top1


@app.get("/api/mappings", response_model=List[schemas.MappingRecord])
def list_mappings(
    direction: Optional[schemas.MappingDirection] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[schemas.MappingRecord]:
    query = db.query(models.Mapping)
    if direction is not None:
        query = query.filter(models.Mapping.direction == direction.value)
    rows = query.order_by(models.Mapping.created_at.desc()).all()
    return [schemas.MappingRecord.model_validate(row) for row in rows]

