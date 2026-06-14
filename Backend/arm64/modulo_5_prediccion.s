//  Tendencia Acumulada Avanzada
// Modulo 5: Hecho por Angel Jose Cardenas Pocon  | 202304063
//    Lee la columna TEMP (col 1) de los 30 registros de lecturas.csv
//    y calcula:
//      1. Cantidad de incrementos  (X_i > X_(i-1))
//      2. Cantidad de decrementos  (X_i < X_(i-1))
//      3. Racha máxima de crecimiento continuo (MAX_UP_STREAK)
//      4. Racha máxima de decremento continuo  (MAX_DOWN_STREAK)
//      5. Diferencia acumulada: DIF_ACUM = Σ(X_i - X_(i-1))  i=1..29
//      6. Tendencia final: UP / DOWN / STABLE
//  Formulas
//      DIF_i   = X_i - X_(i-1)
//      DIF_ACUM = Σ DIF_i
//      DIF_ACUM > 0  → UP
//      DIF_ACUM < 0  → DOWN
//      DIF_ACUM = 0  → STABLE
//
//
//  Compilar:
//      as -o utils.o utils.s
//      as -o modulo_5_tendencia.o modulo_5_tendencia.s
//      ld -o modulo_5_tendencia modulo_5_tendencia.o utils.o
//
//  Ejecutar:
//      ./modulo_5_tendencia
//
//  Depurar con GDB:
//      gdb ./modulo_5_tendencia
//      (gdb) break _start
//      (gdb) run
//      (gdb) info registers
//      (gdb) next
//      (gdb) x/30dg &data_array    <- ver array de datos

// Importar funciones de utils.s 
.extern read_csv
.extern get_column
.extern parse_int
.extern int_to_ascii
.extern open_output
.extern write_result
.extern close_fd
.extern newline

.section .data

// Nombre del archivo de salida
output_filename:
    .asciz "resultado_tendencia.txt"

// Strings de salida fijos
str_module:
    .ascii "MODULE=ADVANCED_TREND"
    .byte 0x0A
str_module_len = . - str_module

str_total:
    .ascii "TOTAL_VALUES=30"
    .byte 0x0A
str_total_len = . - str_total

str_inc_label:
    .asciz "INCREMENTS="
str_dec_label:
    .asciz "DECREMENTS="
str_maxup_label:
    .asciz "MAX_UP_STREAK="
str_maxdn_label:
    .asciz "MAX_DOWN_STREAK="
str_accum_label:
    .asciz "ACCUM_DIFF="
str_trend_label:
    .asciz "TREND="

str_up:
    .ascii "UP"
    .byte 0x0A
str_up_len = . - str_up

str_down:
    .ascii "DOWN"
    .byte 0x0A
str_down_len = . - str_down

str_stable:
    .ascii "STABLE"
    .byte 0x0A
str_stable_len = . - str_stable

// Buffer reutilizable para números
num_buf:
    .space 24

// Buffer para get_column
col_buf:
    .space 32

// Array donde guardamos los 30 valores leídos del CSV

.align 8
.global data_array              
data_array:
    .space 240                  // 30 * 8 bytes

.section .text
.global _start

//  _start punto de entrada del programa
_start:
    //  1. Leer el CSV completo 
    bl read_csv
    cmp x0, #0
    ble exit_error              // si <=0 bytes, error

    // 2. Extraer la columna TEMP (col 1) para las 30 filas 
    mov x19, #0                 // x19 = índice de fila (0..29)
    adr x20, data_array         // x20 = puntero al array

load_loop:
    cmp x19, #30
    bge load_done

    // get_column(fila=x19, col=1, buf=col_buf, maxlen=32)
    mov x0, x19
    mov x1, #1                  // columna TEMP
    adr x2, col_buf
    mov x3, #32
    bl get_column               // x0 = longitud

    // parse_int(col_buf) → x0
    adr x0, col_buf
    bl parse_int                // x0 = valor entero

    // Guardar en data_array[x19]
    str x0, [x20, x19, lsl #3]

    add x19, x19, #1
    b load_loop

load_done:

    // 3. Calcular estadísticas de tendencia
    //
    //  Registros usados (todos callee-saved):
    //    x19 = índice de iteración (i = 1..29)
    //    x20 = &data_array
    //    x21 = contador incrementos
    //    x22 = contador decrementos
    //    x23 = diferencia acumulada (puede ser negativa)
    //    x24 = racha UP actual
    //    x25 = racha DOWN actual
    //    x26 = racha UP máxima
    //    x27 = racha DOWN máxima
    //    x28 = valor anterior  X_(i-1)

    mov x19, #1                 // empezamos en i=1
    mov x21, #0                 // incrementos
    mov x22, #0                 // decrementos
    mov x23, #0                 // DIF_ACUM
    mov x24, #0                 // racha_up_actual
    mov x25, #0                 // racha_down_actual
    mov x26, #0                 // max_up_streak
    mov x27, #0                 // max_down_streak

    // X_(0) = data_array[0]
    adr x20, data_array
    ldr x28, [x20]              // x28 = X_0

calc_loop:
    cmp x19, #30
    bge calc_done

    // X_i = data_array[x19]
    ldr x9, [x20, x19, lsl #3]

    // DIF_i = X_i - X_(i-1)
    sub x10, x9, x28            // x10 = DIF_i

    // Acumular DIF_ACUM
    add x23, x23, x10

    // ¿Incremento, decremento o igual?
    cmp x10, #0
    bgt trend_increment
    blt trend_decrement
    // si es igual resetear ambas rachas
    mov x24, #0
    mov x25, #0
    b trend_next

trend_increment:
    add x21, x21, #1            // incrementos++
    add x24, x24, #1            // racha_up++
    mov x25, #0                 // resetear racha_down
    // actualizar max_up si corresponde
    cmp x24, x26
    ble trend_next
    mov x26, x24
    b trend_next

trend_decrement:
    add x22, x22, #1            // decrementos++
    add x25, x25, #1            // racha_down++
    mov x24, #0                 // resetear racha_up
    // actualizar max_down si corresponde
    cmp x25, x27
    ble trend_next
    mov x27, x25

trend_next:
    mov x28, x9                 // X_(i-1) = X_i
    add x19, x19, #1
    b calc_loop

calc_done:
    // Guardar resultados en callee-saved para después 
    // x21 = INCREMENTS
    // x22 = DECREMENTS
    // x23 = ACCUM_DIFF
    // x26 = MAX_UP_STREAK
    // x27 = MAX_DOWN_STREAK

    // 4. Abrir archivo de salida
    adr x0, output_filename
    bl open_output
    cmp x0, #0
    blt exit_error
    mov x19, x0                 // x19 = fd salida 

    // 5. Escribir líneas de resultado 

    // MODULE=ADVANCED_TREND\n
    mov x0, x19
    adr x1, str_module
    mov x2, #str_module_len
    bl write_result

    // TOTAL_VALUES=30\n
    mov x0, x19
    adr x1, str_total
    mov x2, #str_total_len
    bl write_result

    // INCREMENTS=<x21>\n
    adr x0, str_inc_label
    bl _strlen
    mov x2, x0
    mov x0, x19
    adr x1, str_inc_label
    bl write_result

    mov x0, x21                 // valor INCREMENTS
    adr x1, num_buf
    bl int_to_ascii
    mov x2, x0
    mov x0, x19
    adr x1, num_buf
    bl write_result
    mov x0, x19
    bl newline

    // DECREMENTS=<x22>\n
    adr x0, str_dec_label
    bl _strlen
    mov x2, x0
    mov x0, x19
    adr x1, str_dec_label
    bl write_result

    mov x0, x22
    adr x1, num_buf
    bl int_to_ascii
    mov x2, x0
    mov x0, x19
    adr x1, num_buf
    bl write_result
    mov x0, x19
    bl newline

    // MAX_UP_STREAK=<x26>\n
    adr x0, str_maxup_label
    bl _strlen
    mov x2, x0
    mov x0, x19
    adr x1, str_maxup_label
    bl write_result

    mov x0, x26
    adr x1, num_buf
    bl int_to_ascii
    mov x2, x0
    mov x0, x19
    adr x1, num_buf
    bl write_result
    mov x0, x19
    bl newline

    // MAX_DOWN_STREAK=<x27>\n
    adr x0, str_maxdn_label
    bl _strlen
    mov x2, x0
    mov x0, x19
    adr x1, str_maxdn_label
    bl write_result

    mov x0, x27
    adr x1, num_buf
    bl int_to_ascii
    mov x2, x0
    mov x0, x19
    adr x1, num_buf
    bl write_result
    mov x0, x19
    bl newline

    // ACCUM_DIFF=<x23>\n  (puede ser negativo, int_to_ascii lo maneja)
    adr x0, str_accum_label
    bl _strlen
    mov x2, x0
    mov x0, x19
    adr x1, str_accum_label
    bl write_result

    mov x0, x23
    adr x1, num_buf
    bl int_to_ascii
    mov x2, x0
    mov x0, x19
    adr x1, num_buf
    bl write_result
    mov x0, x19
    bl newline

    // TREND=<UP|DOWN|STABLE>\n
    adr x0, str_trend_label
    bl _strlen
    mov x2, x0
    mov x0, x19
    adr x1, str_trend_label
    bl write_result

    cmp x23, #0
    bgt write_up
    blt write_down
    // STABLE
    mov x0, x19
    adr x1, str_stable
    mov x2, #str_stable_len
    bl write_result
    b write_trend_done

write_up:
    mov x0, x19
    adr x1, str_up
    mov x2, #str_up_len
    bl write_result
    b write_trend_done

write_down:
    mov x0, x19
    adr x1, str_down
    mov x2, #str_down_len
    bl write_result

write_trend_done:

    // 6. Cerrar archivo y salir 
    mov x0, x19
    bl close_fd

    // exit(0)
    mov x0, #0
    mov x8, #93                 // syscall exit
    svc #0

exit_error:
    mov x0, #1
    mov x8, #93
    svc #0

// _strlen  -  subrutina local (privada a este módulo)
//   Calcula la longitud de un string ASCII terminado en '\0'.
//   Parámetros: x0 = puntero al string
//   Retorna:    x0 = longitud (sin el '\0')
_strlen:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    mov x1, x0                  // x1 = ptr
    mov x0, #0                  // x0 = contador

_strlen_loop:
    ldrb w2, [x1, x0]
    cbz w2, _strlen_done
    add x0, x0, #1
    b _strlen_loop

_strlen_done:
    ldp x29, x30, [sp], #16
    ret