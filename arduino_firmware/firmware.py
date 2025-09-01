import serial
import time
import math
import threading

PI_AVAILABLE = False
MAX_DISTANCE_CM = 200

class MotorSim:
    def frente(self, name, velocidade):
        print(f"[SIM] MOTOR {name} -> Frente @ {velocidade}")

    def tras(self, name, velocidade):
        print(f"[SIM] MOTOR {name} -> Trás @ {velocidade}")

    def parar(self, name):
        print(f"[SIM] MOTOR {name} -> Parado")

class ServoSim:
    def set_angle(self, angulo):
        print(f"[SIM] SERVO -> Ângulo {angulo}")

class SonarSim:
    def get_distance(self, angulo):
        return MAX_DISTANCE_CM - abs(angulo - 90)

motor = MotorSim()
servo = ServoSim()
sonar = SonarSim()

def chassiAvancar(velocidade):
    print("[SIM] CHASSI -> AVANÇAR")
    for roda in ["TR_ESQ", "FR_ESQ", "TR_DIR", "FR_DIR"]:
        motor.frente(roda, velocidade)

def chassiRecuar(velocidade):
    print("[SIM] CHASSI -> RECUAR")
    for roda in ["TR_ESQ", "FR_ESQ", "TR_DIR", "FR_DIR"]:
        motor.tras(roda, velocidade)

def chassiVirarDireita(velocidade):
    print("[SIM] CHASSI -> VIRAR DIREITA")
    for roda in ["TR_ESQ", "FR_ESQ"]:
        motor.frente(roda, velocidade)
    for roda in ["TR_DIR", "FR_DIR"]:
        motor.tras(roda, velocidade)

def chassiVirarEsquerda(velocidade):
    print("[SIM] CHASSI -> VIRAR ESQUERDA")
    for roda in ["TR_ESQ", "FR_ESQ"]:
        motor.tras(roda, velocidade)
    for roda in ["TR_DIR", "FR_DIR"]:
        motor.frente(roda, velocidade)

def chassiParar():
    print("[SIM] CHASSI -> PARAR")
    for roda in ["TR_ESQ", "FR_ESQ", "TR_DIR", "FR_DIR"]:
        motor.parar(roda)

def scannerFazerVarredura(serial_con):
    print("[SIM] SCANNER -> Varredura iniciada")
    for angulo in range(0, 181, 10):
        servo.set_angle(angulo)
        time.sleep(0.04)
        distancia = sonar.get_distance(angulo)
        resposta = f"{angulo};{int(distancia)}\n"
        serial_con.write(resposta.encode('utf-8'))
        print(f"[SIM] SCANNER -> {resposta.strip()}")
    serial_con.write(b"FIM DO SCAN\n")
    print("[SIM] SCANNER -> Varredura concluída")

def main():
    SERIAL_PORT = "COM6"
    BAUD_RATE = 9600
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2)
    print("Firmware Simulado iniciado. Aguardando comandos...")

    try:
        while True:
            if ser.in_waiting > 0:
                comando = ser.readline().decode('utf-8').strip()
                if not comando:
                    continue

                action = comando[0]
                value = int(comando[1:]) if len(comando) > 1 else 0

                if action == 'w': chassiAvancar(value)
                elif action == 's': chassiRecuar(value)
                elif action == 'd': chassiVirarDireita(value)
                elif action == 'a': chassiVirarEsquerda(value)
                elif action == 'q': chassiParar()
                elif action == 'e': scannerFazerVarredura(ser)
                else:
                    ser.write(f"ERR: Comando desconhecido -> {comando}\n".encode('utf-8'))
                    print(f"[SIM] Comando desconhecido: {comando}")

    except KeyboardInterrupt:
        print("\nFirmware simulado encerrado via Ctrl+C")
        chassiParar()
    finally:
        ser.close()

if __name__ == "__main__":
    main()
