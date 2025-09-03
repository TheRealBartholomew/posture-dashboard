from sqlalchemy import Column, Integer, String, Float, Boolean, TIMESTAMP, ForeignKey, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    baseline_angle = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    posture_readings = relationship("PostureReading", back_populates="user", cascade="all, delete-orphan")
    calibrate_sessions = relationship("CalibrateSession", back_populates="user", cascade="all, delete-orphan")
    notification_settings = relationship("NotificationSettings", back_populates="user", uselist=False)

class PostureReading(Base):
    __tablename__ = "posture_readings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(TIMESTAMP, server_default=func.now())
    angle = Column(Float)
    quality_score = Column(Integer) # 1 to 5
    posture = Column(String, nullable=True)  # "good", "warning", "bad"

    user = relationship("User", back_populates="posture_readings") 

class CalibrateSession(Base):
    __tablename__ = "calibrate_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    baseline_angle = Column(Float, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="calibrate_sessions")

class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    enabled = Column(Boolean, default=True)
    threshold_angle = Column(Float, default=30.0)
    notification_interval = Column(Integer, default=300) # in sec
    quiet_hours_start = Column(Time, nullable=True)
    quiet_hours_end = Column(Time, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())  # auto timestamp when created
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())  # auto update timestamp

    user = relationship("User", back_populates="notification_settings")