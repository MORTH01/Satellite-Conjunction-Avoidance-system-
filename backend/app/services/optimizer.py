"""
Maneuver optimizer: finds minimum delta-v burn to reduce Pc below threshold.
Uses scipy SLSQP with the Pc function as constraint.

RTN (Radial-Tangential-Normal) frame:
  R = radial outward
  T = along-track (tangential)
  N = normal to orbit plane
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import numpy as np
from scipy.optimize import minimize

from app.services.propagator import tle_to_satrec, propagate_to_datetime
from app.services.pc_calculator import compute_pc_foster
from app.core.config import settings

logger = logging.getLogger(__name__)

PC_TARGET = 1e-5  # Target Pc after maneuver (10x below alert threshold)
MAX_DV_MS = 10.0  # Maximum allowed delta-v in m/s (10 m/s is generous for CubeSat)


def eci_to_rtn(r: np.ndarray, v: np.ndarray) -> np.ndarray:
    """
    Build RTN (Radial-Tangential-Normal) rotation matrix from ECI.
    Returns 3x3 matrix: R_hat, T_hat, N_hat as rows.
    """
    r_hat = r / np.linalg.norm(r)               # Radial unit vector
    h = np.cross(r, v)                          # Angular momentum
    n_hat = h / np.linalg.norm(h)              # Normal to orbit plane
    t_hat = np.cross(n_hat, r_hat)             # Tangential (along-track)
    return np.array([r_hat, t_hat, n_hat])     # 3x3


def apply_burn_and_propagate(
    sat1_line1: str, sat1_line2: str,
    sat2_line1: str, sat2_line2: str,
    burn_epoch: datetime,
    delta_v_rtn_ms: np.ndarray,  # [R, T, N] in m/s
    tca_time: datetime,
    hbr_m: float = 10.0,
) -> dict:
    """
    Apply an impulsive burn to sat1 at burn_epoch, then propagate both sats to TCA.
    Returns Pc result after burn.
    """
    sat1 = tle_to_satrec(sat1_line1, sat1_line2)
    sat2 = tle_to_satrec(sat2_line1, sat2_line2)

    if sat1 is None or sat2 is None:
        return {"pc": 1.0, "miss_distance_km": 0.0}

    burn_utc = burn_epoch.replace(tzinfo=timezone.utc) if burn_epoch.tzinfo is None else burn_epoch
    tca_utc = tca_time.replace(tzinfo=timezone.utc) if tca_time.tzinfo is None else tca_time

    # Get state at burn epoch
    r_burn, v_burn = propagate_to_datetime(sat1, burn_utc)
    if r_burn is None:
        return {"pc": 1.0, "miss_distance_km": 0.0}

    # Convert RTN delta-v to ECI
    rtn_matrix = eci_to_rtn(r_burn, v_burn)
    delta_v_eci_ms = rtn_matrix.T @ delta_v_rtn_ms  # 3D ECI m/s
    delta_v_eci_km_s = delta_v_eci_ms / 1000.0

    # Post-burn velocity
    v_post = v_burn + delta_v_eci_km_s

    # Propagate post-burn using two-body Kepler (simplified)
    # For the short time to TCA, use linearized approximation
    dt_s = (tca_utc - burn_utc).total_seconds()

    # State transition: x(t) = x0 + v*dt (linear, valid for short intervals)
    # More accurate: integrate two-body equations, but for demo this is sufficient
    r_post_at_tca = r_burn + v_post * dt_s  # rough ECI position at TCA

    # Get secondary at TCA using SGP4
    r2, v2 = propagate_to_datetime(sat2, tca_utc)
    if r2 is None:
        return {"pc": 1.0, "miss_distance_km": 0.0}

    pc_result = compute_pc_foster(r_post_at_tca, v_post, r2, v2, hbr_m=hbr_m)
    return pc_result


def optimize_maneuver(
    line1_primary: str,
    line2_primary: str,
    line1_secondary: str,
    line2_secondary: str,
    tca_time: datetime,
    lead_times_h: list[float] = [24.0, 48.0, 72.0],
    hbr_m: float = 10.0,
) -> list[dict]:
    """
    Find minimum-delta-v maneuver for each lead time.
    Returns list of burn plans sorted by delta-v cost.
    """
    tca_utc = tca_time.replace(tzinfo=timezone.utc) if tca_time.tzinfo is None else tca_time
    burn_plans = []

    for lead_h in lead_times_h:
        burn_epoch = tca_utc - timedelta(hours=lead_h)

        sat1 = tle_to_satrec(line1_primary, line2_primary)
        if sat1 is None:
            continue

        # Get state at burn epoch for RTN frame
        r_burn, v_burn = propagate_to_datetime(sat1, burn_epoch)
        if r_burn is None:
            continue

        # Current Pc (pre-burn)
        sat2 = tle_to_satrec(line1_secondary, line2_secondary)
        if sat2 is None:
            continue
        r2_tca, v2_tca = propagate_to_datetime(sat2, tca_utc)
        r1_tca, v1_tca = propagate_to_datetime(sat1, tca_utc)
        if r1_tca is None or r2_tca is None:
            continue
        pc_pre = compute_pc_foster(r1_tca, v1_tca, r2_tca, v2_tca, hbr_m=hbr_m)["pc"]

        def objective(dv):
            """Minimize ||Δv||"""
            return np.linalg.norm(dv)

        def pc_constraint(dv):
            """Pc must be below target after burn"""
            result = apply_burn_and_propagate(
                line1_primary, line2_primary,
                line1_secondary, line2_secondary,
                burn_epoch, np.array(dv),
                tca_utc, hbr_m,
            )
            # Returns positive when constraint satisfied (Pc <= target)
            return PC_TARGET - result["pc"]

        # Initial guess: small tangential burn
        x0 = np.array([0.0, 0.5, 0.0])  # 0.5 m/s tangential

        constraints = [{"type": "ineq", "fun": pc_constraint}]
        bounds = [(-MAX_DV_MS, MAX_DV_MS)] * 3

        try:
            result = minimize(
                objective,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 100, "ftol": 1e-6},
            )

            if result.success or result.fun < MAX_DV_MS:
                dv_opt = np.array(result.x)
                dv_mag = float(np.linalg.norm(dv_opt))

                # Verify post-burn Pc
                post_result = apply_burn_and_propagate(
                    line1_primary, line2_primary,
                    line1_secondary, line2_secondary,
                    burn_epoch, dv_opt, tca_utc, hbr_m,
                )

                burn_plans.append({
                    "burn_epoch": burn_epoch,
                    "burn_rtn_ms": dv_opt.tolist(),
                    "delta_v_ms": round(dv_mag, 4),
                    "pc_post_burn": post_result["pc"],
                    "lead_time_h": lead_h,
                    "pc_pre_burn": pc_pre,
                    "success": result.success,
                })
                logger.info(
                    f"Burn plan {lead_h}h: Δv={dv_mag:.4f} m/s "
                    f"Pc: {pc_pre:.2e} → {post_result['pc']:.2e}"
                )
            else:
                logger.warning(f"Optimizer did not converge for {lead_h}h lead time")
                burn_plans.append({
                    "burn_epoch": burn_epoch,
                    "burn_rtn_ms": [0.0, 0.0, 0.0],
                    "delta_v_ms": 0.0,
                    "pc_post_burn": pc_pre,
                    "lead_time_h": lead_h,
                    "pc_pre_burn": pc_pre,
                    "success": False,
                })

        except Exception as e:
            logger.error(f"Optimizer error for {lead_h}h: {e}")

    # Sort by delta-v cost (ascending)
    burn_plans.sort(key=lambda x: x["delta_v_ms"])
    return burn_plans
