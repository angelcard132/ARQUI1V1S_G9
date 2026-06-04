import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

# ── Configuracion ──────────────────────────────────
BROKER    = "broker.emqx.io"
PORT      = 1883
TOPIC_S1  = "invernadero/G9/sensores/humedad_suelo_area1"
TOPIC_S2  = "invernadero/G9/sensores/humedad_suelo_area2"
CLIENT_ID = "G9_humedad_suelo_01"

suelo1 = 55.0
suelo2 = 62.0

# ── Callbacks ──────────────────────────────────────
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado al broker {BROKER}")
        print(f"[OK] Publicando en:")
        print(f"     {TOPIC_S1}")
        print(f"     {TOPIC_S2}")
        print("-" * 45)
    else:
        print(f"[ERROR] No se pudo conectar. Codigo: {rc}")

def on_publish(client, userdata, mid, reason_code=None, properties=None):
    pass   # silencioso para no saturar la consola

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

# ── Helpers ────────────────────────────────────────
def clasificar_suelo(h):
    if h < 35:
        return "SECO"
    elif h > 80:
        return "SATURADO"
    return "NORMAL"

def debe_regar(estado):
    return estado == "SECO"

# ── Loop de publicacion ────────────────────────────
try:
    while True:

        # Simula que el suelo se va secando lentamente
        # y sube cuando se riega (si estado = SECO baja rapido)
        suelo1 += random.uniform(-1.5, 0.5)
        suelo2 += random.uniform(-0.8, 0.3)

        suelo1 = round(max(10.0, min(95.0, suelo1)), 1)
        suelo2 = round(max(10.0, min(95.0, suelo2)), 1)

        estado1 = clasificar_suelo(suelo1)
        estado2 = clasificar_suelo(suelo2)

        # Payload area 1
        payload1 = json.dumps({
            "valor":        suelo1,
            "unidad":       "%",
            "estado":       estado1,
            "riego_activo": debe_regar(estado1),
            "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sensor":       "FC-28",
            "area":         "area1"
        })

        # Payload area 2
        payload2 = json.dumps({
            "valor":        suelo2,
            "unidad":       "%",
            "estado":       estado2,
            "riego_activo": debe_regar(estado2),
            "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sensor":       "FC-28",
            "area":         "area2"
        })

        client.publish(TOPIC_S1, payload1, qos=1)
        client.publish(TOPIC_S2, payload2, qos=1)

        def icono(e): return " REGAR" if e == "SECO" else (" SATURADO" if e == "SATURADO" else " Normal")

        print(f"[{datetime.now().strftime('%H:%M:%S')}]")
        print(f"  Area 1 → {suelo1}%  {icono(estado1)}")
        print(f"  Area 2 → {suelo2}%  {icono(estado2)}")

        time.sleep(5)

except KeyboardInterrupt:
    print("\n[Main] Deteniendo humedad_suelo.py...")
    client.loop_stop()
    client.disconnect()
    print("[Main] Desconectado correctamente")