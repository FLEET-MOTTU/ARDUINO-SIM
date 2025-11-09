"""
Define a classe Chassis, responsável pela execução de movimentos e pelo
cálculo da odometria teórica.
"""

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
    Representa a interface de controle do chassi do robô.

    Esta classe possui duas responsabilidades principais:
    1.  Atuação: Traduz uma ação de alto nível (recebida do Navigator) em uma
        sequência de comandos seriais cronometrados para o firmware.
    2.  Estimação de Odometria: Calcula o deslocamento teórico ("dead reckoning")
        resultante da ação executada. Este cálculo é feito no referencial
        local do robô e serve como o "chute" inicial para o algoritmo SLAM.
    """
    def __init__(self, serial_handler: SerialHandler):
        """
        Inicializa o Chassis com uma dependência do SerialHandler.

        Args:
            serial_handler (SerialHandler): O objeto que gerencia a comunicação
                                            serial de baixo nível com o corpo.
        """
        self.serial = serial_handler

    def execute_action(self, action: dict) -> tuple[float, float, float]:
        """
        Executa uma ação de movimento e retorna a odometria local teórica.

        O fluxo de execução é:
        1. Envia o comando de movimento (ex: 'w150').
        2. Aguarda a duração da ação.
        3. Envia o comando para parar ('q').
        4. Retorna o deslocamento que teoricamente deveria ter ocorrido.

        Args:
            action (dict): Dicionário que descreve a ação a ser tomada.

        Returns:
            tuple[float, float, float]: Um tuple representando o delta de
                                        odometria local (d_frente_cm, d_lado_cm, d_theta_rad).
        """
        command_char = action.get('command', 'q')
        speed = action.get('speed', 0)
        duration = action.get('duration', 0)

        print(f"[CHASSIS] Executando ação: cmd='{command_char}', speed={speed}, duration={duration}s")

        if speed > 0 and duration > 0:
            full_command = f"{command_char}{speed}"
            self.serial.enviar_comando(full_command)
            print(f"[CHASSIS] Aguardando {duration}s...")
            time.sleep(duration)
            print(f"[CHASSIS] Movimento completo, enviando parar...")
            self.serial.enviar_comando('q')
        else:
            print(f"[CHASSIS] ⚠️ Ação inválida (speed={speed}, duration={duration}) - enviando parar diretamente")
            self.serial.enviar_comando('q')
        
        return self._calculate_local_odometry_delta(command_char, speed, duration)

    def _calculate_local_odometry_delta(self, command_char: str, speed: int, duration: float) -> tuple[float, float, float]:
        """
        Calcula a mudança de pose teórica baseada no "modelo físico" do robô.

        Este cálculo é puramente teórico e não considera interações com o
        ambiente (como colisões). O resultado é sempre no referencial do robô
        (movimento para frente/trás e rotação).
        """
        delta_frente_cm = 0.0
        delta_lado_cm = 0.0  # robô não possui movimento lateral
        delta_theta_rad = 0.0
        
        if duration > 0 and speed > 0:
            velocidade_percentual = speed / MAX_VELOCIDADE_ARDUINO
            if command_char == 'w':
                delta_frente_cm = VELOCIDADE_MAX_LINEAR_CM_S * velocidade_percentual * duration
            elif command_char == 's':
                delta_frente_cm = -VELOCIDADE_MAX_LINEAR_CM_S * velocidade_percentual * duration
            elif command_char in ('a', 'd'):
                angulo_virado_rad = math.radians(VELOCIDADE_MAX_ANGULAR_GRAUS_S * velocidade_percentual * duration)
                delta_theta_rad = angulo_virado_rad if command_char == 'a' else -angulo_virado_rad
        
        return delta_frente_cm, delta_lado_cm, delta_theta_rad