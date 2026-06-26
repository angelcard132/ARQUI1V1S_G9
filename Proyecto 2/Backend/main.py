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
    conectar as mongo_conectar,
    get_db,
    guardar_lectura,
    registrar_evento,
    guardar_estado_sistema,
    guardar_actuador_log,
    guardar_arm64,
    detener_worker,
)

from mqtt_handler import (
    configurar_mqtt,
)

# Argumentos de línea de comandos
parser = argparse.ArgumentParser()
parser.add_argument("--sim", action="store_true", help="Modo simulacion sin GPIO")
args = parser.parse_args()
SIMULACION = args.sim

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_ID = "G9_backend_main_v2"

CSV_PATH = "lecturas.csv"
ARM64_DIR = "./arm64"
CSV_HEADER = ["ID", "TEMP", "HUM_AIRE", "HUM_SUELO_1", "HUM_SUELO_2", "LUZ", "GAS", "RIEGO_1", "RIEGO_2"]

# Umbrales del Invernadero Inteligente (Escalados para Dashboard)
UMBRAL_TEMP_ALTA = 30
UMBRAL_HUM_BAJA = 40
UMBRAL_HUM_ALTA = 80
UMBRAL_LUZ_BAJA = 300
UMBRAL_GAS_WARN = 200
UMBRAL_GAS_EMERG = 400
UMBRAL_SUELO_SECO = 35
UMBRAL_SUELO_SAT = 80

DURACION_RIEGO = 10     # Duración del ciclo de riego en segundos
INTERVALO_RIEGO = 20    # Pausa mínima obligatoria entre riegos en segundos

# Configuración de Pines GPIO
PIN_LUZ1 = 23
PIN_LUZ2 = 24
PIN_LED_VERDE = 5
PIN_LED_AMAR = 6
PIN_LED_ROJO = 13

PIN_BTN1 = 25
PIN_BTN2 = 19
PIN_BTN3 = 26
PIN_BTN4 = 16

OUTPUTS = [
    PIN_LUZ1,
    PIN_LUZ2,
    PIN_LED_VERDE,
    PIN_LED_AMAR,
    PIN_LED_ROJO,
]

INPUTS = [
    PIN_BTN1,
    PIN_BTN2,
    PIN_BTN3,
    PIN_BTN4,
]

# Configuración Serial del Arduino
ARDUINO_PORT = "/dev/ttyACM0"
BAUDRATE = 9600

CMD_BOMBA_ON = "A"
CMD_BOMBA_OFF = "B"
CMD_VENT_ON = "C"
CMD_VENT_OFF = "D"
CMD_BUZZER_ON = "E"
CMD_BUZZER_OFF = "F"

# Inicialización de Hardware
gpio_ok = False
if not SIMULACION:
    try:
        import RPi.GPIO as GPIO
        import board
        import adafruit_dht

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for pin in OUTPUTS:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

        for pin in INPUTS:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        dht_sensor = adafruit_dht.DHT11(board.D17)
        gpio_ok = True
        print("[GPIO] Raspberry Pi GPIO inicializado (Leds, Botones y DHT)")
    except Exception as e:
        print(f"[GPIO] Fallo al iniciar hardware GPIO: {e} — continuando en simulación")

# Inicialización Pantalla LCD
lcd_ok = False
lcd = None
if not SIMULACION:
    try:
        from RPLCD.i2c import CharLCD
        lcd = CharLCD(
            i2c_expander="PCF8574",
            address=0x27,
            port=1,
            cols=16,
            rows=2,
            dotsize=8,
        )
        lcd.clear()
        lcd.write_string("Iniciando...")
        lcd_ok = True
        print("[LCD] Pantalla I2C PCF8574 inicializada")
    except Exception as e:
        print(f"[LCD] Pantalla no encontrada o deshabilitada: {e}")

# Inicialización Serial Arduino
arduino_ok = False
arduino = None
if not SIMULACION:
    try:
        import serial
        arduino = serial.Serial(ARDUINO_PORT, BAUDRATE, timeout=1)
        time.sleep(2)
        arduino_ok = True
        print(f"[Arduino] Conectado por serial en {ARDUINO_PORT}")
    except Exception as e:
        print(f"[Arduino] No conectado: {e} — simulando sensores analógicos")

# Estado global del sistema (Thread Safe)
lock = threading.Lock()
estado = {
    "lock": lock,
    "modo": "AUTOMATICO",
    "global": "NORMAL",
    "temp": None,
    "hum": None,
    "luz": None,
    "gas": None,
    "suelo1": None,
    "suelo2": None,
    "riego1": False,
    "riego2": False,
    "bomba": False,
    "ventilador": False,
    "luces": False,
    "alarma": False,
    "buzzer": False,
    "lecturas_csv": [],
    "lectura_id": 0,
    "lcd_pantalla": 0,
}

ultimo_riego_off = 0
timers_riego = {}

def enviar_arduino(cmd):
    if not arduino_ok or arduino is None:
        print(f"[Simulación Arduino] Comando enviado: {cmd}")
        return
    try:
        arduino.write(cmd.encode("utf-8"))
        arduino.flush()
        print(f"[RASP -> ARDUINO] {cmd}")
    except Exception as e:
        print(f"[Arduino Error] No se pudo enviar el comando {cmd}: {e}")

def set_bomba(on):
    with lock:
        estado["bomba"] = on
    enviar_arduino(CMD_BOMBA_ON if on else CMD_BOMBA_OFF)
    print(f"[BOMBA] {'ON' if on else 'OFF'}")

def set_ventilador(activar, motivo="automatico"):
    with lock:
        if estado["ventilador"] == activar:
            return
        estado["ventilador"] = activar
    enviar_arduino(CMD_VENT_ON if activar else CMD_VENT_OFF)
    guardar_actuador_log("ventilador", "ON" if activar else "OFF", motivo, estado["global"])
    print(f"[VENTILADOR] {'ON' if activar else 'OFF'} ({motivo})")

def set_luces(activar, motivo="automatico"):
    with lock:
        if estado["luces"] == activar:
            return
        estado["luces"] = activar
    if gpio_ok:
        GPIO.output(PIN_LUZ1, GPIO.HIGH if activar else GPIO.LOW)
        GPIO.output(PIN_LUZ2, GPIO.HIGH if activar else GPIO.LOW)
    else:
        print(f"[Simulación GPIO] Luces {'ON' if activar else 'OFF'}")
    guardar_actuador_log("luces", "ON" if activar else "OFF", motivo, estado["global"])
    print(f"[LUCES] {'ON' if activar else 'OFF'} ({motivo})")

def set_alarma(activar, motivo="automatico"):
    with lock:
        if estado["alarma"] == activar:
            return
        estado["alarma"] = activar
        estado["buzzer"] = activar
    enviar_arduino(CMD_BUZZER_ON if activar else CMD_BUZZER_OFF)
    if gpio_ok:
        GPIO.output(PIN_LED_ROJO, GPIO.HIGH if activar else GPIO.LOW)
    else:
        print(f"[Simulación GPIO] Alarma {'ON' if activar else 'OFF'}")
    guardar_actuador_log("alarma", "ON" if activar else "OFF", motivo, estado["global"])
    print(f"[ALARMA] {'ON' if activar else 'OFF'} ({motivo})")

def set_leds(nombre):
    if gpio_ok:
        GPIO.output(PIN_LED_VERDE, GPIO.HIGH if nombre == "NORMAL" else GPIO.LOW)
        GPIO.output(PIN_LED_AMAR,  GPIO.HIGH if nombre in ("ADVERTENCIA", "RIEGO_ACTIVO", "MODO_MANUAL") else GPIO.LOW)
        GPIO.output(PIN_LED_ROJO,  GPIO.HIGH if nombre == "EMERGENCIA" else GPIO.LOW)
    else:
        print(f"[Simulación Leds] Verde={nombre == 'NORMAL'}, Amarillo={nombre in ('ADVERTENCIA', 'RIEGO_ACTIVO', 'MODO_MANUAL')}, Rojo={nombre == 'EMERGENCIA'}")

def activar_riego(area, on, motivo="automatico"):
    global ultimo_riego_off, timers_riego
    key = f"riego{area}"

    with lock:
        suelo = estado.get(f"suelo{area}")

        if on:
            # Control de Saturación
            if suelo is not None and suelo >= UMBRAL_SUELO_SAT:
                print(f"[Riego] Área {area} BLOQUEADA — Suelo saturado ({suelo}%)")
                return

            # Impedir riego si la otra área u otra bomba ya están regando
            if estado["riego1"] or estado["riego2"]:
                print(f"[Riego] Bomba ocupada. Ignorando petición para área {area}.")
                return

            # Pausa mínima obligatoria
            ahora = time.time()
            if ahora - ultimo_riego_off < INTERVALO_RIEGO:
                print(f"[Riego] Ciclo bloqueado por pausa mínima. Espere {int(INTERVALO_RIEGO - (ahora - ultimo_riego_off))}s")
                return

            estado[key] = True
            set_bomba(True)

            # Mongo y MQTT Logs
            registrar_evento(f"riego_area{area}_ON", f"suelo={suelo}%", motivo, estado["global"])
            guardar_actuador_log(f"riego_area{area}", "ON", motivo, estado["global"])
            
            from mqtt_handler import publicar
            publicar(f"riego_area{area}", {
                "estado": "ON",
                "bomba": True,
                "area": f"area{area}",
                "motivo": motivo,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            publicar("riego", {
                "estado": f"RIEGO_AREA_{area}",
                "bomba": True,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            # Iniciar Temporizador para Apagar
            if area in timers_riego and timers_riego[area]:
                timers_riego[area].cancel()
            
            timers_riego[area] = threading.Timer(
                DURACION_RIEGO,
                activar_riego,
                args=[area, False, "fin_ciclo"]
            )
            timers_riego[area].start()
            print(f"[Riego] Riego Área {area} ACTIVADO por {DURACION_RIEGO}s ({motivo})")

        else:
            if area in timers_riego and timers_riego[area]:
                timers_riego[area].cancel()
                timers_riego[area] = None

            estado[key] = False
            
            # Apagar bomba físicamente si no queda riego activo
            if not estado["riego1"] and not estado["riego2"]:
                set_bomba(False)
                ultimo_riego_off = time.time()

            registrar_evento(f"riego_area{area}_OFF", motivo, motivo, estado["global"])
            guardar_actuador_log(f"riego_area{area}", "OFF", motivo, estado["global"])
            
            from mqtt_handler import publicar
            publicar(f"riego_area{area}", {
                "estado": "OFF",
                "bomba": False,
                "area": f"area{area}",
                "motivo": motivo,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            publicar("riego", {
                "estado": "RIEGO_OFF",
                "bomba": False,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            print(f"[Riego] Riego Área {area} DESACTIVADO ({motivo})")

def convertir_analogico(raw_ldr, raw_gas, raw_suelo1, raw_suelo2):
    # LDR: alto valor = poca luz. Escalar a 0-1000.
    luz = round(raw_ldr / 1023 * 1000)
    # Gas: alto valor = más gas. Escalar a 0-1000.
    gas = round(raw_gas / 1023 * 1000)
    # Sensor resistivo: 1023 = seco (0%), 0 = húmedo (100%)
    suelo1 = round((1023 - raw_suelo1) / 1023 * 100)
    suelo2 = round((1023 - raw_suelo2) / 1023 * 100)
    
    # Clamp por seguridad
    luz = max(0, min(1000, luz))
    gas = max(0, min(1000, gas))
    suelo1 = max(0, min(100, suelo1))
    suelo2 = max(0, min(100, suelo2))
    return luz, gas, suelo1, suelo2

def leer_dht():
    if gpio_ok:
        try:
            temp = dht_sensor.temperature
            hum = dht_sensor.humidity
            if temp is not None and hum is not None:
                with lock:
                    estado["temp"] = round(float(temp), 1)
                    estado["hum"] = round(float(hum), 1)
                return
        except Exception as e:
            print(f"[DHT] Error lectura: {e}")
            
    # Simulación o mantener anterior
    import random
    with lock:
        t_base = estado["temp"] if estado["temp"] is not None else 24.5
        h_base = estado["hum"] if estado["hum"] is not None else 55.0
        estado["temp"] = round(max(15.0, min(40.0, t_base + random.uniform(-0.3, 0.4))), 1)
        estado["hum"] = round(max(20.0, min(95.0, h_base + random.uniform(-0.8, 0.8))), 1)

_ultimo_arduino = {"ldr": 300, "gas": 150, "suelo": 600}

def leer_arduino():
    global _ultimo_arduino
    if not arduino_ok or arduino is None:
        import random
        raw_ldr = max(100, min(900, _ultimo_arduino["ldr"] + random.randint(-15, 15)))
        raw_gas = max(50, min(500, _ultimo_arduino["gas"] + random.randint(-3, 3)))
        raw_suelo = max(350, min(850, _ultimo_arduino["suelo"] + random.randint(-8, 8)))
        _ultimo_arduino = {"ldr": raw_ldr, "gas": raw_gas, "suelo": raw_suelo}
        
        luz, gas, suelo1, suelo2 = convertir_analogico(raw_ldr, raw_gas, raw_suelo, raw_suelo)
        with lock:
            estado["luz"] = luz
            estado["gas"] = gas
            estado["suelo1"] = suelo1
            estado["suelo2"] = suelo2
        return

    try:
        linea = arduino.readline().decode("utf-8", errors="ignore").strip()
        if not linea:
            luz, gas, suelo1, suelo2 = convertir_analogico(_ultimo_arduino["ldr"], _ultimo_arduino["gas"], _ultimo_arduino["suelo"], _ultimo_arduino["suelo"])
            with lock:
                estado["luz"] = luz
                estado["gas"] = gas
                estado["suelo1"] = suelo1
                estado["suelo2"] = suelo2
            return

        datos = {}
        for parte in linea.split(","):
            if ":" not in parte:
                continue
            clave, valor = parte.split(":", 1)
            datos[clave.strip().upper()] = int(valor.strip())

        raw_ldr = datos.get("LUZ", _ultimo_arduino["ldr"])
        raw_gas = datos.get("GAS", _ultimo_arduino["gas"])
        raw_suelo = datos.get("SUELO", _ultimo_arduino["suelo"])
        _ultimo_arduino = {"ldr": raw_ldr, "gas": raw_gas, "suelo": raw_suelo}

        luz, gas, suelo1, suelo2 = convertir_analogico(raw_ldr, raw_gas, raw_suelo, raw_suelo)
        with lock:
            estado["luz"] = luz
            estado["gas"] = gas
            estado["suelo1"] = suelo1
            estado["suelo2"] = suelo2
    except Exception as e:
        print(f"[Arduino] Error de parseo: {e}")
        luz, gas, suelo1, suelo2 = convertir_analogico(_ultimo_arduino["ldr"], _ultimo_arduino["gas"], _ultimo_arduino["suelo"], _ultimo_arduino["suelo"])
        with lock:
            estado["luz"] = luz
            estado["gas"] = gas
            estado["suelo1"] = suelo1
            estado["suelo2"] = suelo2

def calcular_estado():
    with lock:
        gas = estado["gas"]
        temp = estado["temp"]
        hum = estado["hum"]
        suelo1 = estado["suelo1"]
        suelo2 = estado["suelo2"]
        luz = estado["luz"]
        modo = estado["modo"]
        riego1 = estado["riego1"]
        riego2 = estado["riego2"]

    if gas is not None and gas >= UMBRAL_GAS_EMERG:
        return "EMERGENCIA"
    
    warn = any([
        temp is not None and temp >= UMBRAL_TEMP_ALTA,
        hum is not None and (hum <= UMBRAL_HUM_BAJA or hum >= UMBRAL_HUM_ALTA),
        suelo1 is not None and suelo1 < UMBRAL_SUELO_SECO,
        suelo2 is not None and suelo2 < UMBRAL_SUELO_SECO,
        luz is not None and luz < UMBRAL_LUZ_BAJA,
        gas is not None and gas >= UMBRAL_GAS_WARN,
    ])
    
    if warn:
        return "ADVERTENCIA"
    if riego1 or riego2:
        return "RIEGO_ACTIVO"
    if modo == "MANUAL":
        return "MODO_MANUAL"
    return "NORMAL"

def actualizar_estado_global():
    nuevo = calcular_estado()
    with lock:
        anterior = estado["global"]
        estado["global"] = nuevo
        modo = estado["modo"]
        sensores = {
            "temp": estado["temp"],
            "hum": estado["hum"],
            "suelo1": estado["suelo1"],
            "suelo2": estado["suelo2"],
            "luz": estado["luz"],
            "gas": estado["gas"],
        }
    
    set_leds(nuevo)
    
    from mqtt_handler import publicar_estado_global
    publicar_estado_global(nuevo, modo, sensores)
    
    if nuevo != anterior:
        registrar_evento("estado_global", nuevo, "sistema", nuevo)
        print(f"[Estado] Cambiado: {anterior} -> {nuevo}")
        
        # Alarma (buzzer) activa en ADVERTENCIA y EMERGENCIA (Critico)
        if nuevo in ("ADVERTENCIA", "EMERGENCIA"):
            set_alarma(True, f"cambio_estado_{nuevo.lower()}")
        elif nuevo not in ("ADVERTENCIA", "EMERGENCIA") and anterior in ("ADVERTENCIA", "EMERGENCIA"):
            set_alarma(False, "estado_global_normalizado")

def publicar_sensores(lectura):
    def st_temp(v):  return "ALTA"  if v >= UMBRAL_TEMP_ALTA  else "NORMAL"
    def st_hum(v):   return "BAJA"  if v < UMBRAL_HUM_BAJA    else "ALTA" if v > UMBRAL_HUM_ALTA else "NORMAL"
    def st_luz(v):   return "BAJA"  if v < UMBRAL_LUZ_BAJA    else "NORMAL"
    def st_gas(v):   return "GAS_EMERGENCIA" if v >= UMBRAL_GAS_EMERG else "GAS_ADVERTENCIA" if v >= UMBRAL_GAS_WARN else "GAS_NORMAL"
    def st_suelo(v): return "SECO"  if v < UMBRAL_SUELO_SECO  else "SATURADO" if v >= UMBRAL_SUELO_SAT else "NORMAL"

    from mqtt_handler import publicar_sensor
    with lock:
        riego1 = estado["riego1"]
        riego2 = estado["riego2"]

    publicar_sensor("temp",   lectura["temp"],   "C",   st_temp(lectura["temp"]),    {"sensor": "DHT11"})
    publicar_sensor("hum",    lectura["hum"],    "%",   st_hum(lectura["hum"]),      {"sensor": "DHT11"})
    publicar_sensor("luz",    lectura["luz"],    "lux", st_luz(lectura["luz"]),      {"sensor": "LDR+Arduino"})
    publicar_sensor("gas",    lectura["gas"],    "ppm", st_gas(lectura["gas"]),      {"sensor": "MQ+Arduino", "alarma_activa": lectura["gas"] >= UMBRAL_GAS_EMERG})
    publicar_sensor("suelo1", lectura["suelo1"], "%",   st_suelo(lectura["suelo1"]), {"sensor": "FC-28+Arduino", "area": "area1", "riego_activo": riego1})
    publicar_sensor("suelo2", lectura["suelo2"], "%",   st_suelo(lectura["suelo2"]), {"sensor": "FC-28+Arduino", "area": "area2", "riego_activo": riego2})

def acumular_csv(lectura):
    with lock:
        estado["lectura_id"] += 1
        fila = [
            estado["lectura_id"],
            lectura["temp"],   lectura["hum"],
            lectura["suelo1"], lectura["suelo2"],
            lectura["luz"],    lectura["gas"],
            1 if estado["riego1"] else 0,
            1 if estado["riego2"] else 0,
        ]
        estado["lecturas_csv"].append(fila)
        if len(estado["lecturas_csv"]) > 30:
            estado["lecturas_csv"].pop(0)
        if len(estado["lecturas_csv"]) >= 30:
            _escribir_csv()

def _escribir_csv():
    try:
        with lock:
            ultimas = [list(f) for f in estado["lecturas_csv"][-30:]]
            
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            for i, fila in enumerate(ultimas, 1):
                fila[0] = i
                # Quitar floats sin decimales
                fila_csv = [
                    int(x) if isinstance(x, float) and x.is_integer() else x
                    for x in fila
                ]
                writer.writerow(fila_csv)
            writer.writerow(["$"])
        print(f"[CSV] Guardado: {CSV_PATH} actualizado ({len(ultimas)} registros)")
    except Exception as e:
        print(f"[CSV Error] {e}")

def automatismos(lectura):
    with lock:
        modo = estado["modo"]
        riego1 = estado["riego1"]
        riego2 = estado["riego2"]

    # Emergencia por gas MQ (Prioritario, bypass manual)
    if lectura["gas"] >= UMBRAL_GAS_EMERG:
        set_ventilador(True, "gas_emergencia")
        registrar_evento("gas_emergencia", lectura["gas"], "sensor", estado["global"])

    # Si no es automático, no ejecuta reglas automáticas de actuadores
    if modo != "AUTOMATICO":
        return

    # Ventilación por Temperatura
    if lectura["temp"] >= UMBRAL_TEMP_ALTA:
        set_ventilador(True, "temperatura_alta")
    elif lectura["temp"] < UMBRAL_TEMP_ALTA - 2:
        if lectura["gas"] < UMBRAL_GAS_EMERG:
            set_ventilador(False, "temperatura_normal")

    # Iluminación LDR
    if lectura["luz"] < UMBRAL_LUZ_BAJA:
        set_luces(True, "luz_baja")
    elif lectura["luz"] >= UMBRAL_LUZ_BAJA:
        set_luces(False, "luz_suficiente")

    # Riego por Humedad de Suelo
    if lectura["suelo1"] < UMBRAL_SUELO_SECO and not riego1:
        activar_riego(1, True, "suelo_seco_auto")
    if lectura["suelo2"] < UMBRAL_SUELO_SECO and not riego2:
        activar_riego(2, True, "suelo_seco_auto")

def actualizar_lcd(lectura):
    if not lcd_ok or lcd is None:
        return
    try:
        with lock:
            global_state = estado["global"]
            r1 = "ON" if estado["riego1"] else "OFF"
            r2 = "ON" if estado["riego2"] else "OFF"
            vent = "ON" if estado["ventilador"] else "OFF"
            luces = "ON" if estado["luces"] else "OFF"
            pantalla = estado.get("lcd_pantalla", 0)
            estado["lcd_pantalla"] = (pantalla + 1) % 5

        lcd.clear()

        # Emergencia fija
        if global_state == "EMERGENCIA":
            lcd.write_string("¡¡EMERGENCIA !!")
            lcd.crlf()
            lcd.write_string(f"Gas:{lectura['gas']:<4} PELIGRO")
            return

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
            lcd.write_string(f"R1:{r1} R2:{r2}")
            lcd.crlf()
            lcd.write_string(f"Vent:{vent} Luz:{luces}")
        elif pantalla == 4:
            lcd.write_string("Estado:")
            lcd.crlf()
            lcd.write_string(global_state[:16])
    except Exception as e:
        print(f"[LCD Error] {e}")

def hilo_botones():
    if not gpio_ok:
        return
    prev = {p: True for p in INPUTS}
    while True:
        b = {p: GPIO.input(p) for p in INPUTS}
        
        # BTN1: Modo Automático / Manual
        if not b[PIN_BTN1] and prev[PIN_BTN1]:
            with lock:
                nuevo = "MANUAL" if estado["modo"] == "AUTOMATICO" else "AUTOMATICO"
                estado["modo"] = nuevo
            registrar_evento("modo_cambiado", nuevo, "boton_fisico", estado["global"])
            print(f"[Botones] Modo cambiado a: {nuevo}")
            from mqtt_handler import publicar
            publicar("global", {
                "estado": estado["global"],
                "modo": nuevo,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        # BTN2: Riego Manual
        if not b[PIN_BTN2] and prev[PIN_BTN2]:
            print("[Botones] Botón 2 presionado: Iniciando riego manual Área 1")
            activar_riego(1, True, "boton_fisico")

        # BTN3: Luces Manual
        if not b[PIN_BTN3] and prev[PIN_BTN3]:
            with lock:
                nuevo_luces = not estado["luces"]
            set_luces(nuevo_luces, "boton_fisico")
            print(f"[Botones] Luces cambiadas localmente a: {nuevo_luces}")
            from mqtt_handler import publicar
            publicar("luces", {
                "estado": "ON" if nuevo_luces else "OFF",
                "activo": nuevo_luces,
                "modo": "MANUAL",
                "motivo": "boton_fisico",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        # BTN4: Silenciar Alarma
        if not b[PIN_BTN4] and prev[PIN_BTN4]:
            print("[Botones] Silenciando alarma localmente")
            set_alarma(False, "boton_fisico")
            from mqtt_handler import publicar
            publicar("alarma", {
                "estado": "SILENCIADA",
                "buzzer": False,
                "led_rojo": False,
                "motivo": "boton_fisico",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        prev = b
        time.sleep(0.05)

def imprimir_estado(lectura):
    with lock:
        riego1 = "ON" if estado["riego1"] else "OFF"
        riego2 = "ON" if estado["riego2"] else "OFF"
        vent = "ON" if estado["ventilador"] else "OFF"
        luces = "ON" if estado["luces"] else "OFF"
        alarma = "ON" if estado["alarma"] else "OFF"
        modo = estado["modo"]
        g_state = estado["global"]
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
          f"T={lectura['temp']}C H={lectura['hum']}% LUZ={lectura['luz']} GAS={lectura['gas']} "
          f"S1={lectura['suelo1']}% S2={lectura['suelo2']}% "
          f"R1={riego1} R2={riego2} VENT={vent} LUCES={luces} ALARMA={alarma} "
          f"MODO={modo} ESTADO={g_state}")

def hilo_sensores():
    while True:
        leer_dht()
        leer_arduino()
        
        with lock:
            lectura = {
                "temp": estado["temp"],
                "hum": estado["hum"],
                "luz": estado["luz"],
                "gas": estado["gas"],
                "suelo1": estado["suelo1"],
                "suelo2": estado["suelo2"],
            }
            g_state = estado["global"]
            modo = estado["modo"]
            sensores = {k: estado[k] for k in ["temp", "hum", "luz", "gas", "suelo1", "suelo2"]}
            actuadores = {
                "riego1": estado["riego1"],
                "riego2": estado["riego2"],
                "ventilador": estado["ventilador"],
                "luces": estado["luces"],
                "alarma": estado["alarma"],
            }

        # Comunicar datos por MQTT
        publicar_sensores(lectura)
        
        # Persistir registros en MongoDB Atlas
        guardar_lectura(lectura, g_state)
        guardar_estado_sistema(g_state, modo, sensores, actuadores)
        
        # Acumular CSV local y procesar reglas automáticas
        acumular_csv(lectura)
        automatismos(lectura)
        
        # Actualizar LCD físico y LEDs
        actualizar_lcd(lectura)
        actualizar_estado_global()

        # Log en consola
        imprimir_estado(lectura)
        time.sleep(3)

if __name__ == "__main__":
    print("=" * 52)
    print("  Invernadero Inteligente IoT — ACYE1 — Grupo 9")
    modo_str = "SIMULACION"
    if not SIMULACION:
        if gpio_ok and arduino_ok:
            modo_str = "HARDWARE COMPLETO (Raspi + Arduino)"
        elif gpio_ok:
            modo_str = "HARDWARE PARCIAL (Raspi OK, Arduino SIM)"
        elif arduino_ok:
            modo_str = "HARDWARE PARCIAL (Arduino OK, GPIO SIM)"
    print(f"  Modo Operación: {modo_str}")
    print("=" * 52)

    # 1. MongoDB Atlas
    db = mongo_conectar()

    # 2. MQTT Broker
    mqtt_client = configurar_mqtt(
        broker=MQTT_BROKER,
        port=MQTT_PORT,
        client_id=MQTT_ID,
        state=estado,
        db=db,
        actuadores={
            "activar_riego": activar_riego,
            "set_ventilador": set_ventilador,
            "set_luces": set_luces,
            "set_alarma": set_alarma,
        },
    )

    # 3. Asegurar directorio de binarios ARM64
    os.makedirs(ARM64_DIR, exist_ok=True)

    # 4. Hilo de Botones Físicos
    if gpio_ok:
        threading.Thread(target=hilo_botones, daemon=True).start()

    # 5. Registrar evento de arranque
    registrar_evento("sistema", "INICIADO", "main.py", "NORMAL")
    time.sleep(2)

    # 6. Bucle de sensado principal
    print("[Main] Backend en ejecución. Presione Ctrl+C para salir.\n")
    try:
        hilo_sensores()
    except KeyboardInterrupt:
        print("\n[Main] Apagando backend...")
        set_bomba(False)
        set_ventilador(False)
        set_luces(False)
        set_alarma(False)
        
        if gpio_ok:
            for pin in OUTPUTS:
                try:
                    GPIO.output(pin, GPIO.LOW)
                except Exception:
                    pass
            GPIO.cleanup()
            
        for t in timers_riego.values():
            if t:
                t.cancel()
                
        # Publicar desconexión MQTT
        from mqtt_handler import publicar
        publicar("global", {
            "estado": "OFFLINE",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, retain=True)
        
        registrar_evento("sistema", "APAGADO", "main.py", "OFFLINE")
        
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            
        detener_worker()
        
        if arduino_ok and arduino is not None:
            arduino.close()
            
        print("[Main] Backend apagado correctamente.")