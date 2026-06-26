.section .data
out_filename: .asciz "resultado_varianza.txt"

str_module: .asciz "MODULE=VARIANCE\n"
len_module = . - str_module - 1

str_total: .asciz "TOTAL_VALUES="
len_total = . - str_total - 1

str_mean: .asciz "MEAN="
len_mean = . - str_mean - 1

str_var: .asciz "VARIANCE="
len_var = . - str_var - 1

str_std: .asciz "STD_DEV="
len_std = . - str_std - 1

.section .bss
col_buf: .space 32
ascii_buf: .space 32
values: .space 240

.section .text
.global _start

.equ N, 30
.equ COLUMNA, 1

_start:
    bl read_csv
    cmp x0, #0
    blt error_exit

    adr x27, values
    mov x19, #0
    mov x28, #0

read_values:
    cmp x19, #N
    bge calc_mean

    mov x0, x19
    mov x1, #COLUMNA
    adr x2, col_buf
    mov x3, #32
    bl get_column
    cmp x0, #0
    beq error_exit

    adr x0, col_buf
    bl parse_int

    str x0, [x27, x19, lsl #3]
    add x28, x28, x0
    add x19, x19, #1
    b read_values

calc_mean:
    mov x9, #N
    sdiv x22, x28, x9

    mov x19, #0
    mov x23, #0

calc_variance_sum:
    cmp x19, #N
    bge calc_variance

    ldr x10, [x27, x19, lsl #3]
    sub x11, x10, x22
    mul x12, x11, x11
    add x23, x23, x12

    add x19, x19, #1
    b calc_variance_sum

calc_variance:
    mov x9, #N
    sdiv x24, x23, x9

    mov x25, #0

sqrt_loop:
    mul x10, x25, x25
    cmp x10, x24
    bgt sqrt_done
    add x25, x25, #1
    b sqrt_loop

sqrt_done:
    sub x25, x25, #1

    adr x0, out_filename
    bl open_output
    cmp x0, #0
    blt error_exit
    mov x26, x0

    mov x0, x26
    adr x1, str_module
    mov x2, #len_module
    bl write_result

    adr x1, str_total
    mov x2, #len_total
    mov x3, #N
    bl write_line

    adr x1, str_mean
    mov x2, #len_mean
    mov x3, x22
    bl write_line

    adr x1, str_var
    mov x2, #len_var
    mov x3, x24
    bl write_line

    adr x1, str_std
    mov x2, #len_std
    mov x3, x25
    bl write_line

    mov x0, x26
    bl close_fd

    mov x0, #0
    mov x8, #93
    svc #0

write_line:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    str x3, [sp, #16]

    mov x0, x26
    bl write_result

    ldr x0, [sp, #16]
    adr x1, ascii_buf
    bl int_to_ascii

    mov x2, x0
    mov x0, x26
    adr x1, ascii_buf
    bl write_result

    mov x0, x26
    bl newline

    ldp x29, x30, [sp], #32
    ret

error_exit:
    mov x0, #1
    mov x8, #93
    svc #0