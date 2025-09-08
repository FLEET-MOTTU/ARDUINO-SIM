"""
Este arquivo serve como a Única Fonte da Verdade para as especificações
físicas e de hardware do robô, garantindo que tanto o Cérebro (src/) quanto
a Simulação (simulation/) operem com base nos mesmos parâmetros.
"""

# Especificações de Movimento
VELOCIDADE_MAX_LINEAR_CM_S = 20.0
VELOCIDADE_MAX_ANGULAR_GRAUS_S = 90.0

# Especificações de Navegação
FORWARD_CONFIDENCE_THRESHOLD_CM = 75.0
STALLED_DISTANCE_THRESHOLD_CM = 40.0 # Se mover menos que isso em 30 ciclos, está parado
MAP_STABILITY_THRESHOLD_PIXELS = 50 # Se menos de 50 pixels mudaram, o mapa está estável
CYCLES_TO_CONFIRM_COMPLETION = 20   # Precisa de 50 ciclos estáveis seguidos para confirmar
MAP_COVERAGE_STABILITY_THRESHOLD = 20 

# Especificações do "Hardware" (Arduino)
MAX_VELOCIDADE_ARDUINO = 255.0
    