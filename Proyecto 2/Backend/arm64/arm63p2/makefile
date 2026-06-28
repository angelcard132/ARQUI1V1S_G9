AS = aarch64-linux-gnu-as
LD = aarch64-linux-gnu-ld

UTILS = utils.o

PROGRAMS = motor_vivo \
           analizador_historico \
           modulo_1_rmse \
           modulo_2_regresion \
           modulo_3_prediccion \
           modulo_4_integral_error \
           modulo_5_derivada_local

all: $(PROGRAMS)

utils.o: utils.s
	$(AS) -o utils.o utils.s

modulo_1_rmse: modulo_1_rmse.o $(UTILS)
	$(LD) -o modulo_1_rmse modulo_1_rmse.o $(UTILS)

modulo_2_regresion: modulo_2_regresion.o $(UTILS)
	$(LD) -o modulo_2_regresion modulo_2_regresion.o $(UTILS)

modulo_3_prediccion: modulo_3_prediccion.o $(UTILS)
	$(LD) -o modulo_3_prediccion modulo_3_prediccion.o $(UTILS)

modulo_4_integral_error: modulo_4_integral_error.o $(UTILS)
	$(LD) -o modulo_4_integral_error modulo_4_integral_error.o $(UTILS)

modulo_5_derivada_local: modulo_5_derivada_local.o $(UTILS)
	$(LD) -o modulo_5_derivada_local modulo_5_derivada_local.o $(UTILS)

%.o: %.s
	$(AS) -o $@ $<

clean:
	rm -f *.o $(PROGRAMS) resultado_*.txt