.section .data
default_csv: .asciz "lecturas.csv"

err_open: .ascii "Error al abrir archivo\n"
len_err_open = . - err_open

err_read: .ascii "Error al leer archivo\n"
len_err_read = . - err_read

err_range: .ascii "ERROR=INVALID_RANGE\n"
len_err_range = . - err_range

err_column: .ascii "ERROR=INVALID_COLUMN\n"
len_err_column = . - err_column

// Mensajes reutilizables para errores estructurados
.global lbl_status_err
lbl_status_err: .ascii "STATUS=ERROR\n"
len_lbl_status_err = . - lbl_status_err

.global lbl_error
lbl_error: .ascii "ERROR="
len_lbl_error = . - lbl_error

.global err_columna_msg
err_columna_msg: .asciz "INVALID_COLUMN\nDETAIL=COLUMN_NOT_RECOGNIZED\n"

.global err_rango_msg
err_rango_msg: .asciz "INVALID_RANGE\nDETAIL=RANGE_OUT_OF_BOUNDS_OR_INVALID\n"

.global num_buffer
num_buffer: .skip 32

.align 8
.global csv_buffer
csv_buffer: .space 131072

.global csv_bytes_read
csv_bytes_read: .quad 0

.section .bss
tmp_col_buf: .space 32
stdin_buffer: .space 256

.section .text
.global open_csv, read_csv, get_column, parse_int
.global int_to_ascii, write_result, open_output, close_fd, newline
.global count_rows, read_range_column, column_name_to_index
.global read_stdin_line, write_stdout, sqrt_int, abs_int
.global print_uint, print_cstr, report_error

open_csv:
    cbnz x0, oc_use_arg
    ldr x1, =default_csv
    b oc_open

oc_use_arg:
    mov x1, x0

oc_open:
    mov x0, #-100
    mov x2, #0
    mov x3, #0
    mov x8, #56
    svc #0
    ret

read_csv:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    str x19, [sp, #-16]!

    bl open_csv
    cmp x0, #0
    blt rc_err

    mov x19, x0

    mov x0, x19
    adr x1, csv_buffer
    mov x2, #131072
    mov x8, #63
    svc #0
    cmp x0, #0
    blt rd_err

    adr x9, csv_bytes_read
    str x0, [x9]

    mov x0, x19
    mov x8, #57
    svc #0

    adr x9, csv_bytes_read
    ldr x0, [x9]

    ldr x19, [sp], #16
    ldr x29, [sp]
    ldr x30, [sp, #8]
    add sp, sp, #16
    ret

rc_err:
    mov x0, #-1
    ldr x19, [sp], #16
    ldr x29, [sp]
    ldr x30, [sp, #8]
    add sp, sp, #16
    ret

rd_err:
    mov x0, x19
    mov x8, #57
    svc #0

    mov x0, #-2
    ldr x19, [sp], #16
    ldr x29, [sp]
    ldr x30, [sp, #8]
    add sp, sp, #16
    ret

get_column:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    stp x19, x20, [sp, #-16]!
    stp x21, x22, [sp, #-16]!
    stp x23, x24, [sp, #-16]!

    mov x19, x0
    mov x20, x1
    mov x21, x2
    mov x22, x3
    adr x23, csv_buffer

gc_hdr:
    ldrb w9, [x23], #1
    cbz w9, gc_nf
    cmp w9, #'$'
    beq gc_nf
    cmp w9, #10
    bne gc_hdr

    cbz x19, gc_row

gc_rows:
    ldrb w9, [x23], #1
    cbz w9, gc_nf
    cmp w9, #'$'
    beq gc_nf
    cmp w9, #10
    bne gc_rows
    sub x19, x19, #1
    cmp x19, #0
    bne gc_rows

gc_row:
    cbz x20, gc_copy

gc_cols:
    ldrb w9, [x23], #1
    cbz w9, gc_nf
    cmp w9, #'$'
    beq gc_nf
    cmp w9, #10
    beq gc_nf
    cmp w9, #','
    bne gc_cols
    sub x20, x20, #1
    cmp x20, #0
    bne gc_cols

gc_copy:
    mov x24, #0
    sub x22, x22, #1

gc_loop:
    cmp x24, x22
    bge gc_done
    ldrb w9, [x23], #1
    cbz w9, gc_done
    cmp w9, #'$'
    beq gc_done
    cmp w9, #','
    beq gc_done
    cmp w9, #10
    beq gc_done
    strb w9, [x21, x24]
    add x24, x24, #1
    b gc_loop

gc_done:
    mov w9, #0
    strb w9, [x21, x24]
    mov x0, x24
    b gc_exit

gc_nf:
    mov x0, #0
    mov w9, #0
    strb w9, [x21]

gc_exit:
    ldr x23, [sp]
    ldr x24, [sp, #8]
    add sp, sp, #16

    ldr x21, [sp]
    ldr x22, [sp, #8]
    add sp, sp, #16

    ldr x19, [sp]
    ldr x20, [sp, #8]
    add sp, sp, #16

    ldr x29, [sp]
    ldr x30, [sp, #8]
    add sp, sp, #16
    ret

count_rows:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    str x19, [sp, #-16]!

    adr x19, csv_buffer
    mov x0, #0

cr_skip_header:
    ldrb w9, [x19], #1
    cbz w9, cr_done
    cmp w9, #'$'
    beq cr_done
    cmp w9, #10
    bne cr_skip_header

cr_loop:
    ldrb w9, [x19], #1
    cbz w9, cr_done
    cmp w9, #'$'
    beq cr_done
    cmp w9, #10
    bne cr_loop
    add x0, x0, #1
    b cr_loop

cr_done:
    ldr x19, [sp], #16
    ldr x29, [sp]
    ldr x30, [sp, #8]
    add sp, sp, #16
    ret

read_range_column:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    stp x19, x20, [sp, #-16]!
    stp x21, x22, [sp, #-16]!
    stp x23, x24, [sp, #-16]!
    stp x25, x26, [sp, #-16]!
    str x27, [sp, #-16]!

    mov x19, x0
    mov x20, x1
    mov x21, x2
    mov x22, x3

    cmp x19, #1
    blt rrc_error
    cmp x20, x19
    blt rrc_error

    bl count_rows
    cmp x20, x0
    bgt rrc_error

    sub x23, x19, #1
    sub x24, x20, #1
    mov x25, #0

rrc_loop:
    cmp x23, x24
    bgt rrc_done

    mov x0, x23
    mov x1, x21
    adr x2, tmp_col_buf
    mov x3, #32
    bl get_column
    cmp x0, #0
    beq rrc_error

    adr x0, tmp_col_buf
    bl parse_int

    mov x9, #8
    mul x10, x25, x9
    add x11, x22, x10
    str x0, [x11]

    add x25, x25, #1
    add x23, x23, #1
    b rrc_loop

rrc_done:
    mov x0, x25
    b rrc_exit

rrc_error:
    mov x0, #-1

rrc_exit:
    ldr x27, [sp], #16

    ldr x25, [sp]
    ldr x26, [sp, #8]
    add sp, sp, #16

    ldr x23, [sp]
    ldr x24, [sp, #8]
    add sp, sp, #16

    ldr x21, [sp]
    ldr x22, [sp, #8]
    add sp, sp, #16

    ldr x19, [sp]
    ldr x20, [sp, #8]
    add sp, sp, #16

    ldr x29, [sp]
    ldr x30, [sp, #8]
    add sp, sp, #16
    ret

column_name_to_index:
    ldrb w9, [x0]
    cmp w9, #'T'
    beq col_temp
    cmp w9, #'H'
    beq col_hum
    cmp w9, #'S'
    beq col_soil
    cmp w9, #'L'
    beq col_luz
    cmp w9, #'G'
    beq col_gas
    mov x0, #-1
    ret

col_temp:
    mov x0, #1
    ret

col_hum:
    mov x0, #2
    ret

col_soil:
    ldrb w9, [x0, #4]
    cmp w9, #'1'
    beq col_soil1
    cmp w9, #'2'
    beq col_soil2
    mov x0, #-1
    ret

col_soil1:
    mov x0, #3
    ret

col_soil2:
    mov x0, #4
    ret

col_luz:
    mov x0, #5
    ret

col_gas:
    mov x0, #6
    ret

parse_int:
    mov x1, x0
    mov x0, #0
    mov x2, #0
    ldrb w3, [x1]
    cmp w3, #'-'
    bne pi_d
    mov x2, #1
    add x1, x1, #1

pi_d:
    ldrb w3, [x1]
    cmp w3, #'0'
    blt pi_e
    cmp w3, #'9'
    bgt pi_e
    sub w3, w3, #'0'
    mov x4, #10
    mul x0, x0, x4
    add x0, x0, x3
    add x1, x1, #1
    b pi_d

pi_e:
    cbz x2, pi_ret
    sub x0, xzr, x0

pi_ret:
    ret

int_to_ascii:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    stp x19, x20, [sp, #-16]!
    stp x21, x22, [sp, #-16]!
    stp x23, x24, [sp, #-16]!
    sub sp, sp, #32

    mov x19, x0
    mov x20, x1
    mov x21, sp
    mov x22, #0
    mov x24, #0

    cmp x19, #0
    bge ita_l
    sub x19, xzr, x19
    mov x24, #1

ita_l:
    cbnz x19, ita_lp
    mov w10, #'0'
    strb w10, [x21]
    mov x22, #1
    b ita_r

ita_lp:
    cbz x19, ita_r
    mov x11, #10
    udiv x12, x19, x11
    msub x13, x12, x11, x19
    add w13, w13, #'0'
    strb w13, [x21, x22]
    add x22, x22, #1
    mov x19, x12
    b ita_lp

ita_r:
    mov x23, #0
    cbz x24, ita_rev
    mov w10, #'-'
    strb w10, [x20]
    add x23, x23, #1

ita_rev:
    cbz x22, ita_d
    sub x22, x22, #1
    ldrb w10, [x21, x22]
    strb w10, [x20, x23]
    add x23, x23, #1
    b ita_rev

ita_d:
    mov w10, #0
    strb w10, [x20, x23]
    mov x0, x23

    add sp, sp, #32

    ldr x23, [sp]
    ldr x24, [sp, #8]
    add sp, sp, #16

    ldr x21, [sp]
    ldr x22, [sp, #8]
    add sp, sp, #16

    ldr x19, [sp]
    ldr x20, [sp, #8]
    add sp, sp, #16

    ldr x29, [sp]
    ldr x30, [sp, #8]
    add sp, sp, #16
    ret

open_output:
    mov x1, x0
    mov x0, #-100
    mov x2, #0x241
    mov x3, #0x1A4
    mov x8, #56
    svc #0
    ret

write_result:
    mov x8, #64
    svc #0
    ret

write_stdout:
    mov x0, #1
    mov x8, #64
    svc #0
    ret

close_fd:
    mov x8, #57
    svc #0
    ret

newline:
    mov w9, #10
    strb w9, [sp, #-1]!
    mov x1, sp
    mov x2, #1
    mov x8, #64
    svc #0
    add sp, sp, #1
    ret

read_stdin_line:
    mov x0, #0
    adr x1, stdin_buffer
    mov x2, #255
    mov x8, #63
    svc #0

    cmp x0, #0
    ble rsl_ret

    adr x1, stdin_buffer
    mov x2, #0

rsl_zero_loop:
    cmp x2, x0
    bge rsl_finish
    ldrb w3, [x1, x2]
    cmp w3, #10
    beq rsl_put_zero
    add x2, x2, #1
    b rsl_zero_loop

rsl_put_zero:
    mov w3, #0
    strb w3, [x1, x2]

rsl_finish:
    adr x0, stdin_buffer
    ret

rsl_ret:
    mov x0, #0
    ret

sqrt_int:
    mov x1, #0

sqrt_loop:
    mul x2, x1, x1
    cmp x2, x0
    bgt sqrt_done
    add x1, x1, #1
    b sqrt_loop

sqrt_done:
    sub x0, x1, #1
    ret

abs_int:
    cmp x0, #0
    bge abs_done
    sub x0, xzr, x0

abs_done:
    ret

print_cstr:
    mov x1, x0
    mov x2, #0

cstr_len:
    ldrb w3, [x1, x2]
    cbz w3, cstr_print
    add x2, x2, #1
    b cstr_len

cstr_print:
    mov x0, #1
    mov x8, #64
    svc #0
    ret

print_uint:
    ldr x1, =num_buffer
    add x1, x1, #31
    mov w2, #0
    strb w2, [x1]
    mov x3, #10
    mov x4, #0

    cmp x0, #0
    bne convert_loop

    sub x1, x1, #1
    mov w2, #'0'
    strb w2, [x1]
    mov x4, #1
    b write_number

convert_loop:
    udiv x5, x0, x3
    msub x6, x5, x3, x0
    add x6, x6, #'0'
    sub x1, x1, #1
    strb w6, [x1]
    add x4, x4, #1
    mov x0, x5
    cbnz x0, convert_loop

write_number:
    mov x0, #1
    mov x2, x4
    mov x8, #64
    svc #0
    ret

report_error:
    mov x9, x0

    adr x1, lbl_status_err
    mov x2, len_lbl_status_err
    bl write_stdout

    adr x1, lbl_error
    mov x2, len_lbl_error
    bl write_stdout

    mov x0, x9
    bl print_cstr
    ret
