"""
Este arquivo serve como as especificações
físicas, de hardware e de comportamento do robô.

Centralizar estas constantes aqui garante que tanto o "Cérebro" (lógica em src/)
quanto o "Mundo" (a simulação em simulation/) operem com base nos mesmos
parâmetros, evitando a dessincronização entre o modelo e a realidade simulada.

Este é o principal painel de controle para tunar o comportamento do robô
"""

# ==============================================================================
# ESPECIFICAÇÕES FÍSICAS E DE HARDWARE
# Define as capacidades do robô, impactando tanto a simulação quanto a
# odometria teórica calculada pelo Cérebro.
# ==============================================================================
VELOCIDADE_MAX_LINEAR_CM_S = 8.0
VELOCIDADE_MAX_ANGULAR_GRAUS_S = 45.0
MAX_VELOCIDADE_ARDUINO = 255.0
RAIO_ROBO_CM = 4.0

# ==============================================================================
# PARÂMETROS DA SIMULAÇÃO FÍSICA
# Controlam a precisão e o comportamento do motor de física da simulação.
# ==============================================================================
SUBPASSOS_FISICA = 10

# ==============================================================================
# PARÂMETROS DE NAVEGAÇÃO E MISSÃO
# Controlam a inteligência de alto nível e os critérios de decisão do robô.
# ==============================================================================
FORWARD_CONFIDENCE_THRESHOLD_CM = 75.0
STALLED_DISTANCE_THRESHOLD_CM = 20.0
MAP_COVERAGE_STABILITY_THRESHOLD = 50
CYCLES_TO_CONFIRM_COMPLETION = 75