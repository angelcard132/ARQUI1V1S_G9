import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

BROKER     = "broker.emqx.io"
PORT       = 1883
TOPIC_PUB  = "invernadero/G9/actuadores/alarma"
TOPIC_SUB  = "invernadero/G9/control/remoto"
TOPIC_GAS  = "invernadero/G9/sensores/gas"
TOPIC_TEMP = "invernadero/G9/sensores/temperatura"
CLIENT_ID  = "G9_alarma_01"

UMBRAL_GAS_EMRG  = 400
UMBRAL_TEMP_ALTA = 35   # temperatura critica para alarma

estado_alarma = "OFF"
silenciada    = False
gas_actual    = 120.0
temp_actual   = 27.0

def publicar_estado(client, estado, motivo="sistema"):
    global estado_alarma
    estado_alarma = estado

    payload = json.dumps({
        "estado":       estado,
        "buzzer":       estado == "ON",
        "led_rojo":     estado in ("ON", "SILENCIADA"),
        "motivo":       motivo,
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    client.publish(TOPIC_PUB, payload, qos=1)
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
          f"Alarma: {estado}  |  Motivo: {motivo}")
    print(f"     Payload: {payload}")

def evaluar_alarma(client):
    global silenciada

    condicion_activa = (
        gas_actual  >= UMBRAL_GAS_EMRG or
        temp_actual >= UMBRAL_TEMP_ALTA
    )

    if condicion_activa:
        # Si condicion sigue activa, no puede volver a NORMAL automaticamente
        if estado_alarma == "OFF":
            silenciada = False
            motivo = "gas_emergencia" if gas_actual >= UMBRAL_GAS_EMRG else "temperatura_critica"
            publicar_estado(client, "ON", motivo)
    else:
        # Condicion resuelta — reset automatico
        if estado_alarma != "OFF":
            silenciada = False
            publicar_estado(client, "OFF", "condicion_resuelta")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado a {BROKER}:{PORT}")
        print(f"[OK] Publicando en:  {TOPIC_PUB}")
        print(f"[OK] Escuchando en:  {TOPIC_SUB}")
        print(f"[OK] Escuchando en:  {TOPIC_GAS}")
        print(f"[OK] Escuchando en:  {TOPIC_TEMP}")
        print(f"[OK] Umbral gas:     {UMBRAL_GAS_EMRG} ppm")
        print(f"[OK] Umbral temp:    {UMBRAL_TEMP_ALTA} C")
        print("-" * 45)
        client.subscribe(TOPIC_SUB)
        client.subscribe(TOPIC_GAS)
        client.subscribe(TOPIC_TEMP)
    else:
        print(f"[ERROR] Codigo de conexion: {rc}")

def on_message(client, userdata, msg):
    global gas_actual, temp_actual, silenciada

    if msg.topic == TOPIC_GAS:
        try:
            data = json.loads(msg.payload.decode())
            gas_actual = data.get("valor", gas_actual)
            evaluar_alarma(client)
        except Exception as e:
            print(f"[ERROR] Leyendo gas: {e}")
        return

    if msg.topic == TOPIC_TEMP:
        try:
            data = json.loads(msg.payload.decode())
            temp_actual = data.get("valor", temp_actual)
            evaluar_alarma(client)
        except Exception as e:
            print(f"[ERROR] Leyendo temperatura: {e}")
        return

    if msg.topic == TOPIC_SUB:
        try:
            data     = json.loads(msg.payload.decode())
            actuador = data.get("actuador", "")
            cmd      = data.get("cmd", "").upper()

            if actuador == "alarma" and cmd == "SILENCIAR":
                if estado_alarma == "ON":
                    silenciada = True
                    publicar_estado(client, "SILENCIADA", "manual_usuario")
                    print("[INFO] Alarma silenciada — condicion sigue activa")
                else:
                    print("[INFO] No hay alarma activa que silenciar")

            if actuador == "global" and cmd == "RESET":
                silenciada = False
                publicar_estado(client, "OFF", "reset_manual")

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
              f"Alarma: {estado_alarma}  |  "
              f"Gas: {gas_actual} ppm  |  "
              f"Temp: {temp_actual} C  |  "
              f"Silenciada: {silenciada}")
        time.sleep(10)

except KeyboardInterrupt:
    print("\n[INFO] Deteniendo alarma.py...")
    publicar_estado(client, "OFF", "sistema_apagado")
    client.loop_stop()
    client.disconnect()
    print("[INFO] Desconectado")