import os
import time
import math

from PIL import Image, ImageDraw

from src.config import settings


class Mapper:
    """Gerencia a criação e atualização da planta baixa."""
    def __init__(self):
        self.largura = settings.map_width_px
        self.altura = settings.map_height_px
        self.output_dir = settings.map_output_dir
        self.escala = 2 # Pixels/cm
        self.mapa_imagem = Image.new("L", (self.largura, self.altura), "black")
        self.desenho = ImageDraw.Draw(self.mapa_imagem)
        self.posicao_robo = (self.largura // 2, self.altura // 2)
        os.makedirs(self.output_dir, exist_ok=True)


    def adicionar_scan(self, dados_scan):
        print("MAPEAMENTO -> Adicionando novos pontos ao mapa...")
        for angulo_graus, dist_cm in dados_scan:
            if dist_cm > 0:
                angulo_rad = math.radians(angulo_graus)
                delta_x = dist_cm * math.cos(angulo_rad)
                delta_y = dist_cm * math.sin(angulo_rad)
                ponto_x = int(self.posicao_robo[0] + (delta_x * self.escala))
                ponto_y = int(self.posicao_robo[1] - (delta_y * self.escala)) # Y invertido
                if 0 <= ponto_x < self.largura and 0 <= ponto_y < self.altura:
                    self.desenho.point((ponto_x, ponto_y), fill="white")
    
    
    def salvar_mapa(self) -> str:
        """Salva a imagem do mapa com um timestamp e retorna o caminho."""
        timestamp = int(time.time())
        nome_arquivo = f"map_{timestamp}.png"
        caminho_completo = os.path.join(self.output_dir, nome_arquivo)
        self.mapa_imagem.save(caminho_completo)
        print(f"MAPEAMENTO -> Mapa salvo como '{caminho_completo}'")
        return caminho_completo
