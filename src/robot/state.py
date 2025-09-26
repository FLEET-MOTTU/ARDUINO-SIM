"""
Define a classe RobotState, o container de estado para a pose do robô.

Este módulo serve como a "Fonte Única da Verdade" para a posição e orientação
do robô. Qualquer outro componente do Cérebro que precise saber a pose atual
deve consultar uma instância desta classe.
"""

import math

class RobotState:
    """
    Representa e gerencia a pose (posição e orientação) do robô.
    
    A convenção interna é armazenar a pose em centímetros para posição e
    radianos para orientação. A classe fornece métodos para acessar esses
    valores em outras unidades, conforme necessário por diferentes componentes.
    """
    def __init__(self, x_cm: float, y_cm: float, theta_rad: float):
        """
        Inicializa o estado do robô com uma pose absoluta.

        Args:
            x_cm (float): Posição inicial no eixo X em centímetros.
            y_cm (float): Posição inicial no eixo Y em centímetros.
            theta_rad (float): Orientação inicial em radianos.
        """
        self.x_cm = x_cm
        self.y_cm = y_cm
        self.theta_rad = self.normalize_angle(theta_rad)

    def get_pose_cm_rad(self) -> tuple[float, float, float]:
        """Retorna a pose no formato padrão da aplicação (cm, radianos)."""
        return self.x_cm, self.y_cm, self.theta_rad

    def get_pose_mm_deg(self) -> tuple[float, float, float]:
        """Retorna a pose convertida para milímetros e graus, útil para bibliotecas externas."""
        return self.x_cm * 10, self.y_cm * 10, math.degrees(self.theta_rad)

    def update_pose(self, x_cm: float, y_cm: float, theta_rad: float):
        """
        Define a pose do robô para um novo valor absoluto.

        Este método deve ser usado para sobrescrever o estado atual com uma
        informação mais confiável, tipicamente após receber uma correção
        de um sistema de localização como o SLAM.

        Args:
            x_cm (float): Nova posição X absoluta.
            y_cm (float): Nova posição Y absoluta.
            theta_rad (float): Nova orientação absoluta.
        """
        self.x_cm = x_cm
        self.y_cm = y_cm
        self.theta_rad = self.normalize_angle(theta_rad)

    def apply_delta(self, dx_cm: float, dy_cm: float, dtheta_rad: float):
        """
        Aplica um deslocamento incremental (delta) à pose atual.

        Utilizado para atualizar a pose com base em cálculos de odometria.
        Assume-se que o delta recebido já está no referencial global.

        Args:
            dx_cm (float): Variação em X (cm).
            dy_cm (float): Variação em Y (cm).
            dtheta_rad (float): Variação angular (radianos).
        """
        self.x_cm += dx_cm
        self.y_cm += dy_cm
        self.theta_rad = self.normalize_angle(self.theta_rad + dtheta_rad)
    
    @staticmethod
    def normalize_angle(rad: float) -> float:
        """
        Garante que o ângulo permaneça no intervalo [-pi, pi].

        Essencial para evitar que o valor do ângulo cresça indefinidamente e para
        manter a consistência dos cálculos trigonométricos.
        """
        return (rad + math.pi) % (2 * math.pi) - math.pi

    def __repr__(self) -> str:
        """Fornece uma representação textual clara do estado para fins de logging e depuração."""
        return (f"State(x={self.x_cm:.2f}cm, y={self.y_cm:.2f}cm, "
                f"theta={math.degrees(self.theta_rad):.2f}deg)")