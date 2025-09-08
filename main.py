# arquivo: main.py (VERSÃO FINAL 2.0 - COMPLETA)

import math
import os
from PIL import Image
from collections import deque
import numpy as np

# --- Imports da nossa arquitetura ---
from src.config import settings
from src.hardware.serial_handler import SerialHandler
from src.communication.mqtt_publisher import MqttPublisher
from src.robot.state import RobotState
from src.robot.chassis import Chassis
from src.mapping.slam_manager import SLAMManager
from src.navigation.navigator import Navigator
from robot_specifications import (
    STALLED_DISTANCE_THRESHOLD_CM,
    MAP_COVERAGE_STABILITY_THRESHOLD,
    CYCLES_TO_CONFIRM_COMPLETION
)


def save_map_image(image: Image.Image, path: str):
    """Função auxiliar para salvar a imagem do mapa."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        image.save(path)
    except Exception as e:
        print(f"[MAIN] Erro ao salvar a imagem do mapa: {e}")


def main():
    print("--- INICIANDO CÉREBRO AUTÔNOMO DO ROBÔ (ARQUITETURA FINAL) ---")

    # --- FASE DE INICIALIZAÇÃO DOS COMPONENTES ---
    try:
        # Componentes de "baixo nível"
        serial_handler = SerialHandler(settings.serial_port, settings.baud_rate)
        mqtt_publisher = MqttPublisher(settings.mqtt_broker_host, settings.mqtt_broker_port)
        
        # Componentes "especialistas" do robô
        initial_pose_cm_rad = ( (settings.map_size_meters * 100 / 2), (settings.map_size_meters * 100 / 2), 0.0 )
        robot_state = RobotState(*initial_pose_cm_rad)
        
        chassis = Chassis(serial_handler)
        slam_manager = SLAMManager(settings.map_width_px, settings.map_size_meters)
        navigator = Navigator() # Usa o danger_threshold padrão de 20.0cm

        # Variáveis para a lógica de conclusão da missão
        pose_history = deque(maxlen=30)
        last_map_coverage = 0 # Armazena a última contagem de pixels explorados
        consecutive_stable_cycles = 0

        print("[MAIN] Todos os componentes foram inicializados com sucesso.")

    except Exception as e:
        print(f"[MAIN] ERRO CRÍTICO DURANTE A INICIALIZAÇÃO: {e}")
        return

    try:
        # --- OBTÉM A PRIMEIRA LEITURA DO MUNDO ANTES DO LOOP ---
        print("[MAIN] Realizando o primeiro scan para obter o estado inicial do ambiente...")
        serial_handler.enviar_comando('e')
        scan_data_cm = serial_handler.receber_scan_dados()
        if not scan_data_cm:
            print("[MAIN] ERRO: Scan inicial falhou. O robô não pode operar sem sensores.")
            return

        # --- LOOP PRINCIPAL ORQUESTRADO ---
        while True:
            current_pose_cm_rad = robot_state.get_pose_cm_rad()
            print(f"\n--- Novo Ciclo --- Pose Atual: {robot_state}")

            # 1. NAVEGAÇÃO: Onde devemos ir?
            action = navigator.decide_next_action(scan_data_cm)
            
            # 2. AÇÃO E ODOMETRIA: Mova-se e estime o deslocamento.
            local_odometry_delta = chassis.execute_action(action)
            
            # Converte o delta local para o delta global
            d_frente, _, d_theta = local_odometry_delta
            theta = current_pose_cm_rad[2]
            global_delta_x = d_frente * math.cos(theta)
            global_delta_y = d_frente * math.sin(theta)
            global_odometry_delta = (global_delta_x, global_delta_y, d_theta)
            
            # 3. PERCEPÇÃO: Veja o mundo da nova posição.
            serial_handler.enviar_comando('e')
            scan_data_cm = serial_handler.receber_scan_dados()
            if not scan_data_cm:
                print("[MAIN] AVISO: Falha no scan durante o loop. Pulando este ciclo.")
                continue

            # 4. MAPEAMENTO E LOCALIZAÇÃO: Use o SLAM para corrigir a rota.
            slam_manager.update(scan_data_cm, global_odometry_delta)
            corrected_pose_cm_rad = slam_manager.get_corrected_pose_cm_rad()
            
            # 5. ATUALIZAÇÃO DE ESTADO: Corrija a posição "oficial".
            robot_state.update_pose(*corrected_pose_cm_rad)
            print(f"[MAIN] Pose CORRIGIDA pelo SLAM: {robot_state}")

            # 6. PUBLICAÇÃO: Mostre o resultado.
            map_image = slam_manager.get_map_image()
            caminho_mapa = os.path.join(settings.map_output_dir, "map_slam_latest.png")
            save_map_image(map_image, caminho_mapa)
            mqtt_publisher.publicar_mapa(caminho_mapa)

            # --- ETAPA 7: VERIFICAÇÃO DE CONCLUSÃO DA MISSÃO ---
            current_pose = robot_state.get_pose_cm_rad()
            pose_history.append(current_pose)
            
            map_image_gray = map_image.convert('L')
            map_array = np.array(map_image_gray)
            
            if len(pose_history) == pose_history.maxlen:
                # Verifica se o robô está parado
                start_pose = pose_history[0]
                end_pose = pose_history[-1]
                distance_moved = math.hypot(end_pose[0] - start_pose[0], end_pose[1] - start_pose[1])
                robot_is_stalled = distance_moved < STALLED_DISTANCE_THRESHOLD_CM

                # Verifica se o mapa não está crescendo
                current_map_coverage = np.count_nonzero(map_array)
                coverage_growth = current_map_coverage - last_map_coverage
                map_is_stable = coverage_growth < MAP_COVERAGE_STABILITY_THRESHOLD
                
                if robot_is_stalled and map_is_stable:
                    consecutive_stable_cycles += 1
                    print(f"[MISSION] Robô parado e cobertura do mapa estável ({coverage_growth} pixels novos). "
                          f"Ciclos de confirmação: {consecutive_stable_cycles}/{CYCLES_TO_CONFIRM_COMPLETION}")
                else:
                    consecutive_stable_cycles = 0

                last_map_coverage = current_map_coverage
                
                if consecutive_stable_cycles >= CYCLES_TO_CONFIRM_COMPLETION:
                    print("\n" + "="*50)
                    print("MISSÃO CONCLUÍDA: O robô mapeou o ambiente e não há mais progresso a ser feito.")
                    print("="*50)
                    break # Encerra o loop while
            
    except KeyboardInterrupt:
        print("\n[MAIN] Comando de encerramento recebido (Ctrl+C).")
    except Exception as e:
        print(f"\n[MAIN] ERRO INESPERADO NO LOOP PRINCIPAL: {e}")
    finally:
        print("[MAIN] Finalizando... Parando motores e fechando conexões.")
        if 'serial_handler' in locals():
            serial_handler.enviar_comando('q')
            serial_handler.fechar_conexao()
        if 'mqtt_publisher' in locals():
            mqtt_publisher.publicar_status("OFFLINE")
        print("\n--- PROGRAMA FINALIZADO ---")


if __name__ == "__main__":
    main()