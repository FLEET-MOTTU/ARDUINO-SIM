import pygame
import math

LARGURA, ALTURA = 800, 600
COR_FUNDO = (20, 20, 20)
COR_PAREDE = (200, 200, 200)
COR_ROBO = (0, 200, 100)
COR_SENSOR = (255, 50, 50)
ESCALA_VISUALIZACAO = 3.0 # pixels/cm

# Mapa simulado com paredes de (x1, y1) a (x2, y2)
PAREDES_CM = [
    # Bordas externas
    ((10, 10), (260, 10)),
    ((260, 10), (260, 160)),
    ((260, 160), (10, 160)),
    ((10, 160), (10, 10)),

    # Parede interna com porta
    ((100, 10), (100, 80)),
    ((100, 120), (100, 160)),

    # Obstáculo no meio
    ((150, 60), (200, 60)),
    ((200, 60), (200, 100)),
    ((200, 100), (150, 100)),
    ((150, 100), (150, 60)),
]


class Planta:
    def __init__(self):
        pygame.init()
        self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption("Simulador de Mundo 2D")
        self.paredes_px = [
            ( (p[0][0]*ESCALA_VISUALIZACAO, p[0][1]*ESCALA_VISUALIZACAO),
              (p[1][0]*ESCALA_VISUALIZACAO, p[1][1]*ESCALA_VISUALIZACAO) )
            for p in PAREDES_CM
        ]


    def desenhar(self, pos_robo_cm, angulo_robo_rad, pontos_scan_cm):
        self.tela.fill(COR_FUNDO)
        for parede in self.paredes_px:
            pygame.draw.line(self.tela, COR_PAREDE, parede[0], parede[1], 2)
        
        pos_robo_px = (pos_robo_cm[0] * ESCALA_VISUALIZACAO, pos_robo_cm[1] * ESCALA_VISUALIZACAO)
        
        robo_surf = pygame.Surface((15*ESCALA_VISUALIZACAO, 10*ESCALA_VISUALIZACAO), pygame.SRCALPHA)
        robo_surf.fill(COR_ROBO)
        pygame.draw.line(robo_surf, (0,0,0), (7.5*ESCALA_VISUALIZACAO, 5*ESCALA_VISUALIZACAO), (15*ESCALA_VISUALIZACAO, 5*ESCALA_VISUALIZACAO), 2)
        robo_rotacionado = pygame.transform.rotate(robo_surf, -math.degrees(angulo_robo_rad))
        rect = robo_rotacionado.get_rect(center=pos_robo_px)
        self.tela.blit(robo_rotacionado, rect)

        for angulo_rel_graus, dist_cm in pontos_scan_cm:
            if dist_cm > 0:
                angulo_total_rad = angulo_robo_rad + math.radians(angulo_rel_graus)
                ponto_final_px = (pos_robo_px[0] + dist_cm * ESCALA_VISUALIZACAO * math.cos(angulo_total_rad),
                                  pos_robo_px[1] - dist_cm * ESCALA_VISUALIZACAO * math.sin(angulo_total_rad))
                pygame.draw.line(self.tela, COR_SENSOR, pos_robo_px, ponto_final_px, 1)

        pygame.display.flip()


    def calcular_distancia(self, pos_robo_cm, angulo_scan_rad):
        x1, y1 = pos_robo_cm
        raio_longo = 1000 # cm
        x2, y2 = x1 + math.cos(angulo_scan_rad) * raio_longo, y1 - math.sin(angulo_scan_rad) * raio_longo
        dist_min = float('inf')

        for parede in PAREDES_CM:
            x3, y3 = parede[0]
            x4, y4 = parede[1]
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if den == 0: continue
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
            if 0 < t < 1 and u > 0:
                px, py = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
                dist = math.hypot(px - x1, py - y1)
                if dist < dist_min:
                    dist_min = dist
        return int(dist_min) if dist_min != float('inf') else 0
