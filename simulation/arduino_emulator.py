import serial
import time
import math
import pygame

from simulation.planta_virtual import Planta

PORTA_SERIAL_ARDUINO_VIRTUAL = 'COM6'
BAUD_RATE = 9600
MAX_VELOCIDADE_ARDUINO = 255
VELOCIDADE_SIM_CM_S = 20.0 # O robô anda 20 cm/s na velocidade máxima

class ArduinoEmulator:
    def __init__(self):
        self.x_cm, self.y_cm = 150, 120
        self.angulo_rad = math.radians(-45)
        self.velocidade_linear = 0.0
        self.velocidade_angular = 0.0
        
        self.mundo = Planta()
        self.pontos_scan_vis = []
        
        print(f"ARDUINO (SIM) -> Conectando à porta serial virtual {PORTA_SERIAL_ARDUINO_VIRTUAL}...")
        self.ser = serial.Serial(PORTA_SERIAL_ARDUINO_VIRTUAL, BAUD_RATE, timeout=0.1)
        print("ARDUINO (SIM) -> Conectado. Aguardando comandos do Cérebro...")


    def atualizar_posicao(self, dt):
        distancia = self.velocidade_linear * VELOCIDADE_SIM_CM_S * dt
        self.angulo_rad += self.velocidade_angular * math.radians(90) * dt
        self.x_cm += distancia * math.cos(self.angulo_rad)
        self.y_cm += distancia * math.sin(self.angulo_rad)


    def executar_comando(self, comando):
        action = comando[0]
        value = int(comando[1:]) if len(comando) > 1 else 0
        percentual = value / MAX_VELOCIDADE_ARDUINO
        
        if action == 'w': self.velocidade_linear, self.velocidade_angular = percentual, 0
        elif action == 's': self.velocidade_linear, self.velocidade_angular = -percentual, 0
        elif action == 'd': self.velocidade_angular, self.velocidade_linear = -percentual, 0
        elif action == 'a': self.velocidade_angular, self.velocidade_linear = percentual, 0
        elif action == 'q': self.velocidade_linear, self.velocidade_angular = 0, 0
        elif action == 'e': self.fazer_scan()

    def fazer_scan(self):
        print("ARDUINO (SIM) -> Recebeu comando de scan. Calculando distâncias...")
        self.pontos_scan_vis = []
        self.ser.write(b"ACK: INICIANDO SCAN\n")
        for angulo_graus in range(0, 181, 10):
            angulo_sensor_rad = self.angulo_rad + math.radians(angulo_graus)
            dist_cm = self.mundo.calcular_distancia((self.x_cm, self.y_cm), angulo_sensor_rad)
            self.pontos_scan_vis.append((angulo_graus, dist_cm))
            resposta = f"{angulo_graus};{dist_cm}\n"
            self.ser.write(resposta.encode('utf-8'))
            time.sleep(0.01) # Simula o tempo do servo
        self.ser.write(b"ACK: FIM DO SCAN\n")
        print("ARDUINO (SIM) -> Dados do scan enviados.")


    def loop_principal(self):
        clock = pygame.time.Clock()
        rodando = True
        while rodando:
            dt = clock.tick(60) / 1000.0
            if self.ser.in_waiting > 0:
                comando = self.ser.readline().decode('utf-8').strip()
                if comando:
                    print(f"ARDUINO (SIM) -> Comando recebido: '{comando}'")
                    self.executar_comando(comando)
            
            self.atualizar_posicao(dt)
            self.mundo.desenhar((self.x_cm, self.y_cm), self.angulo_rad, self.pontos_scan_vis)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    rodando = False
        
        self.ser.close()
        pygame.quit()


if __name__ == "__main__":
    emulador = ArduinoEmulator()
    emulador.loop_principal()