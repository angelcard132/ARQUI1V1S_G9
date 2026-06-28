.section .data

out_filename:
    .asciz "resultado_derivada.txt"

str_calc:
    .ascii "CALC=LOCAL_DERIVATIVE COLUMN="
len_calc = . - str_calc

str_ws:
    .ascii " WINDOW_START="
len_ws = . - str_ws

str_we:
    .ascii " WINDOW_END="
len_we = . - str_we

str_count:
    .ascii " COUNT="
len_count = . - str_count

str_wsize:
    .ascii " WINDOW_SIZE=5"
len_wsize = . - str_wsize

str_max:
    .ascii " MAX_LOCAL_SLOPE_X100="
len_max = . - str_max

str_ok:
    .ascii " STATUS=OK\n"
len_ok = . - str_ok

err_args:
    .ascii "STATUS=ERROR ERROR=INVALID_ARGS DETAIL=USE_FILE_START_END_COLUMN\n"
len_err_args = . - err_args

err_data:
    .ascii "STATUS=ERROR ERROR=INSUFFICIENT_DATA DETAIL=LOCAL_DERIVATIVE_REQUIRES_AT_LEAST_5_VALUES\n"
len_err_data = . - err_data

err_range:
    .ascii "STATUS=ERROR ERROR=INVALID_RANGE DETAIL=WINDOW_OUT_OF_RANGE\n"
len_err_range = . - err_range

err_col:
    .ascii "STATUS=ERROR ERROR=INVALID_COLUMN DETAIL=COLUMN_NOT_SUPPORTED\n"
len_err_col = . - err_col

.section .bss

values:
    .space 8192

ascii_buf:
    .space 32

.section .text
.global _start

_start:
    ldr x0, [sp]
    cmp x0, #5
    blt error_args

    ldr x20, [sp, #16]
    ldr x21, [sp, #24]
    ldr x22, [sp, #32]
    ldr x23, [sp, #40]

    mov x0, x20
    bl read_csv
    cmp x0, #0
    blt error_range

    mov x0, x21
    bl parse_int
    mov x24, x0

    mov x0, x22
    bl parse_int
    mov x25, x0

    mov x0, x23
    bl column_name_to_index
    cmp x0, #0
    blt error_col
    mov x26, x0

    mov x0, x24
    mov x1, x25
    mov x2, x26
    adr x3, values
    bl read_range_column
    cmp x0, #5
    blt error_data

    mov x27, x0
    adr x28, values

    mov x19, #0
    mov x18, #0

window_loop:
    sub x9, x27, #5
    cmp x19, x9
    bgt write_output

    mov x10, #0
    mov x11, #0
    mov x12, #0

inner_loop:
    cmp x12, #5
    bge calc_slope

    add x13, x19, x12
    mov x14, #8
    mul x15, x13, x14
    add x16, x28, x15
    ldr x17, [x16]

    add x10, x10, x17

    mul x15, x12, x17
    add x11, x11, x15

    add x12, x12, #1
    b inner_loop

calc_slope:
    mov x9, #5
    mul x13, x9, x11

    mov x9, #10
    mul x14, x9, x10

    sub x15, x13, x14

    mov x9, #100
    mul x15, x15, x9

    mov x9, #50
    sdiv x16, x15, x9

    cmp x16, #0
    bge abs_ready
    sub x16, xzr, x16

abs_ready:
    cmp x16, x18
    ble next_window
    mov x18, x16

next_window:
    add x19, x19, #1
    b window_loop

write_output:
    adr x0, out_filename
    bl open_output
    cmp x0, #0
    blt error_range
    mov x19, x0

    mov x0, x19
    adr x1, str_calc
    mov x2, #len_calc
    bl write_result

    mov x0, x23
    bl strlen
    mov x2, x0
    mov x0, x19
    mov x1, x23
    bl write_result

    mov x0, x19
    adr x1, str_ws
    mov x2, #len_ws
    bl write_result
    mov x0, x24
    bl write_number

    mov x0, x19
    adr x1, str_we
    mov x2, #len_we
    bl write_result
    mov x0, x25
    bl write_number

    mov x0, x19
    adr x1, str_count
    mov x2, #len_count
    bl write_result
    mov x0, x27
    bl write_number

    mov x0, x19
    adr x1, str_wsize
    mov x2, #len_wsize
    bl write_result

    mov x0, x19
    adr x1, str_max
    mov x2, #len_max
    bl write_result
    mov x0, x18
    bl write_number

    mov x0, x19
    adr x1, str_ok
    mov x2, #len_ok
    bl write_result

    mov x0, x19
    bl close_fd

    mov x0, #0
    mov x8, #93
    svc #0

write_number:
    sub sp, sp, #16
    str x30, [sp]

    adr x1, ascii_buf
    bl int_to_ascii

    mov x2, x0
    mov x0, x19
    adr x1, ascii_buf
    bl write_result

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

error_col:
    adr x1, err_col
    mov x2, #len_err_col
    b write_error

error_data:
    adr x1, err_data
    mov x2, #len_err_data
    b write_error

error_range:
    adr x1, err_range
    mov x2, #len_err_range

write_error:
    mov x0, #1
    bl write_result

    mov x0, #1
    mov x8, #93
    svc #0