# engentoria/views/admin_view_widget.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QFormLayout, QMessageBox, QStackedWidget, QScrollArea, QFrame,
    QListWidget, QListWidgetItem, QComboBox, QDialog, QTextEdit,
    QMainWindow
)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt, QSize
from typing import Optional, List, Dict, Any

from controllers.admin_controller import AdminController
from utils import styles, validators, helpers

class AdminViewWidget(QWidget):
    """
    Widget para a página do Painel de Administração.

    Esta classe é responsável por exibir as opções administrativas,
    como adicionar clientes, imobiliárias, vistoriadores, remover
    entidades e gerar relatórios. Utiliza uma área de conteúdo dinâmica
    para mostrar diferentes formulários e listas de acordo com a ação selecionada.
    """
    def __init__(self, user_id: int, user_type: str, parent: Optional[QWidget] = None):
        """
        Construtor da AdminViewWidget.

        Args:
            user_id (int): ID do usuário logado (administrador).
            user_type (str): Tipo do usuário logado (deve ser 'adm').
            parent (Optional[QWidget]): Widget pai, se houver.
        """
        super().__init__(parent)
        self.user_id = user_id  # ID do usuário administrador
        self.user_type = user_type  # Tipo do usuário (espera-se 'adm')
        self.admin_controller = AdminController()  # Controller para interações com a lógica de administração
        self.current_form_widget: Optional[QWidget] = None  # Referência ao widget de formulário/conteúdo atualmente exibido na área dinâmica

        # Atributos para os QComboBoxes da seção de relatórios.
        # São inicializados como None e instanciados quando a seção de relatórios é exibida.
        # Manter referências a eles é importante para poder atualizá-los dinamicamente
        # (ex: após adicionar um novo vistoriador ou imobiliária).
        self.combo_vistoriador_rel: Optional[QComboBox] = None
        self.combo_imobiliaria_rel: Optional[QComboBox] = None
        self.combo_imobiliaria_devedores_rel: Optional[QComboBox] = None
        # Referência ao QScrollArea que contém os formulários de relatório.
        # Usado para identificar se a seção de relatórios está ativa e para limpar corretamente.
        self.reports_scroll_area: Optional[QScrollArea] = None

        self._init_ui()

    def _init_ui(self) -> None:
        """
        Inicializa a interface do usuário do painel de administração.

        Configura o layout principal, o título, o painel de botões de ação
        à esquerda e a área de conteúdo dinâmico à direita.
        """
        self.main_layout = QVBoxLayout(self)  # Layout principal vertical
        self.main_layout.setContentsMargins(20, 20, 20, 20) # Margens externas
        self.main_layout.setSpacing(20) # Espaçamento entre título e conteúdo principal
        self.main_layout.setAlignment(Qt.AlignTop) # Alinha conteúdo ao topo

        title_label = QLabel("Painel de Administração")
        title_label.setStyleSheet(styles.PAGE_TITLE_STYLE)
        title_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title_label)

        # Layout horizontal para dividir em painel de botões (esquerda) e área dinâmica (direita)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20) # Espaçamento entre o painel de botões e a área dinâmica

        # --- Painel da Esquerda: Botões de Ação ---
        action_buttons_panel = QWidget()
        action_buttons_panel.setFixedWidth(250) # Largura fixa para o painel de botões
        action_buttons_layout = QVBoxLayout(action_buttons_panel)
        action_buttons_layout.setContentsMargins(0,0,0,0) # Sem margens internas no painel de botões
        action_buttons_layout.setSpacing(10) # Espaçamento entre os botões
        action_buttons_layout.setAlignment(Qt.AlignTop) # Alinha botões ao topo

        # Botão para adicionar cliente
        self.btn_add_cliente = QPushButton("➕ Adicionar Cliente")
        self.btn_add_cliente.setStyleSheet(styles.SECONDARY_BUTTON_STYLE)
        self.btn_add_cliente.clicked.connect(self._mostrar_form_add_cliente)
        action_buttons_layout.addWidget(self.btn_add_cliente)

        # Botão para adicionar imobiliária
        self.btn_add_imobiliaria = QPushButton("🏠 Adicionar Imobiliária")
        self.btn_add_imobiliaria.setStyleSheet(styles.SECONDARY_BUTTON_STYLE)
        self.btn_add_imobiliaria.clicked.connect(self._mostrar_form_add_imobiliaria)
        action_buttons_layout.addWidget(self.btn_add_imobiliaria)

        # Botão para adicionar vistoriador
        self.btn_add_vistoriador = QPushButton("👨‍🔧 Adicionar Vistoriador")
        self.btn_add_vistoriador.setStyleSheet(styles.SECONDARY_BUTTON_STYLE)
        self.btn_add_vistoriador.clicked.connect(self._mostrar_form_add_vistoriador)
        action_buttons_layout.addWidget(self.btn_add_vistoriador)

        action_buttons_layout.addWidget(self._criar_separador()) # Separador visual

        # Botão para remover vistoriador
        self.btn_rem_vistoriador = QPushButton("🚫 Remover Vistoriador")
        self.btn_rem_vistoriador.setStyleSheet(styles.SECONDARY_BUTTON_STYLE) # Poderia ser DANGER_BUTTON_STYLE se a ação fosse imediata
        self.btn_rem_vistoriador.clicked.connect(self._mostrar_form_remover_vistoriador)
        action_buttons_layout.addWidget(self.btn_rem_vistoriador)

        # Botão para remover imobiliária
        self.btn_rem_imobiliaria = QPushButton("🗑️ Remover Imobiliária")
        self.btn_rem_imobiliaria.setStyleSheet(styles.SECONDARY_BUTTON_STYLE)
        self.btn_rem_imobiliaria.clicked.connect(self._mostrar_form_remover_imobiliaria)
        action_buttons_layout.addWidget(self.btn_rem_imobiliaria)

        action_buttons_layout.addWidget(self._criar_separador()) # Outro separador

        # Botão para seção de relatórios
        self.btn_relatorios = QPushButton("📊 Relatórios")
        self.btn_relatorios.setStyleSheet(styles.SECONDARY_BUTTON_STYLE)
        self.btn_relatorios.clicked.connect(self._mostrar_opcoes_relatorios)
        action_buttons_layout.addWidget(self.btn_relatorios)

        action_buttons_layout.addStretch() # Empurra os botões para cima, preenchendo o espaço restante abaixo

        # --- Área da Direita: Conteúdo Dinâmico ---
        # Esta área exibirá diferentes formulários ou listas dependendo da ação selecionada.
        self.dynamic_content_area = QWidget()
        self.dynamic_content_layout = QVBoxLayout(self.dynamic_content_area) # Layout para a área dinâmica
        self.dynamic_content_layout.setContentsMargins(0,0,0,0)

        # Label inicial exibida na área dinâmica antes de qualquer ação ser selecionada
        initial_label = QLabel("Selecione uma ação no painel à esquerda.")
        initial_label.setAlignment(Qt.AlignCenter)
        initial_label.setFont(QFont(styles.FONT_FAMILY_PRIMARY, 16))
        initial_label.setStyleSheet(f"color: {styles.COLOR_TEXT_SECONDARY};")
        self.dynamic_content_layout.addWidget(initial_label)

        # Adiciona o painel de botões e a área dinâmica ao layout de conteúdo horizontal
        content_layout.addWidget(action_buttons_panel)
        content_layout.addWidget(self.dynamic_content_area, 1) # O '1' faz a área dinâmica expandir para ocupar o espaço restante
        self.main_layout.addLayout(content_layout) # Adiciona o layout de conteúdo ao layout principal

    def _criar_separador(self) -> QFrame:
        """
        Cria um widget QFrame estilizado para ser usado como separador horizontal
        entre grupos de botões na sidebar.

        Returns:
            QFrame: O widget separador configurado.
        """
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine) # Define como linha horizontal
        separator.setFrameShadow(QFrame.Sunken) # Efeito de sombra
        separator.setStyleSheet(f"border-color: {styles.COLOR_BORDER_MEDIUM};") # Cor da borda
        return separator

    def _clear_dynamic_content_area(self) -> None:
        """
        Limpa todos os widgets da área de conteúdo dinâmico (`dynamic_content_layout`).

        Se o widget atualmente exibido for a seção de relatórios (identificada por `self.reports_scroll_area`),
        também invalida (define como None) as referências aos QComboBoxes de filtro de relatório.
        Isso é crucial porque esses combos são filhos do widget que será deletado.
        Manter referências a widgets deletados pode causar crashes ou comportamento inesperado.
        Ao invalidar, garantimos que, se a seção de relatórios for recriada, os combos também serão,
        evitando o uso de referências "dangling".
        """
        if self.current_form_widget:
            # Verifica especificamente se o widget atual é o QScrollArea da seção de relatórios.
            if self.reports_scroll_area and self.current_form_widget == self.reports_scroll_area:
                # Se for, os combos de relatório (combo_vistoriador_rel, etc.) são filhos
                # deste reports_scroll_area (ou de um widget dentro dele).
                # Portanto, ao deletar reports_scroll_area, os combos também serão deletados.
                # É importante anular nossas referências a eles para evitar usar ponteiros inválidos.
                self.combo_vistoriador_rel = None
                self.combo_imobiliaria_rel = None
                self.combo_imobiliaria_devedores_rel = None
                self.reports_scroll_area = None # Também anula a referência ao próprio scroll area
            
            self.current_form_widget.deleteLater() # Agenda o widget atual para deleção segura
            self.current_form_widget = None # Remove a referência ao widget deletado

        # Loop para remover quaisquer outros widgets que possam ter sido adicionados diretamente
        # ao dynamic_content_layout (ex: o label inicial).
        while self.dynamic_content_layout.count():
            child = self.dynamic_content_layout.takeAt(0) # Pega o primeiro item do layout
            if child.widget():
                child.widget().deleteLater() # Se for um widget, agenda para deleção

    def _mostrar_form_add_cliente(self) -> None:
        """
        Limpa a área dinâmica e exibe o formulário para adicionar um novo cliente.
        """
        self._clear_dynamic_content_area() # Limpa conteúdo anterior
        form_widget = QWidget() # Widget container para o formulário
        layout = QFormLayout(form_widget) # Layout de formulário (Label: Input)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10) # Margens internas do formulário

        # Título do formulário
        lbl_title_container = QWidget() # Container para centralizar o título
        lbl_title_layout = QHBoxLayout(lbl_title_container)
        lbl_title = QLabel("Adicionar Novo Cliente")
        lbl_title.setStyleSheet(styles.SUBTITLE_LABEL_STYLE)
        lbl_title_layout.addStretch()
        lbl_title_layout.addWidget(lbl_title)
        lbl_title_layout.addStretch()
        self.dynamic_content_layout.addWidget(lbl_title_container) # Adiciona título à área dinâmica

        # Campos do formulário
        nome_input = QLineEdit()
        nome_input.setPlaceholderText("Nome completo do cliente")
        layout.addRow("Nome:", nome_input)
        email_input = QLineEdit()
        email_input.setPlaceholderText("email@exemplo.com")
        layout.addRow("E-mail:", email_input)
        tel1_input = QLineEdit()
        tel1_input.setPlaceholderText("(XX) XXXXX-XXXX (Opcional)")
        layout.addRow("Telefone 1:", tel1_input)
        tel2_input = QLineEdit()
        tel2_input.setPlaceholderText("(XX) XXXXX-XXXX (Opcional)")
        layout.addRow("Telefone 2:", tel2_input)

        # Botão Salvar
        btn_salvar = QPushButton("Salvar Cliente")
        btn_salvar.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        # Conecta o clique ao método de salvar, passando os valores dos inputs via lambda
        btn_salvar.clicked.connect(lambda: self._salvar_novo_cliente(
            nome_input.text(), email_input.text(), tel1_input.text(), tel2_input.text()
        ))
        layout.addRow(btn_salvar) # Adiciona botão ao formulário

        self.current_form_widget = form_widget # Mantém referência ao formulário atual
        self.dynamic_content_layout.addWidget(form_widget) # Adiciona formulário à área dinâmica

    def _salvar_novo_cliente(self, nome: str, email: str, tel1: str, tel2: str) -> None:
        """
        Chama o controller para salvar um novo cliente e exibe o resultado.

        Args:
            nome (str): Nome do cliente.
            email (str): E-mail do cliente.
            tel1 (str): Telefone 1 (opcional).
            tel2 (str): Telefone 2 (opcional).
        """
        resultado = self.admin_controller.cadastrar_novo_cliente(nome, email, tel1, tel2)
        if resultado['success']:
            QMessageBox.information(self, "Sucesso", resultado['message'])
            self._clear_dynamic_content_area() # Limpa o formulário
            # Exibe mensagem de sucesso na área dinâmica
            initial_label = QLabel("Cliente adicionado. Selecione outra ação.")
            initial_label.setAlignment(Qt.AlignCenter)
            self.dynamic_content_layout.addWidget(initial_label)
        else:
            QMessageBox.warning(self, "Erro ao Salvar", resultado['message'])

    def _mostrar_form_add_imobiliaria(self) -> None:
        """
        Limpa a área dinâmica e exibe o formulário para adicionar uma nova imobiliária.
        """
        self._clear_dynamic_content_area()
        form_widget = QWidget()
        layout = QFormLayout(form_widget)
        layout.setSpacing(10)

        lbl_title_container = QWidget()
        lbl_title_layout = QHBoxLayout(lbl_title_container)
        lbl_title = QLabel("Adicionar Nova Imobiliária")
        lbl_title.setStyleSheet(styles.SUBTITLE_LABEL_STYLE)
        lbl_title_layout.addStretch()
        lbl_title_layout.addWidget(lbl_title)
        lbl_title_layout.addStretch()
        self.dynamic_content_layout.addWidget(lbl_title_container)

        nome_input = QLineEdit()
        nome_input.setPlaceholderText("Nome da Imobiliária")
        layout.addRow("Nome:", nome_input)
        val_sm_input = QLineEdit()
        val_sm_input.setPlaceholderText("Ex: 10.50 (Use ponto para decimal)")
        layout.addRow("Valor m² (Sem Mobília):", val_sm_input)
        val_smm_input = QLineEdit()
        val_smm_input.setPlaceholderText("Ex: 12.75 (Use ponto para decimal)")
        layout.addRow("Valor m² (Semi-Mobiliado):", val_smm_input)
        val_m_input = QLineEdit()
        val_m_input.setPlaceholderText("Ex: 15.00 (Use ponto para decimal)")
        layout.addRow("Valor m² (Mobiliado):", val_m_input)

        btn_salvar = QPushButton("Salvar Imobiliária")
        btn_salvar.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        btn_salvar.clicked.connect(lambda: self._salvar_nova_imobiliaria(
            nome_input.text(), val_sm_input.text(), val_smm_input.text(), val_m_input.text()
        ))
        layout.addRow(btn_salvar)

        self.current_form_widget = form_widget
        self.dynamic_content_layout.addWidget(form_widget)

    def _salvar_nova_imobiliaria(self, nome: str, val_sm_str: str, val_smm_str: str, val_m_str: str) -> None:
        """
        Chama o controller para salvar uma nova imobiliária e exibe o resultado.

        Args:
            nome (str): Nome da imobiliária.
            val_sm_str (str): Valor por m² para imóveis sem mobília (como string).
            val_smm_str (str): Valor por m² para imóveis semi-mobiliados (como string).
            val_m_str (str): Valor por m² para imóveis mobiliados (como string).
        """
        resultado = self.admin_controller.cadastrar_nova_imobiliaria(nome, val_sm_str, val_smm_str, val_m_str)
        if resultado['success']:
            QMessageBox.information(self, "Sucesso", resultado['message'])
            self._clear_dynamic_content_area()
            initial_label = QLabel("Imobiliária adicionada. Selecione outra ação.")
            initial_label.setAlignment(Qt.AlignCenter)
            self.dynamic_content_layout.addWidget(initial_label)
            self._atualizar_combos_relatorios_se_existirem() # Atualiza combos de relatório, se visíveis
        else:
            QMessageBox.warning(self, "Erro ao Salvar", resultado['message'])

    def _mostrar_form_add_vistoriador(self) -> None:
        """
        Limpa a área dinâmica e exibe o formulário para adicionar um novo vistoriador.
        """
        self._clear_dynamic_content_area()
        form_widget = QWidget()
        layout = QFormLayout(form_widget)
        layout.setSpacing(10)

        lbl_title_container = QWidget()
        lbl_title_layout = QHBoxLayout(lbl_title_container)
        lbl_title = QLabel("Adicionar Novo Vistoriador")
        lbl_title.setStyleSheet(styles.SUBTITLE_LABEL_STYLE)
        lbl_title_layout.addStretch()
        lbl_title_layout.addWidget(lbl_title)
        lbl_title_layout.addStretch()
        self.dynamic_content_layout.addWidget(lbl_title_container)

        nome_input = QLineEdit()
        layout.addRow("Nome:", nome_input)
        email_input = QLineEdit()
        email_input.setPlaceholderText("email@exemplo.com")
        layout.addRow("E-mail:", email_input)
        senha_input = QLineEdit()
        senha_input.setEchoMode(QLineEdit.Password) # Oculta senha
        layout.addRow("Senha:", senha_input)
        confirma_senha_input = QLineEdit()
        confirma_senha_input.setEchoMode(QLineEdit.Password)
        layout.addRow("Confirmar Senha:", confirma_senha_input)
        tel1_input = QLineEdit()
        tel1_input.setPlaceholderText("(Opcional)")
        layout.addRow("Telefone 1:", tel1_input)
        tel2_input = QLineEdit()
        tel2_input.setPlaceholderText("(Opcional)")
        layout.addRow("Telefone 2:", tel2_input)

        btn_salvar = QPushButton("Salvar Vistoriador")
        btn_salvar.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        btn_salvar.clicked.connect(lambda: self._salvar_novo_vistoriador(
            nome_input.text(), email_input.text(), senha_input.text(), confirma_senha_input.text(),
            tel1_input.text(), tel2_input.text()
        ))
        layout.addRow(btn_salvar)

        self.current_form_widget = form_widget
        self.dynamic_content_layout.addWidget(form_widget)

    def _salvar_novo_vistoriador(self, nome: str, email: str, senha: str, confirma_senha: str, tel1: str, tel2: str) -> None:
        """
        Chama o controller para salvar um novo vistoriador e exibe o resultado.

        Args:
            nome (str): Nome do vistoriador.
            email (str): E-mail do vistoriador.
            senha (str): Senha para o vistoriador.
            confirma_senha (str): Confirmação da senha.
            tel1 (str): Telefone 1 (opcional).
            tel2 (str): Telefone 2 (opcional).
        """
        resultado = self.admin_controller.cadastrar_novo_vistoriador(
            nome, email, senha, confirma_senha, tel1, tel2
        )
        if resultado['success']:
            QMessageBox.information(self, "Sucesso", resultado['message'])
            self._clear_dynamic_content_area()
            initial_label = QLabel("Vistoriador adicionado. Selecione outra ação.")
            initial_label.setAlignment(Qt.AlignCenter)
            self.dynamic_content_layout.addWidget(initial_label)
            self._atualizar_combos_relatorios_se_existirem() # Atualiza combos de relatório
        else:
            QMessageBox.warning(self, "Erro ao Salvar", resultado['message'])

    def _mostrar_form_remover_vistoriador(self) -> None:
        """
        Limpa a área dinâmica e exibe a lista de vistoriadores para remoção.
        """
        self._clear_dynamic_content_area()
        widget_remover = QWidget() # Container principal
        layout_remover = QVBoxLayout(widget_remover) # Layout vertical

        lbl_title_container = QWidget()
        lbl_title_layout = QHBoxLayout(lbl_title_container)
        lbl_title = QLabel("Remover Vistoriador")
        lbl_title.setStyleSheet(styles.SUBTITLE_LABEL_STYLE)
        lbl_title_layout.addStretch()
        lbl_title_layout.addWidget(lbl_title)
        lbl_title_layout.addStretch()
        # Adiciona o título diretamente ao dynamic_content_layout para ficar acima da lista
        self.dynamic_content_layout.addWidget(lbl_title_container)

        # Lista para exibir vistoriadores
        self.lista_vistoriadores_remover = QListWidget()
        self.lista_vistoriadores_remover.setStyleSheet(styles.LIST_WIDGET_ITEM_SELECTED_RED) # Estilo para item selecionado
        self._recarregar_lista_remover_vistoriador() # Popula a lista
        layout_remover.addWidget(self.lista_vistoriadores_remover)

        # Botão para confirmar remoção
        btn_remover = QPushButton("Remover Selecionado")
        btn_remover.setStyleSheet(styles.DANGER_BUTTON_STYLE) # Estilo de perigo
        btn_remover.clicked.connect(self._confirmar_remocao_vistoriador)
        layout_remover.addWidget(btn_remover)

        self.current_form_widget = widget_remover
        self.dynamic_content_layout.addWidget(widget_remover) # Adiciona o widget da lista/botão à área dinâmica

    def _recarregar_lista_remover_vistoriador(self) -> None:
        """
        Recarrega a lista de vistoriadores exibida no formulário de remoção.
        """
        self.lista_vistoriadores_remover.clear() # Limpa itens antigos
        vistoriadores = self.admin_controller.listar_todos_vistoriadores() # Busca do controller
        if vistoriadores:
            for vist in vistoriadores:
                item_text = f"{vist['nome']} (ID: {vist['id']})"
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.UserRole, vist['id']) # Armazena o ID do vistoriador no item
                self.lista_vistoriadores_remover.addItem(list_item)
        else:
            self.lista_vistoriadores_remover.addItem("Nenhum vistoriador cadastrado.")


    def _confirmar_remocao_vistoriador(self) -> None:
        """
        Pede confirmação e, se confirmado, chama o controller para remover o vistoriador selecionado.
        """
        item_selecionado = self.lista_vistoriadores_remover.currentItem()
        if not item_selecionado or item_selecionado.data(Qt.UserRole) is None: # Verifica se um item válido foi selecionado
            QMessageBox.warning(self, "Seleção Necessária", "Por favor, selecione um vistoriador para remover.")
            return

        vistoriador_id = item_selecionado.data(Qt.UserRole) # ID do vistoriador a ser removido
        vistoriador_texto = item_selecionado.text() # Texto do item para a mensagem de confirmação

        # Diálogo de confirmação
        confirm = QMessageBox.question(self, "Confirmar Remoção",
                                       f"Tem certeza que deseja remover o vistoriador:\n{vistoriador_texto}?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            resultado = self.admin_controller.remover_vistoriador(vistoriador_id)
            if resultado['success']:
                QMessageBox.information(self, "Sucesso", resultado['message'])
                self._recarregar_lista_remover_vistoriador() # Atualiza a lista após remoção
                self._atualizar_combos_relatorios_se_existirem() # Atualiza combos de relatório
            else:
                QMessageBox.warning(self, "Erro", resultado['message'])


    def _mostrar_form_remover_imobiliaria(self) -> None:
        """
        Limpa a área dinâmica e exibe a lista de imobiliárias para remoção.
        """
        self._clear_dynamic_content_area()
        widget_remover = QWidget()
        layout_remover = QVBoxLayout(widget_remover)

        lbl_title_container = QWidget()
        lbl_title_layout = QHBoxLayout(lbl_title_container)
        lbl_title = QLabel("Remover Imobiliária")
        lbl_title.setStyleSheet(styles.SUBTITLE_LABEL_STYLE)
        lbl_title_layout.addStretch()
        lbl_title_layout.addWidget(lbl_title)
        lbl_title_layout.addStretch()
        self.dynamic_content_layout.addWidget(lbl_title_container)

        self.lista_imobiliarias_remover = QListWidget()
        self.lista_imobiliarias_remover.setStyleSheet(styles.LIST_WIDGET_ITEM_SELECTED_RED)
        self._recarregar_lista_remover_imobiliaria()
        layout_remover.addWidget(self.lista_imobiliarias_remover)

        btn_remover = QPushButton("Remover Selecionada")
        btn_remover.setStyleSheet(styles.DANGER_BUTTON_STYLE)
        btn_remover.clicked.connect(self._confirmar_remocao_imobiliaria)
        layout_remover.addWidget(btn_remover)

        self.current_form_widget = widget_remover
        self.dynamic_content_layout.addWidget(widget_remover)

    def _recarregar_lista_remover_imobiliaria(self) -> None:
        """
        Recarrega a lista de imobiliárias exibida no formulário de remoção.
        """
        self.lista_imobiliarias_remover.clear()
        imobiliarias = self.admin_controller.listar_todas_imobiliarias_admin() # Método específico para admin
        if imobiliarias:
            for imob in imobiliarias:
                item_text = f"{imob['nome']} (ID: {imob['id']})"
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.UserRole, imob['id'])
                self.lista_imobiliarias_remover.addItem(list_item)
        else:
            self.lista_imobiliarias_remover.addItem("Nenhuma imobiliária cadastrada.")

    def _confirmar_remocao_imobiliaria(self) -> None:
        """
        Pede confirmação e, se confirmado, chama o controller para remover a imobiliária selecionada.
        """
        item_selecionado = self.lista_imobiliarias_remover.currentItem()
        if not item_selecionado or item_selecionado.data(Qt.UserRole) is None:
            QMessageBox.warning(self, "Seleção Necessária", "Por favor, selecione uma imobiliária para remover.")
            return

        imobiliaria_id = item_selecionado.data(Qt.UserRole)
        imobiliaria_texto = item_selecionado.text()

        confirm = QMessageBox.question(self, "Confirmar Remoção",
                                       f"Tem certeza que deseja remover a imobiliária:\n{imobiliaria_texto}?\nIsso pode falhar se houver imóveis ou agendamentos associados.",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            resultado = self.admin_controller.remover_imobiliaria(imobiliaria_id)
            if resultado['success']:
                QMessageBox.information(self, "Sucesso", resultado['message'])
                self._recarregar_lista_remover_imobiliaria()
                self._atualizar_combos_relatorios_se_existirem()
            else:
                QMessageBox.warning(self, "Erro", resultado['message'])

    def _atualizar_combos_relatorios_se_existirem(self) -> None:
        """
        Atualiza o conteúdo dos QComboBoxes na seção de relatórios, se eles já foram criados e são válidos.

        Esta função é chamada após adicionar ou remover vistoriadores/imobiliárias,
        para que os filtros de relatório reflitam os dados mais recentes.
        Tenta preservar a seleção atual dos combos, se possível.
        """
        # Verifica se os combos de relatório existem (não são None).
        # Isso indica que a seção de relatórios já foi exibida pelo menos uma vez.
        if self.combo_vistoriador_rel is not None and \
           self.combo_imobiliaria_rel is not None and \
           self.combo_imobiliaria_devedores_rel is not None:

            print("DEBUG: AdminViewWidget._atualizar_combos_relatorios_se_existirem() chamado - combos existem.")

            # Salva os IDs dos itens atualmente selecionados nos combos para tentar restaurá-los.
            current_vist_id = self.combo_vistoriador_rel.currentData()
            current_imob_id_vist_rel = self.combo_imobiliaria_rel.currentData() # Para filtro de vistorias
            current_imob_id_dev_rel = self.combo_imobiliaria_devedores_rel.currentData() # Para filtro de devedores

            # Bloqueia sinais para evitar que `currentIndexChanged` seja emitido durante a limpeza/repopulação.
            self.combo_vistoriador_rel.blockSignals(True)
            self.combo_imobiliaria_rel.blockSignals(True)
            self.combo_imobiliaria_devedores_rel.blockSignals(True)

            # Limpa e repopula o combo de vistoriadores
            self.combo_vistoriador_rel.clear()
            self.combo_vistoriador_rel.addItem("Geral (Todos Vistoriadores)", None) # Opção "Todos"
            for vist in self.admin_controller.listar_todos_vistoriadores():
                self.combo_vistoriador_rel.addItem(vist['nome'], vist['id'])

            # Limpa e repopula os combos de imobiliárias
            imobiliarias = self.admin_controller.listar_todas_imobiliarias_admin()
            self.combo_imobiliaria_rel.clear()
            self.combo_imobiliaria_rel.addItem("Geral (Todas Imobiliárias)", None)
            self.combo_imobiliaria_devedores_rel.clear()
            self.combo_imobiliaria_devedores_rel.addItem("Todas as Imobiliárias", None)
            for imob in imobiliarias:
                self.combo_imobiliaria_rel.addItem(imob['nome'], imob['id'])
                self.combo_imobiliaria_devedores_rel.addItem(imob['nome'], imob['id'])

            # Tenta restaurar a seleção anterior para cada combo
            idx_vist = self.combo_vistoriador_rel.findData(current_vist_id)
            self.combo_vistoriador_rel.setCurrentIndex(idx_vist if idx_vist != -1 else 0) # Se não encontrar, seleciona "Todos"

            idx_imob_vist = self.combo_imobiliaria_rel.findData(current_imob_id_vist_rel)
            self.combo_imobiliaria_rel.setCurrentIndex(idx_imob_vist if idx_imob_vist != -1 else 0)

            idx_imob_dev = self.combo_imobiliaria_devedores_rel.findData(current_imob_id_dev_rel)
            self.combo_imobiliaria_devedores_rel.setCurrentIndex(idx_imob_dev if idx_imob_dev != -1 else 0)

            # Reabilita os sinais
            self.combo_vistoriador_rel.blockSignals(False)
            self.combo_imobiliaria_rel.blockSignals(False)
            self.combo_imobiliaria_devedores_rel.blockSignals(False)
        else:
            # Se os combos não existem (ex: seção de relatórios nunca foi aberta), não faz nada.
            print("DEBUG: Combos de relatório não existem ou foram invalidados, atualização de combos de relatório ignorada.")


    def _mostrar_opcoes_relatorios(self) -> None:
        """
        Limpa a área dinâmica e exibe as opções para geração de relatórios.
        Usa um QScrollArea para acomodar múltiplos grupos de relatório.
        Os QComboBoxes de filtro são instanciados aqui e suas referências
        são armazenadas em `self.combo_..._rel`.
        """
        self._clear_dynamic_content_area() # Limpa conteúdo anterior

        # Cria o QScrollArea que será o container principal para os relatórios.
        # Isso permite que a seção de relatórios seja rolável se o conteúdo for extenso.
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True) # Permite que o widget interno redimensione com o scroll area
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }") # Estilo do scroll area

        # Widget que irá DENTRO do QScrollArea e conterá o layout dos grupos de relatório.
        content_widget_relatorios = QWidget()
        layout_relatorios = QVBoxLayout(content_widget_relatorios) # Layout vertical para os grupos de relatório
        layout_relatorios.setSpacing(15) # Espaçamento entre os grupos de relatório
        layout_relatorios.setContentsMargins(10,0,10,10) # Margens (sem margem superior, pois o título está fora)

        # Título da seção de relatórios (adicionado diretamente à área dinâmica, acima do scroll area)
        lbl_title_container = QWidget()
        lbl_title_layout = QHBoxLayout(lbl_title_container)
        lbl_title = QLabel("Gerar Relatórios")
        lbl_title.setStyleSheet(styles.SUBTITLE_LABEL_STYLE)
        lbl_title_layout.addStretch()
        lbl_title_layout.addWidget(lbl_title)
        lbl_title_layout.addStretch()
        self.dynamic_content_layout.addWidget(lbl_title_container)

        # --- Grupo: Relatório de Vistorias ---
        group_vistorias = QFrame() # QFrame para agrupar visualmente
        group_vistorias.setFrameShape(QFrame.StyledPanel)
        group_vistorias.setStyleSheet(f"QFrame {{ border: 1px solid {styles.COLOR_BORDER_DARK}; border-radius: 5px; padding: 10px; background-color: {styles.COLOR_BACKGROUND_MEDIUM}; }}")
        layout_group_vistorias = QVBoxLayout(group_vistorias) # Layout interno do grupo

        lbl_vistorias_title = QLabel("Relatório de Vistorias")
        lbl_vistorias_title.setStyleSheet(styles.INFO_TEXT_STYLE + "font-weight: bold; font-size: 15px;")
        layout_group_vistorias.addWidget(lbl_vistorias_title)

        form_vistorias = QFormLayout() # Formulário para filtros do relatório de vistorias
        form_vistorias.setSpacing(10)

        self.combo_tipo_vistoria_rel = QComboBox() # Combo para tipo de vistoria (ENTRADA/SAIDA)
        self.combo_tipo_vistoria_rel.addItems(["ENTRADA", "SAIDA"])
        form_vistorias.addRow("Tipo de Vistoria:", self.combo_tipo_vistoria_rel)

        self.data_inicio_rel = QLineEdit() # Input para data de início
        self.data_inicio_rel.setPlaceholderText("DD/MM/AAAA")
        form_vistorias.addRow("Data Início:", self.data_inicio_rel)

        self.data_fim_rel = QLineEdit() # Input para data de fim
        self.data_fim_rel.setPlaceholderText("DD/MM/AAAA")
        form_vistorias.addRow("Data Fim:", self.data_fim_rel)

        # Combo para filtrar por vistoriador - INSTANCIADO AQUI
        self.combo_vistoriador_rel = QComboBox()
        form_vistorias.addRow("Filtrar por Vistoriador:", self.combo_vistoriador_rel)

        # Combo para filtrar por imobiliária - INSTANCIADO AQUI
        self.combo_imobiliaria_rel = QComboBox()
        form_vistorias.addRow("Filtrar por Imobiliária:", self.combo_imobiliaria_rel)

        layout_group_vistorias.addLayout(form_vistorias) # Adiciona formulário ao grupo

        btn_gerar_rel_vistorias = QPushButton("Gerar Relatório de Vistorias")
        btn_gerar_rel_vistorias.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        btn_gerar_rel_vistorias.clicked.connect(self._executar_geracao_relatorio_vistorias)
        layout_group_vistorias.addWidget(btn_gerar_rel_vistorias, alignment=Qt.AlignRight) # Alinha botão à direita
        layout_relatorios.addWidget(group_vistorias) # Adiciona grupo ao layout principal dos relatórios (dentro do scroll)

        # --- Grupo: Relatório de Devedores ---
        group_devedores = QFrame() # Outro QFrame para o relatório de devedores
        group_devedores.setFrameShape(QFrame.StyledPanel)
        group_devedores.setStyleSheet(f"QFrame {{ border: 1px solid {styles.COLOR_BORDER_DARK}; border-radius: 5px; padding: 10px; background-color: {styles.COLOR_BACKGROUND_MEDIUM}; }}")
        layout_group_devedores = QVBoxLayout(group_devedores)

        lbl_devedores_title = QLabel("Relatório de Clientes Devedores")
        lbl_devedores_title.setStyleSheet(styles.INFO_TEXT_STYLE + "font-weight: bold; font-size: 15px;")
        layout_group_devedores.addWidget(lbl_devedores_title)

        form_devedores = QFormLayout() # Formulário para filtros do relatório de devedores
        form_devedores.setSpacing(10)

        self.data_inicio_devedores_rel = QLineEdit() # Data início do cancelamento
        self.data_inicio_devedores_rel.setPlaceholderText("DD/MM/AAAA (Opcional)")
        form_devedores.addRow("Data Início Cancelamento:", self.data_inicio_devedores_rel)

        self.data_fim_devedores_rel = QLineEdit() # Data fim do cancelamento
        self.data_fim_devedores_rel.setPlaceholderText("DD/MM/AAAA (Opcional)")
        form_devedores.addRow("Data Fim Cancelamento:", self.data_fim_devedores_rel)

        # Combo para filtrar devedores por imobiliária - INSTANCIADO AQUI
        self.combo_imobiliaria_devedores_rel = QComboBox()
        form_devedores.addRow("Filtrar Devedores por Imobiliária:", self.combo_imobiliaria_devedores_rel)

        layout_group_devedores.addLayout(form_devedores)

        btn_gerar_rel_devedores = QPushButton("Gerar Relatório de Devedores")
        btn_gerar_rel_devedores.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        btn_gerar_rel_devedores.clicked.connect(self._executar_geracao_relatorio_devedores)
        layout_group_devedores.addWidget(btn_gerar_rel_devedores, alignment=Qt.AlignRight)
        layout_relatorios.addWidget(group_devedores) # Adiciona grupo ao layout principal dos relatórios

        layout_relatorios.addStretch() # Adiciona espaço flexível abaixo dos grupos

        scroll_area.setWidget(content_widget_relatorios) # Define o widget com todos os grupos DENTRO do QScrollArea

        self.reports_scroll_area = scroll_area # Guarda a referência ao QScrollArea (usado em _clear_dynamic_content_area)
        self.current_form_widget = self.reports_scroll_area # Define o scroll_area como o widget atual
        self.dynamic_content_layout.addWidget(self.current_form_widget) # Adiciona o scroll_area à área dinâmica

        # Após criar os combos, chama a função para populá-los e tentar manter seleções anteriores.
        self._atualizar_combos_relatorios_se_existirem()


    def _executar_geracao_relatorio_vistorias(self) -> None:
        """
        Coleta os filtros, chama o controller para gerar o relatório de vistorias e exibe o resultado.
        """
        # Coleta dos valores dos filtros
        tipo_rel = self.combo_tipo_vistoria_rel.currentText().lower() # 'entrada' ou 'saida'
        data_inicio = self.data_inicio_rel.text()
        data_fim = self.data_fim_rel.text()

        # Obtém ID e nome do vistoriador/imobiliária selecionados, ou None se "Todos"
        id_vistoriador = self.combo_vistoriador_rel.currentData()
        nome_vistoriador = self.combo_vistoriador_rel.currentText() if id_vistoriador else None
        if self.combo_vistoriador_rel.currentIndex() == 0: # Se "Todos Vistoriadores" está selecionado
            id_vistoriador = None
            nome_vistoriador = None

        id_imobiliaria = self.combo_imobiliaria_rel.currentData()
        nome_imobiliaria = self.combo_imobiliaria_rel.currentText() if id_imobiliaria else None
        if self.combo_imobiliaria_rel.currentIndex() == 0: # Se "Todas Imobiliárias" está selecionado
            id_imobiliaria = None
            nome_imobiliaria = None

        # Determina se o filtro específico é por vistoriador ou por imobiliária
        # O controller espera um `id_especifico`, `nome_especifico` e `tipo_id_especifico`
        id_especifico = None
        nome_especifico = None
        tipo_id_especifico = None # 'vistoriador' ou 'imobiliaria'

        if id_vistoriador:
            id_especifico = id_vistoriador
            nome_especifico = nome_vistoriador
            tipo_id_especifico = 'vistoriador'
        elif id_imobiliaria: # Prioriza filtro de vistoriador se ambos estiverem (hipoteticamente) preenchidos
            id_especifico = id_imobiliaria
            nome_especifico = nome_imobiliaria
            tipo_id_especifico = 'imobiliaria'

        # Validação das datas
        # O helper formatar_data_para_banco também valida o formato DD/MM/AAAA.
        # Retorna None se o formato for inválido ou a data não existir.
        if not helpers.formatar_data_para_banco(data_inicio) or not helpers.formatar_data_para_banco(data_fim):
            QMessageBox.warning(self, "Datas Inválidas", "Por favor, insira Data Início e Data Fim no formato DD/MM/AAAA.")
            return

        # Chama o controller
        resultado = self.admin_controller.gerar_relatorio_vistorias(
            tipo_relatorio_vistoria=tipo_rel,
            data_inicio=data_inicio, # Passa como DD/MM/AAAA, controller formata para YYYY-MM-DD
            data_fim=data_fim,
            id_especifico=id_especifico,
            nome_especifico=nome_especifico,
            tipo_id_especifico=tipo_id_especifico
        )
        if resultado['success']:
            QMessageBox.information(self, "Relatório Gerado", f"{resultado['message']}\nSalvo em: {resultado.get('path', 'N/D')}")
        else:
            QMessageBox.warning(self, "Erro ao Gerar Relatório", resultado['message'])

    def _executar_geracao_relatorio_devedores(self) -> None:
        """
        Coleta os filtros, chama o controller para gerar o relatório de clientes devedores e exibe o resultado.
        """
        data_inicio = self.data_inicio_devedores_rel.text()
        data_fim = self.data_fim_devedores_rel.text()
        imob_id = self.combo_imobiliaria_devedores_rel.currentData()
        if self.combo_imobiliaria_devedores_rel.currentIndex() == 0: # Se "Todas as Imobiliárias"
            imob_id = None

        # Valida datas se preenchidas
        if data_inicio and not helpers.formatar_data_para_banco(data_inicio):
            QMessageBox.warning(self, "Data Inválida", "Formato de Data Início inválido. Use DD/MM/AAAA ou deixe em branco.")
            return
        if data_fim and not helpers.formatar_data_para_banco(data_fim):
            QMessageBox.warning(self, "Data Inválida", "Formato de Data Fim inválido. Use DD/MM/AAAA ou deixe em branco.")
            return

        # Chama o controller
        resultado = self.admin_controller.gerar_relatorio_clientes_devedores(
            data_inicio_cancelamento=data_inicio if data_inicio else None, # Envia None se campo vazio
            data_fim_cancelamento=data_fim if data_fim else None,
            imobiliaria_id_filtro=imob_id
        )
        if resultado['success']:
            QMessageBox.information(self, "Relatório Gerado", f"{resultado['message']}\nSalvo em: {resultado.get('path', 'N/D')}")
        else:
            QMessageBox.warning(self, "Erro ao Gerar Relatório", resultado['message'])

# Bloco para testar esta view isoladamente (não faz parte da aplicação final)
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    import os

    # Adiciona o diretório raiz do projeto ao sys.path para permitir importações relativas
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir)) # Sobe dois níveis (views -> engentoria)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from models.database import criar_tabelas # Para garantir que o banco e tabelas existam para o teste
    criar_tabelas() # Cria as tabelas se não existirem

    app = QApplication(sys.argv)
    # Instancia a AdminViewWidget para teste, simulando um usuário administrador (ID 1)
    admin_view = AdminViewWidget(user_id=1, user_type='adm')

    # Cria uma QMainWindow temporária para hospedar o widget
    main_window_temp = QMainWindow()
    main_window_temp.setCentralWidget(admin_view)
    main_window_temp.setWindowTitle("Teste Admin View Widget")
    main_window_temp.setGeometry(100, 100, 900, 700) # Posição e tamanho da janela de teste
    main_window_temp.show()

    sys.exit(app.exec_())
