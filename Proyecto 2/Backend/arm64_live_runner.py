import subprocess
import os
import threading


class ARM64LiveRunner:

    def __init__(self, bin_path="./arm64/motor_vivo"):
        self.bin_path = bin_path
        self.proc = None
        self._stderr_thread = None
        self._binario_faltante = False

    def iniciar(self):
        # Si ya había un proceso vivo, cerrarlo limpiamente antes de
        # abrir uno nuevo (evita procesos huérfanos acumulándose).
        if self.proc is not None:
            self.cerrar()

        if not os.path.exists(self.bin_path):
            print(f"[ARM64 LIVE] No existe el binario: {self.bin_path}")
            self.proc = None
            self._binario_faltante = True
            return False

        try:
            self.proc = subprocess.Popen(
                [self.bin_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # line-buffered
            )
        except Exception as e:
            print(f"[ARM64 LIVE] Error al iniciar el proceso: {e}")
            self.proc = None
            return False

        self._binario_faltante = False

        self._iniciar_lector_stderr()
        print("[ARM64 LIVE] Motor iniciado")
        return True

    def _iniciar_lector_stderr(self):
        proc = self.proc

        def _leer():
            if proc is None or proc.stderr is None:
                return
            for linea in proc.stderr:
                linea = linea.rstrip()
                if linea:
                    print(f"[ARM64 LIVE][stderr] {linea}")

        self._stderr_thread = threading.Thread(target=_leer, daemon=True)
        self._stderr_thread.start()

    def _proceso_vivo(self):
        return self.proc is not None and self.proc.poll() is None

    def consultar(self, lectura, modo="AUTOMATICO"):
        if self._binario_faltante:
            return {"ACTION": "NO_ACTION"}

        if not self._proceso_vivo():
            codigo = self.proc.poll() if self.proc else None
            print(f"[ARM64 LIVE] El proceso no está vivo (exit code={codigo}). Reiniciando...")
            self.iniciar()
            if not self._proceso_vivo():
                return {"ACTION": "NO_ACTION"}

        modo_num = 0 if modo == "AUTOMATICO" else 1
        linea = (
            f"{int(round(lectura['temp'])) if lectura.get('temp') is not None else 0},"
            f"{int(round(lectura['hum'])) if lectura.get('hum') is not None else 0},"
            f"{int(round(lectura['suelo1'])) if lectura.get('suelo1') is not None else 0},"
            f"{int(round(lectura['suelo2'])) if lectura.get('suelo2') is not None else 0},"
            f"{int(round(lectura['luz'])) if lectura.get('luz') is not None else 0},"
            f"{int(round(lectura['gas'])) if lectura.get('gas') is not None else 0},"
            f"{modo_num}\n"
        )

        try:
            self.proc.stdin.write(linea)
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            print(f"[ARM64 LIVE] Pipe roto al escribir ({e}). Reiniciando...")
            self.iniciar()
            return {"ACTION": "NO_ACTION"}

        lines = []
        try:
            while True:
                line = self.proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                lines.append(line)
                if line.startswith("STATUS="):
                    break
        except (BrokenPipeError, OSError, ValueError) as e:
            print(f"[ARM64 LIVE] Error al leer respuesta ({e}). Reiniciando...")
            self.iniciar()
            return {"ACTION": "NO_ACTION"}

        if not lines:
            codigo = self.proc.poll()
            print(f"[ARM64 LIVE] Respuesta vacía — el proceso terminó (exit code={codigo}). Reiniciando...")
            self.iniciar()
            return {"ACTION": "NO_ACTION"}

        res = {}
        for line in lines:
            if "=" in line:
                k, v = line.split("=", 1)
                res[k.strip()] = v.strip()

        return res

    def cerrar(self):
        if self.proc is None:
            return

        proc = self.proc
        self.proc = None 

        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.write("n\n")
                proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass  

        try:
            proc.terminate()
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception:
            pass

        print("[ARM64 LIVE] Motor cerrado")