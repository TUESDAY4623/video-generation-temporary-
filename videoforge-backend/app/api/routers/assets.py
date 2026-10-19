"""Assets router."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Asset
from app.schemas.asset import AssetCreate, AssetResponse, AssetUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=AssetResponse)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/project/{project_id}", response_model=list[AssetResponse])
def list_assets_by_project(project_id: UUID, db: Session = Depends(get_db)):
    return db.query(Asset).filter(Asset.project_id == project_id).order_by(Asset.created_at.desc()).all()


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: UUID, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return asset


@router.patch("/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: UUID, payload: AssetUpdate, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}")
def delete_asset(asset_id: UUID, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    db.delete(asset)
    db.commit()
    return {"deleted": True}
