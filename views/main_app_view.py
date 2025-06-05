# engentoria/views/main_app_view.py

import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QStackedWidget, QScrollArea, QFrame
)
from PyQt5.QtGui import QIcon, QFont, QPixmap # QPixmap para logo, se usado
from PyQt5.QtCore import Qt, QSize
from typing import Optional, Dict, Any # Adicionado Optional, Dict, Any

# Importações de utilidades e das views das páginas específicas
from utils import styles
from views.agenda_view_widget import AgendaViewWidget
from views.admin_view_widget import AdminViewWidget
from views.vistoriador_agenda_view import VistoriadorAgendaViewWidget
from views.gerenciar_vistoriador_view_widget import GerenciarVistoriadorViewWidget


class MainAppView(QMainWindow):
    """
    Janela Principal da Aplicação Engentoria.

    Esta janela é exibida após o login bem-sucedido e contém a navegação
    principal (sidebar) e a área de conteúdo (QStackedWidget) onde as
    diferentes seções/páginas do sistema são carregadas.
    """
    def __init__(self, user_id: int, user_type: str, parent: Optional[QWidget] = None):
        """
        Construtor da MainAppView.

        Args:
            user_id (int): ID do usuário logado.
            user_type (str): Tipo do usuário logado (ex: 'adm', 'vistoriador').
            parent (Optional[QWidget]): Widget pai, se houver.
        """
        super().__init__(parent)
        self.user_id = user_id # ID do usuário logado
        self.user_type = user_type # Tipo do usuário (determina as views acessíveis)

        self.setWindowTitle(f"Engentoria - Sistema de Vistorias ({user_type.capitalize()})")
        self.setGeometry(50, 50, 1250, 780) # Posição e tamanho iniciais da janela
        self.setStyleSheet(styles.STYLESHEET_BASE_DARK) # Aplica o tema escuro base
        self._init_ui()

    def _init_ui(self) -> None:
        """
        Inicializa a interface do usuário da janela principal.

        Configura o widget central, o layout principal (horizontal),
        a sidebar de navegação e o QStackedWidget para as páginas.
        """
        self.central_widget = QWidget() # Widget central que preenche a QMainWindow
        self.setCentralWidget(self.central_widget)

        # Layout principal horizontal: sidebar à esquerda, conteúdo à direita
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0) # Sem margens no layout principal
        self.main_layout.setSpacing(0) # Sem espaçamento entre sidebar e conteúdo

        self._create_sidebar() # Cria a barra lateral de navegação
        self.pages_stack = QStackedWidget() # Widget para empilhar as diferentes páginas
        self.pages_stack.setStyleSheet(f"background-color: {styles.COLOR_BACKGROUND_DARK}; padding: 0px;")
        self._create_pages() # Cria as instâncias das páginas (widgets)

        self.main_layout.addWidget(self.sidebar_widget) # Adiciona sidebar ao layout
        self.main_layout.addWidget(self.pages_stack, 1) # Adiciona área de páginas, ocupando o espaço restante (fator 1)

        # Define a página inicial a ser exibida e atualiza os dados dela, se necessário.
        # O primeiro botão na sidebar (índice 0) corresponderá à primeira página adicionada ao stack.
        self.switch_page(0)

    def _create_sidebar(self) -> None:
        """
        Cria a barra lateral (sidebar) com os botões de navegação.

        Os botões exibidos dependem do tipo de usuário (`self.user_type`).
        """
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setObjectName("sidebarWidget") # Para estilização específica via QSS
        self.sidebar_widget.setStyleSheet(styles.SIDEBAR_WIDGET_STYLE) # Aplica estilo da sidebar

        sidebar_layout = QVBoxLayout(self.sidebar_widget) # Layout vertical para a sidebar
        sidebar_layout.setContentsMargins(10, 15, 10, 15) # Margens internas da sidebar
        sidebar_layout.setSpacing(10) # Espaçamento entre os botões
        sidebar_layout.setAlignment(Qt.AlignTop) # Alinha botões ao topo

        # Dicionário para armazenar referências aos botões e nomes dos widgets associados
        self.sidebar_buttons: Dict[int, Dict[str, Any]] = {}
        page_idx_counter = 0 # Contador para o índice da página no QStackedWidget

        # --- Lógica para adicionar botões com base no tipo de usuário ---
        if self.user_type == 'adm': # Botões para administrador
            # Botão Agenda Geral (Admin)
            btn_agenda_adm = self._create_sidebar_button("🗓️ Agenda Geral", page_idx_counter)
            sidebar_layout.addWidget(btn_agenda_adm)
            self.sidebar_buttons[page_idx_counter] = {'button': btn_agenda_adm, 'widget_name': 'agenda_view_adm'}
            page_idx_counter += 1

            # Botão Painel Admin
            btn_admin_panel = self._create_sidebar_button("⚙️ Painel Admin", page_idx_counter)
            sidebar_layout.addWidget(btn_admin_panel)
            self.sidebar_buttons[page_idx_counter] = {'button': btn_admin_panel, 'widget_name': 'admin_panel_view'}
            page_idx_counter += 1

            # Botão Gerenciar Vistoriadores
            btn_gerenciar_vist = self._create_sidebar_button("👨‍💼 Gerenciar Vistoriadores", page_idx_counter)
            sidebar_layout.addWidget(btn_gerenciar_vist)
            self.sidebar_buttons[page_idx_counter] = {'button': btn_gerenciar_vist, 'widget_name': 'gerenciar_vist_view'}
            page_idx_counter += 1

        elif self.user_type == 'vistoriador': # Botões para vistoriador
            # Botão Minha Agenda (Vistoriador)
            btn_minha_agenda_vist = self._create_sidebar_button("📅 Minha Agenda", page_idx_counter)
            sidebar_layout.addWidget(btn_minha_agenda_vist)
            self.sidebar_buttons[page_idx_counter] = {'button': btn_minha_agenda_vist, 'widget_name': 'vistoriador_agenda_page'}
            page_idx_counter += 1

        sidebar_layout.addStretch() # Empurra os botões para cima, se houver espaço

        # Exemplo: Botão de Logout (pode ser adicionado aqui ou em outro lugar)
        # btn_logout = QPushButton("🚪 Sair")
        # btn_logout.setStyleSheet(styles.SIDEBAR_BUTTON_STYLE_DANGER) # Um estilo diferente para logout
        # btn_logout.clicked.connect(self.logout)
        # sidebar_layout.addWidget(btn_logout)

    def _create_sidebar_button(self, text: str, page_index: int) -> QPushButton:
        """
        Helper para criar um botão da sidebar padronizado.

        Args:
            text (str): Texto do botão (com emoji, se desejado).
            page_index (int): Índice da página no QStackedWidget que este botão ativará.

        Returns:
            QPushButton: O botão configurado.
        """
        button = QPushButton(text)
        button.setStyleSheet(styles.SIDEBAR_BUTTON_STYLE) # Estilo padrão para botões da sidebar
        button.setCheckable(True) # Permite que o botão fique "pressionado" (estado de selecionado)
        button.setFixedHeight(45) # Altura fixa para os botões
        # Conecta o clique do botão para chamar self.switch_page com o índice correspondente.
        # Usa lambda para passar o page_index corretamente.
        button.clicked.connect(lambda checked, idx=page_index: self.switch_page(idx))
        return button

    def _create_pages(self) -> None:
        """
        Cria as instâncias dos widgets das páginas e as adiciona ao QStackedWidget.

        A ordem de adição ao `pages_stack` deve corresponder aos `page_index`
        usados na criação dos botões da sidebar.
        """
        if self.user_type == 'adm':
            # Página de Agenda Geral (para admin)
            self.agenda_view_adm = AgendaViewWidget(self.user_id, self.user_type, self)
            self.pages_stack.addWidget(self.agenda_view_adm) # Índice 0 (se for o primeiro)

            # Página do Painel de Administração
            self.admin_panel_view = AdminViewWidget(self.user_id, self.user_type, self)
            self.pages_stack.addWidget(self.admin_panel_view) # Índice 1

            # Página de Gerenciar Vistoriadores
            self.gerenciar_vist_view = GerenciarVistoriadorViewWidget(self.user_id, self.user_type, self)
            self.pages_stack.addWidget(self.gerenciar_vist_view) # Índice 2

        elif self.user_type == 'vistoriador':
            # Página da Agenda do Vistoriador
            self.vistoriador_agenda_page = VistoriadorAgendaViewWidget(self.user_id, self.user_type, self)
            self.pages_stack.addWidget(self.vistoriador_agenda_page) # Índice 0 (se for o primeiro para vistoriador)

    def switch_page(self, index: int) -> None:
        """
        Muda a página visível no QStackedWidget e atualiza o estado dos botões da sidebar.

        Também chama métodos de atualização específicos da página, se existirem
        (ex: `atualizar_dados_view` para `GerenciarVistoriadorViewWidget`).

        Args:
            index (int): O índice da página a ser exibida.
        """
        if 0 <= index < self.pages_stack.count(): # Verifica se o índice é válido
            self.pages_stack.setCurrentIndex(index) # Define a página atual no QStackedWidget
            current_widget = self.pages_stack.widget(index) # Obtém o widget da página atual

            # Atualiza o estado visual (checked/unchecked) dos botões da sidebar
            for i, data in self.sidebar_buttons.items():
                data['button'].setChecked(i == index) # Marca como 'checked' apenas o botão da página atual

            # Lógica para chamar métodos de atualização específicos da página que está sendo exibida.
            # Isso é útil para carregar ou recarregar dados quando a página se torna visível.
            if isinstance(current_widget, GerenciarVistoriadorViewWidget):
                print(f"DEBUG: Trocando para GerenciarVistoriadorViewWidget, chamando atualizar_dados_view.")
                current_widget.atualizar_dados_view() # Chama método específico desta view
            elif isinstance(current_widget, AdminViewWidget):
                # Exemplo: se AdminViewWidget também precisasse de atualização ao ser exibida
                # current_widget.algum_metodo_de_atualizacao_admin()
                pass # Nenhuma ação de atualização específica no momento para AdminViewWidget
            elif isinstance(current_widget, AgendaViewWidget):
                # Exemplo: se AgendaViewWidget precisasse de atualização
                # current_widget.algum_metodo_de_atualizacao_agenda()
                pass # Nenhuma ação de atualização específica no momento para AgendaViewWidget
            elif isinstance(current_widget, VistoriadorAgendaViewWidget):
                # A VistoriadorAgendaViewWidget já carrega dados no __init__ e tem um botão de refresh próprio.
                # Se fosse necessário recarregar ao se tornar visível, a lógica iria aqui.
                # current_widget._carregar_dados_iniciais() # Exemplo
                pass

        else: # Índice inválido
            print(f"WARN: Índice de página inválido: {index}")
            if self.pages_stack.count() > 0: # Se houver alguma página
                 self.pages_stack.setCurrentIndex(0) # Volta para a primeira página como fallback
                 # Atualiza os botões da sidebar para refletir a primeira página
                 if 0 in self.sidebar_buttons:
                     for i, data in self.sidebar_buttons.items():
                         data['button'].setChecked(i == 0)
                 # Chama a atualização para a primeira página também, se necessário
                 first_widget = self.pages_stack.widget(0)
                 if isinstance(first_widget, GerenciarVistoriadorViewWidget): # Exemplo
                     first_widget.atualizar_dados_view()


    def logout(self) -> None:
        """
        Placeholder para a funcionalidade de logout.
        Em uma aplicação completa, isso fecharia a MainAppView e reabriria a LoginView.
        """
        print("Logout solicitado. Fechando a aplicação por enquanto.")
        # Exemplo de como poderia ser:
        # Se MainAppView foi aberta por um 'ApplicationController' ou 'App' principal:
        # self.parent().mostrar_login_view() # Sinalizaria ao pai para mostrar o login
        self.close() # Por enquanto, apenas fecha a janela principal

# Bloco para testar esta view isoladamente
if __name__ == '__main__':
    # Adiciona o diretório raiz ao sys.path para encontrar os módulos
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from PyQt5.QtWidgets import QApplication
    # Importações para setup do banco e dados de teste
    from models.database import criar_tabelas
    from models import usuario_model, imobiliaria_model, agenda_model

    criar_tabelas() # Garante que o banco e tabelas existam

    # --- Criação de dados de TESTE ---
    # (Similar ao que foi feito em outros arquivos de view para teste)
    id_vist_teste_main = None
    vists = usuario_model.listar_usuarios_por_tipo('vistoriador')
    if vists:
        id_vist_teste_main = vists[0]['id']
    else:
        id_vist_teste_main = usuario_model.cadastrar_usuario("Vist. Teste MainApp", "vist.mainapp@teste.com", "123456", "vistoriador")

    if id_vist_teste_main:
        if not agenda_model.listar_horarios_fixos_por_vistoriador(id_vist_teste_main):
            agenda_model.cadastrar_horarios_fixos_vistoriador(id_vist_teste_main, ['1','2','3','4','5'], ['09:00', '10:00', '14:00', '15:00', '16:00'])
        agenda_model.gerar_agenda_baseada_em_horarios_fixos()

    if not usuario_model.listar_todos_clientes():
        usuario_model.cadastrar_cliente("Cliente Padrão MainApp", "cliente.mainapp@teste.com")
    if not imobiliaria_model.listar_todas_imobiliarias():
        imobiliaria_model.cadastrar_imobiliaria("Imob Padrão MainApp", 10,12,15)

    app = QApplication(sys.argv)

    print("Testando MainAppView para Administrador...")
    # Simula um login de administrador (user_id=1 é placeholder, tipo 'adm')
    main_win_admin = MainAppView(user_id=1, user_type='adm')
    main_win_admin.show()

    # Você pode descomentar abaixo para testar como vistoriador também:
    # print("\nTestando MainAppView para Vistoriador...")
    # id_para_teste_vistoriador = id_vist_teste_main if id_vist_teste_main else 2 # Usa o ID criado ou um fallback
    # main_win_vistoriador = MainAppView(user_id=id_para_teste_vistoriador, user_type='vistoriador')
    # main_win_vistoriador.show()

    sys.exit(app.exec_())
