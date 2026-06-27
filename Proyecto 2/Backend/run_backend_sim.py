import time
import os
import sys
from datetime import datetime

import mongo_handler
import mqtt_handler

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT   = 1883
MQTT_ID     = "G9_backend_sim_pc"

state = {
    "lock":        None, 
    "global":      "NORMAL",
    "modo":        "AUTOMATICO",
    "temp":        25.0,
    "hum":         60.0,
    "luz":         300,
    "gas":         100,
    "suelo1":      50,
    "suelo2":      50,
    "riego1":      False,
    "riego2":      False,
    "ventilador":  False,
    "luces":       False,
    "alarma":      False,
}

import threading
state["lock"] = threading.Lock()

def dummy_riego(area, activar, origen):
    print(f"[SIM] Bomba Riego Area {area} -> {'ON' if activar else 'OFF'} (Origen: {origen})")
    state[f"riego{area}"] = activar

def dummy_ventilador(activar, origen):
    print(f"[SIM] Ventilador -> {'ON' if activar else 'OFF'} (Origen: {origen})")
    state["ventilador"] = activar

def dummy_luces(activar, origen):
    print(f"[SIM] Luces -> {'ON' if activar else 'OFF'} (Origen: {origen})")
    state["luces"] = activar

def dummy_alarma(activar, origen):
    print(f"[SIM] Alarma -> {'ON' if activar else 'OFF'} (Origen: {origen})")
    state["alarma"] = activar

if __name__ == "__main__":
    print("=" * 55)
    print("  Simulador de Backend para PC (Windows/Local) - Grupo 9")
    print("  Este script permite probar la ejecución de módulos ARM64")
    print("  realizando los cálculos en Python cuando corre en PC.")
    print("=" * 55)

    # 1. MongoDB
    print("[Base de Datos] Conectando a MongoDB...")
    db = mongo_handler.conectar()

    # 2. MQTT
    print(f"[MQTT] Conectando al broker {MQTT_BROKER}...")
    mqtt_client = mqtt_handler.configurar_mqtt(
        broker     = MQTT_BROKER,
        port       = MQTT_PORT,
        client_id  = MQTT_ID,
        state      = state,
        db         = db,
        actuadores = {
            "activar_riego":  dummy_riego,
            "set_ventilador": dummy_ventilador,
            "set_luces":      dummy_luces,
            "set_alarma":     dummy_alarma,
        },
    )

    print("\n[Simulación] backend listo ")


    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Simulación] Apagando backend de pruebas...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("[Simulación] Desconectado.")
