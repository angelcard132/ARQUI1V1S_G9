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

    // si recibe n, termina
    ldrb w0, [x21]
    cmp w0, #'n'
    beq exit_ok

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

    // Si modo manual, no decide automáticamente
    cmp x28, #1
    beq print_green
    mov x0, #1
    ldr x1, =ok_msg
    mov x2, #len_ok_msg
    mov x8, #64
    svc #0
    bl guardar_historial
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

calcular_indicadores:
ok_msg:
    .ascii "INDICADORES_OK\n"
len_ok_msg = . - ok_msg

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
    ret
print_alarm:
    mov x0, #1
    ldr x1, =action_alarm
    mov x2, #len_alarm
    mov x8, #64
    svc #0
    ret

print_riego1:
    mov x0, #1
    ldr x1, =action_riego1
    mov x2, #len_riego1
    mov x8, #64
    svc #0
    ret

print_riego2:
    mov x0, #1
    ldr x1, =action_riego2
    mov x2, #len_riego2
    mov x8, #64
    svc #0
    ret

print_light:
    mov x0, #1
    ldr x1, =action_light
    mov x2, #len_light
    mov x8, #64
    svc #0
    ret

print_fan:
    mov x0, #1
    ldr x1, =action_fan
    mov x2, #len_fan
    mov x8, #64
    svc #0
    ret

print_green:
    mov x0, #1
    ldr x1, =action_green
    mov x2, #len_green
    mov x8, #64
    svc #0
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