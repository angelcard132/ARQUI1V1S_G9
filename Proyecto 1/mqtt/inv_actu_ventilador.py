import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

BROKER      = "broker.emqx.io"
PORT        = 1883
TOPIC_PUB   = "invernadero/G9/actuadores/ventilador"
TOPIC_SUB   = "invernadero/G9/control/remoto"
TOPIC_TEMP  = "invernadero/G9/sensores/temperatura"
TOPIC_GAS   = "invernadero/G9/sensores/gas"
CLIENT_ID   = "G9_ventilador_01"

UMBRAL_TEMP_ALTA = 30
UMBRAL_GAS_EMRG  = 400
UMBRAL_GAS_WARN  = 200

ventilador_on  = False
estado_actual  = "VENTILACION_OFF"
temp_actual    = 27.0
gas_actual     = 120.0
modo           = "AUTOMATICO"

def publicar_estado(client, estado, motivo="automatico"):
    global ventilador_on, estado_actual
    estado_actual = estado
    ventilador_on = estado != "VENTILACION_OFF"

    payload = json.dumps({
        "estado":    estado,
        "activo":    ventilador_on,
        "motivo":    motivo,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    client.publish(TOPIC_PUB, payload, qos=1)
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
          f"Ventilador: {estado}  |  Motivo: {motivo}")
    print(f"     Payload: {payload}")

def evaluar_automatico(client):
    """Aplica reglas automaticas segun temperatura y gas."""
    global ventilador_on

    # Emergencia por gas — override aunque este en manual
    if gas_actual >= UMBRAL_GAS_EMRG:
        if estado_actual != "VENTILACION_EMERGENCIA":
            publicar_estado(client, "VENTILACION_EMERGENCIA", "gas_emergencia")
        return

    if modo != "AUTOMATICO":
        return

    # Temperatura alta
    if temp_actual >= UMBRAL_TEMP_ALTA and not ventilador_on:
        publicar_estado(client, "VENTILACION_ON", "temperatura_alta")
    elif temp_actual < UMBRAL_TEMP_ALTA - 2 and ventilador_on:
        if estado_actual not in ("VENTILACION_EMERGENCIA", "VENTILACION_MANUAL"):
            publicar_estado(client, "VENTILACION_OFF", "temperatura_normal")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado a {BROKER}:{PORT}")
        print(f"[OK] Publicando en:  {TOPIC_PUB}")
        print(f"[OK] Escuchando en:  {TOPIC_SUB}")
        print(f"[OK] Escuchando en:  {TOPIC_TEMP}")
        print(f"[OK] Escuchando en:  {TOPIC_GAS}")
        print(f"[OK] Umbral temp:    {UMBRAL_TEMP_ALTA} C")
        print(f"[OK] Umbral gas emg: {UMBRAL_GAS_EMRG} ppm")
        print("-" * 45)
        client.subscribe(TOPIC_SUB)
        client.subscribe(TOPIC_TEMP)
        client.subscribe(TOPIC_GAS)
    else:
        print(f"[ERROR] Codigo de conexion: {rc}")

def on_message(client, userdata, msg):
    global temp_actual, gas_actual, modo

    # Lectura de temperatura
    if msg.topic == TOPIC_TEMP:
        try:
            data = json.loads(msg.payload.decode())
            temp_actual = data.get("valor", temp_actual)
            evaluar_automatico(client)
        except Exception as e:
            print(f"[ERROR] Leyendo temperatura: {e}")
        return

    # Lectura de gas
    if msg.topic == TOPIC_GAS:
        try:
            data = json.loads(msg.payload.decode())
            gas_actual = data.get("valor", gas_actual)
            evaluar_automatico(client)
        except Exception as e:
            print(f"[ERROR] Leyendo gas: {e}")
        return

    # Comandos remotos
    if msg.topic == TOPIC_SUB:
        try:
            data     = json.loads(msg.payload.decode())
            actuador = data.get("actuador", "")
            cmd      = data.get("cmd", "").upper()

            if actuador == "ventilador":
                if cmd == "ON":
                    modo = "MANUAL"
                    publicar_estado(client, "VENTILACION_MANUAL", "manual_dashboard")
                elif cmd == "OFF":
                    # Solo apagar si no hay emergencia activa
                    if gas_actual < UMBRAL_GAS_EMRG:
                        modo = "MANUAL"
                        publicar_estado(client, "VENTILACION_OFF", "manual_dashboard")
                    else:
                        print("[AVISO] No se puede apagar — emergencia de gas activa")

            if actuador == "modo":
                modo = cmd
                print(f"[INFO] Modo cambiado a: {modo}")

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
              f"Estado: {estado_actual}  |  "
              f"Temp: {temp_actual}C  |  "
              f"Gas: {gas_actual} ppm  |  "
              f"Modo: {modo}")
        time.sleep(10)

except KeyboardInterrupt:
    print("\n[INFO] Deteniendo ventilador.py...")
    publicar_estado(client, "VENTILACION_OFF", "sistema_apagado")
    client.loop_stop()
    client.disconnect()
    print("[INFO] Desconectado")