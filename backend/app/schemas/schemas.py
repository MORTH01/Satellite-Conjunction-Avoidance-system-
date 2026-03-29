from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class SatelliteBase(BaseModel):
    norad_id: int
    name: str
    classification: Optional[str] = "U"
    object_type: Optional[str] = None
    country: Optional[str] = None


class SatelliteOut(SatelliteBase):
    id: int
    is_active: bool
    updated_at: datetime

    class Config:
        from_attributes = True


class TLERecordOut(BaseModel):
    id: int
    satellite_id: int
    epoch: datetime
    line1: str
    line2: str
    inclination: Optional[float]
    eccentricity: Optional[float]
    perigee_km: Optional[float]
    apogee_km: Optional[float]
    ingested_at: datetime

    class Config:
        from_attributes = True


class BurnPlan(BaseModel):
    burn_epoch: Optional[datetime]
    burn_rtn_ms: Optional[List[float]]   # [R, T, N] components
    delta_v_ms: Optional[float]
    pc_post_burn: Optional[float]
    lead_time_h: Optional[float]


class ConjunctionEventOut(BaseModel):
    id: int
    primary_sat_id: int
    secondary_sat_id: int
    primary_name: Optional[str] = None
    secondary_name: Optional[str] = None
    primary_norad: Optional[int] = None
    secondary_norad: Optional[int] = None
    tca_time: datetime
    miss_distance_km: float
    relative_speed_km_s: Optional[float]
    pc: float
    pc_method: str
    covariance_available: bool
    pc_history: Optional[List[Any]] = []
    optimal_burn_epoch: Optional[datetime]
    burn_rtn_ms: Optional[List[float]]
    burn_delta_v_ms: Optional[float]
    pc_post_burn: Optional[float]
    burn_lead_time_h: Optional[float]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConjunctionListItem(BaseModel):
    id: int
    primary_sat_id: int
    secondary_sat_id: int
    primary_name: Optional[str] = None
    secondary_name: Optional[str] = None
    primary_norad: Optional[int] = None
    secondary_norad: Optional[int] = None
    tca_time: datetime
    miss_distance_km: float
    pc: float
    status: str
    has_burn_plan: bool = False

    class Config:
        from_attributes = True


class OptimizeRequest(BaseModel):
    lead_times_h: List[float] = Field(default=[24.0, 48.0, 72.0])


class OptimizeResponse(BaseModel):
    event_id: int
    burn_plans: List[BurnPlan]
    best_plan: BurnPlan
    message: str


class ScreeningRunOut(BaseModel):
    id: str
    started_at: datetime
    completed_at: Optional[datetime]
    satellites_screened: int
    pairs_evaluated: int
    events_found: int
    high_pc_events: int
    status: str

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


class AlertMessage(BaseModel):
    type: str  # "new_conjunction" | "screening_complete" | "optimizer_done"
    event_id: Optional[int] = None
    pc: Optional[float] = None
    primary_name: Optional[str] = None
    secondary_name: Optional[str] = None
    tca_time: Optional[datetime] = None
    message: str
