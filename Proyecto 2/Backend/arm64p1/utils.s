.section .data
csv_filename:   .asciz "lecturas.csv"
err_open:       .ascii "Error al abrir archivo\n"
len_err_open = . - err_open
err_read:       .ascii "Error al leer archivo\n"
len_err_read = . - err_read

.align 8
.global csv_buffer
csv_buffer:     .space 65536
.global csv_bytes_read
csv_bytes_read: .quad 0

.section .text
.global open_csv, read_csv, get_column, parse_int
.global int_to_ascii, write_result, open_output, close_fd, newline

open_csv:
    mov x0, #-100
    ldr x1, =csv_filename
    mov x2, #0
    mov x3, #0
    mov x8, #56
    svc #0
    ret

read_csv:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    str x19, [sp, #16]

    bl open_csv
    cmp x0, #0
    blt rc_err

    mov x19, x0

    mov x0, x19
    adr x1, csv_buffer
    mov x2, #65536
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

    ldr x19, [sp, #16]
    ldp x29, x30, [sp], #32
    ret

rc_err:
    mov x0, #1
    adr x1, err_open
    mov x2, len_err_open
    mov x8, #64
    svc #0
    mov x0, #1
    mov x8, #93
    svc #0

rd_err:
    mov x0, #1
    adr x1, err_read
    mov x2, len_err_read
    mov x8, #64
    svc #0
    mov x0, #1
    mov x8, #93
    svc #0

get_column:
    stp x29, x30, [sp, #-64]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]

    mov x19, x0
    mov x20, x1
    mov x21, x2
    mov x22, x3
    adr x23, csv_buffer

gc_hdr:
    ldrb w9, [x23], #1
    cbz w9, gc_nf
    cmp w9, #10
    bne gc_hdr

    cbz x19, gc_row

gc_rows:
    ldrb w9, [x23], #1
    cbz w9, gc_nf
    cmp w9, #10
    bne gc_rows
    subs x19, x19, #1
    bne gc_rows

gc_row:
    cbz x20, gc_copy

gc_cols:
    ldrb w9, [x23], #1
    cbz w9, gc_nf
    cmp w9, #','
    bne gc_cols
    subs x20, x20, #1
    bne gc_cols

gc_copy:
    mov x24, #0
    sub x22, x22, #1

gc_loop:
    cmp x24, x22
    bge gc_done
    ldrb w9, [x23], #1
    cbz w9, gc_done
    cmp w9, #','
    beq gc_done
    cmp w9, #10
    beq gc_done
    cmp w9, #'$'
    beq gc_done
    strb w9, [x21, x24]
    add x24, x24, #1
    b gc_loop

gc_done:
    strb wzr, [x21, x24]
    mov x0, x24
    b gc_exit

gc_nf:
    mov x0, #0
    strb wzr, [x21]

gc_exit:
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #64
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
    add x0, x0, x0, lsl #2
    add x0, x0, x0
    add x0, x0, x3
    add x1, x1, #1
    b pi_d

pi_e:
    cbz x2, pi_ret
    neg x0, x0

pi_ret:
    ret

int_to_ascii:
    stp x29, x30, [sp, #-80]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    sub sp, sp, #32

    mov x19, x0
    mov x20, x1
    mov x21, sp
    mov x22, #0
    mov x24, #0

    cmp x19, #0
    bge ita_l
    neg x19, x19
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
    strb wzr, [x20, x23]
    mov x0, x23

    add sp, sp, #32
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #80
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