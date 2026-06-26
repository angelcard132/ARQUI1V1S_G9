.global int_to_ascii_local

.text

int_to_ascii_local:
    // x0 = numero
    // x1 = buffer
    // retorna x0 = longitud

    stp x29, x30, [sp, #-96]!
    mov x29, sp

    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    str x23, [sp, #48]

    mov x19, x0
    mov x20, x1

    sub sp, sp, #32
    mov x21, sp
    mov x22, #0

    mov x9, #0
    cmp x19, #0
    bge ita_positive

    neg x19, x19
    mov x9, #1

ita_positive:
    cbnz x19, ita_loop

    mov w10, #'0'
    strb w10, [x21]
    mov x22, #1
    b ita_reverse

ita_loop:
    cbz x19, ita_reverse

    mov x11, #10
    udiv x12, x19, x11
    msub x13, x12, x11, x19
    add w13, w13, #'0'
    strb w13, [x21, x22]
    add x22, x22, #1
    mov x19, x12
    b ita_loop

ita_reverse:
    mov x23, #0

    cbz x9, ita_rev_loop
    mov w10, #'-'
    strb w10, [x20]
    add x23, x23, #1

ita_rev_loop:
    cbz x22, ita_done
    sub x22, x22, #1
    ldrb w10, [x21, x22]
    strb w10, [x20, x23]
    add x23, x23, #1
    b ita_rev_loop

ita_done:
    strb wzr, [x20, x23]
    mov x0, x23

    add sp, sp, #32

    ldp x19, x20, [sp, #16]
    ldp x21, x22, [sp, #32]
    ldr x23, [sp, #48]

    ldp x29, x30, [sp], #96
    ret
