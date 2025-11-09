# 📖 API Reference - Classes e Métodos

## Navigator

```python
from src.navigation.navigator import Navigator

nav = Navigator(
    danger_threshold_cm=50.0,  # Distância mínima para evasão
    grid_size_cm=50.0,         # Tamanho da célula de memória
    map_size_m=10.0            # Tamanho total do mapa
)
```

### Métodos Principais

#### `decide_next_action(scan_data, robot_pose) -> dict`
Decide próxima ação baseado em scan e pose atual.

**Parâmetros:**
- `scan_data`: `list[(angulo_int, distancia_int)]` - Scan laser 0-180°
- `robot_pose`: `(x_cm, y_cm, theta_deg)` - Pose atual do robô

**Retorno:**
```python
{
    'command': 'w',     # 'w'|'s'|'a'|'d'|'q'
    'speed': 150,       # 0-255
    'duration': 1.0     # segundos
}
```

**Exemplo:**
```python
scan = [(0, 350), (10, 420), ..., (180, 300)]
pose = (500.0, 500.0, 0.0)
action = nav.decide_next_action(scan, pose)
# {'command': 'w', 'speed': 150, 'duration': 1.0}
```

---

#### `update_position(x_cm, y_cm)`
Atualiza grid de memória espacial.

**Parâmetros:**
- `x_cm`: float - Coordenada X em centímetros
- `y_cm`: float - Coordenada Y em centímetros

**Exemplo:**
```python
nav.update_position(525.5, 480.2)
# Grid[10, 9] += 1
```

---

## SLAM Manager

```python
from src.mapping.slam_manager import SLAMManager

slam = SLAMManager(
    map_size_pixels=500,    # Resolução do mapa
    map_size_meters=10      # Tamanho físico (m)
)
```

### Métodos Principais

#### `update(scan_data_cm, odometry_delta)`
Processa novo scan com odometria.

**Parâmetros:**
- `scan_data_cm`: `list[(angulo, distancia)]` - Scan em cm
- `odometry_delta`: `(dx_cm, dy_cm, dtheta_rad)` - Delta global

**Exemplo:**
```python
scan = [(0, 350), (10, 420), ..., (180, 300)]
delta = (12.5, 3.2, 0.15)  # dx, dy, dθ
slam.update(scan, delta)
```

---

#### `get_corrected_pose_cm_rad() -> tuple`
Retorna pose corrigida pelo SLAM.

**Retorno:**
```python
(x_cm, y_cm, theta_rad)  # float, float, float
```

**Exemplo:**
```python
x, y, theta = slam.get_corrected_pose_cm_rad()
# (512.34, 498.76, 0.087)
```

---

#### `get_map_image() -> PIL.Image`
Retorna mapa atual como imagem PIL.

**Exemplo:**
```python
from PIL import Image

img = slam.get_map_image()
img.save("mapa.png")
```

---

## Chassis

```python
from src.robot.chassis import Chassis
from src.hardware.serial_handler import SerialHandler

serial = SerialHandler("COM5", 9600)
chassis = Chassis(serial)
```

### Métodos Principais

#### `execute_action(action)`
Executa comando de movimento.

**Parâmetros:**
- `action`: dict com `{'command', 'speed', 'duration'}`

**Comandos válidos:**
- `w`: Avançar
- `s`: Recuar
- `a`: Girar esquerda
- `d`: Girar direita
- `q`: Parar

**Exemplo:**
```python
chassis.execute_action({
    'command': 'w',
    'speed': 200,
    'duration': 1.5
})
# Envia 'w200', aguarda 1.5s, envia 'q'
```

---

## Serial Handler

```python
from src.hardware.serial_handler import SerialHandler

serial = SerialHandler("COM5", 9600)
```

### Métodos Principais

#### `enviar_comando(comando)`
Envia comando serial.

**Parâmetros:**
- `comando`: str - Comando sem terminador

**Exemplo:**
```python
serial.enviar_comando('w150')  # Avançar a 150
serial.enviar_comando('e')     # Fazer scan
serial.enviar_comando('o')     # Ler odometria
```

---

#### `receber_scan_dados() -> list`
Recebe scan completo (19 pontos).

**Retorno:**
```python
[(angulo_int, distancia_int), ...]
```

**Exemplo:**
```python
scan = serial.receber_scan_dados()
# [(0, 350), (10, 420), (20, 380), ..., (180, 300)]
```

---

#### `receber_odometria_dados() -> tuple`
Recebe odometria dos encoders virtuais.

**Retorno:**
```python
(dx_cm, dy_cm, dtheta_rad)  # float, float, float
```

**Exemplo:**
```python
dx, dy, dtheta = serial.receber_odometria_dados()
# (12.45, 3.21, 0.15)
```

---

## State

```python
from src.robot.state import State

state = State()
```

### Métodos Principais

#### `update_pose(x_cm, y_cm, theta_rad)`
Atualiza pose completa.

**Exemplo:**
```python
state.update_pose(525.5, 480.2, 1.57)
print(state)
# State(x=525.50cm, y=480.20cm, theta=90.00deg)
```

---

## Corpo Simulado

```python
from simulation.corpo_e_mundo_sim import CorpoRoboSimulado

corpo = CorpoRoboSimulado()
```

### Métodos Principais

#### `set_velocidades(linear_percent, angular_percent)`
Define velocidades do robô.

**Parâmetros:**
- `linear_percent`: float -1.0 a 1.0 (frente/trás)
- `angular_percent`: float -1.0 a 1.0 (esq/dir)

**Exemplo:**
```python
corpo.set_velocidades(0.6, 0.0)  # 60% velocidade máxima frontal
corpo.set_velocidades(0.0, -0.5) # 50% rotação direita
```

---

#### `atualizar_fisica(dt)`
Avança simulação física.

**Parâmetros:**
- `dt`: float - Delta time em segundos

**Exemplo:**
```python
corpo.atualizar_fisica(1/60)  # 60 FPS
```

---

#### `get_odometria_e_resetar() -> tuple`
Retorna e zera encoders virtuais.

**Retorno:**
```python
(dx_cm, dy_cm, dtheta_rad)
```

**Exemplo:**
```python
dx, dy, dtheta = corpo.get_odometria_e_resetar()
# (12.45, 3.21, 0.15)
# Encoders zerados após leitura
```

---

#### `get_distancia_em_angulo(angulo_servo_graus) -> int`
Simula leitura laser.

**Parâmetros:**
- `angulo_servo_graus`: int 0-180

**Retorno:**
- distancia_cm: int

**Exemplo:**
```python
dist = corpo.get_distancia_em_angulo(90)  # Frente
# 350 (cm)
```

---

## MQTT Publisher

```python
from src.communication.mqtt_publisher import MQTTPublisher

mqtt = MQTTPublisher("localhost", 1883)
```

### Métodos Principais

#### `publicar_status(robot_state)`
Publica JSON com status.

**Exemplo:**
```python
mqtt.publicar_status(state)
# Publica em 'robo/status':
# {"x": 525.5, "y": 480.2, "theta": 90.0, "timestamp": "..."}
```

---

#### `publicar_mapa(caminho_imagem)`
Publica imagem do mapa.

**Parâmetros:**
- `caminho_imagem`: str - Path para PNG

**Exemplo:**
```python
mqtt.publicar_mapa("output/maps/map_slam_latest.png")
# Publica em 'robo/mapa' (base64)
```

---

## Settings

```python
from src.config.settings import Settings

settings = Settings()
```

### Atributos

```python
settings.serial_port          # "COM5"
settings.baud_rate            # 9600
settings.mqtt_broker_host     # "localhost"
settings.mqtt_broker_port     # 1883
settings.map_width_px         # 500
settings.map_height_px        # 500
settings.map_size_meters      # 10
settings.map_output_dir       # "output/maps"
```

---

## Constantes (robot_specifications.py)

### Velocidades
```python
VELOCIDADE_MAX_LINEAR_CM_S = 8.0      # cm/s
VELOCIDADE_MAX_ANGULAR_GRAUS_S = 45.0 # graus/s
MAX_VELOCIDADE_ARDUINO = 255.0
```

### Física
```python
SUBPASSOS_FISICA = 10
RAIO_ROBO_CM = 4.0
```

### Navegação
```python
FORWARD_CONFIDENCE_THRESHOLD_CM = 75.0
STALLED_DISTANCE_THRESHOLD_CM = 20.0
MAP_COVERAGE_STABILITY_THRESHOLD = 50
CYCLES_TO_CONFIRM_COMPLETION = 75
```

---

## Exemplo de Uso Completo

```python
from src.navigation.navigator import Navigator
from src.robot.chassis import Chassis
from src.hardware.serial_handler import SerialHandler
from src.mapping.slam_manager import SLAMManager
from src.robot.state import State
import time

# Setup
serial = SerialHandler("COM5", 9600)
chassis = Chassis(serial)
navigator = Navigator()
slam = SLAMManager()
state = State()

# Scan inicial
serial.enviar_comando('e')
scan = serial.receber_scan_dados()

# Loop principal
while True:
    # Decisão
    pose = (state.x_cm, state.y_cm, state.theta_deg)
    action = navigator.decide_next_action(scan, pose)
    
    # Atuação
    chassis.execute_action(action)
    time.sleep(0.8)
    
    # Odometria
    serial.enviar_comando('o')
    delta = serial.receber_odometria_dados()
    
    # Percepção
    serial.enviar_comando('e')
    scan = serial.receber_scan_dados()
    
    # SLAM
    slam.update(scan, delta)
    x, y, theta = slam.get_corrected_pose_cm_rad()
    
    # Atualização
    state.update_pose(x, y, theta)
    navigator.update_position(x, y)
    
    print(state)
```

---

*Referência completa da API - rppi3_fleet v1.0*
