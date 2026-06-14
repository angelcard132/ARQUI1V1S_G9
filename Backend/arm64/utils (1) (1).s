//  utils.s - Biblioteca comun ARM64/AArch64
//
//  Funciones que ofrece esta biblioteca:
//    open_csv        - abre lecturas.csv y retorna fd en x0
//    read_csv        - lee TODO el archivo en buffer global
//    get_column      - extrae columna N del registro I (base 0)
//    parse_int       - convierte string ASCII -> entero (x0)
//    int_to_ascii    - convierte entero -> string ASCII
//    write_result    - escribe string en archivo de salida
//    open_output     - abre/crea archivo de salida, retorna fd
//    close_fd        - cierra descriptor de archivo
//    newline         - escribe '\n' en fd dado
//
//  Registros:
//    x0-x7   parametros / retorno
//    x9-x15  temporales (caller-saved)
//    x19-x28 preservados (callee-saved)  
//    x29     frame pointer
//    x30     link register (lr)
//    sp      stack pointer
//
//  Compilacion:
//    as -o utils.o utils.s
//
//  Enlazar con el modulo especifico:
//    as -o modulo_X.o modulo_X.s
//    ld -o modulo_X modulo_X.o utils.o
.section .data

// Nombre del archivo de entrada
csv_filename:
    .asciz "lecturas.csv"

// Buffer de lectura del CSV
.align 8
.global csv_buffer
csv_buffer:
    .space 65536

// Tamano real del csv leido
.global csv_bytes_read
csv_bytes_read:
    .quad 0


.section .text

// Hacer visibles las funciones
.global open_csv
.global read_csv
.global get_column
.global parse_int
.global int_to_ascii
.global write_result
.global open_output
.global close_fd
.global newline


// open_csv
//   Abre lecturas.csv en modo solo lectura.
//   Parametros: ninguno
//   Retorna:    x0 = fd (negativo si hubo error)
open_csv:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    mov x0, #-100               // dirfd = AT_FDCWD
    adr x1, csv_filename        // pathname
    mov x2, #0                  // flags = O_RDONLY
    mov x3, #0                  // mode (ignorado en lectura)
    mov x8, #56                 // syscall openat
    svc #0                      // x0 = fd

    ldp x29, x30, [sp], #16
    ret


// read_csv
//   Abre lecturas.csv, lee su contenido completo en csv_buffer
//   y guarda el tamano en csv_bytes_read.
//   Parametros: ninguno
//   Retorna:    x0 = bytes leidos (negativo si hubo error)
read_csv:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    str x19, [sp, #16]

    // Abrir archivo
    bl open_csv                 // x0 = fd
    cmp x0, #0
    blt read_csv_error
    mov x19, x0                 // x19 = fd (callee-saved, sobrevive a la llamada)

    // Leer en csv_buffer
    mov x0, x19
    adr x1, csv_buffer
    mov x2, #65536
    mov x8, #63                 // syscall read
    svc #0                      // x0 = bytes leidos

    // Guardar bytes leidos
    adr x9, csv_bytes_read
    str x0, [x9]

    // Cerrar fd
    mov x0, x19
    bl close_fd

    // Retornar bytes leidos (recargar direccion por seguridad)
    adr x9, csv_bytes_read
    ldr x0, [x9]
    b read_csv_done

read_csv_error:
    mov x0, #-1

read_csv_done:
    ldr x19, [sp, #16]
    ldp x29, x30, [sp], #32
    ret


// get_column
//   Extrae el valor ASCII de una columna especifica de una fila
//   del CSV (ya cargado en csv_buffer).
//
//   El CSV tiene header en la fila 0; los datos empiezan en fila 1.
//   Formato: ID,TEMP,HUM_AIRE,HUM_SUELO_1,HUM_SUELO_2,LUZ,GAS,RIEGO_1,RIEGO_2
//            col0 col1 col2     col3        col4      col5 col6  col7   col8
//
//   Parametros:
//     x0 = numero de fila  (0-based, SIN contar el header)
//          -> fila real en el archivo = x0 + 1
//     x1 = numero de columna (0-based)
//     x2 = puntero al buffer de salida (donde se escribira el string)
//     x3 = tamano maximo del buffer de salida
//
//   Retorna:
//     x0 = longitud del string copiado (0 si no encontrado)
//     El buffer x2 contiene el valor ASCII terminado en '\0'
get_column:
    stp x29, x30, [sp, #-80]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    stp x23, x24, [sp, #48]
    str x25, [sp, #64]

    mov x19, x0                 // x19 = fila objetivo (0-based, sin header)
    mov x20, x1                 // x20 = columna objetivo
    mov x21, x2                 // x21 = buffer salida
    mov x22, x3                 // x22 = tamano buffer

    // Puntero al inicio de csv_buffer
    adr x23, csv_buffer         // x23 = ptr actual en buffer

    // Saltar header (fila 0 del archivo): avanzar hasta '\n'
skip_header:
    ldrb w9, [x23]
    cbz w9, gc_not_found         // fin de archivo inesperado
    add x23, x23, #1
    cmp w9, #0x0A                // '\n'
    bne skip_header
    // x23 ahora apunta al primer caracter de los datos

    // Saltar x19 filas de datos
    cbz x19, gc_on_target_row
gc_skip_rows:
    ldrb w9, [x23]
    cbz w9, gc_not_found
    add x23, x23, #1
    cmp w9, #0x0A
    bne gc_skip_rows
    subs x19, x19, #1
    bne gc_skip_rows             // si x19>0, seguir saltando

gc_on_target_row:
    // x23 apunta al inicio de la fila objetivo.
    // Saltar x20 columnas (separadas por ',')
    cbz x20, gc_copy_value
    mov x9, x20                  // contador de columnas a saltar
gc_skip_cols:
    ldrb w10, [x23]
    cbz w10, gc_not_found
    add x23, x23, #1
    cmp w10, #','
    bne gc_skip_cols
    subs x9, x9, #1
    bne gc_skip_cols

gc_copy_value:
    // Copiar hasta encontrar ',' o '\n' o '\r' o '\0'
    // Se deja siempre 1 byte libre para el '\0' final.
    mov x24, #0                  // x24 = indice en buffer salida
    sub x25, x22, #1               // x25 = tamano util (tamano - 1, para el '\0')
gc_copy_loop:
    cmp x24, x25
    bge gc_copy_done             // buffer lleno (sin contar el '\0')
    ldrb w9, [x23]
    cbz w9, gc_copy_done
    cmp w9, #','
    beq gc_copy_done
    cmp w9, #0x0A                // '\n'
    beq gc_copy_done
    cmp w9, #0x0D                // '\r'
    beq gc_copy_done
    strb w9, [x21, x24]
    add x23, x23, #1
    add x24, x24, #1
    b gc_copy_loop

gc_copy_done:
    strb wzr, [x21, x24]         // null-terminar
    mov x0, x24                  // retornar longitud
    b gc_exit

gc_not_found:
    mov x0, #0
    strb wzr, [x21]

gc_exit:
    ldr x25, [sp, #64]
    ldp x23, x24, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #80
    ret


// parse_int
//   Convierte string ASCII de digitos a entero de 64 bits.
//   Soporta numeros negativos con '-' al inicio.
//
//   Parametros:
//     x0 = puntero al string ASCII
//   Retorna:
//     x0 = valor entero
parse_int:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    mov x1, x0                  // x1 = ptr al string
    mov x0, #0                  // x0 = resultado acumulado
    mov x2, #0                  // x2 = signo (0=positivo, 1=negativo)

    // Verificar signo
    ldrb w3, [x1]
    cmp w3, #'-'
    bne pi_digits
    mov x2, #1
    add x1, x1, #1

pi_digits:
    ldrb w3, [x1]
    cmp w3, #'0'
    blt pi_done
    cmp w3, #'9'
    bgt pi_done

    // digito valido: acumulado = acumulado*10 + digito
    sub w3, w3, #'0'             // valor del digito en w3

    // x0 = x0*10  =>  x0*8 + x0*2  (sin usar mul, sin registros sucios)
    lsl x4, x0, #3               // x4 = x0*8
    lsl x5, x0, #1               // x5 = x0*2
    add x0, x4, x5                // x0 = x0*10
    add x0, x0, x3                // x0 += digito

    add x1, x1, #1
    b pi_digits

pi_done:
    cbz x2, pi_positive
    neg x0, x0

pi_positive:
    ldp x29, x30, [sp], #16
    ret


// int_to_ascii
//   Convierte entero de 64 bits a string ASCII decimal.
//   Soporta negativos.
//
//   Parametros:
//     x0 = valor entero
//     x1 = puntero al buffer de salida
//   Retorna:
//     x0 = longitud del string (sin '\0')
//     buffer en x1 contiene el numero terminado en '\0'
int_to_ascii:
    stp x29, x30, [sp, #-64]!
    mov x29, sp
    stp x19, x20, [sp, #16]
    stp x21, x22, [sp, #32]
    str x23, [sp, #48]

    mov x19, x0                 // x19 = valor
    mov x20, x1                 // x20 = buffer destino

    // Buffer temporal de digitos (max 20 digitos para 64-bit)
    sub sp, sp, #32             // 32 para mantener alineacion de 16 bytes
    mov x21, sp                 // x21 = buffer temporal
    mov x22, #0                 // x22 = contador digitos

    // Manejar negativos
    mov x9, #0                  // x9 = flag negativo
    cmp x19, #0
    bge ita_positive
    neg x19, x19
    mov x9, #1

ita_positive:
    // Caso especial: valor == 0
    cbnz x19, ita_loop
    mov w10, #'0'
    strb w10, [x21]
    mov x22, #1
    b ita_reverse

ita_loop:
    cbz x19, ita_reverse
    mov x11, #10
    udiv x12, x19, x11           // x12 = x19 / 10
    msub x13, x12, x11, x19      // x13 = x19 mod 10
    add w13, w13, #'0'
    strb w13, [x21, x22]
    add x22, x22, #1
    mov x19, x12
    b ita_loop

ita_reverse:
    // Los digitos quedaron al reves; copiarlos invertidos a x20
    mov x23, #0                  // indice destino
    cbz x9, ita_rev_loop         // si no es negativo, saltar el signo
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
    strb wzr, [x20, x23]         // null-terminate
    mov x0, x23                  // retornar longitud

    add sp, sp, #32
    ldr x23, [sp, #48]
    ldp x21, x22, [sp, #32]
    ldp x19, x20, [sp, #16]
    ldp x29, x30, [sp], #64
    ret


// open_output
//   Crea o sobreescribe un archivo de salida .txt
//
//   Parametros:
//     x0 = puntero al nombre del archivo (string ASCII)
//   Retorna:
//     x0 = fd (negativo si hubo error)
open_output:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    mov x1, x0                  // x1 = pathname
    mov x0, #-100                // dirfd = AT_FDCWD
    mov x2, #0x241               // flags: O_WRONLY|O_CREAT|O_TRUNC (1|64|512)
    mov x3, #0x1A4                // permisos 0644 en hexadecimal
    mov x8, #56                  // syscall openat
    svc #0

    ldp x29, x30, [sp], #16
    ret


// write_result
//   Escribe un string en un fd abierto.
//
//   Parametros:
//     x0 = fd
//     x1 = puntero al string
//     x2 = longitud del string
//   Retorna:
//     x0 = bytes escritos
write_result:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    mov x8, #64                  // syscall write
    svc #0

    ldp x29, x30, [sp], #16
    ret


// close_fd
//   Cierra un descriptor de archivo.
//
//   Parametros:
//     x0 = fd
//   Retorna:
//     x0 = resultado de close (0 = exito)
close_fd:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    mov x8, #57                  // syscall close
    svc #0

    ldp x29, x30, [sp], #16
    ret


// newline
//   Escribe un caracter '\n' en el fd dado.
//
//   Parametros:
//     x0 = fd
//   Retorna:
//     x0 = bytes escritos (1 si exito)
newline:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    str x19, [sp, #16]

    mov x19, x0                  // guardar fd

    mov w9, #0x0A                 // '\n'
    strb w9, [sp, #24]            // usar espacio del propio frame

    mov x0, x19
    add x1, sp, #24
    mov x2, #1
    mov x8, #64                   // syscall write
    svc #0

    ldr x19, [sp, #16]
    ldp x29, x30, [sp], #32
    ret
