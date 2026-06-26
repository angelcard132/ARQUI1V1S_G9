from pymongo import MongoClient
from datetime import datetime
import threading
import time

# URI de conexion
MONGO_URI = "mongodb+srv://UserDB1:PasswordDB1@cluster0.2qomnft.mongodb.net/?appName=Cluster0"
DB_NAME = "invernadero"

# Cada cuanto se manda a MongoDB. El backend/MQTT puede seguir trabajando mas rapido.
MONGO_FLUSH_INTERVAL = 20

_db = None
_client = None
_worker = None
_stop_worker = threading.Event()
_queue_lock = threading.Lock()

# Cola en memoria para no bloquear el ciclo de sensores esperando respuesta de MongoDB.
_pending_inserts = {
    "sensor_readings": [],
    "events": [],
    "commands": [],
    "actuator_logs": [],
    "arm64_results": [],
}
_pending_status = None


def conectar():
    global _db, _client
    try:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _client.server_info()  # comprueba conexion solo al iniciar
        _db = _client[DB_NAME]
        print(f"[MongoDB] Conectado a '{DB_NAME}'")
        iniciar_worker()
        return _db
    except Exception as e:
        print(f"[MongoDB] Sin conexion: {e}")
        print("[MongoDB] Continuando sin persistencia")
        _db = None
        _client = None
        return None


def get_db():
    return _db


def iniciar_worker():
    global _worker
    if _db is None:
        return
    if _worker is not None and _worker.is_alive():
        return
    _stop_worker.clear()
    _worker = threading.Thread(target=_mongo_worker, daemon=True)
    _worker.start()
    print(f"[MongoDB] Guardado en segundo plano cada {MONGO_FLUSH_INTERVAL}s")


def detener_worker():
    _stop_worker.set()
    if _worker is not None and _worker.is_alive():
        _worker.join(timeout=5)
    flush_pendientes()
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass


def _encolar_insert(coleccion: str, documento: dict):
    if _db is None:
        return
    with _queue_lock:
        _pending_inserts.setdefault(coleccion, []).append(documento)


def _encolar_estado(documento: dict):
    global _pending_status
    if _db is None:
        return
    with _queue_lock:
        # Para el estado actual no interesa guardar 10 copias viejas; solo la ultima.
        _pending_status = documento


def _tomar_lote():
    global _pending_status
    with _queue_lock:
        inserts = {col: docs[:] for col, docs in _pending_inserts.items() if docs}
        for col in inserts:
            _pending_inserts[col].clear()
        status = _pending_status
        _pending_status = None
    return inserts, status


def _devolver_lote(inserts: dict, status: dict | None):
    global _pending_status
    with _queue_lock:
        for col, docs in inserts.items():
            _pending_inserts.setdefault(col, [])[:0] = docs
        if status is not None and _pending_status is None:
            _pending_status = status


def _mongo_worker():
    while not _stop_worker.wait(MONGO_FLUSH_INTERVAL):
        flush_pendientes()


def flush_pendientes():
    if _db is None:
        return

    inserts, status = _tomar_lote()
    if not inserts and status is None:
        return

    try:
        total = 0
        for coleccion, docs in inserts.items():
            if docs:
                _db[coleccion].insert_many(docs, ordered=False)
                total += len(docs)

        if status is not None:
            _db["system_status"].replace_one(
                {"_id": "current"},
                status,
                upsert=True,
            )
            total += 1

        print(f"[MongoDB] Lote enviado: {total} documento(s)")
    except Exception as e:
        print(f"[MongoDB] Error enviando lote, se conserva en memoria: {e}")
        _devolver_lote(inserts, status)


# Lecturas de sensores
def guardar_lectura(lectura: dict, estado_global: str):
    _encolar_insert("sensor_readings", {
        "timestamp": datetime.now(),
        "tipo": "sensor_reading",
        "origen": "raspberry_pi",
        "estado": estado_global,
        **lectura,
    })


# Eventos del sistema
def registrar_evento(tipo: str, valor, origen: str, estado_global: str):
    _encolar_insert("events", {
        "timestamp": datetime.now(),
        "tipo": tipo,
        "valor": str(valor),
        "origen": origen,
        "estado": estado_global,
    })
    print(f"[MongoDB] Evento en cola: {tipo} = {valor}")


# Comandos recibidos
def guardar_comando(actuador: str, cmd: str, origen: str, estado_global: str):
    _encolar_insert("commands", {
        "timestamp": datetime.now(),
        "actuador": actuador,
        "comando": cmd,
        "origen": origen,
        "estado": estado_global,
    })
    print(f"[MongoDB] Comando en cola: {actuador} -> {cmd} ({origen})")


# Estado global del sistema
def guardar_estado_sistema(estado: str, modo: str, sensores: dict, actuadores: dict):
    _encolar_estado({
        "_id": "current",
        "timestamp": datetime.now(),
        "estado": estado,
        "modo": modo,
        "sensores": sensores,
        "actuadores": actuadores,
    })


# Logs de actuadores
def guardar_actuador_log(actuador: str, accion: str, origen: str, estado_global: str):
    _encolar_insert("actuator_logs", {
        "timestamp": datetime.now(),
        "actuador": actuador,
        "accion": accion,
        "origen": origen,
        "estado": estado_global,
    })


# Resultados ARM64
def guardar_arm64(modulo: str, resultado: dict):
    _encolar_insert("arm64_results", {
        "timestamp": datetime.now(),
        "modulo": modulo,
        "resultado": resultado,
    })
    print(f"[MongoDB] ARM64 en cola: {modulo}")
