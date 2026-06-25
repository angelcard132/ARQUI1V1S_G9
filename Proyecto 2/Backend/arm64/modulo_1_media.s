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

.data
file_out: .asciz "arm/resultado_media.txt"

msg_mod: .ascii "MODULE=WEIGHTED_MEAN\n"
len_mod= . - msg_mod
msg_tot: .ascii "TOTAL_VALUES=30\n"
len_tot= . - msg_tot
msg_sumx: .ascii "SUM_Xi="
len_sumx= . - msg_sumx
msg_wsum: .ascii "WEIGHT_SUM="
len_wsum= . - msg_wsum
msg_mean: .ascii "WEIGHTED_MEAN="
len_mean = . - msg_mean

filename:
.asciz "lecturas.csv"

.bss
buffer:
.skip 4064

.text

_start:

// OPENAT(AT_FDCWD, "lecturas.csv", O_RDONLY, 0)
    mov x0, #-100       // AT_FDCWD (Directorio actual)
    ldr x1, =filename   // Dirección del nombre del archivo
    mov x2, #0          // O_RDONLY
    mov x3, #0          // Modo
    mov x8, #56         // syscall openat
    svc #0

    // Verificar si hubo error al abrir el archivo
    cmp x0, #0
    blt open_error

    // Guardar el descriptor de archivo en x19
    mov x19, x0

