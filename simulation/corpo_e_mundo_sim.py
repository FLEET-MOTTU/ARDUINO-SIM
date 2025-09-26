"""
Define a classe CorpoRoboSimulado, que representa a entidade física do robô
no mundo virtual, gerenciando sua pose, movimento e interações físicas.
"""

import math
from simulation.planta_virtual import Planta
from robot_specifications import (
    VELOCIDADE_MAX_LINEAR_CM_S,
    VELOCIDADE_MAX_ANGULAR_GRAUS_S,    
    SUBPASSOS_FISICA
)

class CorpoRoboSimulado:
    """
    Representa o corpo físico do robô e sua interação com o mundo virtual.

    ARQUITETURA:
    Esta classe é o "avatar" do robô na simulação. Ela mantém o estado de
    "verdade fundamental" (ground truth) da pose do robô. Ela é comandada
    pelo FirmwareSimulado e interage com a Planta para colisões e leituras
    de sensor. Crucialmente, ela também simula "encoders de roda" ao acumular
    o deslocamento real a cada frame, fornecendo uma odometria precisa para o Cérebro.
    """
    
    def __init__(self):
        """Inicializa o robô em uma posição padrão e zera suas velocidades e odometria."""
        self.mundo = Planta()
        self.x_cm, self.y_cm = 130, 140
        self.angulo_rad = math.radians(180)
        self.velocidade_linear = 0.0   # Percentual de -1.0 a 1.0
        self.velocidade_angular = 0.0  # Percentual de -1.0 a 1.0
        self.pontos_scan_vis = []
        
        # Atributos que simulam "encoders", acumulando o deslocamento real a cada frame.
        self.delta_x_acumulado = 0.0
        self.delta_y_acumulado = 0.0
        self.delta_theta_acumulado = 0.0

    def get_odometria_e_resetar(self) -> tuple[float, float, float]:
        """
        Fornece os dados acumulados do "encoder virtual" e zera os contadores.
        
        Este método é a interface para o Cérebro obter a odometria de alta precisão
        gerada pela simulação física.
        """
        odometria = (self.delta_x_acumulado, self.delta_y_acumulado, self.delta_theta_acumulado)
        self.delta_x_acumulado = 0.0
        self.delta_y_acumulado = 0.0
        self.delta_theta_acumulado = 0.0
        return odometria
    
    def set_velocidades(self, linear_percent: float, angular_percent: float):
        """Interface para o "controlador de motores", define as velocidades desejadas."""
        self.velocidade_linear = linear_percent
        self.velocidade_angular = angular_percent

    def get_distancia_em_angulo(self, angulo_servo_graus: int) -> int:
        """Interface para o "sensor", delega a medição ao mundo (`Planta`)."""
        angulo_relativo_rad = math.radians(angulo_servo_graus - 90)
        angulo_total_rad = self.angulo_rad + angulo_relativo_rad
        dist = self.mundo.calcular_distancia((self.x_cm, self.y_cm), angulo_total_rad)
        self.pontos_scan_vis.append((angulo_servo_graus, dist))
        return dist

    def limpar_visualizacao_scan(self):
        """Limpa os pontos do último scan para a renderização do próximo."""
        self.pontos_scan_vis = []

    def atualizar_fisica(self, dt: float):
        """
        O motor de física do robô, chamado a cada frame pelo loop principal.

        Executa a simulação de movimento, considerando as colisões:
        1.  Calcula a rotação e o deslocamento ideal para o intervalo de tempo `dt`.
        2.  Divide o movimento em `SUBPASSOS_FISICA` para uma detecção de colisão precisa.
        3.  Move o robô passo a passo, parando se colidir.
        4.  Calcula o deslocamento real e o acumula para a odometria.
        5.  Atualiza a pose "verdadeira" do robô.
        """
        x_inicial, y_inicial = self.x_cm, self.y_cm

        # Rotação
        rotacao = self.velocidade_angular * math.radians(VELOCIDADE_MAX_ANGULAR_GRAUS_S) * dt
        self.angulo_rad = self.normalize_angle(self.angulo_rad + rotacao)
        
        # Deslocamento
        deslocamento_desejado = self.velocidade_linear * VELOCIDADE_MAX_LINEAR_CM_S * dt
        dx_total = deslocamento_desejado * math.cos(self.angulo_rad)
        dy_total = deslocamento_desejado * math.sin(self.angulo_rad)
        
        x_final, y_final = self.x_cm, self.y_cm
        for i in range(SUBPASSOS_FISICA):
            prox_x = x_final + dx_total / SUBPASSOS_FISICA
            prox_y = y_final + dy_total / SUBPASSOS_FISICA
            if self.mundo.verificar_colisao_robo((prox_x, prox_y)):
                break
            x_final, y_final = prox_x, prox_y
        
        # Calcula o deslocamento que realmente ocorreu após a checagem de colisão.
        dx_real = x_final - x_inicial
        dy_real = y_final - y_inicial
        
        # Acumula o deslocamento real nos "encoders".
        self.delta_x_acumulado += dx_real
        self.delta_y_acumulado += dy_real
        self.delta_theta_acumulado += rotacao
        
        # Atualiza a posição final do robô.
        self.x_cm, self.y_cm = x_final, y_final

    def desenhar_na_tela(self, mapa_surface):
        """Delega a renderização para a classe Planta, fornecendo seu estado atual."""
        self.mundo.desenhar((self.x_cm, self.y_cm), self.angulo_rad, self.pontos_scan_vis, mapa_surface)
        
    @staticmethod
    def normalize_angle(rad: float) -> float:
        """Helper para manter o ângulo no intervalo [-pi, pi]."""
        return (rad + math.pi) % (2 * math.pi) - math.pi