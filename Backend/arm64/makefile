#  Uso:
#    make            → compila todo
#    make modulo_5   → compila los modulos, cambiar para el modulo deseado
#    make clean      → borra binarios y .o
#    make run_all    → ejecuta los 5 módulos en orden
#    make test_5     → compila y ejecuta solo el módulo 5
# =============================================================

AS      = as
LD      = ld
ASFLAGS = -g              # incluir info de debug para GDB

# Biblioteca común (todos los módulos la necesitan)
UTILS_SRC = utils.s
UTILS_OBJ = utils.o

# Módulos individuales
MODULES = modulo_1_media \
          modulo_2_varianza \
          modulo_3_anomalias \
          modulo_4_prediccion \
          modulo_5_tendencia

.PHONY: all clean run_all test_5

#  Compilar todo 
all: $(UTILS_OBJ) $(MODULES)

# Compilar utils.o (una sola vez, compartido por todos)
$(UTILS_OBJ): $(UTILS_SRC)
	$(AS) $(ASFLAGS) -o $@ $<

# Regla genérica para cada módulo
# Ejemplo: modulo_5_tendencia → modulo_5_tendencia.o + utils.o → binario
%: %.s $(UTILS_OBJ)
	$(AS) $(ASFLAGS) -o $@.o $<
	$(LD) -o $@ $@.o $(UTILS_OBJ)

#  Limpiar 
clean:
	rm -f $(UTILS_OBJ)
	rm -f $(addsuffix .o, $(MODULES))
	rm -f $(MODULES)
	rm -f resultado_*.txt

#  Ejecutar todos los módulos 
run_all: all
	@echo ">>> Ejecutando módulo 1: Media ponderada"
	./modulo_1_media
	@echo ">>> Ejecutando módulo 2: Varianza y desviación"
	./modulo_2_varianza
	@echo ">>> Ejecutando módulo 3: Detección de anomalías"
	./modulo_3_anomalias
	@echo ">>> Ejecutando módulo 4: Predicción lineal"
	./modulo_4_prediccion
	@echo ">>> Ejecutando módulo 5: Tendencia acumulada"
	./modulo_5_tendencia
	@echo ""
	@echo "=== Resultados generados ==="
	@cat resultado_media.txt      2>/dev/null || echo "(modulo_1 no disponible)"
	@echo "---"
	@cat resultado_varianza.txt   2>/dev/null || echo "(modulo_2 no disponible)"
	@echo "---"
	@cat resultado_anomalias.txt  2>/dev/null || echo "(modulo_3 no disponible)"
	@echo "---"
	@cat resultado_prediccion.txt 2>/dev/null || echo "(modulo_4 no disponible)"
	@echo "---"
	@cat resultado_tendencia.txt  2>/dev/null || echo "(modulo_5 no disponible)"

#  Compilar y correr solo el módulo 5 
test_5: $(UTILS_OBJ) modulo_5_tendencia
	./modulo_5_tendencia
	@echo ""
	@echo "=== resultado_tendencia.txt ==="
	@cat resultado_tendencia.txt