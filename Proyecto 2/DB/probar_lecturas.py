"""
Script de Diagnóstico y Pruebas de Lectura 

"""

import json
from typing import Dict, Any, List
from base_datos import (
    obtener_estado_actual,
    obtener_grafica,
    obtener_eventos,
    obtener_datos_dashboard_unificados
)

def imprimir_separador(titulo: str) -> None:
    """Imprime un separador visual formateado para la consola."""
    print("\n" + "=" * 70)
    print(f" LOG DE PRUEBA: {titulo} ".center(70, "#"))
    print("=" * 70)


def probar_extraccion_datos() -> None:
    """Ejecuta y audita todas las operaciones de lectura del módulo de base de datos."""
    
    print("[INFO] Iniciando secuencia de pruebas de lectura en MongoDB Atlas...")

    # PRUEBA 1: Obtener el documento maestro (system_status)

    imprimir_separador("1. DOCUMENTO MAESTRO EN TIEMPO REAL (_id: greenhouse_state_g9)")
    estado_maestro: Dict[str, Any] = obtener_estado_actual()
    
    if estado_maestro:
        print(f" Ultima actualización en Base de Datos: {estado_maestro.get('fecha_hora', 'N/A')}")
        # Formatear el diccionario a JSON estético para inspección visual
        print(json.dumps(estado_maestro, indent=2, ensure_ascii=False))
    else:
        print("[ADVERTENCIA] No se encontró el documento 'greenhouse_state_g9' o la colección está vacía.")


    # PRUEBA 2: Obtener arreglos históricos para las 6 gráficas (sensor_readings)
    imprimir_separador("2. SERIES TEMPORALES DIARIAS (Para Gráficas de Laboratorio)")
    
    for zona in ["area 1", "area 2"]:
        lecturas_grafica: List[Dict[str, Any]] = obtener_grafica(area=zona)
        print(f"\n-> [{zona.upper()}] Puntos de datos recuperados para hoy: {len(lecturas_grafica)}")
        
        # Muestra únicamente las últimas 2 lecturas en la terminal para no saturar la pantalla
        if lecturas_grafica:
            print(f"   Últimas muestras recolectadas:")
            for lectura in lecturas_grafica[-2:]:
                print(f"     - [{lectura.get('fecha_hora')}]: Temp: {lectura.get('temp')}°C | Hum A: {lectura.get('hum_a')}% | Suelo: {lectura.get('hum_s')}% | Luz: {lectura.get('luz')}lx | Gas: {lectura.get('gas')}ppm")
        else:
            print(f"   [!] Sin lecturas registradas el día de hoy para el cubo de {zona}.")


    # PRUEBA 3: Obtener bitácora de anomalías 
    imprimir_separador("3. REGISTRO CRONOLÓGICO DE EVENTOS Y ALERTAS (Top 10)")
    lista_eventos: List[Dict[str, Any]] = obtener_eventos()
    
    print(f" Total de eventos críticos/advertencias recuperados: {len(lista_eventos)}")
    for idx, evento in enumerate(lista_eventos, 1):
        print(f"  {idx}. [{evento.get('fecha_hora')}] [{evento.get('area', 'GENERAL').upper()}] ({evento.get('tipo_dato')}) -> {evento.get('mensaje')}")

    # PRUEBA 4: Obtener estructura exacta optimizada para el Dashboard Front-end
    imprimir_separador("4. COMPILADO UNIFICADO FINAL (Formato JSON Dashboard)")
    paquete_dashboard: Dict[str, Any] = obtener_datos_dashboard_unificados()
    
    # Esta es la estructura exacta que consumirá tu Front-end para mover las 6 gráficas
    print(json.dumps(paquete_dashboard, indent=2, ensure_ascii=False))
    
    imprimir_separador("FIN DE LA SECUENCIA DE DIAGNÓSTICO")


if __name__ == "__main__":
    probar_extraccion_datos()