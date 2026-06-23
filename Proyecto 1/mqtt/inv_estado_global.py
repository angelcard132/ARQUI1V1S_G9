import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

BROKER      = "broker.emqx.io"
PORT        = 1883
TOPIC_PUB   = "invernadero/G9/estado/global"
TOPIC_SUB   = "invernadero/G9/control/remoto"
CLIENT_ID   = "G9_estado_global_01"

# Topics que escucha para agregar el estado
TOPICS_SENSORES = [
    "invernadero/G9/sensores/temperatura",
    "invernadero/G9/sensores/humedad_ambiente",
    "invernadero/G9/sensores/humedad_suelo_area1",
    "invernadero/G9/sensores/humedad_suelo_area2",
    "invernadero/G9/sensores/luz",
    "invernadero/G9/sensores/gas",
    "invernadero/G9/actuadores/riego_area1",
    "invernadero/G9/actuadores/riego_area2",
    "invernadero/G9/actuadores/ventilador",
    "invernadero/G9/actuadores/alarma",
]

# Umbrales
UMBRAL_TEMP_ALTA = 30
UMBRAL_HUM_BAJA  = 40
UMBRAL_HUM_ALTA  = 80
UMBRAL_LUZ_BAJA  = 300
UMBRAL_GAS_WARN  = 200
UMBRAL_GAS_EMRG  = 400
UMBRAL_SECO      = 35

# Estado agregado
lecturas = {
    "temp":    None,
    "hum":     None,
    "suelo1":  None,
    "suelo2":  None,
    "luz":     None,
    "gas":     None,
    "riego1":  False,
    "riego2":  False,
    "alarma":  False,
}

estado_actual = "NORMAL"
modo          = "AUTOMATICO"

def calcular_estado():
    l = lecturas

    if l["gas"] is not None and l["gas"] >= UMBRAL_GAS_EMRG:
        return "EMERGENCIA"

    condicion_warn = any([
        l["temp"]   is not None and l["temp"]   >= UMBRAL_TEMP_ALTA,
        l["hum"]    is not None and (l["hum"] <= UMBRAL_HUM_BAJA or l["hum"] >= UMBRAL_HUM_ALTA),
        l["suelo1"] is not None and l["suelo1"] <= UMBRAL_SECO,
        l["suelo2"] is not None and l["suelo2"] <= UMBRAL_SECO,
        l["luz"]    is not None and l["luz"]    <= UMBRAL_LUZ_BAJA,
        l["gas"]    is not None and l["gas"]    >= UMBRAL_GAS_WARN,
    ])
    if condicion_warn:
        return "ADVERTENCIA"

    if l["riego1"] or l["riego2"]:
        return "RIEGO_ACTIVO"

    if modo == "MANUAL":
        return "MODO_MANUAL"

    return "NORMAL"

def publicar_estado(client, nuevo_estado, anterior):
    global estado_actual
    estado_actual = nuevo_estado

    # LED logico segun estado
    led = {
        "NORMAL":       {"verde": True,  "amarillo": False, "rojo": False},
        "ADVERTENCIA":  {"verde": False, "amarillo": True,  "rojo": False},
        "RIEGO_ACTIVO": {"verde": False, "amarillo": True,  "rojo": False},
        "MODO_MANUAL":  {"verde": False, "amarillo": True,  "rojo": False},
        "EMERGENCIA":   {"verde": False, "amarillo": False, "rojo": True },
    }.get(nuevo_estado, {"verde": True, "amarillo": False, "rojo": False})

    payload = json.dumps({
        "estado":    nuevo_estado,
        "anterior":  anterior,
        "modo":      modo,
        "leds":      led,
        "lecturas":  {k: v for k, v in lecturas.items()},
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    client.publish(TOPIC_PUB, payload, qos=1, retain=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
          f"Estado: {anterior} -> {nuevo_estado}")
    print(f"     LED verde={led['verde']}  "
          f"amarillo={led['amarillo']}  "
          f"rojo={led['rojo']}")
    print(f"     Payload: {payload}")

def evaluar_y_publicar(client):
    global estado_actual
    nuevo = calcular_estado()
    if nuevo != estado_actual:
        publicar_estado(client, nuevo, estado_actual)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado a {BROKER}:{PORT}")
        print(f"[OK] Publicando en: {TOPIC_PUB}")
        print(f"[OK] Suscrito a {len(TOPICS_SENSORES) + 1} topics")
        print("-" * 45)
        client.subscribe(TOPIC_SUB)
        for t in TOPICS_SENSORES:
            client.subscribe(t)
    else:
        print(f"[ERROR] Codigo de conexion: {rc}")

def on_message(client, userdata, msg):
    global modo
    topic = msg.topic

    try:
        data = json.loads(msg.payload.decode())
    except Exception:
        return

    # Actualizar lecturas segun topic
    if "temperatura" in topic:
        lecturas["temp"] = data.get("valor")
    elif "humedad_ambiente" in topic:
        lecturas["hum"] = data.get("valor")
    elif "humedad_suelo_area1" in topic:
        lecturas["suelo1"] = data.get("valor")
    elif "humedad_suelo_area2" in topic:
        lecturas["suelo2"] = data.get("valor")
    elif "sensores/luz" in topic:
        lecturas["luz"] = data.get("valor")
    elif "sensores/gas" in topic:
        lecturas["gas"] = data.get("valor")
    elif "riego_area1" in topic:
        lecturas["riego1"] = data.get("bomba", False)
    elif "riego_area2" in topic:
        lecturas["riego2"] = data.get("bomba", False)
    elif "alarma" in topic:
        lecturas["alarma"] = data.get("buzzer", False)
    elif topic == TOPIC_SUB:
        actuador = data.get("actuador", "")
        cmd      = data.get("cmd", "").upper()
        if actuador == "modo":
            modo = cmd
            print(f"[INFO] Modo cambiado a: {modo}")
        if actuador == "global" and cmd == "RESET":
            print("[INFO] Reset de estado global")
        print(f"[CMD] {actuador} -> {cmd}")

    evaluar_y_publicar(client)

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

# Publicar estado inicial
publicar_estado(client, "NORMAL", "INICIO")

try:
    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
              f"Estado: {estado_actual}  |  Modo: {modo}  |  "
              f"T={lecturas['temp']}  "
              f"H={lecturas['hum']}  "
              f"S1={lecturas['suelo1']}  "
              f"S2={lecturas['suelo2']}  "
              f"Luz={lecturas['luz']}  "
              f"Gas={lecturas['gas']}")
        time.sleep(10)

except KeyboardInterrupt:
    print("\n[INFO] Deteniendo estado_global.py...")
    publicar_estado(client, "OFFLINE", estado_actual)
    client.loop_stop()
    client.disconnect()
    print("[INFO] Desconectado")