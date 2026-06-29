AS = aarch64-linux-gnu-as
LD = aarch64-linux-gnu-ld

TARGET = analizador_historico
UTILS  = utils.o

all: $(TARGET)

$(TARGET): analizador_historico.o $(UTILS)
	$(LD) -o $(TARGET) analizador_historico.o $(UTILS)

analizador_historico.o: analizador_historico.s
	$(AS) -o analizador_historico.o analizador_historico.s

utils.o: utils.s
	$(AS) -o utils.o utils.s

clean:
	rm -f *.o $(TARGET) resultado_historico.txt