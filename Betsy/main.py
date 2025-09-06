# main.py
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import paho.mqtt.client as mqtt
import json
import time
import os
from dotenv import load_dotenv

# --- Alterações AQUI ---
import models, schemas, crud # De from . import models, schemas, crud
from database import SessionLocal, engine, get_db # De from .database import ...
from email_service import send_motion_alert_email, COOLDOWN_PERIOD_SECONDS # De from .email_service import ...


# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Crie todas as tabelas no banco de dados (se não existirem)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MQTT Sensor API",
    description="API para receber eventos de sensores via MQTT, armazenar no DB e enviar alertas por email.",
    version="1.0.0"
)

# --- Configurações MQTT (obtidas do .env) ---
# ...
# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

print(f"DEBUG: MQTT_BROKER_HOST={os.getenv('MQTT_BROKER_HOST')}")
print(f"DEBUG: MQTT_BROKER_PORT={os.getenv('MQTT_BROKER_PORT')}")
print(f"DEBUG: SENDER_EMAIL={os.getenv('SENDER_EMAIL')}")
print(f"DEBUG: SMTP_PORT={os.getenv('SMTP_PORT')}") # Verifique também a do email service

# --- Configurações MQTT (obtidas do .env) ---
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "broker.hivemq.com") # Adiciona um default host também
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883")) # <<< ALTERADO AQUI: adiciona o default "1883"
MQTT_TOPIC_SUBSCRIBE = os.getenv("MQTT_TOPIC_SUBSCRIBE", "sensors/+/events") # Adiciona um default também
# ...

# Cliente MQTT global
mqtt_client = mqtt.Client()

# --- Funções de Callback MQTT ---
def on_connect(client, userdata, flags, rc):
    """Callback quando o cliente se conecta ao broker MQTT."""
    if rc == 0:
        print(f"MQTT Conectado ao broker: {MQTT_BROKER_HOST}")
        client.subscribe(MQTT_TOPIC_SUBSCRIBE)
        print(f"MQTT Assinado no tópico: {MQTT_TOPIC_SUBSCRIBE}")
    else:
        print(f"Falha na conexão MQTT com código: {rc}")

def on_message(client, userdata, msg):
    """Callback quando uma mensagem é recebida do broker MQTT."""
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode('utf-8'))
        print(f"MQTT Mensagem recebida: Tópico='{topic}', Payload={payload}")

        device_id_mqtt = payload.get("device_id")
        event_type = payload.get("event_type")
        status = payload.get("status")
        timestamp_device = payload.get("timestamp_device") # Alterado para corresponder ao ESP32

        if not all([device_id_mqtt, event_type, status, timestamp_device]):
            print(f"Dados incompletos no payload do evento: {payload}")
            return

        # Criar uma sessão de DB para esta operação de thread
        db = SessionLocal()
        try:
            # 1. Registrar o evento no DB
            motion_event_schema = schemas.MotionEventCreate(
                device_id_mqtt=device_id_mqtt,
                event_type=event_type,
                status=status,
                timestamp_device=timestamp_device
            )
            created_event = crud.create_motion_event(db, motion_event_schema)
            if created_event:
                print(f"Evento de movimento armazenado para o dispositivo {device_id_mqtt}.")

                # 2. Verificar e enviar e-mail de alerta, se aplicável
                if status == "DETECTED": # Apenas envia e-mail para detecções de movimento
                    device_in_db = crud.get_device_by_mqtt_id(db, device_id_mqtt)
                    if device_in_db and device_in_db.owner:
                        user_email = device_in_db.owner.email
                        device_name = device_in_db.name or device_in_db.device_id_mqtt
                        
                        # A função send_motion_alert_email já contém a lógica de cooldown.
                        send_motion_alert_email(user_email, device_name, device_id_mqtt, status)
                    else:
                        print(f"Dispositivo '{device_id_mqtt}' não encontrado ou não tem proprietário para alerta de e-mail.")
            else:
                print(f"Falha ao armazenar evento para o dispositivo {device_id_mqtt}.")

        finally:
            db.close()

    except json.JSONDecodeError:
        print(f"Falha ao decodificar payload JSON: {msg.payload.decode('utf-8')}")
    except Exception as e:
        print(f"Erro ao processar mensagem MQTT: {e}")

# --- Eventos de Ciclo de Vida do FastAPI ---
@app.on_event("startup")
async def startup_event():
    """Executado quando a aplicação FastAPI inicia."""
    print("Iniciando aplicação FastAPI...")
    # Iniciar o cliente MQTT em um thread separado (usando asyncio para não bloquear o servidor)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    # Conectar o cliente MQTT e iniciar o loop em um executor para não bloquear o loop principal do FastAPI.
    # Isso permite que o FastAPI continue a servir requisições HTTP enquanto o MQTT escuta em background.
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, lambda: mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60))
    loop.run_in_executor(None, mqtt_client.loop_forever)
    print("Cliente MQTT iniciado em segundo plano.")

@app.on_event("shutdown")
def shutdown_event():
    """Executado quando a aplicação FastAPI desliga."""
    print("Desligando aplicação FastAPI...")
    mqtt_client.disconnect()
    print("Cliente MQTT desconectado.")

# --- Endpoints da API ---

@app.get("/", summary="Endpoint raiz", response_description="Mensagem de boas-vindas")
async def read_root():
    return {"message": "Bem-vindo à API de Sensor MQTT!"}

# --- User Endpoints ---
@app.post("/users/", response_model=schemas.User, status_code=201, summary="Cria um novo usuário")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="E-mail já registrado")
    return crud.create_user(db=db, user=user)

@app.get("/users/", response_model=List[schemas.User], summary="Obtém todos os usuários")
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@app.get("/users/{user_id}", response_model=schemas.User, summary="Obtém usuário por ID")
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return db_user

# --- Device Endpoints ---
@app.post("/devices/", response_model=schemas.Device, status_code=201, summary="Registra um novo dispositivo")
def create_device_for_user(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    # Verifica se o owner_id existe
    db_user = crud.get_user(db, user_id=device.owner_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuário proprietário não encontrado")
    
    # Verifica se o device_id_mqtt já existe
    existing_device = crud.get_device_by_mqtt_id(db, device.device_id_mqtt)
    if existing_device:
        raise HTTPException(status_code=400, detail="Dispositivo com este ID MQTT já registrado")

    return crud.create_device(db=db, device=device)

@app.get("/devices/", response_model=List[schemas.Device], summary="Obtém todos os dispositivos registrados")
def read_devices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    devices = crud.get_devices(db, skip=skip, limit=limit)
    return devices

@app.get("/devices/{device_id}", response_model=schemas.Device, summary="Obtém dispositivo por ID")
def read_device(device_id: int, db: Session = Depends(get_db)):
    db_device = crud.get_device(db, device_id=device_id)
    if db_device is None:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")
    return db_device

# --- Motion Events Endpoints ---
@app.get("/motion_events/", response_model=List[schemas.MotionEvent], summary="Obtém eventos de movimento")
def read_motion_events(
    device_id: Optional[int] = None, # Filtra por ID do dispositivo (ID numérico do DB)
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    events = crud.get_motion_events(db, device_id=device_id, skip=skip, limit=limit)
    return events