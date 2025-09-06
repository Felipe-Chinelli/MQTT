import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
import time

load_dotenv() # Carrega variáveis de ambiente do .env

# --- Configurações de E-mail (do .env) ---
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD") # Senha de app para Gmail ou senha normal
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# Cooldown para evitar spam. Em produção, este estado deveria ser persistido (ex: em Redis ou DB)
# para sobreviver a reinícios do servidor.
_server_email_cooldowns = {}
COOLDOWN_PERIOD_SECONDS = 300 # 5 minutos

def send_motion_alert_email(receiver_email: str, device_name: str, device_id_mqtt: str, motion_status: str) -> bool:
    """Envia um e-mail de alerta de movimento, respeitando um período de cooldown."""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("Erro: Credenciais de e-mail não configuradas. Verifique o arquivo .env.")
        return False

    current_time = time.time()
    # Verifica se o dispositivo está em cooldown
    if device_id_mqtt in _server_email_cooldowns and \
       (current_time - _server_email_cooldowns[device_id_mqtt] < COOLDOWN_PERIOD_SECONDS):
        print(f"E-mail de alerta para '{device_id_mqtt}' em cooldown. Não enviado.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = f"Alerta de Movimento: {device_name} detectou {motion_status}!"

        html_content = f"""\
        <html>
          <body>
            <p>Olá,</p>
            <p>Seu sensor <b>{device_name}</b> (ID MQTT: {device_id_mqtt}) detectou <b>{motion_status}</b>.</p>
            <p>Verifique a situação se necessário.</p>
            <p>Atenciosamente,<br>Seu Sistema de Monitoramento</p>
            <p><small>Este e-mail foi enviado automaticamente. Por favor, não responda.</small></p>
          </body>
        </html>
        """
        part1 = MIMEText(html_content, "html")
        msg.attach(part1)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Habilita segurança TLS
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        
        _server_email_cooldowns[device_id_mqtt] = current_time # Atualiza o tempo do último envio para este dispositivo
        print(f"E-mail de alerta enviado para {receiver_email} sobre o dispositivo {device_name}.")
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail para {receiver_email}: {e}")
        return False