
import os
import json
import subprocess
from datetime import datetime

ARM64_DIR = "./arm64"
CSV_PATH  = "lecturas.csv"

# Mapeo columna - indice en lecturas.csv
# CSV_HEADER = ["ID","TEMP","HUM_AIRE","HUM_SUELO_1","HUM_SUELO_2","LUZ","GAS","RIEGO_1","RIEGO_2"]
COLUMNA_INDICE = {
    "TEMP":        1,
    "HUM_AIRE":    2,
    "HUM_SUELO_1": 3,
    "HUM_SUELO_2": 4,
    "LUZ":         5,
    "GAS":         6,
}

# Mapeo modulo - (binario, archivo de salida)
MODULOS = {
    "modulo_1_media":      "resultado_media.txt",
    "modulo_2_varianza":   "resultado_varianza.txt",
    "modulo_3_anomalias":  "resultado_anomalias.txt",
    "modulo_4_prediccion": "resultado_prediccion.txt",
    "modulo_5_tendencia":  "resultado_tendencia.txt",
}


def ejecutar_modulo_individual(modulo, columna, publicar_fn, guardar_arm64_fn, log_fn=print):

    ## Ejecuta un modulo ARM64 sobre la columna indicada.

    if modulo not in MODULOS:
        log_fn(f"[ARM64] Modulo desconocido: {modulo}")
        return

    if columna not in COLUMNA_INDICE:
        log_fn(f"[ARM64] Columna desconocida: {columna}")
        return

    if not os.path.exists(CSV_PATH):
        log_fn(f"[ARM64] {CSV_PATH} no existe — aun no hay 30 lecturas")
        return

    bin_path = os.path.join(ARM64_DIR, modulo)
    out_path = os.path.join(ARM64_DIR, MODULOS[modulo])
    indice   = COLUMNA_INDICE[columna]

    if not os.path.exists(bin_path):
        log_fn(f"[ARM64] Binario no encontrado: {bin_path}")
        return

    try:
        # Se pasa el indice de columna como argumento al binario ARM64
        # El binario debe leer sys.argv equivalente (registro x0 en _start) para saber que columna de lecturas.csv procesar.
        subprocess.run(
            [bin_path, str(indice)],
            timeout=15,
            check=True,
        )
        log_fn(f"[ARM64] {modulo} ejecutado sobre columna {columna} (indice {indice})")

        # Leer resultado
        resultado = {}
        with open(out_path) as f:
            for linea in f:
                linea = linea.strip()
                if "=" in linea:
                    k, v = linea.split("=", 1)
                    resultado[k.strip()] = v.strip()

        # Agregar metadata de que columna se uso
        resultado["COLUMNA"] = columna

        log_fn(f"[ARM64] Resultado: {resultado}")

        # Publicar al dashboard
        topic = f"invernadero/G9/arm64/{modulo}"
        publicar_fn(topic, json.dumps(resultado), qos=1)

        # Guardar en MongoDB
        guardar_arm64_fn(modulo, resultado)

    except subprocess.TimeoutExpired:
        log_fn(f"[ARM64] {modulo} excedio el tiempo limite")
    except subprocess.CalledProcessError as e:
        log_fn(f"[ARM64] {modulo} termino con error: {e}")
    except FileNotFoundError:
        log_fn(f"[ARM64] Archivo de salida no encontrado: {out_path}")
    except Exception as e:
        log_fn(f"[ARM64] Error inesperado: {e}")


def ejecutar_todos_los_modulos(publicar_fn, guardar_arm64_fn, log_fn=print):
    if not os.path.exists(CSV_PATH):
        log_fn(f"[ARM64] {CSV_PATH} no existe — no se pueden ejecutar los modulos")
        return

    for modulo, salida in MODULOS.items():
        bin_path = os.path.join(ARM64_DIR, modulo)
        out_path = os.path.join(ARM64_DIR, salida)
        if not os.path.exists(bin_path):
            log_fn(f"[ARM64] Binario no encontrado: {bin_path}")
            continue
        try:
            # Ejecucion sin argumentos para compatibilidad por lote (como en backendantiguo.py)
            subprocess.run([bin_path], timeout=15, check=True)
            resultado = {}
            if os.path.exists(out_path):
                with open(out_path) as f:
                    for linea in f:
                        if "=" in linea:
                            k, v = linea.strip().split("=", 1)
                            resultado[k.strip()] = v.strip()
                log_fn(f"[ARM64] {modulo} ejecutado de forma automatica: {resultado}")
                
                # Publicar por MQTT
                topic = f"invernadero/G9/arm64/{modulo}"
                publicar_fn(topic, json.dumps(resultado), qos=1)
                
                # Guardar en MongoDB
                guardar_arm64_fn(modulo, resultado)
        except Exception as e:
            log_fn(f"[ARM64 Error] Error al ejecutar modulo {modulo}: {e}")
