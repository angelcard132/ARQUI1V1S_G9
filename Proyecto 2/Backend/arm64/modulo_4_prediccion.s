
//  modulo_4_prediccion.s
//  Astrid Vanesa Kim Ortiz
    //Carnet 202300685

//
//   la Formula

//    DIF             = XFINAL - XINICIAL
//    PROMEDIO_CAMBIO = DIF / (N - 1)         (N = 30)
//    PREDICCION      = XFINAL + PROMEDIO_CAMBIO
//


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




.section .bss

// Buffer temporal para extraer cada valor de columna como texto
col_buf:
    .space 32

// Buffer temporal para convertir enteros a texto
ascii_buf:
    .space 32




.section .text
.global _start




// Constantes del modulo
//   N        = 30  
//   COLUMNA  = 1

.equ N, 30
.equ COLUMNA, 2


_start:

    //  Leer el archivo lecturas.csv 
   // 
    bl read_csv
    cmp x0, #0
    blt error_exit


    // XINICIAL = valor de la columna en la fila 0

    mov x0, #0                  // fila 0 
    mov x1, #COLUMNA
    adr x2, col_buf      //aqui voy a guardar el valor de la columna
    mov x3, #32
    bl get_column 		//devuelve la cantidad de caracteres que copio
    cmp x0, #0
    beq error_exit               // error si la columna esta vacia

    adr x0, col_buf
    bl parse_int
    mov x21, x0                  // x21 = XINICIAL




    // XFINAL = valor de la columna en la fila 29

    mov x0, #(N - 1)             // fila 29 que es el ultimo registro se le resta 1 porque empieza de 0
    mov x1, #COLUMNA
    adr x2, col_buf
    mov x3, #32             // espacio del buffer
    bl get_column
    cmp x0, #0
    beq error_exit               // si la columna esta vacia

    adr x0, col_buf
    bl parse_int
    mov x22, x0                  // x22 = XFINAL





    // DIF = XFINAL - XINICIAL

    sub x23, x22, x21            // x23 = DIF tambiénnn puede ser negativo




    // PROMEDIO_CAMBIO = DIF / (N - 1)

    mov x11, #(N - 1)            // x11 = 29
    sdiv x24, x23, x11           



    //  PREDICCION = XFINAL + PROMEDIO_CAMBIO
            
    add x25, x22, x24      



    // Abrir archivo de salida

    adr x0, out_filename
    bl open_output
    cmp x0, #0
    blt error_exit
    mov x19, x0                  // x19 = fd de salida



    // Escribir MODULE=PREDICTION

    mov x0, x19
    adr x1, str_module
    mov x2, #len_module
    bl write_result



    // Escribir INITIAL_VALUE=<XINICIAL>

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



    // Escribir FINAL_VALUE=<XFINAL>

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




    //Escribir TOTAL_DIFF=<DIF>

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




    // Escribir AVG_CHANGE

    mov x0, x19
    adr x1, str_avg
    mov x2, #len_avg
    bl write_result

    mov x0, x24
    adr x1, ascii_buf
    bl int_to_ascii
    mov x20, x0
    
    mov x0, x19
    adr x1, ascii_buf
    mov x2, x20
    bl write_result

    mov x0, x19
    bl newline



    // Escribir NEXT_VALUE

    mov x0, x19
    adr x1, str_next
    mov x2, #len_next
    bl write_result

    mov x0, x25
    adr x1, ascii_buf
    bl int_to_ascii
    mov x20, x0
    
    mov x0, x19
    adr x1, ascii_buf
    mov x2, x20
    bl write_result

    mov x0, x19
    bl newline


    //Cerrar archivo y salir

    mov x0, x19
    bl close_fd

    mov x0, #0
    mov x8, #93         //salida
    svc #0

error_exit:
    mov x0, #1
    mov x8, #93
    svc #0
