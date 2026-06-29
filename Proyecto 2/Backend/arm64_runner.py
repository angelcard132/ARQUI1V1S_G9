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
    # Fase 1
    "modulo_1_media":      "resultado_media.txt",
    "modulo_2_varianza":   "resultado_varianza.txt",
    "modulo_3_anomalias":  "resultado_anomalias.txt",
    "modulo_4_prediccion": "resultado_prediccion.txt",
    "modulo_5_tendencia":  "resultado_tendencia.txt",
    
    # Fase 2
    "modulo_1_rmse":           "resultado_rmse.txt",
    "modulo_2_regresion":      "resultado_regresion.txt",
    "modulo_3_prediccion":     "resultado_prediccion.txt",
    "modulo_4_integral_error": "resultado_integral.txt",
    "modulo_5_derivada_local": "resultado_derivada.txt",
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

    
    fase2_mods = ["modulo_1_rmse", "modulo_2_regresion", "modulo_3_prediccion", "modulo_4_integral_error", "modulo_5_derivada_local"]
    ARM64_DIR = "./arm64/arm63p2" if modulo in fase2_mods else "./arm64/arm64p1"
    if not os.path.exists(ARM64_DIR) and not os.path.exists("./arm64"):
        ARM64_DIR = "./arm63p2" if modulo in fase2_mods else "./arm64p1"

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
        elif modulo == "modulo_1_rmse":
            ideal = 25
            if columna == "TEMP": ideal = 25
            elif columna == "HUM_AIRE": ideal = 60
            elif columna in ("HUM_SUELO_1", "HUM_SUELO_2"): ideal = 55
            elif columna == "LUZ": ideal = 500
            elif columna == "GAS": ideal = 150
            
            errors_sq = [(val - ideal)**2 for val in values]
            mse = sum(errors_sq) // N if N > 0 else 0
            import math
            rmse = int(math.isqrt(mse))
            lines = [
                "MODULE=RMSE",
                f"TOTAL_VALUES={N}",
                f"IDEAL={ideal}",
                f"RMSE={rmse}"
            ]
        elif modulo == "modulo_2_regresion":
            sum_x = sum(range(N))
            sum_y = sum(values)
            sum_xx = sum(i**2 for i in range(N))
            sum_xy = sum(i * val for i, val in enumerate(values))
            num = N * sum_xy - sum_x * sum_y
            den = N * sum_xx - sum_x * sum_x
            slope_x100 = (num * 100) // den if den != 0 else 0
            trend = "ASCENDING" if slope_x100 > 0 else "DESCENDING" if slope_x100 < 0 else "STABLE"
            lines = [
                "MODULE=LINEAR_REGRESSION",
                f"TOTAL_VALUES={N}",
                f"SLOPE_X100={slope_x100}",
                f"TREND={trend}"
            ]
        elif modulo == "modulo_3_prediccion":
            K = 10
            sum_x = sum(range(N))
            sum_y = sum(values)
            sum_xx = sum(i**2 for i in range(N))
            sum_xy = sum(i * val for i, val in enumerate(values))
            num = N * sum_xy - sum_x * sum_y
            den = N * sum_xx - sum_x * sum_x
            slope_x100 = (num * 100) // den if den != 0 else 0
            intercept_x100 = (sum_y * 100 - slope_x100 * sum_x) // N if N > 0 else 0
            x_future = N + K
            y_pred = (slope_x100 * x_future + intercept_x100) // 100
            lines = [
                "MODULE=PREDICTION",
                f"TOTAL_VALUES={N}",
                f"K={K}",
                f"SLOPE_X100={slope_x100}",
                f"INTERCEPT_X100={intercept_x100}",
                f"PREDICTED_10={y_pred}"
            ]
        elif modulo == "modulo_4_integral_error":
            ideal = 25
            if columna == "TEMP": ideal = 25
            elif columna == "HUM_AIRE": ideal = 60
            elif columna in ("HUM_SUELO_1", "HUM_SUELO_2"): ideal = 55
            elif columna == "LUZ": ideal = 500
            elif columna == "GAS": ideal = 150
            
            errors = [abs(val - ideal) for val in values]
            integral = 0
            for i in range(N - 1):
                integral += (errors[i] + errors[i+1]) // 2
            lines = [
                "MODULE=ERROR_INTEGRAL",
                f"TOTAL_VALUES={N}",
                f"IDEAL={ideal}",
                f"ERROR_INTEGRAL={integral}"
            ]
        elif modulo == "modulo_5_derivada_local":
            max_slope = 0
            if N >= 5:
                for i in range(N - 4):
                    win = values[i : i+5]
                    sum_y = sum(win)
                    sum_xy = sum(j * val for j, val in enumerate(win))
                    slope = ((5 * sum_xy - 10 * sum_y) * 100) // 50
                    if abs(slope) > max_slope:
                        max_slope = abs(slope)
            lines = [
                "MODULE=LOCAL_DERIVATIVE",
                f"TOTAL_VALUES={N}",
                "WINDOW_SIZE=5",
                f"MAX_LOCAL_SLOPE_X100={max_slope}"
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
        
        ideal = 25
        if columna == "TEMP": ideal = 25
        elif columna == "HUM_AIRE": ideal = 60
        elif columna in ("HUM_SUELO_1", "HUM_SUELO_2"): ideal = 55
        elif columna == "LUZ": ideal = 500
        elif columna == "GAS": ideal = 150
        

        cmd_args = [f"./{modulo}", "lecturas.csv", str(l_ini), str(l_fin), columna]
        if modulo in ("modulo_1_rmse", "modulo_4_integral_error"):
            cmd_args.append(str(ideal))

        try:
            res_proc = subprocess.run(
                cmd_args,
                cwd=ARM64_DIR,
                timeout=15,
                check=True,
                capture_output=True,
                text=True
            )
            log_fn(f"[ARM64] {modulo} ejecutado con argumentos: {cmd_args}")
            
            
            if modulo == "modulo_1_rmse" and res_proc.stdout:
                with open(out_path, "w", encoding="utf-8") as f_out:
                    f_out.write(res_proc.stdout)
                    
        except subprocess.TimeoutExpired:
            log_fn(f"[ARM64] {modulo} excedio el tiempo limite")
            return
        except subprocess.CalledProcessError as e:
            log_fn(f"[ARM64] {modulo} termino con error: {e}")
            if e.stderr:
                log_fn(f"[ARM64 Stderr] {e.stderr}")
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