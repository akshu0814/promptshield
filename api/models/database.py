from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
import uuid
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://promptshield:promptshield@localhost:5432/promptshield")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ScanEvent(Base):
    __tablename__ = "scan_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String, nullable=True, index=True)
    prompt = Column(Text, nullable=False)
    verdict = Column(String(10), nullable=False)          # ALLOW | BLOCK
    category = Column(String(50), nullable=True)          # prompt_injection | jailbreak | extraction | pii_exfiltration
    severity = Column(String(10), nullable=True)          # low | medium | high | critical
    matched_rule = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)
    scan_duration_ms = Column(Float, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Rule(Base):
    __tablename__ = "rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)
    severity = Column(String(10), nullable=False)
    pattern = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    source = Column(String(20), nullable=False, default="custom")  # "yaml" | "custom"
    created_at = Column(DateTime, default=datetime.utcnow)


class App(Base):
    __tablename__ = "apps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    api_key = Column(String(200), nullable=False)
    block_mode = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_event_id = Column(String, nullable=False, index=True)
    channel = Column(String(50), nullable=False)          # slack | webhook | email
    status = Column(String(20), nullable=False)           # sent | failed
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
