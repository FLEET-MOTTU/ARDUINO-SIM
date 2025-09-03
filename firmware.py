# # Em firmware.py
# import serial
# import time
# import pygame
# import argparse
# import paho.mqtt.client as mqtt
# import base64
# import io
# from src.config import settings

# from simulation.corpo_e_mundo_sim import CorpoRoboSimulado

# MAX_VELOCIDADE_ARDUINO = 255.0

# class FirmwareSimulado:
#     def __init__(self, porta_serial):
#         print("Iniciando o Firmware Simulado (Cérebro Arduino)...")
        
#         # --- CORREÇÃO DO ERRO PRINCIPAL ---
#         # Esta linha provavelmente estava faltando. Ela cria o objeto do robô.
#         self.corpo_robo = CorpoRoboSimulado()
        
#         self.mapa_surface = None
#         self.ultimo_payload_mapa = None

#         # --- Conexão Serial (sem alterações) ---
#         try:
#             self.ser = serial.Serial(porta_serial, 9600, timeout=0.1)
#             print(f"Firmware escutando na porta serial virtual {porta_serial}.")
#         except serial.SerialException as e:
#             print(f"ERRO CRÍTICO: Não foi possível abrir a porta {porta_serial}. {e}")
#             raise SystemExit
            
#         # --- Configuração MQTT ---
#         print("Firmware configurando cliente MQTT para receber mapas...")
        
#         # --- CORREÇÃO DO AVISO ---
#         # Adicionado o argumento 'mqtt.CallbackAPIVersion.VERSION2' para usar a API mais recente
#         self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="robo_simulador_subscriber")
        
#         self.mqtt_client.on_connect = self._on_mqtt_connect
#         self.mqtt_client.on_message = self._on_mqtt_map_message
        
#         try:
#             self.mqtt_client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, 60)
#             self.mqtt_client.loop_start()
#         except Exception as e:
#             print(f"AVISO: Conexão com MQTT falhou. Visualização do mapa desativada. Erro: {e}")

#     def _on_mqtt_connect(self, client, userdata, flags, rc):
#         if rc == 0:
#             print("Firmware conectado ao MQTT com sucesso!")
#             client.subscribe(settings.mqtt_topico_mapa)
#             print(f"Firmware inscrito no tópico '{settings.mqtt_topico_mapa}' para receber mapas.")
#         else:
#             print(f"Firmware falhou ao conectar ao MQTT, código de retorno: {rc}")

#     def _on_mqtt_map_message(self, client, userdata, msg):
#         """
#         CALLBACK DA THREAD MQTT: Apenas recebe o dado bruto e o armazena.
#         Não faz nenhum processamento de imagem aqui.
#         """
#         print("FIRMWARE (MQTT Thread): Payload do mapa recebido.")
#         self.ultimo_payload_mapa = msg.payload

#     # --- NOVO MÉTODO ---
#     def _processar_mapa_recebido(self):
#         """
#         MÉTODO DA THREAD PRINCIPAL (PYGAME): Processa o dado se houver um novo.
#         """
#         if self.ultimo_payload_mapa:
#             print("FIRMWARE (Pygame Thread): Processando novo mapa para exibição...")
#             try:
#                 image_data = base64.b64decode(self.ultimo_payload_mapa)
#                 image_stream = io.BytesIO(image_data)
#                 self.mapa_surface = pygame.image.load(image_stream).convert()
#                 self.ultimo_payload_mapa = None # Limpa para não reprocessar
#             except Exception as e:
#                 print(f"FIRMWARE (Pygame Thread): Erro ao processar imagem do mapa: {e}")
#                 self.ultimo_payload_mapa = None # Limpa mesmo se der erro

#     # ... (toda a lógica do chassi e do scan não muda) ...
#     def _chassi_avancar(self, velocidade):
#         percentual = velocidade / MAX_VELOCIDADE_ARDUINO
#         self.corpo_robo.set_velocidades(percentual, 0)
#     # ... (etc) ...
#     def _chassi_recuar(self, velocidade):
#         percentual = - (velocidade / MAX_VELOCIDADE_ARDUINO)
#         self.corpo_robo.set_velocidades(percentual, 0)

#     def _chassi_virar_direita(self, velocidade):
#         percentual = - (velocidade / MAX_VELOCIDADE_ARDUINO)
#         self.corpo_robo.set_velocidades(0, percentual)

#     def _chassi_virar_esquerda(self, velocidade):
#         percentual = velocidade / MAX_VELOCIDADE_ARDUINO
#         self.corpo_robo.set_velocidades(0, percentual)

#     def _chassi_parar(self):
#         self.corpo_robo.set_velocidades(0, 0)

#     def _fazer_scan(self):
#         self.corpo_robo.limpar_visualizacao_scan()
#         for angulo_graus in range(0, 181, 10):
#             dist_cm = self.corpo_robo.get_distancia_em_angulo(angulo_graus)
#             resposta = f"{angulo_graus};{dist_cm}\n"
#             self.ser.write(resposta.encode('utf-8'))
#             time.sleep(0.04)

#     def executar_comando(self, comando):
#         action = comando[0]
#         value = int(comando[1:]) if len(comando) > 1 else 0
        
#         if action == 'w': self._chassi_avancar(value)
#         elif action == 's': self._chassi_recuar(value)
#         elif action == 'd': self._chassi_virar_direita(value)
#         elif action == 'a': self._chassi_virar_esquerda(value)
#         elif action == 'q': self._chassi_parar()
#         elif action == 'e': self._fazer_scan()

#     def loop_principal(self):
#         clock = pygame.time.Clock()
#         rodando = True
#         while rodando:
#             dt = clock.tick(60) / 1000.0
            
#             # 1. Checa por comandos seriais
#             if self.ser.in_waiting > 0:
#                 comando = self.ser.readline().decode('utf-8').strip()
#                 if comando:
#                     self.executar_comando(comando)
            
#             # 2. ATUALIZADO: Processa o mapa recebido via MQTT (se houver)
#             self._processar_mapa_recebido()
            
#             # 3. Atualiza a física
#             self.corpo_robo.atualizar_fisica(dt)
            
#             # 4. Desenha o mundo
#             self.corpo_robo.desenhar_na_tela(self.mapa_surface)
            
#             # 5. Checa eventos do Pygame
#             for event in pygame.event.get():
#                 if event.type == pygame.QUIT:
#                     rodando = False
        
#         self.mqtt_client.loop_stop()
#         self.ser.close()
#         pygame.quit()
#         print("Simulação e Firmware encerrados.")


# if __name__ == "__main__":
#     # ... (código do __main__ não muda) ...
#     parser = argparse.ArgumentParser(description="Firmware simulado e orquestrador da simulação.")
#     parser.add_argument('--port', default='COM7', help='Porta serial VIRTUAL para escutar o RPi.')
#     args = parser.parse_args()
    
#     simulador_completo = FirmwareSimulado(porta_serial=args.port)
#     simulador_completo.loop_principal()

import serial
import time
import pygame
import argparse
import os

from simulation.corpo_e_mundo_sim import CorpoRoboSimulado


MAX_VELOCIDADE_ARDUINO = 255.0


class FirmwareSimulado:
    def __init__(self, porta_serial):
        print("Iniciando o Firmware Simulado...")
        self.corpo_robo = CorpoRoboSimulado()
        self.mapa_surface = None
        
        # Guardamos o caminho do último mapa carregado para evitar recarregar a mesma imagem
        self.ultimo_mapa_carregado = None
        
        # Timer para checar por novos mapas (em segundos)
        self.timer_mapa = 0.0
        self.intervalo_check_mapa = 1.0 # Checa por um novo mapa a cada 1 segundo

        # Conexão Serial (sem alterações)
        try:
            self.ser = serial.Serial(porta_serial, 9600, timeout=0.1)
            print(f"Firmware escutando na porta serial virtual {porta_serial}.")
        except serial.SerialException as e:
            print(f"ERRO CRÍTICO: Não foi possível abrir a porta {porta_serial}. {e}")
            raise SystemExit
            

    def _carregar_mapa_do_disco(self):
        diretorio_mapas = "output/maps"
        try:
            arquivos = [f for f in os.listdir(diretorio_mapas) if f.endswith('.png')]
            if not arquivos:
                return

            caminhos_completos = [os.path.join(diretorio_mapas, f) for f in arquivos]
            arquivo_mais_recente = max(caminhos_completos, key=os.path.getmtime)

            if arquivo_mais_recente != self.ultimo_mapa_carregado:
                print(f"VISUALIZACAO: Encontrado novo mapa '{arquivo_mais_recente}'. Carregando...")
                self.mapa_surface = pygame.image.load(arquivo_mais_recente).convert()
                self.ultimo_mapa_carregado = arquivo_mais_recente

        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"VISUALIZACAO: Erro ao carregar imagem do mapa: {e}")


    def _chassi_avancar(self, velocidade):
        percentual = velocidade / MAX_VELOCIDADE_ARDUINO
        self.corpo_robo.set_velocidades(percentual, 0)


    def _chassi_recuar(self, velocidade):
        percentual = - (velocidade / MAX_VELOCIDADE_ARDUINO)
        self.corpo_robo.set_velocidades(percentual, 0)


    def _chassi_virar_direita(self, velocidade):
        percentual = - (velocidade / MAX_VELOCIDADE_ARDUINO)
        self.corpo_robo.set_velocidades(0, percentual)


    def _chassi_virar_esquerda(self, velocidade):
        percentual = velocidade / MAX_VELOCIDADE_ARDUINO
        self.corpo_robo.set_velocidades(0, percentual)


    def _chassi_parar(self):
        self.corpo_robo.set_velocidades(0, 0)


    def _fazer_scan(self):
        self.corpo_robo.limpar_visualizacao_scan()
        for angulo_graus in range(0, 181, 10):
            dist_cm = self.corpo_robo.get_distancia_em_angulo(angulo_graus)
            resposta = f"{angulo_graus};{dist_cm}\n"
            self.ser.write(resposta.encode('utf-8'))
            time.sleep(0.04)


    def executar_comando(self, comando):
        action = comando[0]
        value = int(comando[1:]) if len(comando) > 1 else 0
        
        if action == 'w': self._chassi_avancar(value)
        elif action == 's': self._chassi_recuar(value)
        elif action == 'd': self._chassi_virar_direita(value)
        elif action == 'a': self._chassi_virar_esquerda(value)
        elif action == 'q': self._chassi_parar()
        elif action == 'e': self._fazer_scan()


    def loop_principal(self):
        clock = pygame.time.Clock()
        rodando = True
        while rodando:
            dt = clock.tick(60) / 1000.0
            
            # Checa por comandos seriais
            if self.ser.in_waiting > 0:
                comando = self.ser.readline().decode('utf-8').strip()
                if comando:
                    self.executar_comando(comando)

            # ATUALIZADO: Checa periodicamente por um novo mapa no disco
            self.timer_mapa += dt
            if self.timer_mapa >= self.intervalo_check_mapa:
                self._carregar_mapa_do_disco()
                self.timer_mapa = 0.0 # Reseta o timer
            
            # Atualiza a física e desenha na tela
            self.corpo_robo.atualizar_fisica(dt)
            self.corpo_robo.desenhar_na_tela(self.mapa_surface)
            
            # Checa eventos do Pygame
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    rodando = False
        
        self.ser.close()
        pygame.quit()
        print("Simulação e Firmware encerrados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Firmware simulado e orquestrador da simulação.")
    parser.add_argument('--port', default='COM7', help='Porta serial VIRTUAL para escutar o RPi.')
    args = parser.parse_args()
    
    simulador_completo = FirmwareSimulado(porta_serial=args.port)
    simulador_completo.loop_principal()