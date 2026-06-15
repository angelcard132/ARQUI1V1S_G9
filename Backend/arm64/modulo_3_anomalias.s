/*---------------------------------------------------------------------------------
Tulio Jafeth Pirir Schuman || 201700698 
Rutina 3: Detección estadística de anomalías
---------------------------------------------------------------------------------*/

/*
  1. VALIDACIÓN Y PRECARGA:
     - _start: Punto de entrada. Valida argumentos en el Stack (argc/argv).
     - cargar_datos_loop: Lee las 30 celdas del CSV y las guarda en 'array_datos'.

  2. CÁLCULO DE MEDIA ARITMÉTICA:
     - calcular_media: Inicializa registros para el promedio.
     - sum_media_loop: Acumula el valor lineal de los 30 elementos.
     - div_media: Ejecuta la división final (Sumatoria / 30) para fijar la MEDIA.

  3. CÁLCULO DE DESVIACIÓN ESTÁNDAR (FPU MAP):
     - calcular_desviacion: Inicializa registros para la dispersión.
     - sum_varianza_loop: Acumula la distancia cuadrática: (X - MEDIA)^2.
     - obtener_raiz_directa: Calcula la VARIANZA y extrae su raíz cuadrada entera
       por hardware (instrucción FSQRT) para fijar la DESVIACIÓN ESTÁNDAR.

  4. EVALUACIÓN DE ANOMALÍAS (Z-SCORE):
     - evaluar_anomalias: Inicializa el contador del análisis de riesgo.
     - z_score_loop: Calcula el Z-Score individualizado de cada muestra.
     - verificar_regla: Modula el valor absoluto (|Z|) y valida si supera el 
       umbral crítico (>= 2). Si se cumple, incrementa el contador de anomalías.
     - siguiente_z: Controla el desplazamiento del iterador hacia el próximo dato.

  5. PERSISTENCIA Y SALIDA DE DATOS:
     - abrir_descriptor_salida: Abre el archivo 'resultado_anomalias.txt'.
     - Bloques de Impresión Dúal: Secciones espejo que formatean y escriben los
       resultados numéricos de forma síncrona en Consola (stdout) y en el archivo .txt.
     - imprimir_normal / medium / high: Bifurcación que asigna la etiqueta final
       de riesgo sistémico según el volumen total de anomalías detectadas.
     - escribir_riesgo: Plasma la etiqueta de riesgo en pantalla y disco.

  6. MANEJO DE EXCEPCIONES Y SYSCALLS:
     - finalizar_proceso / salto: Libera los File Descriptors y añade saltos de línea.
     - no_argumento / error_extraccion / exit_error: Interrupciones por hardware 
       que abortan el hilo con código de estado (1) ante fallas operativas.
     - finalizar: Cierre seguro del programa enviando el Exit Code (0) al Kernel.



     
=================================================================================*/

.section .data
.align 2                                    // Alineación de memoria a límites de 4 bytes
msg_inicio:
    .asciz "--- INICIANDO MODULO 3 DETECCION DE ANOMALIAS ---\n"
    len_inicio = . - msg_inicio - 1         

output_filename:                                 
    .asciz "resultado_anomalias.txt"         

msg_fin:
    .asciz "\n--- FIN DEL ARCHIVO (Reporte guardado en resultado_anomalias.txt) ---\n"
    len_fin = . - msg_fin - 1                

// --- CONSTANTES DE FORMATEO PARA EL REPORTE DE SALIDA ---
lbl_MODULE:
    .asciz "MODULE=ANOMALY_DETECTION\n"     
    len_MODULE = . - lbl_MODULE - 1

lbl_TOTAL_VALUES:
    .asciz "TOTAL_VALUES=30\n"              
    len_TOTAL_VALUES = . - lbl_TOTAL_VALUES - 1

lbl_MEAN:
    .asciz "MEAN="                           
    len_MEAN = . - lbl_MEAN - 1

lbl_STD_DEV:
    .asciz "STD_DEV="                        
    len_STD_DEV = . - lbl_STD_DEV - 1
 
lbl_ANOMALIES:
    .asciz "ANOMALIES="                      
    len_ANOMALIES = . - lbl_ANOMALIES - 1

lbl_SYSTEM_RISK:
    .asciz "SYSTEM_RISK="                    
    len_SYSTEM_RISK = . - lbl_SYSTEM_RISK - 1

// --- TEXTOS PARA LA CLASIFICACIÓN DEL RIESGO ---
risk_normal:
    .asciz "NORMAL\n"                        
    len_risk_normal = . - risk_normal - 1

risk_medium:
    .asciz "MEDIUM\n"                        
    len_risk_medium = . - risk_medium - 1

risk_high:
    .asciz "HIGH\n"                          
    len_risk_high = . - risk_high - 1

msg_columna:
    .asciz "Columna seleccionada para operar: " 
    len_columna = . - msg_columna - 1

msg_no_arg:
    .ascii "Error: Debe enviar el numero de columna desde el backend\n" 
    msg_no_arg_len = . - msg_no_arg

.align 2                                    
txt_newline:    
    .byte 10                                


.section .bss
.align 4                                    
buffer_columna:
    .skip 16                                
.align 8                                    
array_datos:
    .skip 240                               // Espacio para 30 enteros de 64 bits (30 * 8 bytes)


.section .text
.global _start

_start:
    # -----------------------------------------------------------------
    # EXTRACCIÓN Y VALIDACIÓN DE ARGUMENTOS
    # -----------------------------------------------------------------
    ldr     x0, [sp]                        // Carga argc desde el stack

    cmp     x0, #2                          // Verifica argumentos mínimos necesarios
    blt     no_argumento                    

    ldr     x0, [sp, #16]                   // Carga dirección de argv[1]
    bl      parse_int                       // Convierte argumento ASCII a entero binario
    mov     x20, x0                         // Almacena ID numérico de la columna en x20

    # -- CONTROLES DE RANGO (COLUMNAS 1 A 8) --
    cmp     x20, #1                         
    blt     exit_error                      
    cmp     x20, #8                         
    bgt     exit_error                      

    # -----------------------------------------------------------------
    # IMPRESIÓN DE ENTORNO E INFO EN CONSOLA
    # -----------------------------------------------------------------
    mov     x0, #1                          // stdout descriptor
    adr     x1, msg_inicio                  
    mov     x2, #len_inicio                 
    bl      write_result                    

    mov     x0, #1                          
    adr     x1, msg_columna                 
    mov     x2, #len_columna                
    bl      write_result                    

    mov     x0, x20                         // Parámetro numérico de columna
    adr     x1, buffer_columna              
    bl      int_to_ascii                    

    mov     x2, x0                          // Longitud de la cadena devuelta
    mov     x0, #1                          
    adr     x1, buffer_columna              
    bl      write_result                    
    bl      newline                         

    # -----------------------------------------------------------------
    # PROCESAMIENTO DE ARCHIVO CSV Y PRECARGA DE ARREGLO
    # -----------------------------------------------------------------
    bl      read_csv                        // Inicializa lectura del archivo CSV
    cmp     x0, #0                          
    blt     exit_error                      

    mov     x21, #0                         // Inicializa iterador del bucle (i = 0)
    adr     x22, array_datos                // Carga dirección base del arreglo objetivo

cargar_datos_loop:
    cmp     x21, #30                        // Límite de control para 30 lecturas
    bge     calcular_media                  

    mov     x0, x21                         // Índice de fila actual
    mov     x1, x20                         // Índice de columna seleccionada
    adr     x2, buffer_columna              
    mov     x3, #16                         
    bl      get_column                      
    
    cmp     x0, #0                          // Valida éxito de la extracción de celda
    beq     error_extraccion                
    
    adr     x0, buffer_columna              
    bl      parse_int                       // Convierte el texto de la celda a entero de 64 bits
    
    str     x0, [x22, x21, lsl #3]          // Almacena dato en memoria (dirección base + i * 8)
    
    add     x21, x21, #1                    // Incrementa iterador de fila
    b       cargar_datos_loop               

    # -----------------------------------------------------------------
    # PROCESAMIENTO ESTADÍSTICO MATEMÁTICO
    # -----------------------------------------------------------------
    /*
    - x24 : Almacena el resultado neto de la Media Aritmética (MEAN).
     - x25 : Almacena el resultado neto de la Desviación Estándar (STD_DEV).
     - x26 : Almacena el conteo acumulado de registros atípicos (ANOMALIES)
    */

calcular_media:
    // 1. Obtención de Media Aritmética
    mov     x21, #0                         // Inicializa iterador del arreglo
    mov     x23, #0                         // Inicializa acumulador de suma general
    adr     x22, array_datos                

sum_media_loop:
    cmp     x21, #30                        // Evalúa fin del arreglo de 30 muestras
    bge     div_media                       
    ldr     x9, [x22, x21, lsl #3]          // Carga elemento actual de 64 bits
    add     x23, x23, x9                    // Acumula valor en x23
    add     x21, x21, #1                    // Avanza al siguiente elemento
    b       sum_media_loop                  

div_media:
    mov     x9, #30                         // Denominador N = 30
    sdiv    x24, x23, x9                    // x24 = MEDIA (División entera con signo)

calcular_desviacion:
    // 2. Obtención de Desviación Estándar
    mov     x21, #0                         
    mov     x23, #0                         // Inicializa acumulador de diferencias al cuadrado
    adr     x22, array_datos                

sum_varianza_loop:
    cmp     x21, #30                        
    bge     obtener_raiz_directa            
    ldr     x9, [x22, x21, lsl #3]          
    sub     x9, x9, x24                     // Calcula diferencia: (X - MEDIA)
    mul     x10, x9, x9                     // Calcula cuadrado: (X - MEDIA)^2
    add     x23, x23, x10                   // Acumula diferencias al cuadrado
    add     x21, x21, #1                    
    b       sum_varianza_loop               

obtener_raiz_directa:
    mov     x9, #30                         
    sdiv    x0, x23, x9                     // x0 = Varianza Promedio (Entero)

    # --- CÁLCULO DIRECTO DE LA RAÍZ CUADRADA 
    scvtf   d0, x0                          // Convierte el entero de la varianza (x0) a flotante (d0)
    fsqrt   d0, d0                          // Calcula la raíz cuadrada por hardware en 1 solo paso
    fcvtzs  x25, d0                         // Convierte de vuelta a entero puro en x25 (Truncado a cero)

    # --- CONTROL CONTRA DIVISIÓN POR CERO ---
    cmp     x25, #0                         // Verifica si el entero final es 0
    bne     evaluar_anomalias               
    mov     x25, #1                         // Fuerza STD_DEV = 1 si el resultado es nulo

evaluar_anomalias:
    // 3. Análisis de Desviaciones Atípicas (Z-Score)
    mov     x21, #0                         
    mov     x26, #0                         // Inicializa contador de anomalías (Anomalies = 0)
    adr     x22, array_datos                

z_score_loop:
    cmp     x21, #30                        
    bge     abrir_descriptor_salida         
    ldr     x9, [x22, x21, lsl #3]          
    sub     x9, x9, x24                     // x9 = (X - MEDIA)
    
    sdiv    x10, x9, x25                    // x10 = Z-Score (Diferencial / Desviación Estándar)

    // Obtención de Valor Absoluto de Z (|Z|)
    cmp     x10, #0                         
    bge     verificar_regla                 
    neg     x10, x10                        // Invierte signo si el valor es negativo

verificar_regla:
    cmp     x10, #2                         // Aplica regla de control estadístico: |Z| >= 2
    blt     siguiente_z                     
    add     x26, x26, #1                    // Incrementa contador si es una anomalía crítica

siguiente_z:
    add     x21, x21, #1                    // Incrementa índice de evaluación
    b       z_score_loop                    

    # -----------------------------------------------------------------
    # CONTROL DE PERSISTENCIA (APERTURA DE REPORTE)
    # -----------------------------------------------------------------
abrir_descriptor_salida:
    adr     x0, output_filename             
    bl      open_output                     
    cmp     x0, #0                          
    blt     exit_error                      
    mov     x27, x0                         // x27 = File Descriptor del archivo de texto

    # -----------------------------------------------------------------
    # ESCRITURA DUAL SIMULTÁNEA (CONSOLA Y ARCHIVO)
    # -----------------------------------------------------------------

    // --- FILA 1: MODULE=ANOMALY_DETECTION ---
    mov     x0, #1                          
    adr     x1, lbl_MODULE                  
    mov     x2, #len_MODULE                 
    bl      write_result                    
    mov     x0, x27                         
    adr     x1, lbl_MODULE                  
    mov     x2, #len_MODULE                 
    bl      write_result                    

    // --- FILA 2: TOTAL_VALUES=30 ---
    mov     x0, #1                          
    adr     x1, lbl_TOTAL_VALUES            
    mov     x2, #len_TOTAL_VALUES           
    bl      write_result                    
    mov     x0, x27                         
    adr     x1, lbl_TOTAL_VALUES            
    mov     x2, #len_TOTAL_VALUES           
    bl      write_result                    

    // --- FILA 3: MEAN ---
    mov     x0, #1                          
    adr     x1, lbl_MEAN                    
    mov     x2, #len_MEAN                   
    bl      write_result                    
    mov     x0, x27                         
    adr     x1, lbl_MEAN                    
    mov     x2, #len_MEAN                   
    bl      write_result                    
    
    mov     x0, x24                         // Pasa valor numérico de la media
    adr     x1, buffer_columna              
    bl      int_to_ascii                    
    mov     x2, x0                          
    mov     x0, #1                          
    adr     x1, buffer_columna              
    bl      write_result                    
    mov     x0, x27                         
    adr     x1, buffer_columna              
    bl      write_result                    
    bl      salto                           

    // --- FILA 4: STD_DEV ---
    mov     x0, #1                          
    adr     x1, lbl_STD_DEV                 
    mov     x2, #len_STD_DEV                
    bl      write_result                    
    mov     x0, x27                         
    adr     x1, lbl_STD_DEV                 
    mov     x2, #len_STD_DEV                
    bl      write_result                    
    
    mov     x0, x25                         // Pasa valor numérico de desviación estándar
    adr     x1, buffer_columna              
    bl      int_to_ascii                    
    mov     x2, x0                          
    mov     x0, #1                          
    adr     x1, buffer_columna              
    bl      write_result                    
    mov     x0, x27                         
    adr     x1, buffer_columna              
    bl      write_result                    
    bl      salto                           

    // --- FILA 5: ANOMALIES ---
    mov     x0, #1                          
    adr     x1, lbl_ANOMALIES               
    mov     x2, #len_ANOMALIES              
    bl      write_result                    
    mov     x0, x27                         
    adr     x1, lbl_ANOMALIES               
    mov     x2, #len_ANOMALIES              
    bl      write_result                    
    
    mov     x0, x26                         // Pasa el conteo de anomalías totales
    adr     x1, buffer_columna              
    bl      int_to_ascii                    
    mov     x2, x0                          
    mov     x0, #1                          
    adr     x1, buffer_columna              
    bl      write_result                    
    mov     x0, x27                         
    adr     x1, buffer_columna              
    bl      write_result                    
    bl      salto                           

    // --- FILA 6: SYSTEM_RISK ---
    mov     x0, #1                          
    adr     x1, lbl_SYSTEM_RISK             
    mov     x2, #len_SYSTEM_RISK            
    bl      write_result                    
    mov     x0, x27                         
    adr     x1, lbl_SYSTEM_RISK             
    mov     x2, #len_SYSTEM_RISK            
    bl      write_result                    

    // Evaluación condicional del nivel de riesgo del sistema
    cmp     x26, #0                         
    beq     imprimir_normal                 
    cmp     x26, #3                         
    ble     imprimir_medium                 
    b       imprimir_high                   

imprimir_normal:
    adr     x1, risk_normal                 
    mov     x2, #len_risk_normal            
    b       escribir_riesgo                 

imprimir_medium:
    adr     x1, risk_medium                 
    mov     x2, #len_risk_medium            
    b       escribir_riesgo                 

imprimir_high:
    adr     x1, risk_high                   
    mov     x2, #len_risk_high              

escribir_riesgo:
    mov     x19, x1                         // Resguarda dirección del mensaje seleccionado
    mov     x18, x2                         // Resguarda longitud del mensaje seleccionado
    
    mov     x0, #1                          
    bl      write_result                    

    mov     x0, x27                         
    mov     x1, x19                         
    mov     x2, x18                         
    bl      write_result                    
    b       finalizar_proceso               

# -----------------------------------------------------------------
# FINALIZACIÓN Y CIERRE DE RECURSOS
# -----------------------------------------------------------------
finalizar_proceso:
    mov     x0, x27                         // Pasa descriptor del archivo abierto
    bl      close_fd                        

    mov     x0, #1                          
    adr     x1, msg_fin                     
    mov     x2, #len_fin                    
    bl      write_result                    
    
    mov     x0, #0                          
    b       finalizar                       

# -----------------------------------------------------------------
# MANEJO AUXILIAR DE TERMINAL
# -----------------------------------------------------------------
salto:
    mov     x19, x30                        // Resguarda dirección de retorno (LR)
    
    mov     x0, #1                          
    adr     x1, txt_newline                 
    mov     x2, #1                          
    bl      write_result                    

    mov     x0, x27                         
    adr     x1, txt_newline                 
    mov     x2, #1                          
    
    mov     x30, x19                        // Restaura dirección de retorno
    b       write_result                    

# -----------------------------------------------------------------
# MANEJADORES DE EXCEPCIONES Y SYSCALLS NATIVOS DE LINUX
# -----------------------------------------------------------------
no_argumento:
    mov     x0, #1                          
    adr     x1, msg_no_arg                  
    mov     x2, #msg_no_arg_len             
    mov     x8, #64                         // Syscall ID 64 = sys_write
    svc     #0                              
    b       exit_error                      

exit_error:
    mov     x0, #1                          // Código de estado de salida con error (1)
    mov     x8, #93                         // Syscall ID 93 = sys_exit
    svc     #0                              

error_extraccion:
    mov     x0, #1                          
    mov     x8, #93                         
    svc     #0                              

finalizar:
    mov     x0, #0                          // Código de estado de salida exitosa (0)
    mov     x8, #93                         
    svc     #0