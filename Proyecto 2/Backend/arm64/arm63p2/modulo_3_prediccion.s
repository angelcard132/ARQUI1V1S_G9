.section .data

out_filename:
    .asciz "resultado_prediccion.txt"

str_calc:
    .ascii "CALC=PREDICTION COLUMN="
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

str_k:
    .ascii " K="
len_k = . - str_k

str_slope:
    .ascii " SLOPE_X100="
len_slope = . - str_slope

str_intercept:
    .ascii " INTERCEPT_X100="
len_intercept = . - str_intercept

str_pred:
    .ascii " PREDICTED_"
len_pred = . - str_pred

str_equal:
    .ascii "="
len_equal = . - str_equal

str_ok:
    .ascii " STATUS=OK\n"
len_ok = . - str_ok

err_args:
    .ascii "STATUS=ERROR ERROR=INVALID_ARGS DETAIL=USE_FILE_START_END_COLUMN_OPTIONAL_K\n"
len_err_args = . - err_args

err_file:
    .ascii "STATUS=ERROR ERROR=FILE_READ_FAILED DETAIL=COULD_NOT_READ_CSV\n"
len_err_file = . - err_file

err_col:
    .ascii "STATUS=ERROR ERROR=INVALID_COLUMN DETAIL=COLUMN_NOT_SUPPORTED\n"
len_err_col = . - err_col

err_range:
    .ascii "STATUS=ERROR ERROR=INVALID_RANGE DETAIL=WINDOW_OUT_OF_RANGE\n"
len_err_range = . - err_range

err_data:
    .ascii "STATUS=ERROR ERROR=INSUFFICIENT_DATA DETAIL=PREDICTION_REQUIRES_AT_LEAST_2_VALUES\n"
len_err_data = . - err_data

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

k_val:
    .quad 0

slope_val:
    .quad 0

intercept_val:
    .quad 0

pred_val:
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

    ldr x0, [sp]
    cmp x0, #6
    blt default_k

    ldr x9, [sp, #48]
    mov x0, x9
    bl parse_int
    b save_k

default_k:
    mov x0, #5

save_k:
    adr x10, k_val
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

    mov x19, #0
    mov x23, #0
    mov x24, #0
    mov x25, #0
    mov x26, #0
    adr x27, values

sum_loop:
    cmp x19, x22
    bge calc_regression

    mov x8, #8
    mul x9, x19, x8
    add x10, x27, x9
    ldr x11, [x10]

    add x23, x23, x11
    add x24, x24, x19

    mul x12, x19, x11
    add x25, x25, x12

    mul x13, x19, x19
    add x26, x26, x13

    add x19, x19, #1
    b sum_loop

calc_regression:
    mul x10, x22, x25
    mul x11, x24, x23
    sub x12, x10, x11

    mul x13, x22, x26
    mul x14, x24, x24
    sub x15, x13, x14

    cmp x15, #0
    beq slope_zero

    mov x16, #100
    mul x12, x12, x16
    sdiv x17, x12, x15
    b calc_intercept

slope_zero:
    mov x17, #0

calc_intercept:
    mov x16, #100
    mul x10, x23, x16
    mul x11, x17, x24
    sub x12, x10, x11
    sdiv x18, x12, x22

    adr x9, slope_val
    str x17, [x9]
    adr x9, intercept_val
    str x18, [x9]

calc_prediction:
    adr x9, k_val
    ldr x10, [x9]
    add x11, x22, x10

    mul x12, x17, x11
    add x12, x12, x18
    mov x13, #100
    sdiv x14, x12, x13

    adr x9, pred_val
    str x14, [x9]

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

    adr x1, str_k
    mov x2, #len_k
    bl write_fd
    adr x9, k_val
    ldr x0, [x9]
    bl write_num

    adr x1, str_slope
    mov x2, #len_slope
    bl write_fd
    adr x9, slope_val
    ldr x0, [x9]
    bl write_num

    adr x1, str_intercept
    mov x2, #len_intercept
    bl write_fd
    adr x9, intercept_val
    ldr x0, [x9]
    bl write_num

    adr x1, str_pred
    mov x2, #len_pred
    bl write_fd
    adr x9, k_val
    ldr x0, [x9]
    bl write_num

    adr x1, str_equal
    mov x2, #len_equal
    bl write_fd
    adr x9, pred_val
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
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    adr x9, fd_out
    ldr x0, [x9]
    bl write_result

    ldr x30, [sp, #8]
    ldr x29, [sp]
    add sp, sp, #16
    ret

write_num:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    adr x1, ascii_buf
    bl int_to_ascii

    mov x2, x0
    adr x1, ascii_buf
    bl write_fd

    ldr x30, [sp, #8]
    ldr x29, [sp]
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


