"""
Define a classe MqttPublisher, responsável pela comunicação externa via MQTT.
"""

import base64
import paho.mqtt.client as mqtt
from src.config import settings

class MqttPublisher:
    """
    Gerencia a conexão e a publicação de dados para um broker MQTT.

    ARQUITETURA:
    Esta classe atua como uma camada de abstração (Adapter) sobre a biblioteca
    paho-mqtt. Ela fornece uma interface simples e de alto nível para o resto
    da aplicação, enquanto encapsula os detalhes do protocolo MQTT,
    conexão, tópicos e codificação de payload (Base64 para imagens).

    Ela é projetada para ser resiliente: uma falha na conexão com o MQTT não
    deve interromper a execução da lógica principal do robô.
    """
    def __init__(self):
        """
        Inicializa o cliente MQTT e tenta estabelecer uma conexão não-bloqueante.
        
        A configuração (host, porta, tópicos) é lida diretamente do objeto
        `settings` para manter a consistência.
        """
        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="robo_cerebro_publisher")
        self.conectado = False
        try:
            print(f"Tentando conectar ao Broker MQTT em {settings.mqtt_broker_host}...")
            self.cliente.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, 60)
            self.conectado = True
            self.cliente.loop_start()
            print("Conectado ao Broker MQTT com sucesso!")
        except Exception as e:
            print(f"FALHA: Não foi possível conectar ao Broker MQTT. Erro: {e}")

    def publicar_status(self, mensagem: str):
        """Publica uma mensagem de status de texto simples."""
        if self.conectado:
            self.cliente.publish(settings.mqtt_topico_status, mensagem)

    def publicar_mapa(self, caminho_do_arquivo: str) -> bool:
        """
        Lê um arquivo de imagem, o codifica em Base64 e o publica no tópico do mapa.

        Args:
            caminho_do_arquivo (str): O caminho para o arquivo de imagem do mapa.

        Returns:
            bool: True se a publicação foi bem-sucedida, False caso contrário.
        """
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