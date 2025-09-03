import pygame
import math
from simulation.planta_virtual import Planta

# Constantes de física da simulação
VELOCIDADE_MAX_LINEAR_CM_S = 20.0
VELOCIDADE_MAX_ANGULAR_GRAUS_S = 90.0
RAIO_ROBO_CM = 4.0 # Define um "raio" para o robô para colisões

class CorpoRoboSimulado:
    """Representa a parte física do robô e sua interação com o mundo virtual."""
    def __init__(self):
        self.mundo = Planta()
        # Estado do Robô
        self.x_cm, self.y_cm = 130, 140
        self.angulo_rad = math.radians(180)
        self.velocidade_linear = 0.0
        self.velocidade_angular = 0.0
        self.pontos_scan_vis = []

    def set_velocidades(self, linear_percent, angular_percent):
        """Define as velocidades do robô. Chamado pelo firmware."""
        self.velocidade_linear = linear_percent
        self.velocidade_angular = angular_percent

    def get_distancia_em_angulo(self, angulo_servo_graus):
        """Calcula a distância de um obstáculo em um ângulo específico do sensor."""
        angulo_total_rad = self.angulo_rad + math.radians(angulo_servo_graus)
        dist = self.mundo.calcular_distancia((self.x_cm, self.y_cm), angulo_total_rad)
        
        self.pontos_scan_vis.append((angulo_servo_graus, dist))
        return dist

    def limpar_visualizacao_scan(self):
        self.pontos_scan_vis = []

    def atualizar_fisica(self, dt):
        """Atualiza a posição do robô no mundo, AGORA COM DETECÇÃO DE COLISÃO."""
        # --- NOVA LÓGICA DE COLISÃO ---
        # Só permite o movimento para FRENTE se não houver uma parede iminente.
        # Movimentos de ré e rotação são sempre permitidos.
        pode_mover_frente = True
        if self.velocidade_linear > 0: # Só checa colisão se estiver indo para frente
            # Calcula a distância para a parede na direção em que o robô está apontando
            distancia_a_frente = self.mundo.calcular_distancia((self.x_cm, self.y_cm), self.angulo_rad)
            if distancia_a_frente <= RAIO_ROBO_CM:
                print(f"[COLISAO] Obstaculo detectado a {distancia_a_frente:.1f}cm. Movimento frontal bloqueado.")
                pode_mover_frente = False
                # Para o robô para evitar que ele fique "preso" tentando andar contra a parede
                self.set_velocidades(0, 0)
        
        # --- ATUALIZAÇÃO DA POSIÇÃO ---
        deslocamento = 0
        if (self.velocidade_linear > 0 and pode_mover_frente) or (self.velocidade_linear < 0):
             # Permite o deslocamento se:
             # - for para frente E não houver colisão
             # - ou for para trás (sem verificação)
            deslocamento = self.velocidade_linear * VELOCIDADE_MAX_LINEAR_CM_S * dt

        rotacao = self.velocidade_angular * math.radians(VELOCIDADE_MAX_ANGULAR_GRAUS_S) * dt
        
        self.angulo_rad += rotacao
        self.angulo_rad = math.atan2(math.sin(self.angulo_rad), math.cos(self.angulo_rad))

        self.x_cm += deslocamento * math.cos(self.angulo_rad)
        self.y_cm -= deslocamento * math.sin(self.angulo_rad)

    def desenhar_na_tela(self, mapa_surface):
        """Pede para o mundo se desenhar com o estado atual do robô e o mapa."""
        self.mundo.desenhar((self.x_cm, self.y_cm), self.angulo_rad, self.pontos_scan_vis, mapa_surface)