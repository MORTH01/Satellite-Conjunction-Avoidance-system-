from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models.models import Satellite, TLERecord
from app.schemas.schemas import SatelliteOut, TLERecordOut, PaginatedResponse

router = APIRouter(prefix="/api/satellites", tags=["satellites"])


@router.get("", response_model=PaginatedResponse)
async def list_satellites(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str = Query(None),
    object_type: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Satellite).where(Satellite.is_active == True)
    if search:
        query = query.where(
            Satellite.name.ilike(f"%{search}%") |
            Satellite.norad_id.cast(str).ilike(f"%{search}%")
        )
    if object_type:
        query = query.where(Satellite.object_type == object_type)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    satellites = result.scalars().all()

    return PaginatedResponse(
        items=[SatelliteOut.model_validate(s) for s in satellites],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{norad_id}/tle", response_model=TLERecordOut)
async def get_satellite_tle(norad_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Satellite).where(Satellite.norad_id == norad_id)
    )
    sat = result.scalar_one_or_none()
    if not sat:
        raise HTTPException(status_code=404, detail="Satellite not found")

    tle_result = await db.execute(
        select(TLERecord)
        .where(TLERecord.satellite_id == sat.id, TLERecord.is_latest == True)
        .limit(1)
    )
    tle = tle_result.scalar_one_or_none()
    if not tle:
        raise HTTPException(status_code=404, detail="No TLE record found")

    return TLERecordOut.model_validate(tle)


@router.get("/{norad_id}/track")
async def get_orbit_track(
    norad_id: int,
    hours: float = Query(1.5, ge=0.1, le=24.0),
    step_s: int = Query(30, ge=10, le=300),
    db: AsyncSession = Depends(get_db),
):
    """Return ECI position track for 3D visualization."""
    from datetime import datetime, timedelta, timezone
    from app.services.propagator import tle_to_satrec, propagate_to_datetime

    result = await db.execute(
        select(Satellite, TLERecord)
        .join(TLERecord, TLERecord.satellite_id == Satellite.id)
        .where(Satellite.norad_id == norad_id, TLERecord.is_latest == True)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Satellite or TLE not found")

    _, tle = row
    sat = tle_to_satrec(tle.line1, tle.line2)
    if not sat:
        raise HTTPException(status_code=422, detail="Invalid TLE")

    now = datetime.now(timezone.utc)
    end = now + timedelta(hours=hours)
    track = []
    current = now
    while current <= end:
        r, v = propagate_to_datetime(sat, current)
        if r is not None:
            track.append({
                "time": current.isoformat(),
                "x": round(float(r[0]), 3),
                "y": round(float(r[1]), 3),
                "z": round(float(r[2]), 3),
            })
        current += timedelta(seconds=step_s)

    return {"norad_id": norad_id, "name": row[0].name, "track": track}
