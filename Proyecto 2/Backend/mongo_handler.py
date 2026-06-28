from pymongo import MongoClient
from datetime import datetime
from collections import deque
import threading
import time
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://UserDB1:PasswordDB1@cluster0.2qomnft.mongodb.net/?appName=Cluster0")
DB_NAME = "invernadero"

INTERVALO_MONGO = 20
MAX_LECTURAS_MEMORIA = 5

_client = None
_db = None
_buffer_lecturas = deque(maxlen=MAX_LECTURAS_MEMORIA)
_lock = threading.Lock()
_hilo_activo = False


def conectar():
    global _client, _db

    try:
        _client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
            socketTimeoutMS=3000,
            retryWrites=True
        )
        _client.server_info()
        _db = _client[DB_NAME]
        print(f"[MongoDB] Conectado a '{DB_NAME}'")
        iniciar_worker()
        return _db

    except Exception as e:
        print(f"[MongoDB] Sin conexion: {e}")
        print("[MongoDB] Continuando sin persistencia")
        _client = None
        _db = None
        return None


def get_db():
    return _db


def agregar_lectura_memoria(lectura: dict, estado_global: str):
    """
    No escribe directo a Mongo.
    Solo guarda en RAM las ultimas 5 lecturas.
    """
    doc = {
        "timestamp": datetime.now(),
        "tipo": "sensor_reading",
        "origen": "raspberry_pi",
        "estado": estado_global,
        **lectura,
    }

    with _lock:
        _buffer_lecturas.append(doc)


def flush_lecturas():
    """
    Envia a Mongo solo las ultimas 5 lecturas.
    """
    if _db is None:
        return

    with _lock:
        if not _buffer_lecturas:
            return

        lote = list(_buffer_lecturas)
        _buffer_lecturas.clear()

    try:
        _db["sensor_readings"].insert_many(lote, ordered=False)
        print(f"[MongoDB] Guardadas {len(lote)} lecturas")
    except Exception as e:
        print(f"[MongoDB] Error guardando lecturas: {e}")


def worker_mongo():
    while True:
        time.sleep(INTERVALO_MONGO)
        flush_lecturas()


def iniciar_worker():
    global _hilo_activo

    if _hilo_activo:
        return

    hilo = threading.Thread(target=worker_mongo, daemon=True)
    hilo.start()
    _hilo_activo = True
    print("[MongoDB] Worker iniciado cada 20s")


def registrar_evento(tipo: str, valor, origen: str, estado_global: str):
    if _db is None:
        return

    try:
        _db["events"].insert_one({
            "timestamp": datetime.now(),
            "tipo": tipo,
            "valor": str(valor),
            "origen": origen,
            "estado": estado_global,
        })
        print(f"[MongoDB] Evento: {tipo} = {valor}")
    except Exception as e:
        print(f"[MongoDB] Error en events: {e}")


def guardar_comando(actuador: str, cmd: str, origen: str, estado_global: str):
    if _db is None:
        return

    try:
        _db["commands"].insert_one({
            "timestamp": datetime.now(),
            "actuador": actuador,
            "comando": cmd,
            "origen": origen,
            "estado": estado_global,
        })
        print(f"[MongoDB] Comando: {actuador} -> {cmd}")
    except Exception as e:
        print(f"[MongoDB] Error en commands: {e}")


def guardar_estado_sistema(estado: str, modo: str, sensores: dict, actuadores: dict):
    if _db is None:
        return

    try:
        _db["system_status"].replace_one(
            {"_id": "current"},
            {
                "_id": "current",
                "timestamp": datetime.now(),
                "estado": estado,
                "modo": modo,
                "sensores": sensores,
                "actuadores": actuadores,
            },
            upsert=True,
        )
    except Exception as e:
        print(f"[MongoDB] Error en system_status: {e}")


def guardar_actuador_log(actuador: str, accion: str, origen: str, estado_global: str):
    if _db is None:
        return

    try:
        _db["actuator_logs"].insert_one({
            "timestamp": datetime.now(),
            "actuador": actuador,
            "accion": accion,
            "origen": origen,
            "estado": estado_global,
        })
    except Exception as e:
        print(f"[MongoDB] Error en actuator_logs: {e}")


def guardar_arm64(modulo: str, resultado: dict):
    if _db is None:
        return

    try:
        columna = resultado.get("COLUMNA", "DESCONOCIDA")
        
        nombres_modulos = {
            "modulo_1_media": "Módulo 1 (Media Ponderada)",
            "modulo_2_varianza": "Módulo 2 (Varianza y Desviación Estándar)",
            "modulo_3_anomalias": "Módulo 3 (Detección de Anomalías)",
            "modulo_4_prediccion": "Módulo 4 (Predicción Lineal)",
            "modulo_5_tendencia": "Módulo 5 (Tendencia Acumulada)",
        }
        modulo_friendly = nombres_modulos.get(modulo, modulo)
        
        nombres_columnas = {
            "TEMP": "Temperatura",
            "HUM_AIRE": "Humedad Aire",
            "HUM_SUELO_1": "Humedad Suelo 1",
            "HUM_SUELO_2": "Humedad Suelo 2",
            "LUZ": "Luz",
            "GAS": "Gas",
        }
        columna_friendly = nombres_columnas.get(columna, columna)

        etiqueta_ejecucion = f"{modulo_friendly} sobre columna {columna_friendly}"

        _db["arm64_results"].insert_one({
            "timestamp": datetime.now(),
            "modulo": modulo,
            "columna": columna,
            "etiqueta": etiqueta_ejecucion,
            "descripcion": f"Resultados de haber ejecutado el {modulo} con la columna de {columna.lower()}",
            "resultado": resultado,
        })
        print(f"[MongoDB] ARM64 guardado: {modulo} ({columna}) -> {etiqueta_ejecucion}")
    except Exception as e:
        print(f"[MongoDB] Error en arm64_results: {e}")


def guardar_decision_motor(lectura: dict, res: dict):
    if _db is None:
        return

    try:
        status_raw = res.get("STATUS", "OK")
        action = res.get("ACTION", "NO_ACTION")
        risk = res.get("RISK", "LOW")
        target = res.get("TARGET", "GENERAL")
        reason = res.get("REASON", "NORMAL_CONDITIONS")
        
        # Mapeamos a enteros si es posible
        try:
            val_int = int(res.get("VALUE", "0"))
        except ValueError:
            val_int = 0
            
        try:
            ind_int = int(res.get("INDICATOR", "0"))
        except ValueError:
            ind_int = 0

        doc = {
            "timestamp": datetime.now(),
            "source": "live_engine",
            "module": "motor_vivo",
            "input": lectura,
            "result": {
                "VALUE": val_int,
                "INDICATOR": ind_int,
                "REASON": reason,
            },
            "decision": action,
            "risk": risk,
            "status": status_raw,
        }

        if status_raw == "ERROR":
            doc["error_detail"] = f"{res.get('ERROR', '')}: {res.get('DETAIL', '')}"

        _db["arm64_results"].insert_one(doc)
        print(f"[MongoDB] Decisión Motor Guardada: {action} ({risk})")
    except Exception as e:
        print(f"[MongoDB] Error guardando decision del motor: {e}")