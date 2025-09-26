"""
Define a classe Navigator, o componente de tomada de decisão do Cérebro.
"""

import random
from robot_specifications import FORWARD_CONFIDENCE_THRESHOLD_CM

class Navigator:
    """
    Implementa a estratégia de navegação reativa do robô.

    Esta classe funciona como o "estrategista" do robô. Sua responsabilidade
    é analisar os dados do sensor (scan) e, com base em um conjunto de regras
    e heurísticas, decidir qual a próxima ação de movimento a ser executada.
    Ela é completamente desacoplada do hardware e da execução do movimento.

    A estratégia de navegação é dividida em camadas hierárquicas:
    1. Evasão de Obstáculos: Prioridade máxima para evitar colisões iminentes.
    2. Exploração por Setores: Lógica para navegar em direção a espaços abertos.
    3. Inércia de Ação: Mecanismo para evitar oscilações ("dançar no lugar").
    """
    def __init__(self, danger_threshold_cm: float = 20.0):
        """
        Inicializa o navegador com seus parâmetros de comportamento.

        Args:
            danger_threshold_cm (float): A distância frontal mínima para acionar
                                         uma manobra de evasão de emergência.
        """
        self.DANGER_THRESHOLD_CM = danger_threshold_cm
        
        # --- Atributos de Estado para "Inércia de Ação" ---
        # Mantêm a memória da última ação de virada para garantir que o robô
        # se comprometa com uma direção, evitando mudanças de decisão erráticas.
        self.committed_action = None
        self.commitment_counter = 0
        self.COMMITMENT_CYCLES = 2  # Nº de ciclos para se "comprometer" com uma virada.

    def decide_next_action(self, scan_data_cm: list[tuple[int, int]]) -> dict:
        """
        Analisa o scan atual e retorna um dicionário de ação para o Chassis.
        """
        # 1. LÓGICA DE INÉRCIA: Se estiver comprometido com uma ação, a repete.
        if self.commitment_counter > 0:
            print(f"[NAVIGATOR] Mantendo o compromisso com a ação: '{self.committed_action['command']}'. "
                  f"Ciclos restantes: {self.commitment_counter}")
            self.commitment_counter -= 1
            return self.committed_action

        if not scan_data_cm:
            return self._commit_action({'command': 'q', 'speed': 0, 'duration': 0})

        # 2. LÓGICA DE EVASÃO: Verifica perigo iminente no cone frontal.
        distancia_perigo = 1000
        for angulo, dist_cm in scan_data_cm:
            if 70 <= angulo <= 110 and dist_cm > 0:
                distancia_perigo = min(distancia_perigo, dist_cm)

        if distancia_perigo < self.DANGER_THRESHOLD_CM:
            print(f"[NAVIGATOR] PERIGO IMEDIATO a {distancia_perigo:.1f}cm. Manobra evasiva.")
            direcao = random.choice(['a', 'd'])
            # Se compromete com a virada para garantir que saia da situação de perigo.
            return self._commit_action({'command': direcao, 'speed': 200, 'duration': 1.0}, commit_turns=True)

        # 3. LÓGICA DE EXPLORAÇÃO: Se não há perigo, busca o melhor caminho.
        max_dist_direita, max_dist_frente, max_dist_esquerda = 0, 0, 0
        for angulo, dist_cm in scan_data_cm:
            if 0 <= angulo < 70: max_dist_direita = max(max_dist_direita, dist_cm)
            elif 70 <= angulo <= 110: max_dist_frente = max(max_dist_frente, dist_cm)
            else: max_dist_esquerda = max(max_dist_esquerda, dist_cm)

        print(f"[NAVIGATOR] Exploração por Setores: D={max_dist_direita}cm, F={max_dist_frente}cm, E={max_dist_esquerda}cm")

        # 4. LÓGICA DE DECISÃO: Compara os setores para escolher a ação.
        # Se a frente está confiavelmente aberta, avança para fazer progresso.
        if max_dist_frente > FORWARD_CONFIDENCE_THRESHOLD_CM:
            print(f"[NAVIGATOR] -> Frente está aberta ({max_dist_frente}cm). Avançando com confiança.")
            return self._commit_action({'command': 'w', 'speed': 150, 'duration': 1.0})
        
        # Se a frente não é confiavelmente aberta, mas ainda é a melhor, avança.
        if max_dist_frente >= max_dist_direita and max_dist_frente >= max_dist_esquerda:
            print("[NAVIGATOR] -> Setor frontal é o melhor. Avançando.")
            return self._commit_action({'command': 'w', 'speed': 150, 'duration': 1.0})

        # Se não, vira para o lado mais promissor e se compromete com a virada.
        if max_dist_esquerda > max_dist_direita:
            print("[NAVIGATOR] -> Setor esquerdo é mais livre. Virando à esquerda.")
            return self._commit_action({'command': 'a', 'speed': 130, 'duration': 0.5}, commit_turns=True)
        else:
            print("[NAVIGATOR] -> Setor direito é mais livre. Virando à direita.")
            return self._commit_action({'command': 'd', 'speed': 130, 'duration': 0.5}, commit_turns=True)

    def _commit_action(self, action: dict, commit_turns: bool = False) -> dict:
        """
        Método auxiliar que gerencia o estado de "compromisso" da ação,
        ativando a inércia para as viradas.
        """
        self.committed_action = action
        if commit_turns and action['command'] in ('a', 'd'):
            self.commitment_counter = self.COMMITMENT_CYCLES
        else:
            # Não se compromete com avanços para reavaliar a situação a cada ciclo.
            self.commitment_counter = 0
        return action