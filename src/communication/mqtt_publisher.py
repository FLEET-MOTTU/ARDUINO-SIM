import base64
import paho.mqtt.client as mqtt
from src.config import settings


class MqttPublisher:
    """Gerencia a publicação de status e dados para um broker MQTT."""
    def __init__(self, broker, porta):
        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="robo_cerebro_publisher")
        self.conectado = False
        try:
            print(f"Tentando conectar ao Broker MQTT em {broker}...")
            self.cliente.connect(broker, porta, 60)
            self.conectado = True
            self.cliente.loop_start()
            print("Conectado ao Broker MQTT com sucesso!")
        except Exception as e:
            print(f"FALHA: Não foi possível conectar ao Broker MQTT. Erro: {e}")


    def publicar_status(self, mensagem):
        if self.conectado:
            self.cliente.publish(settings.mqtt_topico_status, mensagem)

    
    def publicar_mapa(self, caminho_do_arquivo):
        if not self.conectado:
            print("ERRO MQTT: Não conectado ao broker. Impossível publicar mapa.")
            return False
        
        print(f"MQTT -> Lendo o arquivo de mapa: {caminho_do_arquivo}")
        try:
            with open(caminho_do_arquivo, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            self.cliente.publish(settings.mqtt_topico_mapa, encoded_string, qos=1)
            print(f"MQTT -> Mapa publicado com sucesso no tópico '{settings.mqtt_topico_mapa}'")
            return True
        except FileNotFoundError:
            print(f"ERRO MQTT: Arquivo de mapa não encontrado em '{caminho_do_arquivo}'")
            return False
        except Exception as e:
            print(f"ERRO MQTT: Falha ao publicar mapa. Erro: {e}")
            return False
