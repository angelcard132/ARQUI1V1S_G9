.global _start
.global main_loop

.bss
buffer:
    .skip 128

.text
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
    beq print_manual

    bl guardar_historial
    bl calcular_indicadores
    bl decidir_accion

    b main_loop

exit_ok:
    mov x0, #0
    mov x8, #93
    svc #0

exit_error:
    mov x0, #1
    mov x8, #93
    svc #0
