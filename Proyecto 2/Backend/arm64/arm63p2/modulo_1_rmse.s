/* --------------------------------------
 * RUTINA 1 - DINA PEREZ
 * -------------------------------------- */
.section .data
lbl_calc:        .ascii "CALC=RMSE\nCOLUMN="
len_lbl_calc = . - lbl_calc
lbl_wstart:      .ascii "\nWINDOW_START="
len_lbl_wstart = . - lbl_wstart
lbl_wend:        .ascii "\nWINDOW_END="
len_lbl_wend = . - lbl_wend
lbl_count:       .ascii "\nCOUNT="
len_lbl_count = . - lbl_count
lbl_ideal:       .ascii "\nIDEAL="
len_lbl_ideal = . - lbl_ideal
lbl_rmse:        .ascii "\nRMSE="
len_lbl_rmse = . - lbl_rmse
lbl_status_ok:   .ascii "\nSTATUS=OK\n"
len_lbl_status_ok = . - lbl_status_ok
err_args_msg:         .asciz "INVALID_ARGS\nDETAIL=EXPECTED_6_ARGUMENTS\n"
err_datos_msg: .asciz "INSUFFICIENT_DATA\nDETAIL=RMSE_REQUIRES_AT_LEAST_2_VALUES\n"

.section .bss
.balign 8
values: .space 800000

.section .text
.global _start

_start:
    ldr x0, [sp]
    add x1, sp, #8
    bl main
    mov x8, #93
    svc #0

main:
    sub sp, sp, #96
    str x29, [sp, #0]
    str x30, [sp, #8]
    mov x29, sp
    str x19, [sp, #16]
    str x20, [sp, #24]
    str x21, [sp, #32]
    str x22, [sp, #40]
    str x23, [sp, #48]
    str x24, [sp, #56]
    str x25, [sp, #64]
    str x26, [sp, #72]
    str x27, [sp, #80]
    str x28, [sp, #88]

    mov x19, x0 // argc
    mov x20, x1 // argv

    cmp x19, #6
    bne error_arg

    // lectura csv
    ldr x0, [x20, #8]
    bl read_csv

    // linea inicial
    ldr x0, [x20, #16]
    bl parse_int
    mov x22, x0

    // linea final
    ldr x0, [x20, #24]
    bl parse_int
    mov x23, x0

    // columna
    ldr x24, [x20, #32]
    mov x0, x24
    bl column_name_to_index
    mov x25, x0
    cmp x25, #0
    blt error_columna

    // ideal
    ldr x0, [x20, #40]
    bl parse_int
    mov x26, x0

    // leer el rango 
    mov x0, x22
    mov x1, x23
    mov x2, x25
    adr x3, values
    bl read_range_column
    mov x27, x0          

    cmp x27, #0          
    blt error_rango
    cmp x27, #2
    blt error_datos_ins

    // Calculo RMSE 
    adr x9, values
    mov x10, #0
    mov x11, #0

sum_loop:
    cmp x10, x27
    bge sum_done
    ldr x12, [x9, x10, lsl #3]
    sub x12, x12, x26
    mul x12, x12, x12
    add x11, x11, x12
    add x10, x10, #1
    b sum_loop

sum_done:
    sdiv x12, x11, x27
    mov x0, x12
    bl sqrt_int
    mov x28, x0

    // CALC=RMSE
    // COLUMN=?
    adr x1, lbl_calc
    mov x2, len_lbl_calc
    bl write_stdout
    mov x0, x24
    bl print_cstr

    // WINDOW_START=
    adr x1, lbl_wstart
    mov x2, len_lbl_wstart
    bl write_stdout
    mov x0, x22
    bl print_uint

    // WINDOW_END=
    adr x1, lbl_wend
    mov x2, len_lbl_wend
    bl write_stdout
    mov x0, x23
    bl print_uint

    // COUNT=
    adr x1, lbl_count
    mov x2, len_lbl_count
    bl write_stdout
    mov x0, x27
    bl print_uint

    // IDEAL=
    adr x1, lbl_ideal
    mov x2, len_lbl_ideal
    bl write_stdout
    mov x0, x26
    bl print_uint

    // RMSE=
    adr x1, lbl_rmse
    mov x2, len_lbl_rmse
    bl write_stdout
    mov x0, x28
    bl print_uint

    // STATUS=OK
    adr x1, lbl_status_ok
    mov x2, len_lbl_status_ok
    bl write_stdout

    mov x0, #0
    b main_exit

error_arg:
    adr x0, err_args_msg
    bl report_error
    mov x0, #1
    b main_exit

error_columna:
    adr x0, err_columna_msg
    bl report_error
    mov x0, #1
    b main_exit

error_rango:
    adr x0, err_rango_msg
    bl report_error
    mov x0, #1
    b main_exit

error_datos_ins:
    adr x0, err_datos_msg
    bl report_error
    mov x0, #1
    b main_exit

main_exit:
    ldr x28, [sp, #88]
    ldr x27, [sp, #80]
    ldr x26, [sp, #72]
    ldr x25, [sp, #64]
    ldr x24, [sp, #56]
    ldr x23, [sp, #48]
    ldr x22, [sp, #40]
    ldr x21, [sp, #32]
    ldr x20, [sp, #24]
    ldr x19, [sp, #16]
    ldr x30, [sp, #8]
    ldr x29, [sp, #0]
    add sp, sp, #96
    ret
