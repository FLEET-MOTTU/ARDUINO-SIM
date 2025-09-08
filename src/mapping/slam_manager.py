import sys
import os
import math
from PIL import Image

diretorio_do_projeto = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
caminho_para_biblioteca = os.path.join(diretorio_do_projeto, "libs", "BreezySLAM-master", "python")
sys.path.append(caminho_para_biblioteca)

try:
    from breezyslam.algorithms import RMHC_SLAM
    from breezyslam.sensors import Laser
except ImportError as e:
    print("="*50)
    print(f"ERRO CRÍTICO: Falha ao importar o BreezySLAM.")
    print(f"Verifique se o caminho está correto: {caminho_para_biblioteca}")
    print(f"Erro original: {e}")
    print("="*50)
    sys.exit(1)


class SLAMManager:
    """
    Wrapper que gerencia todas as interações com a biblioteca BreezySLAM.
    """
    def __init__(self, map_size_pixels: int = 500, map_size_meters: int = 25):
        """
        Inicializa o sensor virtual (Laser) e o algoritmo de SLAM.
        Args:
            map_size_pixels (int): A largura e altura do mapa em pixels.
            map_size_meters (int): A largura e altura do mapa em metros.
        """
        self.MAP_SIZE_PIXELS = map_size_pixels
        self.LIDAR_SCAN_SIZE = 19  # 19 leituras de 0 a 180 graus, com passo de 10

        # Configura o sensor virtual para o SLAM
        laser = Laser(self.LIDAR_SCAN_SIZE, 10, 180, 3000) # (leituras, taxa_hz, angulo_span_graus, dist_max_mm)
        
        # Inicializa o algoritmo de SLAM
        self.slam = RMHC_SLAM(laser, self.MAP_SIZE_PIXELS, map_size_meters)

    def update(self, scan_data_cm: list[tuple[int, int]], odometry_delta: tuple[float, float, float]):
        """
        Atualiza o SLAM com novos dados de scan e odometria.
        
        Args:
            scan_data_cm (list): Lista de tuplas (angulo_graus, distancia_cm).
            odometry_delta (tuple): Tupla (delta_x_cm, delta_y_cm, delta_theta_rad).
        """
        # 1. Converte os dados do scan para o formato que o BreezySLAM espera (lista de distâncias em mm)
        scan_distancias_mm = [0] * self.LIDAR_SCAN_SIZE
        for angulo, dist_cm in scan_data_cm:
            indice = angulo // 10
            if 0 <= indice < self.LIDAR_SCAN_SIZE:
                scan_distancias_mm[indice] = dist_cm * 10

        # 2. Converte a odometria para as unidades do BreezySLAM (mm e graus)
        delta_x_mm = odometry_delta[0] * 10
        delta_y_mm = odometry_delta[1] * 10
        delta_theta_deg = math.degrees(odometry_delta[2])
        odometry_mm_deg = (delta_x_mm, delta_y_mm, delta_theta_deg)

        # 3. Atualiza o algoritmo de SLAM
        self.slam.update(scan_distancias_mm, odometry_mm_deg)

    def get_corrected_pose_cm_rad(self) -> tuple[float, float, float]:
        """
        Retorna a pose corrigida pelo SLAM, já convertida para as unidades padrão (cm, rad).
        """
        x_mm, y_mm, theta_deg = self.slam.getpos()
        
        x_cm = x_mm / 10.0
        y_cm = y_mm / 10.0
        theta_rad = math.radians(theta_deg)
        
        return x_cm, y_cm, theta_rad

    def get_map_image(self) -> Image.Image:
        """
        Gera e retorna a imagem do mapa atual a partir do SLAM.
        """
        mapbytes = bytearray(self.MAP_SIZE_PIXELS * self.MAP_SIZE_PIXELS)
        self.slam.getmap(mapbytes)
        
        # Cria a imagem a partir do buffer de bytes
        mapa_imagem = Image.frombuffer(
            'L', (self.MAP_SIZE_PIXELS, self.MAP_SIZE_PIXELS), 
            bytes(mapbytes), 'raw', 'L', 0, 1
        ).convert("RGB")
        
        return mapa_imagem
