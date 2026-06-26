import time
import json
import threading
import csv
import os
import argparse
from datetime import datetime

from arm64_live_runner import ARM64LiveRunner
from mongo_handler import (
    conectar as mongo_conectar,
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
args = parser.parse_args()
SIMULACION = args.sim

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT   = 1883
MQTT_ID     = "G9_backend_main_v2"

CSV_PATH   = "lecturas.csv"
ARM64_DIR  = "./arm64"
CSV_HEADER = ["ID", "TEMP", "HUM_AIRE", "HUM_SUELO_1", "HUM_SUELO_2",
              "LUZ", "GAS", "RIEGO_1", "RIEGO_2"]
CICLO_SENSORES = 2  # segundos entre lecturas publicadas

ARM64_LIVE_BIN = os.path.join(os.path.dirname(__file__), "arm64", "motor_vivo")
arm64_live = ARM64LiveRunner(ARM64_LIVE_BIN)

UMBRAL_TEMP_ALTA  = 33
UMBRAL_HUM_BAJA   = 25
UMBRAL_HUM_ALTA   = 85
UMBRAL_LUZ_BAJA   = 200
UMBRAL_GAS_WARN   = 180
UMBRAL_GAS_EMRG   = 250
UMBRAL_SUELO_SECO = 25
UMBRAL_SUELO_SAT  = 90
DURACION_RIEGO    = 10  # segundos que dura un ciclo de riego


PIN_LUZ1       = 23
PIN_LUZ2       = 24
PIN_LED_VERDE  = 5
PIN_LED_AMAR   = 6
PIN_LED_ROJO   = 13
PIN_BTN1       = 25  # cambia entre automático y manual
PIN_BTN2       = 19  # riego manual (área 1)
PIN_BTN3       = 26  # encender/apagar luces manual
PIN_BTN4       = 16  # silenciar buzzer / restablecer alerta
PIN_DHT        = 17

GPIO_OUTPUT_PINS = [PIN_LUZ1, PIN_LUZ2, PIN_LED_VERDE, PIN_LED_AMAR, PIN_LED_ROJO]
GPIO_INPUT_PINS  = [PIN_BTN1, PIN_BTN2, PIN_BTN3, PIN_BTN4]

CMD_RIEGO_ON   = "A"
CMD_RIEGO_OFF  = "B"
CMD_VENT_ON    = "C"
CMD_VENT_OFF   = "D"
CMD_BUZZER_ON  = "E"
CMD_BUZZER_OFF = "F"

ARDUINO_PORT     = "/dev/ttyACM0"
ARDUINO_BAUDRATE = 9600
ARDUINO_ECHOS = {
    "LISTO",
    "BOMBA:ON", "BOMBA:OFF",
    "VENTILADOR:ON", "VENTILADOR:OFF",
    "BUZZER:ON", "BUZZER:OFF",
}

state = {
    "lock":              threading.Lock(),
    "global":            "NORMAL",
    "modo":              "AUTOMATICO",
    "temp":              None,
    "hum":               None,
    "luz":               None,
    "gas":               None,
    "suelo1":            None,
    "suelo2":            None,
    "riego1":            False,
    "riego2":            False,
    "ventilador":        False,
    "luces":             False,
    "alarma":            False,
    "alarma_silenciada": False,
    "lcd_pantalla":      0,
    "lecturas_csv":      [],
    "lectura_id":        0,
}

timers_riego  = {1: None, 2: None}
arduino_lock  = threading.Lock()
ultimo_boton  = {"btn1": 0.0, "btn2": 0.0, "btn3": 0.0, "btn4": 0.0}
arm64_live_cond = threading.Condition()
arm64_live_pendiente = None
arm64_live_detener = False

gpio_ok    = False
arduino_ok = False
arduino    = None
dht_sensor = None
GPIO       = None

lcd    = None
lcd_ok = False


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def inicializar_gpio():
    """Inicializa GPIO de la Raspberry Pi: LEDs, luces, botones y DHT11."""
    global gpio_ok, dht_sensor, GPIO
    try:
        import RPi.GPIO as _GPIO
        import adafruit_dht
        import board
        GPIO = _GPIO

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for pin in GPIO_OUTPUT_PINS:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

        for pin in GPIO_INPUT_PINS:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        dht_sensor = adafruit_dht.DHT11(board.D17)

        gpio_ok = True
        log("[GPIO] Raspberry Pi GPIO inicializado (LEDs, luces, botones, DHT11)")
    except Exception as e:
        log(f"[GPIO] Sin hardware GPIO: {e} — modo simulación")


def inicializar_arduino():
    global arduino, arduino_ok
    try:
        import serial as pyserial
        arduino = pyserial.Serial(ARDUINO_PORT, ARDUINO_BAUDRATE, timeout=0.5)
        time.sleep(2)  # esperar reset del Arduino tras abrir el puerto
        arduino_ok = True
        log(f"[Arduino] Conectado en {ARDUINO_PORT} @ {ARDUINO_BAUDRATE} baud")
    except Exception as e:
        log(f"[Arduino] Sin conexión serial: {e} — sensores analógicos y actuadores simulados")


def inicializar_lcd():
    global lcd, lcd_ok
    try:
        from RPLCD.i2c import CharLCD
        lcd = CharLCD(i2c_expander="PCF8574", address=0x27, port=1, cols=16, rows=2, dotsize=8)
        lcd.clear()
        lcd.write_string("Iniciando...")
        lcd_ok = True
        log("[LCD] Pantalla I2C inicializada")
    except Exception as e:
        log(f"[LCD] Sin LCD: {e}")


if not SIMULACION:
    inicializar_gpio()
    inicializar_arduino()
    inicializar_lcd()

_ultimo_arduino = {"ldr": 300, "gas": 100, "suelo1": 500, "suelo2": 500}


def leer_arduino():

    global _ultimo_arduino

    if not arduino_ok or arduino is None:
        return None

    try:
        with arduino_lock:
            linea = arduino.readline().decode("utf-8", errors="ignore").strip()
    except Exception as e:
        log(f"[Arduino] Error de lectura serial: {e}")
        return _ultimo_arduino

    if not linea or linea in ARDUINO_ECHOS:
        return _ultimo_arduino

    datos = {}
    for parte in linea.split(","):
        parte = parte.strip()
        if ":" not in parte:
            continue
        clave, valor = parte.split(":", 1)
        clave = clave.strip().upper()
        valor = valor.strip()
        if clave not in ("LUZ", "GAS", "SUELO", "SUELO1", "SUELO2"):
            continue
        if not valor.lstrip("-").isdigit():
            continue
        datos[clave] = int(valor)

    if not datos:
        return _ultimo_arduino

    resultado = {
        "ldr":    datos.get("LUZ", 300),
        "gas":    datos.get("GAS", 100),
        "suelo1": datos.get("SUELO1", datos.get("SUELO", 500)),
        "suelo2": datos.get("SUELO2", datos.get("SUELO", 500)),
    }
    _ultimo_arduino = resultado
    return resultado


def enviar_arduino(comando):
    if not arduino_ok or arduino is None:
        log(f"[Arduino] No conectado, comando ignorado: {comando}")
        return False
    try:
        with arduino_lock:
            arduino.write(comando.encode("utf-8"))
            arduino.flush()
        log(f"[Arduino] CMD -> {comando}")
        return True
    except Exception as e:
        log(f"[Arduino] Error enviando comando '{comando}': {e}")
        return False


def convertir_analogico(raw_ldr, raw_gas, raw_suelo1, raw_suelo2):

    luz = round(raw_ldr / 1023 * 1000)
    gas = round(raw_gas / 1023 * 1000)
    suelo1 = round((1023 - raw_suelo1) / 1023 * 100)
    suelo2 = round((1023 - raw_suelo2) / 1023 * 100)
    suelo1 = max(0, min(100, suelo1))
    suelo2 = max(0, min(100, suelo2))
    return luz, gas, suelo1, suelo2

def leer_sensores():
    import random

    if gpio_ok:
        # DHT11 — directo en Raspi
        try:
            temp = round(dht_sensor.temperature, 1)
            hum  = round(dht_sensor.humidity, 1)
        except Exception as e:
            log(f"[DHT] Error: {e}")
            temp = None
            hum  = None

        # Arduino — LDR, MQ135, suelo1, suelo2
        ard = leer_arduino()
        if ard is not None:
            luz, gas, suelo1, suelo2 = convertir_analogico(
                ard.get("ldr", 300), ard.get("gas", 100),
                ard.get("suelo1", 500), ard.get("suelo2", 500),
            )
        else:
            luz    = round((state["luz"]    or 400) + random.uniform(-20, 15))
            gas    = round((state["gas"]    or 100) + random.uniform(-5, 10))
            suelo1 = round((state["suelo1"] or 50)  + random.uniform(-1, 0.4))
            suelo2 = round((state["suelo2"] or 50)  + random.uniform(-1, 0.4))
            log("[Arduino] Sin datos — simulando analógicos")

        return {
            "temp":   temp,
            "hum":    hum,
            "luz":    max(0, min(1000, luz)),
            "gas":    max(0, min(1000, gas)),
            "suelo1": max(0, min(100, suelo1)),
            "suelo2": max(0, min(100, suelo2)),
        }

    # Simulación completa
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
    if area not in (1, 2):
        log(f"[Riego] Área inválida: {area}")
        return

    key = f"riego{area}"
    otra_key = "riego2" if area == 1 else "riego1"

    with state["lock"]:
        suelo = state.get(f"suelo{area}")

        if activar:
            if suelo is not None and suelo >= UMBRAL_SUELO_SAT:
                log(f"[Riego] Área {area} BLOQUEADO — suelo saturado ({suelo}%)")
                return
            if state[key] or state[otra_key]:
                # Ya hay riego activo (en esta área o en la otra); la bomba es una sola
                return
            state[key] = True
        else:
            if not state[key]:
                return
            state[key] = False

    if activar:
        enviar_arduino(CMD_RIEGO_ON)
        registrar_evento(f"riego_area{area}_ON", f"suelo={suelo}%", motivo, state["global"])
        guardar_actuador_log(f"riego_area{area}", "ON", motivo, state["global"])

        if timers_riego.get(area):
            timers_riego[area].cancel()
        timers_riego[area] = threading.Timer(
            DURACION_RIEGO, activar_riego, args=[area, False, "fin_ciclo"]
        )
        timers_riego[area].start()
        log(f"[Riego] Área {area} ON — apagado en {DURACION_RIEGO}s")
    else:
        if timers_riego.get(area):
            timers_riego[area].cancel()
            timers_riego[area] = None
        enviar_arduino(CMD_RIEGO_OFF)
        guardar_actuador_log(f"riego_area{area}", "OFF", motivo, state["global"])
        log(f"[Riego] Área {area} OFF ({motivo})")


def set_ventilador(activar, motivo="automatico"):
    with state["lock"]:
        if state["ventilador"] == activar:
            return
        state["ventilador"] = activar
    enviar_arduino(CMD_VENT_ON if activar else CMD_VENT_OFF)
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
    enviar_arduino(CMD_BUZZER_ON if activar else CMD_BUZZER_OFF)
    gpio_set(PIN_LED_ROJO, activar)
    guardar_actuador_log("alarma", "ON" if activar else "OFF", motivo, state["global"])
    log(f"[Alarma] {'ON' if activar else 'OFF'} ({motivo})")

def puede_boton(nombre, espera=1.2):
    ahora = time.time()
    if ahora - ultimo_boton[nombre] < espera:
        return False
    ultimo_boton[nombre] = ahora
    return True


def btn1_callback(channel):
    """Botón 1: cambiar entre modo AUTOMATICO y MANUAL."""
    if not puede_boton("btn1"):
        return
    nuevo = "MANUAL" if state["modo"] == "AUTOMATICO" else "AUTOMATICO"
    with state["lock"]:
        state["modo"] = nuevo
    registrar_evento("modo", nuevo, "boton_1", state["global"])
    log(f"[Botones] Modo cambiado a {nuevo}")


def btn2_callback(channel):
    """Botón 2: riego manual del área 1."""
    if not puede_boton("btn2"):
        return
    activar_riego(1, True, "boton_2")


def btn3_callback(channel):
    """Botón 3: encender/apagar luces manualmente."""
    if not puede_boton("btn3"):
        return
    set_luces(not state["luces"], "boton_3")


def btn4_callback(channel):
    """Botón 4: silenciar alarma / restablecer alerta."""
    if not puede_boton("btn4"):
        return
    with state["lock"]:
        state["alarma_silenciada"] = True
    set_alarma(False, "boton_4_silenciar")
    log("[Botones] Alarma silenciada manualmente")


def configurar_botones():
    if not gpio_ok:
        return
    GPIO.add_event_detect(PIN_BTN1, GPIO.FALLING, callback=btn1_callback, bouncetime=1200)
    GPIO.add_event_detect(PIN_BTN2, GPIO.FALLING, callback=btn2_callback, bouncetime=1200)
    GPIO.add_event_detect(PIN_BTN3, GPIO.FALLING, callback=btn3_callback, bouncetime=1200)
    GPIO.add_event_detect(PIN_BTN4, GPIO.FALLING, callback=btn4_callback, bouncetime=1200)


def hilo_botones():
    if not gpio_ok:
        log("[Botones] GPIO no disponible — botones deshabilitados")
        return
    try:
        configurar_botones()
        log("[Botones] Interrupciones configuradas correctamente (BTN1-4)")
        while True:
            time.sleep(1)
    except Exception as e:
        log(f"[Botones] Error en hilo_botones: {e}")


def aplicar_automatismos(lectura):
    if state["modo"] != "AUTOMATICO":
        if lectura["gas"] >= UMBRAL_GAS_EMRG:
            set_ventilador(True, "gas_emergencia_override")
            set_alarma(True, "gas_emergencia_override")
        return

    if lectura["temp"] is not None and lectura["temp"] >= UMBRAL_TEMP_ALTA:
        set_ventilador(True, "temperatura_alta")
    elif lectura["temp"] is not None and lectura["temp"] < UMBRAL_TEMP_ALTA - 2:
        if state.get("gas", 0) < UMBRAL_GAS_EMRG:
            set_ventilador(False, "temperatura_normal")

    if lectura["gas"] >= UMBRAL_GAS_EMRG:
        set_ventilador(True, "gas_emergencia")
        set_alarma(True, "gas_emergencia")
        registrar_evento("gas_emergencia", lectura["gas"], "sensor", state["global"])
    elif lectura["gas"] < UMBRAL_GAS_EMRG and state["alarma"]:
        if state["global"] not in ("ADVERTENCIA", "EMERGENCIA"):
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
    temp = s.get("temp")
    hum = s.get("hum")
    suelo1 = s.get("suelo1")
    suelo2 = s.get("suelo2")
    luz = s.get("luz")
    warn = any([
        temp is not None and temp >= UMBRAL_TEMP_ALTA,
        hum is not None and hum <= UMBRAL_HUM_BAJA,
        hum is not None and hum >= UMBRAL_HUM_ALTA,
        suelo1 is not None and suelo1 <= UMBRAL_SUELO_SECO,
        suelo2 is not None and suelo2 <= UMBRAL_SUELO_SECO,
        luz is not None and luz <= UMBRAL_LUZ_BAJA,
        s.get("gas", 0) >= UMBRAL_GAS_WARN,
    ])
    if warn:
        return "ADVERTENCIA"
    if s["riego1"] or s["riego2"]:
        return "RIEGO_ACTIVO"
    if s["modo"] == "MANUAL":
        return "MODO_MANUAL"
    return "NORMAL"


def actualizar_estado_global():
    nuevo = calcular_estado()
    anterior = state["global"]

    with state["lock"]:
        state["global"] = nuevo

    set_leds(nuevo)

    # La alarma automática por estado solo se activa si el usuario no la silenció
    if nuevo in ("ADVERTENCIA", "EMERGENCIA"):
        if not state.get("alarma_silenciada", False):
            set_alarma(True, f"estado_{nuevo.lower()}")
    else:
        with state["lock"]:
            state["alarma_silenciada"] = False
        set_alarma(False, "estado_normal")

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

    publicar_sensor("temp",   lectura["temp"],   "C",   "NO_DISPONIBLE" if lectura["temp"] is None else st_temp(lectura["temp"]),   {"sensor": "DHT11"})
    publicar_sensor("hum",    lectura["hum"],    "%",   "NO_DISPONIBLE" if lectura["hum"] is None else st_hum(lectura["hum"]),     {"sensor": "DHT11"})
    publicar_sensor("luz",    lectura["luz"],    "lux", st_luz(lectura["luz"]),     {"sensor": "LDR+Arduino"})
    publicar_sensor("gas",    lectura["gas"],    "ppm", st_gas(lectura["gas"]),     {"sensor": "MQ135+Arduino", "alarma_activa": lectura["gas"] >= UMBRAL_GAS_EMRG})
    publicar_sensor("suelo1", lectura["suelo1"], "%",   st_suelo(lectura["suelo1"]),{"sensor": "FC-28+Arduino", "area": "area1", "riego_activo": state["riego1"]})
    publicar_sensor("suelo2", lectura["suelo2"], "%",   st_suelo(lectura["suelo2"]),{"sensor": "FC-28+Arduino", "area": "area2", "riego_activo": state["riego2"]})

def acumular_csv(lectura):
    with state["lock"]:
        state["lectura_id"] += 1
        fila = [
            state["lectura_id"],
            lectura["temp"], lectura["hum"],
            lectura["suelo1"], lectura["suelo2"],
            lectura["luz"], lectura["gas"],
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
                fila_csv = [int(x) if isinstance(x, float) else x for x in fila]
                writer.writerow(fila_csv)
            writer.writerow(["$"])
        log(f"[CSV] lecturas.csv actualizado ({len(ultimas)} filas)")
    except Exception as e:
        log(f"[CSV] Error: {e}")


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

    elif respuesta == "ACTION=NO_ACTION":
        pass  # decisión explícita de no actuar

    else:
        log(f"[ARM64 LIVE] Acción no reconocida: {respuesta}")


def _procesar_arm64_live(lectura, modo):
    try:
        respuesta = arm64_live.consultar(lectura, modo)
        ejecutar_decision_arm64(respuesta)
    except BrokenPipeError:
        log("[ARM64 LIVE] motor_vivo se cerró inesperadamente. Reiniciando...")
        try:
            arm64_live.cerrar()
        except Exception:
            pass
        arm64_live.iniciar()
        respuesta = "ACTION=NONE"
    except Exception as e:
        log(f"[ARM64 LIVE] Error consultando motor_vivo: {e}")
        respuesta = "ACTION=NONE"

    try:
        guardar_arm64("motor_vivo", {
            "respuesta": respuesta,
            "temp":   int(lectura["temp"]),
            "hum":    int(lectura["hum"]),
            "suelo1": int(lectura["suelo1"]),
            "suelo2": int(lectura["suelo2"]),
            "luz":    int(lectura["luz"]),
            "gas":    int(lectura["gas"]),
            "modo":   modo,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    except Exception as e:
        log(f"[ARM64 LIVE] Error guardando en MongoDB: {e}")

    return respuesta


def hilo_arm64_live():
    global arm64_live_pendiente, arm64_live_detener
    while True:
        with arm64_live_cond:
            while not arm64_live_detener and arm64_live_pendiente is None:
                arm64_live_cond.wait(timeout=1)
            if arm64_live_detener:
                return
            paquete = arm64_live_pendiente
            arm64_live_pendiente = None

        if paquete is None:
            continue

        _procesar_arm64_live(paquete["lectura"], paquete["modo"])


def consultar_arm64_live(lectura):
    global arm64_live_pendiente
    with arm64_live_cond:
        if arm64_live_detener:
            return "ACTION=NO_ACTION"
        arm64_live_pendiente = {
            "lectura": dict(lectura),
            "modo": state["modo"],
        }
        arm64_live_cond.notify()
    return "ACTION=PENDING"

def actualizar_lcd(lectura):
    """Muestra datos rotativos en la LCD. En emergencia muestra alerta fija."""
    if not lcd_ok or lcd is None:
        return
    try:
        estado = state["global"]

        if estado == "EMERGENCIA":
            lcd.clear()
            lcd.write_string("!! EMERGENCIA !!")
            lcd.crlf()
            lcd.write_string(f"Gas:{lectura['gas']:<4} PELIGRO")
            return

        pantalla = state.get("lcd_pantalla", 0)
        state["lcd_pantalla"] = (pantalla + 1) % 5
        lcd.clear()

        if pantalla == 0:
            lcd.write_string(f"Temp: {'N/A' if lectura['temp'] is None else lectura['temp']}C")
            lcd.crlf()
            lcd.write_string(f"Hum:  {'N/A' if lectura['hum'] is None else lectura['hum']}%")
        elif pantalla == 1:
            lcd.write_string(f"Suelo1: {lectura['suelo1']}%")
            lcd.crlf()
            lcd.write_string(f"Suelo2: {lectura['suelo2']}%")
        elif pantalla == 2:
            lcd.write_string(f"Luz:  {lectura['luz']}")
            lcd.crlf()
            lcd.write_string(f"Gas:  {lectura['gas']}")
        elif pantalla == 3:
            r1 = "ON " if state["riego1"] else "OFF"
            r2 = "ON " if state["riego2"] else "OFF"
            lcd.write_string(f"Riego1:{r1} R2:{r2}")
            lcd.crlf()
            vent = "ON " if state["ventilador"] else "OFF"
            luz  = "ON " if state["luces"] else "OFF"
            lcd.write_string(f"Vent:{vent} Luz:{luz}")
        elif pantalla == 4:
            lcd.write_string("Estado:")
            lcd.crlf()
            lcd.write_string(estado[:16])
    except Exception as e:
        log(f"[LCD] Error al escribir: {e}")


def hilo_sensores():
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

        aplicar_automatismos(lectura)       # red de seguridad básica
        acumular_csv(lectura)               # historial para análisis ARM64 por lote
        consultar_arm64_live(lectura)        # decisión principal (ARM64 en vivo)

        actualizar_lcd(lectura)
        actualizar_estado_global()

        log(f"[Loop] T={lectura['temp']}C H={lectura['hum']}% "
            f"S1={lectura['suelo1']}% S2={lectura['suelo2']}% "
            f"Luz={lectura['luz']} Gas={lectura['gas']} [{state['global']}]")
        time.sleep(CICLO_SENSORES)

def apagar_sistema():
    log("\n[Main] Apagando sistema...")

    global arm64_live_detener
    with arm64_live_cond:
        arm64_live_detener = True
        arm64_live_cond.notify_all()

    if gpio_ok:
        for pin in GPIO_OUTPUT_PINS:
            GPIO.output(pin, GPIO.LOW)
        GPIO.cleanup()

    enviar_arduino(CMD_RIEGO_OFF)
    enviar_arduino(CMD_VENT_OFF)
    enviar_arduino(CMD_BUZZER_OFF)

    for t in timers_riego.values():
        if t:
            t.cancel()

    if lcd_ok and lcd:
        lcd.clear()
        lcd.write_string("Sistema off")
        time.sleep(1)
        lcd.clear()

    publicar(T["global"], json.dumps({
        "estado": "OFFLINE",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }), retain=True)
    registrar_evento("sistema", "APAGADO", "main_v2.py", "OFFLINE")

    arm64_live.cerrar()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    log("[Main] Sistema apagado correctamente")


if __name__ == "__main__":
    print("=" * 52)
    print("  Invernadero IoT — ACYE1 USAC — Grupo 9")
    if SIMULACION:
        modo_str = "SIMULACION"
    elif gpio_ok and arduino_ok:
        modo_str = "HARDWARE COMPLETO (Raspi + Arduino)"
    elif gpio_ok:
        modo_str = "HARDWARE PARCIAL (Raspi OK, Arduino no encontrado)"
    elif arduino_ok:
        modo_str = "HARDWARE PARCIAL (Arduino OK, GPIO no disponible)"
    else:
        modo_str = "SIN HARDWARE — SIMULACION"
    print(f"  Modo: {modo_str}")
    print("=" * 52)

    db = mongo_conectar()

    mqtt_client = configurar_mqtt(
        broker=MQTT_BROKER,
        port=MQTT_PORT,
        client_id=MQTT_ID,
        state=state,
        db=db,
        actuadores={
            "activar_riego":  activar_riego,
            "set_ventilador": set_ventilador,
            "set_luces":      set_luces,
            "set_alarma":     set_alarma,
        },
    )

    os.makedirs(ARM64_DIR, exist_ok=True)
    arm64_live.iniciar()
    threading.Thread(target=hilo_arm64_live, daemon=True).start()

    if gpio_ok:
        threading.Thread(target=hilo_botones, daemon=True).start()

    registrar_evento("sistema", "INICIADO", "main_v2.py", "NORMAL")
    time.sleep(2)

    log("[Main] Sistema corriendo — Ctrl+C para salir\n")
    try:
        hilo_sensores()
    except KeyboardInterrupt:
        apagar_sistema()