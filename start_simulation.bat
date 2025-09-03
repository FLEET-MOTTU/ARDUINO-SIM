@echo off

SET CONTAINER_NAME=mosquitto-broker-robo
ECHO.
ECHO [AUTOMACAO] Script de inicio do simulador robotico
ECHO [AUTOMACAO] Nome do container do Broker: %CONTAINER_NAME%

ECHO.
ECHO [AUTOMACAO] Verificando se o Docker estah rodando...
docker info > nul 2>&1
if %errorlevel% neq 0 (
    ECHO [ERRO] Docker Desktop nao parece estar rodando.
    ECHO [ERRO] Por favor, inicie o Docker e tente novamente.
    pause
    exit /b
)
ECHO [AUTOMACAO] Docker OK.

ECHO.
ECHO [AUTOMACAO] Gerenciando o container do Broker MQTT...

docker start %CONTAINER_NAME% > nul 2>&1 || (
    ECHO [DOCKER] Container nao encontrado ou nao pode ser iniciado. Tentando criar um novo...    
    docker run -d -p 1883:1883 --name %CONTAINER_NAME% eclipse-mosquitto
)

ECHO [AUTOMACAO] Broker MQTT (%CONTAINER_NAME%) esta em execucao.

ECHO.
ECHO [AUTOMACAO] Aguardando 5 segundos para o broker inicializar completamente...
TIMEOUT /T 5 /NOBREAK > nul

ECHO.
ECHO [AUTOMACAO] Iniciando os programas Python em novas janelas...

ECHO [AUTOMACAO] -> Iniciando o Simulador (Firmware + Mundo Visual)...
START "Simulador Robótico (Firmware)" cmd /k python firmware.py --port COM6

TIMEOUT /T 2 /NOBREAK > nul

ECHO [AUTOMACAO] -> Iniciando o Cerebro do Robo (main.py)...
START "Cérebro do Robô (RPi)" cmd /k python main.py

ECHO.
ECHO [AUTOMACAO] Setup concluido! Duas novas janelas foram abertas.
ECHO [AUTOMACAO] Voce pode fechar esta janela agora.
ECHO.
pause