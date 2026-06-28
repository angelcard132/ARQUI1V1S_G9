AS      = as
LD      = ld
ASFLAGS = -g              


UTILS_SRC = utils.s
UTILS_OBJ = utils.o


MODULES = modulo_1_media \
          modulo_2_varianza \
          modulo_3_anomalias \
          modulo_4_prediccion \
          modulo_5_tendencia

.PHONY: all clean run_all test_5


all: $(UTILS_OBJ) $(MODULES)


$(UTILS_OBJ): $(UTILS_SRC)
	$(AS) $(ASFLAGS) -o $@ $<

%: %.s $(UTILS_OBJ)
	$(AS) $(ASFLAGS) -o $@.o $<
	$(LD) -o $@ $@.o $(UTILS_OBJ)


clean:
	rm -f $(UTILS_OBJ)
	rm -f $(addsuffix .o, $(MODULES))
	rm -f $(MODULES)
	rm -f resultado_*.txt
 
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

test_5: $(UTILS_OBJ) modulo_5_tendencia
	./modulo_5_tendencia
	@echo ""
	@echo "=== resultado_tendencia.txt ==="
	@cat resultado_tendencia.txt