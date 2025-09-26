"""
Define a classe SLAMManager, que serve como uma interface (Adapter) para a
biblioteca externa BreezySLAM.
"""

import sys
import os
import math
from PIL import Image

# Bloco de código para garantir que a biblioteca local BreezySLAM seja encontrada.
# Isola a complexidade da configuração do ambiente do resto da aplicação.
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
    Encapsula toda a interação com a biblioteca BreezySLAM.

    ARQUITETURA:
    Esta classe atua como uma camada de abstração. Sua responsabilidade é
    traduzir os dados da nossa aplicação para o formato que a biblioteca
    BreezySLAM entende, executar o algoritmo e, em seguida, traduzir os
    resultados de volta para o formato utilizado pelo nosso sistema.
    Isso desacopla totalmente a lógica do nosso robô dos detalhes de
    implementação da biblioteca de SLAM.
    """
    def __init__(self, map_size_pixels: int = 500, map_size_meters: int = 25):
        """
        Configura e inicializa os componentes internos do BreezySLAM.

        Args:
            map_size_pixels (int): A resolução do mapa em pixels (largura e altura).
            map_size_meters (int): A dimensão do mapa em metros.
        """
        self.MAP_SIZE_PIXELS = map_size_pixels
        self.LIDAR_SCAN_SIZE = 19  # O sensor envia 19 leituras (0 a 180 graus, com passo de 10)

        # Configura o modelo de sensor virtual que o BreezySLAM usará.
        laser = Laser(self.LIDAR_SCAN_SIZE, 10, 180, 3000) # (leituras, taxa_hz, angulo_span_graus, dist_max_mm)
        
        # Instancia o algoritmo de SLAM.
        self.slam = RMHC_SLAM(laser, self.MAP_SIZE_PIXELS, map_size_meters)

    def update(self, scan_data_cm: list[tuple[int, int]], odometry_delta: tuple[float, float, float]):
        """
        Alimenta o algoritmo de SLAM com novos dados de sensor e odometria.

        Este método realiza a "tradução" dos dados:
        1. Converte o scan de (ângulo, distância_cm) para uma lista de [distância_mm].
        2. Converte o delta de odometria de (dx_cm, dy_cm, dtheta_rad) para (dx_mm, dy_mm, dtheta_deg).
        """
        # 1. Formata os dados do scan.
        scan_distancias_mm = [0] * self.LIDAR_SCAN_SIZE
        for angulo, dist_cm in scan_data_cm:
            indice = angulo // 10
            if 0 <= indice < self.LIDAR_SCAN_SIZE:
                scan_distancias_mm[indice] = dist_cm * 10

        # 2. Formata os dados da odometria.
        delta_x_mm = odometry_delta[0] * 10
        delta_y_mm = odometry_delta[1] * 10
        delta_theta_deg = math.degrees(odometry_delta[2])
        odometry_mm_deg = (delta_x_mm, delta_y_mm, delta_theta_deg)

        # 3. Executa o passo de atualização do SLAM.
        self.slam.update(scan_distancias_mm, odometry_mm_deg)

    def get_corrected_pose_cm_rad(self) -> tuple[float, float, float]:
        """
        Consulta o SLAM para obter a pose mais provável do robô e a retorna
        nas unidades padrão da nossa aplicação (cm e radianos).
        """
        x_mm, y_mm, theta_deg = self.slam.getpos()
        return x_mm / 10.0, y_mm / 10.0, math.radians(theta_deg)

    def get_map_image(self) -> Image.Image:
        """
        Extrai os dados brutos do mapa do SLAM e os converte em um objeto de
        imagem da biblioteca PIL, pronto para ser salvo ou exibido.
        """
        mapbytes = bytearray(self.MAP_SIZE_PIXELS * self.MAP_SIZE_PIXELS)
        self.slam.getmap(mapbytes)
        
        return Image.frombuffer(
            'L', (self.MAP_SIZE_PIXELS, self.MAP_SIZE_PIXELS), 
            bytes(mapbytes), 'raw', 'L', 0, 1
        ).convert("RGB")