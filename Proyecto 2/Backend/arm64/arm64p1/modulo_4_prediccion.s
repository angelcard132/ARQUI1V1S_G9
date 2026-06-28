Astrid Vanesa Kim Ortiz
202300685

.section .data

out_filename:
    .asciz "resultado_prediccion.txt"

str_module:
    .asciz "MODULE=PREDICTION\n"
len_module = . - str_module - 1

str_total:
    .asciz "TOTAL_VALUES="
len_total = . - str_total - 1

str_initial:
    .asciz "INITIAL_VALUE="
len_initial = . - str_initial - 1

str_final:
    .asciz "FINAL_VALUE="
len_final = . - str_final - 1

str_diff:
    .asciz "TOTAL_DIFF="
len_diff = . - str_diff - 1

str_avg:
    .asciz "AVG_CHANGE="
len_avg = . - str_avg - 1

str_next:
    .asciz "NEXT_VALUE="
len_next = . - str_next - 1

.section .bss

col_buf:
    .space 32

ascii_buf:
    .space 32

.section .text
.global _start

.equ COLUMNA, 1

_start:
    mov x0, #0
    bl read_csv
    cmp x0, #0
    blt error_exit

    bl count_rows
    cmp x0, #2
    blt error_exit
    mov x26, x0

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

    sub x0, x26, #1
    mov x1, #COLUMNA
    adr x2, col_buf
    mov x3, #32
    bl get_column
    cmp x0, #0
    beq error_exit

    adr x0, col_buf
    bl parse_int
    mov x22, x0

    sub x23, x22, x21

    sub x11, x26, #1
    sdiv x24, x23, x11

    add x25, x22, x24

    adr x0, out_filename
    bl open_output
    cmp x0, #0
    blt error_exit
    mov x19, x0

    mov x0, x19
    adr x1, str_module
    mov x2, #len_module
    bl write_result

    mov x0, x19
    adr x1, str_total
    mov x2, #len_total
    bl write_result
    mov x0, x26
    bl write_number

    mov x0, x19
    adr x1, str_initial
    mov x2, #len_initial
    bl write_result
    mov x0, x21
    bl write_number

    mov x0, x19
    adr x1, str_final
    mov x2, #len_final
    bl write_result
    mov x0, x22
    bl write_number

    mov x0, x19
    adr x1, str_diff
    mov x2, #len_diff
    bl write_result
    mov x0, x23
    bl write_number

    mov x0, x19
    adr x1, str_avg
    mov x2, #len_avg
    bl write_result
    mov x0, x24
    bl write_number

    mov x0, x19
    adr x1, str_next
    mov x2, #len_next
    bl write_result
    mov x0, x25
    bl write_number

    mov x0, x19
    bl close_fd

    mov x0, #0
    mov x8, #93
    svc #0

write_number:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    adr x1, ascii_buf
    bl int_to_ascii
    mov x20, x0

    mov x0, x19
    adr x1, ascii_buf
    mov x2, x20
    bl write_result

    mov x0, x19
    bl newline

    ldp x29, x30, [sp], #16
    ret

error_exit:
    mov x0, #1
    mov x8, #93
    svc #0