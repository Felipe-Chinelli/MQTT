# crud.py
from sqlalchemy.orm import Session
import models, schemas # De from . import models, schemas
import bcrypt
from typing import Optional

# ... o restante do seu crud.py permanece o mesmo ...

# --- User CRUD ---
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    # Hash da senha antes de armazenar
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Device CRUD ---
def get_device(db: Session, device_id: int):
    return db.query(models.Device).filter(models.Device.id == device_id).first()

def get_device_by_mqtt_id(db: Session, device_id_mqtt: str):
    return db.query(models.Device).filter(models.Device.device_id_mqtt == device_id_mqtt).first()

def get_devices(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Device).offset(skip).limit(limit).all()

def create_device(db: Session, device: schemas.DeviceCreate):
    db_device = models.Device(
        device_id_mqtt=device.device_id_mqtt,
        name=device.name,
        location=device.location,
        owner_id=device.owner_id
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

# --- MotionEvent CRUD ---
def create_motion_event(db: Session, event: schemas.MotionEventCreate):
    db_device = get_device_by_mqtt_id(db, event.device_id_mqtt)
    if not db_device:
        print(f"Dispositivo MQTT ID '{event.device_id_mqtt}' não encontrado. Evento não armazenado.")
        return None # Retorna None se o dispositivo não existir

    db_event = models.MotionEvent(
        device_id=db_device.id,
        event_type=event.event_type,
        status=event.status,
        timestamp_device=event.timestamp_device
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def get_motion_events(db: Session, device_id: Optional[int] = None, skip: int = 0, limit: int = 100):
    query = db.query(models.MotionEvent)
    if device_id:
        query = query.filter(models.MotionEvent.device_id == device_id)
    return query.offset(skip).limit(limit).all()