import serial
import time
import pygame
import argparse
import os

from simulation.corpo_e_mundo_sim import CorpoRoboSimulado


MAX_VELOCIDADE_ARDUINO = 255.0


class FirmwareSimulado:
    def __init__(self, porta_serial):
        print("Iniciando o Firmware Simulado...")
        self.corpo_robo = CorpoRoboSimulado()
        self.mapa_surface = None
        self.ultimo_mtime_mapa = 0.0
        self.caminho_mapa_esperado = os.path.join("output", "maps", "map_slam_latest.png")        
        self.timer_mapa = 0.0
        self.intervalo_check_mapa = 1.0

        # Conexão Serial (sem alterações)
        try:
            self.ser = serial.Serial(porta_serial, 9600, timeout=0.1)
            print(f"Firmware escutando na porta serial virtual {porta_serial}.")
        except serial.SerialException as e:
            print(f"ERRO CRÍTICO: Não foi possível abrir a porta {porta_serial}. {e}")
            raise SystemExit
            

    def _carregar_mapa_do_disco(self):
        """
        Verifica se o arquivo 'map_slam_latest.png' foi modificado e, se sim,
        recarrega a imagem para exibição.
        """
        try:
            if not os.path.exists(self.caminho_mapa_esperado):
                return

            mtime_atual = os.path.getmtime(self.caminho_mapa_esperado)

            if mtime_atual > self.ultimo_mtime_mapa:
                print(f"VISUALIZACAO: Mapa foi atualizado no disco. Recarregando...")
                self.mapa_surface = pygame.image.load(self.caminho_mapa_esperado).convert()
                self.ultimo_mtime_mapa = mtime_atual

        except pygame.error as e:
             pass
        except Exception as e:
            print(f"VISUALIZACAO: Erro inesperado ao carregar imagem do mapa: {e}")


    def _chassi_avancar(self, velocidade):
        percentual = velocidade / MAX_VELOCIDADE_ARDUINO
        self.corpo_robo.set_velocidades(percentual, 0)


    def _chassi_recuar(self, velocidade):
        percentual = - (velocidade / MAX_VELOCIDADE_ARDUINO)
        self.corpo_robo.set_velocidades(percentual, 0)


    def _chassi_virar_direita(self, velocidade):
        percentual = - (velocidade / MAX_VELOCIDADE_ARDUINO)
        self.corpo_robo.set_velocidades(0, percentual)


    def _chassi_virar_esquerda(self, velocidade):
        percentual = velocidade / MAX_VELOCIDADE_ARDUINO
        self.corpo_robo.set_velocidades(0, percentual)


    def _chassi_parar(self):
        self.corpo_robo.set_velocidades(0, 0)


    def _fazer_scan(self):
        self.corpo_robo.limpar_visualizacao_scan()
        for angulo_graus in range(0, 181, 10):
            dist_cm = self.corpo_robo.get_distancia_em_angulo(angulo_graus)
            resposta = f"{angulo_graus};{dist_cm}\n"
            self.ser.write(resposta.encode('utf-8'))
            time.sleep(0.04)


    def executar_comando(self, comando):
        action = comando[0]
        value = int(comando[1:]) if len(comando) > 1 else 0
        
        if action == 'w': self._chassi_avancar(value)
        elif action == 's': self._chassi_recuar(value)
        elif action == 'd': self._chassi_virar_direita(value)
        elif action == 'a': self._chassi_virar_esquerda(value)
        elif action == 'q': self._chassi_parar()
        elif action == 'e': self._fazer_scan()


    def loop_principal(self):
        clock = pygame.time.Clock()
        rodando = True
        while rodando:
            dt = clock.tick(60) / 1000.0
            
            # Checa por comandos seriais
            if self.ser.in_waiting > 0:
                comando = self.ser.readline().decode('utf-8').strip()
                if comando:
                    self.executar_comando(comando)

            # ATUALIZADO: Checa periodicamente por um novo mapa no disco
            self.timer_mapa += dt
            if self.timer_mapa >= self.intervalo_check_mapa:
                self._carregar_mapa_do_disco()
                self.timer_mapa = 0.0 # Reseta o timer
            
            # Atualiza a física e desenha na tela
            self.corpo_robo.atualizar_fisica(dt)
            self.corpo_robo.desenhar_na_tela(self.mapa_surface)
            
            # Checa eventos do Pygame
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    rodando = False
        
        self.ser.close()
        pygame.quit()
        print("Simulação e Firmware encerrados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Firmware simulado e orquestrador da simulação.")
    parser.add_argument('--port', default='COM7', help='Porta serial VIRTUAL para escutar o RPi.')
    args = parser.parse_args()
    
    simulador_completo = FirmwareSimulado(porta_serial=args.port)
    simulador_completo.loop_principal()