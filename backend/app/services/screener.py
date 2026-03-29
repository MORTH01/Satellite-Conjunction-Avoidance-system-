"""
Conjunction screening: finds close approach events between satellite pairs.
Phase 1: Perigee/apogee filter (O(N) per object)
Phase 2: Coarse screen at 60s timesteps (flagged pairs only)
Phase 3: Fine TCA minimization with scipy
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import numpy as np
from scipy.optimize import minimize_scalar
from sgp4.api import Satrec, jday

from app.services.propagator import (
    tle_to_satrec, propagate_to_datetime,
    compute_miss_distance, orbits_can_intersect, compute_perigee_apogee,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def screen_pair_coarse(
    sat1: Satrec, sat2: Satrec,
    start: datetime, end: datetime,
    step_s: int = 60,
    threshold_km: float = 10.0,
) -> Optional[dict]:
    """
    Coarse screen: propagate pair at fixed timesteps.
    Returns approximate closest approach or None if never within threshold.
    """
    start_utc = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start
    total_s = (end - start).total_seconds()
    n_steps = int(total_s / step_s)

    min_dist = float("inf")
    min_time = None
    close_window = False

    for i in range(n_steps + 1):
        dt = start_utc + timedelta(seconds=i * step_s)
        r1, v1 = propagate_to_datetime(sat1, dt)
        r2, v2 = propagate_to_datetime(sat2, dt)
        if r1 is None or r2 is None:
            continue
        dist = compute_miss_distance(r1, r2)
        if dist < threshold_km:
            close_window = True
        if dist < min_dist:
            min_dist = dist
            min_time = dt
            best_v1, best_v2 = v1, v2

    if not close_window:
        return None

    return {
        "approx_tca": min_time,
        "approx_miss_km": min_dist,
    }


def find_tca(
    sat1: Satrec, sat2: Satrec,
    approx_tca: datetime,
    window_s: float = 300.0,
) -> dict:
    """
    Fine TCA search using scipy minimize_scalar.
    Searches within ±window_s seconds of approx_tca.
    Returns exact TCA time, miss distance, and velocity vectors.
    """
    ref = approx_tca.replace(tzinfo=timezone.utc) if approx_tca.tzinfo is None else approx_tca

    def miss_at_offset(offset_s):
        dt = ref + timedelta(seconds=float(offset_s))
        r1, v1 = propagate_to_datetime(sat1, dt)
        r2, v2 = propagate_to_datetime(sat2, dt)
        if r1 is None or r2 is None:
            return 1e9
        return compute_miss_distance(r1, r2)

    result = minimize_scalar(
        miss_at_offset,
        bounds=(-window_s, window_s),
        method="bounded",
        options={"xatol": 1.0},  # 1-second accuracy
    )

    tca_offset = float(result.x)
    tca = ref + timedelta(seconds=tca_offset)
    miss_km = float(result.fun)

    r1, v1 = propagate_to_datetime(sat1, tca)
    r2, v2 = propagate_to_datetime(sat2, tca)

    rel_vel = None
    if v1 is not None and v2 is not None:
        rel_vel = float(np.linalg.norm(v1 - v2))

    return {
        "tca_time": tca,
        "miss_distance_km": miss_km,
        "relative_speed_km_s": rel_vel,
        "r1_at_tca": r1,
        "v1_at_tca": v1,
        "r2_at_tca": r2,
        "v2_at_tca": v2,
    }


def screen_catalog(
    satellites: list[dict],
    screen_days: int = 7,
    step_s: int = 60,
    miss_threshold_km: float = 10.0,
) -> list[dict]:
    """
    Full catalog conjunction screen.
    satellites: list of {id, norad_id, name, line1, line2, perigee_km, apogee_km}
    Returns list of conjunction event dicts.
    """
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    end = now + timedelta(days=screen_days)

    events = []
    n = len(satellites)
    pairs_checked = 0
    pairs_screened = 0

    logger.info(f"Starting conjunction screen: {n} satellites, {screen_days} day window")

    # Build satrec objects and perigee/apogee
    sat_records = []
    for sat in satellites:
        if not sat.get("line1") or not sat.get("line2"):
            continue
        satrec = tle_to_satrec(sat["line1"], sat["line2"])
        if satrec is None:
            continue
        perigee = sat.get("perigee_km") or 0.0
        apogee = sat.get("apogee_km") or 2000.0
        sat_records.append({
            **sat,
            "satrec": satrec,
            "perigee_km": perigee,
            "apogee_km": apogee,
        })

    n = len(sat_records)

    for i in range(n):
        for j in range(i + 1, n):
            if sat_records[i]["norad_id"] == sat_records[j]["norad_id"]:
                continue
            s1 = sat_records[i]
            s2 = sat_records[j]
            pairs_checked += 1

            # Phase 1: perigee/apogee filter
            if not orbits_can_intersect(
                s1["perigee_km"], s1["apogee_km"],
                s2["perigee_km"], s2["apogee_km"],
                buffer_km=50.0,
            ):
                continue

            pairs_screened += 1

            # Phase 2: coarse screen
            coarse = screen_pair_coarse(
                s1["satrec"], s2["satrec"],
                now, end, step_s, miss_threshold_km,
            )
            if coarse is None:
                continue

            # Phase 3: fine TCA
            tca_data = find_tca(
                s1["satrec"], s2["satrec"],
                coarse["approx_tca"],
            )

            if tca_data["miss_distance_km"] > miss_threshold_km:
                continue

            events.append({
                "primary_sat_id": s1["id"],
                "secondary_sat_id": s2["id"],
                "primary_name": s1["name"],
                "secondary_name": s2["name"],
                "primary_norad": s1["norad_id"],
                "secondary_norad": s2["norad_id"],
                "tca_time": tca_data["tca_time"],
                "miss_distance_km": tca_data["miss_distance_km"],
                "relative_speed_km_s": tca_data["relative_speed_km_s"],
                "line1_primary": s1["line1"],
                "line2_primary": s1["line2"],
                "line1_secondary": s2["line1"],
                "line2_secondary": s2["line2"],
            })

            logger.info(
                f"CONJUNCTION: {s1['name']} / {s2['name']} "
                f"TCA={tca_data['tca_time']} "
                f"miss={tca_data['miss_distance_km']:.3f} km"
            )

    logger.info(
        f"Screen complete: {pairs_checked} pairs checked, "
        f"{pairs_screened} orbit-overlap candidates, "
        f"{len(events)} conjunctions found"
    )
    return events, pairs_checked, pairs_screened
