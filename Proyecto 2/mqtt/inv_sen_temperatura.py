import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

# ── Configuracion ──────────────────────────────────
BROKER   = "broker.emqx.io"
PORT     = 1883
TOPIC    = "invernadero/G9/sensores/temperatura"
CLIENT_ID = "G9_temperatura_01"

# Simula temperatura que varia entre 24 y 35 grados
temp_actual = 27.0

# ── Callbacks ──────────────────────────────────────
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado al broker {BROKER}")
        print(f"[OK] Publicando en: {TOPIC}")
        print("-" * 45)
    else:
        print(f"[ERROR] No se pudo conectar. Codigo: {rc}")

def on_publish(client, userdata, mid, reason_code=None, properties=None):
    print(f"     Mensaje entregado al broker (id={mid})")

# ── Conexion ───────────────────────────────────────
client = mqtt.Client(
    client_id=CLIENT_ID,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)
client.on_connect = on_connect
client.on_publish = on_publish

print(f"Conectando a {BROKER}:{PORT}...")
client.connect(BROKER, PORT, keepalive=60)
client.loop_start()

time.sleep(1)  # esperar que se establezca la conexion

# ── Loop de publicacion ────────────────────────────
try:
 while True:
    # Variacion realista de temperatura
    temp_actual += random.uniform(-0.5, 0.8)
    temp_actual = round(max(20.0, min(38.0, temp_actual)), 1)

    payload = json.dumps({
        "valor":     temp_actual,
        "unidad":    "C",
        "estado":    "ALTA" if temp_actual >= 30 else "NORMAL",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sensor":    "DHT22",
        "area":      "general"
    })

    result = client.publish(TOPIC, payload, qos=1)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
          f"Temperatura: {temp_actual}°C  "
          f"{' ALTA' if temp_actual >= 30 else ' Normal'}")

    time.sleep(5)

except KeyboardInterrupt:
    print("\n[Main] Deteniendo temperatura.py...")
    client.loop_stop()
    client.disconnect()
    print("[Main] Desconectado correctamente")