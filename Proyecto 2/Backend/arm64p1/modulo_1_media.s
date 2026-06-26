/* ====================================================================
 * MODULO 1 - DINA PEREZ
 * ==================================================================== */
.section .data
out_filename:   .asciz "resultado_media.txt"
str_module:     .asciz "MODULE=WEIGHTED_MEAN\n"
len_module      = . - str_module - 1
str_total:      .asciz "TOTAL_VALUES="
len_total       = . - str_total - 1
str_sumx:       .asciz "SUM_X="
len_sumx        = . - str_sumx - 1
str_weights:    .asciz "WEIGHT_SUM="
len_weights     = . - str_weights - 1
str_mean:       .asciz "WEIGHTED_MEAN="
len_mean        = . - str_mean - 1

.section .bss
col_buf:        .space 32
ascii_buf:      .space 32

.section .text
.global _start

.equ N, 30
.equ COLUMNA, 1

_start:
    bl read_csv
    cmp x0, #0
    blt error_exit

    mov x19, #0     // iterador
    mov x21, #0     // SUM_X 
    mov x22, #0     // suma ponderada
    mov x23, #0     // WEIGHT_SUM

read_values:
    cmp x19, #N
    bge calc_weighted_mean

    mov x0, x19
    mov x1, #COLUMNA
    adr x2, col_buf
    mov x3, #32
    bl get_column
    cmp x0, #0
    beq error_exit

    adr x0, col_buf
    bl parse_int

    add x21, x21, x0          // suma x
    add x10, x19, #1          // peso = fila + 1
    madd x22, x0, x10, x22    // suma ponderada
    add x23, x23, x10         // sumamos peso

    add x19, x19, #1
    b read_values

calc_weighted_mean:
    sdiv x24, x22, x23        // media ponderada

    adr x0, out_filename
    bl open_output
    cmp x0, #0
    blt error_exit
    mov x20, x0

    mov x0, x20
    adr x1, str_module
    mov x2, #len_module
    bl write_result

    // Etiquetas y valores
    adr x1, str_total
    mov x2, #len_total
    mov x3, #N
    bl write_number_line

    adr x1, str_sumx
    mov x2, #len_sumx
    mov x3, x21
    bl write_number_line

    adr x1, str_weights
    mov x2, #len_weights
    mov x3, x23
    bl write_number_line

    adr x1, str_mean
    mov x2, #len_mean
    mov x3, x24
    bl write_number_line

    mov x0, x20
    bl close_fd
    mov x0, #0
    mov x8, #93
    svc #0

write_number_line:
    stp x29, x30, [sp, #-16]! 
    mov x29, sp

    mov x0, x20
    bl write_result

    mov x0, x3
    adr x1, ascii_buf
    bl int_to_ascii

    mov x2, x0
    mov x0, x20
    adr x1, ascii_buf
    bl write_result

    mov x0, x20
    bl newline

    ldp x29, x30, [sp], #16
    ret

error_exit:
    mov x0, #1
    mov x8, #93
    svc #0