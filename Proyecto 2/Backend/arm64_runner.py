import os
import json
import subprocess
from datetime import datetime

ARM64_DIR = "./arm64p1"
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


def ejecutar_modulo_individual(modulo, columna, publicar_fn, guardar_arm64_fn, log_fn=print, archivo="lecturas.csv", linea_inicial=1, linea_final=30):

    ## Ejecuta un modulo ARM64 sobre la columna indicada.

    if modulo not in MODULOS:
        log_fn(f"[ARM64] Modulo desconocido: {modulo}")
        return

    if columna not in COLUMNA_INDICE:
        log_fn(f"[ARM64] Columna desconocida: {columna}")
        return

    # Validar existencia del archivo
    if not os.path.exists(archivo):
        log_fn(f"[ARM64] {archivo} no existe")
        err_res = {
            "MODULE": "HISTORICAL_ANALYZER",
            "STATUS": "ERROR",
            "ERROR": "FILE_NOT_FOUND",
            "DETAIL": f"El archivo '{archivo}' no existe."
        }
        publicar_fn(f"invernadero/G9/arm64/{modulo}", json.dumps(err_res), qos=1)
        return

    # Validar rango inicial y final
    try:
        l_ini = int(linea_inicial)
        l_fin = int(linea_final)
    except ValueError:
        err_res = {
            "MODULE": "HISTORICAL_ANALYZER",
            "STATUS": "ERROR",
            "ERROR": "INVALID_RANGE",
            "DETAIL": "Los límites de línea deben ser números enteros."
        }
        publicar_fn(f"invernadero/G9/arm64/{modulo}", json.dumps(err_res), qos=1)
        return

    if l_ini < 1 or l_fin < l_ini:
        err_res = {
            "MODULE": "HISTORICAL_ANALYZER",
            "STATUS": "ERROR",
            "ERROR": "INVALID_RANGE",
            "DETAIL": f"Rango inválido: L{l_ini}-L{l_fin}."
        }
        publicar_fn(f"invernadero/G9/arm64/{modulo}", json.dumps(err_res), qos=1)
        return

    # Ensure output directory exists
    os.makedirs(ARM64_DIR, exist_ok=True)

    bin_path = os.path.join(ARM64_DIR, modulo)
    out_path = os.path.join(ARM64_DIR, MODULOS[modulo])
    indice   = COLUMNA_INDICE[columna]

    import csv

    target_csv = os.path.join(ARM64_DIR, "lecturas.csv")
    try:
        # Leer filas de datos
        data_rows = []
        with open(archivo, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                if len(row) > 0 and row[0] == '$':
                    break
                data_rows.append(row)

        total_filas = len(data_rows)
        if l_ini > total_filas or l_fin > total_filas:
            err_res = {
                "MODULE": "HISTORICAL_ANALYZER",
                "STATUS": "ERROR",
                "ERROR": "INVALID_RANGE",
                "DETAIL": f"Las líneas solicitadas superan la longitud del archivo ({total_filas} filas)."
            }
            publicar_fn(f"invernadero/G9/arm64/{modulo}", json.dumps(err_res), qos=1)
            return

        sliced_rows = data_rows[l_ini - 1 : l_fin]

        if len(sliced_rows) < 2:
            err_res = {
                "MODULE": "HISTORICAL_ANALYZER",
                "STATUS": "ERROR",
                "ERROR": "INSUFFICIENT_DATA",
                "DETAIL": f"El rango seleccionado contiene {len(sliced_rows)} datos, se requieren al menos 2."
            }
            publicar_fn(f"invernadero/G9/arm64/{modulo}", json.dumps(err_res), qos=1)
            return

        rows_to_write = [header]
        for row in sliced_rows:
            if len(row) > max(1, indice):
                row[1] = row[indice]  
            rows_to_write.append(row)
        rows_to_write.append(['$'])

        with open(target_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows_to_write)
        
        log_fn(f"[ARM64] CSV preparado en {target_csv}: columna {columna} mapeada a TEMP con rango L{l_ini}-L{l_fin}")
    except Exception as e:
        log_fn(f"[ARM64] Error al preprocesar CSV: {e}")
        err_res = {
            "MODULE": "HISTORICAL_ANALYZER",
            "STATUS": "ERROR",
            "ERROR": "INTERNAL_ERROR",
            "DETAIL": f"Error al preprocesar CSV: {e}"
        }
        publicar_fn(f"invernadero/G9/arm64/{modulo}", json.dumps(err_res), qos=1)
        return

    import sys
    use_simulation = (sys.platform == "win32") or (not os.path.exists(bin_path))

    if use_simulation:
        log_fn(f"[ARM64 Simulation] Ejecutando calculo simulado en Python para {modulo} sobre {columna}")
        values = []
        try:
            with open(target_csv, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader) # skip header
                for row in reader:
                    if len(row) > 0 and row[0] == '$':
                        break
                    if len(row) > 1:
                        values.append(int(row[1]))
        except Exception as e:
            log_fn(f"[ARM64 Simulation] Error al leer CSV: {e}")
            return

        lines = []
        N = len(values)
        if modulo == "modulo_1_media":
            sum_x = sum(values)
            weight_sum = sum(i + 1 for i in range(N))
            weighted_sum = sum(val * (i + 1) for i, val in enumerate(values))
            weighted_mean = (weighted_sum + weight_sum // 2) // weight_sum if weight_sum > 0 else 0
            lines = [
                "MODULE=WEIGHTED_MEAN",
                f"TOTAL_VALUES={N}",
                f"SUM_X={sum_x}",
                f"WEIGHT_SUM={weight_sum}",
                f"WEIGHTED_MEAN={weighted_mean}"
            ]
        elif modulo == "modulo_2_varianza":
            mean = sum(values) // N if N > 0 else 0
            variance = sum((x - mean) ** 2 for x in values) // N if N > 0 else 0
            import math
            std_dev = int(math.isqrt(variance)) if variance >= 0 else 0
            lines = [
                "MODULE=VARIANCE",
                f"TOTAL_VALUES={N}",
                f"MEAN={mean}",
                f"VARIANCE={variance}",
                f"STD_DEV={std_dev}"
            ]
        elif modulo == "modulo_3_anomalias":
            mean = sum(values) // N if N > 0 else 0
            variance = sum((x - mean) ** 2 for x in values) // N if N > 0 else 0
            import math
            std_dev = int(math.isqrt(variance)) if variance >= 0 else 0
            anomalies = 0
            for x in values:
                if std_dev > 0 and abs(x - mean) > 2 * std_dev:
                    anomalies += 1
            risk = "NORMAL" if anomalies == 0 else "MEDIUM" if anomalies <= 3 else "HIGH"
            lines = [
                "MODULE=ANOMALY_DETECTION",
                f"TOTAL_VALUES={N}",
                f"MEAN={mean}",
                f"STD_DEV={std_dev}",
                f"ANOMALIES={anomalies}",
                f"SYSTEM_RISK={risk}"
            ]
        elif modulo == "modulo_4_prediccion":
            initial_val = values[0] if N > 0 else 0
            final_val = values[-1] if N > 0 else 0
            total_diff = final_val - initial_val
            avg_change = total_diff // (N - 1) if N > 1 else 0
            next_val = final_val + avg_change
            lines = [
                "MODULE=PREDICTION",
                f"TOTAL_VALUES={N}",
                f"INITIAL_VALUE={initial_val}",
                f"FINAL_VALUE={final_val}",
                f"TOTAL_DIFF={total_diff}",
                f"AVG_CHANGE={avg_change}",
                f"NEXT_VALUE={next_val}"
            ]
        elif modulo == "modulo_5_tendencia":
            increments = 0
            decrements = 0
            max_up = 0
            max_down = 0
            curr_up = 0
            curr_down = 0
            for i in range(1, N):
                diff = values[i] - values[i-1]
                if diff > 0:
                    increments += 1
                    curr_up += 1
                    curr_down = 0
                    if curr_up > max_up:
                        max_up = curr_up
                elif diff < 0:
                    decrements += 1
                    curr_down += 1
                    curr_up = 0
                    if curr_down > max_down:
                        max_down = curr_down
                else:
                    curr_up = 0
                    curr_down = 0
            accum_diff = values[-1] - values[0] if N > 0 else 0
            trend = "UP" if increments > decrements else "DOWN" if decrements > increments else "STABLE"
            lines = [
                "MODULE=ADVANCED_TREND",
                f"TOTAL_VALUES={N}",
                f"INCREMENTS={increments}",
                f"DECREMENTS={decrements}",
                f"MAX_UP_STREAK={max_up}",
                f"MAX_DOWN_STREAK={max_down}",
                f"ACCUM_DIFF={accum_diff}",
                f"TREND={trend}"
            ]
        
        try:
            with open(out_path, mode='w', encoding='utf-8') as f:
                f.write("\n".join(lines) + "\n")
        except Exception as e:
            log_fn(f"[ARM64 Simulation] Error al escribir archivo de salida: {e}")
            return
    else:
        if not os.path.exists(bin_path):
            log_fn(f"[ARM64] Binario no encontrado: {bin_path}")
            return
        try:
            subprocess.run(
                [f"./{modulo}"],
                cwd=ARM64_DIR,
                timeout=15,
                check=True,
            )
            log_fn(f"[ARM64] {modulo} ejecutado sobre columna {columna}")
        except subprocess.TimeoutExpired:
            log_fn(f"[ARM64] {modulo} excedio el tiempo limite")
            return
        except subprocess.CalledProcessError as e:
            log_fn(f"[ARM64] {modulo} termino con error: {e}")
            return

    try:
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
    except FileNotFoundError:
        log_fn(f"[ARM64] Archivo de salida no encontrado: {out_path}")
    except Exception as e:
        log_fn(f"[ARM64] Error al procesar resultados: {e}")