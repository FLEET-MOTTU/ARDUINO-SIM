# import os
# import time
# import math

# from PIL import Image, ImageDraw

# from src.config import settings


# class Mapper:
#     """Gerencia a criação e atualização da planta baixa."""
#     def __init__(self):
#         self.largura = settings.map_width_px
#         self.altura = settings.map_height_px
#         self.output_dir = settings.map_output_dir
#         self.escala = 2 # Pixels/cm
#         self.mapa_imagem = Image.new("L", (self.largura, self.altura), "black")
#         self.desenho = ImageDraw.Draw(self.mapa_imagem)
#         self.posicao_robo = (self.largura // 2, self.altura // 2)
#         os.makedirs(self.output_dir, exist_ok=True)


#     def adicionar_scan(self, dados_scan):
#         print("MAPEAMENTO -> Adicionando novos pontos ao mapa...")
#         for angulo_graus, dist_cm in dados_scan:
#             if dist_cm > 0:
#                 angulo_rad = math.radians(angulo_graus)
#                 delta_x = dist_cm * math.cos(angulo_rad)
#                 delta_y = dist_cm * math.sin(angulo_rad)
#                 ponto_x = int(self.posicao_robo[0] + (delta_x * self.escala))
#                 ponto_y = int(self.posicao_robo[1] - (delta_y * self.escala)) # Y invertido
#                 if 0 <= ponto_x < self.largura and 0 <= ponto_y < self.altura:
#                     self.desenho.point((ponto_x, ponto_y), fill="white")
    
    
#     def salvar_mapa(self) -> str:
#         """Salva a imagem do mapa com um timestamp e retorna o caminho."""
#         timestamp = int(time.time())
#         nome_arquivo = f"map_{timestamp}.png"
#         caminho_completo = os.path.join(self.output_dir, nome_arquivo)
#         self.mapa_imagem.save(caminho_completo)
#         print(f"MAPEAMENTO -> Mapa salvo como '{caminho_completo}'")
#         return caminho_completo

import os
import time
import math

from PIL import Image, ImageDraw

from src.config import settings


class Mapper:
    """Gerencia a criação e atualização INCREMENTAL da planta baixa."""
    def __init__(self):
        self.largura = settings.map_width_px
        self.altura = settings.map_height_px
        self.output_dir = settings.map_output_dir
        self.escala = 2.0        
        self.mapa_imagem = Image.new("L", (self.largura, self.altura), "black")
        self.desenho = ImageDraw.Draw(self.mapa_imagem)
        
        os.makedirs(self.output_dir, exist_ok=True)


    def adicionar_scan(self, dados_scan, pose_robo):
        """
        Adiciona os pontos de um novo scan ao mapa existente,
        considerando a posição e orientação atual do robô.
        'pose_robo' é um dicionário: {'x': cm, 'y': cm, 'theta_rad': radianos}
        """
        robo_x_px = pose_robo['x'] * self.escala
        robo_y_px = pose_robo['y'] * self.escala
        
        for angulo_relativo_graus, dist_cm in dados_scan:
            if 0 < dist_cm < 200:
                
                # O ângulo global do raio do sensor (orientação do robô + o ângulo do sensor)
                angulo_relativo_rad = math.radians(angulo_relativo_graus)
                angulo_global_rad = pose_robo['theta_rad'] + angulo_relativo_rad
                
                # Calcula a posição do ponto detectado no mundo (em cm)
                ponto_x_cm = pose_robo['x'] + dist_cm * math.cos(angulo_global_rad)
                ponto_y_cm = pose_robo['y'] + dist_cm * math.sin(angulo_global_rad)
                
                # Converte a posição do ponto para pixels no mapa
                ponto_x_px = int(ponto_x_cm * self.escala)
                ponto_y_px = int(self.altura - (ponto_y_cm * self.escala))
                
                # Desenha o ponto no mapa
                if 0 <= ponto_x_px < self.largura and 0 <= ponto_y_px < self.altura:
                    self.desenho.point((ponto_x_px, ponto_y_px), fill="white")


    def salvar_mapa(self) -> str:
        """Salva a imagem do mapa ATUALIZADO com um timestamp e retorna o caminho."""
        timestamp = int(time.time())
        nome_arquivo = f"map_{timestamp}.png"
        caminho_completo = os.path.join(self.output_dir, nome_arquivo)

        self.mapa_imagem.save(caminho_completo)

        return caminho_completo
