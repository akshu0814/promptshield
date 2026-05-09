import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import get_db, App, ScanEvent
from models.schemas import AppCreate, AppOut

router = APIRouter()


@router.post("/apps", response_model=AppOut, status_code=status.HTTP_201_CREATED, tags=["Apps"])
def create_app(payload: AppCreate, db: Session = Depends(get_db)):
    """Register a new application and receive a unique API key."""
    app = App(
        id=str(uuid.uuid4()),
        app_id=str(uuid.uuid4()),
        name=payload.name,
        api_key=secrets.token_urlsafe(32),
        block_mode=payload.block_mode,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.get("/apps", tags=["Apps"])
def list_apps(db: Session = Depends(get_db)):
    """List all registered applications with their scan counts."""
    apps = db.query(App).order_by(App.created_at.desc()).all()

    scan_counts = dict(
        db.query(ScanEvent.app_id, func.count(ScanEvent.id))
        .filter(ScanEvent.app_id.isnot(None))
        .group_by(ScanEvent.app_id)
        .all()
    )

    return [
        {
            "app_id": a.app_id,
            "name": a.name,
            "api_key": a.api_key,
            "block_mode": a.block_mode,
            "created_at": a.created_at,
            "total_scans": scan_counts.get(a.app_id, 0),
        }
        for a in apps
    ]


@router.get("/apps/{app_id}", response_model=AppOut, tags=["Apps"])
def get_app(app_id: str, db: Session = Depends(get_db)):
    """Get a single application by app_id."""
    app = db.query(App).filter(App.app_id == app_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    return app


@router.delete("/apps/{app_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Apps"])
def delete_app(app_id: str, db: Session = Depends(get_db)):
    """Delete an application."""
    app = db.query(App).filter(App.app_id == app_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    db.delete(app)
    db.commit()
