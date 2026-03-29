"""
Foster's method for Probability of Collision (Pc) computation.
References:
  - Foster & Estes (1992) "A Parametric Analysis of Orbital Debris Collision Probability"
  - NASA CARA conjunction assessment methodology
"""
import logging
import numpy as np
from scipy import integrate

logger = logging.getLogger(__name__)

# Default combined hard-body radius (primary + secondary) in meters
DEFAULT_HBR_M = 10.0


def compute_pc_foster(
    r1: np.ndarray,
    v1: np.ndarray,
    r2: np.ndarray,
    v2: np.ndarray,
    cov1: np.ndarray = None,
    cov2: np.ndarray = None,
    hbr_m: float = DEFAULT_HBR_M,
) -> dict:
    """
    Compute Pc using Foster's 2D method.

    Parameters:
        r1, r2: ECI position vectors (km) at TCA
        v1, v2: ECI velocity vectors (km/s) at TCA
        cov1, cov2: 3x3 position covariance matrices (km²). If None, uses default uncertainty.
        hbr_m: combined hard-body radius (meters)

    Returns:
        dict with 'pc', 'miss_distance_km', 'covariance_available'
    """
    # Relative position and velocity at TCA
    delta_r = r1 - r2  # km
    delta_v = v1 - v2  # km/s
    miss_distance_km = float(np.linalg.norm(delta_r))

    # Handle case where covariance is not available
    covariance_available = cov1 is not None and cov2 is not None
    if not covariance_available:
        # Default: 1 km 1-sigma along-track, 0.1 km radial, 0.2 km cross-track
        cov1 = np.diag([0.01, 1.0, 0.04])  # km²
        cov2 = np.diag([0.01, 1.0, 0.04])  # km²

    # Combined covariance
    cov_combined = cov1 + cov2  # 3x3, km²

    # Relative velocity unit vector — defines the normal to the conjunction plane
    v_rel = delta_v
    v_rel_norm = np.linalg.norm(v_rel)
    if v_rel_norm < 1e-10:
        return {"pc": 0.0, "miss_distance_km": miss_distance_km, "covariance_available": covariance_available}

    z_hat = v_rel / v_rel_norm  # unit vector along relative velocity

    # Build conjunction plane basis (two vectors perpendicular to z_hat)
    # Use Gram-Schmidt to get x_hat and y_hat
    arbitrary = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(z_hat, arbitrary)) > 0.9:
        arbitrary = np.array([0.0, 1.0, 0.0])
    x_hat = np.cross(z_hat, arbitrary)
    x_hat /= np.linalg.norm(x_hat)
    y_hat = np.cross(z_hat, x_hat)

    # Projection matrix: 3D ECI → 2D conjunction plane
    T = np.array([x_hat, y_hat])  # 2x3

    # Project miss vector into conjunction plane
    miss_2d = T @ delta_r  # 2D miss distance vector in km

    # Project combined covariance into conjunction plane
    C2d = T @ cov_combined @ T.T  # 2x2

    # Hard-body radius in km
    hbr_km = hbr_m / 1000.0

    # Compute Pc via 2D numerical integration of bivariate normal over disk
    pc = _integrate_bivariate_normal_disk(miss_2d, C2d, hbr_km)

    return {
        "pc": float(np.clip(pc, 0.0, 1.0)),
        "miss_distance_km": miss_distance_km,
        "covariance_available": covariance_available,
    }


def _integrate_bivariate_normal_disk(
    mean: np.ndarray,
    cov: np.ndarray,
    radius: float,
) -> float:
    """
    Integrate bivariate normal PDF N(mean, cov) over a disk of given radius centered at origin.
    Uses double numerical integration via scipy.
    """
    try:
        # Cholesky decomposition for efficiency
        try:
            L = np.linalg.cholesky(cov)
        except np.linalg.LinAlgError:
            # Covariance not positive definite — add small regularization
            cov = cov + np.eye(2) * 1e-6
            L = np.linalg.cholesky(cov)

        det_cov = np.linalg.det(cov)
        if det_cov <= 0:
            return 0.0

        inv_cov = np.linalg.inv(cov)
        norm_factor = 1.0 / (2 * np.pi * np.sqrt(det_cov))

        def integrand(y, x):
            pos = np.array([x, y]) - mean
            exponent = -0.5 * pos @ inv_cov @ pos
            return norm_factor * np.exp(exponent)

        def y_lower(x):
            disc = radius**2 - x**2
            if disc < 0:
                return 0.0
            return -np.sqrt(disc)

        def y_upper(x):
            disc = radius**2 - x**2
            if disc < 0:
                return 0.0
            return np.sqrt(disc)

        result, _ = integrate.dblquad(
            integrand,
            -radius, radius,
            y_lower, y_upper,
            epsabs=1e-8, epsrel=1e-6,
            limit=100,
        )
        return result

    except Exception as e:
        logger.error(f"Pc integration failed: {e}")
        # Fallback: Gaussian approximation
        return _pc_gaussian_approx(mean, cov, radius)


def _pc_gaussian_approx(mean, cov, radius):
    """
    Simple approximation: treat as 1D Gaussian using miss distance and combined sigma.
    Less accurate but never crashes.
    """
    from scipy.stats import norm
    miss = np.linalg.norm(mean)
    sigma = np.sqrt(np.mean(np.diag(cov)))
    if sigma < 1e-10:
        return 0.0
    # P(|X - miss| < radius) approximation
    z1 = (miss - radius) / sigma
    z2 = (miss + radius) / sigma
    return float(norm.cdf(z2) - norm.cdf(z1))


def compute_pc_timeline(
    line1_primary: str,
    line2_primary: str,
    line1_secondary: str,
    line2_secondary: str,
    tca_time,
    hbr_m: float = DEFAULT_HBR_M,
    n_points: int = 20,
) -> list[dict]:
    """
    Compute Pc at multiple points leading up to TCA.
    Used for the Pc-vs-time timeline chart in the dashboard.
    """
    from app.services.propagator import tle_to_satrec, propagate_to_datetime
    from datetime import timedelta, timezone

    sat1 = tle_to_satrec(line1_primary, line2_primary)
    sat2 = tle_to_satrec(line1_secondary, line2_secondary)

    if sat1 is None or sat2 is None:
        return []

    tca_utc = tca_time.replace(tzinfo=timezone.utc) if tca_time.tzinfo is None else tca_time
    timeline = []

    # Points: from 72h before TCA to TCA
    max_lead_h = 72
    for i in range(n_points + 1):
        hours_before = max_lead_h * (1 - i / n_points)
        eval_time = tca_utc - timedelta(hours=hours_before)

        r1, v1 = propagate_to_datetime(sat1, eval_time)
        r2, v2 = propagate_to_datetime(sat2, eval_time)

        if r1 is None or r2 is None:
            continue

        pc_result = compute_pc_foster(r1, v1, r2, v2, hbr_m=hbr_m)
        timeline.append({
            "time": eval_time.isoformat(),
            "hours_to_tca": hours_before,
            "pc": pc_result["pc"],
            "miss_distance_km": pc_result["miss_distance_km"],
        })

    return timeline
