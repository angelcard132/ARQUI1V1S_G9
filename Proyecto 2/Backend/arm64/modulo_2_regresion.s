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