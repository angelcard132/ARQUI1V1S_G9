
import json
import threading
from datetime import datetime
import paho.mqtt.client as mqtt


_state      = None
_db         = None
_actuadores = None
_client     = None

BASE = "invernadero/G9"

TOPIC_REMOTO = f"{BASE}/control/remoto"
TOPIC_MANUAL = f"{BASE}/control/manual"
TOPIC_ARM64_REQUEST = f"{BASE}/arm64/request"

# Topics de publicacion
T = {
    "temp":       f"{BASE}/sensores/temperatura",
    "hum":        f"{BASE}/sensores/humedad_ambiente",
    "suelo1":     f"{BASE}/sensores/humedad_suelo_area1",
    "suelo2":     f"{BASE}/sensores/humedad_suelo_area2",
    "luz":        f"{BASE}/sensores/luz",
    "gas":        f"{BASE}/sensores/gas",
    "riego":      f"{BASE}/actuadores/riego",
    "riego1":     f"{BASE}/actuadores/riego_area1",
    "riego2":     f"{BASE}/actuadores/riego_area2",
    "ventilador": f"{BASE}/actuadores/ventilador",
    "luces":      f"{BASE}/actuadores/luces",
    "alarma":     f"{BASE}/actuadores/alarma",
    "global":     f"{BASE}/estado/global",
    "arm64_req":  f"{BASE}/arm64/request",
}

# Comandos validos por actuador
COMANDOS_VALIDOS = {
    "riego":        ["ON", "OFF"],
    "riego_area1":  ["ON", "OFF"],
    "riego_area2":  ["ON", "OFF"],
    "ventilador":   ["ON", "OFF"],
    "luces":        ["ON", "OFF"],
    "alarma":       ["ON", "OFF", "SILENCIAR"],
    "modo":         ["AUTOMATICO", "MANUAL"],
    "global":       ["RESET"],
}


def configurar_mqtt(broker, port, client_id, state, db, actuadores):
    global _state, _db, _actuadores, _client
    _state      = state
    _db         = db
    _actuadores = actuadores

    # Soporte dinámico para compatibilidad con Paho MQTT v1 y v2
    if hasattr(mqtt, "CallbackAPIVersion"):
        _client = mqtt.Client(
            client_id=client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
    else:
        _client = mqtt.Client(
            client_id=client_id
        )
    _client.on_connect    = _on_connect
    _client.on_disconnect = _on_disconnect
    _client.on_message    = _on_message
    _client.reconnect_delay_set(min_delay=1, max_delay=30)
    _client.connect(broker, port, keepalive=60)
    _client.loop_start()
    return _client


def publicar(topic_key_or_full, payload, retain=False, qos=1):

    if _client and _client.is_connected():
        topic = T.get(topic_key_or_full, topic_key_or_full)
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        _client.publish(topic, payload, qos=qos, retain=retain)


def publicar_sensor(key, valor, unidad, estado, extra=None):
    doc = {"valor": valor, "unidad": unidad, "estado": estado, "timestamp": _ts()}
    if extra:
        doc.update(extra)
    publicar(key, doc)


def publicar_estado_global(estado, modo, lecturas):
    led = {
        "verde":    estado == "NORMAL",
        "amarillo": estado in ("ADVERTENCIA", "RIEGO_ACTIVO", "MODO_MANUAL"),
        "rojo":     estado == "EMERGENCIA",
    }
    publicar("global", {
        "estado": estado, "modo": modo,
        "leds": led, "lecturas": lecturas,
        "timestamp": _ts(),
    }, retain=True)


def _on_connect(client, userdata, flags, rc, properties=None):
    # rc puede ser un entero en v1 o un objeto ReasonCode en v2
    code = rc.value if hasattr(rc, "value") else rc
    if code == 0:
        print(f"[MQTT] Conectado al broker")
        client.subscribe(TOPIC_REMOTO, qos=1)
        client.subscribe(TOPIC_MANUAL, qos=1)
        client.subscribe(TOPIC_ARM64_REQUEST, qos=1)   
        client.subscribe(f"{BASE}/control/arm64", qos=1)
        print(f"[MQTT] Suscrito a control/remoto, control/manual, arm64/request y control/arm64")
    else:
        print(f"[MQTT] Error de conexion: {code}")


def _on_disconnect(client, userdata, rc, properties=None, reasonCode=None):
    print(f"[MQTT] Desconectado (rc={rc}) — reconectando...")


def _on_message(client, userdata, msg):
    topic   = msg.topic
    payload = msg.payload.decode("utf-8").strip()
    print(f"[MQTT] <- {topic}: {payload}")

    if topic == TOPIC_REMOTO:
        try:
            data     = json.loads(payload)
            actuador = data.get("actuador", "").lower().strip()
            cmd      = data.get("cmd", "").upper().strip()
            origen   = data.get("origen", "dashboard")
            _procesar_comando(actuador, cmd, origen)
        except json.JSONDecodeError:
            print(f"[MQTT] Payload no es JSON: {payload}")

    elif topic == TOPIC_MANUAL:
        if ":" in payload:
            partes   = payload.split(":", 1)
            actuador = partes[0].strip().lower()
            cmd      = partes[1].strip().upper()
            _procesar_comando(actuador, cmd, "boton_fisico")

    elif topic in (TOPIC_ARM64_REQUEST, f"{BASE}/control/arm64"):
        try:
            data    = json.loads(payload)
            modulo  = data.get("modulo", "")
            # Habilitar soporte para ambos formatos (columna y sensor)
            columna = data.get("columna", data.get("sensor", ""))
            origen  = data.get("origen", "dashboard")
 
            if not modulo or not columna:
                print(f"[ARM64] Solicitud incompleta: modulo={modulo}, columna={columna}")
                return

            print(f"[ARM64] Solicitud: {modulo} sobre columna {columna} ({origen})")
 
            # Llamar al runner en un hilo para no bloquear MQTT
            import threading
            from arm64_runner import ejecutar_modulo_individual
            from mongo_handler import guardar_arm64
 
            threading.Thread(
                target=ejecutar_modulo_individual,
                args=(modulo, columna, publicar, guardar_arm64, print),
                daemon=True,
            ).start()
        except json.JSONDecodeError:
            print(f"[ARM64] Payload no es JSON: {payload}")
def _procesar_comando(actuador, cmd, origen):


    # Validar que el actuador y comando sean conocidos
    if actuador not in COMANDOS_VALIDOS:
        print(f"[Cmd] Actuador desconocido: '{actuador}'")
        return

    if cmd not in COMANDOS_VALIDOS[actuador]:
        print(f"[Cmd] Comando '{cmd}' no valido para '{actuador}'. Validos: {COMANDOS_VALIDOS[actuador]}")
        return

    print(f"[Cmd] {actuador} -> {cmd} ({origen})")

    # Guardar en MongoDB antes de ejecutar
    _guardar_comando(actuador, cmd, origen)

    if actuador == "riego":
        activar = cmd == "ON"
        _actuadores["activar_riego"](1, activar, origen)
        _publicar_riego(1, activar, origen)

    elif actuador == "riego_area1":
        activar = cmd == "ON"
        _actuadores["activar_riego"](1, activar, origen)
        _publicar_riego(1, activar, origen)

    elif actuador == "riego_area2":
        activar = cmd == "ON"
        _actuadores["activar_riego"](2, activar, origen)
        _publicar_riego(2, activar, origen)

    elif actuador == "ventilador":
        activar = cmd == "ON"

        if not activar and (_state.get("gas") or 0) >= 400:
            print(f"[Cmd] No se puede apagar ventilador — emergencia de gas activa")
            publicar("ventilador", {
                "estado":  "VENTILACION_EMERGENCIA",
                "activo":  True,
                "motivo":  "bloqueado_emergencia_gas",
                "timestamp": _ts(),
            })
            return

        _actuadores["set_ventilador"](activar, origen)
        estado_str = "VENTILACION_MANUAL" if origen in ("dashboard","boton_fisico") else \
                     "VENTILACION_ON"     if activar else "VENTILACION_OFF"
        publicar("ventilador", {
            "estado":    estado_str,
            "activo":    activar,
            "motivo":    origen,
            "timestamp": _ts(),
        })
        _guardar_actuador_log("ventilador", cmd, origen)

    elif actuador == "luces":
        activar = cmd == "ON"
        _actuadores["set_luces"](activar, origen)
        publicar("luces", {
            "estado":    "ON" if activar else "OFF",
            "activo":    activar,
            "modo":      "MANUAL" if origen in ("dashboard","boton_fisico") else "AUTOMATICO",
            "motivo":    origen,
            "timestamp": _ts(),
        })
        _guardar_actuador_log("luces", cmd, origen)

    elif actuador == "alarma":
        if cmd in ("OFF", "SILENCIAR"):
            _actuadores["set_alarma"](False, origen)
            publicar("alarma", {
                "estado":    "SILENCIADA" if cmd == "SILENCIAR" else "OFF",
                "buzzer":    False,
                "led_rojo":  False,
                "motivo":    origen,
                "timestamp": _ts(),
            })
            _guardar_actuador_log("alarma", cmd, origen)
        elif cmd == "ON":
            _actuadores["set_alarma"](True, origen)
            publicar("alarma", {
                "estado":    "ON",
                "buzzer":    True,
                "led_rojo":  True,
                "motivo":    origen,
                "timestamp": _ts(),
            })
            _guardar_actuador_log("alarma", "ON", origen)

    elif actuador == "modo":
        with _state["lock"]:
            _state["modo"] = cmd
        print(f"[Modo] Cambiado a: {cmd}")
        publicar("global", {
            "estado":    _state.get("global", "NORMAL"),
            "modo":      cmd,
            "timestamp": _ts(),
        })
        _guardar_evento("modo_cambiado", cmd, origen)

    elif actuador == "global" and cmd == "RESET":
        with _state["lock"]:
            _state["global"] = "NORMAL"
        publicar("global", {
            "estado":    "NORMAL",
            "modo":      _state.get("modo", "AUTOMATICO"),
            "timestamp": _ts(),
        }, retain=True)
        _guardar_evento("reset_estado_global", "NORMAL", origen)
        print(f"[Estado] Reset a NORMAL por {origen}")


def _publicar_riego(area, activar, origen):
    """Publica el estado del riego en los topics correspondientes."""
    suelo = _state.get(f"suelo{area}")

    # Verificar saturacion
    if activar and suelo is not None and suelo >= 80:
        estado = "BLOQUEADO_POR_SATURACION"
        activar = False
    else:
        estado = "ON" if activar else "OFF"

    key_area  = f"riego{area}"
    riego_str = f"RIEGO_AREA_{area}" if activar else "RIEGO_OFF"

    publicar(key_area, {
        "estado":    estado,
        "bomba":     activar,
        "area":      f"area{area}",
        "motivo":    origen,
        "timestamp": _ts(),
    })
    publicar("riego", {
        "estado":    riego_str,
        "bomba":     activar,
        "timestamp": _ts(),
    })
    _guardar_actuador_log(f"riego_area{area}", estado, origen)


def _guardar_comando(actuador, cmd, origen):
    from mongo_handler import guardar_comando
    guardar_comando(actuador, cmd, origen, _state.get("global", "NORMAL"))


def _guardar_actuador_log(actuador, accion, origen):
    from mongo_handler import guardar_actuador_log
    guardar_actuador_log(actuador, accion, origen, _state.get("global", "NORMAL"))


def _guardar_evento(tipo, valor, origen):
    from mongo_handler import registrar_evento
    registrar_evento(tipo, valor, origen, _state.get("global", "NORMAL"))

def _ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")