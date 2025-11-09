"""
Navigator - Sistema de Navegação Autônoma com Memória Espacial

Implementa lógica de decisão inteligente para exploração de ambientes,
evitando loops através de grid de memória e detecção de perigo iminente.

Estratégia Hierárquica:
1. Compromisso com ação anterior (evita oscilações)
2. Evasão de perigo (<30cm = ré, <50cm = rotação)
3. Escape de loops (detecta 4 células em 10 movimentos)
4. Exploração biased (áreas inexploradas prioritárias)

Autor: FLEET-MOTTU
"""

import random
import numpy as np
from collections import deque
from robot_specifications import FORWARD_CONFIDENCE_THRESHOLD_CM

class Navigator:
    """
    Navegação autônoma com memória espacial e anti-loop.
    
    Grid 20x20 (50cm/célula) rastreia visitas para bias de exploração.
    Bias dinâmico: 0 visitas=+200cm, 1=+50cm, 2=-50cm, 3+=-150cm
    """
    def __init__(self, danger_threshold_cm: float = 50.0, grid_size_cm: float = 50.0, map_size_m: float = 10.0):
        """
        Inicializa navegador com parâmetros de comportamento.

        Args:
            danger_threshold_cm: Distância para acionar evasão de obstáculo
            grid_size_cm: Tamanho de cada célula do grid de memória
            map_size_m: Tamanho total do mapa (para dimensionar grid)
        """
        self.DANGER_THRESHOLD_CM = danger_threshold_cm
        
        # --- Memória Espacial (Grid de Visitas) ---
        self.grid_size_cm = grid_size_cm
        map_size_cm = map_size_m * 100
        self.grid_cells = int(map_size_cm / grid_size_cm)
        self.visit_grid = np.zeros((self.grid_cells, self.grid_cells), dtype=int)
        self.position_history = deque(maxlen=15)  # Reduzido de 20 para 15
        self.stuck_threshold = 3  # Reduzido de 5 para 3 (mais sensível)
        
        # Anti-loop: Cooldown para evitar rotações infinitas
        self.last_loop_escape_time = 0
        self.loop_escape_cooldown = 10  # Segundos entre manobras anti-loop
        self.consecutive_loop_escapes = 0  # Contador de escapes consecutivos
        self.max_consecutive_escapes = 2  # Máximo de escapes antes de desistir
        
        # --- Atributos de Estado para "Inércia de Ação" ---
        # Mantêm a memória da última ação de virada para garantir que o robô
        # se comprometa com uma direção, evitando mudanças de decisão erráticas.
        self.committed_action = None
        self.commitment_counter = 0
        self.COMMITMENT_CYCLES = 2  # Nº de ciclos para se "comprometer" com uma virada.

    def _pos_to_grid(self, x_cm: float, y_cm: float) -> tuple:
        """Converte posição em cm para índice de célula do grid."""
        col = int(x_cm / self.grid_size_cm)
        row = int(y_cm / self.grid_size_cm)
        col = max(0, min(self.grid_cells - 1, col))
        row = max(0, min(self.grid_cells - 1, row))
        return (row, col)
    
    def update_position(self, x_cm: float, y_cm: float):
        """Atualiza a memória espacial com a posição atual do robô."""
        grid_pos = self._pos_to_grid(x_cm, y_cm)
        self.visit_grid[grid_pos] += 1
        self.position_history.append(grid_pos)
        
        visit_count = self.visit_grid[grid_pos]
        if visit_count > 1:
            print(f"[NAVIGATOR] Posição ({x_cm:.0f}, {y_cm:.0f}) já visitada {visit_count}x")
    
    def is_stuck_in_loop(self) -> bool:
        """Detecta se o robô está preso em um loop (visitando mesmas células)."""
        if len(self.position_history) < 10:  # Aumentado para ter histórico suficiente
            return False
        
        # Conta visitas únicas nas últimas 10 posições
        recent_positions = list(self.position_history)[-10:]
        unique_positions = len(set(recent_positions))
        
        # Se visitou menos de 4 células únicas em 10 movimentos = loop
        if unique_positions < 4:
            print(f"[NAVIGATOR] ⚠️ LOOP DETECTADO! Apenas {unique_positions} células únicas em 10 movimentos")
            return True
        return False
    
    def get_exploration_bias(self, x_cm: float, y_cm: float, theta_deg: float, direction: str) -> float:
        """
        Calcula bias de exploração para uma direção baseado em áreas já visitadas.
        
        Args:
            x_cm, y_cm: Posição atual
            theta_deg: Orientação atual
            direction: 'front', 'left', ou 'right'
        
        Returns:
            Bonus em cm para adicionar à distância do setor (favorece não-visitados)
        """
        import math
        
        # Calcula posição aproximada se mover nessa direção
        move_distance = 100  # cm (estimativa)
        
        if direction == 'front':
            angle_offset = 0
        elif direction == 'left':
            angle_offset = 45
        elif direction == 'right':
            angle_offset = -45
        else:
            return 0
        
        target_angle = math.radians(theta_deg + angle_offset)
        target_x = x_cm + move_distance * math.cos(target_angle)
        target_y = y_cm + move_distance * math.sin(target_angle)
        
        target_grid = self._pos_to_grid(target_x, target_y)
        visits = self.visit_grid[target_grid]
        
        # Bonus MUITO mais agressivo: penaliza FORTEMENTE áreas visitadas
        # Não visitada = +200cm, 1x = +50cm, 2x = -50cm, 3+x = -150cm
        if visits == 0:
            bonus = 200
        elif visits == 1:
            bonus = 50
        elif visits == 2:
            bonus = -50
        else:
            bonus = -150  # Penalidade severa para áreas muito visitadas
        
        if abs(bonus) > 0:
            print(f"[NAVIGATOR] Direção {direction}: {bonus:+.0f}cm bias (visitas: {visits})")
        
        return bonus

    def decide_next_action(self, scan_data_cm: list[tuple[int, int]], robot_pose: tuple = None) -> dict:
        """
        Analisa o scan atual e retorna um dicionário de ação para o Chassis.
        
        Args:
            scan_data_cm: Lista de (angulo, distancia_cm)
            robot_pose: Tupla (x_cm, y_cm, theta_deg) - pose atual do robô
        """
        # Atualiza memória espacial se pose fornecida
        if robot_pose is not None:
            x_cm, y_cm, theta_deg = robot_pose
            self.update_position(x_cm, y_cm)
        
        # 1. LÓGICA DE INÉRCIA: Se estiver comprometido com uma ação, a repete.
        if self.commitment_counter > 0:
            print(f"[NAVIGATOR] Mantendo o compromisso com a ação: '{self.committed_action['command']}'. "
                  f"Ciclos restantes: {self.commitment_counter}")
            self.commitment_counter -= 1
            return self.committed_action

        if not scan_data_cm:
            return self._commit_action({'command': 'q', 'speed': 0, 'duration': 0})

        # 2. DETECÇÃO DE LOOP: Se preso em loop, força exploração aleatória
        import time
        current_time = time.time()
        
        if self.is_stuck_in_loop():
            # Cooldown: evita rotações infinitas
            if current_time - self.last_loop_escape_time < self.loop_escape_cooldown:
                print("[NAVIGATOR] ⏸️ Loop detectado mas em cooldown - usando exploração normal")
                self.consecutive_loop_escapes = 0  # Reset contador
            elif self.consecutive_loop_escapes >= self.max_consecutive_escapes:
                print("[NAVIGATOR] 🛑 MUITAS manobras anti-loop! Parando por 3 segundos...")
                self.consecutive_loop_escapes = 0  # Reset contador
                return self._commit_action({'command': 'q', 'speed': 0, 'duration': 3.0})
            else:
                print(f"[NAVIGATOR] 🔄 Executando manobra anti-loop #{self.consecutive_loop_escapes + 1}: avanço forçado")
                self.last_loop_escape_time = current_time
                self.consecutive_loop_escapes += 1
                # Em vez de girar, AVANÇA na direção atual para sair da área
                return self._commit_action({'command': 'w', 'speed': 255, 'duration': 2.0}, commit_turns=True)
        else:
            # Não está em loop: reseta contador
            self.consecutive_loop_escapes = 0

        # 3. LÓGICA DE EVASÃO: Verifica perigo iminente no cone frontal.
        distancia_perigo = 1000
        for angulo, dist_cm in scan_data_cm:
            if 70 <= angulo <= 110 and dist_cm > 0:
                distancia_perigo = min(distancia_perigo, dist_cm)

        if distancia_perigo < self.DANGER_THRESHOLD_CM:
            print(f"[NAVIGATOR] 🚨 PERIGO IMINENTE! Obstáculo a {distancia_perigo:.1f}cm.")
            
            # Se MUITO próximo (<30cm), RECUA antes de girar
            if distancia_perigo < 30.0:
                print(f"[NAVIGATOR] 🔙 RÉ DE EMERGÊNCIA! Recuando 0.5s antes de girar...")
                return self._commit_action({'command': 's', 'speed': 200, 'duration': 0.5}, commit_turns=True)
            else:
                # Senão, só gira
                print(f"[NAVIGATOR] 🔄 Girando 270° para desviar...")
                return self._commit_action({'command': 'd', 'speed': 200, 'duration': 3.0}, commit_turns=True)

        # 4. LÓGICA DE EXPLORAÇÃO COM MEMÓRIA: Se não há perigo, busca o melhor caminho.
        max_dist_direita, max_dist_frente, max_dist_esquerda = 0, 0, 0
        for angulo, dist_cm in scan_data_cm:
            if 0 <= angulo < 70: max_dist_direita = max(max_dist_direita, dist_cm)
            elif 70 <= angulo <= 110: max_dist_frente = max(max_dist_frente, dist_cm)
            else: max_dist_esquerda = max(max_dist_esquerda, dist_cm)

        # Adiciona bonus de exploração baseado em memória espacial
        if robot_pose is not None:
            x_cm, y_cm, theta_deg = robot_pose
            max_dist_frente += self.get_exploration_bias(x_cm, y_cm, theta_deg, 'front')
            max_dist_esquerda += self.get_exploration_bias(x_cm, y_cm, theta_deg, 'left')
            max_dist_direita += self.get_exploration_bias(x_cm, y_cm, theta_deg, 'right')

        print(f"[NAVIGATOR] Exploração por Setores (com memória): D={max_dist_direita:.0f}cm, F={max_dist_frente:.0f}cm, E={max_dist_esquerda:.0f}cm")

        # 5. LÓGICA DE DECISÃO: Compara os setores para escolher a ação.
        # Se a frente está confiavelmente aberta, avança para fazer progresso.
        if max_dist_frente > FORWARD_CONFIDENCE_THRESHOLD_CM:
            print(f"[NAVIGATOR] -> Frente está aberta ({max_dist_frente:.0f}cm). Avançando com confiança.")
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