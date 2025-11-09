"""
Ponto de entrada principal para o "Cérebro" do robô.

ARQUITETURA:
Este módulo atua como o "Orquestrador" do sistema. Ele não contém lógica de
negócio complexa (navegação, SLAM, etc.), mas é responsável por:
1. Inicializar todos os módulos especialistas (drivers, estado, atuadores, algoritmos).
2. Gerenciar o loop de controle principal, orquestrando o fluxo de dados entre
   os diferentes componentes na sequência correta.
"""

import math
import os
from PIL import Image
from collections import deque
import numpy as np
import time

from src.config import settings
from src.hardware.serial_handler import SerialHandler
from src.communication.mqtt_publisher import MqttPublisher
from src.robot.state import RobotState
from src.robot.chassis import Chassis
from src.mapping.slam_manager import SLAMManager
from src.navigation.navigator import Navigator
from src.odometry.laser_odometry import LaserOdometry
from robot_specifications import (
    STALLED_DISTANCE_THRESHOLD_CM,
    MAP_COVERAGE_STABILITY_THRESHOLD,
    CYCLES_TO_CONFIRM_COMPLETION
)

def save_map_image(image: Image.Image, path: str):
    """Função auxiliar para salvar a imagem do mapa no disco."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        image.save(path)
    except Exception as e:
        print(f"[MAIN] Erro ao salvar a imagem do mapa: {e}")

def main():
    """
    Inicializa todos os subsistemas e executa o loop de controle principal do robô.

    O loop de controle segue um ciclo de Sense-Plan-Act modificado:
    1.  NAVEGAÇÃO: Consulta o `Navigator` para decidir a próxima ação com base no último scan.
    2.  AÇÃO: Comanda o `Chassis` para executar o movimento.
    3.  PERCEPÇÃO: Obtém um novo scan do ambiente.
    4.  ODOMETRIA (ICP): Usa o `LaserOdometry` para calcular o deslocamento real
        comparando o scan novo com o antigo.
    5.  MAPEAMENTO (SLAM): Atualiza o `SLAMManager` com o scan e a odometria de alta precisão.
    6.  ATUALIZAÇÃO DE ESTADO: Corrige a pose do `RobotState` com a estimativa do SLAM.
    7.  PUBLICAÇÃO: Envia o mapa atualizado via MQTT.
    8.  VERIFICAÇÃO DE CONCLUSÃO: Checa se a missão de mapeamento terminou.
    """
    print("INICIANDO CÉREBRO AUTÔNOMO DO ROBÔ (ARQUITETURA HÍBRIDA)")
    try:
        # FASE 1: INICIALIZAÇÃO DOS COMPONENTES
        serial_handler = SerialHandler(settings.serial_port, settings.baud_rate)
        mqtt_publisher = MqttPublisher()
        
        initial_pose_cm_rad = (settings.map_size_meters * 100 / 2, settings.map_size_meters * 100 / 2, 0.0)
        robot_state = RobotState(*initial_pose_cm_rad)
        
        chassis = Chassis(serial_handler)
        slam_manager = SLAMManager(settings.map_width_px, settings.map_size_meters)
        navigator = Navigator(danger_threshold_cm=50.0)
        laser_odometry = LaserOdometry()
        
        # Buffers para a lógica de fim de missão
        odometry_history = deque(maxlen=30)
        last_map_coverage = 0
        consecutive_stable_cycles = 0
        print("[MAIN] Todos os componentes foram inicializados com sucesso.")

    except Exception as e:
        print(f"[MAIN] ERRO CRÍTICO DURANTE A INICIALIZAÇÃO: {e}")
        return

    try:
        # FASE 2: PRIMEIRO SCAN
        print("[MAIN] Realizando o primeiro scan para obter o estado inicial do ambiente")
        serial_handler.enviar_comando('e')
        scan_data_cm = serial_handler.receber_scan_dados()
        if not scan_data_cm:
            print("[MAIN] ERRO: Scan inicial falhou.")
            return
        
        # Inicializa o calculador de odometria com o primeiro scan.
        laser_odometry.calculate_delta(scan_data_cm)

        # FASE 3: LOOP DE CONTROLE PRINCIPAL
        while True:
            pose_antes_da_correcao = robot_state.get_pose_cm_rad()
            x_cm, y_cm, theta_rad = pose_antes_da_correcao
            theta_deg = math.degrees(theta_rad)
            print(f"\n--- Novo Ciclo --- Pose Atual: {robot_state}")

            # 1. NAVEGAÇÃO (com memória espacial)
            action = navigator.decide_next_action(scan_data_cm, robot_pose=(x_cm, y_cm, theta_deg))
            
            # 2. AÇÃO
            chassis.execute_action(action)
            # Delay para garantir que o movimento físico termine antes do próximo scan
            time.sleep(0.8)  # Aumentado para 800ms - robô precisa parar completamente

            # 3. ODOMETRIA REAL (via encoders virtuais do firmware)
            # Mais precisa que ICP - usa física simulada diretamente
            serial_handler.enviar_comando('o')
            local_odometry_delta = serial_handler.receber_odometria_dados()
            odometry_history.append(local_odometry_delta)
            
            # Converte o delta local (do robô) para global (do mapa)
            d_frente, d_lado, d_theta = local_odometry_delta
            theta = pose_antes_da_correcao[2]
            global_delta_x = d_frente * math.cos(theta) - d_lado * math.sin(theta)
            global_delta_y = d_frente * math.sin(theta) + d_lado * math.cos(theta)
            global_odometry_delta = (global_delta_x, global_delta_y, d_theta)

            # 4. PERCEPÇÃO (após movimento)
            serial_handler.enviar_comando('e')
            scan_data_cm_atual = serial_handler.receber_scan_dados()
            if not scan_data_cm_atual:
                print("[MAIN] AVISO: Falha no scan durante o loop.")
                continue

            # 5. MAPEAMENTO E LOCALIZAÇÃO (SLAM)
            slam_manager.update(scan_data_cm_atual, global_odometry_delta)
            corrected_pose_cm_rad = slam_manager.get_corrected_pose_cm_rad()
            
            # Bloco de diagnóstico para comparar a odometria ICP com a correção final do SLAM
            dx_chute, dy_chute, dtheta_chute = global_odometry_delta
            pose_depois_do_chute_x = pose_antes_da_correcao[0] + dx_chute
            pose_depois_do_chute_y = pose_antes_da_correcao[1] + dy_chute
            pose_depois_do_chute_theta = pose_antes_da_correcao[2] + dtheta_chute
            dx_correcao = corrected_pose_cm_rad[0] - pose_depois_do_chute_x
            dy_correcao = corrected_pose_cm_rad[1] - pose_depois_do_chute_y
            
            distancia_correcao = math.sqrt(dx_correcao**2 + dy_correcao**2)
            
            print(f"[DIAGNOSTICO] Odometria Encoders (dx, dy): ({dx_chute:.2f}, {dy_chute:.2f})")
            print(f"[DIAGNOSTICO] ⛔ SLAM DESABILITADO - correção ignorada: ({dx_correcao:.2f}, {dy_correcao:.2f})")
            print(f"[MAIN] 🎯 Usando encoders virtuais puros (sem SLAM)")
            
            corrected_pose_cm_rad = (
                pose_depois_do_chute_x,
                pose_depois_do_chute_y,
                pose_depois_do_chute_theta
            )
            
            # 6. ATUALIZAÇÃO DE ESTADO
            robot_state.update_pose(*corrected_pose_cm_rad)
            print(f"[MAIN] Pose atualizada (ICP puro): {robot_state}")

            # 7. PUBLICAÇÃO
            map_image = slam_manager.get_map_image()
            caminho_mapa = os.path.join(settings.map_output_dir, "map_slam_latest.png")
            save_map_image(map_image, caminho_mapa)
            mqtt_publisher.publicar_mapa(caminho_mapa)

            # 8. VERIFICAÇÃO DE CONCLUSÃO DA MISSÃO
            if len(odometry_history) == odometry_history.maxlen:
                total_frente_moved = sum(delta[0] for delta in odometry_history)
                robot_is_stalled = abs(total_frente_moved) < STALLED_DISTANCE_THRESHOLD_CM
                
                map_array = np.array(map_image.convert('L'))
                current_map_coverage = np.count_nonzero(map_array)
                coverage_growth = current_map_coverage - last_map_coverage
                map_is_stable = coverage_growth < MAP_COVERAGE_STABILITY_THRESHOLD
                
                if robot_is_stalled and map_is_stable:
                    consecutive_stable_cycles += 1
                    print(f"[MISSION] Robô parado e cobertura estável ({coverage_growth} pixels novos). "
                          f"Ciclos: {consecutive_stable_cycles}/{CYCLES_TO_CONFIRM_COMPLETION}")
                else:
                    consecutive_stable_cycles = 0
                last_map_coverage = current_map_coverage
                
                if consecutive_stable_cycles >= CYCLES_TO_CONFIRM_COMPLETION:
                    print("\n" + "="*50); print("MISSÃO CONCLUÍDA"); print("="*50)
                    break
            
            scan_data_cm = scan_data_cm_atual

    except KeyboardInterrupt:
        print("\n[MAIN] Comando de encerramento recebido (Ctrl+C).")
    finally:
        print("[MAIN] Finalizando. Parando motores e fechando conexões.")
        if 'serial_handler' in locals():
            serial_handler.enviar_comando('q')
            serial_handler.fechar_conexao()
        if 'mqtt_publisher' in locals():
            mqtt_publisher.publicar_status("OFFLINE")
        print("\n--- PROGRAMA FINALIZADO ---")

if __name__ == "__main__":
    main()