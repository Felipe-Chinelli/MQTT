#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h> // Instale esta biblioteca via PlatformIO ou Arduino IDE

// --- Configurações da sua rede Wi-Fi ---
const char* ssid = "SEU_SSID";
const char* password = "SUA_SENHA_WIFI";

// --- Configurações do Broker MQTT ---
const char* mqtt_server = "broker.hivemq.com"; // Utilize um broker público ou seu próprio
const int mqtt_port = 1883;
const char* mqtt_user = ""; // Preencha se o broker exigir
const char* mqtt_password = ""; // Preencha se o broker exigir

// --- ID ÚNICO DO DISPOSITIVO E TÓPICO MQTT ---
// É CRUCIAL que cada dispositivo tenha um DEVICE_ID ÚNICO.
// Este ID será usado no backend para identificar o sensor e associá-lo a um usuário.
const char* DEVICE_ID = "ESP32_PIR_001"; // <<< !!! MUDE ISSO PARA CADA DISPOSITIVO !!!
char mqtt_topic_publish[60]; // Buffer para o tópico completo (ex: sensors/ESP32_PIR_001/events)

// --- Pino do sensor PIR ---
const int pirPin = 2; // Exemplo: Pino GPIO2 no ESP32. Adapte conforme sua conexão.

// --- Variáveis para controle do sensor e MQTT ---
bool motionDetected = false;
unsigned long lastMotionChangeTime = 0; // Timestamp da última mudança de estado (HIGH para LOW ou vice-versa)
const unsigned long DEBOUNCE_DELAY = 500; // Milissegundos para debounce: tempo mínimo para considerar uma mudança de estado

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi conectado");
  Serial.println("Endereço IP: ");
  Serial.println(WiFi.localIP());
}

void reconnect_mqtt() {
  while (!client.connected()) {
    Serial.print("Tentando conexão MQTT...");
    // Crie um ID de cliente MQTT aleatório para evitar conflitos
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_password)) {
      Serial.println("conectado");
    } else {
      Serial.print("falha, rc=");
      Serial.print(client.state());
      Serial.println(" tentando novamente em 5 segundos");
      delay(5000);
    }
  }
}

// Função para publicar um evento MQTT
void publish_motion_event(const char* status) {
  StaticJsonDocument<200> doc; // Alocar documento JSON na stack
  doc["device_id"] = DEVICE_ID;
  doc["event_type"] = "motion";
  doc["status"] = status;
  doc["timestamp_device"] = String(millis()); // Timestamp do dispositivo

  char jsonBuffer[200];
  serializeJson(doc, jsonBuffer); // Serializa o JSON para um buffer
  client.publish(mqtt_topic_publish, jsonBuffer);
  Serial.print("Publicado no MQTT: ");
  Serial.println(jsonBuffer);
}

void setup() {
  Serial.begin(115200);
  pinMode(pirPin, INPUT_PULLUP); // Define o pino do PIR como entrada. [1]
  
  // Constrói o tópico de publicação com o DEVICE_ID
  sprintf(mqtt_topic_publish, "sensors/%s/events", DEVICE_ID);

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  // Não precisamos de callback de mensagem, pois o ESP32 só publica
}

void loop() {
  if (!client.connected()) {
    reconnect_mqtt();
  }
  client.loop(); // Mantém a conexão MQTT ativa. [7]

  int pirState = digitalRead(pirPin); // Lê o estado do sensor PIR. [6]
  unsigned long currentTime = millis();

  if (pirState == HIGH) { // Movimento Detectado
    if (!motionDetected && (currentTime - lastMotionChangeTime > DEBOUNCE_DELAY)) {
      publish_motion_event("DETECTED");
      motionDetected = true;
      lastMotionChangeTime = currentTime;
    }
  } else { // Nenhum Movimento
    if (motionDetected && (currentTime - lastMotionChangeTime > DEBOUNCE_DELAY)) {
      publish_motion_event("NO_MOTION");
      motionDetected = false;
      lastMotionChangeTime = currentTime;
    }
  }
  delay(100); // Pequeno atraso para estabilidade
}