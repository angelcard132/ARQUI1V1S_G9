/*---------------------------------------------------------------------------------
Tulio Jafeth Pirir Schuman || 201700698   
Rutina 4: Predicción lineal simple
Este módulo realiza una predicción predictiva basada en datos de  enteras utilizando
lecturas extraídas de un archivo CSV para un entorno de monitoreo automatizado.
---------------------------------------------------------------------------------*/

.section .data
.align 2
msg_inicio:
    .asciz "--- INICIANDO MODULO 4 PREDICCION LINEAL SIMPLE ---\n"
    len_inicio = . - msg_inicio - 1         

output_filename:                                
    .asciz "resultado_prediccion.txt"              

msg_fin:
    .asciz "\n--- FIN DEL ARCHIVO (Reporte guardado en resultado_prediccion.txt) ---\n"
    len_fin = . - msg_fin - 1                

// --- CONSTANTES DE FORMATEO PARA EL REPORTE DE SALIDA ---
lbl_MODULE:
    .asciz "MODULE=PREDICTION\n"
    len_MODULE = . - lbl_MODULE - 1

lbl_INITIAL_VALUE:
    .asciz "INITIAL_VALUE="
    len_INITIAL_VALUE = . - lbl_INITIAL_VALUE - 1

lbl_FINAL_VALUE:
    .asciz "FINAL_VALUE="
    len_FINAL_VALUE = . - lbl_FINAL_VALUE - 1
 
lbl_TOTAL_DIFF:
    .asciz "TOTAL_DIFF="
    len_TOTAL_DIFF = . - lbl_TOTAL_DIFF - 1

lbl_AVG_CHANGE:
    .asciz "AVG_CHANGE="
    len_AVG_CHANGE = . - lbl_AVG_CHANGE - 1

lbl_NEXT_VALUE:
    .asciz "NEXT_VALUE="
    len_NEXT_VALUE = . - lbl_NEXT_VALUE - 1

msg_columna:
    .asciz "Columna seleccionada para operar: "
    len_columna = . - msg_columna - 1

msg_no_arg:
    .ascii "Error: Debe enviar el numero de columna desde el backend\n"
    msg_no_arg_len = . - msg_no_arg

// Declaración limpia en formato byte para garantizar saltos de línea puros en QEMU
.align 2
txt_newline:    
    .byte 10


.section .bss
.align 4
buffer_columna:
    .skip 16    // Buffer temporal para conversiones numéricas a ASCII


.section .text
.global _start

_start:
        # -----------------------------------------------------------------
        # EXTRACCIÓN Y VALIDACIÓN DE ARGUMENTOS DESDE EL STACK
        # -----------------------------------------------------------------
        ldr     x0, [sp]                    // Carga argc (Cantidad de argumentos) desde backend

        cmp     x0, #2                      // Valida la existencia del argumento requerido
        blt     no_argumento                

        ldr     x0, [sp, #16]               // Carga dirección base de argv[1]
        bl      parse_int                   // Convierte la entrada ASCII a entero
        mov     x20, x0                     // x20 = ID de Columna objetivo (Rango: 1 a 8)

        # -- VERIFICACIONES DE CONTROLES DE RANGO --
        cmp     x20, #1                     
        blt     exit_error                  
        cmp     x20, #8                     
        bgt     exit_error                  

        # -----------------------------------------------------------------
        # INICIALIZACIÓN DE ENTORNO 
        # -----------------------------------------------------------------
        mov     x0, #1                      // x1 = Standard Output (Consola)
        adr     x1, msg_inicio              
        mov     x2, #len_inicio             
        bl      write_result                

        # -----------------------------------------------------------------
        # IMPRESIÓN EN CONSOLA DE LA COLUMNA SELECCIONADA
        # -----------------------------------------------------------------
        mov     x0, #1                      
        adr     x1, msg_columna             
        mov     x2, #len_columna            
        bl      write_result                

        mov     x0, x20                     // Pasa el entero de la columna para conversión
        adr     x1, buffer_columna          
        bl      int_to_ascii                

        mov     x2, x0                      // x0 retorna la longitud de la cadena
        mov     x0, #1                      
        adr     x1, buffer_columna          
        bl      write_result                
        bl      newline                     

        # -----------------------------------------------------------------
        # LECTURA DE   CSV (lecturas.csv)
        # -----------------------------------------------------------------
        bl      read_csv                    
        cmp     x0, #0                      // Validar descriptor lógico del archivo cargado
        blt     exit_error                  

        # -----------------------------------------------------------------
        # PROCESAMIENTO Y EXTRACCIÓN DE DATOS DEL  CSV LOS SE GUARDAN EN EL STACK
        # -----------------------------------------------------------------
        
        // --- EXTRAER EL PRIMER DATO (Fila 0 - VALOR_INICIAL ) ---
        mov     x0, #0                      // Fila = 0
        mov     x1, x20                     // Columna mapeada desde x20
        adr     x2, buffer_columna          
        mov     x3, #16                     
        bl      get_column                  
        
        cmp     x0, #0                      // Validar éxito de la extracción de celda
        beq     error_extraccion            
        
        adr     x0, buffer_columna         // Se utliza el buffer_columna para guardar valore
        bl      parse_int                   // pasa a entero
        mov     x22, x0                     // x22 = VALOR INICIAL

        // --- EXTRAER EL ÚLTIMO DATO (Fila 29 - VALOR_FINAL ) ---
        mov     x0, #29                     // Fila = 29
        mov     x1, x20                     
        adr     x2, buffer_columna          
        mov     x3, #16                     
        bl      get_column                  
        
        cmp     x0, #0                      
        beq     error_extraccion            
        
        adr     x0, buffer_columna          
        bl      parse_int                   
        mov     x25, x0                     // x25 = VALOR FINAL

        # -----------------------------------------------------------------
        # CÁLCULOS MATEMÁTICOS DE TENDENCIA LINEAL (SOLO ENTEROS)
        # -----------------------------------------------------------------
        //  DIFERENCIA TOTAL = XFINAL - XINICIAL
        sub     x26, x25, x22               // x26 = DIF

        // PROMEDIO_CAMBIO = DIFERENCIA / (N - 1) -> N=DATOS RESIVIDOS SON 30 --> 29 pasos
        mov     x9, #29                     
        sdiv    x27, x26, x9                // x27 = PROMEDIO_CAMBIO

        //PREDICCION  = XFINAL + PROMEDIO_CAMBIO
        add     x28, x25, x27               // x28 = PREDICCION (Día 31)

        # -----------------------------------------------------------------
        # SÉCURIZACIÓN Y APERTURA DE DESCRIPTOR DE SALIDA (.TXT)
        # -----------------------------------------------------------------
        adr     x0, output_filename         
        bl      open_output                  // CON UTILS.S ABRIR ARCHIVO .REXT
        cmp     x0, #0                      
        blt     exit_error                  
        mov     x24, x0                     // x24 = Guardar File Descriptor asignado

        # -----------------------------------------------------------------
        # GENERACIÓN SISTEMÁTICA DEL REPORTE (CONSOLA Y ARCHIVO)
        # -----------------------------------------------------------------

        // --- FILA 1: IDENTIFICACIÓN DE MÓDULO ---
        mov     x0, #1             // x0 = 1 (Descriptor de archivo para stdout / pantalla)         
        adr     x1, lbl_MODULE      // direccion de memoria para texto
        mov     x2, #len_MODULE     //logitud del la cadena
        bl      write_result        // Llama a la función para imprimir en pantalla

        mov     x0, x24                //x0 = Descriptor de archivo guardado en x24  (el . txt)     
        adr     x1, lbl_MODULE
        mov     x2, #len_MODULE
        bl      write_result            // Llama a la función para imprimir en el archivo


        // --- FILA 2: INITIAL_VALUE ---
        // Etiqueta
        mov     x0, #1                      
        adr     x1, lbl_INITIAL_VALUE   
        mov     x2, #len_INITIAL_VALUE   
        bl      write_result

        mov     x0, x24     
        adr     x1, lbl_INITIAL_VALUE   
        mov     x2, #len_INITIAL_VALUE   
        bl      write_result
        
        
    // Conversión de entero a caracteres ASCII

        // Registro
        mov     x0, x22                         // x0 = El valor numérico a convertir (guardado en x22) valor inicial
        adr     x1, buffer_columna              // x1 = Puntero al buffer de memoria donde se guardará el texto resultant
        bl      int_to_ascii                    // Llama a la subrutina
         // Primera impresión del número  (Consola)
        mov     x2, x0
        mov     x0, #1      
        adr     x1, buffer_columna      
        bl      write_result
        // Segunda impresión del número: Duplicar salida (Archivo)
        mov     x0, x24     
        adr     x1, buffer_columna      
        bl      write_result
        
        
        // Salto de Línea Múltiple vía Subrutina
        bl      salto


        // --- FILA 3: FINAL_VALUE ---
        // Etiqueta
        mov     x0, #1      
        adr     x1, lbl_FINAL_VALUE     
        mov     x2, #len_FINAL_VALUE     
        bl      write_result

        mov     x0, x24     
        adr     x1, lbl_FINAL_VALUE     
        mov     x2, #len_FINAL_VALUE     
        bl      write_result
        
        
        // Registro
        mov     x0, x25                     // x0 = El valor numérico a convertir (guardado en x25) valor final
        adr     x1, buffer_columna      
        bl      int_to_ascii              
        mov     x2, x0

        //IMPRECION CONSOLA
        mov     x0, #1      
        adr     x1, buffer_columna      
        bl      write_result
        //IMPRECION ARCHIVO ,TXT
        mov     x0, x24     
        adr     x1, buffer_columna      
        bl      write_result

        bl      salto

        
        // --- FILA 4: TOTAL_DIFF ---
        // Etiqueta
        mov     x0, #1
        adr     x1, lbl_TOTAL_DIFF
        mov     x2, #len_TOTAL_DIFF
        bl      write_result

        mov     x0, x24
        adr     x1, lbl_TOTAL_DIFF
        mov     x2, #len_TOTAL_DIFF
        bl      write_result
        
        // Registro
        mov     x0, x26                     //X26 = DIFERENCIA 
        adr     x1, buffer_columna
        bl      int_to_ascii
        
        //IMPRESION EN CONSOLA
        mov     x2, x0
        mov     x0, #1
        adr     x1, buffer_columna
        bl write_result
        //IMPRESION ARCHIVO.TXT
        mov     x0, x24
        adr     x1, buffer_columna
        bl      write_result
        
        bl      salto


        // --- FILA 5: AVG_CHANGE ---
        // Etiqueta
        mov     x0, #1
        adr     x1, lbl_AVG_CHANGE
        mov     x2, #len_AVG_CHANGE
        bl      write_result


        mov     x0, x24
        adr     x1, lbl_AVG_CHANGE     
        mov     x2, #len_AVG_CHANGE    
        bl      write_result
        // Registro
        mov     x0, x27                 //X27 = PROMEDIO
        adr     x1, buffer_columna    
        bl      int_to_ascii              
        //IMPRESION EN LA CONSOLA        
        mov     x2, x0
        mov     x0, #1      
        adr     x1, buffer_columna      
        bl      write_result
        // IMPORESION EN ARCHIVO
        mov     x0, x24     
        adr     x1, buffer_columna      
        bl      write_result

        bl      salto


        // --- FILA 6: NEXT_VALUE (PREDICCIÓN FINALES) ---
        // Etiqueta
        mov     x0, #1      
        adr     x1, lbl_NEXT_VALUE      
        mov     x2, #len_NEXT_VALUE      
        bl      write_result

        mov     x0, x24     
        adr     x1, lbl_NEXT_VALUE      
        mov     x2, #len_NEXT_VALUE      
        bl       write_result

        // Registro
        mov     x0, x28                     //X28 PREDICCION
        adr     x1, buffer_columna      
        bl      int_to_ascii

        //IMPRESION EN CONSOLA              
        mov     x2, x0
        mov     x0, #1      
        adr     x1, buffer_columna      
        bl      write_result
        //IMPRESION EN ARCHIVO 
        mov     x0, x24    
        adr     x1, buffer_columna      
        bl      write_result

        bl      salto
        // CERRAR ARCHIVO.TXT Y FINALIZACION DEL PROCESO 
        b       finalizar_proceso
# -----------------------------------------------------------------
# D FINALIZACION DEL PORCESO 
# -----------------------------------------------------------------

finalizar_proceso:
    // 8. Cerrar el archivo de texto de forma segura
    mov     x0, x24
    bl      close_fd

    // 9. Mensaje de cierre final en la consola
    mov     x0, #1
    adr     x1, msg_fin
    mov     x2, #len_fin
    bl      write_result
    
    mov     x0, #0                      // Éxito
    b       finalizar
# -----------------------------------------------------------------
# SUBRUTINAS COMPACTAS DE CONTROL DE FLUJO
# -----------------------------------------------------------------

/* Subrutina: salto
  Aplica un salto de línea síncrono (Consola y Archivo).
  Optimización: Tail-Call mediante registro x19 para preservar x30 sin tocar el Stack.
*/
salto:
        mov     x19, x30                    // Resguarda dirección de retorno del flujo principal
        
        mov     x0, #1                      // Destino: Consola
        adr     x1, txt_newline
        mov     x2, #1
        bl      write_result                // Ejecuta e intercepta x30 interno

        mov     x0, x24                     // Destino: Archivo Descriptor (.txt)
        adr     x1, txt_newline
        mov     x2, #1
        
        mov     x30, x19                    // Restaura x30 original antes del desenlace
        b       write_result                // Salto incondicional final: delega el 'ret' a utils.o

# -----------------------------------------------------------------
# MANEJADORES DE EXCEPCIONES Y DESCONEXIÓN DEL SISTEMA (SYSCALLS)
# -----------------------------------------------------------------
no_argumento:
        mov     x0, #1                      
        adr     x1, msg_no_arg              
        mov     x2, #msg_no_arg_len         
        mov     x8, #64                     // Syscall 64 = sys_write
        svc     #0                          
        b       exit_error                  

exit_error:
        mov     x0, #1                      // Status code = 1 (Error general)
        mov     x8, #93                     // Syscall 93 = sys_exit
        svc     #0                          

error_extraccion:
        mov     x0, #1                      
        mov     x8, #93                     
        svc     #0   

finalizar:
        mov     x0, #0                      // Status code = 0 (Salida Exitosa)
        mov     x8, #93                     
        svc     #0