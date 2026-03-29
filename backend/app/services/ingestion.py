"""
TLE ingestion: fetches from Space-Track, upserts to database.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Satellite, TLERecord
from app.services.spacetrack import SpaceTrackClient, parse_gp_record
from app.services.propagator import compute_perigee_apogee

logger = logging.getLogger(__name__)


async def ingest_tle_catalog(db: AsyncSession, limit: int = 500) -> dict:
    """
    Fetch TLEs from Space-Track and upsert into database.
    Returns stats dict.
    """
    stats = {"fetched": 0, "satellites_upserted": 0, "tle_records_added": 0, "errors": 0}

    with SpaceTrackClient() as client:
        records = client.fetch_gp_catalog(limit=limit)

    if records is None:
        logger.error("Failed to fetch GP catalog — check SPACETRACK_USER and SPACETRACK_PASS in .env")
        return stats

    stats["fetched"] = len(records)

    for raw in records:
        try:
            parsed = parse_gp_record(raw)

            if not parsed["line1"] or not parsed["line2"]:
                continue
            if len(parsed["line1"]) < 60 or len(parsed["line2"]) < 60:
                continue

            # Upsert satellite
            sat_stmt = (
                insert(Satellite)
                .values(
                    norad_id=parsed["norad_id"],
                    name=parsed["name"],
                    classification=parsed["classification"],
                    intl_designator=parsed["intl_designator"],
                    object_type=parsed["object_type"],
                    country=parsed["country"],
                    is_active=True,
                    updated_at=datetime.utcnow(),
                )
                .on_conflict_do_update(
                    index_elements=["norad_id"],
                    set_={
                        "name": parsed["name"],
                        "object_type": parsed["object_type"],
                        "is_active": True,
                        "updated_at": datetime.utcnow(),
                    },
                )
                .returning(Satellite.id)
            )
            result = await db.execute(sat_stmt)
            sat_id = result.scalar_one()
            stats["satellites_upserted"] += 1

            # Mark previous TLEs as not latest
            await db.execute(
                update(TLERecord)
                .where(TLERecord.satellite_id == sat_id, TLERecord.is_latest == True)
                .values(is_latest=False)
            )

            # Parse epoch
            try:
                epoch_str = parsed["epoch"]
                epoch = datetime.fromisoformat(epoch_str.replace("Z", "+00:00"))
            except Exception:
                epoch = datetime.utcnow()

            # Compute perigee/apogee from TLE
            perigee, apogee = compute_perigee_apogee(parsed["line1"], parsed["line2"])

            # Insert new TLE record
            tle_stmt = insert(TLERecord).values(
                satellite_id=sat_id,
                epoch=epoch,
                line1=parsed["line1"],
                line2=parsed["line2"],
                mean_motion=parsed["mean_motion"],
                eccentricity=parsed["eccentricity"],
                inclination=parsed["inclination"],
                raan=parsed["raan"],
                arg_perigee=parsed["arg_perigee"],
                mean_anomaly=parsed["mean_anomaly"],
                bstar=parsed["bstar"],
                perigee_km=perigee,
                apogee_km=apogee,
                is_latest=True,
                ingested_at=datetime.utcnow(),
            ).on_conflict_do_nothing()

            await db.execute(tle_stmt)
            stats["tle_records_added"] += 1

        except Exception as e:
            logger.error(f"Error ingesting NORAD {raw.get('NORAD_CAT_ID')}: {e}")
            stats["errors"] += 1

    await db.commit()
    logger.info(f"Ingest complete: {stats}")
    return stats


async def get_active_satellites_with_tles(db: AsyncSession) -> list[dict]:
    """
    Fetch all active satellites with their latest TLEs for conjunction screening.
    """
    stmt = (
        select(
            Satellite.id,
            Satellite.norad_id,
            Satellite.name,
            TLERecord.line1,
            TLERecord.line2,
            TLERecord.perigee_km,
            TLERecord.apogee_km,
        )
        .join(TLERecord, TLERecord.satellite_id == Satellite.id)
        .where(
            Satellite.is_active == True,
            TLERecord.is_latest == True,
            TLERecord.line1.isnot(None),
            TLERecord.line2.isnot(None),
        )
    )

    result = await db.execute(stmt)
    rows = result.fetchall()
    return [
        {
            "id": row.id,
            "norad_id": row.norad_id,
            "name": row.name,
            "line1": row.line1,
            "line2": row.line2,
            "perigee_km": row.perigee_km or 0.0,
            "apogee_km": row.apogee_km or 2000.0,
        }
        for row in rows
    ]
