.data
newline: .ascii "\n"

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

.text
.global _start
.include "atoi_num.s"

_start:

main_loop:
    // read(stdin, buffer, 128)
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
    // TEMP,HUM_AIRE,SOIL1,SOIL2,LUZ,GAS,MODO

    bl atoi_csv
    cbz x7, print_error
    mov x22, x10        // TEMP

    bl atoi_csv
    cbz x7, print_error
    mov x23, x10        // HUM_AIRE

    bl atoi_csv
    cbz x7, print_error
    mov x24, x10        // SOIL1

    bl atoi_csv
    cbz x7, print_error
    mov x25, x10        // SOIL2

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

    // Prioridad 1: gas alto
    cmp x27, #400
    bge print_alarm

    // Prioridad 2: suelo1 seco
    cmp x24, #35
    blt print_riego1

    // Prioridad 3: suelo2 seco
    cmp x25, #35
    blt print_riego2

    // Prioridad 4: luz baja
    cmp x26, #300
    blt print_light

    // Prioridad 5: temperatura alta
    cmp x22, #30
    bge print_fan

    b print_green

print_alarm:
    mov x0, #1
    ldr x1, =action_alarm
    mov x2, #len_alarm
    mov x8, #64
    svc #0
    b main_loop

print_riego1:
    mov x0, #1
    ldr x1, =action_riego1
    mov x2, #len_riego1
    mov x8, #64
    svc #0
    b main_loop

print_riego2:
    mov x0, #1
    ldr x1, =action_riego2
    mov x2, #len_riego2
    mov x8, #64
    svc #0
    b main_loop

print_light:
    mov x0, #1
    ldr x1, =action_light
    mov x2, #len_light
    mov x8, #64
    svc #0
    b main_loop

print_fan:
    mov x0, #1
    ldr x1, =action_fan
    mov x2, #len_fan
    mov x8, #64
    svc #0
    b main_loop

print_green:
    mov x0, #1
    ldr x1, =action_green
    mov x2, #len_green
    mov x8, #64
    svc #0
    b main_loop

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