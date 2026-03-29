"""
SGP4 orbit propagation using python-sgp4.
Converts TLE lines to ECI position/velocity vectors.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
import numpy as np
from sgp4.api import Satrec, jday

logger = logging.getLogger(__name__)

# Earth constants
EARTH_RADIUS_KM = 6371.0
MU = 398600.4418  # km^3/s^2


def tle_to_satrec(line1: str, line2: str) -> Optional[Satrec]:
    """Parse TLE lines into an SGP4 satellite record."""
    try:
        sat = Satrec.twoline2rv(line1, line2)
        return sat
    except Exception as e:
        logger.error(f"Failed to parse TLE: {e}")
        return None


def propagate_to_datetime(sat: Satrec, dt: datetime) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Propagate satellite to a given UTC datetime.
    Returns (position_km, velocity_km_s) in ECI frame, or (None, None) on error.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)
    e, r, v = sat.sgp4(jd, fr)
    if e != 0:
        return None, None
    return np.array(r), np.array(v)


def propagate_track(
    line1: str,
    line2: str,
    start: datetime,
    end: datetime,
    step_seconds: int = 60,
) -> list[dict]:
    """
    Propagate orbit from start to end at step_seconds intervals.
    Returns list of {time, r, v} dicts for ECI positions.
    """
    sat = tle_to_satrec(line1, line2)
    if sat is None:
        return []

    results = []
    total_seconds = (end - start).total_seconds()
    n_steps = int(total_seconds / step_seconds)

    start_utc = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start

    for i in range(n_steps + 1):
        dt_offset = i * step_seconds
        current = start_utc.replace(
            second=0, microsecond=0
        )
        # Use timestamp arithmetic for precision
        from datetime import timedelta
        current = start_utc + timedelta(seconds=dt_offset)

        r, v = propagate_to_datetime(sat, current)
        if r is not None:
            results.append({"time": current, "r": r, "v": v})

    return results


def compute_miss_distance(r1: np.ndarray, r2: np.ndarray) -> float:
    """Compute miss distance (km) between two ECI position vectors."""
    return float(np.linalg.norm(r1 - r2))


def compute_perigee_apogee(line1: str, line2: str) -> Tuple[float, float]:
    """
    Compute perigee and apogee altitude (km above Earth surface) from TLE.
    Used for fast orbit overlap pre-filter.
    """
    try:
        sat = Satrec.twoline2rv(line1, line2)
        # Mean motion in rad/min
        n = sat.nm  # mean motion rad/min
        # Semi-major axis
        a = (MU / (n * np.pi / 30) ** 2) ** (1 / 3)
        e = sat.ecco
        perigee = a * (1 - e) - EARTH_RADIUS_KM
        apogee = a * (1 + e) - EARTH_RADIUS_KM
        return max(perigee, 0.0), max(apogee, 0.0)
    except Exception:
        return 0.0, 2000.0  # conservative fallback


def orbits_can_intersect(
    perigee1: float, apogee1: float,
    perigee2: float, apogee2: float,
    buffer_km: float = 50.0,
) -> bool:
    """
    Fast pre-filter: can two orbits possibly intersect?
    Returns False if one orbit's apogee is below the other's perigee.
    """
    # Orbit 1 is entirely below orbit 2
    if apogee1 + buffer_km < perigee2:
        return False
    # Orbit 2 is entirely below orbit 1
    if apogee2 + buffer_km < perigee1:
        return False
    return True
