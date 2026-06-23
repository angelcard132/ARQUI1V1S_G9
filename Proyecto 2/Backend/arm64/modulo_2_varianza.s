//  Oliverio Abraham Caal Artola 202303864

.section .data

//Columna objetivo dentro de lecturas.csv
// CSV_HEADER = ID,TEMP,HUM_AIRE,HUM_SUELO_1,HUM_SUELO_2,LUZ,GAS,RIEGO_1,RIEGO_2
//              col0 col1  col2     col3        col4    col5 col6  col7    col8
.equ COL_OBJETIVO, 1        // 1 = TEMP. Cambiar a 2,3,4,5,6 segun se necesite.
.equ N_DATOS, 30            // cantidad de registros a procesar

// Nombre del archivo de salida
out_filename:
    .asciz "resultado_varianza.txt"

// Etiquetas del formato de salida
lbl_module:
    .asciz "MODULE=VARIANCE\n"
lbl_total:
    .asciz "TOTAL_VALUES="
lbl_mean:
    .asciz "MEAN="
lbl_variance:
    .asciz "VARIANCE="
lbl_stddev:
    .asciz "STD_DEV="

//Buffer temporal para convertir numeros a texto
.align 8
num_buffer:
    .space 32

//Buffer temporal para extraer cada valor de columna como texto
.align 8
col_buffer:
    .space 32

//arreglo donde guardamos los 30 valores leidos
.align 8
.global datos_x
datos_x:
    .space 240          // 30 * 8 bytes

// Variables globales para resultados de calcular_varianza

.align 8
result_mean:
    .quad 0
result_variance:
    .quad 0
result_stddev:
    .quad 0


.section .text
.global _start


_start:
    // 1-leer lecturas.csv completo en csv_buffer
    bl read_csv
    cmp x0, #0
    blt programa_error          // si read_csv retorno negativo, error

    // 2-leer las 30 filas y extraer la columna objetivo de cada una
    bl cargar_columna

    // 3-calcular media, varianza y desviacion estandar
    //   Los resultados quedan en result_mean, result_variance, result_stddev
    bl calcular_varianza

    // 4-Escribir resultado_varianza.txt
    bl escribir_resultado

    // 5-Salir limpiamente
    mov x0, #0
    mov x8, #93                  // syscall exit
    svc #0

programa_error:
    mov x0, #1
    mov x8, #93
    svc #0


// cargar_columna
//   Recorre las N_DATOS filas de csv_buffer y guarda en datos_x[]
//   el valor entero de la columna COL_OBJETIVO para cada fila.
//
//   Registros usados (callee-saved, se preservan correctamente):
//     x19 = contador de fila
//     x20 = puntero a datos_x[i]

cargar_columna:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    stp x19, x20, [sp, #16]

    mov x19, #0                  // x19 = fila actual
    adr x20, datos_x             // x20 = puntero al arreglo de salida

cc_loop:
    cmp x19, #N_DATOS
    bge cc_done                  // ya procesamos las N_DATOS filas

    mov x0, x19
    mov x1, #COL_OBJETIVO
    adr x2, col_buffer
    mov x3, #32
    bl get_column                 // x0 = longitud copiada

    adr x0, col_buffer
    bl parse_int                  // x0 = entero de esta fila

    // guardar en datos_x[x19]
    str x0, [x20]
    add x20, x20, #8              // siguiente slot de 8 bytes

    add x19, x19, #1
    b cc_loop

cc_done:
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #32
    ret


// calcular_varianza
//   Calcula MEDIA, VARIANZA y DESV_EST sobre datos_x[]
//   y los guarda en las variables globales result_mean,
//   result_variance y result_stddev.
//
//   Formulas:
//     MEDIA    = (sum X_i) / N
//     VARIANZA = (sum (X_i - MEDIA)^2) / N
//     DESV_EST = sqrt(VARIANZA)   (raiz entera)


calcular_varianza:
    stp x29, x30, [sp, #-64]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]

    // paso1: SUM_X = suma de los N_DATOS valores
    adr x23, datos_x             // x23 = puntero recorredor
    mov x22, #0                  // x22 = acumulador SUM_X
    mov x24, #0                  // x24 = contador

suma_loop:
    cmp x24, #N_DATOS
    bge suma_done
    ldr x9, [x23]
    add x22, x22, x9             // SUM_X += X_i
    add x23, x23, #8
    add x24, x24, #1
    b suma_loop

suma_done:
    // paso2: MEDIA = SUM_X / N
    mov x10, #N_DATOS
    sdiv x19, x22, x10           // x19 = MEDIA = SUM_X / N

    // paso3: SUM_SQ_DIFF = suma de (X_i - MEDIA)^2
    adr x23, datos_x
    mov x20, #0                  // x20 = acumulador SUM_SQ_DIFF
    mov x24, #0                  // x24 = contador

sumsq_loop:
    cmp x24, #N_DATOS
    bge sumsq_done

    ldr x9, [x23]                // x9 = X_i
    sub x9, x9, x19              // x9 = (X_i - MEDIA)
    mul x9, x9, x9               // x9 = (X_i - MEDIA)^2
    add x20, x20, x9             // SUM_SQ_DIFF += x9

    add x23, x23, #8
    add x24, x24, #1
    b sumsq_loop

sumsq_done:
    // paso4: VARIANZA = SUM_SQ_DIFF / N
    mov x10, #N_DATOS
    sdiv x20, x20, x10           // x20 = VARIANZA

    adr x9, result_mean
    str x19, [x9]                // guardar MEDIA ahora
    adr x9, result_variance
    str x20, [x9]                // guardar VARIANZA ahora

    // paso5: DESV_EST = sqrt(VARIANZA)  (raiz entera)
    // x19 y x20 
    bl raiz_entera               // x0 = floor

    // guardar STD_DEV
    adr x9, result_stddev
    str x0, [x9]


    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #64
    ret


// raiz_entera
//   Calcula la raiz cuadrada entera de un numero no negativo
//   usando el metodo de Newton-Raphson iterativo.
//
//   Parametros:
//     x0 = numero (N)
//   Retorna:
//     x0 = floor(sqrt(N))


raiz_entera:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    stp x19, x20, [sp, #16]

    mov x19, x0                  // x19 = N

    cmp x19, #1
    ble raiz_trivial

    // Estimacion inicial: x = N
    mov x20, x19                  

raiz_loop:
    // siguiente = (x + N/x) / 2
    sdiv x9, x19, x20             
    add x9, x9, x20               
    mov x10, #2
    sdiv x9, x9, x10              
  
    cmp x9, x20
    bge raiz_done

    mov x20, x9                   // x = siguiente
    b raiz_loop

raiz_done:
    mov x0, x20
    b raiz_exit

raiz_trivial:
    mov x0, x19

raiz_exit:
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #32
    ret


// escribir_resultado
//   Abre resultado_varianza.txt y escribe:
//     MODULE=VARIANCE
//     TOTAL_VALUES=30
//     MEAN=<valor>
//     VARIANCE=<valor>
//     STD_DEV=<valor>
//

escribir_resultado:
    stp x29, x30, [sp, #-48]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]

    // Cargar resultados desde variables globales
    adr x9, result_mean
    ldr x19, [x9]                // x19 = MEAN
    adr x9, result_variance
    ldr x20, [x9]                // x20 = VARIANCE
    adr x9, result_stddev
    ldr x21, [x9]                // x21 = STD_DEV

    // Abrir archivo de salida
    adr x0, out_filename
    bl open_output               // x0 = fd
    mov x22, x0                  // x22 = fd

    mov x0, x22
    adr x1, lbl_module
    mov x2, #16
    bl write_result

    mov x0, x22
    adr x1, lbl_total
    mov x2, #13
    bl write_result

    mov x0, #N_DATOS
    adr x1, num_buffer
    bl int_to_ascii
    mov x2, x0
    mov x0, x22
    adr x1, num_buffer
    bl write_result

    mov x0, x22
    bl newline

    mov x0, x22
    adr x1, lbl_mean
    mov x2, #5
    bl write_result

    mov x0, x19                  // MEAN
    adr x1, num_buffer
    bl int_to_ascii
    mov x2, x0
    mov x0, x22
    adr x1, num_buffer
    bl write_result

    mov x0, x22
    bl newline

    mov x0, x22
    adr x1, lbl_variance
    mov x2, #9
    bl write_result

    mov x0, x20                  // VARIANCE
    adr x1, num_buffer
    bl int_to_ascii
    mov x2, x0
    mov x0, x22
    adr x1, num_buffer
    bl write_result

    mov x0, x22
    bl newline

    mov x0, x22
    adr x1, lbl_stddev
    mov x2, #8
    bl write_result

    mov x0, x21                  // STD_DEV
    adr x1, num_buffer
    bl int_to_ascii
    mov x2, x0
    mov x0, x22
    adr x1, num_buffer
    bl write_result

    mov x0, x22
    bl newline

    // Cerrar archivo
    mov x0, x22
    bl close_fd

    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #48
    ret