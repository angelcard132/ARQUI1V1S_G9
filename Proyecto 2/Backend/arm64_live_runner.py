import subprocess
import os

class ARM64LiveRunner:
    def __init__(self, bin_path="./arm64/motor_vivo"):
        self.bin_path = bin_path
        self.proc = None

    def iniciar(self):
        if not os.path.exists(self.bin_path):
            print(f"[ARM64 LIVE] No existe: {self.bin_path}")
            return False

        self.proc = subprocess.Popen(
            [self.bin_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        print("[ARM64 LIVE] Motor iniciado")
        return True

    def consultar(self, lectura, modo="AUTOMATICO"):
        if self.proc is None:
            return "ACTION=NO_ACTION"

        modo_num = 0 if modo == "AUTOMATICO" else 1

        linea = (
            f"{int(lectura['temp'])},"
            f"{int(lectura['hum'])},"
            f"{int(lectura['suelo1'])},"
            f"{int(lectura['suelo2'])},"
            f"{int(lectura['luz'])},"
            f"{int(lectura['gas'])},"
            f"{modo_num}\n"
        )

        self.proc.stdin.write(linea)
        self.proc.stdin.flush()

        respuesta = self.proc.stdout.readline().strip()
        return respuesta

    def cerrar(self):
        if self.proc:
            try:
                self.proc.stdin.write("n\n")
                self.proc.stdin.flush()
                self.proc.terminate()
            except Exception:
                pass
