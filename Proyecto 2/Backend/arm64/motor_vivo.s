.data
err_input:
    .ascii "ERROR\n"
len_err_input = . - err_input

action_alarm:
    .ascii "ACTION=ALARM_ON\n"
len_alarm = . - action_alarm

action_riego1:
    .ascii "ACTION=RIEGO_1_ON\n"
len_riego1 = . - action_riego1

action_riego2:
    .ascii "ACTION=RIEGO_2_ON\n"
len_riego2 = . - action_riego2

action_light:
    .ascii "ACTION=LIGHT_ON\n"
len_light = . - action_light

action_fan:
    .ascii "ACTION=FAN_ON\n"
len_fan = . - action_fan

action_green:
    .ascii "ACTION=LED_GREEN\n"
len_green = . - action_green

.bss
buffer:
    .skip 128

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
.global _start
.include "atoi_num.s"

_start:
    ldr x0, =hist_count
    str xzr, [x0]

    ldr x0, =hist_index
    str xzr, [x0]
    mov x5, #10

main_loop:
    mov x0, #0
    ldr x1, =buffer
    mov x2, #128
    mov x8, #63
    svc #0

    cmp x0, #0
    beq exit_ok
    ble exit_error

    ldr x21, =buffer
    add x23, x21, x0        // x23 = fin del buffer
    mov x22, x21  

    // si recibe n, termina
    ldrb w0, [x21]
    cmp w0, #'n'
    beq exit_ok

    mov x5, #10  
    // Formato:
    // TEMP,HUM_AIRE,SUELO1,SUELO2,LUZ,GAS,MODO

    bl atoi_csv
    cbz x7, print_error
    mov x22, x10        // TEMP

    bl atoi_csv
    cbz x7, print_error
    mov x23, x10        // HUM_AIRE

    bl atoi_csv
    cbz x7, print_error
    mov x24, x10        // SUELO1

    bl atoi_csv
    cbz x7, print_error
    mov x25, x10        // SUELO2

    bl atoi_csv
    cbz x7, print_error
    mov x26, x10        // LUZ

    bl atoi_csv
    cbz x7, print_error
    mov x27, x10        // GAS

    bl atoi_csv
    cbz x7, print_error
    mov x28, x10        // MODO

    // Si está en modo manual, no decide acciones automáticas
    cmp x28, #1
    beq print_green

    bl guardar_historial
    bl calcular_indicadores
    bl decidir_accion

    b main_loop

// Esta parte de guardar_historial, guarda la lectura actual en buffers circulares de 5 posiciones
// x22 TEMP
// x24 SUELO1
// x25 SUELO2
// x26 LUZ
// x27 GAS
guardar_historial:
    ldr x0, =hist_index
    ldr x1, [x0]            // x1 = índice actual 0..4

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

// Calcula:
// x9  = promedio GAS
// x10 = amplitud GAS
// x11 = promedio SUELO1
// x12 = tendencia SUELO1
// x13 = promedio SUELO2
// x14 = tendencia SUELO2
// x15 = promedio LUZ
// x16 = tendencia LUZ
// x17 = promedio TEMP
// x18 = tendencia TEMP
calcular_indicadores:
    stp x29, x30, [sp, #-16]! //pila para entrar en la funcion
    mov x29, sp

    ldr x0, =hist_count
    ldr x19, [x0]           // x19 = N

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

// promedio_tendencia
// Entrada:
// x20 = puntero al buffer
// x19 = cantidad N
//
// Retorna:
// x0 = promedio
// x1 = tendencia acumulada = ultimo - primero
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

// promedio_amplitud
// Entrada:
// x20 = puntero al buffer
// x19 = cantidad N
// Retorna:
// x0 = promedio
// x1 = amplitud = max - min
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



// Prioridades
// 1 GAS alto o amplitud GAS alta = ALARM_ON
// 2 SUELO1 bajo y tendencia descendente = RIEGO_1_ON
// 3 SUELO2 bajo y tendencia descendente = RIEGO_2_ON
// 4 LUZ baja y tendencia descendente = LIGHT_ON
// 5 TEMP alta y tendencia ascendente = FAN_ON
// 6 LED_GREEN
decidir_accion:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    // GAS promedio alto o amplitud alta
    cmp x9, #400
    bge print_alarm

    cmp x10, #150
    bge print_alarm

    // SUELO1 promedio bajo y tendencia descendente
    cmp x11, #35
    bge check_suelo2
    cmp x12, #0
    blt print_riego1

check_suelo2:
    cmp x13, #35
    bge check_luz
    cmp x14, #0
    blt print_riego2

check_luz:
    cmp x15, #300
    bge check_temp
    cmp x16, #0
    blt print_light

check_temp:
    cmp x17, #30
    blt print_green
    cmp x18, #0
    bgt print_fan

    b print_green


print_alarm:
    mov x0, #1
    ldr x1, =action_alarm
    mov x2, #len_alarm
    mov x8, #64
    svc #0
    ldp x29, x30, [sp], #16
    ret

print_riego1:
    mov x0, #1
    ldr x1, =action_riego1
    mov x2, #len_riego1
    mov x8, #64
    svc #0
    ldp x29, x30, [sp], #16
    ret

print_riego2:
    mov x0, #1
    ldr x1, =action_riego2
    mov x2, #len_riego2
    mov x8, #64
    svc #0
    ldp x29, x30, [sp], #16
    ret

print_light:
    mov x0, #1
    ldr x1, =action_light
    mov x2, #len_light
    mov x8, #64
    svc #0
    ldp x29, x30, [sp], #16
    ret

print_fan:
    mov x0, #1
    ldr x1, =action_fan
    mov x2, #len_fan
    mov x8, #64
    svc #0
    ldp x29, x30, [sp], #16
    ret

print_green:
    mov x0, #1
    ldr x1, =action_green
    mov x2, #len_green
    mov x8, #64
    svc #0
    ldp x29, x30, [sp], #16
    ret

print_error:
    mov x0, #1
    ldr x1, =err_input
    mov x2, #len_err_input
    mov x8, #64
    svc #0
    b main_loop

exit_ok:
    mov x0, #0
    mov x8, #93
    svc #0

exit_error:
    mov x0, #1
    mov x8, #93
    svc #0