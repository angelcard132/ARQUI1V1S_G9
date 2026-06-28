// Rutina 3: Prediccion futura por regresion 
//Tuli Pirir 
.section .data
msg_inicio:     .asciz "Leyendo CsV ...\n"
len_inicio = . - msg_inicio -1
msg_error_arg:  .asciz "Error: Faltan argumentos. COLUMNA FILA_INICIO FILA_FIN [K]\n"
len_error_arg = . - msg_error_arg -1 
// archivo de salida 
out_filename:   .asciz "resultado_prediccion.txt"
// salidas 
str_calc:       .asciz "CALC=PREDICTION\n"
len_calc = . - str_calc -1

str_col:        .asciz "COLUMN="
len_col =  .- str_col -1

str_wstart:     .asciz "WINDOW_START="
len_wstart = .- str_wstart -1

str_wend:       .asciz "WINDOW_END="
len_wend = . - str_wend -1

str_count:      .asciz "COUNT="
len_count = . - str_count -1 

str_k:          .asciz "K="
len_k = . - str_k -1 

str_slope:      .asciz "SLOPE_x100="
len_slope = . - str_slope -1 

str_intercept:  .asciz "INTERCEPT_x100="
len_intercept = . - str_intercept -1 

str_predicted:  .asciz "PREDICTED_K="
len_predicted = . - str_predicted -1 

str_status:     .asciz "STATUS=OK\n"
len_status = . - str_status - 1

// errores 
str_status_err: .asciz "STATUS=ERROR\n"
len_status_err = . - str_status_err -1 

str_err_type:   .asciz "ERROR=INVALID_INPUT\n"
len_err_type = .- str_err_detail -1

str_err_detail: .asciz "DETAIL=INVALID_DATA_OR_FIELDS\n"
len_err_detail = . - str_err_detail -1

.align 8
.section .bss
ascii_buf:      .space 32       // buffer temporal para parse
values_array:   .space 8000     // almacenamiento

.section .text
.global _start

// funciones deutils.s
.extern read_csv
.extern read_range_column
.extern parse_int
.extern open_output
.extern write_result
.extern int_to_ascii
.extern newline
.extern close_fd

_start:
    //argumentos iniciales
    ldr x0, [sp]            // cantidad de argumentos
    cmp x0, #4              //l -inicio -fin
    blt error_argumentos
    //extraer datos 
    ldr x0, [sp, #16]       //  argv[1]  f_ini
    bl parse_int           
    mov x20, x0             // f_inicioe en  x20

    ldr x0, [sp, #24]       // x0 = argv[2] 
    bl parse_int            
    mov x21, x0             // f_ final  en x21

    ldr x0, [sp, #32]       // x0 = argv[3]
    bl parse_int            
    mov x19, x0             // col en 19

    //cantidad de elementos 
    sub x0, x21, x20        // x0 = fin - inicio
    mov x25, x0
    //  si   K  en argv[4]
    ldr x0, [sp]            // cargar  argc
    cmp x0, #5              //  parametro opcional K
    blt usar_k_por_defecto

    ldr x0, [sp, #40]       // x0 = argv[4]  desplazamiento K
    bl parse_int            
    mov x26, x0             //  K  en x26
    b inicio_procesamiento

usar_k_por_defecto:
    mov x26, #5             // por defecto K = 5 

inicio_procesamiento:
   // inicio 
    mov x0, #1
    ldr x1, =msg_inicio
    mov x2, #len_inicio
    bl write_result

    // cargar archivo 
    mov x0, #0            
    bl read_csv
    cmp x0, #0               
    blt reporte_error  //Manejo de erroes 

    // datos para trabajar en el buffer arreglo
    mov x0, x20             // FILA_INICIO
    mov x1, x21             // FILA_FIN
    mov x2, x19             // COL 

    ldr x3, =values_array   //  putero al espacio deonde se guardo 
    bl read_range_column    // se llena con info  

    cmp x0, #0              // error rango
    ble reporte_error // 

    //  sumatorias 
    mov x0, x25             //  N 
    ldr x1, =values_array   // datos 
    
    // sumatorias para trabajar despues con la formula 
    /*
        x0=sum_y  --   suma  de todos los datos
        x1=sum_x -- suamatoria de n 
        x2=sum_xy -- suma de la multiplicación cruzada
        x3=sum_xx  -- suma de las posiciones al cuadrado
    */
    bl calc_sumatorias     
    // coeficientes de la recta 
    mov x4, x25  //  m a x4 
    /*
        x0 = M_x100 = pendient * 100.  
        x1 =B_x100 =  intercepto * 100.  
    */
    bl ejecutar_regresion   
    mov x17, x0             //  pendiente en x17
    mov x18, x1             //  intercepto  en x18

    // prediccion 
    mov x0, x17             //  pendiente m
    mov x2, x25             //  N
    mov x3, x26             //  K
    bl predecir_futuro      //  x0 = Valor futuro 
    mov x19, x0             // valor final  en x19
    //  reporte de texto
    bl guardar_reporte
    b terminar

error_argumentos:
    mov x0, #1
    ldr x1, =msg_error_arg
    mov x2, #len_error_arg
    bl write_result
    ble reporte_error
terminar:
    mov x8, #93             // syscall exit
    svc #0

/*
  sumatorias calculos 
  entra  
    x0 = N 
    x1 = putero inicio del aregla 
 sale
   x0 = sum_y
   x1 = sum_x
   x2 = sum_xy
   x3 = sum_xx
*/
calc_sumatorias:
    stp x19, x20, [sp, #-32]! //preindex 
    stp x21, x22, [sp, #16]

    // variables locales
    mov x19, x0             // x19 =  N 
    mov x20, x1             // x20 =  base del arreglo de datos
    mov x12, #0             // x12 =  iterna

    // retisros limpios 
    mov x0, #0             
    mov x1, #0             
    mov x2, #0              
    mov x3, #0              

sumatoria_loop:
    cmp x12, x19            // iterador 
    bge fin_sumatorias      
    //  carga datos del arreglo
    // x12 * 8 (lsl #3) 
    ldr x10, [x20, x12, lsl #3] // x10 = y_i  desde el arreglo
    mov x9, x12                 // x9  = x_i indice

    // sum_y= x0 y sum_x = x1
    add x0, x0, x10             // x0 = suma_y = x0 + x10
    add x1, x1, x9              // x0 = suma_x = x1 + x9
    
    //sum_xy sumatoria curzada 
    // multiplica 
    mul x21, x9, x10            // x21 = x_i * y_i = x9*x10
    // suma 
    add x2, x2, x21             // x2= suma_xy = x21 + x21

    //sum_xx sumatoria de cuadrados 
    mul x22, x9, x9            // x22 = x_i * x_i
    add x3, x3, x22             // x3=  suma_xx = x3 + x22

    // siguiente elemento
    add x12, x12, #1            // i = i + 1
    b sumatoria_loop      //  ciclo

fin_sumatorias:
    // restaurar  los registros en la pila 
    ldp x21, x22, [sp, #16]
    ldp x19, x20, [sp], #32
    ret

ejecutar_regresion:

    /*
        ejecutar_regresion
        entra
            x0 = sum_y
            x1 = sum_x
            x2 = sum_xy
            x3 = sum_xx
            x4 = N
        sale 
        x0 = slope_x100
            x1 = intercept_x100
    */

    
//  CALCULO  PENDIENTE slope_x100 = m
// slope_x100 = 100 * (N * sum_xy - sum_x * sum_y) / (N * sum_xx - sum_x * sum_x)
m_numerador:
    // fomula : numerador_M = N * suma_xy - suma_x * suma_y
    mul x9, x4, x2          // x9 = N * suma_xy
    mul x10, x1, x0         // x10 = suma_x * suma_y
    sub x9, x9, x10         // x9 = (N * suma_xy) - (suma_x * suma_y)
    //  por 100 
    mov x11, #100
    mul x9, x9, x11         // x9 = numerador_M * 100
m_denominador:
    // formula : denominador_M = N * suma_xx - (suma_x)^2
    mul x12, x4, x3         // x12 = N * suma_xx
    mul x13, x1, x1         // x13 = suma_x * suma_x
    sub x12, x12, x13       // x12 = Denominador_M
m_division:
    //divicion con signo
    // Dividir = pendiente m
    sdiv x14, x9, x12       // x14 = sLOPE_x100 = (Numerador * 100) / Denominador
//el intercepto  B_x100
b_numerador:
    // Intercepto_B  = (suma_y *100)-( m * suma_x) / N
    mul x9, x0, x11         // x9 = suma_y * 100
    mul x10, x14, x1        // x10 = m_x100 * suma_x
    sub x9, x9, x10         // x9 = (suma_y * 100) - (m_x100 * suma_x)
b_division:
    // divido n
    sdiv x15, x9, x4        // x15 =Intercepto_B_x100 = B_x100 
regresion_salida:
    mov x0, x14             //   pendiente en x0
    mov x1, x15             //   intercepto en x1
    ret

        /*
        predecir_futuro
        entra:
            x0 = m_x100 
            x1 = b_x100
            x2 = N
            x3 = K
        sasle
            x0 = y_predic
        */
predecir_futuro:
    //  x_futuro = N + K - 1 
    add x9, x2, x3
    sub x9, x9, #1          // x9 = x_futuro
    //Y_PRED = ((M_X100 * X_FUTURE) + B_X100) / 100 
    mul x10, x0, x9         // x10 = m_x100 * x_futuro
    add x10, x10, x1        // x10 = (m_x100 * x_futuro) + b_x100
    // dividiendo  por 100
    mov x11, #100
    sdiv x0, x10, x11       // x0 = y aproximada redonda Resultado final
    ret
 //gurdar_reporte

guardar_reporte:
    stp x29, x30, [sp, #-16]!
    mov x29, sp

    // Abrir el archivo 
    ldr x0, =out_filename
    bl open_output
    cmp x0, #0                  
    blt fin_guardar
    mov x23, x0                 

    // escritura y concatenacion
    mov x0, x23
    ldr x1, =str_calc
    mov x2, #len_calc
    bl write_result

    ldr x1, =str_col
    mov x2, #len_col
    mov x3, x19                 // COLUMN
    bl escribir_linea

    ldr x1, =str_wstart
    mov x2, #len_wstart
    mov x3, x20                 //  WINDOW_sTART
    bl escribir_linea

    ldr x1, =str_wend
    mov x2, #len_wend
    mov x3, x21                 //WINDOW_END
    bl escribir_linea

    ldr x1, =str_count
    mov x2, #len_count
    mov x3, x25                 // COUNT
    bl escribir_linea

    ldr x1, =str_k
    mov x2, #len_k
    mov x3, x26                 //  K
    bl escribir_linea

    ldr x1, =str_slope
    mov x2, #len_slope
    mov x3, x17                 //  sLOPE_x100
    bl escribir_linea

    ldr x1, =str_intercept
    mov x2, #len_intercept
    mov x3, x18                 //  INTERCEPT_x100
    bl escribir_linea

    ldr x1, =str_predicted
    mov x2, #len_predicted
    mov x3, x19                 // PREDICTED_K
    bl escribir_linea

    // salida 
    mov x0, x23
    ldr x1, =str_status
    mov x2, #len_status
    bl write_result

    // Cerrar archivo 
    mov x0, x23
    bl close_fd

fin_guardar:
    ldp x29, x30, [sp], #16
    ret


//scribir_linea

escribir_linea:
    stp x29, x30, [sp, #-32]!
    mov x29, sp
    str x3, [sp, #16]    

    // header 
    mov x0, x23                 
    bl write_result

    // Convertir  ASCII
    ldr x0, [sp, #16]
    ldr x1, =ascii_buf
    bl int_to_ascii

    // 
    mov x2, x0         //  registro x0 
    mov x0, x23                 
    ldr x1, =ascii_buf
    bl write_result

    //  \n 
    mov x0, x23
    bl newline

    ldp x29, x30, [sp], #32
    ret

//Manejo de reporte de errores 
reporte_error:
    ldr x0, =out_filename
    bl open_output
    cmp x0, #0                  
    blt terminar               
    mov x23, x0                 

    // STATUS=ERROR
    mov x0, x23
    ldr x1, =str_status_err
    mov x2, #len_status_err
    bl write_result

    //ERROR=INVALID_INPUT
    mov x0, x23
    ldr x1, =str_err_type
    mov x2, #len_err_type
    bl write_result

    //DETAIL=INVALID_DATA_OR_FIELDS
    mov x0, x23
    ldr x1, =str_err_detail
    mov x2, #len_err_detail
    bl write_result

    // Cerra
    mov x0, x23
    bl close_fd
    b terminar
