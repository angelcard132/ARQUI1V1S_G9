import time
import threading
import serial

import RPi.GPIO as GPIO
import board
import adafruit_dht
from RPLCD.i2c import CharLCD

PIN_LUZ1 = 23
PIN_LUZ2 = 24
PIN_LED_VERDE = 5
PIN_LED_AMAR = 6
PIN_LED_ROJO = 13

PIN_BTN1 = 25
PIN_BTN2 = 19
PIN_BTN3 = 26
PIN_BTN4 = 16

ARDUINO_PORT = "/dev/ttyACM0"
BAUDRATE = 9600

CMD_BOMBA_ON = "A"
CMD_BOMBA_OFF = "B"
CMD_VENT_ON = "C"
CMD_VENT_OFF = "D"
CMD_BUZZER_ON = "E"
CMD_BUZZER_OFF = "F"

UMBRAL_TEMP_ALTA = 30

UMBRAL_GAS_WARN = 80
UMBRAL_GAS_EMERG = 90
UMBRAL_GAS_MAXIMO = 110

UMBRAL_LUZ_OSCURO = 220

UMBRAL_SUELO_SECO = 700
UMBRAL_SUELO_SATURADO = 400

INTERVALO_RIEGO = 20
DURACION_RIEGO = 5

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

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

for pin in OUTPUTS:
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

for pin in INPUTS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

dht = adafruit_dht.DHT11(board.D17)

lcd = CharLCD(
    i2c_expander="PCF8574",
    address=0x27,
    port=1,
    cols=16,
    rows=2,
    dotsize=8,
)

arduino = serial.Serial(ARDUINO_PORT, BAUDRATE, timeout=1)
time.sleep(2)

estado = {
    "modo": "AUTOMATICO",
    "global": "NORMAL",
    "temp": None,
    "hum": None,
    "luz": None,
    "gas": None,
    "suelo1": None,
    "suelo2": None,
    "bomba": False,
    "ventilador": False,
    "luces": False,
    "buzzer": False,
}

lock = threading.Lock()

ultimo_riego = 0
riego_en_curso = False


def enviar_arduino(cmd):
    try:
        arduino.write(cmd.encode("utf-8"))
        arduino.flush()
        print(f"[RASP -> ARDUINO] {cmd}")
    except Exception as e:
        print(f"[SERIAL ERROR] {e}")


def set_bomba(on):
    with lock:
        if estado["bomba"] == on:
            return
        estado["bomba"] = on

    enviar_arduino(CMD_BOMBA_ON if on else CMD_BOMBA_OFF)
    print(f"[BOMBA] {'ON' if on else 'OFF'}")


def set_ventilador(on):
    with lock:
        if estado["ventilador"] == on:
            return
        estado["ventilador"] = on

    enviar_arduino(CMD_VENT_ON if on else CMD_VENT_OFF)
    print(f"[VENTILADOR] {'ON' if on else 'OFF'}")


def set_buzzer(on):
    with lock:
        if estado["buzzer"] == on:
            return
        estado["buzzer"] = on

    enviar_arduino(CMD_BUZZER_ON if on else CMD_BUZZER_OFF)
    print(f"[BUZZER] {'ON' if on else 'OFF'}")


def set_luces(on):
    with lock:
        if estado["luces"] == on:
            return
        estado["luces"] = on

    GPIO.output(PIN_LUZ1, GPIO.HIGH if on else GPIO.LOW)
    GPIO.output(PIN_LUZ2, GPIO.HIGH if on else GPIO.LOW)
    print(f"[LUCES] {'ON' if on else 'OFF'}")


def set_leds(nombre):
    GPIO.output(PIN_LED_VERDE, GPIO.LOW)
    GPIO.output(PIN_LED_AMAR, GPIO.LOW)
    GPIO.output(PIN_LED_ROJO, GPIO.LOW)

    if nombre == "NORMAL":
        GPIO.output(PIN_LED_VERDE, GPIO.HIGH)
    elif nombre in ("ADVERTENCIA", "RIEGO_ACTIVO", "MODO_MANUAL"):
        GPIO.output(PIN_LED_AMAR, GPIO.HIGH)
    elif nombre == "EMERGENCIA":
        GPIO.output(PIN_LED_ROJO, GPIO.HIGH)


def leer_dht():
    try:
        temp = dht.temperature
        hum = dht.humidity

        if temp is not None and hum is not None:
            with lock:
                estado["temp"] = round(temp, 1)
                estado["hum"] = round(hum, 1)

    except Exception as e:
        print(f"[DHT] Error: {e}")


def leer_arduino():
    try:
        linea = arduino.readline().decode("utf-8", errors="ignore").strip()

        if not linea:
            return

        if not linea.startswith("LUZ:"):
            print(f"[ARDUINO] {linea}")
            return

        datos = {}

        for parte in linea.split(","):
            if ":" not in parte:
                continue

            clave, valor = parte.split(":", 1)
            datos[clave.strip().upper()] = int(valor.strip())

        with lock:
            estado["luz"] = datos.get("LUZ")
            estado["gas"] = datos.get("GAS")
            estado["suelo1"] = datos.get("SUELO1", datos.get("SUELO"))
            estado["suelo2"] = datos.get("SUELO2", datos.get("SUELO"))

    except Exception as e:
        print(f"[ARDUINO ERROR] {e}")


def activar_riego_cada_20s():
    global ultimo_riego, riego_en_curso

    ahora = time.time()

    if riego_en_curso:
        return

    if ahora - ultimo_riego < INTERVALO_RIEGO:
        return

    riego_en_curso = True
    ultimo_riego = ahora

    print("[RIEGO] Activando bomba por ciclo controlado")
    set_bomba(True)

    def apagar():
        global riego_en_curso
        time.sleep(DURACION_RIEGO)
        set_bomba(False)
        riego_en_curso = False
        print("[RIEGO] Ciclo terminado")

    threading.Thread(target=apagar, daemon=True).start()


def riego_manual():
    global ultimo_riego, riego_en_curso

    with lock:
        suelo = estado["suelo1"]

    if suelo is not None and suelo <= UMBRAL_SUELO_SATURADO:
        print("[RIEGO MANUAL] Bloqueado por suelo saturado")
        return

    if riego_en_curso:
        print("[RIEGO MANUAL] Ya hay un ciclo activo")
        return

    ultimo_riego = 0
    activar_riego_cada_20s()


def automatismos():
    with lock:
        modo = estado["modo"]
        temp = estado["temp"]
        luz = estado["luz"]
        gas = estado["gas"]
        suelo1 = estado["suelo1"]
        bomba = estado["bomba"]

    emergencia = False
    advertencia = False

    if gas is not None:
        if gas >= UMBRAL_GAS_EMERG:
            set_buzzer(True)
            set_ventilador(True)
            emergencia = True
        else:
            set_buzzer(False)
            if temp is None or temp < UMBRAL_TEMP_ALTA:
                set_ventilador(False)
            if gas >= UMBRAL_GAS_WARN:
                advertencia = True

    if temp is not None and temp >= UMBRAL_TEMP_ALTA:
        set_ventilador(True)
        advertencia = True

    if luz is not None:
        if luz >= UMBRAL_LUZ_OSCURO:
            set_luces(True)
            advertencia = True
        else:
            set_luces(False)

    if suelo1 is not None:
        if suelo1 >= UMBRAL_SUELO_SECO:
            activar_riego_cada_20s()
            advertencia = True

    with lock:
        if emergencia:
            estado["global"] = "EMERGENCIA"
        elif estado["bomba"]:
            estado["global"] = "RIEGO_ACTIVO"
        elif modo == "MANUAL":
            estado["global"] = "MODO_MANUAL"
        elif advertencia:
            estado["global"] = "ADVERTENCIA"
        else:
            estado["global"] = "NORMAL"

        estado_global = estado["global"]

    set_leds(estado_global)


def actualizar_lcd():
    with lock:
        e = dict(estado)

    try:
        lcd.clear()

        if e["global"] == "EMERGENCIA":
            lcd.write_string("EMERGENCIA GAS")
            lcd.crlf()
            lcd.write_string(f"GAS:{e['gas']}")
            return

        pantalla = int(time.time()) % 5

        if pantalla == 0:
            lcd.write_string(f"T:{e['temp']}C")
            lcd.crlf()
            lcd.write_string(f"H:{e['hum']}%")

        elif pantalla == 1:
            lcd.write_string(f"S1:{e['suelo1']}")
            lcd.crlf()
            lcd.write_string(f"S2:{e['suelo2']}")

        elif pantalla == 2:
            lcd.write_string(f"LUZ:{e['luz']}")
            lcd.crlf()
            lcd.write_string(f"GAS:{e['gas']}")

        elif pantalla == 3:
            lcd.write_string(f"B:{'ON' if e['bomba'] else 'OFF'}")
            lcd.crlf()
            lcd.write_string(
                f"V:{'ON' if e['ventilador'] else 'OFF'} "
                f"L:{'ON' if e['luces'] else 'OFF'}"
            )

        elif pantalla == 4:
            lcd.write_string("ESTADO:")
            lcd.crlf()
            lcd.write_string(e["global"][:16])

    except Exception as ex:
        print(f"[LCD ERROR] {ex}")


def hilo_botones():
    prev = {pin: GPIO.HIGH for pin in INPUTS}

    while True:
        for pin in INPUTS:
            actual = GPIO.input(pin)

            if actual == GPIO.LOW and prev[pin] == GPIO.HIGH:
                time.sleep(0.08)

                if GPIO.input(pin) == GPIO.LOW:
                    if pin == PIN_BTN1:
                        with lock:
                            estado["modo"] = (
                                "MANUAL"
                                if estado["modo"] == "AUTOMATICO"
                                else "AUTOMATICO"
                            )
                            modo = estado["modo"]

                        print(f"[BTN1] Modo: {modo}")

                    elif pin == PIN_BTN2:
                        print("[BTN2] Riego manual")
                        riego_manual()

                    elif pin == PIN_BTN3:
                        with lock:
                            nuevo = not estado["luces"]
                        set_luces(nuevo)
                        print("[BTN3] Luces manual")

                    elif pin == PIN_BTN4:
                        set_buzzer(False)
                        print("[BTN4] Buzzer silenciado")

            prev[pin] = actual

        time.sleep(0.05)


def imprimir_estado():
    with lock:
        e = dict(estado)

    print(
        f"T={e['temp']}C "
        f"H={e['hum']}% "
        f"LUZ={e['luz']} "
        f"GAS={e['gas']} "
        f"S1={e['suelo1']} "
        f"S2={e['suelo2']} "
        f"BOMBA={'ON' if e['bomba'] else 'OFF'} "
        f"VENT={'ON' if e['ventilador'] else 'OFF'} "
        f"LUCES={'ON' if e['luces'] else 'OFF'} "
        f"BUZZER={'ON' if e['buzzer'] else 'OFF'} "
        f"MODO={e['modo']} "
        f"ESTADO={e['global']}"
    )


try:
    print("=== PRUEBA ENUNCIADO ACTUALIZADA ===")
    print("Gas >= 80  -> advertencia")
    print("Gas >= 90  -> buzzer ON y ventilador ON (emergencia)")
    print("Luz >= 220 -> luces ON")
    print("Suelo >= 700 -> riego cada 20s por 5s")
    print("BTN1: automatico/manual")
    print("BTN2: riego manual")
    print("BTN3: luces manual")
    print("BTN4: silenciar buzzer")
    lcd.clear()
    lcd.write_string("Prueba sistema")
    lcd.crlf()
    lcd.write_string("Iniciando...")

    set_leds("NORMAL")

    threading.Thread(target=hilo_botones, daemon=True).start()

    while True:
        leer_dht()
        leer_arduino()
        automatismos()
        actualizar_lcd()
        imprimir_estado()
        time.sleep(1)

except KeyboardInterrupt:
    print("\nApagando prueba...")

finally:
    set_bomba(False)
    set_ventilador(False)
    set_buzzer(False)
    set_luces(False)

    try:
        lcd.clear()
        lcd.write_string("Sistema apagado")
    except Exception:
        pass

    for pin in OUTPUTS:
        GPIO.output(pin, GPIO.LOW)

    GPIO.cleanup()
    arduino.close()

    print("Prueba finalizada.")