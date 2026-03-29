"""
Celery background workers:
- run_full_screening: TLE ingest + conjunction screen + Pc calculation
- compute_pc_for_event: Pc timeline for a single event
Scheduled via Celery Beat every 6 hours.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "conjunction",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Schedule: run full screen every 6 hours
celery_app.conf.beat_schedule = {
    "full-screening-every-6h": {
        "task": "app.workers.celery_app.run_full_screening",
        "schedule": crontab(minute=0, hour="*/6"),
    },
}


def run_async(coro):
    """Run an async coroutine from a sync context (Celery task)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.celery_app.run_full_screening", bind=True)
def run_full_screening(self):
    """
    Full pipeline:
    1. Fetch TLEs from Space-Track
    2. Run conjunction screen
    3. Compute Pc for each conjunction
    4. Write events to DB
    5. Push WebSocket alerts for high-Pc events
    """
    return run_async(_async_full_screening(self.request.id))


async def _async_full_screening(task_id: str):
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy import update
    from app.db.session import AsyncSessionLocal
    from app.models.models import ConjunctionEvent, ScreeningRun, Satellite, TLERecord
    from app.services.ingestion import ingest_tle_catalog, get_active_satellites_with_tles
    from app.services.screener import screen_catalog
    from app.services.pc_calculator import compute_pc_foster, compute_pc_timeline
    from app.services.propagator import tle_to_satrec, propagate_to_datetime
    from app.core.config import settings
    import json

    run_id = str(uuid.uuid4())
    logger.info(f"Starting screening run {run_id}")

    async with AsyncSessionLocal() as db:
        # Create screening run record
        run = ScreeningRun(
            id=run_id,
            started_at=datetime.utcnow(),
            status="running",
        )
        db.add(run)
        await db.commit()

        try:
            # Step 1: Ingest TLEs
            logger.info("Ingesting TLEs from Space-Track...")
            ingest_stats = await ingest_tle_catalog(db, limit=settings.SCREEN_DAYS * 100)

            # Step 2: Get satellites for screening
            satellites = await get_active_satellites_with_tles(db)
            logger.info(f"Screening {len(satellites)} satellites")

            if not satellites:
                run.status = "completed"
                run.completed_at = datetime.utcnow()
                run.satellites_screened = 0
                await db.commit()
                return {"status": "no_satellites"}

            # Step 3: Run conjunction screen
            events, pairs_checked, pairs_screened = screen_catalog(
                satellites,
                screen_days=settings.SCREEN_DAYS,
                step_s=settings.SCREEN_TIMESTEP_S,
                miss_threshold_km=settings.SCREEN_MISS_DISTANCE_KM,
            )

            high_pc_count = 0

            # Step 4: Compute Pc and save each event
            for ev in events:
                try:
                    # Get TLE lines
                    line1_p = ev["line1_primary"]
                    line2_p = ev["line2_primary"]
                    line1_s = ev["line1_secondary"]
                    line2_s = ev["line2_secondary"]

                    sat1 = tle_to_satrec(line1_p, line2_p)
                    sat2 = tle_to_satrec(line1_s, line2_s)

                    tca = ev["tca_time"]

                    r1, v1 = propagate_to_datetime(sat1, tca)
                    r2, v2 = propagate_to_datetime(sat2, tca)

                    if r1 is None or r2 is None:
                        continue

                    pc_result = compute_pc_foster(r1, v1, r2, v2, hbr_m=settings.HARD_BODY_RADIUS_M)
                    pc = pc_result["pc"]

                    # Compute Pc timeline (lightweight, 10 points)
                    timeline = compute_pc_timeline(
                        line1_p, line2_p, line1_s, line2_s,
                        tca, hbr_m=settings.HARD_BODY_RADIUS_M, n_points=10,
                    )

                    if pc > settings.PC_ALERT_THRESHOLD:
                        high_pc_count += 1

                    conj = ConjunctionEvent(
                        primary_sat_id=ev["primary_sat_id"],
                        secondary_sat_id=ev["secondary_sat_id"],
                        tca_time=tca,
                        miss_distance_km=ev["miss_distance_km"],
                        relative_speed_km_s=ev.get("relative_speed_km_s"),
                        pc=pc,
                        pc_method="foster",
                        covariance_available=pc_result["covariance_available"],
                        pc_history=timeline,
                        status="active",
                        screen_run_id=run_id,
                    )
                    db.add(conj)

                except Exception as e:
                    logger.error(f"Error computing Pc for event: {e}")

            # Step 5: Update run record
            run.completed_at = datetime.utcnow()
            run.status = "completed"
            run.satellites_screened = len(satellites)
            run.pairs_evaluated = pairs_screened
            run.events_found = len(events)
            run.high_pc_events = high_pc_count

            await db.commit()
            logger.info(f"Screening run {run_id} complete: {len(events)} events, {high_pc_count} high-Pc")

            return {
                "run_id": run_id,
                "events": len(events),
                "high_pc": high_pc_count,
            }

        except Exception as e:
            logger.error(f"Screening run {run_id} failed: {e}")
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            await db.commit()
            raise


@celery_app.task(name="app.workers.celery_app.run_optimizer_task")
def run_optimizer_task(event_id: int):
    """Run maneuver optimizer for a conjunction event and update DB."""
    return run_async(_async_run_optimizer(event_id))


async def _async_run_optimizer(event_id: int):
    from sqlalchemy import select, update
    from app.db.session import AsyncSessionLocal
    from app.models.models import ConjunctionEvent, Satellite, TLERecord
    from app.services.optimizer import optimize_maneuver

    async with AsyncSessionLocal() as db:
        # Fetch event with satellite TLEs
        event = await db.get(ConjunctionEvent, event_id)
        if not event:
            return {"error": "Event not found"}

        # Get TLE records for both satellites
        async def get_latest_tle(sat_id):
            result = await db.execute(
                select(TLERecord)
                .where(TLERecord.satellite_id == sat_id, TLERecord.is_latest == True)
                .limit(1)
            )
            return result.scalar_one_or_none()

        tle1 = await get_latest_tle(event.primary_sat_id)
        tle2 = await get_latest_tle(event.secondary_sat_id)

        if not tle1 or not tle2:
            return {"error": "TLE records not found"}

        burn_plans = optimize_maneuver(
            tle1.line1, tle1.line2,
            tle2.line1, tle2.line2,
            event.tca_time,
        )

        if not burn_plans:
            return {"error": "Optimizer returned no plans"}

        best = burn_plans[0]

        await db.execute(
            update(ConjunctionEvent)
            .where(ConjunctionEvent.id == event_id)
            .values(
                optimal_burn_epoch=best["burn_epoch"],
                burn_rtn_ms=best["burn_rtn_ms"],
                burn_delta_v_ms=best["delta_v_ms"],
                pc_post_burn=best["pc_post_burn"],
                burn_lead_time_h=best["lead_time_h"],
            )
        )
        await db.commit()

        return {"event_id": event_id, "best_plan": best, "all_plans": burn_plans}
