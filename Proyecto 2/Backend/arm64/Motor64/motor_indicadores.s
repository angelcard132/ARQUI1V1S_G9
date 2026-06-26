.global hist_count
.global hist_index
.global guardar_historial
.global calcular_indicadores

.bss
temp_buf:
    .skip 40
suelo1_buf:
    .skip 40
suelo2_buf:
    .skip 40
luz_buf:
    .skip 40
gas_buf:
    .skip 40

hist_count:
    .skip 8
hist_index:
    .skip 8

.text

guardar_historial:
    ldr x0, =hist_index
    ldr x1, [x0]            // x1 = índice actual

    lsl x2, x1, #3          

    ldr x3, =temp_buf
    str x22, [x3, x2]

    ldr x3, =suelo1_buf
    str x24, [x3, x2]

    ldr x3, =suelo2_buf
    str x25, [x3, x2]

    ldr x3, =luz_buf
    str x26, [x3, x2]

    ldr x3, =gas_buf
    str x27, [x3, x2]

    // hist_index = (hist_index + 1) % 5
    add x1, x1, #1
    cmp x1, #5
    blt guardar_index
    mov x1, #0

guardar_index:
    str x1, [x0]

    // hist_count aumenta hasta máximo 5
    ldr x0, =hist_count
    ldr x1, [x0]
    cmp x1, #5
    bge guardar_done
    add x1, x1, #1
    str x1, [x0]

guardar_done:
    ret

calcular_indicadores:
    stp x29, x30, [sp, #-16]! 
    mov x29, sp

    ldr x0, =hist_count
    ldr x19, [x0]           

    cmp x19, #0
    beq indicadores_cero

    // GAS: promedio y amplitud
    ldr x20, =gas_buf
    bl promedio_amplitud
    mov x9, x0              // avg gas
    mov x10, x1             // amp gas

    // SUELO1: promedio y tendencia
    ldr x20, =suelo1_buf
    bl promedio_tendencia
    mov x11, x0             // avg suelo1
    mov x12, x1             // trend suelo1

    // SUELO2
    ldr x20, =suelo2_buf
    bl promedio_tendencia
    mov x13, x0
    mov x14, x1

    // LUZ
    ldr x20, =luz_buf
    bl promedio_tendencia
    mov x15, x0
    mov x16, x1

    // TEMP
    ldr x20, =temp_buf
    bl promedio_tendencia
    mov x17, x0
    mov x18, x1

    ldp x29, x30, [sp], #16
    ret

indicadores_cero:
    mov x9, #0
    mov x10, #0
    mov x11, #0
    mov x12, #0
    mov x13, #0
    mov x14, #0
    mov x15, #0
    mov x16, #0
    mov x17, #0
    mov x18, #0

    ldp x29, x30, [sp], #16
    ret

promedio_tendencia:
    mov x2, #0              // i
    mov x3, #0              // suma

    ldr x4, [x20]           // primero
    mov x5, x4              // ultimo temporal

pt_loop:
    cmp x2, x19
    bge pt_done

    lsl x6, x2, #3
    ldr x7, [x20, x6]

    add x3, x3, x7
    mov x5, x7

    add x2, x2, #1
    b pt_loop

pt_done:
    udiv x0, x3, x19
    sub x1, x5, x4
    ret

promedio_amplitud:
    mov x2, #0
    mov x3, #0

    ldr x4, [x20]           // min
    mov x5, x4              // max

pa_loop:
    cmp x2, x19
    bge pa_done

    lsl x6, x2, #3
    ldr x7, [x20, x6]

    add x3, x3, x7

    cmp x7, x4
    bge pa_check_max
    mov x4, x7

pa_check_max:
    cmp x7, x5
    ble pa_next
    mov x5, x7

pa_next:
    add x2, x2, #1
    b pa_loop

pa_done:
    udiv x0, x3, x19
    sub x1, x5, x4
    ret
