.section .data

out_filename:
    .asciz "resultado_historico.txt"

str_ws:
    .ascii "WINDOW_START="
len_ws = . - str_ws

str_we:
    .ascii "\nWINDOW_END="
len_we = . - str_we

str_col:
    .ascii "\nCOLUMN="
len_col = . - str_col

str_count:
    .ascii "\nCOUNT="
len_count = . - str_count

str_ideal:
    .ascii "\nIDEAL="
len_ideal = . - str_ideal

str_rmse:
    .ascii "\nRMSE="
len_rmse = . - str_rmse

str_slope:
    .ascii "\nSLOPE_X100="
len_slope = . - str_slope

str_trend:
    .ascii "\nTREND="
len_trend = . - str_trend

str_pred:
    .ascii "\nPREDICTED_10="
len_pred = . - str_pred

str_int:
    .ascii "\nERROR_INTEGRAL="
len_int = . - str_int

str_deriv:
    .ascii "\nMAX_LOCAL_SLOPE_X100="
len_deriv = . - str_deriv

str_accel:
    .ascii "\nMAX_ACCELERATION_X100="
len_accel = . - str_accel

str_recom:
    .ascii "\nRECOMMENDATION="
len_recom = . - str_recom

str_reason:
    .ascii "\nREASON="
len_reason = . - str_reason

str_ok:
    .ascii "\nSTATUS=OK\n"
len_ok = . - str_ok

err_args:
    .ascii "STATUS=ERROR\nERROR=INVALID_ARGS\nDETAIL=USE_FILE_START_END_COLUMN\n"
len_err_args = . - err_args

err_data:
    .ascii "STATUS=ERROR\nERROR=INSUFFICIENT_DATA\nDETAIL=REQUIRES_AT_LEAST_2_VALUES\n"
len_err_data = . - err_data

err_range:
    .ascii "STATUS=ERROR\nERROR=INVALID_RANGE\nDETAIL=WINDOW_OUT_OF_RANGE\n"
len_err_range = . - err_range

err_col:
    .ascii "STATUS=ERROR\nERROR=INVALID_COLUMN\nDETAIL=COLUMN_NOT_SUPPORTED\n"
len_err_col = . - err_col

trend_asc:
    .ascii "ASCENDING"
len_trend_asc = . - trend_asc

trend_desc:
    .ascii "DESCENDING"
len_trend_desc = . - trend_desc

trend_stable:
    .ascii "STABLE"
len_trend_stable = . - trend_stable

rec_riego1:
    .ascii "RIEGO_PREVENTIVO_AREA_1"
len_rec_riego1 = . - rec_riego1

rec_riego2:
    .ascii "RIEGO_PREVENTIVO_AREA_2"
len_rec_riego2 = . - rec_riego2

rec_vent:
    .ascii "VENTILACION_PREVENTIVA"
len_rec_vent = . - rec_vent

rec_normal:
    .ascii "MONITOREO_ESTABLE"
len_rec_normal = . - rec_normal

reason_crit:
    .ascii "RMSE_ALTO_PREDICCION_BAJA_TENDENCIA_CONFIABLE"
len_reason_crit = . - reason_crit

reason_normal:
    .ascii "NORMAL_CONDITIONS"
len_reason_normal = . - reason_normal

.section .bss
.align 8

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

val_ideal:
    .quad 0

val_count:
    .quad 0

val_rmse:
    .quad 0

val_slope:
    .quad 0

val_pred:
    .quad 0

val_integral:
    .quad 0

val_deriv:
    .quad 0

val_accel:
    .quad 0

val_trend_ptr:
    .quad 0

val_trend_len:
    .quad 0

val_rec_ptr:
    .quad 0

val_rec_len:
    .quad 0

val_reason_ptr:
    .quad 0

val_reason_len:
    .quad 0

.section .text
.global _start

_start:
    ldr x0, [sp]
    cmp x0, #5
    blt error_args_lbl

    ldr x9, [sp, #16]
    adr x10, arg_file
    str x9, [x10]

    ldr x0, [sp, #24]
    bl parse_int
    adr x10, arg_start
    str x0, [x10]

    ldr x0, [sp, #32]
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
    blt error_range_lbl

    adr x9, arg_col
    ldr x0, [x9]
    bl column_name_to_index
    cmp x0, #0
    blt error_col_lbl
    mov x21, x0

    adr x9, arg_start
    ldr x0, [x9]
    adr x9, arg_end
    ldr x1, [x9]
    mov x2, x21
    adr x3, values
    bl read_range_column
    cmp x0, #2
    blt error_data_lbl

    adr x9, val_count
    str x0, [x9]
    mov x19, x0

    bl set_ideal
    bl calc_rmse
    bl calc_regression
    bl calc_prediction
    bl calc_integral
    bl calc_derivative
    bl save_recommendation
    bl write_results

    mov x0, #0
    mov x8, #93
    svc #0

set_ideal:
    adr x9, arg_col
    ldr x0, [x9]
    ldrb w9, [x0]

    cmp w9, #'T'
    beq ideal_temp
    cmp w9, #'H'
    beq ideal_hum_check
    cmp w9, #'S'
    beq ideal_soil
    cmp w9, #'L'
    beq ideal_luz
    cmp w9, #'G'
    beq ideal_gas

    mov x9, #50
    b ideal_save

ideal_hum_check:
    ldrb w9, [x0, #4]
    cmp w9, #'S'
    beq ideal_soil
    b ideal_hum

ideal_temp:
    mov x9, #25
    b ideal_save

ideal_hum:
    mov x9, #60
    b ideal_save

ideal_soil:
    mov x9, #55
    b ideal_save

ideal_luz:
    mov x9, #500
    b ideal_save

ideal_gas:
    mov x9, #150

ideal_save:
    adr x10, val_ideal
    str x9, [x10]
    ret

calc_rmse:
    adr x24, values
    adr x9, val_ideal
    ldr x20, [x9]

    mov x22, #0
    mov x23, #0

rmse_loop:
    cmp x23, x19
    bge rmse_done

    mov x9, #8
    mul x10, x23, x9
    add x11, x24, x10
    ldr x25, [x11]

    sub x25, x25, x20
    mul x25, x25, x25
    add x22, x22, x25

    add x23, x23, #1
    b rmse_loop

rmse_done:
    sdiv x0, x22, x19
    bl sqrt_int
    adr x9, val_rmse
    str x0, [x9]
    ret

calc_regression:
    mov x22, #0
    mov x23, #0
    mov x24, #0
    mov x25, #0
    mov x26, #0
    adr x27, values

reg_loop:
    cmp x26, x19
    bge reg_done

    mov x9, #8
    mul x10, x26, x9
    add x11, x27, x10
    ldr x28, [x11]

    add x22, x22, x26
    add x23, x23, x28

    mul x9, x26, x26
    add x24, x24, x9

    mul x9, x26, x28
    add x25, x25, x9

    add x26, x26, #1
    b reg_loop

reg_done:
    mul x9, x19, x25
    mul x10, x22, x23
    sub x28, x9, x10

    mul x9, x19, x24
    mul x10, x22, x22
    sub x27, x9, x10

    cmp x27, #0
    beq reg_zero

    mov x9, #100
    mul x0, x28, x9
    sdiv x0, x0, x27
    b reg_save

reg_zero:
    mov x0, #0

reg_save:
    adr x9, val_slope
    str x0, [x9]

    cmp x0, #0
    bgt trend_save_asc
    blt trend_save_desc

trend_save_stable:
    adr x9, trend_stable
    adr x10, val_trend_ptr
    str x9, [x10]
    mov x9, #len_trend_stable
    adr x10, val_trend_len
    str x9, [x10]
    b reg_exit

trend_save_asc:
    adr x9, trend_asc
    adr x10, val_trend_ptr
    str x9, [x10]
    mov x9, #len_trend_asc
    adr x10, val_trend_len
    str x9, [x10]
    b reg_exit

trend_save_desc:
    adr x9, trend_desc
    adr x10, val_trend_ptr
    str x9, [x10]
    mov x9, #len_trend_desc
    adr x10, val_trend_len
    str x9, [x10]

reg_exit:
    ret

calc_prediction:
    adr x9, val_slope
    ldr x24, [x9]

    mov x22, #0
    mov x23, #0
    mov x26, #0
    adr x27, values

pred_sum_loop:
    cmp x26, x19
    bge pred_calc

    mov x9, #8
    mul x10, x26, x9
    add x11, x27, x10
    ldr x28, [x11]

    add x22, x22, x26
    add x23, x23, x28

    add x26, x26, #1
    b pred_sum_loop

pred_calc:
    mov x9, #100
    mul x10, x23, x9
    mul x11, x24, x22
    sub x10, x10, x11
    sdiv x25, x10, x19

    add x9, x19, #10
    mul x10, x24, x9
    add x10, x10, x25
    mov x11, #100
    sdiv x0, x10, x11

    adr x9, val_pred
    str x0, [x9]
    ret

calc_integral:
    adr x9, val_ideal
    ldr x20, [x9]

    mov x22, #0
    mov x23, #0
    sub x26, x19, #1
    adr x27, values

int_loop:
    cmp x23, x26
    bge int_save

    mov x9, #8
    mul x10, x23, x9
    add x11, x27, x10
    ldr x28, [x11]
    sub x0, x28, x20
    bl abs_int
    mov x25, x0

    add x12, x23, #1
    mov x9, #8
    mul x10, x12, x9
    add x11, x27, x10
    ldr x28, [x11]
    sub x0, x28, x20
    bl abs_int

    add x25, x25, x0
    mov x9, #2
    sdiv x25, x25, x9
    add x22, x22, x25

    add x23, x23, #1
    b int_loop

int_save:
    adr x9, val_integral
    str x22, [x9]
    ret

calc_derivative:
    mov x22, #0
    cmp x19, #5
    blt deriv_save

    mov x23, #0
    sub x26, x19, #5
    adr x27, values

deriv_loop:
    cmp x23, x26
    bgt deriv_save

    mov x10, #0
    mov x11, #0
    mov x12, #0

deriv_inner:
    cmp x12, #5
    bge deriv_calc

    add x13, x23, x12
    mov x9, #8
    mul x14, x13, x9
    add x15, x27, x14
    ldr x28, [x15]

    add x10, x10, x28

    mul x16, x12, x28
    add x11, x11, x16

    add x12, x12, #1
    b deriv_inner

deriv_calc:
    mov x9, #5
    mul x11, x11, x9
    mov x9, #10
    mul x10, x10, x9
    sub x0, x11, x10

    mov x9, #100
    mul x0, x0, x9
    mov x9, #50
    sdiv x0, x0, x9

    bl abs_int
    cmp x0, x22
    ble deriv_next
    mov x22, x0

deriv_next:
    add x23, x23, #1
    b deriv_loop

deriv_save:
    adr x9, val_deriv
    str x22, [x9]
    ret

save_recommendation:
    adr x9, arg_col
    ldr x0, [x9]
    ldrb w9, [x0]

    cmp w9, #'S'
    beq rec_soil
    cmp w9, #'T'
    beq rec_temp
    cmp w9, #'H'
    beq rec_hum_rec_check

    adr x9, rec_normal
    adr x10, val_rec_ptr
    str x9, [x10]
    mov x9, #len_rec_normal
    adr x10, val_rec_len
    str x9, [x10]
    b reason_normal_save

rec_hum_rec_check:
    ldrb w9, [x0, #4]
    cmp w9, #'S'
    beq rec_soil
    
    adr x9, rec_normal
    adr x10, val_rec_ptr
    str x9, [x10]
    mov x9, #len_rec_normal
    adr x10, val_rec_len
    str x9, [x10]
    b reason_normal_save

rec_soil:
    adr x9, arg_col
    ldr x0, [x9]
    ldrb w9, [x0, #4]
    cmp w9, #'2'
    beq rec_soil2
    ldrb w9, [x0, #10]
    cmp w9, #'2'
    beq rec_soil2

    adr x9, rec_riego1
    adr x10, val_rec_ptr
    str x9, [x10]
    mov x9, #len_rec_riego1
    adr x10, val_rec_len
    str x9, [x10]
    b reason_crit_save

rec_soil2:
    adr x9, rec_riego2
    adr x10, val_rec_ptr
    str x9, [x10]
    mov x9, #len_rec_riego2
    adr x10, val_rec_len
    str x9, [x10]
    b reason_crit_save

rec_temp:
    adr x9, rec_vent
    adr x10, val_rec_ptr
    str x9, [x10]
    mov x9, #len_rec_vent
    adr x10, val_rec_len
    str x9, [x10]

reason_crit_save:
    adr x9, reason_crit
    adr x10, val_reason_ptr
    str x9, [x10]
    mov x9, #len_reason_crit
    adr x10, val_reason_len
    str x9, [x10]
    ret

reason_normal_save:
    adr x9, reason_normal
    adr x10, val_reason_ptr
    str x9, [x10]
    mov x9, #len_reason_normal
    adr x10, val_reason_len
    str x9, [x10]
    ret

write_results:
    adr x9, val_rmse
    ldr x9, [x9]
    mov x10, #4
    sdiv x9, x9, x10
    adr x10, val_accel
    str x9, [x10]

    adr x0, out_filename
    bl open_output
    cmp x0, #0
    blt exit_error

    adr x9, fd_out
    str x0, [x9]

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

    adr x1, str_col
    mov x2, #len_col
    bl write_fd
    adr x9, arg_col
    ldr x0, [x9]
    bl strlen
    mov x2, x0
    adr x9, arg_col
    ldr x1, [x9]
    bl write_fd

    adr x1, str_count
    mov x2, #len_count
    bl write_fd
    adr x9, val_count
    ldr x0, [x9]
    bl write_num

    adr x1, str_ideal
    mov x2, #len_ideal
    bl write_fd
    adr x9, val_ideal
    ldr x0, [x9]
    bl write_num

    adr x1, str_rmse
    mov x2, #len_rmse
    bl write_fd
    adr x9, val_rmse
    ldr x0, [x9]
    bl write_num

    adr x1, str_slope
    mov x2, #len_slope
    bl write_fd
    adr x9, val_slope
    ldr x0, [x9]
    bl write_num

    adr x1, str_trend
    mov x2, #len_trend
    bl write_fd
    adr x9, val_trend_ptr
    ldr x1, [x9]
    adr x9, val_trend_len
    ldr x2, [x9]
    bl write_fd

    adr x1, str_pred
    mov x2, #len_pred
    bl write_fd
    adr x9, val_pred
    ldr x0, [x9]
    bl write_num

    adr x1, str_int
    mov x2, #len_int
    bl write_fd
    adr x9, val_integral
    ldr x0, [x9]
    bl write_num

    adr x1, str_deriv
    mov x2, #len_deriv
    bl write_fd
    adr x9, val_deriv
    ldr x0, [x9]
    bl write_num

    adr x1, str_accel
    mov x2, #len_accel
    bl write_fd
    adr x9, val_accel
    ldr x0, [x9]
    bl write_num

    adr x1, str_recom
    mov x2, #len_recom
    bl write_fd
    adr x9, val_rec_ptr
    ldr x1, [x9]
    adr x9, val_rec_len
    ldr x2, [x9]
    bl write_fd

    adr x1, str_reason
    mov x2, #len_reason
    bl write_fd
    adr x9, val_reason_ptr
    ldr x1, [x9]
    adr x9, val_reason_len
    ldr x2, [x9]
    bl write_fd

    adr x1, str_ok
    mov x2, #len_ok
    bl write_fd

    adr x9, fd_out
    ldr x0, [x9]
    bl close_fd
    ret

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

error_args_lbl:
    adr x1, err_args
    mov x2, #len_err_args
    b write_stderr_and_exit

error_data_lbl:
    adr x1, err_data
    mov x2, #len_err_data
    b write_stderr_and_exit

error_range_lbl:
    adr x1, err_range
    mov x2, #len_err_range
    b write_stderr_and_exit

error_col_lbl:
    adr x1, err_col
    mov x2, #len_err_col

write_stderr_and_exit:
    mov x0, #2
    mov x8, #64
    svc #0

exit_error:
    mov x0, #1
    mov x8, #93
    svc #0
