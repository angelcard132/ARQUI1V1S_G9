import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

# ── Configuracion ──────────────────────────────────
BROKER    = "broker.emqx.io"
PORT      = 1883
TOPIC     = "invernadero/G9/sensores/humedad_ambiente"
CLIENT_ID = "G9_humedad_ambiente_01"

hum_actual = 65.0

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

time.sleep(1)

# ── Loop de publicacion ────────────────────────────
def clasificar_humedad(h):
    if h < 40:
        return "BAJA"
    elif h > 80:
        return "ALTA"
    return "NORMAL"

try:
    while True:
        hum_actual += random.uniform(-1.0, 1.0)
        hum_actual  = round(max(20.0, min(95.0, hum_actual)), 1)
        estado      = clasificar_humedad(hum_actual)

        payload = json.dumps({
            "valor":     hum_actual,
            "unidad":    "%",
            "estado":    estado,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sensor":    "DHT22",
            "area":      "general"
        })

        client.publish(TOPIC, payload, qos=1)

        icono = "si" if estado == "NORMAL" else "no"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
              f"Humedad: {hum_actual}%  {icono} {estado}")
        print(f"     Payload: {payload}")

        time.sleep(5)

except KeyboardInterrupt:
    print("\n[Main] Deteniendo humedad_ambiente.py...")
    client.loop_stop()
    client.disconnect()
    print("[Main] Desconectado correctamente")