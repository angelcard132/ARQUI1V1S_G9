.section .data

out_filename:
    .asciz "resultado_tendencia.txt"

str_module:
    .asciz "MODULE=ADVANCED_TREND\n"
len_module = . - str_module - 1

str_total:
    .asciz "TOTAL_VALUES="
len_total = . - str_total - 1

str_inc:
    .asciz "INCREMENTS="
len_inc = . - str_inc - 1

str_dec:
    .asciz "DECREMENTS="
len_dec = . - str_dec - 1

str_max_up:
    .asciz "MAX_UP_STREAK="
len_max_up = . - str_max_up - 1

str_max_down:
    .asciz "MAX_DOWN_STREAK="
len_max_down = . - str_max_down - 1

str_accum:
    .asciz "ACCUM_DIFF="
len_accum = . - str_accum - 1

str_trend:
    .asciz "TREND="
len_trend = . - str_trend - 1

trend_up:
    .ascii "UP"
len_trend_up = . - trend_up

trend_down:
    .ascii "DOWN"
len_trend_down = . - trend_down

trend_stable:
    .ascii "STABLE"
len_trend_stable = . - trend_stable

.section .bss

col_buf:
    .space 32

ascii_buf:
    .space 32

.section .text
.global _start

.equ COLUMNA, 1

_start:
    bl read_csv
    cmp x0, #0
    blt error_exit

    bl count_rows
    cmp x0, #2
    blt error_exit
    mov x29, x0

    mov x0, #0
    mov x1, #COLUMNA
    adr x2, col_buf
    mov x3, #32
    bl get_column
    cmp x0, #0
    beq error_exit

    adr x0, col_buf
    bl parse_int

    mov x21, x0
    mov x19, #1
    mov x22, #0
    mov x23, #0
    mov x24, #0
    mov x25, #0
    mov x26, #0
    mov x27, #0
    mov x28, #0

trend_loop:
    cmp x19, x29
    bge write_output

    mov x0, x19
    mov x1, #COLUMNA
    adr x2, col_buf
    mov x3, #32
    bl get_column
    cmp x0, #0
    beq error_exit

    adr x0, col_buf
    bl parse_int

    sub x10, x0, x21
    add x28, x28, x10
    mov x21, x0

    cmp x10, #0
    bgt is_increment
    blt is_decrement

    mov x24, #0
    mov x25, #0
    b next_value

is_increment:
    add x22, x22, #1
    add x24, x24, #1
    mov x25, #0
    cmp x24, x26
    ble next_value
    mov x26, x24
    b next_value

is_decrement:
    add x23, x23, #1
    add x25, x25, #1
    mov x24, #0
    cmp x25, x27
    ble next_value
    mov x27, x25

next_value:
    add x19, x19, #1
    b trend_loop

write_output:
    adr x0, out_filename
    bl open_output
    cmp x0, #0
    blt error_exit
    mov x20, x0

    mov x0, x20
    adr x1, str_module
    mov x2, #len_module
    bl write_result

    adr x1, str_total
    mov x2, #len_total
    mov x3, x29
    bl write_number_line

    adr x1, str_inc
    mov x2, #len_inc
    mov x3, x22
    bl write_number_line

    adr x1, str_dec
    mov x2, #len_dec
    mov x3, x23
    bl write_number_line

    adr x1, str_max_up
    mov x2, #len_max_up
    mov x3, x26
    bl write_number_line

    adr x1, str_max_down
    mov x2, #len_max_down
    mov x3, x27
    bl write_number_line

    adr x1, str_accum
    mov x2, #len_accum
    mov x3, x28
    bl write_number_line

    mov x0, x20
    adr x1, str_trend
    mov x2, #len_trend
    bl write_result

    cmp x28, #0
    bgt write_up
    blt write_down

    mov x0, x20
    adr x1, trend_stable
    mov x2, #len_trend_stable
    bl write_result
    b finish

write_up:
    mov x0, x20
    adr x1, trend_up
    mov x2, #len_trend_up
    bl write_result
    b finish

write_down:
    mov x0, x20
    adr x1, trend_down
    mov x2, #len_trend_down
    bl write_result

finish:
    mov x0, x20
    bl newline

    mov x0, x20
    bl close_fd

    mov x0, #0
    mov x8, #93
    svc #0

write_number_line:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    str x3, [sp, #16]

    mov x0, x20
    bl write_result

    ldr x0, [sp, #16]
    adr x1, ascii_buf
    bl int_to_ascii

    mov x2, x0
    mov x0, x20
    adr x1, ascii_buf
    bl write_result

    mov x0, x20
    bl newline

    ldp x29, x30, [sp], #32
    ret

error_exit:
    mov x0, #1
    mov x8, #93
    svc #0