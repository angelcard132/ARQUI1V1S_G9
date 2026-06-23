import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

BROKER    = "broker.emqx.io"
PORT      = 1883
TOPIC     = "invernadero/G9/sensores/humedad_suelo_area2"
CLIENT_ID = "G9_suelo_area2_01"

suelo2 = 62.0

def clasificar_suelo(h):
    if h < 35:
        return "SECO"
    elif h > 80:
        return "SATURADO"
    return "NORMAL"

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado a {BROKER}:{PORT}")
        print(f"[OK] Publicando en: {TOPIC}")
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
       
        suelo2 += random.uniform(-1.2, 0.4)
        suelo2  = round(max(10.0, min(95.0, suelo2)), 1)
        estado  = clasificar_suelo(suelo2)

        payload = json.dumps({
            "valor":        suelo2,
            "unidad":       "%",
            "estado":       estado,
            "riego_activo": estado == "SECO",
            "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sensor":       "FC-28",
            "area":         "area2"
        })

        client.publish(TOPIC, payload, qos=1)

        print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
              f"Suelo Area 2: {suelo2}%  |  Estado: {estado}")
        print(f"     Payload: {payload}")

        time.sleep(5)

except KeyboardInterrupt:
    print("\n[INFO] Deteniendo humedad_suelo_area2.py...")
    client.loop_stop()
    client.disconnect()
    print("[INFO] Desconectado")