from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, UniqueConstraint

from .database import Base


class Mapping(Base):
    __tablename__ = "mappings"
    __table_args__ = (
        UniqueConstraint(
            "source_term",
            "target_term",
            "direction",
            name="uq_mapping_source_target_direction",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_term = Column(String, index=True, nullable=False)
    target_term = Column(String, index=True, nullable=False)
    direction = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TermPairFeedback(Base):
    __tablename__ = "term_pair_feedback"

    id = Column(Integer, primary_key=True, index=True)
    source_term = Column(String, index=True, nullable=False)
    target_term = Column(String, index=True, nullable=False)
    direction = Column(String, index=True, nullable=False)
    approved = Column(Boolean, nullable=False)
    score_at_time = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LearnedAcronym(Base):
    __tablename__ = "learned_acronyms"
    __table_args__ = (
        UniqueConstraint("token", "expansion", name="uq_learned_token_expansion"),
    )

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, index=True, nullable=False)
    expansion = Column(String, nullable=False)
    approval_count = Column(Integer, default=0, nullable=False)
    rejection_count = Column(Integer, default=0, nullable=False)
