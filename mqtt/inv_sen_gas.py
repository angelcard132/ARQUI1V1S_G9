import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

BROKER    = "broker.emqx.io"
PORT      = 1883
TOPIC     = "invernadero/G9/sensores/gas"
CLIENT_ID = "G9_gas_01"

UMBRAL_WARN = 200
UMBRAL_EMRG = 400

gas_actual = 120.0

def clasificar_gas(g):
    if g >= UMBRAL_EMRG:
        return "GAS_EMERGENCIA"
    elif g >= UMBRAL_WARN:
        return "GAS_ADVERTENCIA"
    return "GAS_NORMAL"

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado a {BROKER}:{PORT}")
        print(f"[OK] Publicando en: {TOPIC}")
        print(f"[OK] Umbral advertencia: {UMBRAL_WARN} ppm")
        print(f"[OK] Umbral emergencia:  {UMBRAL_EMRG} ppm")
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
        gas_actual += random.uniform(-8, 12)
        gas_actual  = round(max(50.0, min(600.0, gas_actual)), 1)
        estado      = clasificar_gas(gas_actual)

        payload = json.dumps({
            "valor":             gas_actual,
            "unidad":            "ppm",
            "estado":            estado,
            "alarma_activa":     estado == "GAS_EMERGENCIA",
            "ventilador_activo": estado in ("GAS_ADVERTENCIA", "GAS_EMERGENCIA"),
            "timestamp":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sensor":            "MQ-2",
            "area":              "general"
        })

        client.publish(TOPIC, payload, qos=1)

        prefijo = ""
        if estado == "GAS_EMERGENCIA":
            prefijo = "  *** EMERGENCIA ***"
        elif estado == "GAS_ADVERTENCIA":
            prefijo = "  * ADVERTENCIA"

        print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
              f"Gas: {gas_actual} ppm  |  {estado}{prefijo}")
        print(f"     Payload: {payload}")

        time.sleep(5)

except KeyboardInterrupt:
    print("\n[INFO] Deteniendo gas.py...")
    client.loop_stop()
    client.disconnect()
    print("[INFO] Desconectado")