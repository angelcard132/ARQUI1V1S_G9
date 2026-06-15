// =====================================================================
//  modulo_4_prediccion.s
//  Astrid Vannesa Kim Ortiz
    //Carnet 202300685
//
//   la Formula

//    DIF             = XFINAL - XINICIAL
//    PROMEDIO_CAMBIO = DIF / (N - 1)         (N = 30)
//    PREDICCION      = XFINAL + PROMEDIO_CAMBIO
//


//    - AVG_CHANGE y NEXT_VALUE pueden tener decimales, por lo que
//      se calculan en formato fixed point con 2 decimales
//      se multiplica por 100 antes de dividir y al imprimir se
//      separa la parte entera de la parte decimal 




.section .data

out_filename:
    .asciz "resultado_prediccion.txt"

// Etiquetas de salida (formato MODULE=KEY\n / KEY=VALUE\n)
str_module:
    .asciz "MODULE=PREDICTION\n"
len_module = . - str_module - 1

str_initial:
    .asciz "INITIAL_VALUE="
len_initial = . - str_initial - 1

str_final:
    .asciz "FINAL_VALUE="
len_final = . - str_final - 1

str_diff:
    .asciz "TOTAL_DIFF="
len_diff = . - str_diff - 1

str_avg:
    .asciz "AVG_CHANGE="
len_avg = . - str_avg - 1

str_next:
    .asciz "NEXT_VALUE="
len_next = . - str_next - 1

dot_char:
    .asciz "."




.section .bss

// Buffer temporal para extraer cada valor de columna como texto
col_buf:
    .space 32

// Buffer temporal para convertir enteros a texto
ascii_buf:
    .space 32




.section .text
.global _start

// ---------------------------------------------------------------
// Constantes del modulo
//   N        = 30  (cantidad total de registros)
//   COLUMNA  = 1   (columna TEMP en lecturas.csv)

.equ N, 30
.equ COLUMNA, 1
.equ ESCALA, 100         // factor para 2 decimales fijos


_start:




    // 1) Leer todo el archivo lecturas.csv a memoria
    // -----------------------------------------------------------
    bl read_csv
    cmp x0, #0
    blt error_exit





    // 2) Obtener XINICIAL = valor de la columna en la fila 0
    // -----------------------------------------------------------

    mov x0, #0                  // fila 0 (primer registro)
    mov x1, #COLUMNA
    adr x2, col_buf      //aqui voy a guardar el valor de la columna
    mov x3, #32
    bl get_column 		//devuelve la cantidad de caracteres que copio
    cmp x0, #0
    beq error_exit               // si la columna esta vacia, me dara error

    adr x0, col_buf
    bl parse_int
    mov x21, x0                  // x21 = XINICIAL






    // 3) Obtener XFINAL = valor de la columna en la fila 29
    // -----------------------------------------------------------
    mov x0, #(N - 1)             // fila 29 (ultimo registro) se le resta 1 porque empieza de 0
    mov x1, #COLUMNA
    adr x2, col_buf
    mov x3, #32             // espacio del buffer
    bl get_column
    cmp x0, #0
    beq error_exit               // si la columna esta vacia

    adr x0, col_buf
    bl parse_int
    mov x22, x0                  // x22 = XFINAL





    // 4) DIF = XFINAL - XINICIAL
    // -----------------------------------------------------------
    sub x23, x22, x21            // x23 = DIF tambiénnn puede ser negativo



    // -----------------------------------------------------------
    // 5) PROMEDIO_CAMBIO = DIF / (N - 1)
    //    Calculado en fixed-point: AVG_SCALED = (DIF * 100) / 29
    //    AVG_SCALED esta escalado x100
    // -----------------------------------------------------------


    mov x9, #ESCALA
    mul x10, x23, x9             // x10 = DIF * 100
    mov x11, #(N - 1)            // x11 = 29
    sdiv x24, x10, x11           // x24 = AVG_SCALED = (DIF*100)/29





    // -----------------------------------------------------------
    // 6) PREDICCION = XFINAL + PROMEDIO_CAMBIO
    //    En fixed-point: NEXT_SCALED = XFINAL*100 + AVG_SCALED
    // -----------------------------------------------------------
    mul x12, x22, x9             // x12 = XFINAL * 100
    add x25, x12, x24             // x25 = NEXT_SCALED (escalado x100)






    // 7) Abrir archivo de salida
    // -----------------------------------------------------------
    adr x0, out_filename
    bl open_output
    cmp x0, #0
    blt error_exit
    mov x19, x0                  // x19 = fd de salida





    // 8) Escribir MODULE=PREDICTION
    // -----------------------------------------------------------
    mov x0, x19
    adr x1, str_module
    mov x2, #len_module
    bl write_result






    // 9) Escribir INITIAL_VALUE=<XINICIAL>
    // -----------------------------------------------------------
    mov x0, x19			//el fd del archivo abierto
    adr x1, str_initial        //donnde esta el valor INITIAL_VALUE
    mov x2, #len_initial	//el tamanio del archivo
    bl write_result

    mov x0, x21
    adr x1, ascii_buf		//aqui se guardara el valor ascii
    bl int_to_ascii
    mov x20, x0                  // x20 = longitud
    mov x0, x19
    adr x1, ascii_buf
    mov x2, x20
    bl write_result

    mov x0, x19
    bl newline







    // 10) Escribir FINAL_VALUE=<XFINAL>
    // -----------------------------------------------------------
    mov x0, x19
    adr x1, str_final
    mov x2, #len_final
    bl write_result

    mov x0, x22
    adr x1, ascii_buf
    bl int_to_ascii
    mov x20, x0

    mov x0, x19
    adr x1, ascii_buf
    mov x2, x20
    bl write_result

    mov x0, x19
    bl newline








    // -----------------------------------------------------------
    // 11) Escribir TOTAL_DIFF=<DIF>
    // -----------------------------------------------------------
    mov x0, x19
    adr x1, str_diff
    mov x2, #len_diff
    bl write_result

    mov x0, x23
    adr x1, ascii_buf
    bl int_to_ascii
    mov x20, x0

    mov x0, x19
    adr x1, ascii_buf
    mov x2, x20
    bl write_result

    mov x0, x19
    bl newline




    // 12) Escribir AVG_CHANGE=<entero>.<decimal>
    //     a partir de x24 = AVG_SCALED (escalado x100)
    // -----------------------------------------------------------
    mov x0, x19
    adr x1, str_avg
    mov x2, #len_avg
    bl write_result

    mov x0, x24
    bl write_fixed_point

    mov x0, x19
    bl newline







    // 13) Escribir NEXT_VALUE=<entero>.<decimal>
    //     a partir de x25 = NEXT_SCALED escalado x100
    // -----------------------------------------------------------
    mov x0, x19
    adr x1, str_next
    mov x2, #len_next
    bl write_result

    mov x0, x25
    bl write_fixed_point

    mov x0, x19
    bl newline





    // -----------------------------------------------------------
    // 14) Cerrar archivo y salir
    // -----------------------------------------------------------
    mov x0, x19
    bl close_fd

    mov x0, #0
    mov x8, #93                  // syscall exit
    svc #0

error_exit:
    mov x0, #1
    mov x8, #93
    svc #0







// write_fixed_point
//   Escribe un valor escalado x100 como "ENTERO.DD" en el fd x19
//   (subrutina propia del modulo, usa el fd  guardado en x19).
//
//   Parametros:
//     x0 = valor escalado x100 y puede ser negativo
//
//   Ejemplo: x0 = 3420  ->  escribe "34.20"
//
//   Usa registros callee-saved x26, x27, x28 los guarda y restaura
// =====================================================================

write_fixed_point:
    stp x29, x30, [sp, #-48]!
    mov x29, sp
    stp x26, x27, [sp, #16]
    str x28, [sp, #32]

    mov x26, x0                  // x26 = valor escalado (con signo)

    // Determinar signo y trabajar con valor absoluto
    mov x27, #0                  // x27 = flag negativo
    cmp x26, #0
    bge wfp_abs_ok
    neg x26, x26
    mov x27, #1

wfp_abs_ok:
    // parte entera = valor_abs / 100
    mov x9, #ESCALA
    udiv x28, x26, x9             // x28 = parte entera

    // Si el numero original era negativo, escribir '-' antes
    cbz x27, wfp_write_int
    mov x0, x19
    adr x1, neg_sign
    mov x2, #1
    bl write_result

wfp_write_int:
    // Escribir parte entera
    mov x0, x28
    adr x1, ascii_buf
    bl int_to_ascii
    mov x9, x0
    mov x0, x19
    adr x1, ascii_buf
    mov x2, x9
    bl write_result

    // Escribir el punto decimal
    mov x0, x19
    adr x1, dot_char
    mov x2, #1
    bl write_result

    // parte decimal = valor_abs mod 100
    mov x9, #ESCALA
    udiv x10, x26, x9
    msub x28, x10, x9, x26        // x28 = valor_abs - (parte_entera*100)

    // Asegurar 2 digitos: si x28 < 10, escribir '0' primero
    cmp x28, #10
    bge wfp_write_dec
    mov x0, x19
    adr x1, zero_char
    mov x2, #1
    bl write_result

wfp_write_dec:
    mov x0, x28
    adr x1, ascii_buf
    bl int_to_ascii
    mov x9, x0
    mov x0, x19
    adr x1, ascii_buf
    mov x2, x9
    bl write_result

    ldr x28, [sp, #32]
    ldp x26, x27, [sp, #16]
    ldp x29, x30, [sp], #48
    ret


.section .data
neg_sign:
    .asciz "-"
zero_char:
    .asciz "0"
