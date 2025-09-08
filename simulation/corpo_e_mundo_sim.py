import pygame
import math

from simulation.planta_virtual import Planta
from robot_specifications import (
    VELOCIDADE_MAX_LINEAR_CM_S,
    VELOCIDADE_MAX_ANGULAR_GRAUS_S
)

RAIO_ROBO_CM = 4.0  # Raio do robô
SUBPASSOS = 5        # Número de sub-passos para colisão segura

class CorpoRoboSimulado:
    """Representa a parte física do robô e sua interação com o mundo virtual."""
    
    def __init__(self):
        self.mundo = Planta()
        self.x_cm, self.y_cm = 130, 140
        self.angulo_rad = math.radians(180)
        self.velocidade_linear = 0.0
        self.velocidade_angular = 0.0
        self.pontos_scan_vis = []

    def set_velocidades(self, linear_percent, angular_percent):
        self.velocidade_linear = linear_percent
        self.velocidade_angular = angular_percent

    def get_distancia_em_angulo(self, angulo_servo_graus):
        """
        Calcula a distância em um ângulo específico do servo.
        CORRIGIDO: Converte o ângulo do servo (0-180) para um ângulo relativo 
        ao robô (-90 a +90) antes de calcular a direção global do raio.
        """
        # Converte o ângulo do servo para ser relativo à frente do robô (90° -> 0°)
        angulo_relativo_rad = math.radians(angulo_servo_graus - 90)
        
        # Soma a orientação global do robô com o ângulo relativo do sensor
        angulo_total_rad = self.angulo_rad + angulo_relativo_rad
        
        # O resto da função continua igual
        dist = self.mundo.calcular_distancia((self.x_cm, self.y_cm), angulo_total_rad)
        self.pontos_scan_vis.append((angulo_servo_graus, dist))
        print(f"[SCAN] Robo ({self.x_cm:.1f}, {self.y_cm:.1f}) θ={math.degrees(self.angulo_rad):.1f}° | "
              f"Ângulo {angulo_servo_graus}° => Dist {dist} cm")
        return dist

    def limpar_visualizacao_scan(self):
        self.pontos_scan_vis = []

    def atualizar_fisica(self, dt):
        # Rotação
        rotacao = self.velocidade_angular * math.radians(VELOCIDADE_MAX_ANGULAR_GRAUS_S) * dt
        self.angulo_rad += rotacao
        self.angulo_rad = math.atan2(math.sin(self.angulo_rad), math.cos(self.angulo_rad))

        # Deslocamento desejado total
        deslocamento_desejado = self.velocidade_linear * VELOCIDADE_MAX_LINEAR_CM_S * dt
        dx_total = deslocamento_desejado * math.cos(self.angulo_rad)
        dy_total = deslocamento_desejado * math.sin(self.angulo_rad)

        # Sub-passos para evitar atravessar paredes
        dx_real, dy_real = 0.0, 0.0
        for i in range(SUBPASSOS):
            sub_dx = dx_total / SUBPASSOS
            sub_dy = dy_total / SUBPASSOS
            novo_x = self.x_cm + dx_real + sub_dx
            novo_y = self.y_cm + dy_real + sub_dy
            angulo_mov = math.atan2(sub_dy, sub_dx)
            distancia = self.mundo.calcular_distancia((self.x_cm + dx_real, self.y_cm + dy_real), angulo_mov)
            if math.hypot(sub_dx, sub_dy) > distancia - RAIO_ROBO_CM:
                # Para ao encostar na parede
                break
            dx_real += sub_dx
            dy_real += sub_dy

        self.x_cm += dx_real
        self.y_cm += dy_real

        print(f"[FISICA] Pos=({self.x_cm:.1f}, {self.y_cm:.1f}) θ={math.degrees(self.angulo_rad):.1f}° | "
              f"Vlin={self.velocidade_linear:.2f}, Vang={self.velocidade_angular:.2f} | "
              f"DeslocX={dx_real:.2f}, DeslocY={dy_real:.2f})")

    def desenhar_na_tela(self, mapa_surface):
        self.mundo.desenhar((self.x_cm, self.y_cm), self.angulo_rad, self.pontos_scan_vis, mapa_surface)
