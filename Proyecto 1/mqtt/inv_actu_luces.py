import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

BROKER     = "broker.emqx.io"
PORT       = 1883
TOPIC_PUB  = "invernadero/G9/actuadores/luces"
TOPIC_SUB  = "invernadero/G9/control/remoto"
TOPIC_LUZ  = "invernadero/G9/sensores/luz"
CLIENT_ID  = "G9_luces_01"

UMBRAL_LUZ_BAJA = 300

luces_on   = False
modo       = "AUTOMATICO"
luz_actual = 400.0

def publicar_estado(client, on, motivo="automatico"):
    global luces_on
    luces_on = on

    payload = json.dumps({
        "estado":    "ON" if on else "OFF",
        "activo":    on,
        "modo":      modo,
        "motivo":    motivo,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    client.publish(TOPIC_PUB, payload, qos=1)
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
          f"Luces: {'ON' if on else 'OFF'}  |  Modo: {modo}  |  Motivo: {motivo}")
    print(f"     Payload: {payload}")

def evaluar_automatico(client):
    if modo != "AUTOMATICO":
        return
    if luz_actual < UMBRAL_LUZ_BAJA and not luces_on:
        publicar_estado(client, True, "automatico_luz_baja")
    elif luz_actual >= UMBRAL_LUZ_BAJA and luces_on:
        publicar_estado(client, False, "automatico_luz_suficiente")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado a {BROKER}:{PORT}")
        print(f"[OK] Publicando en:  {TOPIC_PUB}")
        print(f"[OK] Escuchando en:  {TOPIC_SUB}")
        print(f"[OK] Escuchando en:  {TOPIC_LUZ}")
        print(f"[OK] Umbral luz:     {UMBRAL_LUZ_BAJA} lux")
        print("-" * 45)
        client.subscribe(TOPIC_SUB)
        client.subscribe(TOPIC_LUZ)
    else:
        print(f"[ERROR] Codigo de conexion: {rc}")

def on_message(client, userdata, msg):
    global luz_actual, modo

    if msg.topic == TOPIC_LUZ:
        try:
            data = json.loads(msg.payload.decode())
            luz_actual = data.get("valor", luz_actual)
            evaluar_automatico(client)
        except Exception as e:
            print(f"[ERROR] Leyendo luz: {e}")
        return

    if msg.topic == TOPIC_SUB:
        try:
            data     = json.loads(msg.payload.decode())
            actuador = data.get("actuador", "")
            cmd      = data.get("cmd", "").upper()

            if actuador == "luces":
                if cmd == "ON":
                    modo = "MANUAL"
                    publicar_estado(client, True, "manual_dashboard")
                elif cmd == "OFF":
                    modo = "MANUAL"
                    publicar_estado(client, False, "manual_dashboard")

            if actuador == "modo":
                modo = cmd
                print(f"[INFO] Modo cambiado a: {modo}")
                if modo == "AUTOMATICO":
                    evaluar_automatico(client)

            print(f"[CMD] {actuador} -> {cmd}")
        except Exception as e:
            print(f"[ERROR] Comando invalido: {e}")

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

try:
    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
              f"Luces: {'ON' if luces_on else 'OFF'}  |  "
              f"Modo: {modo}  |  "
              f"Luz ambiente: {luz_actual} lux")
        time.sleep(10)

except KeyboardInterrupt:
    print("\n[INFO] Deteniendo luces.py...")
    publicar_estado(client, False, "sistema_apagado")
    client.loop_stop()
    client.disconnect()
    print("[INFO] Desconectado")