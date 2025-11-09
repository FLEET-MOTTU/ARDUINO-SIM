# 🤖 Sistema Autônomo de Mapeamento e Navegação com SLAM

Sistema de robótica simulada com mapeamento SLAM (Simultaneous Localization and Mapping) em tempo real, desenvolvido para demonstrar navegação autônoma inteligente com anti-colisão e exploração espacial.

## 📋 Visão Geral

Este projeto implementa um robô autônomo virtual que:
- 🗺️ **Mapeia ambientes** usando algoritmo RMHC-SLAM (BreezySLAM)
- 🧭 **Navega autonomamente** com memória espacial para evitar loops
- 🚧 **Detecta e desvia de obstáculos** em tempo real
- 📡 **Comunica via MQTT** para monitoramento remoto
- 🎮 **Simula física realista** com detecção de colisão precisa

### Arquitetura Híbrida (Cérebro + Corpo)

O sistema separa **inteligência** (main.py) da **física** (firmware.py) através de comunicação serial virtual, simulando a arquitetura real de um robô com microcontrolador.

```
┌─────────────────────┐         COM5 ↔ COM6        ┌──────────────────────┐
│   CÉREBRO (RPi)     │ ◄────Serial Virtual────► │   CORPO (Arduino)     │
│                     │                            │                       │
│ • SLAM Manager      │                            │ • Física (Pygame)     │
│ • Navigator         │                            │ • Sensores Laser      │
│ • ICP Odometry      │                            │ • Encoders Virtuais   │
│ • MQTT Publisher    │                            │ • Motor Controller    │
└─────────────────────┘                            └──────────────────────┘
```

## 🚀 Quick Start

### Pré-requisitos

- Python 3.8+
- Docker Desktop (para MQTT broker)
- **com0com** (Windows) ou similar para portas seriais virtuais
  - [Download aqui](https://sourceforge.net/projects/com0com/)
  - Criar par virtual: `COM5 ↔ COM6`

### Instalação

```bash
# 1. Clonar repositório
git clone https://github.com/FLEET-MOTTU/ARDUINO-SIM.git
cd ARDUINO-SIM

# 2. Criar ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar portas virtuais (Windows)
# Instalar com0com e criar par COM5-COM6
```

### Execução Rápida

```bash
# Opção 1: Script automático (recomendado)
start_simulation.bat

# Opção 2: Manual (2 terminais)
# Terminal 1:
python firmware.py --port COM6

# Terminal 2:
python main.py
```

### Resultados

- **Janela Pygame**: Visualização da simulação física (robô + laser scan)
- **Mapa gerado**: `output/maps/map_slam_latest.png`
- **MQTT**: Tópicos `robo/status` e `robo/mapa` (localhost:1883)

## 📁 Estrutura do Projeto

```
rppi3_fleet/
├── main.py                      # Loop principal do cérebro autônomo
├── firmware.py                  # Simulador físico (corpo do robô)
├── robot_specifications.py      # Parâmetros centralizados (velocidades, física)
├── requirements.txt             # Dependências Python
├── .env                         # Configurações (portas serial, MQTT)
│
├── src/                         # Módulos do cérebro
│   ├── config/
│   │   └── settings.py          # Carregamento de configurações (.env)
│   ├── hardware/
│   │   └── serial_handler.py    # Comunicação serial (protocolo Arduino)
│   ├── robot/
│   │   ├── chassis.py           # Abstração de controle dos motores
│   │   └── state.py             # Estado do robô (pose x,y,θ)
│   ├── odometry/
│   │   └── laser_odometry.py    # ICP scan matching (não usado atualmente)
│   ├── mapping/
│   │   └── slam_manager.py      # Wrapper para BreezySLAM
│   ├── navigation/
│   │   └── navigator.py         # IA de navegação (memória espacial)
│   └── communication/
│       └── mqtt_publisher.py    # Cliente MQTT para telemetria
│
├── simulation/                  # Módulos do corpo (física)
│   ├── corpo_e_mundo_sim.py     # Física do robô + encoders virtuais
│   └── planta_virtual.py        # Mundo simulado (paredes, colisões)
│
├── libs/
│   └── BreezySLAM-master/       # Biblioteca SLAM (submodule)
│
├── output/
│   └── maps/                    # Mapas gerados (.png)
│
└── dashboard/                   # Interface Streamlit (monitoramento)
    ├── app.py                   # Dashboard web
    └── simulator.py             # Simulador de frota (8 motos)
```

## 🧩 Componentes Principais

### 1. **Navigator** (`src/navigation/navigator.py`)
Sistema de decisão inteligente com memória espacial.

**Funcionalidades:**
- Grid 20x20 rastreia células visitadas
- Bias de exploração: +200cm (nunca visitado) → -150cm (visitado 3+x)
- Detecção de loops: <4 células únicas em 10 movimentos
- Anti-colisão com 2 níveis:
  - `<30cm`: Ré de emergência (0.5s)
  - `30-50cm`: Rotação 270° (3s)

### 2. **SLAM Manager** (`src/mapping/slam_manager.py`)
Wrapper para BreezySLAM com proteções contra drift.

**Configuração Atual:**
- `map_quality=20` (estabilidade > detalhes)
- `hole_width_mm=1200` (tolerante a inconsistências)
- Deltas limitados: 15cm/20° por ciclo
- Pose clamping: [0, map_size]

### 3. **Corpo Simulado** (`simulation/corpo_e_mundo_sim.py`)
Física do robô com encoders virtuais.

**Recursos:**
- Movimento com `SUBPASSOS_FISICA=10` (colisão precisa)
- Encoders virtuais: acumulam dx, dy, dθ reais
- Raio de colisão: 4cm
- Velocidades: 8cm/s linear, 45°/s angular

### 4. **Serial Handler** (`src/hardware/serial_handler.py`)
Protocolo de comunicação serial (simula Arduino).

**Comandos:**
- `w<speed>`: Avançar (0-255)
- `s<speed>`: Recuar (0-255)
- `d<speed>`: Girar direita
- `a<speed>`: Girar esquerda
- `q`: Parar
- `e`: Scan 180° (19 pontos)
- `o`: Ler odometria (encoders)

## ⚙️ Configuração

### Arquivo `.env`

```env
# Comunicação Serial
SERIAL_PORT=COM5          # Porta do cérebro (pareia com COM6)
BAUD_RATE=9600

# MQTT Broker
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_TOPICO_STATUS=robo/status
MQTT_TOPICO_MAPA=robo/mapa
```

### Parâmetros de Tuning (`robot_specifications.py`)

```python
# Velocidades (afeta movimento e qualidade do mapa)
VELOCIDADE_MAX_LINEAR_CM_S = 8.0 # Reduzir se motion blur
VELOCIDADE_MAX_ANGULAR_GRAUS_S = 45.0

# Física (precisão vs performance)
SUBPASSOS_FISICA = 10 # Aumentar para colisão mais precisa

# Navegação
FORWARD_CONFIDENCE_THRESHOLD_CM = 75.0  # Quando avançar com confiança
```

## 📊 Dashboard (Opcional)

Interface Streamlit para monitoramento de frota (8 motos simuladas).

```bash
streamlit run dashboard/app.py
```

**Funcionalidades:**
- Visualização do mapa em tempo real
- Grid de zonas configurável (2-5 linhas/colunas)
- Tabela de status por moto
- Estatísticas de ocupação por zona
- Auto-refresh configurável (1-10s)

## 🐛 Troubleshooting

### Robô não se move
- ✅ Verifique se **ambos** os programas estão rodando
- ✅ Confirme par virtual `COM5 ↔ COM6` no Device Manager
- ✅ Logs do firmware devem mostrar comandos recebidos

### Mapa com motion blur / distorcido
- 🔧 Reduzir `VELOCIDADE_MAX_LINEAR_CM_S` (ex: 5cm/s)
- 🔧 Aumentar `time.sleep()` após ação (main.py, linha ~105)
- 🔧 Reduzir `map_quality` no SLAM (mais estável)

### ICP errors "Too few correspondences"
- ℹ️ Normal quando robô está parado (scans idênticos)
- ✅ Sistema agora usa encoders virtuais (mais preciso)

### Docker MQTT não inicia
```bash
# Verificar se Docker Desktop está rodando
docker info

# Reiniciar container manualmente
docker restart mosquitto-broker-robo
```

## 🔬 Algoritmos Utilizados

- **SLAM**: RMHC-SLAM (Random Mutation Hill Climbing)
- **Scan Matching**: SimpleICP (Iterative Closest Point) - *legacy*
- **Odometria**: Encoders virtuais da física simulada
- **Navegação**: Exploração baseada em memória espacial (grid)
- **Física**: Euler integration com multi-step collision detection

## 📝 Fluxo de Execução

```
1. INICIALIZAÇÃO
   ├─ Conectar serial (COM5)
   ├─ Conectar MQTT broker
   ├─ Inicializar SLAM (mapa 500x500px, 10m)
   └─ Scan inicial (19 pontos)

2. LOOP PRINCIPAL (cada ciclo)
   ├─ Navigator decide ação (w/s/a/d + speed)
   ├─ Chassis executa comando via serial
   ├─ Aguardar movimento completar (800ms)
   ├─ Ler odometria real (encoders virtuais)
   ├─ Converter delta local → global
   ├─ Fazer novo scan (19 pontos)
   ├─ SLAM processa scan + odometria
   ├─ Atualizar pose do robô
   ├─ Salvar mapa .png
   ├─ Publicar via MQTT
   └─ Verificar conclusão (robô parado + mapa estável)

3. FINALIZAÇÃO
   └─ Mapa completo salvo em output/maps/
```