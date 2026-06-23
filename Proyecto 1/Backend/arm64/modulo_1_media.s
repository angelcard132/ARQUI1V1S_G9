// ==============================================================================
// Módulo 1
// Dina Rebeca Pérez Bátres
// ==============================================================================

.global _start

.extern read_csv
.extern get_column
.extern parse_int
.extern int_to_ascii
.extern open_output
.extern write_result
.extern close_fd
.extern newline

.section .data
file_out:   .asciz "resultado_media.txt"

msg_mod:    .ascii "MODULE=WEIGHTED_MEAN\n"
len_mod = . - msg_mod
msg_tot:    .ascii "TOTAL_VALUES=30\n"
len_tot = . - msg_tot
msg_sumx:   .ascii "SUM_X="
len_sumx = . - msg_sumx
msg_wsum:   .ascii "WEIGHT_SUM="
len_wsum = . - msg_wsum
msg_mean:   .ascii "WEIGHTED_MEAN="
len_mean = . - msg_mean

.section .bss
str_buffer: .space 64

.section .text
_start:
    ldr x0, [sp]            
    cmp x0, 2               
    b.lt default_col        

    ldr x0, [sp, 16]        
    bl parse_int            
    mov x28, x0             
    b iniciar_programa

default_col:
    mov x28, 1              

iniciar_programa:
    bl read_csv

    // Inicialización de registros acumuladores
    mov x19, 0
    mov x20, 0
    mov x21, 0
    mov x22, 0

loop_lectura:
    cmp x19, 30
    b.eq calcular_media

    mov x0, x19
    mov x1, x28             
    adr x2, str_buffer
    mov x3, 64
    bl get_column

    adr x0, str_buffer
    mov x9, 1               
    bl parse_int
    mov x23, x0

    add x24, x19, 1         

    add x20, x20, x23       
    add x21, x21, x24       

    mul x25, x23, x24       
    add x22, x22, x25       

    add x19, x19, 1
    b loop_lectura

calcular_media:
    udiv x26, x22, x21

escribir_resultados:
    adr x0, file_out
    bl open_output
    mov x27, x0

    // Escritura: MODULE=WEIGHTED_MEAN
    mov x0, x27
    adr x1, msg_mod
    mov x2, len_mod
    bl write_result

    // Escritura: TOTAL_VALUES=30
    mov x0, x27
    adr x1, msg_tot
    mov x2, len_tot
    bl write_result

    // Escritura: SUM_X=
    mov x0, x27
    adr x1, msg_sumx
    mov x2, len_sumx
    bl write_result

    // Valor de SUM_X
    mov x0, x20
    adr x1, str_buffer
    bl int_to_ascii
    mov x2, x0
    mov x0, x27
    adr x1, str_buffer
    bl write_result
    mov x0, x27
    bl newline

    // Escritura: WEIGHT_SUM=
    mov x0, x27
    adr x1, msg_wsum
    mov x2, len_wsum
    bl write_result

    // Valor de WEIGHT_SUM
    mov x0, x21
    adr x1, str_buffer
    bl int_to_ascii
    mov x2, x0
    mov x0, x27
    adr x1, str_buffer
    bl write_result
    mov x0, x27
    bl newline

    // Escritura: WEIGHTED_MEAN=
    mov x0, x27
    adr x1, msg_mean
    mov x2, len_mean
    bl write_result

    // Valor de WEIGHTED_MEAN
    mov x0, x26
    adr x1, str_buffer
    bl int_to_ascii
    mov x2, x0
    mov x0, x27
    adr x1, str_buffer
    bl write_result
    mov x0, x27
    bl newline

    // Cerrar archivo
    mov x0, x27
    bl close_fd

salir:
    mov x8, 93
    mov x0, 0
    svc 0


