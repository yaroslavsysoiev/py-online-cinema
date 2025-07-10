from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from database.models.movies import CertificationModel
from schemas.movies import (
    CertificationSchema,
    CertificationCreateSchema,
    CertificationUpdateSchema
)

router = APIRouter(prefix="/certifications", tags=["Certifications"])

@router.post("/", response_model=CertificationSchema, status_code=status.HTTP_201_CREATED)
async def create_certification(
    data: CertificationCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(select(CertificationModel).where(CertificationModel.name == data.name))
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="Certification with this name already exists.")
    certification = CertificationModel(name=data.name)
    db.add(certification)
    await db.commit()
    await db.refresh(certification)
    return certification

@router.get("/", response_model=list[CertificationSchema])
async def list_certifications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CertificationModel))
    return result.scalars().all()

@router.get("/{certification_id}", response_model=CertificationSchema)
async def get_certification(certification_id: int, db: AsyncSession = Depends(get_db)):
    certification = await db.get(CertificationModel, certification_id)
    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found.")
    return certification

@router.patch("/{certification_id}", response_model=CertificationSchema)
async def update_certification(
    certification_id: int,
    data: CertificationUpdateSchema,
    db: AsyncSession = Depends(get_db)
):
    certification = await db.get(CertificationModel, certification_id)
    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found.")
    certification.name = data.name
    await db.commit()
    await db.refresh(certification)
    return certification

@router.delete("/{certification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certification(certification_id: int, db: AsyncSession = Depends(get_db)):
    certification = await db.get(CertificationModel, certification_id)
    if not certification:
        raise HTTPException(status_code=404, detail="Certification not found.")
    await db.delete(certification)
    await db.commit() 