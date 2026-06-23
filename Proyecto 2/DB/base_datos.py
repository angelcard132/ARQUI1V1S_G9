"""
Módulo de Persistencia y Extracción de Datos
"""
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import PyMongoError
from pymongo import DESCENDING

# Cargar variables de entorno del archivo .env
load_dotenv()

# Inicialización y configuración del cliente global de MongoDB
try:
    _URI: Optional[str] = os.getenv("MONGODB_URI")
    _DB_NAME: Optional[str] = os.getenv("MONGODB_DB")
    
    if not _URI or not _DB_NAME:
        raise ValueError("Las variables MONGODB_URI o MONGODB_DB no están configuradas en el .env")
        
    client: MongoClient = MongoClient(_URI, server_api=ServerApi("1"))
    db = client[_DB_NAME]
    print(f"[INFO] {datetime.now()}: Conexión exitosa a MongoDB Atlas.")
except (PyMongoError, ValueError) as err:
    print(f"[ERROR CRÍTICO] Fallo en la inicialización de la base de datos: {err}")
    db = None


def _get_timestamp() -> str:

    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# OPERACIONES DE ESCRITURA LA PERSISTENCIA

def guardar_lectura_sensores(area: str, temp: float, hum_a: float, hum_s: float, luz: int, gas: int) -> bool:

    if db is None:
        return False
        
    try:
        fecha_hora = _get_timestamp()
        dia_actual = datetime.now().strftime("%d/%m/%Y")
        
        # 1. sensor_readings: Estructura Time-Series en bloque para optimizar consultas de gráficos
        db["sensor_readings"].update_one(
            {"area": area, "fecha_dia": dia_actual},
            {
                "$setOnInsert": {
                    "tipo_dato": "TELEMETRIA", 
                    "origen": "SENSORES", 
                    "estado_relacionado": "OK"
                },
                "$push": {
                    "lecturas": {
                        "fecha_hora": fecha_hora, 
                        "temp": temp, 
                        "hum_a": hum_a, 
                        "hum_s": hum_s, 
                        "luz": luz, 
                        "gas": gas
                    }
                },
                "$set": {"valor": temp}
            },
            upsert=True
        )
        
        # 2. system_status: Documento de memoria caché central para telemetría en tiempo real
        db["system_status"].update_one(
            {"_id": "greenhouse_state"},
            {"$set": {
                "fecha_hora": fecha_hora,
                f"areas.{area}.telemetria": {
                    "temp": temp, 
                    "hum_a": hum_a, 
                    "hum_s": hum_s, 
                    "luz": luz, 
                    "gas": gas
                }
            }},
            upsert=True
        )
        return True
    except PyMongoError as err:
        print(f"[LOG ERROR] Error al persistir telemetría de {area}: {err}")
        return False


def guardar_log_actuador(area: str, actuador: str, estado: str, origen: str) -> bool:

    if db is None:
        return False
        
    try:
        fecha_hora = _get_timestamp()
        
        # Historial secuencial de cambios físicos
        db["actuator_logs"].insert_one({
            "fecha_hora": fecha_hora,
            "tipo_dato": "HARDWARE",
            "valor": estado,
            "origen": actuador,
            "estado_relacionado": "EJECUTADO",
            "area": area,
            "metodo": origen
        })
        
        # Sincronización del estado físico actual en el documento de control maestro
        db["system_status"].update_one(
            {"_id": "greenhouse_state"},
            {"$set": {
                "fecha_hora": fecha_hora,
                f"areas.{area}.actuadores.{actuador}": estado
            }},
            upsert=True
        )
        return True
    except PyMongoError as err:
        print(f"[LOG ERROR] Error al actualizar estado del actuador {actuador}: {err}")
        return False


def guardar_evento(area: str, tipo_dato: str, mensaje: str, valor: Any) -> bool:

    if db is None:
        return False
    try:
        db["events"].insert_one({
            "fecha_hora": _get_timestamp(),
            "tipo_dato": tipo_dato, # 'WARN' o 'CRITICAL'
            "valor": valor,
            "origen": "SISTEMA",
            "estado_relacionado": "ALERTA",
            "area": area,
            "mensaje": mensaje
        })
        return True
    except PyMongoError as err:
        print(f"[LOG ERROR] Error al insertar evento de alerta: {err}")
        return False


def guardar_comando_manual(area: str, actuador: str, orden: str) -> bool:

    if db is None:
        return False
    try:
        db["commands"].insert_one({
            "fecha_hora": _get_timestamp(),
            "tipo_dato": "MANUAL",
            "valor": orden,
            "origen": "DASHBOARD",
            "estado_relacionado": "RECIBIDO",
            "area": area,
            "actuador": actuador
        })
        return True
    except PyMongoError as err:
        print(f"[LOG ERROR] Error al auditar comando manual: {err}")
        return False


# OPERACIONES DE LECTURA 

def obtener_estado_actual() -> Dict[str, Any]:

    if db is None:
        return {}
    try:
        resultado = db["system_status"].find_one({"_id": "greenhouse_state_g9"})
        return resultado if resultado else {}
    except PyMongoError as err:
        print(f"[LOG ERROR] Error al leer estado actual del invernadero: {err}")
        return {}


def obtener_grafica(area: str) -> List[Dict[str, Any]]:

    if db is None:
        return []
    try:
        dia_actual = datetime.now().strftime("%d/%m/%Y")
        documento = db["sensor_readings"].find_one({"area": area, "fecha_dia": dia_actual})
        return documento["lecturas"] if documento and "lecturas" in documento else []
    except PyMongoError as err:
        print(f"[LOG ERROR] Error al consultar histórico para {area}: {err}")
        return []


def obtener_eventos() -> List[Dict[str, Any]]:

    if db is None:
        return []
    try:
        return list(db["events"].find().sort("_id", DESCENDING).limit(10))
    except PyMongoError as err:
        print(f"[LOG ERROR] Error al extraer logs de eventos: {err}")
        return []


def obtener_datos_dashboard_unificados() -> Dict[str, Any]:

    estado_maestro = obtener_estado_actual()
    alertas_recientes = obtener_eventos()
    
    estructurado_areas: Dict[str, Any] = {}
    
    for identificador_zona in ["area 1", "area 2"]:
        nodo_zona = estado_maestro.get("areas", {}).get(identificador_zona, {}) if estado_maestro else {}
        telemetria_cruda = nodo_zona.get("telemetria", {})
        
        estructurado_areas[identificador_zona] = {
            "telemetria": {
                "temperatura": telemetria_cruda.get("temp", None),
                "humedad_ambiental": telemetria_cruda.get("hum_a", None),
                "luz": telemetria_cruda.get("luz", None),
                "gas": telemetria_cruda.get("gas", None),
                "humedad_suelo": telemetria_cruda.get("hum_s", None)
            }
        }
        
    alertas_limpias: List[Dict[str, str]] = []
    for doc_evento in alertas_recientes:
        alertas_limpias.append({
            "area": str(doc_evento.get("area", "general")),
            "tipo_dato": str(doc_evento.get("tipo_dato", "WARN")),
            "mensaje": str(doc_evento.get("mensaje", "")),
            "fecha_hora": str(doc_evento.get("fecha_hora", ""))
        })
        
    return {
        "status": "success",
        "real_time": {
            "areas": estructurado_areas
        },
        "alertas": alertas_limpias
    }