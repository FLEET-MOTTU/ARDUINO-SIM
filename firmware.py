"""
Módulo do Firmware Simulado (O "Corpo" / "Arduino").

Este módulo tem a dupla responsabilidade de ser o ponto central da aplicação de
simulação (gerenciando o loop do Pygame e a física) e de emular a camada de
hardware de baixo nível de um robô real.

A comunicação com o Cérebro (main.py) é feita exclusivamente via uma porta serial
virtual, garantindo que o Cérebro opere de forma "cega", sem acesso direto ao
estado do mundo simulado.
"""

import serial
import time
import pygame
import argparse
import os

from simulation.corpo_e_mundo_sim import CorpoRoboSimulado

# Esta constante define o valor máximo que a eletrônica do robô (simulada) aceita.
# É usada para converter os comandos de velocidade (0-255) em um percentual.
MAX_VELOCIDADE_ARDUINO = 255.0


class FirmwareSimulado:
    """
    Simula o firmware de um microcontrolador e orquestra a simulação gráfica.
    """
    def __init__(self, porta_serial: str):
        """
        Inicializa a simulação, o corpo físico do robô e a comunicação serial.

        Args:
            porta_serial (str): O nome da porta serial virtual a ser usada (ex: 'COM7').
        """
        print("Iniciando o Firmware Simulado...")
        
        # Instancia a representação física do robô dentro do mundo virtual.
        self.corpo_robo = CorpoRoboSimulado()
        
        # Atributos para gerenciar a exibição do mapa gerado pelo Cérebro.
        self.mapa_surface = None
        self.ultimo_mtime_mapa = 0.0
        self.caminho_mapa_esperado = os.path.join("output", "maps", "map_slam_latest.png")
        self.timer_mapa = 0.0
        self.intervalo_check_mapa = 1.0

        try:
            self.ser = serial.Serial(porta_serial, 9600, timeout=0.1)
            print(f"Firmware escutando na porta serial virtual {porta_serial}.")
        except serial.SerialException as e:
            print(f"ERRO CRÍTICO: Não foi possível abrir a porta {porta_serial}. {e}")
            raise SystemExit

    def _obter_odometria(self):
        """
        Atende a um pedido do Cérebro ('o'), consultando a simulação sobre o
        deslocamento real acumulado e o envia de volta pela serial.
        """
        dx, dy, dtheta = self.corpo_robo.get_odometria_e_resetar()
        resposta = f"{dx};{dy};{dtheta}\n"
        self.ser.write(resposta.encode('utf-8'))
        print(f"[FIRMWARE] Odometria real enviada: ({dx:.2f}, {dy:.2f}, {dtheta:.2f})")

    def _carregar_mapa_do_disco(self):
        """
        Verifica se o arquivo de mapa foi modificado pelo Cérebro para atualizar
        a visualização na janela da simulação.
        """
        try:
            if not os.path.exists(self.caminho_mapa_esperado):
                return

            mtime_atual = os.path.getmtime(self.caminho_mapa_esperado)

            if mtime_atual > self.ultimo_mtime_mapa:
                print(f"VISUALIZACAO: Mapa foi atualizado no disco. Recarregando...")
                self.mapa_surface = pygame.image.load(self.caminho_mapa_esperado).convert()
                self.ultimo_mtime_mapa = mtime_atual
        except pygame.error:
            # Ignora erros que ocorrem ao tentar ler o arquivo enquanto ele
            # está sendo escrito pelo outro processo (Cérebro).
            pass
        except Exception as e:
            print(f"VISUALIZACAO: Erro inesperado ao carregar imagem do mapa: {e}")

    # --- Funções de Controle do Chassi ---
    def _chassi_avancar(self, velocidade: int):
        self.corpo_robo.set_velocidades(velocidade / MAX_VELOCIDADE_ARDUINO, 0)

    def _chassi_recuar(self, velocidade: int):
        self.corpo_robo.set_velocidades(-(velocidade / MAX_VELOCIDADE_ARDUINO), 0)

    def _chassi_virar_direita(self, velocidade: int):
        self.corpo_robo.set_velocidades(0, -(velocidade / MAX_VELOCIDADE_ARDUINO))

    def _chassi_virar_esquerda(self, velocidade: int):
        self.corpo_robo.set_velocidades(0, velocidade / MAX_VELOCIDADE_ARDUINO)

    def _chassi_parar(self):
        self.corpo_robo.set_velocidades(0, 0)

    def _fazer_scan(self):
        """
        Atende a um pedido do Cérebro ('e'), realizando uma varredura de 180 graus
        e enviando cada leitura de sensor de volta pela serial.
        """
        self.corpo_robo.limpar_visualizacao_scan()
        for angulo_graus in range(0, 181, 10):
            dist_cm = self.corpo_robo.get_distancia_em_angulo(angulo_graus)
            resposta = f"{angulo_graus};{dist_cm}\n"
            self.ser.write(resposta.encode('utf-8'))
            time.sleep(0.04)  # Simula a latência mecânica de um servo motor.

    def executar_comando(self, comando: str):
        """Interpreta a string de comando vinda do Cérebro."""
        action = comando[0]
        value = int(comando[1:]) if len(comando) > 1 else 0
        
        if   action == 'w': self._chassi_avancar(value)
        elif action == 's': self._chassi_recuar(value)
        elif action == 'd': self._chassi_virar_direita(value)
        elif action == 'a': self._chassi_virar_esquerda(value)
        elif action == 'q': self._chassi_parar()
        elif action == 'e': self._fazer_scan()
        elif action == 'o': self._obter_odometria()

    def loop_principal(self):
        """
        O loop central da simulação. É responsável por manter a aplicação
        rodando, ler comandos seriais, atualizar a física e renderizar a cena.
        """
        clock = pygame.time.Clock()
        rodando = True
        while rodando:
            dt = clock.tick(60) / 1000.0
            
            if self.ser.in_waiting > 0:
                comando = self.ser.readline().decode('utf-8').strip()
                if comando:
                    self.executar_comando(comando)

            self.timer_mapa += dt
            if self.timer_mapa >= self.intervalo_check_mapa:
                self._carregar_mapa_do_disco()
                self.timer_mapa = 0.0
            
            self.corpo_robo.atualizar_fisica(dt)
            self.corpo_robo.desenhar_na_tela(self.mapa_surface)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    rodando = False
        
        self.ser.close()
        pygame.quit()
        print("Simulação e Firmware encerrados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Firmware simulado e orquestrador da simulação.")
    parser.add_argument('--port', default='COM7', help='Porta serial VIRTUAL para escutar o Cérebro (RPi).')
    args = parser.parse_args()
    
    simulador_completo = FirmwareSimulado(porta_serial=args.port)
    simulador_completo.loop_principal()