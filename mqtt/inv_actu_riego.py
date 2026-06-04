import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

BROKER    = "broker.emqx.io"
PORT      = 1883
TOPIC_PUB = "invernadero/G9/actuadores/riego"
TOPIC_SUB = "invernadero/G9/control/remoto"
CLIENT_ID = "G9_riego_01"

estado_riego = "RIEGO_OFF"
bomba_activa = False

def clasificar_estado(suelo1=None, suelo2=None, manual=False, saturado=False):
    if saturado:
        return "BLOQUEADO_POR_SATURACION"
    if manual:
        return "RIEGO_MANUAL"
    if suelo1 is not None and suelo1 < 35:
        return "RIEGO_AREA_1"
    if suelo2 is not None and suelo2 < 35:
        return "RIEGO_AREA_2"
    return "RIEGO_OFF"

def publicar_estado(client, estado, duracion_seg=0):
    payload = json.dumps({
        "estado":       estado,
        "bomba_activa": estado != "RIEGO_OFF" and estado != "BLOQUEADO_POR_SATURACION",
        "duracion_seg": duracion_seg,
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "origen":       "automatico"
    })
    client.publish(TOPIC_PUB, payload, qos=1)
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
          f"Riego: {estado}  |  Bomba: {'ON' if estado not in ('RIEGO_OFF','BLOQUEADO_POR_SATURACION') else 'OFF'}")
    print(f"     Payload: {payload}")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado a {BROKER}:{PORT}")
        print(f"[OK] Publicando en: {TOPIC_PUB}")
        print(f"[OK] Escuchando comandos en: {TOPIC_SUB}")
        print("-" * 45)
        client.subscribe(TOPIC_SUB)
    else:
        print(f"[ERROR] Codigo de conexion: {rc}")

def on_message(client, userdata, msg):
    global estado_riego, bomba_activa
    try:
        data = json.loads(msg.payload.decode())
        actuador = data.get("actuador", "")
        cmd      = data.get("cmd", "").upper()

        if actuador in ("riego", "riego_area1", "riego_area2"):
            if cmd == "ON":
                estado_riego = "RIEGO_MANUAL"
                bomba_activa = True
                publicar_estado(client, estado_riego)
            elif cmd == "OFF":
                estado_riego = "RIEGO_OFF"
                bomba_activa = False
                publicar_estado(client, estado_riego)

        print(f"[CMD] Comando recibido -> actuador={actuador}  cmd={cmd}")
    except Exception as e:
        print(f"[ERROR] Mensaje no valido: {e}")

def on_publish(client, userdata, mid, reason_code=None, properties=None):
    print(f"     Mensaje entregado (id={mid})")

client = mqtt.Client(
    client_id=CLIENT_ID,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)
client.on_connect = on_connect
client.on_message = on_message
client.on_publish = on_publish

print(f"Conectando a {BROKER}:{PORT}...")
client.connect(BROKER, PORT, keepalive=60)
client.loop_start()

time.sleep(1)

# Secuencia de estados para demo
secuencia = [
    ("RIEGO_OFF",               0),
    ("RIEGO_AREA_1",           10),
    ("RIEGO_OFF",               0),
    ("RIEGO_AREA_2",           10),
    ("RIEGO_OFF",               0),
    ("BLOQUEADO_POR_SATURACION",0),
    ("RIEGO_OFF",               0),
]

idx = 0

try:
    while True:
        estado, dur = secuencia[idx % len(secuencia)]
        publicar_estado(client, estado, dur)
        idx += 1
        time.sleep(6)

except KeyboardInterrupt:
    print("\n[INFO] Deteniendo riego.py...")
    publicar_estado(client, "RIEGO_OFF", 0)
    client.loop_stop()
    client.disconnect()
    print("[INFO] Desconectado")