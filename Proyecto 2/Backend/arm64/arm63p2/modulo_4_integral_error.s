// modulo_4_integral_error.s
// Integral del error por regla del trapecio
// ASTRID VANESA KIM ORTIZ
.section .data

out_filename: .asciz "resultado_integral.txt"

str_calc: .ascii "CALC=ERROR_INTEGRAL\nCOLUMN="
len_calc = . - str_calc

str_ws: .ascii "\nWINDOW_START="
len_ws = . - str_ws

str_we: .ascii "\nWINDOW_END="
len_we = . - str_we

str_count: .ascii "\nCOUNT="
len_count = . - str_count

str_ideal: .ascii "\nIDEAL="
len_ideal = . - str_ideal

str_integral: .ascii "\nERROR_INTEGRAL="
len_integral = . - str_integral

str_ok: .ascii "\nSTATUS=OK\n"
len_ok = . - str_ok

err_args: .ascii "STATUS=ERROR\nERROR=INVALID_ARGS\nDETAIL=USE_FILE_START_END_COLUMN_IDEAL\n"
len_err_args = . - err_args

err_file: .ascii "STATUS=ERROR\nERROR=FILE_READ_FAILED\nDETAIL=COULD_NOT_READ_CSV\n"
len_err_file = . - err_file

err_col: .ascii "STATUS=ERROR\nERROR=INVALID_COLUMN\nDETAIL=COLUMN_NOT_SUPPORTED\n"
len_err_col = . - err_col

err_range: .ascii "STATUS=ERROR\nERROR=INVALID_RANGE\nDETAIL=WINDOW_OUT_OF_RANGE\n"
len_err_range = . - err_range

err_data: .ascii "STATUS=ERROR\nERROR=INSUFFICIENT_DATA\nDETAIL=ERROR_INTEGRAL_REQUIRES_AT_LEAST_2_VALUES\n"
len_err_data = . - err_data

.section .bss

values: .space 8192
ascii_buf: .space 32
fd_out: .quad 0
arg_file: .quad 0
arg_start: .quad 0
arg_end: .quad 0
arg_col: .quad 0
ideal_val: .quad 0
count_val: .quad 0
integral_val: .quad 0

.section .text
.global _start

_start:
    ldr x0, [sp]
    cmp x0, #6
    blt error_args

    ldr x9, [sp, #16]
    adr x10, arg_file
    str x9, [x10]

    ldr x9, [sp, #24]
    mov x0, x9
    bl parse_int
    adr x10, arg_start
    str x0, [x10]

    ldr x9, [sp, #32]
    mov x0, x9
    bl parse_int
    adr x10, arg_end
    str x0, [x10]

    ldr x9, [sp, #40]
    adr x10, arg_col
    str x9, [x10]

    ldr x9, [sp, #48]
    mov x0, x9
    bl parse_int
    adr x10, ideal_val
    str x0, [x10]

    adr x9, arg_file
    ldr x0, [x9]
    bl read_csv
    cmp x0, #0
    blt error_file

    adr x9, arg_col
    ldr x0, [x9]
    bl column_name_to_index
    cmp x0, #0
    blt error_col
    mov x21, x0

    adr x9, arg_start
    ldr x0, [x9]
    adr x9, arg_end
    ldr x1, [x9]
    mov x2, x21
    adr x3, values
    bl read_range_column
    cmp x0, #0
    blt error_range
    cmp x0, #2
    blt error_data

    adr x9, count_val
    str x0, [x9]
    mov x22, x0

    adr x23, values
    mov x19, #0
    mov x24, #0

integral_loop:
    sub x10, x22, #1
    cmp x19, x10
    bge save_integral

    mov x11, #8
    mul x12, x19, x11
    add x13, x23, x12
    ldr x14, [x13]

    add x15, x19, #1
    mul x12, x15, x11
    add x13, x23, x12
    ldr x15, [x13]

    adr x9, ideal_val
    ldr x16, [x9]

    sub x0, x14, x16
    bl abs_int
    mov x17, x0

    sub x0, x15, x16
    bl abs_int
    mov x18, x0

    add x17, x17, x18
    mov x10, #2
    sdiv x17, x17, x10
    add x24, x24, x17

    add x19, x19, #1
    b integral_loop

save_integral:
    adr x9, integral_val
    str x24, [x9]

write_output:
    adr x0, out_filename
    bl open_output
    cmp x0, #0
    blt error_file
    adr x9, fd_out
    str x0, [x9]

    adr x1, str_calc
    mov x2, #len_calc
    bl write_fd

    adr x9, arg_col
    ldr x0, [x9]
    bl strlen
    mov x2, x0
    adr x9, arg_col
    ldr x1, [x9]
    bl write_fd

    adr x1, str_ws
    mov x2, #len_ws
    bl write_fd
    adr x9, arg_start
    ldr x0, [x9]
    bl write_num

    adr x1, str_we
    mov x2, #len_we
    bl write_fd
    adr x9, arg_end
    ldr x0, [x9]
    bl write_num

    adr x1, str_count
    mov x2, #len_count
    bl write_fd
    adr x9, count_val
    ldr x0, [x9]
    bl write_num

    adr x1, str_ideal
    mov x2, #len_ideal
    bl write_fd
    adr x9, ideal_val
    ldr x0, [x9]
    bl write_num

    adr x1, str_integral
    mov x2, #len_integral
    bl write_fd
    adr x9, integral_val
    ldr x0, [x9]
    bl write_num

    adr x1, str_ok
    mov x2, #len_ok
    bl write_fd

    adr x9, fd_out
    ldr x0, [x9]
    bl close_fd

    mov x0, #0
    mov x8, #93
    svc #0

write_fd:
    sub sp, sp, #16
    str x30, [sp]

    adr x9, fd_out
    ldr x0, [x9]
    bl write_result

    ldr x30, [sp]
    add sp, sp, #16
    ret

write_num:
    sub sp, sp, #16
    str x30, [sp]

    adr x1, ascii_buf
    bl int_to_ascii

    mov x2, x0
    adr x1, ascii_buf
    bl write_fd

    ldr x30, [sp]
    add sp, sp, #16
    ret

strlen:
    mov x1, x0
    mov x0, #0

strlen_loop:
    ldrb w2, [x1, x0]
    cbz w2, strlen_done
    add x0, x0, #1
    b strlen_loop

strlen_done:
    ret

error_args:
    adr x1, err_args
    mov x2, #len_err_args
    b write_error

error_file:
    adr x1, err_file
    mov x2, #len_err_file
    b write_error

error_col:
    adr x1, err_col
    mov x2, #len_err_col
    b write_error

error_range:
    adr x1, err_range
    mov x2, #len_err_range
    b write_error

error_data:
    adr x1, err_data
    mov x2, #len_err_data

write_error:
    mov x0, #1
    bl write_result
    mov x0, #1
    mov x8, #93
    svc #0
