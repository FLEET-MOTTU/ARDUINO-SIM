# import os
# import time
# import serial

# from src.config import settings
# from src.communication import MqttPublisher
# from src.hardware import SerialHandler
# from src.mapping import Mapper

# def main():
#     print("--- INICIANDO CÉREBRO AUTÔNOMO DO ROBÔ ---")
    
#     ponte_serial = None
#     try:
#         # Tenta se conectar a QUALQUER porta definida no .env.
#         # Não há mais modo de simulação, apenas "conectar ao hardware".
#         # O "hardware" pode ser real ou o nosso firmware virtual.
#         ponte_serial = SerialHandler(settings.serial_port, settings.baud_rate)
            
#     except serial.SerialException as e:
#         print("\nERRO FATAL: Não foi possível estabelecer comunicação serial.")
#         print(f"Verifique se o dispositivo (real ou simulado) está disponível na porta '{settings.serial_port}'.")
#         print(f"Se estiver em simulação, garanta que 'firmware.py' está rodando.")
#         print(f"Se estiver em produção, garanta que o Arduino está conectado.")
#         print(f"Detalhe do Erro: {e}")
#         return

#     comunicador_mqtt = MqttPublisher(settings.mqtt_broker_host, settings.mqtt_broker_port)
#     mapeador = Mapper()
    
#     comunicador_mqtt.publicar_status("ONLINE - Iniciando exploração autônoma")
#     time.sleep(1)

#     try:
#         # Loop de controle principal. Cada iteração é um "tick" de decisão.
#         while True:
#             # --- PERCEPÇÃO ---
#             ponte_serial.enviar_comando('e')
#             dados_scan = ponte_serial.receber_scan_dados()
            
#             if not dados_scan:
#                 print("AVISO: Scan falhou. Parando por seguranca.")
#                 ponte_serial.enviar_comando('q') # Para se o sensor falhar
#                 time.sleep(1)
#                 continue

#             # ... (código de mapeamento e publicação não muda) ...
#             mapeador.adicionar_scan(dados_scan)
#             caminho_mapa = mapeador.salvar_mapa()
#             if comunicador_mqtt.publicar_mapa(caminho_mapa):
#                 os.remove(caminho_mapa)

#             # --- DECISÃO ---
#             distancia_frente = 1000
#             distancia_direita = 1000
#             for angulo, dist in dados_scan:
#                 if dist > 0:
#                     if 80 <= angulo <= 100:
#                         distancia_frente = min(distancia_frente, dist)
#                     if 0 <= angulo <= 30:
#                         distancia_direita = min(distancia_direita, dist)
            
#             # --- LÓGICA DE AÇÃO CONTÍNUA ---
#             VELOCIDADE_MOVIMENTO = 150
#             VELOCIDADE_ROTACAO = 120
#             DISTANCIA_SEGURANCA_FRENTE = 40
#             DISTANCIA_ALVO_PAREDE = 35
#             MARGEM_PAREDE = 10
            
#             # A decisão agora define o estado de movimento para o próximo ciclo.
#             # O robô não para mais entre as decisões.
            
#             if distancia_frente < DISTANCIA_SEGURANCA_FRENTE:
#                 comunicador_mqtt.publicar_status(f"AUTONOMIA: Obstaculo a {distancia_frente}cm. Virando a esquerda.")
#                 ponte_serial.enviar_comando(f'a{VELOCIDADE_ROTACAO + 30}')
            
#             elif distancia_direita > DISTANCIA_ALVO_PAREDE + MARGEM_PAREDE:
#                 comunicador_mqtt.publicar_status(f"AUTONOMIA: Longe da parede ({distancia_direita}cm). Virando a direita.")
#                 ponte_serial.enviar_comando(f'd{VELOCIDADE_ROTACAO}')
            
#             elif distancia_direita < DISTANCIA_ALVO_PAREDE - MARGEM_PAREDE:
#                 comunicador_mqtt.publicar_status(f"AUTONOMIA: Perto da parede ({distancia_direita}cm). Virando a esquerda.")
#                 ponte_serial.enviar_comando(f'a{VELOCIDADE_ROTACAO}')

#             else:
#                 comunicador_mqtt.publicar_status(f"AUTONOMIA: Seguindo parede a {distancia_direita}cm. Avancando.")
#                 ponte_serial.enviar_comando(f'w{VELOCIDADE_MOVIMENTO}')

#             # O tempo de sleep agora é o "tempo de reação" do robô.
#             # Ele continuará fazendo a última ação comandada durante este tempo.
#             time.sleep(0.3)

#     except KeyboardInterrupt:
#         print("\nComando de encerramento recebido (Ctrl+C).")
#     finally:
#         if ponte_serial:
#             print("Finalizando... Parando motores e fechando conexão.")
#             ponte_serial.enviar_comando('q')
#             ponte_serial.fechar_conexao()
#         comunicador_mqtt.publicar_status("OFFLINE")
#         print("\n--- PROGRAMA FINALIZADO ---")

# if __name__ == "__main__":
#     main()

# Em main.py
import os
import time
import serial
import random

from src.config import settings
from src.communication import MqttPublisher
from src.hardware import SerialHandler
from src.mapping import Mapper

ROBO_VELOCIDADE_LINEAR_CM_S = 20.0
ROBO_VELOCIDADE_ANGULAR_GRAUS_S = 90.0

def main():
    # ... (inicialização do serial, mqtt, mapper não mudam) ...
    ponte_serial = SerialHandler(settings.serial_port, settings.baud_rate)
    comunicador_mqtt = MqttPublisher(settings.mqtt_broker_host, settings.mqtt_broker_port)
    mapeador = Mapper()
    
    # --- POSE INICIAL DO ROBÔ (POSIÇÃO E ORIENTAÇÃO) ---
    # O mapa tem 500x500 pixels. A escala é 2px/cm.
    # O "mundo" tem 250x250 cm. O centro é (125, 125).
    pose_robo = {
        'x': 130.0,  # Posição inicial em cm
        'y': 140.0,  # Posição inicial em cm
        'theta_rad': math.pi # Apontando para "baixo" (180 graus), em radianos
    }
    
    try:
        while True:
            # 1. PERCEPÇÃO
            print("\n--- Novo Ciclo ---")
            ponte_serial.enviar_comando('e')
            dados_scan = ponte_serial.receber_scan_dados()
            
            if not dados_scan:
                print("AVISO: Scan falhou. Parando por seguranca.")
                ponte_serial.enviar_comando('q')
                continue

            # 2. MAPEAMENTO
            # Agora passamos os dados do scan E a pose atual do robô
            mapeador.adicionar_scan(dados_scan, pose_robo)
            caminho_mapa = mapeador.salvar_mapa()
            comunicador_mqtt.publicar_mapa(caminho_mapa)
            # os.remove(caminho_mapa) # Mantemos o mapa para o simulador ler
            print(f"MAPEAMENTO: Mapa incremental atualizado em '{caminho_mapa}'")

            # 3. DECISÃO
            distancia_frente = 1000
            for angulo, dist in dados_scan:
                if 80 <= angulo <= 100 and dist > 0:
                    distancia_frente = min(distancia_frente, dist)
            
            is_stuck = distancia_frente < 20 # Distância de "preso" um pouco maior
            print(f"PERCEPÇÃO: Distancia a frente: {distancia_frente}cm. Preso? {is_stuck}")

            # 4. AÇÃO E ATUALIZAÇÃO DA ODOMETRIA
            if is_stuck:
                # Manobra evasiva
                direcao = random.choice(['a', 'd'])
                velocidade = random.randint(180, 220)
                duracao = random.uniform(1.0, 1.5)
                
                print(f"ACAO: Preso! Virando para '{direcao}' por {duracao:.1f}s.")
                ponte_serial.enviar_comando(f'{direcao}{velocidade}')
                time.sleep(duracao)
                ponte_serial.enviar_comando('q')
                
                # Atualiza a orientação na nossa pose estimada
                velocidade_percentual = velocidade / 255.0
                angulo_virado_graus = ROBO_VELOCIDADE_ANGULAR_GRAUS_S * velocidade_percentual * duracao
                if direcao == 'a': # Esquerda é positivo
                    pose_robo['theta_rad'] += math.radians(angulo_virado_graus)
                else: # Direita é negativo
                    pose_robo['theta_rad'] -= math.radians(angulo_virado_graus)

            else:
                # Andar para frente
                velocidade = 150
                duracao = 0.8
                print(f"ACAO: Caminho livre. Avancando por {duracao}s.")
                ponte_serial.enviar_comando(f'w{velocidade}')
                time.sleep(duracao)
                # Não precisa parar, o próximo comando (scan) interrompe o movimento
                
                # Atualiza a posição X e Y na nossa pose estimada
                velocidade_percentual = velocidade / 255.0
                distancia_movida = ROBO_VELOCIDADE_LINEAR_CM_S * velocidade_percentual * duracao
                
                pose_robo['x'] += distancia_movida * math.cos(pose_robo['theta_rad'])
                pose_robo['y'] += distancia_movida * math.sin(pose_robo['theta_rad'])
            
            # Normaliza o ângulo para evitar que ele cresça indefinidamente
            pose_robo['theta_rad'] = math.atan2(math.sin(pose_robo['theta_rad']), math.cos(pose_robo['theta_rad']))
            print(f"ODOMETRIA: Nova pose estimada -> X={pose_robo['x']:.1f}cm, Y={pose_robo['y']:.1f}cm, Angulo={math.degrees(pose_robo['theta_rad']):.1f}deg")

    except KeyboardInterrupt:
        print("\nComando de encerramento recebido (Ctrl+C).")
    finally:
        if ponte_serial:
            print("Finalizando... Parando motores e fechando conexão.")
            ponte_serial.enviar_comando('q')
            ponte_serial.fechar_conexao()
        comunicador_mqtt.publicar_status("OFFLINE")
        print("\n--- PROGRAMA FINALIZADO ---")

# Pequena alteração para o Mapper ser mais auto-contido
class Mapper:
    """Gerencia a criação e atualização INCREMENTAL da planta baixa."""
    def __init__(self):
        self.largura = settings.map_width_px
        self.altura = settings.map_height_px
        self.output_dir = settings.map_output_dir
        self.escala = 2.0 # Pixels/cm. Usar float para precisão.
        
        # --- MUDANÇA PRINCIPAL: O mapa agora é um atributo persistente ---
        self.mapa_imagem = Image.new("L", (self.largura, self.altura), "black")
        self.desenho = ImageDraw.Draw(self.mapa_imagem)
        
        os.makedirs(self.output_dir, exist_ok=True)

    def adicionar_scan(self, dados_scan, pose_robo):
        """
        Adiciona os pontos de um novo scan ao mapa existente,
        considerando a posição e orientação atual do robô.
        'pose_robo' é um dicionário: {'x': cm, 'y': cm, 'theta_rad': radianos}
        """
        # Posição do robô no mapa (em pixels)
        robo_x_px = pose_robo['x'] * self.escala
        robo_y_px = pose_robo['y'] * self.escala
        
        for angulo_relativo_graus, dist_cm in dados_scan:
            if 0 < dist_cm < 200: # Ignora leituras inválidas ou muito longas
                
                # O ângulo global do raio do sensor é a orientação do robô + o ângulo do sensor
                angulo_relativo_rad = math.radians(angulo_relativo_graus)
                angulo_global_rad = pose_robo['theta_rad'] + angulo_relativo_rad
                
                # Calcula a posição do ponto detectado no mundo (em cm)
                ponto_x_cm = pose_robo['x'] + dist_cm * math.cos(angulo_global_rad)
                ponto_y_cm = pose_robo['y'] + dist_cm * math.sin(angulo_global_rad)
                
                # Converte a posição do ponto para pixels no mapa
                ponto_x_px = int(ponto_x_cm * self.escala)
                # O eixo Y da imagem é invertido em relação à matemática
                ponto_y_px = int(self.altura - (ponto_y_cm * self.escala))
                
                # Desenha o ponto no mapa se estiver dentro dos limites
                if 0 <= ponto_x_px < self.largura and 0 <= ponto_y_px < self.altura:
                    self.desenho.point((ponto_x_px, ponto_y_px), fill="white")

    def salvar_mapa(self) -> str:
        """Salva a imagem do mapa ATUALIZADO com um timestamp e retorna o caminho."""
        timestamp = int(time.time())
        nome_arquivo = f"map_{timestamp}.png"
        caminho_completo = os.path.join(self.output_dir, nome_arquivo)
        
        # Salva o mapa que está sendo construído na memória
        self.mapa_imagem.save(caminho_completo)
        return caminho_completo

if __name__ == "__main__":
    # Adicionamos os imports que faltavam no topo do arquivo main.py
    from PIL import Image, ImageDraw
    from src.config import settings
    import math

    main()