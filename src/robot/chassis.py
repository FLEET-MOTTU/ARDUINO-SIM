import math
import time

from src.hardware.serial_handler import SerialHandler
from robot_specifications import (
    VELOCIDADE_MAX_LINEAR_CM_S,
    VELOCIDADE_MAX_ANGULAR_GRAUS_S,
    MAX_VELOCIDADE_ARDUINO
)


class Chassis:
    """
    Controla os movimentos físicos do robô e calcula a odometria (dead reckoning)
    no referencial do próprio robô.
    """

    def __init__(self, serial_handler: SerialHandler):
        self.serial = serial_handler

    def execute_action(self, action: dict) -> tuple[float, float, float]:
        """
        Executa uma ação de movimento e retorna a odometria calculada no referencial local do robô.
        
        Args:
            action (dict): Ex: {'command': 'w', 'speed': 150, 'duration': 1.0}

        Returns:
            tuple[float, float, float]: O delta de odometria local (d_frente_cm, d_lado_cm, d_theta_rad).
                                        Para nós, d_lado_cm será sempre 0.
        """
        command_char = action.get('command', 'q')
        speed = action.get('speed', 0)
        duration = action.get('duration', 0)

        if speed > 0 and duration > 0:
            full_command = f"{command_char}{speed}"
            self.serial.enviar_comando(full_command)
            time.sleep(duration)
            self.serial.enviar_comando('q')

        return self._calculate_local_odometry_delta(command_char, speed, duration)

    def _calculate_local_odometry_delta(self, command_char: str, speed: int, duration: float) -> tuple[float, float, float]:
        """Calcula a mudança de pose no referencial local do robô."""
        delta_frente_cm = 0.0
        delta_lado_cm = 0.0  # Nosso robô não se move de lado (não é omnidirecional)
        delta_theta_rad = 0.0
        
        if duration == 0 or speed == 0:
            return delta_frente_cm, delta_lado_cm, delta_theta_rad
            
        velocidade_percentual = speed / MAX_VELOCIDADE_ARDUINO

        if command_char == 'w':
            delta_frente_cm = VELOCIDADE_MAX_LINEAR_CM_S  * velocidade_percentual * duration
        elif command_char == 's':
            delta_frente_cm = -VELOCIDADE_MAX_LINEAR_CM_S * velocidade_percentual * duration
        elif command_char in ('a', 'd'):
            angulo_virado_rad = math.radians(VELOCIDADE_MAX_ANGULAR_GRAUS_S * velocidade_percentual * duration)
            delta_theta_rad = angulo_virado_rad if command_char == 'a' else -angulo_virado_rad
        
        return delta_frente_cm, delta_lado_cm, delta_theta_rad