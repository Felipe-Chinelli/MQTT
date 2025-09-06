from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str # Será hashed no backend

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

# --- Device Schemas ---
class DeviceBase(BaseModel):
    device_id_mqtt: str
    name: Optional[str] = None
    location: Optional[str] = None

class DeviceCreate(DeviceBase):
    owner_id: int # ID do usuário proprietário

class Device(DeviceBase):
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- MotionEvent Schemas ---
class MotionEventBase(BaseModel):
    event_type: str
    status: str
    timestamp_device: str # String do timestamp do dispositivo

class MotionEventCreate(MotionEventBase):
    device_id_mqtt: str # Usado para encontrar o Device no DB, não o FK direto

class MotionEvent(MotionEventBase):
    id: int
    device_id: int
    timestamp_server: datetime

    class Config:
        from_attributes = True