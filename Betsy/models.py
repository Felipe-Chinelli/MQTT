# models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base # De from .database import Base

# ... o restante do seu models.py permanece o mesmo ...

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False) # Para autenticação futura
    is_active = Column(Boolean, default=True)

    devices = relationship("Device", back_populates="owner")

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id_mqtt = Column(String, unique=True, index=True, nullable=False) # ID usado no MQTT (ESP32)
    name = Column(String, default="Unknown Device")
    location = Column(String, default="General")
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    owner = relationship("User", back_populates="devices")
    motion_events = relationship("MotionEvent", back_populates="device")

class MotionEvent(Base):
    __tablename__ = "motion_events"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    event_type = Column(String, default="motion") # Ex: "motion"
    status = Column(String, nullable=False) # Ex: "DETECTED", "NO_MOTION"
    timestamp_device = Column(Text, nullable=False) # Timestamp como string enviado pelo dispositivo
    timestamp_server = Column(DateTime(timezone=True), server_default=func.now()) # Timestamp do servidor

    device = relationship("Device", back_populates="motion_events")