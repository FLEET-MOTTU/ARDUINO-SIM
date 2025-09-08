import pygame
import math

LARGURA, ALTURA = 1200, 600
COR_FUNDO = (20, 20, 20)
COR_PAREDE = (200, 200, 200)
COR_ROBO = (0, 200, 100)
COR_SENSOR = (255, 50, 50)
ESCALA_VISUALIZACAO = 2.5
RAIO_ROBO_CM = 4.0

# Mapa simulado
PAREDES_CM = [
    # Bordas externas
    ((10, 10), (260, 10)),
    ((260, 10), (260, 160)),
    ((260, 160), (10, 160)),
    ((10, 160), (10, 10))
]

class Planta:
    def __init__(self):
        pygame.init()
        self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption("Simulador Robótico - [Esquerda: Realidade] | [Direita: Mapa do Robô]")

        # Converte paredes para coordenadas da tela
        self.paredes_px = []
        for p in PAREDES_CM:
            p1_px = (p[0][0] * ESCALA_VISUALIZACAO, ALTURA - (p[0][1] * ESCALA_VISUALIZACAO))
            p2_px = (p[1][0] * ESCALA_VISUALIZACAO, ALTURA - (p[1][1] * ESCALA_VISUALIZACAO))
            self.paredes_px.append((p1_px, p2_px))

        self.area_simulador = pygame.Rect(0, 0, LARGURA // 2, ALTURA)
        self.area_mapa = pygame.Rect(LARGURA // 2, 0, LARGURA // 2, ALTURA)

    def desenhar(self, pos_robo_cm, angulo_robo_rad, pontos_scan_cm, mapa_surface):
        self.tela.fill(COR_FUNDO)

        # Desenha paredes
        for parede in self.paredes_px:
            pygame.draw.line(self.tela, COR_PAREDE, parede[0], parede[1], 2)

        # Desenha robô
        pos_robo_px = (pos_robo_cm[0] * ESCALA_VISUALIZACAO, ALTURA - (pos_robo_cm[1] * ESCALA_VISUALIZACAO))
        pygame.draw.circle(self.tela, COR_ROBO, pos_robo_px, int(RAIO_ROBO_CM * ESCALA_VISUALIZACAO))

        # Frente do robô
        frente_x = pos_robo_px[0] + 8 * ESCALA_VISUALIZACAO * math.cos(angulo_robo_rad)
        frente_y = pos_robo_px[1] - 8 * ESCALA_VISUALIZACAO * math.sin(angulo_robo_rad)
        pygame.draw.line(self.tela, (0, 0, 0), pos_robo_px, (frente_x, frente_y), 3)

        # Desenha scan
        for angulo_rel_graus, dist_cm in pontos_scan_cm:
            if 0 < dist_cm < 200:
                angulo_total_rad = angulo_robo_rad + math.radians(angulo_rel_graus)
                ponto_final_px_x = pos_robo_px[0] + dist_cm * ESCALA_VISUALIZACAO * math.cos(angulo_total_rad)
                ponto_final_px_y = pos_robo_px[1] - dist_cm * ESCALA_VISUALIZACAO * math.sin(angulo_total_rad)
                pygame.draw.line(self.tela, COR_SENSOR, pos_robo_px, (ponto_final_px_x, ponto_final_px_y), 1)

        # Desenha mapa
        if mapa_surface:
            mapa_red = pygame.transform.scale(mapa_surface, self.area_mapa.size)
            self.tela.blit(mapa_red, self.area_mapa.topleft)

        pygame.draw.line(self.tela, (100, 100, 100), (LARGURA // 2, 0), (LARGURA // 2, ALTURA), 3)
        pygame.display.flip()

    def calcular_distancia(self, pos_robo_cm, angulo_scan_rad):
        """
        Calcula a distância até a parede considerando o raio do robô.
        Retorna a distância máxima de 200 cm se não houver parede.
        """
        x1, y1 = pos_robo_cm
        raio_longo = 1000  # Raio longo para projeção do feixe

        x2 = x1 + math.cos(angulo_scan_rad) * raio_longo
        y2 = y1 + math.sin(angulo_scan_rad) * raio_longo

        dist_min = float('inf')

        for parede in PAREDES_CM:
            x3, y3 = parede[0]
            x4, y4 = parede[1]
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if den == 0:
                continue
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
            if 0 < t < 1 and 0 < u < 1:
                px = x1 + t * (x2 - x1)
                py = y1 + t * (y2 - y1)
                dist = math.hypot(px - x1, py - y1) - RAIO_ROBO_CM
                if dist < 0:
                    dist = 0
                if dist < dist_min:
                    dist_min = dist

        final_dist = int(dist_min) if dist_min != float('inf') else 200
        return final_dist
