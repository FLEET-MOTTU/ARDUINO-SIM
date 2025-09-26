"""
Este arquivo serve como a Única Fonte da Verdade para as especificações
físicas, de hardware e de comportamento do robô.

Centralizar estas constantes aqui garante que tanto o "Cérebro" (lógica em src/)
quanto o "Mundo" (a simulação em simulation/) operem com base nos mesmos
parâmetros, evitando a dessincronização entre o modelo e a realidade simulada.

Este é o principal painel de controle para "tunar" o comportamento do robô
sem precisar alterar a lógica central.
"""

# ==============================================================================
# ESPECIFICAÇÕES FÍSICAS E DE HARDWARE
# Define as capacidades do robô, impactando tanto a simulação quanto a
# odometria teórica calculada pelo Cérebro.
# ==============================================================================
VELOCIDADE_MAX_LINEAR_CM_S = 20.0
VELOCIDADE_MAX_ANGULAR_GRAUS_S = 90.0
MAX_VELOCIDADE_ARDUINO = 255.0
RAIO_ROBO_CM = 4.0

# ==============================================================================
# PARÂMETROS DA SIMULAÇÃO FÍSICA
# Controlam a precisão e o comportamento do motor de física da simulação.
# ==============================================================================

# Aumentar este número torna a detecção de colisão mais precisa, prevenindo
# que o robô "atravesse" paredes finas em alta velocidade, ao custo de um
# processamento ligeiramente maior.
SUBPASSOS_FISICA = 10

# ==============================================================================
# PARÂMETROS DE NAVEGAÇÃO E MISSÃO
# Controlam a inteligência de alto nível e os critérios de decisão do robô.
# ==============================================================================

# Limiar de confiança para o Navigator avançar. Se o setor frontal tiver uma
# distância maior que este valor, o robô avançará, mesmo que os setores
# laterais sejam marginalmente mais abertos. Previne hesitação em espaços amplos.
FORWARD_CONFIDENCE_THRESHOLD_CM = 75.0

# Limiar para a lógica de fim de missão considerar o robô "parado". Se o
# deslocamento total comandado em N ciclos for menor que este valor, a condição
# de estagnação do robô é atendida.
STALLED_DISTANCE_THRESHOLD_CM = 20.0

# Limiar de estabilidade do mapa. Se o número de novos pixels explorados
# entre ciclos for menor que este valor, o mapa é considerado "estável".
MAP_COVERAGE_STABILITY_THRESHOLD = 50

# Número de ciclos consecutivos em que o robô precisa estar "parado" E o mapa
# "estável" para que a missão seja declarada como concluída. Previne paradas
# prematuras.
CYCLES_TO_CONFIRM_COMPLETION = 75