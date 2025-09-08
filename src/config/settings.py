from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # MQTT Settings
    mqtt_broker_host: str
    mqtt_broker_port: int
    mqtt_topico_status: str
    mqtt_topico_mapa: str

    # Serial Settings
    serial_port: str
    baud_rate: int

    # Mapping Settings
    map_width_px: int = 500
    map_height_px: int = 500
    map_output_dir: str = "output/maps"
    map_size_meters: int = 25

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()