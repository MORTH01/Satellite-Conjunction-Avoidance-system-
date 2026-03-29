"""
Space-Track.org API client.
Register for free at: https://www.space-track.org/auth/createAccount
"""
import logging
from typing import Optional
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)

SPACETRACK_LOGIN_URL = f"{settings.SPACETRACK_BASE_URL}/ajaxauth/login"
SPACETRACK_GP_URL = (
    f"{settings.SPACETRACK_BASE_URL}/basicspacedata/query/class/gp"
    "/EPOCH/>now-30/orderby/NORAD_CAT_ID asc/format/json"
)
SPACETRACK_GP_ACTIVE_URL = (
    f"{settings.SPACETRACK_BASE_URL}/basicspacedata/query/class/gp"
    "/EPOCH/>now-30/OBJECT_TYPE/PAYLOAD,ROCKET BODY,DEBRIS"
    "/DECAY/null-val/orderby/NORAD_CAT_ID asc/format/json/limit/500"
)


class SpaceTrackClient:
    """Session-based client for the Space-Track REST API."""

    def __init__(self):
        self.session = requests.Session()
        self._logged_in = False

    def login(self) -> bool:
        if not settings.SPACETRACK_USER or not settings.SPACETRACK_PASS:
            logger.error("SPACETRACK_USER and SPACETRACK_PASS must be set in .env")
            return False
        try:
            resp = self.session.post(
                SPACETRACK_LOGIN_URL,
                data={
                    "identity": settings.SPACETRACK_USER,
                    "password": settings.SPACETRACK_PASS,
                },
                timeout=30,
            )
            resp.raise_for_status()
            self._logged_in = True
            logger.info("Space-Track login successful")
            return True
        except Exception as e:
            logger.error(f"Space-Track login failed: {e}")
            return False

    def logout(self):
        try:
            self.session.get(
                f"{settings.SPACETRACK_BASE_URL}/ajaxauth/logout",
                timeout=10,
            )
        except Exception:
            pass
        self._logged_in = False

    def fetch_gp_catalog(self, limit: int = 500) -> Optional[list]:
        """Fetch GP (General Perturbations) catalog — contains TLE data."""
        if not self._logged_in:
            if not self.login():
                return None

        url = (
            f"{settings.SPACETRACK_BASE_URL}/basicspacedata/query/class/gp"
            f"/EPOCH/>now-30/DECAY/null-val"
            f"/orderby/NORAD_CAT_ID asc/format/json/limit/{limit}"
        )
        try:
            resp = self.session.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Fetched {len(data)} GP records from Space-Track")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch GP catalog: {e}")
            return None

    def fetch_single_sat(self, norad_id: int) -> Optional[dict]:
        """Fetch GP record for a single satellite by NORAD ID."""
        if not self._logged_in:
            if not self.login():
                return None

        url = (
            f"{settings.SPACETRACK_BASE_URL}/basicspacedata/query/class/gp"
            f"/NORAD_CAT_ID/{norad_id}/format/json/limit/1"
        )
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data[0] if data else None
        except Exception as e:
            logger.error(f"Failed to fetch sat {norad_id}: {e}")
            return None

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, *args):
        self.logout()


def parse_gp_record(record: dict) -> dict:
    """Parse a Space-Track GP JSON record into our internal format."""
    return {
        "norad_id": int(record.get("NORAD_CAT_ID", 0)),
        "name": record.get("OBJECT_NAME", "UNKNOWN").strip(),
        "classification": record.get("CLASSIFICATION_TYPE", "U"),
        "intl_designator": record.get("INTLDES", ""),
        "object_type": record.get("OBJECT_TYPE", ""),
        "country": record.get("COUNTRY_CODE", ""),
        "line1": record.get("TLE_LINE1", ""),
        "line2": record.get("TLE_LINE2", ""),
        "epoch": record.get("EPOCH", ""),
        "mean_motion": float(record.get("MEAN_MOTION", 0) or 0),
        "eccentricity": float(record.get("ECCENTRICITY", 0) or 0),
        "inclination": float(record.get("INCLINATION", 0) or 0),
        "raan": float(record.get("RA_OF_ASC_NODE", 0) or 0),
        "arg_perigee": float(record.get("ARG_OF_PERICENTER", 0) or 0),
        "mean_anomaly": float(record.get("MEAN_ANOMALY", 0) or 0),
        "bstar": float(record.get("BSTAR", 0) or 0),
        "perigee_km": float(record.get("PERIGEE", 0) or 0),
        "apogee_km": float(record.get("APOGEE", 0) or 0),
    }
