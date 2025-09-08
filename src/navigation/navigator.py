# arquivo: src/navigation/navigator.py (VERSÃO 2.1 - COM INÉRCIA DE AÇÃO)

import random
from robot_specifications import FORWARD_CONFIDENCE_THRESHOLD_CM


class Navigator:
    """
    Decide a próxima ação com base em setores e possui uma "inércia" para evitar
    oscilações (dançar no lugar).
    """
    def __init__(self, danger_threshold_cm: float = 20.0):
        self.DANGER_THRESHOLD_CM = danger_threshold_cm
        
        # --- NOVAS VARIÁVEIS DE ESTADO PARA INÉRCIA ---
        self.committed_action = None
        self.commitment_counter = 0
        self.COMMITMENT_CYCLES = 2 # Número de ciclos para se "comprometer" com uma virada

    def decide_next_action(self, scan_data_cm: list[tuple[int, int]]) -> dict:
        # --- LÓGICA DE INÉRCIA ---
        # Se estamos "comprometidos" com uma ação, a executamos novamente.
        if self.commitment_counter > 0:
            print(f"[NAVIGATOR] Mantendo o compromisso com a ação: {self.committed_action['command']}. Ciclos restantes: {self.commitment_counter}")
            self.commitment_counter -= 1
            return self.committed_action

        if not scan_data_cm:
            return self._commit_action({'command': 'q', 'speed': 0, 'duration': 0})

        # --- Lógica de Evasão (sem alterações) ---
        distancia_perigo = 1000
        for angulo, dist_cm in scan_data_cm:
            if 70 <= angulo <= 110 and dist_cm > 0:
                distancia_perigo = min(distancia_perigo, dist_cm)

        if distancia_perigo < self.DANGER_THRESHOLD_CM:
            print(f"[NAVIGATOR] PERIGO IMEDIATO a {distancia_perigo:.1f}cm. Manobra evasiva.")
            direcao = random.choice(['a', 'd'])
            return self._commit_action({'command': direcao, 'speed': 200, 'duration': 1.0})

        # --- Lógica de Exploração por Setores (sem alterações) ---
        max_dist_direita, max_dist_frente, max_dist_esquerda = 0, 0, 0
        for angulo, dist_cm in scan_data_cm:
            if 0 <= angulo < 70: max_dist_direita = max(max_dist_direita, dist_cm)
            elif 70 <= angulo <= 110: max_dist_frente = max(max_dist_frente, dist_cm)
            else: max_dist_esquerda = max(max_dist_esquerda, dist_cm)

        print(f"[NAVIGATOR] Exploração por Setores: D={max_dist_direita}cm, F={max_dist_frente}cm, E={max_dist_esquerda}cm")

        # --- Lógica de Decisão e COMPROMISSO ---
        # 1. Se o caminho à frente é confiavelmente aberto, AVANCE.
        if max_dist_frente > FORWARD_CONFIDENCE_THRESHOLD_CM:
            print(f"[NAVIGATOR] -> Frente está aberta ({max_dist_frente}cm). Avançando com confiança.")
            return self._commit_action({'command': 'w', 'speed': 150, 'duration': 1.0})
        
        # 2. Caso contrário, se a frente ainda for a melhor opção, AVANCE.
        if max_dist_frente >= max_dist_direita and max_dist_frente >= max_dist_esquerda:
            print("[NAVIGATOR] -> Setor frontal é o melhor. Avançando.")
            return self._commit_action({'command': 'w', 'speed': 150, 'duration': 1.0})

        # 3. Se não, vire para o melhor lado.
        if max_dist_esquerda > max_dist_direita:
            print("[NAVIGATOR] -> Setor esquerdo é mais livre. Virando à esquerda.")
            return self._commit_action({'command': 'a', 'speed': 130, 'duration': 0.5}, commit_turns=True)
        else:
            print("[NAVIGATOR] -> Setor direito é mais livre. Virando à direita.")
            return self._commit_action({'command': 'd', 'speed': 130, 'duration': 0.5}, commit_turns=True)

    def _commit_action(self, action: dict, commit_turns: bool = False) -> dict:
        """Método auxiliar para registrar a ação e o contador de compromisso."""
        self.committed_action = action
        if commit_turns and action['command'] in ('a', 'd'):
            self.commitment_counter = self.COMMITMENT_CYCLES
        else:
            self.commitment_counter = 0 # Não se compromete a avançar, reavalia a cada ciclo
        return action