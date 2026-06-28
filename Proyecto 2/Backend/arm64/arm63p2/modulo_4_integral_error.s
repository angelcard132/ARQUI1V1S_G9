// modulo_4_integral_error.s
// Rutina 4: Integral del error por regla del trapecio
//ASTRID VANESA KIM ORTIZ

.section .data

str_calc:       .ascii "CALC=ERROR_INTEGRAL\nCOLUMN="
                len_calc = . - str_calc
str_wstart:     .ascii "\nWINDOW_START="
                len_wstart = . - str_wstart
str_wend:       .ascii "\nWINDOW_END="
                len_wend = . - str_wend
str_count:      .ascii "\nCOUNT="
                len_count = . - str_count
str_ideal:      .ascii "\nIDEAL="
                len_ideal = . - str_ideal
str_integral:   .ascii "\nERROR_INTEGRAL="
                len_integral = . - str_integral
str_ok:         .ascii "\nSTATUS=OK\n"
                len_ok = . - str_ok

err_args:       .ascii "STATUS=ERROR\nERROR=INVALID_ARGS\nDETAIL=SE_ESPERAN_4_ARGUMENTOS\n"
                len_err_args = . - err_args
err_range:      .ascii "STATUS=ERROR\nERROR=INVALID_RANGE\nDETAIL=LINEA_FUERA_DEL_ARCHIVO\n"
                len_err_range = . - err_range
err_data:       .ascii "STATUS=ERROR\nERROR=INSUFFICIENT_DATA\nDETAIL=SE_NECESITAN_AL_MENOS_2_VALORES\n"
                len_err_data = . - err_data

.section .bss

.balign 8
y_array:        .space 8192
ascii_buf:      .space 32

.section .text
.global _start

_start:
    ldr x0, [sp]
    cmp x0, #5
    blt do_err_args

    // linea inicial
    ldr x0, [sp, #16]
    bl parse_int
    mov x19, x0            // linea_ini

    // linea final
    ldr x0, [sp, #24]
    bl parse_int
    mov x20, x0            // linea_fin

    // columna (nombre -> indice)
    ldr x26, [sp, #32]     // guardar puntero al nombre
    mov x0, x26
    bl column_name_to_index
    cmp x0, #0
    blt do_err_args
    mov x21, x0            // columna

    // ideal
    ldr x0, [sp, #40]
    bl parse_int
    mov x22, x0            // ideal

    // validar rango basico
    cmp x19, #1
    blt do_err_range
    cmp x20, x19
    blt do_err_range

    // leer csv
    mov x0, #0
    bl read_csv

    // VOY a validar que las lineas existan
    bl count_rows
    cmp x20, x0
    bgt do_err_range


    mov x0, x19
    mov x1, x20
    mov x2, x21
    adr x3, y_array
    bl read_range_column
    cmp x0, #0
    blt do_err_range
    cmp x0, #2
    blt do_err_data

    mov x23, x0            // COUNT
    adr x24, y_array       // base del arreglo

    // calcular integral del trapecio
    mov x10, #0            // i
    mov x25, #0            // AREA_ERROR acumulada

