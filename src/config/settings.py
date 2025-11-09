"""
Define e carrega as configurações da aplicação a partir de um arquivo .env.

ARQUITETURA:
Este módulo utiliza a biblioteca `pydantic-settings` para criar uma camada de
configuração robusta e com validação de tipos. Ele serve como um ponto
centralizado para todos os parâmetros que podem variar ou precisar de ajuste,
desacoplando a lógica do código da fonte das configurações.
"""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Define o esquema de todas as configurações necessárias para a aplicação.

    A herança de `BaseSettings` automaticamente habilita a leitura de variáveis
    de ambiente ou de um arquivo .env, validando seus tipos.
    """
    # Configurações para o broker de comunicação MQTT (visualização)
    mqtt_broker_host: str
    mqtt_broker_port: int
    mqtt_topico_status: str
    mqtt_topico_mapa: str

    # Configurações da porta serial para comunicação com o Corpo
    serial_port: str
    baud_rate: int

    # Configurações para o algoritmo de SLAM e a geração do mapa
    map_width_px: int = 500
    map_height_px: int = 500
    map_output_dir: str = "output/maps"
    map_size_meters: int = 10


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()