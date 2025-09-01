import os
import time

from src.config import settings
from src.communication import MqttPublisher
from src.hardware import SerialHandler
from src.mapping import Mapper


def main():
    print("--- INICIANDO CÉREBRO AUTÔNOMO DO ROBÔ ---")

    comunicador_mqtt = MqttPublisher(settings.mqtt_broker_host, settings.mqtt_broker_port)
    ponte_serial = SerialHandler(settings.serial_port, settings.baud_rate)
    mapeador = Mapper()
    
    if ponte_serial.em_simulacao:
        print("ERRO FATAL: Não foi possível conectar ao Arduino (real ou simulado).")
        print("Verifique se o arduino_emulator.py está rodando ou se o hardware está conectado.")
        return

    comunicador_mqtt.publicar_status("ONLINE - Iniciando exploração autônoma")
    time.sleep(1)

    try:
        while True:
            # ESTADO 1: PERCEPÇÃO - Sempre começa escaneando
            comunicador_mqtt.publicar_status("AUTONOMIA: Escaneando ambiente...")
            ponte_serial.enviar_comando('e')
            dados_scan = ponte_serial.receber_scan_dados()
            
            if dados_scan:
                mapeador.adicionar_scan(dados_scan)
                caminho_mapa = mapeador.salvar_mapa()
                if comunicador_mqtt.publicar_mapa(caminho_mapa):
                    os.remove(caminho_mapa)

            # ESTADO 2: DECISÃO - Lógica simples de "seguir a parede"
            distancia_frente = 0
            distancia_direita = 0
            for angulo, dist in dados_scan:
                if 80 <= angulo <= 100:
                    distancia_frente = dist
                if 0 <= angulo <= 20:
                    distancia_direita = dist
            
            comunicador_mqtt.publicar_status(f"AUTONOMIA: Decidindo... Frente: {distancia_frente}cm, Direita: {distancia_direita}cm")

            # Ações com base na decisão
            if distancia_frente > 30: # Se o caminho à frente está livre
                ponte_serial.enviar_comando('w150') # Anda pra frente
                time.sleep(1) # por 1 segundo
            else: # Se há uma parede à frente
                comunicador_mqtt.publicar_status("AUTONOMIA: Obstáculo! Virando à esquerda.")
                ponte_serial.enviar_comando('a180') # Vira à esquerda
                time.sleep(1.5) # por 1.5 segundos
            
            ponte_serial.enviar_comando('q') # Sempre para antes do próximo ciclo
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nComando de encerramento recebido (Ctrl+C).")
    finally:
        ponte_serial.enviar_comando('q')
        comunicador_mqtt.publicar_status("OFFLINE")
        print("\n--- PROGRAMA FINALIZADO ---")


if __name__ == "__main__":
    main()