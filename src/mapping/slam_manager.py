"""
SLAM Manager - Wrapper para BreezySLAM com Proteções Contra Drift

Encapsula algoritmo RMHC-SLAM fornecendo interface limpa e proteções:
- Limita deltas de odometria (15cm/20° por ciclo)
- Clamping de pose para bounds do mapa
- Conversão automática cm ↔ mm

Parâmetros Conservadores:
- map_quality=20 (estabilidade > detalhes)
- hole_width_mm=1200 (tolerante a ruído)

Autor: FLEET-MOTTU
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
    Adapter para BreezySLAM com proteções contra drift.
    
    Traduz dados da aplicação (cm/rad) para BreezySLAM (mm/deg) e vice-versa.
    Limita deltas absurdos e clamps pose dentro dos bounds do mapa.
    """
    def __init__(self, map_size_pixels: int = 500, map_size_meters: int = 25):
        """
        Configura SLAM com parâmetros conservadores.

        Args:
            map_size_pixels: Resolução do mapa (largura = altura)
            map_size_meters: Dimensão física do mapa
        """
        self.MAP_SIZE_PIXELS = map_size_pixels
        self.MAP_SIZE_METERS = map_size_meters
        self.LIDAR_SCAN_SIZE = 19  # O sensor envia 19 leituras (0 a 180 graus, com passo de 10)

        # Configura o modelo de sensor virtual que o BreezySLAM usará.
        # Parâmetros: (num_leituras, taxa_hz, angulo_span_graus, dist_max_mm)
        # Reduzido dist_max para 3000mm (3m) para evitar drift de long-range
        laser = Laser(self.LIDAR_SCAN_SIZE, 10, 180, 3000)
        
        # Instancia o algoritmo de SLAM com parâmetros ULTRA conservadores
        # para evitar motion blur e drift
        self.slam = RMHC_SLAM(
            laser, 
            self.MAP_SIZE_PIXELS, 
            map_size_meters,
            map_quality=20,       # MUITO reduzido - prioriza estabilidade sobre detalhes
            hole_width_mm=1200    # MUITO aumentado - ignora pequenas inconsistências
        )
        
        # Limites rígidos para a pose (em mm)
        self.max_x_mm = map_size_meters * 1000
        self.max_y_mm = map_size_meters * 1000
        self.min_x_mm = 0
        self.min_y_mm = 0

    def update(self, scan_data_cm: list[tuple[int, int]], odometry_delta: tuple[float, float, float]):
        """
        Alimenta o algoritmo de SLAM com novos dados de sensor e odometria.

        Este método realiza a "tradução" dos dados:
        1. Converte o scan de (ângulo, distância_cm) para uma lista de [distância_mm].
        2. Converte o delta de odometria de (dx_cm, dy_cm, dtheta_rad) para (dx_mm, dy_mm, dtheta_deg).
        3. Aplica limites ao delta de odometria para evitar drift.
        """
        # 1. Formata os dados do scan.
        scan_distancias_mm = [0] * self.LIDAR_SCAN_SIZE
        for angulo, dist_cm in scan_data_cm:
            indice = angulo // 10
            if 0 <= indice < self.LIDAR_SCAN_SIZE:
                scan_distancias_mm[indice] = dist_cm * 10

        # 2. Formata os dados da odometria com limitação.
        delta_x_cm = odometry_delta[0]
        delta_y_cm = odometry_delta[1]
        delta_theta_rad = odometry_delta[2]
        
        # Limita deltas muito grandes (provavelmente erros)
        MAX_DELTA_CM = 15.0  # MUITO reduzido - máximo 15cm por ciclo
        MAX_DELTA_THETA_RAD = math.radians(20)  # Reduzido para 20° por ciclo
        
        import math as m
        delta_dist = m.sqrt(delta_x_cm**2 + delta_y_cm**2)
        if delta_dist > MAX_DELTA_CM:
            # Escala para o máximo permitido
            scale = MAX_DELTA_CM / delta_dist
            delta_x_cm *= scale
            delta_y_cm *= scale
            print(f"[SLAM] ⚠️ Odometria limitada: {delta_dist:.1f}cm -> {MAX_DELTA_CM}cm")
        
        if abs(delta_theta_rad) > MAX_DELTA_THETA_RAD:
            delta_theta_rad = MAX_DELTA_THETA_RAD if delta_theta_rad > 0 else -MAX_DELTA_THETA_RAD
            print(f"[SLAM] ⚠️ Rotação limitada para ±{math.degrees(MAX_DELTA_THETA_RAD):.0f}°")
        
        delta_x_mm = delta_x_cm * 10
        delta_y_mm = delta_y_cm * 10
        delta_theta_deg = math.degrees(delta_theta_rad)
        odometry_mm_deg = (delta_x_mm, delta_y_mm, delta_theta_deg)

        # 3. Executa o passo de atualização do SLAM.
        self.slam.update(scan_distancias_mm, odometry_mm_deg)

    def get_corrected_pose_cm_rad(self) -> tuple[float, float, float]:
        """
        Consulta o SLAM para obter a pose mais provável do robô e a retorna
        nas unidades padrão da nossa aplicação (cm e radianos).
        
        Aplica limites rígidos (clamping) para evitar drift para fora do mapa.
        """
        x_mm, y_mm, theta_deg = self.slam.getpos()
        
        # Clamp para manter dentro dos limites do mapa
        x_mm = max(self.min_x_mm, min(self.max_x_mm, x_mm))
        y_mm = max(self.min_y_mm, min(self.max_y_mm, y_mm))
        
        # Normaliza theta para [-180, 180]
        while theta_deg > 180:
            theta_deg -= 360
        while theta_deg < -180:
            theta_deg += 360
        
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