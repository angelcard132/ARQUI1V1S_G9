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
    "analizador_historico":     "resultado_historico.txt",
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

    if modulo == "analizador_historico":
        ARM64_DIR = "./arm64"
    else:
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
    N_clean = 0
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
            if len(row) >= 9:
                val = row[indice].strip()
                if val.isdigit() or (val.startswith('-') and val[1:].isdigit()):
                    row[1] = val
                    rows_to_write.append(row)
        
        N_clean = len(rows_to_write) - 1
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

    if not os.path.exists(bin_path):
        log_fn(f"[ARM64] Binario no encontrado: {bin_path}")
        return
    
    ideal = 25
    if columna == "TEMP": ideal = 25
    elif columna == "HUM_AIRE": ideal = 60
    elif columna in ("HUM_SUELO_1", "HUM_SUELO_2"): ideal = 55
    elif columna == "LUZ": ideal = 500
    elif columna == "GAS": ideal = 150
    
    cmd_args = [f"./{modulo}", "lecturas.csv", "1", str(N_clean), columna, str(ideal)]

    try:
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
            err_res = {
                "MODULE": "HISTORICAL_ANALYZER",
                "STATUS": "ERROR",
                "ERROR": "TIMEOUT",
                "DETAIL": f"El módulo {modulo} excedió el tiempo límite de ejecución."
            }
            publicar_fn(f"invernadero/G9/arm64/{modulo}", json.dumps(err_res), qos=1)
            return
        except subprocess.CalledProcessError as e:
            log_fn(f"[ARM64] {modulo} termino con error: {e}")
            err_detail = e.stderr.strip() if e.stderr else (e.output.strip() if e.output else str(e))
            parsed_err = {}
            for part in err_detail.replace("\n", " ").split():
                if "=" in part:
                    k, v = part.split("=", 1)
                    parsed_err[k.strip()] = v.strip()
            
            err_res = {
                "MODULE": "HISTORICAL_ANALYZER",
                "STATUS": "ERROR",
                "ERROR": parsed_err.get("ERROR", "EXECUTION_ERROR"),
                "DETAIL": parsed_err.get("DETAIL", err_detail)
            }
            publicar_fn(f"invernadero/G9/arm64/{modulo}", json.dumps(err_res), qos=1)
            return
        except Exception as e:
            log_fn(f"[ARM64] Error al ejecutar binario {modulo}: {e}")
            err_res = {
                "MODULE": "HISTORICAL_ANALYZER",
                "STATUS": "ERROR",
                "ERROR": "EXECUTION_FAILED",
                "DETAIL": str(e)
            }
            publicar_fn(f"invernadero/G9/arm64/{modulo}", json.dumps(err_res), qos=1)
            return
    except Exception as outer_e:
        log_fn(f"[ARM64] Error general en orquestador para {modulo}: {outer_e}")
        return

    try:
        resultado = {}
        with open(out_path, encoding="utf-8") as f:
            content = f.read().strip()
            parts = content.replace("\n", " ").split()
            for part in parts:
                if "=" in part:
                    k, v = part.split("=", 1)
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