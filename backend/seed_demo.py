#!/usr/bin/env python3
import asyncio
import uuid
from datetime import datetime, timedelta
import random

DEMO_SATELLITES = [
    {"norad_id": 25544, "name": "ISS (ZARYA)", "object_type": "PAYLOAD", "country": "ISS",
     "line1": "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9993",
     "line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.49815386421940",
     "perigee_km": 415.0, "apogee_km": 420.0},
    {"norad_id": 20580, "name": "HST (HUBBLE)", "object_type": "PAYLOAD", "country": "US",
     "line1": "1 20580U 90037B   24001.50000000  .00001234  00000-0  56789-4 0  9991",
     "line2": "2 20580  28.4700 180.3456 0002910 260.1234  99.8766 15.09270000123456",
     "perigee_km": 535.0, "apogee_km": 541.0},
    {"norad_id": 43226, "name": "LEMUR-2-THERESAHARADA", "object_type": "PAYLOAD", "country": "US",
     "line1": "1 43226U 18007D   24001.50000000  .00001000  00000-0  45678-4 0  9992",
     "line2": "2 43226  97.6500  45.1234 0012345 180.0000 180.0000 14.89000000345678",
     "perigee_km": 500.0, "apogee_km": 510.0},
    {"norad_id": 48274, "name": "STARLINK-1867", "object_type": "PAYLOAD", "country": "US",
     "line1": "1 48274U 21024BJ  24001.50000000  .00003456  00000-0  23456-3 0  9993",
     "line2": "2 48274  53.0534 300.1234 0001234 200.0000 160.0000 15.06000000456789",
     "perigee_km": 540.0, "apogee_km": 560.0},
    {"norad_id": 44713, "name": "COSMOS 2542", "object_type": "PAYLOAD", "country": "CIS",
     "line1": "1 44713U 19079A   24001.50000000  .00000500  00000-0  12345-4 0  9994",
     "line2": "2 44713  97.9000  90.0000 0010000 100.0000 260.0000 14.76000000567890",
     "perigee_km": 490.0, "apogee_km": 530.0},
    {"norad_id": 39084, "name": "FLOCK 1B-1", "object_type": "PAYLOAD", "country": "US",
     "line1": "1 39084U 14016C   24001.50000000  .00002000  00000-0  18765-3 0  9995",
     "line2": "2 39084  97.9800 180.4321 0008765 50.0000 310.0000 14.82000000678901",
     "perigee_km": 460.0, "apogee_km": 480.0},
    {"norad_id": 37820, "name": "COSMOS 2251 DEB", "object_type": "DEBRIS", "country": "CIS",
     "line1": "1 37820U 09005B   24001.50000000  .00005678  00000-0  45678-3 0  9996",
     "line2": "2 37820  74.0000 220.0000 0150000 90.0000 270.0000 14.70000000789012",
     "perigee_km": 420.0, "apogee_km": 590.0},
    {"norad_id": 33442, "name": "IRIDIUM 33 DEB", "object_type": "DEBRIS", "country": "US",
     "line1": "1 33442U 09005C   24001.50000000  .00006789  00000-0  56789-3 0  9997",
     "line2": "2 33442  86.4000 150.0000 0200000 60.0000 300.0000 14.60000000890123",
     "perigee_km": 400.0, "apogee_km": 620.0},
]

DEMO_EVENTS = [
    {"primary_norad": 25544, "secondary_norad": 37820, "tca_hours": 18.5, "miss_km": 0.42, "pc": 3.2e-3, "rel_speed": 7.8},
    {"primary_norad": 48274, "secondary_norad": 33442, "tca_hours": 31.0, "miss_km": 1.87, "pc": 8.7e-4, "rel_speed": 11.2},
    {"primary_norad": 43226, "secondary_norad": 37820, "tca_hours": 52.3, "miss_km": 3.21, "pc": 1.2e-4, "rel_speed": 9.4},
    {"primary_norad": 39084, "secondary_norad": 44713, "tca_hours": 78.1, "miss_km": 4.85, "pc": 2.4e-5, "rel_speed": 6.9},
    {"primary_norad": 20580, "secondary_norad": 33442, "tca_hours": 102.6, "miss_km": 7.23, "pc": 5.1e-6, "rel_speed": 8.3},
]


async def seed():
    from app.db.session import AsyncSessionLocal, engine
    from app.models.models import Base, Satellite, TLERecord, ConjunctionEvent, ScreeningRun
    from sqlalchemy.dialects.postgresql import insert

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        sat_ids = {}

        for sat_data in DEMO_SATELLITES:
            stmt = (
                insert(Satellite)
                .values(
                    norad_id=sat_data["norad_id"],
                    name=sat_data["name"],
                    object_type=sat_data.get("object_type", "PAYLOAD"),
                    country=sat_data.get("country", "US"),
                    is_active=True,
                    classification="U",
                    updated_at=datetime.utcnow(),
                )
                .on_conflict_do_update(
                    index_elements=["norad_id"],
                    set_={"name": sat_data["name"], "updated_at": datetime.utcnow()},
                )
                .returning(Satellite.id)
            )
            result = await db.execute(stmt)
            sat_id = result.scalar_one()
            sat_ids[sat_data["norad_id"]] = sat_id

            tle_stmt = (
                insert(TLERecord)
                .values(
                    satellite_id=sat_id,
                    epoch=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                    line1=sat_data["line1"],
                    line2=sat_data["line2"],
                    perigee_km=sat_data["perigee_km"],
                    apogee_km=sat_data["apogee_km"],
                    inclination=float(sat_data["line2"].split()[2]),
                    eccentricity=float("0." + sat_data["line2"].split()[4]),
                    is_latest=True,
                    ingested_at=datetime.utcnow(),
                )
                .on_conflict_do_nothing()
            )
            await db.execute(tle_stmt)

        await db.commit()
        print(f"Seeded {len(DEMO_SATELLITES)} satellites")

        now = datetime.utcnow()

        run_id = str(uuid.uuid4())
        run = ScreeningRun(
            id=run_id,
            started_at=datetime.utcnow() - timedelta(minutes=12),
            completed_at=datetime.utcnow() - timedelta(minutes=5),
            satellites_screened=len(DEMO_SATELLITES),
            pairs_evaluated=28,
            events_found=len(DEMO_EVENTS),
            high_pc_events=2,
            status="completed",
        )
        db.add(run)

        for ev in DEMO_EVENTS:
            p_id = sat_ids.get(ev["primary_norad"])
            s_id = sat_ids.get(ev["secondary_norad"])
            if not p_id or not s_id:
                continue

            tca = now + timedelta(hours=ev["tca_hours"])

            pc_history = []
            for i in range(15):
                h = ev["tca_hours"] * (1 - i / 14)
                pc_at = ev["pc"] * (0.1 + 0.9 * (i / 14)) * random.uniform(0.85, 1.15)
                hist_time = now + timedelta(hours=ev["tca_hours"] - h)
                pc_history.append({
                    "time": hist_time.isoformat(),
                    "hours_to_tca": h,
                    "pc": round(max(0, pc_at), 8),
                    "miss_distance_km": round(ev["miss_km"] * (1 + (14 - i) * 0.1), 3),
                })

            conj = ConjunctionEvent(
                primary_sat_id=p_id,
                secondary_sat_id=s_id,
                tca_time=tca,
                miss_distance_km=ev["miss_km"],
                relative_speed_km_s=ev["rel_speed"],
                pc=ev["pc"],
                pc_method="foster",
                covariance_available=False,
                pc_history=pc_history,
                status="active",
                screen_run_id=run_id,
            )
            db.add(conj)

        await db.commit()
        print(f"Seeded {len(DEMO_EVENTS)} conjunction events")
        print("Demo data ready!")


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(seed())