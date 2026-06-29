// Modulo 1 - DINA PEREZ RMSE

.section .data

lbl_calc:
    .ascii "CALC=RMSE\nCOLUMN="
len_lbl_calc = . - lbl_calc

lbl_wstart:
    .ascii "\nWINDOW_START="
len_lbl_wstart = . - lbl_wstart

lbl_wend:
    .ascii "\nWINDOW_END="
len_lbl_wend = . - lbl_wend

lbl_count:
    .ascii "\nCOUNT="
len_lbl_count = . - lbl_count

lbl_ideal:
    .ascii "\nIDEAL="
len_lbl_ideal = . - lbl_ideal

lbl_rmse:
    .ascii "\nRMSE="
len_lbl_rmse = . - lbl_rmse

lbl_status_ok:
    .ascii "\nSTATUS=OK\n"
len_lbl_status_ok = . - lbl_status_ok

err_args_msg:
    .asciz "INVALID_ARGS\nDETAIL=EXPECTED_FILE_START_END_COLUMN_IDEAL\n"

err_file_msg:
    .asciz "FILE_ERROR\nDETAIL=CSV_COULD_NOT_BE_READ\n"

err_col_msg:
    .asciz "INVALID_COLUMN\nDETAIL=COLUMN_NOT_SUPPORTED\n"

err_range_msg:
    .asciz "INVALID_RANGE\nDETAIL=WINDOW_OUT_OF_RANGE\n"

err_data_msg:
    .asciz "INSUFFICIENT_DATA\nDETAIL=RMSE_REQUIRES_AT_LEAST_2_VALUES\n"

.section .bss
values:
    .space 800000

.section .text
.global _start

_start:
    ldr x0, [sp]
    cmp x0, #6
    bne error_args

    ldr x19, [sp, #16]     
    ldr x20, [sp, #24]     
    ldr x21, [sp, #32]     
    ldr x22, [sp, #40]     
    ldr x23, [sp, #48]     

    //leemos el archivo
    mov x0, x19
    bl read_csv
    cmp x0, #0
    blt error_file

    //fila inicial
    mov x0, x20
    bl parse_int
    mov x24, x0            

    //fila final
    mov x0, x21
    bl parse_int
    mov x25, x0            

    //columna
    mov x0, x22
    bl column_name_to_index
    cmp x0, #0
    blt error_col
    mov x26, x0           

    //ideal
    mov x0, x23
    bl parse_int
    mov x27, x0            

    mov x0, x24
    mov x1, x25
    mov x2, x26
    adr x3, values
    bl read_range_column
    cmp x0, #0
    blt error_range
    cmp x0, #2
    blt error_data
    mov x28, x0          

    adr x19, values
    mov x20, #0            
    mov x21, #0           
    mov x17, #8           

sum_loop:
    cmp x20, x28
    bge calc_rmse

    mul x9, x20, x17
    add x10, x19, x9
    ldr x11, [x10]

    sub x11, x11, x27
    mul x11, x11, x11
    add x21, x21, x11

    add x20, x20, #1
    b sum_loop

calc_rmse:
    sdiv x0, x21, x28
    bl sqrt_int
    mov x23, x0            

    //imprimimos los valores finales
    adr x1, lbl_calc
    mov x2, len_lbl_calc
    bl write_stdout
    mov x0, x22
    bl print_cstr

    adr x1, lbl_wstart
    mov x2, len_lbl_wstart
    bl write_stdout
    mov x0, x24
    bl print_uint

    adr x1, lbl_wend
    mov x2, len_lbl_wend
    bl write_stdout
    mov x0, x25
    bl print_uint

    adr x1, lbl_count
    mov x2, len_lbl_count
    bl write_stdout
    mov x0, x28
    bl print_uint

    adr x1, lbl_ideal
    mov x2, len_lbl_ideal
    bl write_stdout
    mov x0, x27
    bl print_uint

    adr x1, lbl_rmse
    mov x2, len_lbl_rmse
    bl write_stdout
    mov x0, x23
    bl print_uint

    adr x1, lbl_status_ok
    mov x2, len_lbl_status_ok
    bl write_stdout

    mov x0, #0
    mov x8, #93
    svc #0

//funciones de error
error_args:
    adr x0, err_args_msg
    bl report_error
    b exit_error

error_file:
    adr x0, err_file_msg
    bl report_error
    b exit_error

error_col:
    adr x0, err_col_msg
    bl report_error
    b exit_error

error_range:
    adr x0, err_range_msg
    bl report_error
    b exit_error

error_data:
    adr x0, err_data_msg
    bl report_error

exit_error:
    mov x0, #1
    mov x8, #93
    svc #0
