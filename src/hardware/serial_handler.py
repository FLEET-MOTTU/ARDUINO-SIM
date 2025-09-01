import serial
import time

from src.config import settings


class SerialHandler:
    """Gerencia a comunicação de baixo nível com o Arduino."""
    def __init__(self, porta, baud):
        self.conexao = None
        self.em_simulacao = True
        try:
            print(f"Tentando conectar ao Arduino na porta {porta}...")
            self.conexao = serial.Serial(porta, baud, timeout=2)
            time.sleep(2)
            self.em_simulacao = False
            self.conexao.flushInput() # Limpa o buffer de entrada
            print("Conectado ao Arduino com sucesso!")
        except serial.SerialException:
            print(f"FALHA: Arduino não encontrado. Entrando em MODO DE SIMULAÇÃO.")


    def enviar_comando(self, comando):
        if not self.em_simulacao:
            comando_final = comando + '\n'
            self.conexao.write(comando_final.encode('utf-8'))
        print(f"CÉREBRO -> Enviando comando para o corpo: '{comando}'")


    def receber_scan_dados(self):
        dados_brutos = []
        if self.em_simulacao:
            print("CÉREBRO (SIM) -> Recebendo dados de scan simulados...")

            # Simulando os dados do arquivo de configuração
            DADOS_SIMULADOS_SCAN = [ "0;180", "10;175", "20;170", "30;90", "40;85", "50;80", "60;78", "70;75", "80;74", "90;73", "100;74", "110;75", "120;78", "130;80", "140;85", "150;90", "160;170", "170;175", "180;180" ]
            dados_brutos = DADOS_SIMULADOS_SCAN

        else:
            print("CÉREBRO -> Aguardando dados de scan do Arduino...")
            while True:
                linha = self.conexao.readline().decode('utf-8').strip()
                if linha:
                    if "FIM DO SCAN" in linha:
                        break
                    if ';' in linha:
                        dados_brutos.append(linha)
        
        dados_processados = []
        for linha in dados_brutos:
            try:
                angulo_str, dist_str = linha.split(';')
                dados_processados.append((int(angulo_str), int(dist_str)))
            except ValueError:
                print(f"AVISO: Não foi possível processar a linha de dados: '{linha}'")
        
        print(f"Scan recebido e processado. {len(dados_processados)} pontos capturados.")
        return dados_processados
