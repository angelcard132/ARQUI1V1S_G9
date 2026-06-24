import time
import json
import threading
import csv
import os
import sys
import subprocess
import argparse
from datetime import datetime
from arm64_live_runner import ARM64LiveRunner

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

ARM64_LIVE_BIN = os.path.join(os.path.dirname(__file__), "arm64", "motor_vivo")
arm64_live = ARM64LiveRunner(ARM64_LIVE_BIN)

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT   = 1883
MQTT_ID     = "G9_backend_main_v2"

CSV_PATH  = "lecturas.csv"
ARM64_DIR = "./arm64"
CSV_HEADER = ["ID","TEMP","HUM_AIRE","HUM_SUELO_1","HUM_SUELO_2","LUZ","GAS","RIEGO_1","RIEGO_2"]

#  Umbrales 
UMBRAL_TEMP_ALTA  = 33
UMBRAL_HUM_BAJA   = 30
UMBRAL_HUM_ALTA   = 85
UMBRAL_LUZ_BAJA   = 200
UMBRAL_GAS_WARN   = 300
UMBRAL_GAS_EMRG   = 420
UMBRAL_SUELO_SECO = 25
UMBRAL_SUELO_SAT  = 90
DURACION_RIEGO    = 10

PIN_BOMBA      = 20
PIN_VENTILADOR = 21
PIN_LUZ1       = 23
PIN_LUZ2       = 24
PIN_LED_VERDE  = 5
PIN_LED_AMAR   = 6
PIN_LED_ROJO   = 13
PIN_BUZZER     = 12
PIN_BTN1       = 0  # cambia entre automatico y manual
PIN_BTN2       = 19  # riego manual
PIN_BTN3       = 26 # encender y apagar luces manual
PIN_BTN4       = 16 # silenciar buzzer y restablecer alerta
PIN_DHT        = 17

ARDUINO_PORT     = "/dev/ttyACM0"   
ARDUINO_BAUDRATE = 9600

#  Estado global 
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


gpio_ok    = False
arduino_ok = False
arduino    = None   # objeto serial global

if not SIMULACION:
    try:
        import RPi.GPIO as GPIO
        import adafruit_dht, board

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for pin in [ PIN_BOMBA, PIN_VENTILADOR,
                    PIN_LUZ1, PIN_LUZ2, PIN_LED_VERDE,
                    PIN_LED_AMAR, PIN_LED_ROJO, PIN_BUZZER]:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

        for pin in [PIN_BTN1, PIN_BTN2, PIN_BTN3, PIN_BTN4]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        dht_sensor = adafruit_dht.DHT11(board.D17)

        gpio_ok = True
        print("[GPIO] Raspberry Pi GPIO inicializado (actuadores + DHT)")
    except Exception as e:
        print(f"[GPIO] Sin hardware GPIO: {e} — modo simulacion")


    try:
        import serial as pyserial
        arduino = pyserial.Serial(ARDUINO_PORT, ARDUINO_BAUDRATE, timeout=3)
        time.sleep(2)  # esperar reset del Arduino tras abrir puerto
        arduino_ok = True
        print(f"[Arduino] Conectado en {ARDUINO_PORT} @ {ARDUINO_BAUDRATE} baud")
    except Exception as e:
        print(f"[Arduino] Sin conexión serial: {e} — sensores analógicos simulados")


_ultimo_arduino = {"ldr": 300, "gas": 100, "suelo1": 500, "suelo2": 500}

def leer_arduino():
    """
    Lee una línea del Arduino con formato: LUZ:320, GAS:145, SUELO:680
    Retorna dict con claves en minúscula: {"ldr":320,"gas":145,"suelo1":680}
    """
    global _ultimo_arduino
    if not arduino_ok or arduino is None:
        return None
    try:
        arduino.reset_input_buffer()
        linea = arduino.readline().decode("utf-8", errors="ignore").strip()
        if not linea:
            return _ultimo_arduino

        # Parsear formato CLAVE:VALOR,CLAVE:VALOR
        datos = {}
        for parte in linea.split(","):
            parte = parte.strip()
            if ":" not in parte:
                continue
            clave, valor = parte.split(":")
            datos[clave.strip().upper()] = int(valor.strip())


        resultado = {
            "ldr":    datos.get("LUZ",   300),
            "gas":    datos.get("GAS",   100),
            "suelo1": datos.get("SUELO1", datos.get("SUELO", 500)),
            "suelo2": datos.get("SUELO2", datos.get("SUELO", 500)),
        }
        _ultimo_arduino = resultado
        return resultado

    except Exception as e:
        print(f"[Arduino] Error parseo: {e} — línea: '{linea}'")
        return _ultimo_arduino

def convertir_analogico(raw_ldr, raw_gas, raw_suelo1, raw_suelo2):
    """
    Convierte valores ADC del Arduino (0-1023) a unidades del sistema.
    Sensor de suelo RESISTIVO: 1023=seco(0%), 0=húmedo(100%)
    """
    # LDR: valor alto = poca luz. Escalamos a 0-1000.
    luz = round(raw_ldr / 1023 * 1000)

    # Gas: valor alto = más gas. Escalamos a 0-1000.
    gas = round(raw_gas / 1023 * 1000)

    suelo1 = round((1023 - raw_suelo1) / 1023 * 100)
    suelo2 = round((1023 - raw_suelo2) / 1023 * 100)

    # Clamp por seguridad
    suelo1 = max(0, min(100, suelo1))
    suelo2 = max(0, min(100, suelo2))

    return luz, gas, suelo1, suelo2


lcd = None
lcd_ok = False

if not SIMULACION:
    try:
        from RPLCD.i2c import CharLCD
        lcd = CharLCD(
            i2c_expander='PCF8574',
            address=0x27,
            port=1,
            cols=16,
            rows=2,
            dotsize=8
        )
        lcd.clear()
        lcd.write_string("Iniciando...")
        lcd_ok = True
        print("[LCD] Pantalla I2C inicializada")
    except Exception as e:
        print(f"[LCD] Sin LCD: {e}")

def leer_sensores():
    import random

    if gpio_ok:
        # 1. DHT22 — temperatura y humedad (sigue igual, directo en Raspi)
        try:
            temp = round(dht_sensor.temperature, 1)
            hum  = round(dht_sensor.humidity,    1)
        except Exception as e:
            print(f"[DHT] Error: {e}")
            temp = state["temp"] or 25.0
            hum  = state["hum"]  or 60.0

        # 2. Arduino — sensores analógicos (LDR, MQ, suelo)
        ard = leer_arduino()
        if ard is not None:
            luz, gas, suelo1, suelo2 = convertir_analogico(
                ard.get("ldr",    300),
                ard.get("gas",    100),
                ard.get("suelo1", 500),
                ard.get("suelo2", 500),
            )
        else:

            luz    = round((state["luz"]    or 400) + random.uniform(-20, 15))
            gas    = round((state["gas"]    or 100) + random.uniform(-5,  10))
            suelo1 = round((state["suelo1"] or 50)  + random.uniform(-1,   0.4))
            suelo2 = round((state["suelo2"] or 50)  + random.uniform(-1,   0.4))
            print("[Arduino] Sin datos — usando simulación para analógicos")

        return {
            "temp":   temp,
            "hum":    hum,
            "luz":    max(0, min(1000, luz)),
            "gas":    max(0, min(1000, gas)),
            "suelo1": max(0, min(100,  suelo1)),
            "suelo2": max(0, min(100,  suelo2)),
        }


    else:
        def v(base, mn, mx, dn, dp):
            val = (base or (mn + mx) / 2) + random.uniform(dn, dp)
            return round(max(mn, min(mx, val)), 1)
        return {
            "temp":   round(random.uniform(20, 38), 1),
            "hum":    round(random.uniform(20, 95), 1),
            "luz":    round(random.uniform(100, 1000), 1),
            "gas":    round(random.uniform(50, 500), 1),
            "suelo1": round(random.uniform(10, 95), 1),
            "suelo2": round(random.uniform(10, 95), 1),
        }



def gpio_set(pin, on):
    if gpio_ok:
        GPIO.output(pin, GPIO.HIGH if on else GPIO.LOW)

def set_leds(estado):
    gpio_set(PIN_LED_VERDE, estado == "NORMAL")
    gpio_set(PIN_LED_AMAR,  estado in ("ADVERTENCIA", "RIEGO_ACTIVO", "MODO_MANUAL"))
    gpio_set(PIN_LED_ROJO,  estado == "EMERGENCIA")

def activar_riego(area, activar, motivo="automatico"):
    global timers_riego

    key = f"riego{area}"
    pin = PIN_BOMBA

    with state["lock"]:
        suelo = state.get(f"suelo{area}")

        if activar:
            if suelo is not None and suelo >= UMBRAL_SUELO_SAT:
                log(f"[Riego] Area {area} BLOQUEADO — suelo saturado ({suelo}%)")
                return

            if state["riego1"] or state["riego2"]:
                return

            state[key] = True
            gpio_set(pin, True)

            registrar_evento(f"riego_area{area}_ON", f"suelo={suelo}%", motivo, state["global"])
            guardar_actuador_log(f"riego_area{area}", "ON", motivo, state["global"])

            if area in timers_riego and timers_riego[area]:
                timers_riego[area].cancel()

            timers_riego[area] = threading.Timer(
                DURACION_RIEGO,
                activar_riego,
                args=[area, False, "fin_ciclo"]
            )
            timers_riego[area].start()

            log(f"[Riego] Bomba ON para Area {area} — apagado en {DURACION_RIEGO}s")

        else:
            if area in timers_riego and timers_riego[area]:
                timers_riego[area].cancel()
                timers_riego[area] = None

            state[key] = False

            if not state["riego1"] and not state["riego2"]:
                gpio_set(pin, False)

            registrar_evento(f"riego_area{area}_OFF", motivo, motivo, state["global"])
            guardar_actuador_log(f"riego_area{area}", "OFF", motivo, state["global"])
            log(f"[Riego] Bomba OFF para Area {area} ({motivo})")

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
        s.get("temp",  0)  >= UMBRAL_TEMP_ALTA,
        (s.get("hum")  or 50) <= UMBRAL_HUM_BAJA,
        (s.get("hum")  or 50) >= UMBRAL_HUM_ALTA,
        (s.get("suelo1") or 50) <= UMBRAL_SUELO_SECO,
        (s.get("suelo2") or 50) <= UMBRAL_SUELO_SECO,
        (s.get("luz")  or 500) <= UMBRAL_LUZ_BAJA,
        s.get("gas",   0)  >= UMBRAL_GAS_WARN,
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
    def st_temp(v):  return "ALTA"  if v >= UMBRAL_TEMP_ALTA  else "NORMAL"
    def st_hum(v):   return "BAJA"  if v < UMBRAL_HUM_BAJA    else "ALTA" if v > UMBRAL_HUM_ALTA else "NORMAL"
    def st_luz(v):   return "BAJA"  if v < UMBRAL_LUZ_BAJA    else "NORMAL"
    def st_gas(v):   return "GAS_EMERGENCIA" if v >= UMBRAL_GAS_EMRG else "GAS_ADVERTENCIA" if v >= UMBRAL_GAS_WARN else "GAS_NORMAL"
    def st_suelo(v): return "SECO"  if v < UMBRAL_SUELO_SECO  else "SATURADO" if v > UMBRAL_SUELO_SAT else "NORMAL"

    publicar_sensor("temp",   lectura["temp"],   "C",   st_temp(lectura["temp"]),    {"sensor": "DHT22"})
    publicar_sensor("hum",    lectura["hum"],    "%",   st_hum(lectura["hum"]),      {"sensor": "DHT22"})
    publicar_sensor("luz",    lectura["luz"],    "lux", st_luz(lectura["luz"]),      {"sensor": "LDR+Arduino"})
    publicar_sensor("gas",    lectura["gas"],    "ppm", st_gas(lectura["gas"]),      {"sensor": "MQ+Arduino", "alarma_activa": lectura["gas"] >= UMBRAL_GAS_EMRG})
    publicar_sensor("suelo1", lectura["suelo1"], "%",   st_suelo(lectura["suelo1"]),{"sensor": "FC-28+Arduino", "area": "area1", "riego_activo": state["riego1"]})
    publicar_sensor("suelo2", lectura["suelo2"], "%",   st_suelo(lectura["suelo2"]),{"sensor": "FC-28+Arduino", "area": "area2", "riego_activo": state["riego2"]})


def acumular_csv(lectura):
    with state["lock"]:
        state["lectura_id"] += 1
        fila = [
            state["lectura_id"],
            lectura["temp"],   lectura["hum"],
            lectura["suelo1"], lectura["suelo2"],
            lectura["luz"],    lectura["gas"],
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
            for i, fila in enumerate(ultimas, 1):
                fila[0] = i
                fila_csv = [
                    int(x) if isinstance(x, float) else x
                    for x in fila
                ]   
                writer.writerow(fila_csv)
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

# cambiar manual/automatico
def btn1_callback(channel):
    nuevo = "MANUAL" if state["modo"] == "AUTOMATICO" else "AUTOMATICO"
    state["modo"] = nuevo
    registrar_evento("modo", nuevo, "boton_1", state["global"])
    log(f"[Botones] Modo cambiado a {nuevo}")

# activar riego manual
def btn2_callback(channel):
    activar_riego(1, True, "boton_2")

# activar luces manual
def btn3_callback(channel):
    set_luces(not state["luces"], "boton_3")

# apagar alarma
def btn4_callback(channel):
    set_alarma(False, "boton_4")

def configurar_botones():
    if not gpio_ok: return
    
    GPIO.add_event_detect(PIN_BTN1, GPIO.FALLING, callback=btn1_callback, bouncetime=300)
    GPIO.add_event_detect(PIN_BTN2, GPIO.FALLING, callback=btn2_callback, bouncetime=300)
    GPIO.add_event_detect(PIN_BTN3, GPIO.FALLING, callback=btn3_callback, bouncetime=300)
    GPIO.add_event_detect(PIN_BTN4, GPIO.FALLING, callback=btn4_callback, bouncetime=300)


def mapear(valor, in_min, in_max, out_min, out_max):
    """Mapea un rango a otro — igual que en tu código de prueba."""
    if in_max == in_min:
        return out_min
    return int((valor - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)


def actualizar_lcd(lectura):
    """
    Muestra datos rotativos en la LCD según el estado del sistema.
    En emergencia muestra alerta fija.
    """
    if not lcd_ok or lcd is None:
        return
    try:
        estado = state["global"]

        if estado == "EMERGENCIA":
            lcd.clear()
            lcd.write_string("¡¡EMERGENCIA !!")
            lcd.crlf()
            lcd.write_string(f"Gas:{lectura['gas']:<4} PELIGRO")
            return


        pantalla = state.get("lcd_pantalla", 0)
        state["lcd_pantalla"] = (pantalla + 1) % 5

        lcd.clear()

        if pantalla == 0:
            lcd.write_string(f"Temp: {lectura['temp']}C")
            lcd.crlf()
            lcd.write_string(f"Hum:  {lectura['hum']}%")

        elif pantalla == 1:
            lcd.write_string(f"Suelo1: {lectura['suelo1']}%")
            lcd.crlf()
            lcd.write_string(f"Suelo2: {lectura['suelo2']}%")

        elif pantalla == 2:
            lcd.write_string(f"Luz:  {lectura['luz']}")
            lcd.crlf()
            lcd.write_string(f"Gas:  {lectura['gas']}")

        elif pantalla == 3:
            riego_str = "ON " if state["riego1"] else "OFF"
            riego2_str = "ON " if state["riego2"] else "OFF"
            lcd.write_string(f"Riego1:{riego_str} R2:{riego2_str}")
            lcd.crlf()
            vent_str = "ON " if state["ventilador"] else "OFF"
            luz_str  = "ON " if state["luces"]      else "OFF"
            lcd.write_string(f"Vent:{vent_str} Luz:{luz_str}")

        elif pantalla == 4:
            lcd.write_string(f"Estado:")
            lcd.crlf()
            lcd.write_string(estado[:16])

    except Exception as e:
        print(f"[LCD] Error al escribir: {e}")

def hilo_sensores():
    arm64_counter = 0
    while True:
        lectura = leer_sensores()
        if lectura is None:
            log("[Sensor] Fallo — reintentando en 2s")
            time.sleep(2)
            continue

        with state["lock"]:
            for k in ["temp", "hum", "luz", "gas", "suelo1", "suelo2"]:
                state[k] = lectura[k]

        publicar_sensores(lectura)
        guardar_lectura(lectura, state["global"])
        guardar_estado_sistema(
            state["global"], state["modo"],
            {k: state[k] for k in ["temp", "hum", "luz", "gas", "suelo1", "suelo2"]},
            {k: state[k] for k in ["riego1", "riego2", "ventilador", "luces", "alarma"]},
        )
        acumular_csv(lectura)
        respuesta_arm64 = arm64_live.consultar(lectura, state["modo"])
        ejecutar_decision_arm64(respuesta_arm64)
        try:
            guardar_arm64("motor_vivo", {
                "respuesta": respuesta_arm64,
                "temp": int(lectura["temp"]),
                "hum": int(lectura["hum"]),
                "suelo1": int(lectura["suelo1"]),
                "suelo2": int(lectura["suelo2"]),
                "luz": int(lectura["luz"]),
                "gas": int(lectura["gas"]),
                "modo": state["modo"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception as e:
            log(f"[ARM64 LIVE] Error guardando MongoDB: {e}")
        actualizar_lcd(lectura)      
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



def ejecutar_decision_arm64(respuesta):
    log(f"[ARM64 LIVE] {respuesta}")

    if respuesta == "ACTION=ALARM_ON":
        set_alarma(True, "arm64_live")
        set_ventilador(True, "arm64_live")

    elif respuesta == "ACTION=RIEGO_1_ON":
        activar_riego(1, True, "arm64_live")

    elif respuesta == "ACTION=RIEGO_2_ON":
        activar_riego(2, True, "arm64_live")

    elif respuesta == "ACTION=LIGHT_ON":
        set_luces(True, "arm64_live")

    elif respuesta == "ACTION=FAN_ON":
        set_ventilador(True, "arm64_live")

    elif respuesta == "ACTION=LED_GREEN":
        set_leds("NORMAL")

    else:
        log("[ARM64 LIVE] Sin accion reconocida")




if __name__ == "__main__":
    print("=" * 52)
    print("  Invernadero IoT — ACYE1 USAC — Grupo 9")
    modo_str = "SIMULACION"
    if not SIMULACION:
        if gpio_ok and arduino_ok:
            modo_str = "HARDWARE COMPLETO (Raspi + Arduino)"
        elif gpio_ok:
            modo_str = "HARDWARE PARCIAL (Raspi OK, Arduino no encontrado)"
        elif arduino_ok:
            modo_str = "HARDWARE PARCIAL (Arduino OK, GPIO no disponible)"
    print(f"  Modo: {modo_str}")
    print("=" * 52)

    # 1. MongoDB
    db = mongo_conectar()

    # 2. MQTT
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

    arm64_live.iniciar()

    # 4. Botones físicos
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
            for pin in [PIN_BOMBA, PIN_VENTILADOR,
                        PIN_LUZ1, PIN_LUZ2, PIN_LED_VERDE,
                        PIN_LED_AMAR, PIN_LED_ROJO, PIN_BUZZER]:
                GPIO.output(pin, GPIO.LOW)
            GPIO.cleanup()
        for t in timers_riego.values():
            if t: t.cancel()
        publicar(T["global"], json.dumps({
            "estado": "OFFLINE",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), retain=True)
        registrar_evento("sistema", "APAGADO", "main_v2.py", "OFFLINE")
        arm64_live.cerrar()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        log("[Main] Sistema apagado correctamente")
