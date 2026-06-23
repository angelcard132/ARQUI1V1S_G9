import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

BROKER     = "broker.emqx.io"
PORT       = 1883
TOPIC_PUB  = "invernadero/G9/control/manual"
TOPIC_SUB  = "invernadero/G9/control/manual"
CLIENT_ID  = "G9_control_manual_01"

TOPIC_REMOTO = "invernadero/G9/control/remoto"

modo_actual = "AUTOMATICO"

# Mapeo de botones fisicos a acciones
# Boton 1 -> modo:toggle
# Boton 2 -> riego_area1:ON
# Boton 3 -> luces:toggle
# Boton 4 -> alarma:SILENCIAR
ACCIONES_BOTONES = {
    "BTN1": ("modo",        "toggle"),
    "BTN2": ("riego_area1", "ON"),
    "BTN3": ("luces",       "toggle"),
    "BTN4": ("alarma",      "SILENCIAR"),
}

estados_toggle = {
    "modo":  "AUTOMATICO",
    "luces": "OFF",
}

def publicar_accion(client, actuador, cmd, origen="boton_fisico"):
    """Publica la accion como JSON en control/remoto para que lo procesen los demas."""
    payload_remoto = json.dumps({
        "actuador": actuador,
        "cmd":      cmd,
        "origen":   origen,
        "ts":       int(time.time()),
    })
    client.publish(TOPIC_REMOTO, payload_remoto, qos=1)
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
          f"Accion manual: {actuador} -> {cmd}  (origen: {origen})")
    print(f"     Reenviado a: {TOPIC_REMOTO}")

def procesar_toggle(actuador):
    """Alterna el estado de un actuador tipo toggle."""
    global estados_toggle, modo_actual

    if actuador == "modo":
        nuevo = "MANUAL" if estados_toggle["modo"] == "AUTOMATICO" else "AUTOMATICO"
        estados_toggle["modo"] = nuevo
        modo_actual = nuevo
        return nuevo
    elif actuador == "luces":
        nuevo = "OFF" if estados_toggle["luces"] == "ON" else "ON"
        estados_toggle["luces"] = nuevo
        return nuevo
    return "ON"

def simular_boton(client, boton):
    """Simula la presion de un boton fisico."""
    if boton not in ACCIONES_BOTONES:
        print(f"[ERROR] Boton desconocido: {boton}")
        return

    actuador, cmd = ACCIONES_BOTONES[boton]

    if cmd == "toggle":
        cmd = procesar_toggle(actuador)

    # Publicar en formato simple (texto)
    payload_simple = f"{actuador}:{cmd}"
    client.publish(TOPIC_PUB, payload_simple, qos=1)
    print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
          f"Boton {boton} presionado -> {payload_simple}")

    # Tambien reenviar como JSON a control/remoto
    publicar_accion(client, actuador, cmd, f"boton_{boton}")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[OK] Conectado a {BROKER}:{PORT}")
        print(f"[OK] Publicando en:  {TOPIC_PUB}")
        print(f"[OK] Escuchando en:  {TOPIC_SUB}")
        print(f"[OK] Botones configurados:")
        for btn, (act, cmd) in ACCIONES_BOTONES.items():
            print(f"     {btn} -> {act}:{cmd}")
        print("-" * 45)
        client.subscribe(TOPIC_SUB)
    else:
        print(f"[ERROR] Codigo de conexion: {rc}")

def on_message(client, userdata, msg):
    """Recibe comandos manuales en formato texto: actuador:comando"""
    raw = msg.payload.decode().strip()
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}]  "
          f"Mensaje manual recibido: {raw}")

    if ":" in raw:
        partes   = raw.split(":", 1)
        actuador = partes[0].strip().lower()
        cmd      = partes[1].strip().upper()
        publicar_accion(client, actuador, cmd, "control_manual")
    else:
        print(f"[ERROR] Formato invalido. Esperado: 'actuador:CMD'  Recibido: '{raw}'")

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

# Demo: simular botones fisicos en secuencia
print("\n[DEMO] Simulando presiones de botones fisicos...\n")
demo_secuencia = [
    ("BTN1", 3),   # toggle modo
    ("BTN3", 3),   # toggle luces
    ("BTN2", 3),   # riego area1 ON
    ("BTN4", 3),   # silenciar alarma
    ("BTN1", 3),   # toggle modo de vuelta
]

try:
    for boton, espera in demo_secuencia:
        simular_boton(client, boton)
        time.sleep(espera)

    print("\n[INFO] Demo finalizado — escuchando comandos manuales...")
    print("[INFO] Para enviar un comando manual desde MQTTX usa el formato:")
    print("       Topic:   invernadero/G9/control/manual")
    print("       Payload: luces:ON")
    print("       Payload: modo:MANUAL")
    print("       Payload: alarma:SILENCIAR\n")

    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}]  "
              f"Esperando comandos manuales...  |  Modo: {modo_actual}")
        time.sleep(15)

except KeyboardInterrupt:
    print("\n[INFO] Deteniendo control_manual.py...")
    client.loop_stop()
    client.disconnect()
    print("[INFO] Desconectado")