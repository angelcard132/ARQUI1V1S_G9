
import time
import json
import threading
import csv
import os
import sys
import subprocess
import argparse
from datetime import datetime

from mongo_handler import (
    conectar        as mongo_conectar,
    get_db,
    guardar_lectura,
    registrar_evento,
    guardar_estado_sistema,
    guardar_actuador_log,
    guardar_arm64,
)
from mqtt_handler import (
    configurar_mqtt,
    publicar,
    publicar_sensor,
    publicar_estado_global,
    T,
)


parser = argparse.ArgumentParser()
parser.add_argument("--sim", action="store_true", help="Modo simulacion sin GPIO")
args      = parser.parse_args()
SIMULACION = args.sim

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT   = 1883
MQTT_ID     = "G9_backend_main_v2"

CSV_PATH  = "lecturas.csv"
ARM64_DIR = "./arm64"
CSV_HEADER = ["ID","TEMP","HUM_AIRE","HUM_SUELO_1","HUM_SUELO_2","LUZ","GAS","RIEGO_1","RIEGO_2"]

UMBRAL_TEMP_ALTA  = 30
UMBRAL_HUM_BAJA   = 40
UMBRAL_HUM_ALTA   = 80
UMBRAL_LUZ_BAJA   = 300
UMBRAL_GAS_WARN   = 200
UMBRAL_GAS_EMRG   = 400
UMBRAL_SUELO_SECO = 35
UMBRAL_SUELO_SAT  = 80
DURACION_RIEGO    = 10

# Pines GPIO
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
PIN_DHT        = 4
CANAL_LDR      = 0
CANAL_GAS      = 1
CANAL_SUELO1   = 2
CANAL_SUELO2   = 3


state = {
    "lock":        threading.Lock(),
    "global":      "NORMAL",
    "modo":        "AUTOMATICO",
    "temp":        None,
    "hum":         None,
    "luz":         None,
    "gas":         None,
    "suelo1":      None,
    "suelo2":      None,
    "riego1":      False,
    "riego2":      False,
    "ventilador":  False,
    "luces":       False,
    "alarma":      False,
    "lecturas_csv":[],
    "lectura_id":  0,
}

timers_riego = {}


gpio_ok = False

if not SIMULACION:
    try:
        import RPi.GPIO as GPIO
        import adafruit_dht, board, busio
        import adafruit_mcp3xxx.mcp3008 as MCP
        from adafruit_mcp3xxx.analog_in import AnalogIn

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for pin in [PIN_BOMBA1, PIN_BOMBA2, PIN_VENTILADOR, PIN_LUZ1, PIN_LUZ2,
                    PIN_LED_VERDE, PIN_LED_AMAR, PIN_LED_ROJO, PIN_BUZZER]:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

        for pin in [PIN_BTN1, PIN_BTN2, PIN_BTN3, PIN_BTN4]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        dht_sensor   = adafruit_dht.DHT22(board.D4)
        spi          = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
        mcp          = MCP.MCP3008(spi, board.CE0)
        ch_ldr       = AnalogIn(mcp, CANAL_LDR)
        ch_gas       = AnalogIn(mcp, CANAL_GAS)
        ch_suelo1    = AnalogIn(mcp, CANAL_SUELO1)
        ch_suelo2    = AnalogIn(mcp, CANAL_SUELO2)

        gpio_ok = True
        print("[GPIO] Hardware inicializado")
    except Exception as e:
        print(f"[GPIO] Sin hardware: {e} — modo simulacion")


def leer_sensores():
    import random

    if gpio_ok:
        try:
            temp   = round(dht_sensor.temperature, 1)
            hum    = round(dht_sensor.humidity, 1)
            luz    = round(ch_ldr.value   / 65535 * 1000)
            gas    = round(ch_gas.value   / 65535 * 1000)
            suelo1 = round(100 - ch_suelo1.value / 65535 * 100)
            suelo2 = round(100 - ch_suelo2.value / 65535 * 100)
            return {"temp":temp,"hum":hum,"luz":luz,"gas":gas,"suelo1":suelo1,"suelo2":suelo2}
        except Exception as e:
            print(f"[Sensor] Error: {e}")
            return None
    else:
        def v(base, mn, mx, dn, dp):
            val = (base or (mn+mx)/2) + random.uniform(dn, dp)
            return round(max(mn, min(mx, val)), 1)
        return {
            "temp":   v(state["temp"],   18, 38, -0.5,  0.8),
            "hum":    v(state["hum"],    20, 95, -1.0,  1.0),
            "luz":    v(state["luz"],     0, 1000,-30,   25),
            "gas":    v(state["gas"],    50, 600, -8,   12),
            "suelo1": v(state["suelo1"], 10, 95, -1.5,  0.4),
            "suelo2": v(state["suelo2"], 10, 95, -1.2,  0.4),
        }


def gpio_set(pin, on):
    if gpio_ok:
        GPIO.output(pin, GPIO.HIGH if on else GPIO.LOW)

def set_leds(estado):
    gpio_set(PIN_LED_VERDE, estado == "NORMAL")
    gpio_set(PIN_LED_AMAR,  estado in ("ADVERTENCIA","RIEGO_ACTIVO","MODO_MANUAL"))
    gpio_set(PIN_LED_ROJO,  estado == "EMERGENCIA")

def activar_riego(area, activar, motivo="automatico"):
    global timers_riego
    key   = f"riego{area}"
    pin   = PIN_BOMBA1 if area == 1 else PIN_BOMBA2
    db    = get_db()

    with state["lock"]:
        suelo = state.get(f"suelo{area}")

        if activar:
            if suelo is not None and suelo >= UMBRAL_SUELO_SAT:
                log(f"[Riego] Area {area} BLOQUEADO — suelo saturado ({suelo}%)")
                return

            if state[key]:
                return

            state[key] = True
            gpio_set(pin, True)

            registrar_evento(f"riego_area{area}_ON", f"suelo={suelo}%", motivo, state["global"])
            guardar_actuador_log(f"riego_area{area}", "ON", motivo, state["global"])

            if area in timers_riego and timers_riego[area]:
                timers_riego[area].cancel()
            timers_riego[area] = threading.Timer(
                DURACION_RIEGO, activar_riego, args=[area, False, "fin_ciclo"]
            )
            timers_riego[area].start()
            log(f"[Riego] Area {area} ON — apagado en {DURACION_RIEGO}s")

        else:
            if area in timers_riego and timers_riego[area]:
                timers_riego[area].cancel()
                timers_riego[area] = None

            state[key] = False
            gpio_set(pin, False)

            registrar_evento(f"riego_area{area}_OFF", motivo, motivo, state["global"])
            guardar_actuador_log(f"riego_area{area}", "OFF", motivo, state["global"])
            log(f"[Riego] Area {area} OFF ({motivo})")

def set_ventilador(activar, motivo="automatico"):
    with state["lock"]:
        if state["ventilador"] == activar:
            return
        state["ventilador"] = activar
    gpio_set(PIN_VENTILADOR, activar)
    guardar_actuador_log("ventilador", "ON" if activar else "OFF", motivo, state["global"])
    log(f"[Vent] {'ON' if activar else 'OFF'} ({motivo})")

def set_luces(activar, motivo="automatico"):
    with state["lock"]:
        if state["luces"] == activar:
            return
        state["luces"] = activar
    gpio_set(PIN_LUZ1, activar)
    gpio_set(PIN_LUZ2, activar)
    guardar_actuador_log("luces", "ON" if activar else "OFF", motivo, state["global"])
    log(f"[Luces] {'ON' if activar else 'OFF'} ({motivo})")

def set_alarma(activar, motivo="automatico"):
    with state["lock"]:
        if state["alarma"] == activar:
            return
        state["alarma"] = activar
    gpio_set(PIN_BUZZER,   activar)
    gpio_set(PIN_LED_ROJO, activar)
    guardar_actuador_log("alarma", "ON" if activar else "OFF", motivo, state["global"])
    log(f"[Alarma] {'ON' if activar else 'OFF'} ({motivo})")


def aplicar_automatismos(lectura):
    if state["modo"] != "AUTOMATICO":
        if lectura["gas"] >= UMBRAL_GAS_EMRG:
            set_ventilador(True, "gas_emergencia_override")
            set_alarma(True, "gas_emergencia_override")
        return

    if lectura["temp"] >= UMBRAL_TEMP_ALTA:
        set_ventilador(True, "temperatura_alta")
    elif lectura["temp"] < UMBRAL_TEMP_ALTA - 2:
        if state.get("gas", 0) < UMBRAL_GAS_EMRG:
            set_ventilador(False, "temperatura_normal")

    if lectura["gas"] >= UMBRAL_GAS_EMRG:
        set_ventilador(True, "gas_emergencia")
        set_alarma(True, "gas_emergencia")
        registrar_evento("gas_emergencia", lectura["gas"], "sensor", state["global"])
    elif lectura["gas"] < UMBRAL_GAS_EMRG and state["alarma"]:
        set_alarma(False, "gas_normalizado")

    if lectura["luz"] < UMBRAL_LUZ_BAJA:
        set_luces(True, "luz_baja")
    elif lectura["luz"] >= UMBRAL_LUZ_BAJA and state["luces"]:
        set_luces(False, "luz_suficiente")

    if lectura["suelo1"] < UMBRAL_SUELO_SECO and not state["riego1"]:
        activar_riego(1, True, "suelo_seco_auto")
    if lectura["suelo2"] < UMBRAL_SUELO_SECO and not state["riego2"]:
        activar_riego(2, True, "suelo_seco_auto")

def calcular_estado():
    s = state
    if s.get("gas", 0) >= UMBRAL_GAS_EMRG:
        return "EMERGENCIA"
    warn = any([
        s.get("temp",  0) >= UMBRAL_TEMP_ALTA,
        (s.get("hum") or 50) <= UMBRAL_HUM_BAJA,
        (s.get("hum") or 50) >= UMBRAL_HUM_ALTA,
        (s.get("suelo1") or 50) <= UMBRAL_SUELO_SECO,
        (s.get("suelo2") or 50) <= UMBRAL_SUELO_SECO,
        (s.get("luz")  or 500) <= UMBRAL_LUZ_BAJA,
        s.get("gas",   0) >= UMBRAL_GAS_WARN,
    ])
    if warn:
        return "ADVERTENCIA"
    if s["riego1"] or s["riego2"]:
        return "RIEGO_ACTIVO"
    if s["modo"] == "MANUAL":
        return "MODO_MANUAL"
    return "NORMAL"

def actualizar_estado_global():
    nuevo    = calcular_estado()
    anterior = state["global"]
    with state["lock"]:
        state["global"] = nuevo
    set_leds(nuevo)
    publicar_estado_global(nuevo, state["modo"], {
        "temp": state["temp"], "hum": state["hum"],
        "suelo1": state["suelo1"], "suelo2": state["suelo2"],
        "luz": state["luz"], "gas": state["gas"],
    })
    if nuevo != anterior:
        registrar_evento("estado_global", nuevo, "sistema", nuevo)
        log(f"[Estado] {anterior} -> {nuevo}")


def publicar_sensores(lectura):
    def st_temp(v):  return "ALTA" if v >= UMBRAL_TEMP_ALTA else "NORMAL"
    def st_hum(v):   return "BAJA" if v < UMBRAL_HUM_BAJA else "ALTA" if v > UMBRAL_HUM_ALTA else "NORMAL"
    def st_luz(v):   return "BAJA" if v < UMBRAL_LUZ_BAJA else "NORMAL"
    def st_gas(v):   return "GAS_EMERGENCIA" if v >= UMBRAL_GAS_EMRG else "GAS_ADVERTENCIA" if v >= UMBRAL_GAS_WARN else "GAS_NORMAL"
    def st_suelo(v): return "SECO" if v < UMBRAL_SUELO_SECO else "SATURADO" if v > UMBRAL_SUELO_SAT else "NORMAL"

    publicar_sensor("temp",   lectura["temp"],   "C",   st_temp(lectura["temp"]),    {"sensor": "DHT22"})
    publicar_sensor("hum",    lectura["hum"],    "%",   st_hum(lectura["hum"]),      {"sensor": "DHT22"})
    publicar_sensor("luz",    lectura["luz"],    "lux", st_luz(lectura["luz"]),      {"sensor": "LDR", "iluminacion_activa": lectura["luz"] < UMBRAL_LUZ_BAJA})
    publicar_sensor("gas",    lectura["gas"],    "ppm", st_gas(lectura["gas"]),      {"sensor": "MQ-2", "alarma_activa": lectura["gas"] >= UMBRAL_GAS_EMRG})
    publicar_sensor("suelo1", lectura["suelo1"], "%",   st_suelo(lectura["suelo1"]),{"sensor": "FC-28", "area": "area1", "riego_activo": state["riego1"]})
    publicar_sensor("suelo2", lectura["suelo2"], "%",   st_suelo(lectura["suelo2"]),{"sensor": "FC-28", "area": "area2", "riego_activo": state["riego2"]})


def acumular_csv(lectura):
    with state["lock"]:
        state["lectura_id"] += 1
        fila = [state["lectura_id"], lectura["temp"], lectura["hum"],
                lectura["suelo1"], lectura["suelo2"], lectura["luz"], lectura["gas"],
                1 if state["riego1"] else 0, 1 if state["riego2"] else 0]
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
            for i, fila in enumerate(ultimas, 1):
                fila[0] = i
                writer.writerow(fila)
            writer.writerow(["$"])
        log(f"[CSV] lecturas.csv actualizado ({len(ultimas)} filas)")
    except Exception as e:
        log(f"[CSV] Error: {e}")

def ejecutar_arm64():
    if not os.path.exists(CSV_PATH):
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
            continue
        try:
            subprocess.run([bin_path], timeout=15, check=True)
            resultado = {}
            with open(out_path) as f:
                for linea in f:
                    if "=" in linea:
                        k, v = linea.strip().split("=", 1)
                        resultado[k.strip()] = v.strip()
            log(f"[ARM64] {binario}: {resultado}")
            publicar(f"invernadero/G9/arm64/{binario}", json.dumps(resultado), qos=1)
            guardar_arm64(binario, resultado)
        except Exception as e:
            log(f"[ARM64] Error en {binario}: {e}")


def hilo_botones():
    if not gpio_ok:
        return
    prev = {p: True for p in [PIN_BTN1, PIN_BTN2, PIN_BTN3, PIN_BTN4]}
    while True:
        b = {p: GPIO.input(p) for p in [PIN_BTN1, PIN_BTN2, PIN_BTN3, PIN_BTN4]}
        if not b[PIN_BTN1] and prev[PIN_BTN1]:
            nuevo = "MANUAL" if state["modo"] == "AUTOMATICO" else "AUTOMATICO"
            state["modo"] = nuevo
            registrar_evento("modo", nuevo, "boton_1", state["global"])
        if not b[PIN_BTN2] and prev[PIN_BTN2]:
            activar_riego(1, not state["riego1"], "boton_2")
        if not b[PIN_BTN3] and prev[PIN_BTN3]:
            set_luces(not state["luces"], "boton_3")
        if not b[PIN_BTN4] and prev[PIN_BTN4]:
            set_alarma(False, "boton_4")
        prev = b
        time.sleep(0.05)


def hilo_sensores():
    arm64_counter = 0
    while True:
        lectura = leer_sensores()
        if lectura is None:
            log("[Sensor] Fallo — reintentando en 2s")
            time.sleep(2)
            continue

        with state["lock"]:
            for k in ["temp","hum","luz","gas","suelo1","suelo2"]:
                state[k] = lectura[k]

        publicar_sensores(lectura)
        guardar_lectura(lectura, state["global"])
        guardar_estado_sistema(
            state["global"], state["modo"],
            {k: state[k] for k in ["temp","hum","luz","gas","suelo1","suelo2"]},
            {k: state[k] for k in ["riego1","riego2","ventilador","luces","alarma"]},
        )
        acumular_csv(lectura)
        aplicar_automatismos(lectura)
        actualizar_estado_global()

        arm64_counter += 1
        if arm64_counter >= 30 and len(state["lecturas_csv"]) >= 30:
            arm64_counter = 0
            threading.Thread(target=ejecutar_arm64, daemon=True).start()

        log(f"[Loop] T={lectura['temp']}C H={lectura['hum']}% "
            f"S1={lectura['suelo1']}% S2={lectura['suelo2']}% "
            f"Luz={lectura['luz']} Gas={lectura['gas']} [{state['global']}]")
        time.sleep(5)

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


if __name__ == "__main__":
    print("=" * 52)
    print("  Invernadero IoT — ACYE1 USAC — Grupo 9")
    print(f"  Modo: {'SIMULACION' if SIMULACION or not gpio_ok else 'HARDWARE REAL'}")
    print("=" * 52)

    # 1. MongoDB
    db = mongo_conectar()

    # 2. MQTT — inyectar state, db y funciones de actuadores
    mqtt_client = configurar_mqtt(
        broker     = MQTT_BROKER,
        port       = MQTT_PORT,
        client_id  = MQTT_ID,
        state      = state,
        db         = db,
        actuadores = {
            "activar_riego":  activar_riego,
            "set_ventilador": set_ventilador,
            "set_luces":      set_luces,
            "set_alarma":     set_alarma,
        },
    )

    # 3. Carpeta ARM64
    os.makedirs(ARM64_DIR, exist_ok=True)

    # 4. Botones fisicos
    if gpio_ok:
        threading.Thread(target=hilo_botones, daemon=True).start()

    # 5. Evento de inicio
    registrar_evento("sistema", "INICIADO", "main_v2.py", "NORMAL")
    time.sleep(2)

    # 6. Loop principal
    log("[Main] Sistema corriendo — Ctrl+C para salir\n")
    try:
        hilo_sensores()
    except KeyboardInterrupt:
        log("\n[Main] Apagando sistema...")
        if gpio_ok:
            for pin in [PIN_BOMBA1, PIN_BOMBA2, PIN_VENTILADOR, PIN_LUZ1, PIN_LUZ2,
                        PIN_LED_VERDE, PIN_LED_AMAR, PIN_LED_ROJO, PIN_BUZZER]:
                GPIO.output(pin, GPIO.LOW)
            GPIO.cleanup()
        for t in timers_riego.values():
            if t: t.cancel()
        publicar(T["global"], json.dumps({"estado":"OFFLINE","timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}), retain=True)
        registrar_evento("sistema", "APAGADO", "main_v2.py", "OFFLINE")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        log("[Main] Sistema apagado correctamente")