# 📚 Documentação Técnica das Classes

## Módulos Principais

### 🧭 Navigator (`src/navigation/navigator.py`)

**Propósito**: Sistema de decisão inteligente com memória espacial para navegação autônoma.

**Atributos Principais**:
- `visit_grid` (20x20): Grid numpy rastreando visitas por célula
- `DANGER_THRESHOLD_CM` (50.0): Distância mínima para evasão
- `position_history` (deque): Últimas 15 posições para detecção de loop
- `committed_action`: Ação comprometida para evitar oscilações

**Métodos**:
```python
decide_next_action(scan_data, robot_pose) -> dict
    """Decide próxima ação baseado em hierarquia de prioridades"""
    Retorna: {'command': 'w'|'s'|'a'|'d', 'speed': 0-255, 'duration': segundos}

update_position(x_cm, y_cm)
    """Atualiza grid de memória com nova posição"""

is_stuck_in_loop() -> bool
    """Detecta loop se <4 células únicas em 10 movimentos"""

get_exploration_bias(visits) -> float
    """Retorna bias baseado em visitas: 0→+200cm, 3+→-150cm"""
```

**Hierarquia de Decisão**:
1. **Compromisso**: Continua ação anterior se tiver ciclos restantes
2. **Evasão**: <30cm = ré 0.5s, 30-50cm = rotação 270° (3s)
3. **Anti-loop**: Avanço forçado se loop detectado (cooldown 10s)
4. **Exploração**: Escolhe setor (D/F/E) com maior distância + bias

---

### 🗺️ SLAM Manager (`src/mapping/slam_manager.py`)

**Propósito**: Wrapper para BreezySLAM com proteções contra drift.

**Configuração Atual**:
```python
RMHC_SLAM(
    laser=Laser(19, 10Hz, 180°, 3000mm),
    map_size_pixels=500,
    map_size_meters=10,
    map_quality=20,        # Baixo = estável, alto = detalhado
    hole_width_mm=1200     # Tolerância a inconsistências
)
```

**Métodos**:
```python
update(scan_data_cm, odometry_delta)
    """Processa scan + odometria com limitação de deltas"""
    Limites: 15cm/ciclo, 20°/ciclo

get_corrected_pose_cm_rad() -> (x, y, θ)
    """Retorna pose corrigida com clamping nos bounds"""

get_map_image() -> PIL.Image
    """Retorna mapa atual como imagem PIL"""
```

**Proteções**:
- Delta linear máximo: 15cm/ciclo
- Delta angular máximo: 20°/ciclo  
- Pose clamped: [0, map_size_meters * 100]

---

### 🚗 Chassis (`src/robot/chassis.py`)

**Propósito**: Abstração de controle dos motores via serial.

**Métodos**:
```python
execute_action(action: dict)
    """Executa ação com validação de parâmetros"""
    action = {'command': 'w', 'speed': 150, 'duration': 1.0}
    
    Validações:
    - speed ∈ [0, 255]
    - duration > 0
    - command ∈ ['w', 's', 'a', 'd', 'q']
    
    Fluxo:
    1. Envia comando (ex: 'w150')
    2. Aguarda duração (time.sleep)
    3. Envia stop ('q')
```

**Comandos Suportados**:
- `w<speed>`: Avançar
- `s<speed>`: Recuar
- `a<speed>`: Girar esquerda
- `d<speed>`: Girar direita
- `q`: Parar

---

### 📡 Serial Handler (`src/hardware/serial_handler.py`)

**Propósito**: Comunicação serial (protocolo Arduino).

**Métodos**:
```python
enviar_comando(comando: str)
    """Envia comando terminado em \\n"""
    Exemplo: 'w150\\n'

receber_scan_dados() -> list[(angulo, distancia)]
    """Recebe 19 leituras no formato 'angulo;distancia'"""
    Retorna: [(0, 350), (10, 420), ..., (180, 300)]

receber_odometria_dados() -> (dx, dy, dθ)
    """Recebe odometria real dos encoders virtuais"""
    Formato: 'dx;dy;dtheta\\n'
```

**Protocolo**:
- Baudrate: 9600
- Timeout: 3s
- Terminador: `\n`
- Encoding: UTF-8

---

### 🎮 Corpo Simulado (`simulation/corpo_e_mundo_sim.py`)

**Propósito**: Física do robô com encoders virtuais.

**Atributos**:
- `x_cm, y_cm`: Posição atual (ground truth)
- `angulo_rad`: Orientação atual
- `velocidade_linear/angular`: Percentual (-1.0 a 1.0)
- `delta_*_acumulado`: Encoders virtuais

**Métodos**:
```python
set_velocidades(linear_percent, angular_percent)
    """Define velocidades desejadas (-1.0 a 1.0)"""

atualizar_fisica(dt)
    """Loop de física com SUBPASSOS_FISICA=10"""
    
    Fluxo:
    1. Calcula rotação e deslocamento ideal
    2. Divide em 10 subpassos
    3. Move passo a passo, para se colidir
    4. Acumula deslocamento real em encoders
    5. Atualiza pose final

get_odometria_e_resetar() -> (dx, dy, dθ)
    """Retorna encoders acumulados e zera"""
    Odometria PERFEITA (ground truth)

get_distancia_em_angulo(angulo_servo) -> int
    """Simula laser rangefinder"""
    Raycast do mundo virtual
```

**Especificações**:
- Velocidade linear: 8cm/s (VELOCIDADE_MAX_LINEAR_CM_S)
- Velocidade angular: 45°/s (VELOCIDADE_MAX_ANGULAR_GRAUS_S)
- Raio colisão: 4cm
- Subpassos física: 10 (precisão de colisão)

---

### 🌍 Planta Virtual (`simulation/planta_virtual.py`)

**Propósito**: Mundo simulado com paredes e detecção de colisão.

**Paredes (cm)**:
```python
PAREDES_RECTANGLES_CM = [
    ((30, 30), (30, 450)),    # Esquerda
    ((30, 450), (450, 450)),  # Topo
    ((450, 450), (450, 30)),  # Direita
    ((450, 30), (30, 30)),    # Base
    # ... obstáculos internos
]
```

**Métodos**:
```python
verificar_colisao_robo(pos_cm) -> bool
    """Verifica se posição colide com paredes"""
    Usa raio de RAIO_ROBO_CM=4cm

calcular_distancia(pos, angulo) -> int
    """Raycast para simular laser rangefinder"""
    Retorna: distância até parede mais próxima (cm)

desenhar(robot_pos, robot_angle, scan_points, mapa_surface)
    """Renderiza mundo no Pygame"""
```

---

### 🔄 Laser Odometry (`src/odometry/laser_odometry.py`)

**Propósito**: ICP scan matching para odometria visual *(não usado atualmente)*.

**Métodos**:
```python
calculate_delta(current_scan) -> (dx, dy, dθ)
    """Calcula movimento usando ICP (SimpleICP)"""
    
    Parâmetros ICP:
    - max_overlap_distance: 25cm
    - max_iterations: 30
    - min_change: 0.001
    
    Filtros:
    - Outlier removal (3σ ou 2x mediana)
    - Mínimo 8 pontos válidos
    - Delta máximo: 20cm/30° por ciclo
```

**Status**: Desabilitado em favor de encoders virtuais (mais precisos).

---

### 📊 State (`src/robot/state.py`)

**Propósito**: Armazena pose atual do robô.

```python
class State:
    x_cm: float
    y_cm: float
    theta_rad: float
    
    def update_pose(x, y, theta):
        """Atualiza pose completa"""
    
    def __str__():
        """Formato: State(x=500.00cm, y=500.00cm, theta=0.00deg)"""
```

---

### 📤 MQTT Publisher (`src/communication/mqtt_publisher.py`)

**Propósito**: Publica telemetria para broker MQTT.

**Tópicos**:
- `robo/status`: JSON com pose e timestamp
- `robo/mapa`: Imagem PNG do mapa (base64)

**Métodos**:
```python
publicar_status(robot_state: State)
    """Publica JSON: {x, y, theta, timestamp}"""

publicar_mapa(caminho_imagem: str)
    """Publica imagem PNG via MQTT"""
```

---

### ⚙️ Settings (`src/config/settings.py`)

**Propósito**: Carrega configurações do `.env` usando Pydantic.

**Campos**:
```python
serial_port: str = "COM5"
baud_rate: int = 9600
mqtt_broker_host: str = "localhost"
mqtt_broker_port: int = 1883
map_width_px: int = 500
map_height_px: int = 500
map_size_meters: int = 10
```

---

## 🔄 Fluxo de Execução (Main Loop)

```python
while True:
    # 1. DECISÃO
    action = navigator.decide_next_action(scan_data, pose)
    
    # 2. ATUAÇÃO
    chassis.execute_action(action)
    time.sleep(0.8)  # Aguarda movimento completar
    
    # 3. ODOMETRIA (encoders virtuais)
    serial_handler.enviar_comando('o')
    delta = serial_handler.receber_odometria_dados()
    
    # 4. PERCEPÇÃO
    serial_handler.enviar_comando('e')
    scan_data = serial_handler.receber_scan_dados()
    
    # 5. SLAM
    slam_manager.update(scan_data, delta)
    corrected_pose = slam_manager.get_corrected_pose()
    
    # 6. ATUALIZAÇÃO DE ESTADO
    robot_state.update_pose(*corrected_pose)
    navigator.update_position(x, y)
    
    # 7. TELEMETRIA
    map_image = slam_manager.get_map_image()
    save_map_image(map_image, "output/maps/map_slam_latest.png")
    mqtt_publisher.publicar_mapa(caminho_mapa)
```

---

## 📐 Especificações Técnicas

### Parâmetros de Navegação
- `DANGER_THRESHOLD_CM`: 50cm
- `FORWARD_CONFIDENCE_THRESHOLD_CM`: 75cm
- `Grid de memória`: 20x20 células (50cm cada)
- `Loop threshold`: <4 células únicas em 10 movimentos

### Parâmetros de Física
- `VELOCIDADE_MAX_LINEAR_CM_S`: 8cm/s
- `VELOCIDADE_MAX_ANGULAR_GRAUS_S`: 45°/s
- `SUBPASSOS_FISICA`: 10
- `RAIO_ROBO_CM`: 4cm

### Parâmetros de SLAM
- `map_quality`: 20 (conservador)
- `hole_width_mm`: 1200 (tolerante)
- `Delta linear máximo`: 15cm/ciclo
- `Delta angular máximo`: 20°/ciclo
- `Mapa`: 500x500px = 10m x 10m

### Timing
- Delay pós-ação: 800ms
- Scan: 19 pontos (0-180°, 10° step)
- Scan latency: 40ms/ponto (simulado)
- Loop rate: ~1.5 ciclos/segundo

---

## 🎯 Pontos de Atenção

### Performance
- ICP desabilitado (encoders mais eficientes)
- SLAM em modo conservador (menos CPU)
- Velocidades reduzidas (melhor qualidade de mapa)

### Configuração
- Portas virtuais **devem** estar pareadas (COM5↔COM6)
- Docker MQTT deve estar rodando antes
- Biblioteca BreezySLAM deve estar em `libs/`

### Troubleshooting
- Motion blur → Reduzir velocidades em `robot_specifications.py`
- Robot stuck → Verificar se firmware está rodando
- ICP errors → Normal se robô parado (encoders resolvem)

---

