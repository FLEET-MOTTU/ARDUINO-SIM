import math

class RobotState:
    """
    Representa a única fonte da verdade sobre a pose (posição e orientação) do robô.
    Armazena internamente a pose em centímetros e radianos.
    """
    def __init__(self, x_cm: float, y_cm: float, theta_rad: float):
        """
        Inicializa o estado do robô.
        
        Args:
            x_cm (float): Posição inicial no eixo X em centímetros.
            y_cm (float): Posição inicial no eixo Y em centímetros.
            theta_rad (float): Orientação inicial em radianos.
        """
        self.x_cm = x_cm
        self.y_cm = y_cm
        self.theta_rad = theta_rad

    def get_pose_cm_rad(self) -> tuple[float, float, float]:
        """Retorna a pose atual no formato (x_cm, y_cm, theta_rad)."""
        return self.x_cm, self.y_cm, self.theta_rad

    def get_pose_mm_deg(self) -> tuple[float, float, float]:
        """Retorna a pose atual convertida para (x_mm, y_mm, theta_deg)."""
        return self.x_cm * 10, self.y_cm * 10, math.degrees(self.theta_rad)

    def update_pose(self, x_cm: float, y_cm: float, theta_rad: float):
        """
        Atualiza a pose do robô com novos valores absolutos.
        
        Args:
            x_cm (float): Nova posição no eixo X em centímetros.
            y_cm (float): Nova posição no eixo Y em centímetros.
            theta_rad (float): Nova orientação em radianos.
        """
        self.x_cm = x_cm
        self.y_cm = y_cm
        self.theta_rad = self.normalize_angle(theta_rad)
    
    @staticmethod
    def normalize_angle(rad: float) -> float:
        """Normaliza um ângulo em radianos para o intervalo [-pi, pi]."""
        return (rad + math.pi) % (2 * math.pi) - math.pi

    def __repr__(self) -> str:
        """Retorna uma representação em string do estado para debugging."""
        return (f"State(x={self.x_cm:.2f}cm, y={self.y_cm:.2f}cm, "
                f"theta={math.degrees(self.theta_rad):.2f}deg)")