import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

BROKER    = "broker.emqx.io"
PORT      = 1883
TOPIC     = "invernadero/G9/sensores/luz"
CLIENT_ID = "G9_luz_01"

UMBRAL_LUZ_BAJA = 300

luz_actual = 400.0

def clasificar_luz(l):
    if l < UMBRAL_LUZ_BAJA:
        return "BAJA"
    elif l > 700:
        return "ALTA"
    return "NORMAL"

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado a {BROKER}:{PORT}")
        print(f"[OK] Publicando en: {TOPIC}")
        print(f"[OK] Umbral luz baja: {UMBRAL_LUZ_BAJA} lux")
        print("-" * 45)
    else:
        print(f"[ERROR] Codigo de conexion: {rc}")

def on_publish(client, userdata, mid, reason_code=None, properties=None):
    print(f"     Mensaje entregado (id={mid})")

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

try:
    while True:
  
        luz_actual += random.uniform(-30, 25)
        luz_actual  = round(max(0.0, min(1000.0, luz_actual)), 1)
        estado      = clasificar_luz(luz_actual)

        payload = json.dumps({
            "valor":              luz_actual,
            "unidad":             "lux",
            "estado":             estado,
            "iluminacion_activa": estado == "BAJA",
            "timestamp":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sensor":             "LDR",
            "area":               "general"
        })

        client.publish(TOPIC, payload, qos=1)

        print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
              f"Luz: {luz_actual} lux  |  Estado: {estado}"
              + ("  -> Luces ON" if estado == "BAJA" else ""))
        print(f"     Payload: {payload}")

        time.sleep(5)

except KeyboardInterrupt:
    print("\n[INFO] Deteniendo luz.py...")
    client.loop_stop()
    client.disconnect()
    print("[INFO] Desconectado")