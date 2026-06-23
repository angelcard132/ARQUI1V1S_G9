import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

BROKER     = "broker.emqx.io"
PORT       = 1883
TOPIC_SUB  = "invernadero/G9/control/remoto"
CLIENT_ID  = "G9_control_remoto_01"

# Re-publica el comando en el topic especifico del actuador
TOPIC_MAP = {
    "riego":        "invernadero/G9/actuadores/riego",
    "riego_area1":  "invernadero/G9/actuadores/riego_area1",
    "riego_area2":  "invernadero/G9/actuadores/riego_area2",
    "ventilador":   "invernadero/G9/actuadores/ventilador",
    "luces":        "invernadero/G9/actuadores/luces",
    "alarma":       "invernadero/G9/actuadores/alarma",
    "global":       "invernadero/G9/estado/global",
}

historial_comandos = []

def registrar_comando(actuador, cmd, origen, resultado):
    entrada = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "actuador":  actuador,
        "cmd":       cmd,
        "origen":    origen,
        "resultado": resultado,
    }
    historial_comandos.append(entrada)
    if len(historial_comandos) > 50:
        historial_comandos.pop(0)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado a {BROKER}:{PORT}")
        print(f"[OK] Escuchando comandos en: {TOPIC_SUB}")
        print(f"[OK] Actuadores registrados: {list(TOPIC_MAP.keys())}")
        print("-" * 45)
        client.subscribe(TOPIC_SUB, qos=1)
    else:
        print(f"[ERROR] Codigo de conexion: {rc}")

def on_message(client, userdata, msg):
    raw = msg.payload.decode().strip()
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}]  Comando recibido")
    print(f"     Topic:   {msg.topic}")
    print(f"     Payload: {raw}")

    try:
        data     = json.loads(raw)
        actuador = data.get("actuador", "").lower()
        cmd      = data.get("cmd", "").upper()
        origen   = data.get("origen", "desconocido")

        if not actuador:
            print("[ERROR] Falta campo 'actuador' en el comando")
            registrar_comando("?", cmd, origen, "ERROR_SIN_ACTUADOR")
            return

        if not cmd:
            print("[ERROR] Falta campo 'cmd' en el comando")
            registrar_comando(actuador, "?", origen, "ERROR_SIN_CMD")
            return

        # Validar actuador conocido
        if actuador not in TOPIC_MAP:
            print(f"[ERROR] Actuador desconocido: '{actuador}'")
            print(f"        Validos: {list(TOPIC_MAP.keys())}")
            registrar_comando(actuador, cmd, origen, "ERROR_ACTUADOR_DESCONOCIDO")
            return

        # Construir respuesta confirmacion
        confirmacion = json.dumps({
            "actuador":  actuador,
            "cmd":       cmd,
            "origen":    origen,
            "estado":    "EJECUTADO",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        # Re-publicar en topic del actuador
        topic_destino = TOPIC_MAP[actuador]
        client.publish(topic_destino, confirmacion, qos=1)

        registrar_comando(actuador, cmd, origen, "OK")
        print(f"     Actuador: {actuador}")
        print(f"     Comando:  {cmd}")
        print(f"     Origen:   {origen}")
        print(f"     Reenviado a: {topic_destino}")

    except json.JSONDecodeError:
        print(f"[ERROR] El payload no es JSON valido: {raw}")
        registrar_comando("?", "?", "?", "ERROR_JSON")

def on_publish(client, userdata, mid, reason_code=None, properties=None):
    print(f"     Confirmacion enviada (id={mid})")

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

try:
    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
              f"Esperando comandos...  |  "
              f"Historial: {len(historial_comandos)} comandos")
        time.sleep(15)

except KeyboardInterrupt:
    print("\n[INFO] Deteniendo control_remoto.py...")
    print(f"[INFO] Comandos procesados en esta sesion: {len(historial_comandos)}")
    for c in historial_comandos[-5:]:
        print(f"       {c['timestamp']}  {c['actuador']} -> {c['cmd']}  [{c['resultado']}]")
    client.loop_stop()
    client.disconnect()
    print("[INFO] Desconectado")