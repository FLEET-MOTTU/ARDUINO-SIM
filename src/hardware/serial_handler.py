"""
Define a classe SerialHandler, a camada de abstração para a comunicação
serial de baixo nível.
"""

import serial
import time

class SerialHandler:
    """
    Gerencia a comunicação serial com o "Corpo" do robô (Arduino/Firmware).

    ARQUITETURA:
    Esta classe atua como um "Driver". Sua única responsabilidade é encapsular
    a complexidade da biblioteca `pyserial` e do protocolo de comunicação
    definido. Ela traduz chamadas de método Python de alto nível em
    operações de escrita e leitura de bytes na porta serial.
    """
    def __init__(self, porta: str, baud: int):
        """
        Tenta estabelecer uma conexão serial e a prepara para a comunicação.

        Args:
            porta (str): O nome da porta serial (ex: 'COM5').
            baud (int): A taxa de transmissão (baud rate), ex: 9600.
        """
        self.conexao = None
        try:
            print(f"Tentando conectar ao Arduino na porta {porta}...")
            self.conexao = serial.Serial(porta, baud, timeout=3)
            time.sleep(2)
            self.conexao.flushInput()
            print("Conectado ao Arduino com sucesso!")
        except serial.SerialException as e:
            print(f"FALHA: Não foi possível conectar ao Arduino. Verifique a porta e a conexão.")
            raise e

    def enviar_comando(self, comando: str):
        """
        Codifica e envia uma string de comando para o firmware.

        Este método garante que todos os comandos enviados sigam o protocolo
        padrão: uma string terminada por um caractere de nova linha ('\n').
        """
        print(f"CÉREBRO -> Enviando comando para o corpo: '{comando}'")
        comando_final = comando + '\n'
        self.conexao.write(comando_final.encode('utf-8'))

    def receber_scan_dados(self) -> list[tuple[int, int]]:
        """
        Recebe e processa um conjunto completo de dados de scan (180 graus).

        Este método é bloqueante e implementa o protocolo de recebimento de scan:
        1. Espera por um número fixo de linhas (NUMERO_DE_LEITURAS_ESPERADAS).
        2. Lê cada linha, que deve estar no formato "angulo;distancia".
        3. Lida com timeouts ou linhas malformadas de forma segura.

        Returns:
            list[tuple[int, int]]: Uma lista de tuplas (angulo, distancia).
        """
        dados_processados = []
        NUMERO_DE_LEITURAS_ESPERADAS = 19
        
        print(f"CÉREBRO -> Aguardando {NUMERO_DE_LEITURAS_ESPERADAS} pontos de scan do Arduino...")
        
        for i in range(NUMERO_DE_LEITURAS_ESPERADAS):
            linha = self.conexao.readline().decode('utf-8').strip()
            if linha and ';' in linha:
                try:
                    angulo_str, dist_str = linha.split(';')
                    dados_processados.append((int(angulo_str), int(dist_str)))
                except ValueError:
                    print(f"AVISO: Não foi possível processar a linha de dados: '{linha}'")
            else:
                print(f"AVISO: Leitura {i+1}/{NUMERO_DE_LEITURAS_ESPERADAS} falhou ou retornou vazia (timeout?).")
        
        print(f"Scan recebido e processado. {len(dados_processados)} pontos capturados.")
        return dados_processados

    def receber_odometria_dados(self) -> tuple[float, float, float]:
        """
        Recebe e processa a odometria real enviada pelo firmware.

        NOTA ARQUITETURAL: Este método suporta a arquitetura de "encoder virtual".
        Na implementação atual que usa odometria teórica, este método não é chamado,
        mas é mantido para flexibilidade e futuras iterações.

        Returns:
            tuple[float, float, float]: O delta de odometria (dx, dy, dtheta) ou (0,0,0) em caso de falha.
        """
        linha = self.conexao.readline().decode('utf-8').strip()
        if linha and ';' in linha:
            try:
                dx_str, dy_str, dtheta_str = linha.split(';')
                return (float(dx_str), float(dy_str), float(dtheta_str))
            except ValueError:
                print(f"AVISO: Não foi possível processar a linha de odometria: '{linha}'")
        
        return (0.0, 0.0, 0.0)

    def fechar_conexao(self):
        """Encerra a conexão serial de forma segura."""
        if self.conexao and self.conexao.is_open:
            self.conexao.close()
            print("Conexão com o Arduino fechada.")