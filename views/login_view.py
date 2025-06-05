# engentoria/views/login_view.py

import sys
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QApplication, QMessageBox, QDialog, QMainWindow # Adicionado QMainWindow
)
from PyQt5.QtGui import QIcon, QFont # QIcon para ícones, QFont para fontes
from PyQt5.QtCore import Qt, pyqtSignal # pyqtSignal para comunicação entre widgets/janelas
from typing import Optional # Adicionado Optional

# Importando o controller de autenticação e os módulos de utilidades
from controllers.auth_controller import AuthController
from utils import styles # Módulo com estilos CSS-like para QSS
from utils.validators import is_valid_email # Função para validar formato de e-mail

# --- Janela de Diálogo para Redefinição de Senha (ForgotPasswordDialog) ---
class ForgotPasswordDialog(QDialog):
    """
    Janela de diálogo para o processo de redefinição de senha.

    Coleta e-mail, nova senha e confirmação da nova senha,
    e interage com o AuthController para processar a redefinição.
    """
    def __init__(self, auth_controller: AuthController, parent: Optional[QWidget] = None):
        """
        Construtor do ForgotPasswordDialog.

        Args:
            auth_controller (AuthController): Instância do controlador de autenticação.
            parent (Optional[QWidget]): Widget pai, se houver.
        """
        super().__init__(parent)
        self.auth_controller = auth_controller # Controller para a lógica de redefinição
        self.setWindowTitle("Redefinir Senha - Engentoria")
        self.setFixedSize(380, 320) # Tamanho fixo para o diálogo
        # self.setWindowIcon(QIcon("caminho/para/seu/icone.ico")) # Descomente e defina o caminho do ícone

        self.setStyleSheet(styles.STYLESHEET_BASE_DARK) # Aplica estilo base escuro
        self._init_ui()

    def _init_ui(self) -> None:
        """
        Inicializa a interface do usuário do diálogo de redefinição de senha.
        """
        layout = QVBoxLayout(self) # Layout principal vertical
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        title_label = QLabel("Redefinir Senha")
        title_label.setStyleSheet(styles.DIALOG_TITLE_STYLE) # Estilo para o título do diálogo
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Campo para e-mail
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Seu e-mail de cadastro")
        self.email_input.setStyleSheet(styles.LOGIN_INPUT_STYLE) # Reutiliza estilo de input do login
        layout.addWidget(self.email_input)

        # Campo para nova senha
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("Nova senha")
        self.new_password_input.setEchoMode(QLineEdit.Password) # Oculta a senha digitada
        self.new_password_input.setStyleSheet(styles.LOGIN_INPUT_STYLE)
        layout.addWidget(self.new_password_input)

        # Campo para confirmar nova senha
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirme a nova senha")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setStyleSheet(styles.LOGIN_INPUT_STYLE)
        layout.addWidget(self.confirm_password_input)

        # Label para exibir mensagens de erro ou sucesso (dentro do diálogo)
        self.message_label = QLabel("")
        self.message_label.setStyleSheet(styles.ERROR_MESSAGE_STYLE) # Estilo para mensagens de erro
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True) # Permite quebra de linha
        layout.addWidget(self.message_label)

        layout.addStretch(1) # Espaço flexível para empurrar botões para baixo

        # Layout para os botões de ação (Redefinir, Cancelar)
        buttons_layout = QHBoxLayout()
        self.reset_button = QPushButton("Redefinir Senha")
        self.reset_button.setStyleSheet(styles.PRIMARY_BUTTON_STYLE) # Botão primário
        self.reset_button.clicked.connect(self._handle_reset_password)

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setStyleSheet(styles.SECONDARY_BUTTON_STYLE) # Botão secundário
        self.cancel_button.clicked.connect(self.reject) # Fecha o diálogo com resultado 'Rejected'

        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addStretch() # Espaçador entre botões
        buttons_layout.addWidget(self.reset_button)
        layout.addLayout(buttons_layout)

    def _handle_reset_password(self) -> None:
        """
        Manipula o clique no botão "Redefinir Senha".

        Coleta os dados, realiza validações básicas e chama o controller.
        Exibe mensagens de sucesso ou erro.
        """
        email = self.email_input.text().strip()
        nova_senha = self.new_password_input.text() # Senhas não devem ter strip()
        confirmacao_nova_senha = self.confirm_password_input.text()

        # Validações básicas na View (o controller também fará validações mais robustas)
        if not email or not nova_senha or not confirmacao_nova_senha:
            self.message_label.setText("Todos os campos são obrigatórios.")
            self.message_label.setStyleSheet(styles.ERROR_MESSAGE_STYLE)
            return
        if not is_valid_email(email): # Valida formato do e-mail
            self.message_label.setText("Formato de e-mail inválido.")
            self.message_label.setStyleSheet(styles.ERROR_MESSAGE_STYLE)
            return
        if nova_senha != confirmacao_nova_senha: # Verifica se as senhas coincidem
            self.message_label.setText("As senhas não coincidem.")
            self.message_label.setStyleSheet(styles.ERROR_MESSAGE_STYLE)
            return
        if len(nova_senha) < 6 : # Exemplo de regra de complexidade de senha
            self.message_label.setText("A nova senha deve ter pelo menos 6 caracteres.")
            self.message_label.setStyleSheet(styles.ERROR_MESSAGE_STYLE)
            return

        # Chama o controller para processar a redefinição
        resultado = self.auth_controller.processar_redefinicao_senha(email, nova_senha, confirmacao_nova_senha)

        if resultado['success']:
            QMessageBox.information(self, "Sucesso", resultado['message']) # Exibe pop-up de sucesso
            self.accept()  # Fecha o diálogo com resultado 'Accepted'
        else:
            self.message_label.setText(resultado['message']) # Exibe erro no label do diálogo
            self.message_label.setStyleSheet(styles.ERROR_MESSAGE_STYLE)


# --- Janela de Login Principal (LoginView) ---
class LoginView(QWidget):
    """
    Janela principal de Login do sistema.

    Permite que o usuário insira e-mail e senha para autenticação.
    Emite um sinal `login_sucesso` contendo o ID e o tipo do usuário
    em caso de login bem-sucedido.
    """
    # Sinal emitido quando o login é bem-sucedido.
    # Passa o ID do usuário (int) e o tipo do usuário (str) como argumentos.
    login_sucesso = pyqtSignal(int, str)

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Construtor da LoginView.

        Args:
            parent (Optional[QWidget]): Widget pai, se houver.
        """
        super().__init__(parent)
        self.auth_controller = AuthController() # Controller para a lógica de login
        self.main_window: Optional[QMainWindow] = None # Referência para a janela principal do app (a ser aberta após login)

        self.setWindowTitle("Login - Engentoria")
        self.setGeometry(400, 200, 400, 500) # Posição (x,y) e tamanho (largura, altura)
        # self.setWindowIcon(QIcon("caminho/para/seu/icone_app.ico")) # Descomente e defina o ícone do app

        self.setStyleSheet(styles.STYLESHEET_BASE_DARK) # Aplica estilo base escuro
        self._init_ui()

    def _init_ui(self) -> None:
        """
        Inicializa a interface do usuário da janela de login.
        """
        main_layout = QVBoxLayout(self) # Layout principal vertical
        main_layout.setContentsMargins(40, 40, 40, 40) # Margens internas
        main_layout.setSpacing(20) # Espaçamento entre widgets
        main_layout.setAlignment(Qt.AlignCenter) # Centraliza o conteúdo verticalmente

        # Título do sistema
        title_label = QLabel("Engentoria") # Ou o nome do seu sistema
        title_label.setStyleSheet(styles.LOGIN_TITLE_STYLE) # Estilo para o título principal
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Campo de E-mail
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("E-mail") # Texto de ajuda no campo
        self.email_input.setStyleSheet(styles.LOGIN_INPUT_STYLE) # Estilo para campos de input
        self.email_input.setFixedHeight(45) # Altura fixa para o campo
        main_layout.addWidget(self.email_input)

        # Campo de Senha
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Senha")
        self.password_input.setEchoMode(QLineEdit.Password) # Oculta a senha
        self.password_input.setStyleSheet(styles.LOGIN_INPUT_STYLE)
        self.password_input.setFixedHeight(45)
        main_layout.addWidget(self.password_input)

        # Label para exibir mensagens de erro de login
        self.error_label = QLabel("")
        self.error_label.setStyleSheet(styles.ERROR_MESSAGE_STYLE) # Estilo para mensagens de erro
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True) # Permite quebra de linha para mensagens longas
        main_layout.addWidget(self.error_label)

        main_layout.addStretch(1) # Adiciona espaço flexível antes dos botões

        # Botão de Login
        self.login_button = QPushButton("Entrar")
        self.login_button.setStyleSheet(styles.PRIMARY_BUTTON_STYLE) # Estilo de botão primário
        self.login_button.setFixedHeight(50) # Altura do botão
        self.login_button.clicked.connect(self._handle_login) # Conecta ao método de manipulação de login
        main_layout.addWidget(self.login_button)

        # Botão "Esqueci minha senha"
        self.forgot_password_button = QPushButton("Esqueci minha senha")
        self.forgot_password_button.setStyleSheet(styles.TEXT_BUTTON_STYLE) # Estilo de botão de texto (link)
        self.forgot_password_button.setCursor(Qt.PointingHandCursor) # Muda cursor para mãozinha
        self.forgot_password_button.clicked.connect(self._show_forgot_password_dialog) # Abre diálogo de redefinição
        main_layout.addWidget(self.forgot_password_button, alignment=Qt.AlignCenter) # Alinha ao centro

        main_layout.addStretch(2) # Mais espaço flexível abaixo

        # Rodapé (opcional)
        footer_label = QLabel("© 2025 Neectify. Todos os direitos reservados.") # Exemplo de rodapé
        footer_label.setStyleSheet(styles.FOOTER_TEXT_STYLE) # Estilo para texto de rodapé
        footer_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(footer_label)


    def _handle_login(self) -> None:
        """
        Manipula o clique no botão "Entrar".

        Coleta e-mail e senha, realiza validações básicas, chama o controller
        para autenticação e trata o resultado.
        """
        email = self.email_input.text().strip() # Remove espaços extras do e-mail
        password = self.password_input.text() # Senha não deve ter strip()

        # Validação básica na View (o controller também validará)
        if not email or not password:
            self.error_label.setText("Por favor, preencha e-mail e senha.")
            return
        if not is_valid_email(email): # Valida formato do e-mail
            self.error_label.setText("Formato de e-mail inválido.")
            return

        self.login_button.setEnabled(False) # Desabilita o botão durante o processamento
        self.login_button.setText("Entrando...") # Feedback visual
        QApplication.processEvents() # Garante que a UI (texto do botão) atualize imediatamente

        # Chama o controller para processar o login
        resultado = self.auth_controller.processar_login(email, password)

        self.login_button.setEnabled(True) # Reabilita o botão
        self.login_button.setText("Entrar") # Restaura texto original

        if resultado['success']:
            self.error_label.setText("") # Limpa mensagem de erro, se houver
            print(f"Login bem-sucedido para ID: {resultado['user_id']}, Tipo: {resultado['user_type']}")
            # Emite o sinal de sucesso no login, passando ID e tipo do usuário.
            # Este sinal será conectado no arquivo principal da aplicação (ex: app.py)
            # para fechar a janela de login e abrir a janela principal do sistema.
            self.login_sucesso.emit(resultado['user_id'], resultado['user_type'])
            self.close() # Fecha a janela de login
        else:
            self.error_label.setText(resultado['message']) # Exibe mensagem de erro do controller
            self.password_input.clear() # Limpa o campo de senha em caso de erro
            self.password_input.setFocus() # Coloca o foco de volta no campo de senha


    def _show_forgot_password_dialog(self) -> None:
        """
        Cria e exibe o diálogo de redefinição de senha.
        """
        dialog = ForgotPasswordDialog(self.auth_controller, self) # Passa o controller e o parent
        dialog.exec_() # Exibe o diálogo de forma modal (bloqueia a janela de login)


# Bloco para testar esta view isoladamente
if __name__ == '__main__':
    # Adiciona o diretório raiz ao sys.path para encontrar os módulos
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir)) # Sobe dois níveis para 'engentoria'
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Importações necessárias para o teste, especialmente para criar dados iniciais no banco
    from models.database import criar_tabelas
    from models import usuario_model # Model para interagir com usuários

    # Garante que as tabelas do banco de dados existam
    criar_tabelas()

    # Cadastra um usuário administrador de teste se ele não existir.
    # Isso é apenas para facilitar o teste da tela de login.
    # Em uma aplicação real, o cadastro de usuários seria feito de outra forma.
    if not usuario_model.login_usuario("admin@engentoria.com", "admin123"): # Verifica se o admin já existe
         usuario_model.cadastrar_usuario("Admin Engentoria", "admin@engentoria.com", "admin123", "adm")


    app = QApplication(sys.argv) # Cria a aplicação Qt
    login_win = LoginView() # Instancia a janela de login

    # Função de exemplo para lidar com o sinal de login_sucesso
    # Em uma aplicação real, esta lógica estaria no arquivo principal (app.py)
    def handle_login_success(user_id: int, user_type: str) -> None:
        print(f"Sinal de login_sucesso recebido! User ID: {user_id}, Tipo: {user_type}")
        # Aqui, você normalmente abriria a janela principal do sistema, passando user_id e user_type.
        # Exemplo:
        # from views.main_app_view import MainAppView # Supondo que MainAppView é a janela principal
        # login_win.main_window = MainAppView(user_id, user_type)
        # login_win.main_window.show()
        QMessageBox.information(None, "Login Sucesso", f"Usuário ID: {user_id}\nTipo: {user_type}\n\nAbriria a janela principal aqui.")
        app.quit() # Fecha a aplicação de teste após o sucesso do login

    # Conecta o sinal login_sucesso da janela de login à função handle_login_success
    login_win.login_sucesso.connect(handle_login_success)
    login_win.show() # Exibe a janela de login
    sys.exit(app.exec_()) # Inicia o loop de eventos da aplicação
