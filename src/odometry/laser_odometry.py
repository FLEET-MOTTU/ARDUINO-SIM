"""
Define a classe LaserOdometry.

ARQUITETURA:
Este módulo fornece uma fonte de odometria de alta precisão baseada em
"scan matching". Sua responsabilidade arquitetural é servir como uma alternativa
superior à odometria teórica (dead reckoning), usando dados de sensores para
inferir o movimento. O resultado é um "chute" de odometria muito mais acurado
para o algoritmo de SLAM principal.
"""

import numpy as np
import math
import sys
import io
from simpleicp import SimpleICP, PointCloud

class LaserOdometry:
    """
    Calcula a odometria do robô via alinhamento de scans (Scan Matching).

    Esta classe encapsula a lógica do algoritmo ICP (Iterative Closest Point)
    usando a biblioteca `simpleicp`. Ela funciona como uma "caixa-preta" que
    responde à pergunta: "Dado o scan anterior e o atual, qual foi o movimento
    relativo (translação e rotação) que ocorreu?".
    """
    def __init__(self):
        """
        Inicializa o solucionador ICP e o estado interno da classe.

        O objeto `icp_solver` é criado uma vez e reutilizado a cada ciclo para
        maior eficiência. `previous_scan_points` armazena a "imagem" do mundo
        do ciclo anterior para comparação.
        """
        self.previous_scan_points = None
        # Instancia o solucionador ICP, que manterá seu estado e configurações.
        self.icp_solver = SimpleICP()

    def _scan_to_points(self, scan_data_cm: list[tuple[int, int]]) -> np.ndarray:
        """
        Converte os dados brutos do sensor (formato polar) para uma nuvem de
        pontos cartesiana (formato X, Y, Z), que é o formato exigido pelo
        algoritmo ICP.
        """
        points = []
        distances = []
        
        for angulo_graus, dist_cm in scan_data_cm:
            # Filtra leituras inválidas para não poluir o cálculo do ICP.
            # Limitado a 300cm (3m) para evitar drift de long-range
            if 5 < dist_cm < 300:
                distances.append(dist_cm)
                # Converte o ângulo do servo (0-180) para um ângulo matemático (-90 a +90).
                angulo_rad = math.radians(angulo_graus - 90)
                x = dist_cm * math.cos(angulo_rad)
                y = dist_cm * math.sin(angulo_rad)
                # A biblioteca simpleicp opera em 3D, então adicionamos z=0 por compatibilidade.
                points.append([x, y, 0.0])
        
        if not points:
            return np.array([])
        
        # Filtro de outliers: remove pontos muito distantes da mediana
        # (ajuda a remover leituras espúrias que causam drift)
        # Apenas aplica se tiver pontos suficientes
        if len(distances) > 10:  # Aumentado de 5 para 10
            median_dist = np.median(distances)
            std_dist = np.std(distances)
            filtered_points = []
            for i, dist in enumerate(distances):
                # Critério mais liberal: aceita pontos dentro de 3 desvios padrão
                # OU dentro de 3x a mediana (o que for maior)
                max_dev = max(std_dist * 3, median_dist * 2.0)
                if abs(dist - median_dist) < max_dev:
                    filtered_points.append(points[i])
            
            # Só usa o filtro se ainda sobrar pelo menos 8 pontos
            if len(filtered_points) >= 8:
                return np.array(filtered_points)
        
        return np.array(points)

    def calculate_delta(self, current_scan_cm: list[tuple[int, int]]) -> tuple[float, float, float]:
        """
        Calcula o delta de odometria local (dx, dy, d_theta) a partir do scan atual.

        Este é o método público principal. Ele orquestra o processo de scan matching:
        1. Converte o scan atual para uma nuvem de pontos.
        2. Usa o algoritmo ICP para encontrar a matriz de transformação (H) que
           melhor alinha a nuvem de pontos anterior com a atual.
        3. Extrai os parâmetros de translação (dx, dy) e rotação (d_theta) da matriz H.
        4. Armazena a nuvem de pontos atual para ser usada no próximo ciclo.

        Returns:
            tuple[float, float, float]: O deslocamento no referencial LOCAL do robô
                                        (dx, dy, d_theta) em cm e radianos.
        """
        current_scan_points = self._scan_to_points(current_scan_cm)

        # Guarda de segurança para o primeiro ciclo ou para scans com poucos pontos válidos.
        # O ICP precisa de um mínimo de pontos (6 para 3D) para funcionar de forma confiável.
        if self.previous_scan_points is None or current_scan_points.shape[0] < 6:
            self.previous_scan_points = current_scan_points
            return (0.0, 0.0, 0.0)

        if self.previous_scan_points.shape[0] < 6:
            self.previous_scan_points = current_scan_points
            return (0.0, 0.0, 0.0)

        # Verifica se os scans são muito similares (robô não se moveu)
        # Calcula a diferença média entre os pontos
        if self.previous_scan_points.shape[0] == current_scan_points.shape[0]:
            diff = np.linalg.norm(current_scan_points - self.previous_scan_points, axis=1)
            mean_diff = np.mean(diff)
            if mean_diff < 1.0:  # Menos de 1cm de diferença média
                self.previous_scan_points = current_scan_points
                return (0.0, 0.0, 0.0)

        # Prepara os dados no formato que a biblioteca `simpleicp` exige.
        pc_fix = PointCloud(self.previous_scan_points, columns=["x", "y", "z"])
        pc_mov = PointCloud(current_scan_points, columns=["x", "y", "z"])

        # Executa o algoritmo de alinhamento com tratamento de erro.
        # Redireciona stdout para suprimir logs verbosos do SimpleICP
        try:
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()  # Captura output do ICP
            
            self.icp_solver.add_point_clouds(pc_fix, pc_mov)
            H, _, _, _ = self.icp_solver.run(
                max_overlap_distance=25,   # Aumentado de 10 para 25 (mais tolerante)
                max_iterations=30,         # Reduzido de 50 para 30 (mais rápido)
                min_change=0.001           # Aumentado de 0.0001 para 0.001 (menos iterações desnecessárias)
            )
        except Exception as e:
            print(f"[ICP ODOM] ERRO no matching: {e}. Retornando delta zero.", file=old_stdout)
            self.previous_scan_points = current_scan_points
            return (0.0, 0.0, 0.0)
        finally:
            sys.stdout = old_stdout  # Restaura stdout

        # Extrai os resultados da matriz de transformação homogênea 4x4.
        dx = H[0, 3]  # Translação em X (tx)
        dy = H[1, 3]  # Translação em Y (ty)
        d_theta = math.atan2(H[1, 0], H[0, 0]) # Rotação em torno de Z

        # Filtro de sanidade: limita movimentos muito grandes que indicam erro de matching
        # Em um ciclo típico, o robô não deve se mover mais que 20cm ou girar mais que 30°
        max_translation = 20.0  # cm (reduzido de 30)
        max_rotation = math.radians(30)  # rad (reduzido de 45)
        
        total_translation = math.sqrt(dx**2 + dy**2)
        
        if total_translation > max_translation or abs(d_theta) > max_rotation:
            print(f"[ICP ODOM] AVISO: Movimento anômalo detectado e filtrado "
                  f"(dx={dx:.2f}, dy={dy:.2f}, dθ={math.degrees(d_theta):.2f}°)")
            # Retorna movimento zero quando detecta anomalia
            self.previous_scan_points = current_scan_points
            return (0.0, 0.0, 0.0)

        # Armazena o scan atual para ser o "scan anterior" no próximo ciclo.
        self.previous_scan_points = current_scan_points

        print(f"[ICP ODOM] Delta Calculado: (dx={dx:.2f}, dy={dy:.2f}, dθ={math.degrees(d_theta):.2f}°)")
        return (dx, dy, d_theta)