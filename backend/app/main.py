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
    suggestions = matching.suggest_mappings(
        db=db,
        direction=request.direction,
        source_terms=request.source_terms,
        target_terms=request.target_terms,
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

