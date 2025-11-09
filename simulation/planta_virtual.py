"""
Define a classe Planta, que representa todo o ambiente de simulação 2D,
incluindo a geometria das paredes, a renderização gráfica e a simulação
de sensores.
"""

import pygame
import math
from robot_specifications import RAIO_ROBO_CM

# Constantes de visualização
LARGURA, ALTURA = 1200, 600
COR_FUNDO = (20, 20, 20)
COR_PAREDE = (200, 200, 200)
COR_ROBO = (0, 200, 100)
COR_SENSOR = (255, 50, 50)

# Geometria do mundo em centímetros.
# Formato: lista de retângulos (x, y, largura, altura)
ESPESSURA_PAREDE_CM = 2.0
PAREDES_RECTANGLES_CM = [
    # Quadrado Externo (250x250 cm)
    (10, 10, 250, ESPESSURA_PAREDE_CM),
    (10, 10, ESPESSURA_PAREDE_CM, 250),
    (260 - ESPESSURA_PAREDE_CM, 10, ESPESSURA_PAREDE_CM, 250),
    (10, 260 - ESPESSURA_PAREDE_CM, 250, ESPESSURA_PAREDE_CM),

    # Obstáculos Internos para teste de navegação
    (80, 80, 40, ESPESSURA_PAREDE_CM),
    (160, 80, 40, ESPESSURA_PAREDE_CM),
    (120, 150, ESPESSURA_PAREDE_CM, 50)
]

class Planta:
    """
    Gerencia a geometria, visualização e interações sensoriais do mundo simulado.
    
    ARQUITETURA:
    Esta classe encapsula toda a lógica do Pygame e do ambiente. Ela fornece
    uma API simples para o CorpoRoboSimulado interagir com o mundo através de
    métodos como `verificar_colisao_robo` (para física) e `calcular_distancia`
    (para sensores), sem expor os detalhes de implementação.
    """
    def __init__(self):
        pygame.init()
        self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption("Simulador Robótico - [Esquerda: Realidade] | [Direita: Mapa do Robô]")

        # Divide a tela em duas áreas de 600x600 pixels
        self.area_simulador = pygame.Rect(0, 0, LARGURA // 2, ALTURA)
        self.area_mapa = pygame.Rect(LARGURA // 2, 0, LARGURA // 2, ALTURA)

        # Calcula a escala de visualização dinamicamente para que o mundo sempre
        # caiba na área de simulação.
        max_x_cm = max(p[0] + p[2] for p in PAREDES_RECTANGLES_CM) + 10 # Margem de segurança
        max_y_cm = max(p[1] + p[3] for p in PAREDES_RECTANGLES_CM) + 10 # Margem de segurança
        escala_x = self.area_simulador.width / max_x_cm
        escala_y = self.area_simulador.height / max_y_cm
        self.escala_visualizacao = min(escala_x, escala_y)
        print(f"[VISUALIZACAO] Escala calculada automaticamente: {self.escala_visualizacao:.2f} pixels/cm")

        # --- Dupla Representação das Paredes ---
        # 1. Para a FÍSICA: Uma lista de objetos Rect, otimizada para detecção de colisão.
        self.paredes_rect_cm = [pygame.Rect(p) for p in PAREDES_RECTANGLES_CM]

        # 2. Para o SENSOR: Uma lista de segmentos de linha, necessária para o
        #    algoritmo de ray-casting do sensor ultrassônico.
        self.paredes_linhas_cm = []
        for rect in PAREDES_RECTANGLES_CM:
            x, y, w, h = rect
            p1, p2, p3, p4 = (x, y), (x + w, y), (x + w, y + h), (x, y + h)
            self.paredes_linhas_cm.extend([ (p1, p2), (p2, p3), (p3, p4), (p4, p1) ])

    def verificar_colisao_robo(self, pos_robo_cm: tuple[float, float]) -> bool:
        """
        Motor de colisão principal. Verifica se a área circular do robô
        se sobrepõe a alguma das paredes retangulares.
        """
        # Cria um retângulo que representa a "bounding box" do robô
        robo_rect = pygame.Rect(
            pos_robo_cm[0] - RAIO_ROBO_CM,
            pos_robo_cm[1] - RAIO_ROBO_CM,
            RAIO_ROBO_CM * 2,
            RAIO_ROBO_CM * 2
        )
        # Usa o método otimizado do Pygame para verificar a colisão com a lista de paredes.
        return robo_rect.collidelist(self.paredes_rect_cm) != -1

    def desenhar(self, pos_robo_cm, angulo_robo_rad, pontos_scan_cm, mapa_surface):
        """Motor de renderização. Desenha o estado atual da simulação na tela."""
        self.tela.fill(COR_FUNDO)

        # Desenha as paredes (retângulos)
        for parede_rect in self.paredes_rect_cm:
            # Converte as coordenadas de cm (com origem no canto inferior esquerdo) para
            # pixels do Pygame (com origem no canto superior esquerdo).
            parede_rect_px = pygame.Rect(
                parede_rect.x * self.escala_visualizacao,
                ALTURA - ((parede_rect.y + parede_rect.height) * self.escala_visualizacao),
                parede_rect.width * self.escala_visualizacao,
                parede_rect.height * self.escala_visualizacao
            )
            pygame.draw.rect(self.tela, COR_PAREDE, parede_rect_px)

        # Desenha o robô e sua orientação
        pos_robo_px = (pos_robo_cm[0] * self.escala_visualizacao, ALTURA - (pos_robo_cm[1] * self.escala_visualizacao))
        pygame.draw.circle(self.tela, COR_ROBO, pos_robo_px, int(RAIO_ROBO_CM * self.escala_visualizacao))
        frente_x = pos_robo_px[0] + 8 * self.escala_visualizacao * math.cos(angulo_robo_rad)
        frente_y = pos_robo_px[1] - 8 * self.escala_visualizacao * math.sin(angulo_robo_rad)
        pygame.draw.line(self.tela, (0, 0, 0), pos_robo_px, (frente_x, frente_y), 3)

        # Desenha os raios do sensor
        for angulo_servo_graus, dist_cm in pontos_scan_cm:
            if 0 < dist_cm < 300:
                angulo_relativo_rad = math.radians(angulo_servo_graus - 90)
                angulo_total_rad = angulo_robo_rad + angulo_relativo_rad
                ponto_final_px_x = pos_robo_px[0] + dist_cm * self.escala_visualizacao * math.cos(angulo_total_rad)
                ponto_final_px_y = pos_robo_px[1] - dist_cm * self.escala_visualizacao * math.sin(angulo_total_rad)
                pygame.draw.line(self.tela, COR_SENSOR, pos_robo_px, (ponto_final_px_x, ponto_final_px_y), 1)

        # Desenha o mapa gerado pelo Cérebro no painel direito
        if mapa_surface:
            mapa_redimensionado = pygame.transform.scale(mapa_surface, self.area_mapa.size)
            self.tela.blit(mapa_redimensionado, self.area_mapa.topleft)

        # Desenha a linha divisória e atualiza a tela
        pygame.draw.line(self.tela, (100, 100, 100), (LARGURA // 2, 0), (LARGURA // 2, ALTURA), 3)
        pygame.display.flip()

    def calcular_distancia(self, pos_robo_cm: tuple[float, float], angulo_scan_rad: float) -> int:
        """
        Motor de simulação do sensor. Usa um algoritmo de ray-casting para
        calcular a distância até a parede mais próxima em um determinado ângulo.
        """
        x1, y1 = pos_robo_cm
        # Projeta um raio longo a partir da posição do robô
        raio_longo = 3000
        x2 = x1 + math.cos(angulo_scan_rad) * raio_longo
        y2 = y1 + math.sin(angulo_scan_rad) * raio_longo
        dist_min = float('inf')

        # Verifica a intersecção do raio com cada segmento de parede (representação de linhas)
        for parede in self.paredes_linhas_cm:
            x3, y3 = parede[0]
            x4, y4 = parede[1]
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if den == 0: continue # Linhas paralelas
            
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
            
            # Se houver uma intersecção válida
            if 0 < t < 1 and 0 < u < 1:
                px = x1 + t * (x2 - x1)
                py = y1 + t * (y2 - y1)
                dist = math.hypot(px - x1, py - y1) - RAIO_ROBO_CM
                if dist < 0: dist = 0
                if dist < dist_min: dist_min = dist
        
        # Retorna a distância máxima do sensor se nenhum obstáculo for encontrado
        return int(dist_min) if dist_min != float('inf') else 300