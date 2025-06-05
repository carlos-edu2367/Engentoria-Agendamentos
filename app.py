# engentoria/app.py
"""
Ponto de Entrada Principal da Aplicação Engentoria.

Este módulo é responsável por:
1. Configurar o ambiente da aplicação, incluindo o sys.path.
2. Inicializar o logging.
3. Definir e instanciar o `ApplicationController`, que gerencia o fluxo
   entre as janelas de login e a aplicação principal.
4. Realizar configurações iniciais como criação/verificação de tabelas do banco,
   atualização de estrutura do banco, limpeza de dados antigos e geração da agenda.
5. Iniciar a interface gráfica do usuário (GUI) com a janela de login.
"""
import sys
import os

# --- Configuração do sys.path ---
# Garante que os módulos do projeto possam ser importados corretamente,
# adicionando o diretório atual (onde app.py está) ao início do sys.path.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# --- Importações Principais ---
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont # QFont pode ser usado para definir fontes padrão, se necessário
from typing import Optional # Para type hinting de atributos que podem ser None
import logging # Para registrar eventos e informações durante a execução

# Importa as Views principais da aplicação
from views.login_view import LoginView
from views.main_app_view import MainAppView

# Importa funções de inicialização do banco de dados e da agenda
from models.database import criar_tabelas
from models.imovel_model import atualizar_estrutura_banco # Para atualizações de schema do banco
# A geração da agenda será chamada explicitamente após a limpeza, se necessário.

# Importa a rotina de limpeza do banco de dados
from utils.cleanup_routines import executar_limpeza_inicial_banco

# Configuração básica do logging para registrar informações em nível INFO ou superior.
# O formato inclui timestamp, nível do log, nome do arquivo, número da linha e a mensagem.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')


class ApplicationController:
    """
    Controla o fluxo principal da aplicação Engentoria.

    Esta classe gerencia a transição entre a janela de login e a janela
    principal da aplicação. Também é responsável por orquestrar as
    configurações iniciais, como a inicialização do banco de dados e
    a exibição da primeira view (LoginView).
    """
    def __init__(self):
        """
        Construtor do ApplicationController.

        Inicializa a QApplication, as referências às janelas (login e principal)
        como None e chama o método de setup da aplicação.
        """
        self.app = QApplication(sys.argv) # Instância principal da aplicação Qt
        self.login_window: Optional[LoginView] = None # Referência à janela de login, inicialmente None
        self.main_window: Optional[MainAppView] = None # Referência à janela principal, inicialmente None

        self._setup_application() # Chama as rotinas de configuração inicial

    def _setup_application(self) -> None:
        """
        Configurações iniciais da aplicação.

        Este método orquestra:
        - Criação/verificação das tabelas do banco de dados.
        - Atualização da estrutura do banco (ex: adicionar novas colunas).
        - Execução de rotinas de limpeza de dados antigos ou órfãos.
        - Geração/atualização da agenda baseada nos horários fixos dos vistoriadores.
        - Cadastro de um usuário administrador padrão, se não existir.
        """
        logging.info("Iniciando configuração da aplicação...")

        logging.info("Verificando/Criando tabelas do banco de dados...")
        criar_tabelas() # Garante que todas as tabelas necessárias existam

        logging.info("Verificando/Atualizando estrutura do banco (se necessário)...")
        atualizar_estrutura_banco() # Executa migrações de schema, como adicionar colunas

        # Executa a rotina de limpeza do banco de dados para remover dados desatualizados
        # ou inconsistentes antes de popular a agenda.
        logging.info("Executando rotina de limpeza de dados antigos e órfãos...")
        executar_limpeza_inicial_banco(meses_antiguidade_agendamentos=3) # Ex: Limpa agendamentos com mais de 3 meses

        # Gera a agenda (slots de horário) baseada nos horários fixos dos vistoriadores.
        # É importante que isso ocorra após a limpeza para evitar popular horários que seriam removidos.
        logging.info("Gerando/Atualizando agenda baseada em horários fixos (se houver)...")
        from models.agenda_model import gerar_agenda_baseada_em_horarios_fixos # Importação local para evitar dependência circular no topo
        gerar_agenda_baseada_em_horarios_fixos()

        logging.info("Configuração inicial do banco de dados e dados concluída.")

        # Cadastra um usuário administrador padrão se não existir um com o e-mail específico.
        # Isso é útil para a primeira execução do sistema ou para garantir um acesso de fallback.
        from models.usuario_model import login_usuario, cadastrar_usuario # Importação local
        admin_email = "engentoria@outlook.com"
        admin_pass = "123123"
        if not login_usuario(admin_email, admin_pass): # Verifica se o admin já existe tentando logar
            logging.info(f"Usuário admin padrão ('{admin_email}') não encontrado. Tentando cadastrar...")
            cadastrado_id = cadastrar_usuario(
                nome="Administrador Padrão",
                email=admin_email,
                senha=admin_pass,
                tipo="adm", # Define o tipo como administrador
                telefone1="000000000" # Telefone placeholder
            )
            if cadastrado_id:
                logging.info(f"Usuário admin padrão cadastrado com ID: {cadastrado_id}")
            else:
                logging.error(f"Falha ao cadastrar usuário admin padrão ('{admin_email}').")
        else:
            logging.info(f"Usuário admin padrão ('{admin_email}') já existe.")

    def mostrar_login_view(self) -> None:
        """
        Cria e exibe a janela de login.

        Se a janela principal estiver aberta, ela é fechada primeiro.
        Conecta o sinal `login_sucesso` da LoginView ao método `mostrar_main_app_view`.
        """
        if self.main_window: # Se a janela principal estiver aberta
            self.main_window.close() # Fecha-a
            self.main_window = None # Remove a referência

        self.login_window = LoginView() # Cria uma nova instância da janela de login
        # Conecta o sinal de login bem-sucedido da LoginView
        # ao método que mostrará a janela principal da aplicação.
        self.login_window.login_sucesso.connect(self.mostrar_main_app_view)
        self.login_window.show() # Exibe a janela de login

    def mostrar_main_app_view(self, user_id: int, user_type: str) -> None:
        """
        Chamado quando o login é bem-sucedido.

        Fecha a janela de login (se aberta) e cria e exibe a janela principal
        da aplicação, passando o ID e o tipo do usuário logado.

        Args:
            user_id (int): O ID do usuário que realizou o login.
            user_type (str): O tipo do usuário (ex: 'adm', 'vistoriador').
        """
        logging.info(f"Login bem-sucedido. User ID: {user_id}, Tipo: {user_type}. Abrindo janela principal.")
        if self.login_window: # Se a janela de login estiver aberta
            self.login_window.close() # Fecha-a
            self.login_window = None # Remove a referência

        # Cria uma nova instância da janela principal, passando os dados do usuário
        self.main_window = MainAppView(user_id, user_type)
        self.main_window.show() # Exibe a janela principal

    def run(self) -> None:
        """
        Inicia a aplicação.

        Mostra a janela de login e inicia o loop de eventos da QApplication.
        Este método bloqueia até que a aplicação seja encerrada.
        """
        self.mostrar_login_view() # Ponto de partida da interface gráfica
        sys.exit(self.app.exec_()) # Inicia o loop de eventos do Qt e sai quando ele terminar


# Ponto de entrada da aplicação quando o script é executado diretamente.
if __name__ == "__main__":
    controller_app = ApplicationController() # Cria a instância do controlador da aplicação
    controller_app.run() # Inicia a aplicação
