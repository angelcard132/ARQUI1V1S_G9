.section .data

out_filename:
    .asciz "resultado_regresion.txt"

str_calc:
    .ascii "CALC=LINEAR_REGRESSION COLUMN="
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

str_slope:
    .ascii " SLOPE_X100="
len_slope = . - str_slope

str_trend:
    .ascii " TREND="
len_trend = . - str_trend

str_status:
    .ascii " STATUS=OK\n"
len_status = . - str_status

trend_up:
    .ascii "ASCENDING"
len_trend_up = . - trend_up

trend_down:
    .ascii "DESCENDING"
len_trend_down = . - trend_down

trend_stable:
    .ascii "STABLE"
len_trend_stable = . - trend_stable

err_args:
    .ascii "STATUS=ERROR ERROR=INVALID_ARGS DETAIL=USE_FILE_START_END_COLUMN\n"
len_err_args = . - err_args

err_data:
    .ascii "STATUS=ERROR ERROR=INSUFFICIENT_DATA DETAIL=REGRESSION_REQUIRES_AT_LEAST_2_VALUES\n"
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

fd_out:
    .quad 0

arg_file:
    .quad 0

arg_start:
    .quad 0

arg_end:
    .quad 0

arg_col:
    .quad 0

count_val:
    .quad 0

slope_val:
    .quad 0

.section .text
.global _start

_start:
    ldr x0, [sp]
    cmp x0, #5
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

    adr x9, arg_file
    ldr x0, [x9]
    bl read_csv
    cmp x0, #0
    blt error_range

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
    cmp x0, #2
    blt error_data

    adr x9, count_val
    str x0, [x9]
    mov x22, x0

    mov x19, #0
    mov x23, #0
    mov x24, #0
    mov x25, #0
    mov x26, #0
    adr x27, values

sum_loop:
    cmp x19, x22
    bge calc_regression

    mov x4, #8
    mul x5, x19, x4
    add x6, x27, x5
    ldr x10, [x6]

    add x23, x23, x19
    add x24, x24, x10

    mul x11, x19, x10
    add x25, x25, x11

    mul x12, x19, x19
    add x26, x26, x12

    add x19, x19, #1
    b sum_loop

calc_regression:
    mul x10, x22, x25
    mul x11, x23, x24
    sub x12, x10, x11

    mul x13, x22, x26
    mul x14, x23, x23
    sub x15, x13, x14

    cbz x15, slope_zero

    mov x16, #100
    mul x12, x12, x16
    sdiv x17, x12, x15
    b save_slope

slope_zero:
    mov x17, #0

save_slope:
    adr x9, slope_val
    str x17, [x9]

    adr x0, out_filename
    bl open_output
    cmp x0, #0
    blt error_range

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

    adr x1, str_slope
    mov x2, #len_slope
    bl write_fd

    adr x9, slope_val
    ldr x0, [x9]
    bl write_num

    adr x1, str_trend
    mov x2, #len_trend
    bl write_fd

    adr x9, slope_val
    ldr x0, [x9]
    cmp x0, #0
    bgt trend_is_up
    blt trend_is_down

trend_is_stable:
    adr x1, trend_stable
    mov x2, #len_trend_stable
    bl write_fd
    b finish_ok

trend_is_up:
    adr x1, trend_up
    mov x2, #len_trend_up
    bl write_fd
    b finish_ok

trend_is_down:
    adr x1, trend_down
    mov x2, #len_trend_down
    bl write_fd

finish_ok:
    adr x1, str_status
    mov x2, #len_status
    bl write_fd

    adr x9, fd_out
    ldr x0, [x9]
    bl close_fd

    mov x0, #0
    mov x8, #93
    svc #0

write_fd:
    str x30, [sp, #-16]!

    adr x9, fd_out
    ldr x0, [x9]
    bl write_result

    ldr x30, [sp], #16
    ret

write_num:
    str x30, [sp, #-16]!

    adr x1, ascii_buf
    bl int_to_ascii

    mov x2, x0
    adr x1, ascii_buf
    bl write_fd

    ldr x30, [sp], #16
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

error_data:
    adr x1, err_data
    mov x2, #len_err_data
    b write_error

error_col:
    adr x1, err_col
    mov x2, #len_err_col
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


//Oliverio Abraham Caal Artola 202303864
//Modulo_2_regresion