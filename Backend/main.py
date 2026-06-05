
import time
import json
import threading
import csv
import os
import sys
import subprocess
import argparse
from datetime import datetime

import paho.mqtt.client as mqtt
from pymongo import MongoClient


#  ARGUMENTOS


parser = argparse.ArgumentParser()
parser.add_argument("--sim", action="store_true", help="Modo simulacion sin GPIO")
args = parser.parse_args()

SIMULACION = args.sim


#  CONFIGURACION CENTRAL


# MQTT
MQTT_BROKER   = "broker.emqx.io"
MQTT_PORT     = 1883
MQTT_CLIENT   = "G9_backend_main_01"
MQTT_USER     = ""
MQTT_PASS     = ""

# Base de topics
BASE          = "invernadero/G9"

# Topics de publicacion - sensores
T_TEMP        = f"{BASE}/sensores/temperatura"
T_HUM         = f"{BASE}/sensores/humedad_ambiente"
T_SUELO1      = f"{BASE}/sensores/humedad_suelo_area1"
T_SUELO2      = f"{BASE}/sensores/humedad_suelo_area2"
T_LUZ         = f"{BASE}/sensores/luz"
T_GAS         = f"{BASE}/sensores/gas"

# Topics de publicacion - actuadores
T_RIEGO       = f"{BASE}/actuadores/riego"
T_RIEGO1      = f"{BASE}/actuadores/riego_area1"
T_RIEGO2      = f"{BASE}/actuadores/riego_area2"
T_VENTILADOR  = f"{BASE}/actuadores/ventilador"
T_LUCES       = f"{BASE}/actuadores/luces"
T_ALARMA      = f"{BASE}/actuadores/alarma"

# Topics de publicacion - estado y control
T_GLOBAL      = f"{BASE}/estado/global"
T_CTRL_REMOTO = f"{BASE}/control/remoto"
T_CTRL_MANUAL = f"{BASE}/control/manual"
T_ARM64       = f"{BASE}/arm64"

# MongoDB
MONGO_URI     = "mongodb+srv://UserDB1:PasswordDB1@cluster0.2qomnft.mongodb.net/?appName=Cluster0"
DB_NAME       = "invernadero"

# Umbrales
UMBRAL_TEMP_ALTA  = 30
UMBRAL_HUM_BAJA   = 40
UMBRAL_HUM_ALTA   = 80
UMBRAL_LUZ_BAJA   = 300
UMBRAL_GAS_WARN   = 200
UMBRAL_GAS_EMRG   = 400
UMBRAL_SUELO_SECO = 35
UMBRAL_SUELO_SAT  = 80
DURACION_RIEGO    = 10    # segundos por ciclo de riego

# Pines GPIO (BCM)
PIN_DHT        = 4
PIN_BOMBA1     = 17
PIN_BOMBA2     = 27
PIN_VENTILADOR = 22
PIN_LUZ1       = 23
PIN_LUZ2       = 24
PIN_LED_VERDE  = 5
PIN_LED_AMAR   = 6
PIN_LED_ROJO   = 13
PIN_BUZZER     = 19
PIN_BTN1       = 16
PIN_BTN2       = 20
PIN_BTN3       = 21
PIN_BTN4       = 12

# Canal MCP3008
CANAL_LDR    = 0
CANAL_GAS    = 1
CANAL_SUELO1 = 2
CANAL_SUELO2 = 3

# Rutas ARM64
CSV_PATH  = "lecturas.csv"
ARM64_DIR = "./arm64"
CSV_HEADER = [
    "ID","TEMP","HUM_AIRE",
    "HUM_SUELO_1","HUM_SUELO_2",
    "LUZ","GAS","RIEGO_1","RIEGO_2"
]


#  ESTADO GLOBAL


state = {
    "global":       "NORMAL",
    "modo":         "AUTOMATICO",
    "temp":         None,
    "hum":          None,
    "luz":          None,
    "gas":          None,
    "suelo1":       None,
    "suelo2":       None,
    "riego1":       False,
    "riego2":       False,
    "ventilador":   False,
    "luces":        False,
    "alarma":       False,
    "lecturas_csv": [],
    "lectura_id":   0,
}

lock           = threading.Lock()
timers_riego   = {}
mqtt_client    = None
db             = None
#  HARDWARE - GPIO

gpio_ok = False

if not SIMULACION:
    try:
        import RPi.GPIO as GPIO
        import adafruit_dht
        import board
        import busio
        import adafruit_mcp3xxx.mcp3008 as MCP
        from adafruit_mcp3xxx.analog_in import AnalogIn

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        PINES_SALIDA = [
            PIN_BOMBA1, PIN_BOMBA2, PIN_VENTILADOR,
            PIN_LUZ1, PIN_LUZ2,
            PIN_LED_VERDE, PIN_LED_AMAR, PIN_LED_ROJO,
            PIN_BUZZER,
        ]
        for pin in PINES_SALIDA:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

        PINES_ENTRADA = [PIN_BTN1, PIN_BTN2, PIN_BTN3, PIN_BTN4]
        for pin in PINES_ENTRADA:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        dht_sensor = adafruit_dht.DHT22(board.D4)

        spi          = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
        mcp          = MCP.MCP3008(spi, board.CE0)
        ch_ldr       = AnalogIn(mcp, CANAL_LDR)
        ch_gas       = AnalogIn(mcp, CANAL_GAS)
        ch_suelo1    = AnalogIn(mcp, CANAL_SUELO1)
        ch_suelo2    = AnalogIn(mcp, CANAL_SUELO2)

        gpio_ok = True
        print("[GPIO] Hardware inicializado correctamente")

    except Exception as e:
        print(f"[GPIO] Error iniciando hardware: {e}")
        print("[GPIO] Usando modo simulacion automaticamente")

#  LECTURA DE SENSORES

def leer_sensores():
    import random

    if gpio_ok:
        try:
            temp  = round(dht_sensor.temperature, 1)
            hum   = round(dht_sensor.humidity, 1)
            luz   = round(ch_ldr.value    / 65535 * 1000)
            gas   = round(ch_gas.value    / 65535 * 1000)
            # Sensor de suelo: valor alto = seco, invertir a porcentaje
            suelo1 = round(100 - (ch_suelo1.value / 65535 * 100))
            suelo2 = round(100 - (ch_suelo2.value / 65535 * 100))
            return {
                "temp": temp, "hum": hum,
                "luz": luz,   "gas": gas,
                "suelo1": suelo1, "suelo2": suelo2,
            }
        except Exception as e:
            print(f"[Sensor] Error leyendo hardware: {e}")
            return None
    else:
        # Simulacion con variaciones realistas
        import random
        def varia(base, mn, mx, delta_n, delta_p):
            val = (base or (mn + mx) / 2) + random.uniform(delta_n, delta_p)
            return round(max(mn, min(mx, val)), 1)

        return {
            "temp":   varia(state["temp"],   18, 38,  -0.5,  0.8),
            "hum":    varia(state["hum"],    20, 95,  -1.0,  1.0),
            "luz":    varia(state["luz"],     0, 1000,-30,   25),
            "gas":    varia(state["gas"],    50, 600,  -8,   12),
            "suelo1": varia(state["suelo1"], 10, 95,  -1.5,  0.4),
            "suelo2": varia(state["suelo2"], 10, 95,  -1.2,  0.4),
        }

#  CONTROL DE ACTUADORES

def gpio_set(pin, encender):
    if gpio_ok:
        GPIO.output(pin, GPIO.HIGH if encender else GPIO.LOW)

def set_leds_por_estado(estado):
    gpio_set(PIN_LED_VERDE, estado == "NORMAL")
    gpio_set(PIN_LED_AMAR,  estado in ("ADVERTENCIA", "RIEGO_ACTIVO", "MODO_MANUAL"))
    gpio_set(PIN_LED_ROJO,  estado == "EMERGENCIA")

def activar_riego(area, activar, motivo="automatico"):
    global timers_riego

    key_bomba = f"riego{area}"
    pin_bomba = PIN_BOMBA1 if area == 1 else PIN_BOMBA2
    topic     = T_RIEGO1   if area == 1 else T_RIEGO2

    with lock:
        suelo = state[f"suelo{area}"]

        if activar:
            if suelo is not None and suelo >= UMBRAL_SUELO_SAT:
                payload = _payload_riego(area, False, "BLOQUEADO_POR_SATURACION", motivo)
                mqtt_client.publish(topic, payload, qos=1)
                mqtt_client.publish(T_RIEGO, payload, qos=1)
                _log(f"[Riego] Area {area} BLOQUEADO — suelo saturado ({suelo}%)")
                return

            if state[key_bomba]:
                return

            state[key_bomba] = True
            gpio_set(pin_bomba, True)

            payload = _payload_riego(area, True, "RIEGO_ACTIVO", motivo)
            mqtt_client.publish(topic, payload, qos=1)
            mqtt_client.publish(T_RIEGO, payload, qos=1)
            registrar_evento(f"riego_area{area}", "ON", motivo)

            # Apagado automatico tras DURACION_RIEGO segundos
            if area in timers_riego and timers_riego[area]:
                timers_riego[area].cancel()
            timers_riego[area] = threading.Timer(
                DURACION_RIEGO,
                activar_riego,
                args=[area, False, "fin_ciclo"]
            )
            timers_riego[area].start()
            _log(f"[Riego] Area {area} ON — se apaga en {DURACION_RIEGO}s")

        else:
            if area in timers_riego and timers_riego[area]:
                timers_riego[area].cancel()
                timers_riego[area] = None

            state[key_bomba] = False
            gpio_set(pin_bomba, False)

            payload = _payload_riego(area, False, "RIEGO_OFF", motivo)
            mqtt_client.publish(topic, payload, qos=1)
            mqtt_client.publish(T_RIEGO, payload, qos=1)
            registrar_evento(f"riego_area{area}", "OFF", motivo)
            _log(f"[Riego] Area {area} OFF ({motivo})")

def _payload_riego(area, on, estado, motivo):
    return json.dumps({
        "estado":    estado,
        "bomba":     on,
        "area":      f"area{area}",
        "motivo":    motivo,
        "timestamp": _ts(),
    })

def set_ventilador(encender, motivo="automatico"):
    with lock:
        if state["ventilador"] == encender:
            return
        state["ventilador"] = encender

    gpio_set(PIN_VENTILADOR, encender)

    estado = "VENTILACION_EMERGENCIA" if motivo == "gas_emergencia" else \
             "VENTILACION_MANUAL"     if "manual" in motivo else \
             "VENTILACION_ON"         if encender else \
             "VENTILACION_OFF"

    payload = json.dumps({
        "estado":    estado,
        "activo":    encender,
        "motivo":    motivo,
        "timestamp": _ts(),
    })
    mqtt_client.publish(T_VENTILADOR, payload, qos=1)
    registrar_evento("ventilador", "ON" if encender else "OFF", motivo)
    _log(f"[Ventilador] {'ON' if encender else 'OFF'} ({motivo})")

def set_luces(encender, motivo="automatico"):
    with lock:
        if state["luces"] == encender:
            return
        state["luces"] = encender

    gpio_set(PIN_LUZ1, encender)
    gpio_set(PIN_LUZ2, encender)

    payload = json.dumps({
        "estado":    "ON" if encender else "OFF",
        "activo":    encender,
        "motivo":    motivo,
        "timestamp": _ts(),
    })
    mqtt_client.publish(T_LUCES, payload, qos=1)
    registrar_evento("luces", "ON" if encender else "OFF", motivo)
    _log(f"[Luces] {'ON' if encender else 'OFF'} ({motivo})")

def set_alarma(encender, motivo="sistema"):
    with lock:
        if state["alarma"] == encender:
            return
        state["alarma"] = encender

    gpio_set(PIN_BUZZER, encender)
    gpio_set(PIN_LED_ROJO, encender)

    payload = json.dumps({
        "estado":    "ON" if encender else "OFF",
        "buzzer":    encender,
        "led_rojo":  encender,
        "motivo":    motivo,
        "timestamp": _ts(),
    })
    mqtt_client.publish(T_ALARMA, payload, qos=1)
    registrar_evento("alarma", "ON" if encender else "OFF", motivo)
    _log(f"[Alarma] {'ON' if encender else 'OFF'} ({motivo})")

#  LOGICA DE AUTOMATISMOS


def aplicar_automatismos(lectura):
    if state["modo"] != "AUTOMATICO":
        # Gas emergencia override siempre — aunque sea manual
        if lectura["gas"] >= UMBRAL_GAS_EMRG:
            set_ventilador(True, "gas_emergencia")
            set_alarma(True, "gas_emergencia")
        return

    # Temperatura alta -> ventilador
    if lectura["temp"] >= UMBRAL_TEMP_ALTA:
        set_ventilador(True, "temperatura_alta")
    elif lectura["temp"] < UMBRAL_TEMP_ALTA - 2:
        if state["gas"] is None or state["gas"] < UMBRAL_GAS_EMRG:
            set_ventilador(False, "temperatura_normal")

    # Gas -> ventilador y alarma
    if lectura["gas"] >= UMBRAL_GAS_EMRG:
        set_ventilador(True, "gas_emergencia")
        set_alarma(True, "gas_emergencia")
    elif lectura["gas"] >= UMBRAL_GAS_WARN:
        set_ventilador(True, "gas_advertencia")
        if state["alarma"]:
            set_alarma(False, "gas_bajo_emergencia")
    else:
        if state["alarma"] and state["gas"] is not None:
            set_alarma(False, "gas_normalizado")

    # Luz baja -> luces artificiales
    if lectura["luz"] < UMBRAL_LUZ_BAJA:
        set_luces(True, "luz_baja")
    elif lectura["luz"] >= UMBRAL_LUZ_BAJA:
        set_luces(False, "luz_suficiente")

    # Suelo seco -> riego por area
    if lectura["suelo1"] < UMBRAL_SUELO_SECO and not state["riego1"]:
        activar_riego(1, True, "suelo_seco_auto")
    if lectura["suelo2"] < UMBRAL_SUELO_SECO and not state["riego2"]:
        activar_riego(2, True, "suelo_seco_auto")

def calcular_estado_global():
    s = state

    if s["gas"] is not None and s["gas"] >= UMBRAL_GAS_EMRG:
        return "EMERGENCIA"

    condicion_warn = any([
        s["temp"]   is not None and s["temp"]   >= UMBRAL_TEMP_ALTA,
        s["hum"]    is not None and (s["hum"] <= UMBRAL_HUM_BAJA or s["hum"] >= UMBRAL_HUM_ALTA),
        s["suelo1"] is not None and s["suelo1"] <= UMBRAL_SUELO_SECO,
        s["suelo2"] is not None and s["suelo2"] <= UMBRAL_SUELO_SECO,
        s["luz"]    is not None and s["luz"]    <= UMBRAL_LUZ_BAJA,
        s["gas"]    is not None and s["gas"]    >= UMBRAL_GAS_WARN,
    ])
    if condicion_warn:
        return "ADVERTENCIA"

    if s["riego1"] or s["riego2"]:
        return "RIEGO_ACTIVO"

    if s["modo"] == "MANUAL":
        return "MODO_MANUAL"

    return "NORMAL"

def publicar_estado_global():
    nuevo = calcular_estado_global()

    with lock:
        anterior      = state["global"]
        state["global"] = nuevo

    set_leds_por_estado(nuevo)

    led = {
        "verde":    nuevo == "NORMAL",
        "amarillo": nuevo in ("ADVERTENCIA", "RIEGO_ACTIVO", "MODO_MANUAL"),
        "rojo":     nuevo == "EMERGENCIA",
    }

    payload = json.dumps({
        "estado":    nuevo,
        "anterior":  anterior,
        "modo":      state["modo"],
        "leds":      led,
        "lecturas": {
            "temp":   state["temp"],
            "hum":    state["hum"],
            "suelo1": state["suelo1"],
            "suelo2": state["suelo2"],
            "luz":    state["luz"],
            "gas":    state["gas"],
        },
        "timestamp": _ts(),
    })
    mqtt_client.publish(T_GLOBAL, payload, qos=1, retain=True)

    if nuevo != anterior:
        registrar_evento("estado_global", nuevo, "sistema")
        _log(f"[Estado] {anterior} -> {nuevo}")

#  PUBLICACION DE SENSORES

def publicar_sensores(lectura):
    def _pub(topic, valor, unidad, estado_fn, extra=None):
        d = {
            "valor":     valor,
            "unidad":    unidad,
            "estado":    estado_fn(valor),
            "timestamp": _ts(),
        }
        if extra:
            d.update(extra)
        mqtt_client.publish(topic, json.dumps(d), qos=1)

    def st_temp(v):
        return "ALTA" if v >= UMBRAL_TEMP_ALTA else "NORMAL"

    def st_hum(v):
        if v < UMBRAL_HUM_BAJA:  return "BAJA"
        if v > UMBRAL_HUM_ALTA:  return "ALTA"
        return "NORMAL"

    def st_luz(v):
        return "BAJA" if v < UMBRAL_LUZ_BAJA else "NORMAL"

    def st_gas(v):
        if v >= UMBRAL_GAS_EMRG: return "GAS_EMERGENCIA"
        if v >= UMBRAL_GAS_WARN: return "GAS_ADVERTENCIA"
        return "GAS_NORMAL"

    def st_suelo(v):
        if v < UMBRAL_SUELO_SECO: return "SECO"
        if v > UMBRAL_SUELO_SAT:  return "SATURADO"
        return "NORMAL"

    _pub(T_TEMP,   lectura["temp"],   "C",   st_temp, {"sensor": "DHT22"})
    _pub(T_HUM,    lectura["hum"],    "%",   st_hum,  {"sensor": "DHT22"})
    _pub(T_LUZ,    lectura["luz"],    "lux", st_luz,  {"sensor": "LDR",  "iluminacion_activa": lectura["luz"] < UMBRAL_LUZ_BAJA})
    _pub(T_GAS,    lectura["gas"],    "ppm", st_gas,  {"sensor": "MQ-2", "alarma_activa": lectura["gas"] >= UMBRAL_GAS_EMRG})
    _pub(T_SUELO1, lectura["suelo1"], "%",   st_suelo, {"sensor": "FC-28", "area": "area1", "riego_activo": state["riego1"]})
    _pub(T_SUELO2, lectura["suelo2"], "%",   st_suelo, {"sensor": "FC-28", "area": "area2", "riego_activo": state["riego2"]})

#  MONGODB

def conectar_mongo():
    global db
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client[DB_NAME]
        _log(f"[MongoDB] Conectado a '{DB_NAME}'")
    except Exception as e:
        _log(f"[MongoDB] Sin conexion: {e} — continuando sin persistencia")
        db = None

def guardar_lectura(lectura):
    if db is None:
        return
    try:
        db["sensor_readings"].insert_one({
            "timestamp": datetime.now(),
            "origen":    "raspberry_pi",
            "estado":    state["global"],
            **lectura,
        })
    except Exception as e:
        _log(f"[MongoDB] Error en sensor_readings: {e}")

def registrar_evento(tipo, valor, origen):
    _log(f"[Evento] {tipo} = {valor} ({origen})")
    if db is None:
        return
    try:
        db["events"].insert_one({
            "timestamp": datetime.now(),
            "tipo":      tipo,
            "valor":     str(valor),
            "origen":    origen,
            "estado":    state["global"],
        })
    except Exception as e:
        _log(f"[MongoDB] Error en events: {e}")

def registrar_comando(actuador, cmd, origen):
    if db is None:
        return
    try:
        db["commands"].insert_one({
            "timestamp": datetime.now(),
            "actuador":  actuador,
            "comando":   cmd,
            "origen":    origen,
            "estado":    state["global"],
        })
    except Exception as e:
        _log(f"[MongoDB] Error en commands: {e}")

def guardar_estado_sistema():
    if db is None:
        return
    try:
        db["system_status"].replace_one(
            {"_id": "current"},
            {
                "_id":       "current",
                "timestamp": datetime.now(),
                "estado":    state["global"],
                "modo":      state["modo"],
                "sensores": {
                    "temp":   state["temp"],
                    "hum":    state["hum"],
                    "suelo1": state["suelo1"],
                    "suelo2": state["suelo2"],
                    "luz":    state["luz"],
                    "gas":    state["gas"],
                },
                "actuadores": {
                    "riego1":     state["riego1"],
                    "riego2":     state["riego2"],
                    "ventilador": state["ventilador"],
                    "luces":      state["luces"],
                    "alarma":     state["alarma"],
                },
            },
            upsert=True,
        )
    except Exception as e:
        _log(f"[MongoDB] Error en system_status: {e}")

def guardar_actuador_log(actuador, accion, origen):
    if db is None:
        return
    try:
        db["actuator_logs"].insert_one({
            "timestamp": datetime.now(),
            "actuador":  actuador,
            "accion":    accion,
            "origen":    origen,
            "estado":    state["global"],
        })
    except Exception as e:
        _log(f"[MongoDB] Error en actuator_logs: {e}")

def guardar_arm64(modulo, resultado):
    if db is None:
        return
    try:
        db["arm64_results"].insert_one({
            "timestamp": datetime.now(),
            "modulo":    modulo,
            "resultado": resultado,
        })
    except Exception as e:
        _log(f"[MongoDB] Error en arm64_results: {e}")


#  CSV Y ARM64

def acumular_csv(lectura):
    with lock:
        state["lectura_id"] += 1
        fila = [
            state["lectura_id"],
            lectura["temp"],
            lectura["hum"],
            lectura["suelo1"],
            lectura["suelo2"],
            lectura["luz"],
            lectura["gas"],
            1 if state["riego1"] else 0,
            1 if state["riego2"] else 0,
        ]
        state["lecturas_csv"].append(fila)
        if len(state["lecturas_csv"]) > 30:
            state["lecturas_csv"].pop(0)

        if len(state["lecturas_csv"]) >= 30:
            _escribir_csv()

def _escribir_csv():
    try:
        ultimas = state["lecturas_csv"][-30:]
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            for i, fila in enumerate(ultimas, start=1):
                fila[0] = i
                writer.writerow(fila)
            writer.writerow(["$"])
        _log(f"[CSV] lecturas.csv actualizado con {len(ultimas)} filas")
    except Exception as e:
        _log(f"[CSV] Error escribiendo: {e}")

def ejecutar_arm64():
    if not os.path.exists(CSV_PATH):
        _log("[ARM64] lecturas.csv no existe — espera 30 lecturas")
        return

    modulos = [
        ("modulo_1_media",      "resultado_media.txt"),
        ("modulo_2_varianza",   "resultado_varianza.txt"),
        ("modulo_3_anomalias",  "resultado_anomalias.txt"),
        ("modulo_4_prediccion", "resultado_prediccion.txt"),
        ("modulo_5_tendencia",  "resultado_tendencia.txt"),
    ]

    for binario, salida in modulos:
        bin_path = os.path.join(ARM64_DIR, binario)
        out_path = os.path.join(ARM64_DIR, salida)

        if not os.path.exists(bin_path):
            _log(f"[ARM64] Binario no encontrado: {bin_path}")
            continue

        try:
            subprocess.run([bin_path], timeout=15, check=True)
            _log(f"[ARM64] {binario} ejecutado OK")
            _leer_resultado_arm64(binario, out_path)
        except subprocess.TimeoutExpired:
            _log(f"[ARM64] {binario} timeout")
        except subprocess.CalledProcessError as e:
            _log(f"[ARM64] {binario} error: {e}")
        except FileNotFoundError:
            _log(f"[ARM64] No se encontro: {bin_path}")

def _leer_resultado_arm64(modulo, ruta):
    if not os.path.exists(ruta):
        _log(f"[ARM64] Salida no encontrada: {ruta}")
        return

    resultado = {}
    try:
        with open(ruta, "r") as f:
            for linea in f:
                linea = linea.strip()
                if "=" in linea:
                    clave, valor = linea.split("=", 1)
                    resultado[clave.strip()] = valor.strip()

        _log(f"[ARM64] {modulo}: {resultado}")
        mqtt_client.publish(f"{T_ARM64}/{modulo}", json.dumps(resultado), qos=1)
        guardar_arm64(modulo, resultado)

    except Exception as e:
        _log(f"[ARM64] Error leyendo {ruta}: {e}")
#  MQTT - CALLBACKS

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        _log(f"[MQTT] Conectado a {MQTT_BROKER}:{MQTT_PORT}")
        # Suscribirse a todos los topics de control
        subs = [
            (T_CTRL_REMOTO, 1),
            (T_CTRL_MANUAL, 1),
        ]
        client.subscribe(subs)
        _log(f"[MQTT] Suscrito a {len(subs)} topics de control")
    else:
        _log(f"[MQTT] Error de conexion codigo: {rc}")

def on_disconnect(client, userdata, rc, properties=None, reasonCode=None):
    _log(f"[MQTT] Desconectado (rc={rc}) — reconectando automaticamente...")

def on_message(client, userdata, msg):
    topic   = msg.topic
    payload = msg.payload.decode("utf-8").strip()

    _log(f"[MQTT] Recibido <- {topic}: {payload}")

    # Control remoto desde dashboard (JSON)
    if topic == T_CTRL_REMOTO:
        try:
            data     = json.loads(payload)
            actuador = data.get("actuador", "").lower()
            cmd      = data.get("cmd", "").upper()
            origen   = data.get("origen", "dashboard")
            registrar_comando(actuador, cmd, origen)
            _ejecutar_comando(actuador, cmd)
        except json.JSONDecodeError:
            _log(f"[MQTT] Payload no es JSON: {payload}")

    # Control manual desde botones fisicos (texto simple)
    elif topic == T_CTRL_MANUAL:
        if ":" in payload:
            partes   = payload.split(":", 1)
            actuador = partes[0].strip().lower()
            cmd      = partes[1].strip().upper()
            registrar_comando(actuador, cmd, "boton_fisico")
            _ejecutar_comando(actuador, cmd)

def _ejecutar_comando(actuador, cmd):
    _log(f"[Cmd] Ejecutando: {actuador} -> {cmd}")

    if actuador == "modo":
        with lock:
            state["modo"] = cmd
        _log(f"[Modo] Cambiado a: {cmd}")
        publicar_estado_global()
        return

    if actuador in ("riego", "riego_area1"):
        activar_riego(1, cmd == "ON", "manual_remoto")
        guardar_actuador_log("riego_area1", cmd, "remoto")

    if actuador == "riego_area2":
        activar_riego(2, cmd == "ON", "manual_remoto")
        guardar_actuador_log("riego_area2", cmd, "remoto")

    if actuador == "ventilador":
        set_ventilador(cmd == "ON", "manual_remoto")
        guardar_actuador_log("ventilador", cmd, "remoto")

    if actuador == "luces":
        set_luces(cmd == "ON", "manual_remoto")
        guardar_actuador_log("luces", cmd, "remoto")

    if actuador == "alarma" and cmd == "SILENCIAR":
        set_alarma(False, "silenciado_usuario")
        guardar_actuador_log("alarma", "SILENCIAR", "remoto")

    if actuador == "global" and cmd == "RESET":
        with lock:
            state["global"] = "NORMAL"
        set_leds_por_estado("NORMAL")
        mqtt_client.publish(T_GLOBAL, json.dumps({
            "estado": "NORMAL", "timestamp": _ts()
        }), retain=True)
        registrar_evento("reset", "NORMAL", "usuario")

    publicar_estado_global()

def on_publish(client, userdata, mid, reason_code=None, properties=None):
    pass   # silencioso

#  HILO - BOTONES FISICOS

def hilo_botones():
    if not gpio_ok:
        return

    prev = {p: True for p in [PIN_BTN1, PIN_BTN2, PIN_BTN3, PIN_BTN4]}

    while True:
        b1 = GPIO.input(PIN_BTN1)
        b2 = GPIO.input(PIN_BTN2)
        b3 = GPIO.input(PIN_BTN3)
        b4 = GPIO.input(PIN_BTN4)

        # Boton 1 — toggle modo auto/manual
        if not b1 and prev[PIN_BTN1]:
            nuevo_modo = "MANUAL" if state["modo"] == "AUTOMATICO" else "AUTOMATICO"
            with lock:
                state["modo"] = nuevo_modo
            mqtt_client.publish(T_CTRL_MANUAL, f"modo:{nuevo_modo}")
            registrar_evento("modo", nuevo_modo, "boton_1")
            _log(f"[BTN1] Modo -> {nuevo_modo}")

        # Boton 2 — riego manual area 1
        if not b2 and prev[PIN_BTN2]:
            activar_riego(1, not state["riego1"], "boton_2")
            _log("[BTN2] Toggle riego area 1")

        # Boton 3 — toggle luces
        if not b3 and prev[PIN_BTN3]:
            set_luces(not state["luces"], "boton_3")
            _log("[BTN3] Toggle luces")

        # Boton 4 — silenciar alarma
        if not b4 and prev[PIN_BTN4]:
            set_alarma(False, "boton_4")
            _log("[BTN4] Alarma silenciada")

        prev = {PIN_BTN1: b1, PIN_BTN2: b2, PIN_BTN3: b3, PIN_BTN4: b4}
        time.sleep(0.05)

#  HILO PRINCIPAL - LOOP DE SENSORES

def hilo_sensores():
    arm64_counter = 0

    while True:
        lectura = leer_sensores()

        if lectura is None:
            _log("[Sensor] Fallo en lectura — reintentando en 2s")
            time.sleep(2)
            continue

        # Actualizar estado
        with lock:
            state["temp"]   = lectura["temp"]
            state["hum"]    = lectura["hum"]
            state["luz"]    = lectura["luz"]
            state["gas"]    = lectura["gas"]
            state["suelo1"] = lectura["suelo1"]
            state["suelo2"] = lectura["suelo2"]

        # Publicar por MQTT
        publicar_sensores(lectura)

        # Guardar en MongoDB
        guardar_lectura(lectura)
        guardar_estado_sistema()

        # Acumular CSV
        acumular_csv(lectura)

        # Automatismos
        aplicar_automatismos(lectura)
        publicar_estado_global()

        # Ejecutar ARM64 cada 30 lecturas
        arm64_counter += 1
        if arm64_counter >= 30 and len(state["lecturas_csv"]) >= 30:
            arm64_counter = 0
            threading.Thread(
                target=ejecutar_arm64,
                daemon=True
            ).start()

        _log(
            f"[Loop] "
            f"T={lectura['temp']}C  "
            f"H={lectura['hum']}%  "
            f"S1={lectura['suelo1']}%  "
            f"S2={lectura['suelo2']}%  "
            f"Luz={lectura['luz']}  "
            f"Gas={lectura['gas']}  "
            f"Estado={state['global']}"
        )

        time.sleep(5)

#  HELPERS

def _ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

#  ARRANQUE

if __name__ == "__main__":
    print("  PROYECTO 1 ARQUI 1")
    print(f"  Modo: {'SIMULACION' if SIMULACION or not gpio_ok else 'HARDWARE REAL'}")

    # 1. MongoDB
    conectar_mongo()

    # 2. Carpeta ARM64
    os.makedirs(ARM64_DIR, exist_ok=True)

    # 3. MQTT
    mqtt_client = mqtt.Client(
        client_id=MQTT_CLIENT,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    if MQTT_USER:
        mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)

    mqtt_client.on_connect    = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message    = on_message
    mqtt_client.on_publish    = on_publish

    # Reconexion automatica
    mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)

    _log(f"[MQTT] Conectando a {MQTT_BROKER}:{MQTT_PORT}...")
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()

    time.sleep(2)

    # 4. Hilo de botones fisicos
    if gpio_ok:
        t_btn = threading.Thread(target=hilo_botones, daemon=True)
        t_btn.start()
        _log("[BTN] Hilo de botones iniciado")

    # 5. Evento de inicio
    registrar_evento("sistema", "INICIADO", "main.py")
    mqtt_client.publish(T_GLOBAL, json.dumps({
        "estado":    "NORMAL",
        "timestamp": _ts(),
    }), retain=True)

    # 6. Loop principal
    _log("[Main] Sistema corriendo — Ctrl+C para salir\n")
    try:
        hilo_sensores()

    except KeyboardInterrupt:
        _log("\n[Main] Apagando sistema...")

        # Apagar todos los actuadores
        if gpio_ok:
            for pin in [
                PIN_BOMBA1, PIN_BOMBA2, PIN_VENTILADOR,
                PIN_LUZ1, PIN_LUZ2,
                PIN_LED_VERDE, PIN_LED_AMAR, PIN_LED_ROJO,
                PIN_BUZZER,
            ]:
                GPIO.output(pin, GPIO.LOW)
            GPIO.cleanup()

        # Cancelar timers de riego
        for area, timer in timers_riego.items():
            if timer:
                timer.cancel()

        # Publicar estado offline
        mqtt_client.publish(T_GLOBAL, json.dumps({
            "estado":    "OFFLINE",
            "timestamp": _ts(),
        }), retain=True)

        registrar_evento("sistema", "APAGADO", "main.py")

        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        _log("[Main] Sistema apagado correctamente")