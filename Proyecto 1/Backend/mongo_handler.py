
from pymongo import MongoClient
from datetime import datetime

# URI de conexion 
MONGO_URI     = "mongodb+srv://UserDB1:PasswordDB1@cluster0.2qomnft.mongodb.net/?appName=Cluster0"
DB_NAME   = "invernadero"

_db = None

#
def conectar():

    global _db
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()   # dispara excepcion si no conecta
        _db = client[DB_NAME]
        print(f"[MongoDB] Conectado a '{DB_NAME}'")
        return _db
    except Exception as e:
        print(f"[MongoDB] Sin conexion: {e}")
        print("[MongoDB] Continuando sin persistencia")
        _db = None
        return None


def get_db():
    return _db


#  Lecturas de sensores
def guardar_lectura(lectura: dict, estado_global: str):
    """
    Guarda una lectura de sensores en 'sensor_readings'.
    lectura = { "temp": 28.5, "hum": 65, "luz": 320, "gas": 120, "suelo1": 55, "suelo2": 62 }
    """
    if _db is None:
        return
    try:
        _db["sensor_readings"].insert_one({
            "timestamp": datetime.now(),
            "tipo":      "sensor_reading",
            "origen":    "raspberry_pi",
            "estado":    estado_global,
            **lectura,
        })
    except Exception as e:
        print(f"[MongoDB] Error en sensor_readings: {e}")


#  Eventos del sistema 
def registrar_evento(tipo: str, valor, origen: str, estado_global: str):
    """
    Guarda un evento en 'events'.
    Ejemplos de tipo: "riego_activado", "gas_emergencia", "temperatura_alta"
    """
    if _db is None:
        return
    try:
        _db["events"].insert_one({
            "timestamp": datetime.now(),
            "tipo":      tipo,
            "valor":     str(valor),
            "origen":    origen,
            "estado":    estado_global,
        })
        print(f"[MongoDB] Evento: {tipo} = {valor}")
    except Exception as e:
        print(f"[MongoDB] Error en events: {e}")


#  Comandos recibidos 
def guardar_comando(actuador: str, cmd: str, origen: str, estado_global: str):
    """
    Guarda un comando en 'commands'.
    Se llama cada vez que llega un mensaje MQTT de control.
    """
    if _db is None:
        return
    try:
        _db["commands"].insert_one({
            "timestamp": datetime.now(),
            "actuador":  actuador,
            "comando":   cmd,
            "origen":    origen,
            "estado":    estado_global,
        })
        print(f"[MongoDB] Comando guardado: {actuador} -> {cmd} ({origen})")
    except Exception as e:
        print(f"[MongoDB] Error en commands: {e}")


#  Estado global del sistema
def guardar_estado_sistema(estado: str, modo: str, sensores: dict, actuadores: dict):
    """
    Actualiza (upsert) el documento de estado actual en 'system_status'.
    Solo existe un documento — se reemplaza cada vez.
    """
    if _db is None:
        return
    try:
        _db["system_status"].replace_one(
            {"_id": "current"},
            {
                "_id":        "current",
                "timestamp":  datetime.now(),
                "estado":     estado,
                "modo":       modo,
                "sensores":   sensores,
                "actuadores": actuadores,
            },
            upsert=True,
        )
    except Exception as e:
        print(f"[MongoDB] Error en system_status: {e}")


#  Logs de actuadores
def guardar_actuador_log(actuador: str, accion: str, origen: str, estado_global: str):
    """
    Guarda en 'actuator_logs' cada activacion/desactivacion de un actuador.
    """
    if _db is None:
        return
    try:
        _db["actuator_logs"].insert_one({
            "timestamp": datetime.now(),
            "actuador":  actuador,
            "accion":    accion,
            "origen":    origen,
            "estado":    estado_global,
        })
    except Exception as e:
        print(f"[MongoDB] Error en actuator_logs: {e}")


#  Resultados ARM64 
def guardar_arm64(modulo: str, resultado: dict):
    """
    Guarda en 'arm64_results' el resultado de un modulo ARM64.
    """
    if _db is None:
        return
    try:
        _db["arm64_results"].insert_one({
            "timestamp": datetime.now(),
            "modulo":    modulo,
            "resultado": resultado,
        })
        print(f"[MongoDB] ARM64 guardado: {modulo}")
    except Exception as e:
        print(f"[MongoDB] Error en arm64_results: {e}")