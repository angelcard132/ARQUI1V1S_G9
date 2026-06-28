.section .data

out_filename: .asciz "resultado_derivada.txt"

str_calc: .ascii "CALC=LOCAL_DERIVATIVE COLUMN="
len_calc = . - str_calc

str_ws: .ascii " WINDOW_START="
len_ws = . - str_ws

str_we: .ascii " WINDOW_END="
len_we = . - str_we

str_count: .ascii " COUNT="
len_count = . - str_count

str_wsize: .ascii " WINDOW_SIZE=5"
len_wsize = . - str_wsize

str_max: .ascii " MAX_LOCAL_SLOPE_X100="
len_max = . - str_max

str_ok: .ascii " STATUS=OK\n"
len_ok = . - str_ok

err_args: .ascii "STATUS=ERROR ERROR=INVALID_ARGS DETAIL=USE_FILE_START_END_COLUMN\n"
len_err_args = . - err_args

err_data: .ascii "STATUS=ERROR ERROR=INSUFFICIENT_DATA DETAIL=LOCAL_DERIVATIVE_REQUIRES_AT_LEAST_5_VALUES\n"
len_err_data = . - err_data

err_range: .ascii "STATUS=ERROR ERROR=INVALID_RANGE DETAIL=WINDOW_OUT_OF_RANGE\n"
len_err_range = . - err_range

err_col: .ascii "STATUS=ERROR ERROR=INVALID_COLUMN DETAIL=COLUMN_NOT_SUPPORTED\n"
len_err_col = . - err_col

.section .bss

values: .space 8192
ascii_buf: .space 32
fd_out: .quad 0
arg_file: .quad 0
arg_start: .quad 0
arg_end: .quad 0
arg_col: .quad 0
count_val: .quad 0
max_slope: .quad 0

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
    cmp x0, #5
    blt error_data

    adr x9, count_val
    str x0, [x9]
    mov x22, x0

    mov x19, #0
    mov x28, #0
    adr x27, values

local_window_loop:
    sub x10, x22, #5
    cmp x19, x10
    bgt write_output

    mov x23, #0
    mov x24, #0

    ldr x10, [x27, x19, lsl #3]
    add x24, x24, x10

    add x11, x19, #1
    ldr x10, [x27, x11, lsl #3]
    add x24, x24, x10
    add x23, x23, x10

    add x11, x19, #2
    ldr x10, [x27, x11, lsl #3]
    add x24, x24, x10
    mov x12, #2
    madd x23, x10, x12, x23

    add x11, x19, #3
    ldr x10, [x27, x11, lsl #3]
    add x24, x24, x10
    mov x12, #3
    madd x23, x10, x12, x23

    add x11, x19, #4
    ldr x10, [x27, x11, lsl #3]
    add x24, x24, x10
    mov x12, #4
    madd x23, x10, x12, x23

    mov x10, #5
    mul x11, x10, x23

    mov x10, #10
    mul x12, x10, x24

    sub x13, x11, x12

    mov x10, #100
    mul x13, x13, x10

    mov x10, #50
    sdiv x14, x13, x10

    mov x0, x14
    cmp x0, #0
    bge abs_ready
    neg x0, x0

abs_ready:
    cmp x0, x28
    ble next_window
    mov x28, x0

next_window:
    add x19, x19, #1
    b local_window_loop

write_output:
    adr x9, max_slope
    str x28, [x9]

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

    adr x1, str_wsize
    mov x2, #len_wsize
    bl write_fd

    adr x1, str_max
    mov x2, #len_max
    bl write_fd
    adr x9, max_slope
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
    ldp x29, x30, [sp], #16
    ret

write_num:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    adr x1, ascii_buf
    bl int_to_ascii
    mov x2, x0
    adr x1, ascii_buf
    bl write_fd
    ldp x29, x30, [sp], #16
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