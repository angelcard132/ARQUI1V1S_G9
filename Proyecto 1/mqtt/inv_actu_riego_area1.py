import paho.mqtt.client as mqtt
import json
import time
import threading
from datetime import datetime

BROKER      = "broker.emqx.io"
PORT        = 1883
TOPIC_PUB   = "invernadero/G9/actuadores/riego_area1"
TOPIC_SUB   = "invernadero/G9/control/remoto"
TOPIC_SUELO = "invernadero/G9/sensores/humedad_suelo_area1"
CLIENT_ID   = "G9_riego_area1_01"

UMBRAL_SECO    = 35
UMBRAL_SAT     = 80
DURACION_RIEGO = 10   # segundos que dura cada ciclo de riego

bomba_on      = False
suelo_actual  = 55.0
timer_apagado = None

def publicar_estado(client, on, motivo="automatico"):
    payload = json.dumps({
        "estado":    "ON" if on else "OFF",
        "bomba":     on,
        "motivo":    motivo,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "area":      "area1"
    })
    client.publish(TOPIC_PUB, payload, qos=1)
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
          f"Riego Area 1: {'ON' if on else 'OFF'}  |  Motivo: {motivo}")
    print(f"     Payload: {payload}")

def apagar_bomba(client):
    global bomba_on, timer_apagado
    bomba_on = False
    timer_apagado = None
    publicar_estado(client, False, "fin_ciclo")

def encender_bomba(client, motivo):
    global bomba_on, timer_apagado

    if suelo_actual >= UMBRAL_SAT:
        print(f"[AVISO] Riego bloqueado — suelo saturado ({suelo_actual}%)")
        publicar_estado(client, False, "bloqueado_saturacion")
        return

    if bomba_on:
        print("[INFO] Bomba ya esta encendida")
        return

    bomba_on = True
    publicar_estado(client, True, motivo)

    # Apagar automaticamente tras DURACION_RIEGO segundos
    if timer_apagado:
        timer_apagado.cancel()
    timer_apagado = threading.Timer(DURACION_RIEGO, apagar_bomba, args=[client])
    timer_apagado.start()
    print(f"[INFO] Bomba se apagara en {DURACION_RIEGO} segundos")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado a {BROKER}:{PORT}")
        print(f"[OK] Publicando en: {TOPIC_PUB}")
        print(f"[OK] Escuchando en:  {TOPIC_SUB}")
        print(f"[OK] Umbral seco:    {UMBRAL_SECO}%")
        print(f"[OK] Umbral sat:     {UMBRAL_SAT}%")
        print(f"[OK] Duracion riego: {DURACION_RIEGO}s")
        print("-" * 45)
        client.subscribe(TOPIC_SUB)
        client.subscribe(TOPIC_SUELO)
    else:
        print(f"[ERROR] Codigo de conexion: {rc}")

def on_message(client, userdata, msg):
    global suelo_actual

    # Actualizar valor de suelo si llega lectura
    if msg.topic == TOPIC_SUELO:
        try:
            data = json.loads(msg.payload.decode())
            suelo_actual = data.get("valor", suelo_actual)
            # Riego automatico si esta seco
            if suelo_actual < UMBRAL_SECO and not bomba_on:
                print(f"[AUTO] Suelo seco ({suelo_actual}%) -> activando riego Area 1")
                encender_bomba(client, "automatico_suelo_seco")
        except Exception as e:
            print(f"[ERROR] Leyendo suelo: {e}")
        return

    # Comandos remotos
    if msg.topic == TOPIC_SUB:
        try:
            data     = json.loads(msg.payload.decode())
            actuador = data.get("actuador", "")
            cmd      = data.get("cmd", "").upper()

            if actuador in ("riego", "riego_area1"):
                if cmd == "ON":
                    encender_bomba(client, "manual_dashboard")
                elif cmd == "OFF":
                    if timer_apagado:
                        timer_apagado.cancel()
                    apagar_bomba(client)

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
        # Heartbeat cada 10 segundos — muestra estado actual
        print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
              f"Suelo: {suelo_actual}%  |  Bomba: {'ON' if bomba_on else 'OFF'}")
        time.sleep(10)

except KeyboardInterrupt:
    print("\n[INFO] Deteniendo riego_area1.py...")
    if timer_apagado:
        timer_apagado.cancel()
    apagar_bomba(client)
    client.loop_stop()
    client.disconnect()
    print("[INFO] Desconectado")