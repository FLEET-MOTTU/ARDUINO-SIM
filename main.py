import os
import time
import serial

from src.config import settings
from src.communication import MqttPublisher
from src.hardware import SerialHandler
from src.mapping import Mapper

def main():
    print("--- INICIANDO CÉREBRO AUTÔNOMO DO ROBÔ ---")
    
    ponte_serial = None
    try:
        # Tenta se conectar a QUALQUER porta definida no .env.
        # Não há mais modo de simulação, apenas "conectar ao hardware".
        # O "hardware" pode ser real ou o nosso firmware virtual.
        ponte_serial = SerialHandler(settings.serial_port, settings.baud_rate)
            
    except serial.SerialException as e:
        print("\nERRO FATAL: Não foi possível estabelecer comunicação serial.")
        print(f"Verifique se o dispositivo (real ou simulado) está disponível na porta '{settings.serial_port}'.")
        print(f"Se estiver em simulação, garanta que 'firmware.py' está rodando.")
        print(f"Se estiver em produção, garanta que o Arduino está conectado.")
        print(f"Detalhe do Erro: {e}")
        return

    comunicador_mqtt = MqttPublisher(settings.mqtt_broker_host, settings.mqtt_broker_port)
    mapeador = Mapper()
    
    comunicador_mqtt.publicar_status("ONLINE - Iniciando exploração autônoma")
    time.sleep(1)

    try:
        # A lógica principal do robô permanece idêntica
        while True:
            comunicador_mqtt.publicar_status("AUTONOMIA: Escaneando ambiente...")
            ponte_serial.enviar_comando('e')
            dados_scan = ponte_serial.receber_scan_dados()
            
            if not dados_scan:
                print("AVISO: Scan não retornou dados. Pulando ciclo.")
                time.sleep(1)
                continue

            mapeador.adicionar_scan(dados_scan)
            caminho_mapa = mapeador.salvar_mapa()
            if comunicador_mqtt.publicar_mapa(caminho_mapa):
                os.remove(caminho_mapa)

            distancia_frente = 1000
            for angulo, dist in dados_scan:
                if 80 <= angulo <= 100 and dist > 0:
                    distancia_frente = min(distancia_frente, dist)
            
            comunicador_mqtt.publicar_status(f"AUTONOMIA: Decidindo... Obstáculo à frente: {distancia_frente}cm")

            VELOCIDADE_MOVIMENTO = 150
            VELOCIDADE_ROTACAO = 180
            
            if distancia_frente > 35:
                ponte_serial.enviar_comando(f'w{VELOCIDADE_MOVIMENTO}')
                time.sleep(1.0)
            else:
                comunicador_mqtt.publicar_status("AUTONOMIA: Obstáculo! Virando à esquerda.")
                ponte_serial.enviar_comando(f'a{VELOCIDADE_ROTACAO}')
                time.sleep(1.2)
            
            ponte_serial.enviar_comando('q')
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nComando de encerramento recebido (Ctrl+C).")
    finally:
        if ponte_serial:
            print("Finalizando... Parando motores e fechando conexão.")
            ponte_serial.enviar_comando('q')
            ponte_serial.fechar_conexao()
        comunicador_mqtt.publicar_status("OFFLINE")
        print("\n--- PROGRAMA FINALIZADO ---")

if __name__ == "__main__":
    main()