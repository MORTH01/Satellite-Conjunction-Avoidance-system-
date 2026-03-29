import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update
from app.db.session import get_db
from app.models.models import ConjunctionEvent, Satellite, TLERecord, ScreeningRun
from app.schemas.schemas import (
    ConjunctionEventOut, ConjunctionListItem, OptimizeRequest,
    OptimizeResponse, BurnPlan, PaginatedResponse, ScreeningRunOut,
)
from app.core.websocket import manager

router = APIRouter(prefix="/api/conjunctions", tags=["conjunctions"])


def _enrich_event(event: ConjunctionEvent, primary: Satellite, secondary: Satellite) -> dict:
    return {
        "id": event.id,
        "primary_sat_id": event.primary_sat_id,
        "secondary_sat_id": event.secondary_sat_id,
        "primary_name": primary.name if primary else None,
        "secondary_name": secondary.name if secondary else None,
        "primary_norad": primary.norad_id if primary else None,
        "secondary_norad": secondary.norad_id if secondary else None,
        "tca_time": event.tca_time,
        "miss_distance_km": event.miss_distance_km,
        "relative_speed_km_s": event.relative_speed_km_s,
        "pc": event.pc,
        "pc_method": event.pc_method,
        "covariance_available": event.covariance_available,
        "pc_history": event.pc_history or [],
        "optimal_burn_epoch": event.optimal_burn_epoch,
        "burn_rtn_ms": event.burn_rtn_ms,
        "burn_delta_v_ms": event.burn_delta_v_ms,
        "pc_post_burn": event.pc_post_burn,
        "burn_lead_time_h": event.burn_lead_time_h,
        "status": event.status,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }


@router.get("", response_model=PaginatedResponse)
async def list_conjunctions(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    sort_by: str = Query("pc", regex="^(pc|tca_time|miss_distance_km|created_at)$"),
    sort_dir: str = Query("desc", regex="^(asc|desc)$"),
    status: str = Query(None),
    min_pc: float = Query(None),
    db: AsyncSession = Depends(get_db),
):
    PriSat = Satellite.__table__.alias("primary_sat")
    SecSat = Satellite.__table__.alias("secondary_sat")

    query = (
        select(ConjunctionEvent)
        .where(ConjunctionEvent.status != "expired")
    )

    if status:
        query = query.where(ConjunctionEvent.status == status)
    if min_pc is not None:
        query = query.where(ConjunctionEvent.pc >= min_pc)

    sort_col = getattr(ConjunctionEvent, sort_by)
    query = query.order_by(desc(sort_col) if sort_dir == "desc" else sort_col)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    events = result.scalars().all()

    items = []
    for ev in events:
        pri = await db.get(Satellite, ev.primary_sat_id)
        sec = await db.get(Satellite, ev.secondary_sat_id)
        items.append(ConjunctionListItem(
            id=ev.id,
            primary_sat_id=ev.primary_sat_id,
            secondary_sat_id=ev.secondary_sat_id,
            primary_name=pri.name if pri else "Unknown",
            secondary_name=sec.name if sec else "Unknown",
            primary_norad=pri.norad_id if pri else None,
            secondary_norad=sec.norad_id if sec else None,
            tca_time=ev.tca_time,
            miss_distance_km=ev.miss_distance_km,
            pc=ev.pc,
            status=ev.status,
            has_burn_plan=ev.burn_delta_v_ms is not None,
        ))

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_result = await db.execute(
        select(func.count()).where(ConjunctionEvent.status == "active")
    )
    high_pc_result = await db.execute(
        select(func.count()).where(
            ConjunctionEvent.status == "active",
            ConjunctionEvent.pc >= 1e-4,
        )
    )
    sat_result = await db.execute(
        select(func.count()).where(Satellite.is_active == True)
    )
    run_result = await db.execute(
        select(ScreeningRun).order_by(desc(ScreeningRun.started_at)).limit(1)
    )
    last_run = run_result.scalar_one_or_none()

    return {
        "active_conjunctions": total_result.scalar(),
        "high_pc_count": high_pc_result.scalar(),
        "satellites_tracked": sat_result.scalar(),
        "last_screen_at": last_run.completed_at if last_run else None,
        "last_screen_status": last_run.status if last_run else None,
    }


@router.get("/{event_id}", response_model=ConjunctionEventOut)
async def get_conjunction(event_id: int, db: AsyncSession = Depends(get_db)):
    event = await db.get(ConjunctionEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Conjunction event not found")

    pri = await db.get(Satellite, event.primary_sat_id)
    sec = await db.get(Satellite, event.secondary_sat_id)

    return ConjunctionEventOut(**_enrich_event(event, pri, sec))


@router.post("/{event_id}/optimize", response_model=OptimizeResponse)
async def optimize_conjunction(
    event_id: int,
    req: OptimizeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(ConjunctionEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Conjunction event not found")

    pri_tle_result = await db.execute(
        select(TLERecord)
        .where(TLERecord.satellite_id == event.primary_sat_id, TLERecord.is_latest == True)
        .limit(1)
    )
    sec_tle_result = await db.execute(
        select(TLERecord)
        .where(TLERecord.satellite_id == event.secondary_sat_id, TLERecord.is_latest == True)
        .limit(1)
    )
    tle1 = pri_tle_result.scalar_one_or_none()
    tle2 = sec_tle_result.scalar_one_or_none()

    if not tle1 or not tle2:
        raise HTTPException(status_code=422, detail="TLE records not available for optimization")

    from app.services.optimizer import optimize_maneuver

    burn_plans = await asyncio.to_thread(
        optimize_maneuver,
        tle1.line1, tle1.line2,
        tle2.line1, tle2.line2,
        event.tca_time,
        req.lead_times_h,
    )

    if not burn_plans:
        raise HTTPException(status_code=422, detail="Optimizer found no valid burn plans")

    best = burn_plans[0]

    await db.execute(
        update(ConjunctionEvent)
        .where(ConjunctionEvent.id == event_id)
        .values(
            optimal_burn_epoch=best.get("burn_epoch"),
            burn_rtn_ms=best.get("burn_rtn_ms"),
            burn_delta_v_ms=best.get("delta_v_ms"),
            pc_post_burn=best.get("pc_post_burn"),
            burn_lead_time_h=best.get("lead_time_h"),
        )
    )
    await db.commit()

    await manager.broadcast({
        "type": "optimizer_done",
        "event_id": event_id,
        "delta_v_ms": best.get("delta_v_ms"),
        "pc_post_burn": best.get("pc_post_burn"),
    })

    plans_out = [
        BurnPlan(
            burn_epoch=p.get("burn_epoch"),
            burn_rtn_ms=p.get("burn_rtn_ms"),
            delta_v_ms=p.get("delta_v_ms"),
            pc_post_burn=p.get("pc_post_burn"),
            lead_time_h=p.get("lead_time_h"),
        )
        for p in burn_plans
    ]

    return OptimizeResponse(
        event_id=event_id,
        burn_plans=plans_out,
        best_plan=plans_out[0],
        message=f"Optimal burn: {best.get('delta_v_ms', 0):.4f} m/s at {best.get('lead_time_h', 0):.0f}h before TCA",
    )


@router.post("/trigger-screen")
async def trigger_screen(background_tasks: BackgroundTasks):
    """Manually trigger a conjunction screening run."""
    from app.workers.celery_app import run_full_screening
    task = run_full_screening.delay()
    return {"task_id": task.id, "message": "Screening run enqueued"}


@router.get("/runs/history", response_model=list[ScreeningRunOut])
async def get_screening_runs(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScreeningRun)
        .order_by(desc(ScreeningRun.started_at))
        .limit(limit)
    )
    runs = result.scalars().all()
    return [ScreeningRunOut.model_validate(r) for r in runs]
