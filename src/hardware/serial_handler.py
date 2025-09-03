import serial
import time


class SerialHandler:
    """Gerencia a comunicação de baixo nível com o Arduino REAL."""
    def __init__(self, porta, baud):
        """Tenta estabelecer uma conexão serial. Se falhar, levanta uma exceção."""
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
        

    def enviar_comando(self, comando):
        """Envia um comando para o Arduino pela porta serial."""
        print(f"CÉREBRO -> Enviando comando para o corpo: '{comando}'")
        comando_final = comando + '\n'
        self.conexao.write(comando_final.encode('utf-8'))


    def receber_scan_dados(self):
        """
        Recebe e processa os dados de um scan de 180 graus do Arduino.
        O protocolo espera 19 linhas de dados (de 0 a 180 graus, com passo de 10).
        """
        dados_brutos = []
        NUMERO_DE_LEITURAS_ESPERADAS = 19 
        
        print(f"CÉREBRO -> Aguardando {NUMERO_DE_LEITURAS_ESPERADAS} pontos de scan do Arduino...")
        
        for i in range(NUMERO_DE_LEITURAS_ESPERADAS):
            linha = self.conexao.readline().decode('utf-8').strip()
            if linha and ';' in linha:
                dados_brutos.append(linha)
            else:
                print(f"AVISO: Leitura {i+1}/{NUMERO_DE_LEITURAS_ESPERADAS} falhou ou retornou vazia (timeout?).")
        
        dados_processados = []
        for linha in dados_brutos:
            try:
                angulo_str, dist_str = linha.split(';')
                dados_processados.append((int(angulo_str), int(dist_str)))
            except ValueError:
                print(f"AVISO: Não foi possível processar a linha de dados: '{linha}'")
        
        print(f"Scan recebido e processado. {len(dados_processados)} pontos capturados.")
        return dados_processados
    

    def fechar_conexao(self):
        """Fecha a porta serial se ela estiver aberta."""
        if self.conexao and self.conexao.is_open:
            self.conexao.close()
            print("Conexão com o Arduino fechada.")
