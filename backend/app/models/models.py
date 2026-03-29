from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Boolean,
    ForeignKey, Text, JSON, BigInteger, Index
)
from sqlalchemy.orm import relationship
from app.db.session import Base


class Satellite(Base):
    __tablename__ = "satellites"

    id = Column(Integer, primary_key=True, index=True)
    norad_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    classification = Column(String(1), default="U")  # U=unclassified, C=classified, S=secret
    intl_designator = Column(String(20))
    object_type = Column(String(20))  # PAYLOAD, ROCKET BODY, DEBRIS, etc.
    country = Column(String(10))
    launch_date = Column(DateTime, nullable=True)
    decay_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tle_records = relationship("TLERecord", back_populates="satellite", cascade="all, delete-orphan")
    primary_conjunctions = relationship("ConjunctionEvent", foreign_keys="ConjunctionEvent.primary_sat_id", back_populates="primary_satellite")
    secondary_conjunctions = relationship("ConjunctionEvent", foreign_keys="ConjunctionEvent.secondary_sat_id", back_populates="secondary_satellite")


class TLERecord(Base):
    __tablename__ = "tle_records"

    id = Column(BigInteger, primary_key=True, index=True)
    satellite_id = Column(Integer, ForeignKey("satellites.id"), nullable=False)
    epoch = Column(DateTime, nullable=False)
    line1 = Column(String(70), nullable=False)
    line2 = Column(String(70), nullable=False)
    mean_motion = Column(Float)
    eccentricity = Column(Float)
    inclination = Column(Float)
    raan = Column(Float)
    arg_perigee = Column(Float)
    mean_anomaly = Column(Float)
    bstar = Column(Float)
    perigee_km = Column(Float)
    apogee_km = Column(Float)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    is_latest = Column(Boolean, default=True)

    satellite = relationship("Satellite", back_populates="tle_records")

    __table_args__ = (
        Index("idx_tle_satellite_latest", "satellite_id", "is_latest"),
        Index("idx_tle_epoch", "epoch"),
    )


class ConjunctionEvent(Base):
    __tablename__ = "conjunction_events"

    id = Column(BigInteger, primary_key=True, index=True)
    primary_sat_id = Column(Integer, ForeignKey("satellites.id"), nullable=False)
    secondary_sat_id = Column(Integer, ForeignKey("satellites.id"), nullable=False)

    # TCA data
    tca_time = Column(DateTime, nullable=False)
    miss_distance_km = Column(Float, nullable=False)
    relative_speed_km_s = Column(Float)

    # Pc calculation
    pc = Column(Float, nullable=False)
    pc_method = Column(String(20), default="foster")
    covariance_available = Column(Boolean, default=False)
    pc_history = Column(JSON, default=list)  # [{time, pc}, ...] for timeline chart

    # Maneuver optimization result
    optimal_burn_epoch = Column(DateTime, nullable=True)
    burn_rtn_ms = Column(JSON, nullable=True)        # [radial, tangential, normal] m/s
    burn_delta_v_ms = Column(Float, nullable=True)   # ||Δv|| magnitude
    pc_post_burn = Column(Float, nullable=True)
    burn_lead_time_h = Column(Float, nullable=True)

    # Status
    status = Column(String(20), default="active")   # active, resolved, maneuvered, expired
    alert_sent = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    # Screening metadata
    screen_run_id = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    primary_satellite = relationship("Satellite", foreign_keys=[primary_sat_id], back_populates="primary_conjunctions")
    secondary_satellite = relationship("Satellite", foreign_keys=[secondary_sat_id], back_populates="secondary_conjunctions")

    __table_args__ = (
        Index("idx_conj_primary_tca", "primary_sat_id", "tca_time"),
        Index("idx_conj_status", "status"),
        Index("idx_conj_pc", "pc"),
    )


class ScreeningRun(Base):
    __tablename__ = "screening_runs"

    id = Column(String(36), primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    satellites_screened = Column(Integer, default=0)
    pairs_evaluated = Column(Integer, default=0)
    events_found = Column(Integer, default=0)
    high_pc_events = Column(Integer, default=0)
    status = Column(String(20), default="running")  # running, completed, failed
    error_message = Column(Text, nullable=True)
