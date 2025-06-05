# engentoria/views/gerenciar_vistoriador_view_widget.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QComboBox, QLineEdit, QFormLayout, QMessageBox,
    QStackedWidget, QScrollArea, QFrame, QDialog, QTextEdit, QCheckBox,
    QApplication, QMainWindow, QGridLayout, QGroupBox, QSpinBox, QInputDialog,
    QDateEdit, QTabWidget,
    QSizePolicy, QDialogButtonBox
)
from PyQt5.QtGui import QFont, QColor, QIcon, QDoubleValidator
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QDate, QTimer

import datetime

from controllers.admin_controller import AdminController
from controllers.agenda_controller import AgendaController
from utils import styles, validators, helpers
from models import agenda_model, imovel_model, usuario_model, imobiliaria_model # Usados para obter dados detalhados

from typing import Optional, Dict, Any, List, Tuple

# --- Diálogo para Marcar Vistoria como Improdutiva ---
class MarcarImprodutivaDialog(QDialog):
    """
    Diálogo customizado para coletar informações ao marcar uma vistoria como improdutiva.

    Permite ao administrador inserir o motivo da improdutividade e o valor a ser cobrado.
    """
    def __init__(self, agenda_item_data: dict, parent: Optional[QWidget] = None):
        """
        Construtor do MarcarImprodutivaDialog.

        Args:
            agenda_item_data (dict): Dados do item da agenda que será marcado como improdutivo.
                                     Usado para exibir informações relevantes no diálogo.
            parent (Optional[QWidget]): Widget pai, se houver.
        """
        super().__init__(parent)
        self.agenda_item_data = agenda_item_data # Dados da vistoria original
        self.setWindowTitle("Marcar Vistoria como Improdutiva")
        self.setMinimumWidth(450)
        self.setStyleSheet(styles.STYLESHEET_BASE_DARK) # Aplica estilo base ao diálogo

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15,15,15,15)
        self.layout.setSpacing(10)

        # Informações da vistoria original
        data_formatada = helpers.formatar_data_para_exibicao(agenda_item_data.get('data', 'N/A'))
        horario_formatado = helpers.formatar_horario_para_exibicao(agenda_item_data.get('horario', 'N/A'))
        cod_imovel = agenda_item_data.get('cod_imovel', 'N/A')
        cliente_nome = agenda_item_data.get('nome_cliente', 'N/A')

        title_text = (f"<b>Vistoria:</b> {cod_imovel}<br>"
                      f"<b>Data/Hora:</b> {data_formatada} às {horario_formatado}<br>"
                      f"<b>Cliente:</b> {cliente_nome}")
        title_label = QLabel(title_text)
        title_label.setStyleSheet(styles.INFO_TEXT_STYLE + "font-size: 14px; margin-bottom: 10px;")
        title_label.setWordWrap(True)
        self.layout.addWidget(title_label)

        # Formulário para motivo e valor
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.motivo_input = QTextEdit() # Campo para o motivo (multi-linhas)
        self.motivo_input.setPlaceholderText("Descreva o motivo da improdutividade (ex: cliente não compareceu, chave errada, etc.)")
        self.motivo_input.setMinimumHeight(80)
        form_layout.addRow("Motivo da Improdutividade:*", self.motivo_input)

        self.valor_cobranca_input = QLineEdit() # Campo para o valor da cobrança
        self.valor_cobranca_input.setPlaceholderText("Ex: 50.00")
        self.valor_cobranca_input.setValidator(QDoubleValidator(0.00, 9999.99, 2)) # Validador para valor monetário
        form_layout.addRow("Valor da Cobrança (R$):*", self.valor_cobranca_input)

        self.layout.addLayout(form_layout)

        # Botões de Ok e Cancelar
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Confirmar Improdutiva")
        self.buttons.button(QDialogButtonBox.Ok).setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        self.buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.buttons.button(QDialogButtonBox.Cancel).setStyleSheet(styles.SECONDARY_BUTTON_STYLE)

        self.buttons.accepted.connect(self.accept_data) # Conecta o OK para validação e depois self.accept()
        self.buttons.rejected.connect(self.reject) # Conecta o Cancelar para self.reject()
        self.layout.addWidget(self.buttons)

    def accept_data(self) -> None:
        """
        Valida os dados inseridos antes de fechar o diálogo com 'Accepted'.
        Se a validação falhar, exibe uma mensagem e não fecha o diálogo.
        """
        motivo = self.motivo_input.toPlainText().strip()
        valor_str = self.valor_cobranca_input.text().replace(',', '.').strip() # Garante ponto decimal

        if not motivo:
            QMessageBox.warning(self, "Campo Obrigatório", "O motivo da improdutividade é obrigatório.")
            self.motivo_input.setFocus()
            return # Impede o fechamento do diálogo
        if not valor_str:
            QMessageBox.warning(self, "Campo Obrigatório", "O valor da cobrança é obrigatório.")
            self.valor_cobranca_input.setFocus()
            return

        try:
            valor = float(valor_str)
            if valor < 0: # Valor não pode ser negativo
                QMessageBox.warning(self, "Valor Inválido", "O valor da cobrança não pode ser negativo.")
                self.valor_cobranca_input.setFocus()
                return
        except ValueError:
            QMessageBox.warning(self, "Valor Inválido", "Por favor, insira um valor numérico válido para a cobrança.")
            self.valor_cobranca_input.setFocus()
            return

        self.accept() # Se tudo ok, aceita e fecha o diálogo

    def get_data(self) -> Optional[Dict[str, Any]]:
        """
        Retorna os dados coletados pelo diálogo se ele foi aceito.

        Returns:
            Optional[Dict[str, Any]]: Um dicionário com 'motivo' e 'valor_cobranca',
                                      ou None se o diálogo foi cancelado.
        """
        if self.result() == QDialog.Accepted:
            return {
                "motivo": self.motivo_input.toPlainText().strip(),
                "valor_cobranca": float(self.valor_cobranca_input.text().replace(',', '.').strip())
            }
        return None

class GerenciarVistoriadorViewWidget(QWidget):
    """
    Widget para a página de Gerenciamento de Vistoriadores.

    Permite que administradores selecionem um vistoriador e gerenciem
    sua agenda (visualizar, fechar/reabrir horários, cancelar/editar/reagendar vistorias)
    e sua disponibilidade (horários fixos e avulsos).
    Utiliza um QTabWidget para separar as funcionalidades de agenda e disponibilidade.
    """
    def __init__(self, user_id: int, user_type: str, parent: Optional[QWidget] = None):
        """
        Construtor da GerenciarVistoriadorViewWidget.

        Args:
            user_id (int): ID do usuário administrador logado.
            user_type (str): Tipo do usuário logado (deve ser 'adm').
            parent (Optional[QWidget]): Widget pai, se houver.
        """
        super().__init__(parent)
        self.user_id = user_id # ID do administrador
        self.user_type = user_type # Tipo do usuário

        # Esta view é apenas para administradores
        if self.user_type != 'adm':
            self._show_error_page("Acesso não permitido. Esta página é exclusiva para administradores.")
            return

        self.admin_controller = AdminController() # Para listar vistoriadores, etc.
        self.agenda_controller = AgendaController() # Para manipular agenda e horários

        # --- Atributos de estado da view ---
        self.selected_vistoriador_id: Optional[int] = None # ID do vistoriador atualmente selecionado no combo
        self.current_vistoriador_data: Optional[Dict[str, Any]] = None # Dados completos do vistoriador selecionado
        self.current_agenda_item_data: Optional[Dict[str, Any]] = None # Dados do item da agenda selecionado na lista
        self._tab_changed_connection = None # Para gerenciar conexão do sinal currentChanged do QTabWidget
        self.vistoriador_detail_widget: Optional[QWidget] = None # Widget que contém as abas, é recriado ao trocar de vistoriador

        self._init_ui()

    def _show_error_page(self, message: str) -> None:
        """Exibe uma mensagem de erro centralizada se o acesso não for permitido."""
        layout = QVBoxLayout(self)
        error_label = QLabel(message)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet(styles.ERROR_MESSAGE_STYLE)
        layout.addWidget(error_label)
        self.setLayout(layout) # Define este layout de erro como o principal

    def _init_ui(self) -> None:
        """
        Inicializa a interface do usuário principal da tela de gerenciamento.
        """
        self.main_layout = QVBoxLayout(self) # Layout principal vertical
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)
        self.main_layout.setAlignment(Qt.AlignTop)

        title_label = QLabel("Gerenciar Vistoriadores e Suas Agendas")
        title_label.setStyleSheet(styles.PAGE_TITLE_STYLE)
        self.main_layout.addWidget(title_label)

        # Layout para seleção do vistoriador
        vistoriador_selection_layout = QHBoxLayout()
        lbl_select_vist = QLabel("Selecione um Vistoriador:")
        lbl_select_vist.setStyleSheet(styles.INFO_TEXT_STYLE + "font-weight: bold; font-size:14px;")
        self.combo_vistoriadores = QComboBox() # ComboBox para listar os vistoriadores
        self.combo_vistoriadores.setMinimumHeight(35)
        self.combo_vistoriadores.currentIndexChanged.connect(self._on_vistoriador_selection_changed) # Ao mudar, carrega dados
        vistoriador_selection_layout.addWidget(lbl_select_vist)
        vistoriador_selection_layout.addWidget(self.combo_vistoriadores, 1) # Ocupa espaço restante
        self.main_layout.addLayout(vistoriador_selection_layout)

        # Área de conteúdo que muda conforme o vistoriador selecionado
        self.content_area = QStackedWidget()
        self.main_layout.addWidget(self.content_area, 1) # Ocupa o restante da tela

        # Widget placeholder exibido quando nenhum vistoriador está selecionado
        self.placeholder_widget = QLabel("Selecione um vistoriador acima para ver e gerenciar seus dados.")
        self.placeholder_widget.setAlignment(Qt.AlignCenter)
        self.placeholder_widget.setStyleSheet(f"color: {styles.COLOR_TEXT_SECONDARY}; font-size: 16px; padding: 20px;")
        self.content_area.addWidget(self.placeholder_widget)

        # O self.vistoriador_detail_widget (que contém as abas) será criado e adicionado
        # dinamicamente em _on_vistoriador_selection_changed.

        self.content_area.setCurrentWidget(self.placeholder_widget) # Começa com o placeholder

    def _clear_layout(self, layout: Optional[Any]) -> None:
        """
        Helper recursivo para limpar todos os itens (widgets e layouts) de um dado layout.

        Args:
            layout: O layout (QVBoxLayout, QHBoxLayout, etc.) a ser limpo.
        """
        if layout is not None:
            while layout.count(): # Enquanto houver itens no layout
                item = layout.takeAt(0) # Pega o primeiro item
                widget = item.widget()
                if widget: # Se for um widget
                    widget.setParent(None) # Remove o parentesco
                    widget.deleteLater() # Agenda para deleção
                else:
                    sub_layout = item.layout() # Se for um sub-layout
                    if sub_layout:
                        self._clear_layout(sub_layout) # Limpa recursivamente
                        sub_layout.deleteLater() # Agenda o sub-layout para deleção

    def _rebuild_widget_layout(self, widget: QWidget, new_layout_factory: callable,
                               set_margins_and_spacing: bool = True,
                               default_margins: Tuple[int,int,int,int] = (0,0,0,0),
                               default_spacing: int = 10) -> Any:
        """
        Limpa o layout antigo de um widget (se existir) e aplica um novo layout.

        Args:
            widget (QWidget): O widget cujo layout será reconstruído.
            new_layout_factory (callable): Uma função que retorna uma nova instância de layout (ex: QHBoxLayout).
            set_margins_and_spacing (bool): Se True, define margens e espaçamento padrão.
            default_margins (Tuple[int,int,int,int]): Margens padrão (left, top, right, bottom).
            default_spacing (int): Espaçamento padrão entre os itens do layout.

        Returns:
            Any: A nova instância do layout aplicada ao widget.
        """
        old_layout = widget.layout() # Pega o layout atual do widget
        if old_layout is not None:
            self._clear_layout(old_layout) # Limpa todos os itens do layout antigo
            old_layout.deleteLater() # Agenda o objeto QLayout antigo para deleção

        new_layout = new_layout_factory() # Cria uma nova instância do layout desejado
        widget.setLayout(new_layout) # Define o novo layout para o widget

        # Configura margens e espaçamento se solicitado
        if set_margins_and_spacing and isinstance(new_layout, (QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout)):
            new_layout.setContentsMargins(*default_margins)
            if hasattr(new_layout, 'setSpacing'): # Nem todos os layouts têm setSpacing (ex: QFormLayout)
                 if not isinstance(new_layout, QFormLayout):
                    new_layout.setSpacing(default_spacing)
                 else: # QFormLayout tem espaçamentos vertical e horizontal separados
                    new_layout.setVerticalSpacing(default_spacing)
                    new_layout.setHorizontalSpacing(default_spacing + 5) # Um pouco mais de espaço horizontal
        return new_layout


    def atualizar_dados_view(self) -> None:
        """
        Método público para ser chamado quando esta view se torna visível
        ou quando dados externos que afetam a lista de vistoriadores mudam.

        Recarrega a lista de vistoriadores no QComboBox.
        """
        print("DEBUG: GerenciarVistoriadorViewWidget.atualizar_dados_view() chamado.")
        self._carregar_vistoriadores_para_selecao()

    def _carregar_vistoriadores_para_selecao(self) -> None:
        """
        Carrega a lista de todos os vistoriadores no QComboBox.

        Tenta manter a seleção atual do vistoriador, se possível, após recarregar a lista.
        """
        old_selected_data = self.combo_vistoriadores.currentData() # Salva dados do item atualmente selecionado

        self.combo_vistoriadores.blockSignals(True) # Bloqueia sinais para evitar chamadas recursivas
        self.combo_vistoriadores.clear() # Limpa itens antigos
        self.combo_vistoriadores.addItem("-- Selecione um Vistoriador --", None) # Adiciona placeholder

        vistoriadores = self.admin_controller.listar_todos_vistoriadores() # Busca vistoriadores
        new_index_to_set = 0 # Índice do item a ser selecionado após recarregar (default: placeholder)

        for i, vist_data_loop in enumerate(vistoriadores):
            # Adiciona cada vistoriador ao combo (texto e dados completos)
            self.combo_vistoriadores.addItem(f"{vist_data_loop['nome']} (ID: {vist_data_loop['id']})", vist_data_loop)
            # Se o vistoriador atual era o selecionado anteriormente, marca seu novo índice
            if old_selected_data and isinstance(old_selected_data, dict) and vist_data_loop['id'] == old_selected_data.get('id'):
                new_index_to_set = i + 1 # +1 por causa do placeholder no índice 0

        self.combo_vistoriadores.setCurrentIndex(new_index_to_set) # Restaura a seleção
        self.combo_vistoriadores.blockSignals(False) # Reabilita sinais

        # Força a chamada para _on_vistoriador_selection_changed para garantir que a UI
        # reflita a seleção atual do combo, mesmo que o índice não tenha mudado,
        # mas os dados (ex: nome do vistoriador) possam ter sido atualizados.
        # Isso é crucial se um vistoriador foi renomeado, por exemplo.
        self._on_vistoriador_selection_changed(self.combo_vistoriadores.currentIndex())


    def _on_vistoriador_selection_changed(self, index: int) -> None:
        """
        Chamado quando a seleção no QComboBox de vistoriadores muda.

        Atualiza a interface para mostrar os detalhes e a agenda do vistoriador selecionado,
        ou o placeholder se nenhum vistoriador estiver selecionado.

        Args:
            index (int): O índice do item selecionado no QComboBox.
        """
        new_vistoriador_data = self.combo_vistoriadores.itemData(index) # Pega os dados do vistoriador selecionado

        # --- Otimização: Evita reconstrução desnecessária da UI ---
        # Se os dados do novo vistoriador são os mesmos que os atuais:
        if new_vistoriador_data == self.current_vistoriador_data:
            # E se for o placeholder, e o placeholder já estiver visível, não faz nada.
            if new_vistoriador_data is None and self.content_area.currentWidget() == self.placeholder_widget:
                return
            # E se for um vistoriador real, e sua UI de detalhes já estiver montada,
            # pode ser necessário apenas recarregar os dados das abas (ex: agenda atualizada).
            if new_vistoriador_data is not None and self.vistoriador_detail_widget and self.content_area.currentWidget() == self.vistoriador_detail_widget:
                print(f"DEBUG: Mesmo vistoriador ID {new_vistoriador_data.get('id', 'N/A')} já selecionado. Recarregando dados das abas.")
                self._carregar_dados_para_abas_se_necessario() # Função para recarregar dados internos das abas
                return

        self.current_vistoriador_data = new_vistoriador_data # Atualiza os dados do vistoriador atual
        self.current_agenda_item_data = None # Reseta a seleção de item da agenda

        # Remove o widget de detalhes do vistoriador anterior do QStackedWidget, se existir.
        # Isso é importante para garantir que estamos sempre trabalhando com uma instância "limpa"
        # do widget de detalhes para o novo vistoriador, evitando estados inconsistentes.
        if self.vistoriador_detail_widget is not None:
            self.content_area.removeWidget(self.vistoriador_detail_widget)
            self.vistoriador_detail_widget.deleteLater() # Deleta o widget antigo para liberar memória
            self.vistoriador_detail_widget = None

        if self.current_vistoriador_data: # Se um vistoriador real foi selecionado (não o placeholder)
            self.selected_vistoriador_id = self.current_vistoriador_data['id']
            print(f"DEBUG: Trocando para Vistoriador ID {self.selected_vistoriador_id}. Configurando UI de detalhes...")

            self.vistoriador_detail_widget = QWidget() # Cria uma NOVA instância do widget de detalhes
            self._setup_vistoriador_detail_view(self.vistoriador_detail_widget) # Configura o conteúdo deste novo widget
            self.content_area.addWidget(self.vistoriador_detail_widget) # Adiciona ao QStackedWidget
            self.content_area.setCurrentWidget(self.vistoriador_detail_widget) # Mostra o widget de detalhes
        else: # Se o placeholder ("-- Selecione --") foi selecionado
            self.selected_vistoriador_id = None
            print("DEBUG: Nenhum vistoriador selecionado (placeholder). Mostrando placeholder UI.")
            self.content_area.setCurrentWidget(self.placeholder_widget) # Mostra o placeholder

    def _carregar_dados_para_abas_se_necessario(self) -> None:
        """
        Chamado quando o mesmo vistoriador é re-selecionado ou a view precisa ser atualizada.
        Garante que os dados nas abas (agenda, horários fixos) sejam recarregados.
        """
        if self.vistoriador_detail_widget and self.content_area.currentWidget() == self.vistoriador_detail_widget:
            # Se a UI de detalhes do vistoriador está montada e visível, recarrega os dados das abas.
            self._carregar_dados_para_abas()


    def _setup_vistoriador_detail_view(self, detail_widget_instance: QWidget) -> None:
        """
        Configura o layout e o conteúdo do widget de detalhes para o vistoriador selecionado.
        Este widget conterá um QTabWidget para "Agenda e Vistorias" e "Configurar Disponibilidade".

        Args:
            detail_widget_instance (QWidget): A instância do widget (recém-criada)
                                              onde os detalhes do vistoriador serão exibidos.
        """
        detail_layout = QVBoxLayout(detail_widget_instance) # Aplica um layout vertical ao widget fornecido
        detail_layout.setContentsMargins(0,0,0,0) # Sem margens externas para o container das abas
        detail_layout.setSpacing(10)

        vist_nome = self.current_vistoriador_data.get('nome', "N/A") if self.current_vistoriador_data else "N/A"
        info_label = QLabel(f"Gerenciando Vistoriador: {vist_nome}")
        info_label.setStyleSheet(styles.SUBTITLE_LABEL_STYLE) # Estilo de subtítulo
        detail_layout.addWidget(info_label)

        # Cria o QTabWidget para as seções
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {styles.COLOR_BORDER_DARK};
                background-color: {styles.COLOR_BACKGROUND_MEDIUM};
                padding: 10px;
            }}
            QTabBar::tab {{
                background: {styles.COLOR_BACKGROUND_LIGHT};
                color: {styles.COLOR_TEXT_SECONDARY};
                padding: 10px 20px; /* Espaçamento interno da aba */
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                border: 1px solid {styles.COLOR_BORDER_DARK};
                border-bottom: none; /* Remove a borda inferior da aba não selecionada */
                margin-right: 2px; /* Espaço entre as abas */
                font-size: 14px;
            }}
            QTabBar::tab:selected {{
                background: {styles.COLOR_BACKGROUND_MEDIUM}; /* Fundo da aba selecionada (mesmo do painel) */
                color: {styles.COLOR_ACCENT_PRIMARY}; /* Cor do texto da aba selecionada */
                font-weight: bold;
                border-bottom: 1px solid {styles.COLOR_BACKGROUND_MEDIUM}; /* "Remove" a borda inferior da aba selecionada */
            }}
            QTabBar::tab:hover {{
                background: {styles.COLOR_ACCENT_SECONDARY_HOVER};
                color: {styles.COLOR_TEXT_PRIMARY};
            }}
        """)

        # Cria os widgets que servirão como conteúdo para cada aba
        self.agenda_tab = QWidget()
        self.disponibilidade_tab = QWidget()

        # Adiciona as abas ao QTabWidget
        self.tab_widget.addTab(self.agenda_tab, "📅 Agenda e Vistorias")
        self.tab_widget.addTab(self.disponibilidade_tab, "⚙️ Configurar Disponibilidade")

        # Configura o conteúdo interno de cada aba
        self._setup_agenda_vistorias_tab_content(self.agenda_tab)
        self._setup_disponibilidade_tab_content(self.disponibilidade_tab)

        detail_layout.addWidget(self.tab_widget) # Adiciona o QTabWidget ao layout de detalhes

        self._carregar_dados_para_abas() # Carrega os dados para a aba inicialmente visível

        # Gerencia a conexão do sinal currentChanged para recarregar dados quando a aba muda
        if self._tab_changed_connection is not None:
            try:
                self.tab_widget.currentChanged.disconnect(self._tab_changed_connection)
            except TypeError: # Erro se a conexão não existia ou já foi desconectada
                pass
        self._tab_changed_connection = self.tab_widget.currentChanged.connect(self._tab_changed)


    def _tab_changed(self, index: int) -> None:
        """
        Chamado quando o usuário clica em uma aba diferente.
        Recarrega os dados para a aba recém-selecionada.

        Args:
            index (int): O índice da nova aba selecionada.
        """
        self._carregar_dados_para_abas() # Carrega os dados relevantes para a aba atual
        self.current_agenda_item_data = None # Reseta a seleção de item da agenda ao trocar de aba

    def _carregar_dados_para_abas(self) -> None:
        """
        Carrega os dados apropriados dependendo de qual aba está atualmente visível.
        """
        if not self.selected_vistoriador_id or not hasattr(self, 'tab_widget'):
            # Se nenhum vistoriador está selecionado ou o tab_widget não foi inicializado, não faz nada.
            return

        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index == 0: # Aba "Agenda e Vistorias"
            self._carregar_agenda_do_vistoriador()
        elif current_tab_index == 1: # Aba "Configurar Disponibilidade"
            self._carregar_horarios_fixos_atuais()

    def _create_panel_frame(self, object_name: Optional[str] = "styledPanel") -> QFrame:
        """
        Cria um QFrame estilizado para ser usado como painel.

        Args:
            object_name (Optional[str]): Nome do objeto para estilização via QSS, se necessário.

        Returns:
            QFrame: O painel QFrame configurado.
        """
        frame = QFrame()
        frame.setObjectName(object_name) # Permite estilização específica por nome de objeto
        frame.setFrameShape(QFrame.StyledPanel) # Forma padrão que pode ser alterada por QSS
        frame.setStyleSheet(styles.PANEL_STYLE) # Aplica o estilo de painel definido em utils/styles.py
        return frame

    def _setup_agenda_vistorias_tab_content(self, parent_tab_widget: QWidget) -> None:
        """
        Configura o conteúdo da aba "Agenda e Vistorias".

        Inclui filtros, a lista de itens da agenda e um painel de detalhes/ações.

        Args:
            parent_tab_widget (QWidget): O widget da aba onde o conteúdo será inserido.
        """
        # Usa _rebuild_widget_layout para garantir que o layout da aba seja limpo e reconstruído corretamente.
        # O layout principal desta aba será horizontal (QHBoxLayout).
        tab_layout = self._rebuild_widget_layout(parent_tab_widget, QHBoxLayout, default_spacing=15)

        # --- Painel da Esquerda: Lista de Agendamentos/Horários ---
        agenda_list_panel = self._create_panel_frame() # Cria um painel estilizado
        # Layout interno do painel da lista será vertical (QVBoxLayout).
        agenda_list_layout = self._rebuild_widget_layout(agenda_list_panel, QVBoxLayout, default_spacing=10)

        # Grupo para os filtros da agenda
        agenda_filters_group = QGroupBox("Filtros da Agenda")
        agenda_filters_group.setStyleSheet(styles.GROUP_BOX_TITLE_STYLE) # Estilo para o título do grupo
        agenda_filters_form_layout = QFormLayout() # Layout de formulário para os filtros
        agenda_filters_group.setLayout(agenda_filters_form_layout)
        agenda_filters_form_layout.setSpacing(10)

        # Filtro por período
        self.combo_filtro_periodo_agenda = QComboBox()
        self.combo_filtro_periodo_agenda.addItems([
            "Últimos 5 dias", "Hoje", "Amanhã", "Esta semana", "Próximos 7 dias", "Próximas 2 semanas",
            "Últimos 15 dias", "Mês Atual", "Mês Anterior", "Todo o período"
        ])
        self.combo_filtro_periodo_agenda.setCurrentText("Últimos 5 dias") # Padrão
        self.combo_filtro_periodo_agenda.currentIndexChanged.connect(self._carregar_agenda_do_vistoriador)
        agenda_filters_form_layout.addRow("Período:", self.combo_filtro_periodo_agenda)

        # Filtro por status
        self.combo_filtro_status_agenda = QComboBox()
        self.combo_filtro_status_agenda.addItems(["Todos Status", "Livre", "Agendado", "Fechado", "Improdutiva"])
        self.combo_filtro_status_agenda.setCurrentText("Todos Status") # Padrão
        self.combo_filtro_status_agenda.currentIndexChanged.connect(self._carregar_agenda_do_vistoriador)
        agenda_filters_form_layout.addRow("Status:", self.combo_filtro_status_agenda)
        agenda_list_layout.addWidget(agenda_filters_group) # Adiciona grupo de filtros ao painel da lista

        # Lista de itens da agenda
        self.list_widget_agenda_vistoriador = QListWidget()
        self.list_widget_agenda_vistoriador.setStyleSheet(f"""
            QListWidget {{
                background-color: {styles.COLOR_BACKGROUND_MEDIUM};
                border: 1px solid {styles.COLOR_BORDER_MEDIUM};
                border-radius: 5px; padding: 5px; font-size: 14px; outline: 0;
            }}
            QListWidget::item {{
                padding: 10px 8px; border-bottom: 1px solid {styles.COLOR_BORDER_DARK};
                color: {styles.COLOR_TEXT_SECONDARY}; border-radius: 4px;
            }}
            QListWidget::item:alternate {{ background-color: {styles.COLOR_BACKGROUND_LIGHT}; }} /* Cor para itens alternados */
            QListWidget::item:selected {{
                background-color: {styles.COLOR_ACCENT_PRIMARY_PRESSED}; color: {styles.COLOR_TEXT_PRIMARY};
                font-weight: bold;
            }}
            QListWidget::item:hover {{
                background-color: {styles.COLOR_ACCENT_SECONDARY_HOVER}; color: {styles.COLOR_TEXT_PRIMARY};
            }}
        """)
        self.list_widget_agenda_vistoriador.itemClicked.connect(self._on_agenda_list_item_selected)
        agenda_list_layout.addWidget(self.list_widget_agenda_vistoriador, 1) # Ocupa o espaço restante no painel

        tab_layout.addWidget(agenda_list_panel, 2) # Painel da lista ocupa 2/3 da largura da aba

        # --- Painel da Direita: Detalhes e Ações ---
        # Usa QScrollArea para o caso de muitos botões de ação ou detalhes extensos.
        self.details_action_scroll_area = QScrollArea()
        self.details_action_scroll_area.setWidgetResizable(True) # Permite que o widget interno redimensione
        self.details_action_scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        # Widget que irá DENTRO do QScrollArea e conterá o layout dos detalhes/ações.
        self.details_action_panel_content_widget = QWidget()
        self.details_action_scroll_area.setWidget(self.details_action_panel_content_widget)

        # Configura o conteúdo do painel de detalhes/ações (placeholder, botões, etc.)
        self._setup_agenda_actions_widgets_content()

        tab_layout.addWidget(self.details_action_scroll_area, 1) # Painel de detalhes/ações ocupa 1/3 da largura

    def _setup_agenda_actions_widgets_content(self) -> None:
        """
        Configura os widgets que aparecerão no painel de ações da aba de agenda.
        Isso inclui o placeholder, formulários para fechar horário, editar agendamento, reagendar, etc.
        Estes widgets são mostrados/ocultados dinamicamente com base no item selecionado na lista.
        """
        # Usa _rebuild_widget_layout para o widget que vai dentro do QScrollArea.
        # O layout será vertical (QVBoxLayout).
        self.details_action_layout = self._rebuild_widget_layout(
            self.details_action_panel_content_widget,
            QVBoxLayout,
            default_spacing=10
        )
        self.details_action_layout.setAlignment(Qt.AlignTop) # Alinha conteúdo ao topo

        # Placeholder inicial
        self.details_action_placeholder = QLabel("Selecione um item da agenda para ver detalhes e ações.")
        self.details_action_placeholder.setAlignment(Qt.AlignCenter)
        self.details_action_placeholder.setWordWrap(True)
        self.details_action_placeholder.setStyleSheet(f"color: {styles.COLOR_TEXT_SECONDARY}; font-size: 14px; padding:10px;")
        self.details_action_layout.addWidget(self.details_action_placeholder)

        # --- Widget para Fechar Horário Livre ---
        self.fechar_horario_widget_content = QWidget() # Container para o formulário de fechamento
        fechar_layout = QFormLayout(self.fechar_horario_widget_content)
        fechar_layout.setContentsMargins(0,0,0,0)
        self.motivo_fechamento_input = QLineEdit()
        self.motivo_fechamento_input.setPlaceholderText("Ex: Consulta médica")
        fechar_layout.addRow("Motivo:", self.motivo_fechamento_input)
        self.btn_confirmar_fechar = QPushButton("Confirmar Fechamento")
        self.btn_confirmar_fechar.setStyleSheet(styles.DANGER_BUTTON_STYLE)
        self.btn_confirmar_fechar.clicked.connect(self._handle_fechar_horario_action)
        fechar_layout.addRow(self.btn_confirmar_fechar)
        self.details_action_layout.addWidget(self.fechar_horario_widget_content)

        # --- Botão para Reabrir Horário Fechado ---
        self.btn_confirmar_reabrir = QPushButton("Confirmar Reabertura de Horário")
        self.btn_confirmar_reabrir.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        self.btn_confirmar_reabrir.clicked.connect(self._handle_reabrir_horario_action)
        self.details_action_layout.addWidget(self.btn_confirmar_reabrir)

        # --- Botão para Cancelar Agendamento ---
        self.btn_confirmar_cancelar_ag = QPushButton("Confirmar Cancelamento da Vistoria")
        self.btn_confirmar_cancelar_ag.setStyleSheet(styles.DANGER_BUTTON_STYLE)
        self.btn_confirmar_cancelar_ag.clicked.connect(self._handle_cancelar_agendamento_action)
        self.details_action_layout.addWidget(self.btn_confirmar_cancelar_ag)

        # --- Widget para Editar Dados da Vistoria (Agendamento) ---
        self.edit_agendamento_widget_content = QWidget() # Container para o formulário de edição
        edit_ag_layout = QFormLayout(self.edit_agendamento_widget_content)
        edit_ag_layout.setContentsMargins(0,0,0,0)
        edit_ag_layout.setSpacing(8) # Espaçamento menor para formulário compacto
        # Campos de edição (serão preenchidos com dados do agendamento selecionado)
        self.edit_cod_imovel_input = QLineEdit()
        edit_ag_layout.addRow("Cód. Imóvel:", self.edit_cod_imovel_input)
        self.edit_endereco_input = QLineEdit()
        edit_ag_layout.addRow("Endereço:", self.edit_endereco_input)
        self.edit_cep_input = QLineEdit()
        self.edit_cep_input.setInputMask("#####-###") # Máscara para CEP
        edit_ag_layout.addRow("CEP:", self.edit_cep_input)
        self.edit_referencia_input = QLineEdit()
        edit_ag_layout.addRow("Referência:", self.edit_referencia_input)
        self.edit_tamanho_input = QLineEdit()
        self.edit_tamanho_input.setValidator(QDoubleValidator(0.01, 99999.99, 2)) # Validador para tamanho
        edit_ag_layout.addRow("Tamanho (m²):", self.edit_tamanho_input)
        self.edit_tipo_mobilia_combo = QComboBox()
        self.edit_tipo_mobilia_combo.addItems(["sem_mobilia", "semi_mobiliado", "mobiliado"])
        edit_ag_layout.addRow("Mobília:", self.edit_tipo_mobilia_combo)
        self.edit_tipo_vistoria_combo = QComboBox()
        self.edit_tipo_vistoria_combo.addItems(["ENTRADA", "SAIDA", "CONFERENCIA"])
        edit_ag_layout.addRow("Tipo Vistoria:", self.edit_tipo_vistoria_combo)
        self.btn_salvar_edicao_ag = QPushButton("Salvar Alterações na Vistoria")
        self.btn_salvar_edicao_ag.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        self.btn_salvar_edicao_ag.clicked.connect(self._handle_salvar_edicao_agendamento_action)
        edit_ag_layout.addRow(self.btn_salvar_edicao_ag)
        self.details_action_layout.addWidget(self.edit_agendamento_widget_content)

        # --- Widget para Reagendar Vistoria ---
        self.reagendar_widget_content = QWidget() # Container para o formulário de reagendamento
        reagendar_layout_container = QVBoxLayout(self.reagendar_widget_content) # Layout principal do container
        reagendar_layout_container.setContentsMargins(0,0,0,0)
        reagendar_info_label = QLabel("Selecione abaixo a nova data e um horário livre para este vistoriador.")
        reagendar_info_label.setWordWrap(True)
        reagendar_info_label.setStyleSheet(styles.INFO_TEXT_STYLE)
        reagendar_layout_container.addWidget(reagendar_info_label)
        reagendar_form = QFormLayout() # Formulário para data e hora do reagendamento
        self.reagendar_data_input = QDateEdit(QDate.currentDate()) # QDateEdit para selecionar nova data
        self.reagendar_data_input.setCalendarPopup(True)
        self.reagendar_data_input.setDisplayFormat("dd/MM/yyyy")
        self.reagendar_data_input.dateChanged.connect(self._load_horarios_para_reagendamento) # Ao mudar data, carrega horários
        reagendar_form.addRow("Nova Data:", self.reagendar_data_input)
        self.reagendar_horario_combo = QComboBox() # ComboBox para selecionar novo horário livre
        self.reagendar_horario_combo.setPlaceholderText("Selecione um novo horário livre")
        self.reagendar_horario_combo.currentIndexChanged.connect( # Habilita botão de confirmar apenas se horário selecionado
            lambda: self.btn_confirmar_reagendamento.setEnabled(self.reagendar_horario_combo.currentIndex() > 0) # >0 para ignorar placeholder
        )
        reagendar_form.addRow("Novo Horário:", self.reagendar_horario_combo)
        reagendar_layout_container.addLayout(reagendar_form)
        self.btn_confirmar_reagendamento = QPushButton("Confirmar Reagendamento")
        self.btn_confirmar_reagendamento.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        self.btn_confirmar_reagendamento.setEnabled(False) # Começa desabilitado
        self.btn_confirmar_reagendamento.clicked.connect(self._handle_reagendar_action)
        reagendar_layout_container.addWidget(self.btn_confirmar_reagendamento)
        self.details_action_layout.addWidget(self.reagendar_widget_content)

        # --- Botões de Ação Principais (toggle para formulários de edição/reagendamento) ---
        # Estes botões são mostrados quando um agendamento ativo é selecionado.
        self.btn_toggle_edit_form = QPushButton("✏️ Editar Dados da Vistoria")
        self.btn_toggle_edit_form.setStyleSheet(styles.SECONDARY_BUTTON_STYLE)
        self.btn_toggle_edit_form.setCheckable(True) # Botão de alternância (on/off)
        self.btn_toggle_edit_form.toggled.connect( # Ao ser clicado, mostra/oculta o formulário de edição
            lambda checked: self._toggle_inline_widget(checked, self.edit_agendamento_widget_content, self._preencher_form_edicao_agendamento)
        )
        self.details_action_layout.addWidget(self.btn_toggle_edit_form)

        self.btn_toggle_reagendar_form = QPushButton("🔄 Reagendar (Mudar Data/Hora)")
        self.btn_toggle_reagendar_form.setStyleSheet(styles.SECONDARY_BUTTON_STYLE)
        self.btn_toggle_reagendar_form.setCheckable(True)
        self.btn_toggle_reagendar_form.toggled.connect( # Mostra/oculta formulário de reagendamento
            lambda checked: self._toggle_inline_widget(checked, self.reagendar_widget_content, self._preencher_form_reagendamento)
        )
        self.details_action_layout.addWidget(self.btn_toggle_reagendar_form)

        # Botão para Marcar como Improdutiva
        self.btn_marcar_improdutiva = QPushButton("⚠️ Marcar como Improdutiva")
        self.btn_marcar_improdutiva.setStyleSheet(styles.DANGER_BUTTON_STYLE)
        self.btn_marcar_improdutiva.clicked.connect(self._handle_marcar_improdutiva_action)
        self.details_action_layout.addWidget(self.btn_marcar_improdutiva)

        # Inicialmente, todos os formulários e botões de ação específicos estão ocultos, exceto o placeholder.
        self.fechar_horario_widget_content.hide()
        self.btn_confirmar_reabrir.hide()
        self.btn_confirmar_cancelar_ag.hide()
        self.edit_agendamento_widget_content.hide()
        self.reagendar_widget_content.hide()
        self.btn_toggle_edit_form.hide()
        self.btn_toggle_reagendar_form.hide()
        self.btn_marcar_improdutiva.hide()
        self.details_action_placeholder.show()


    def _populate_details_action_panel(self) -> None:
        """
        Popula o painel de detalhes e ações com base no item da agenda atualmente selecionado.

        Mostra informações do item e os botões de ação relevantes para o status do item.
        Oculta widgets de ação que não são aplicáveis.
        """
        layout = self.details_action_layout # Layout do painel de ações (dentro do QScrollArea)
        if layout is None:
            print("ERRO: _populate_details_action_panel chamado antes do layout de ações ser criado.")
            return

        # Lista de widgets que são "permanentes" no layout de ações (placeholder, formulários ocultos, etc.)
        # Eles não são removidos, apenas mostrados/ocultados.
        permanent_action_widgets = [
            self.details_action_placeholder,
            self.fechar_horario_widget_content, self.btn_confirmar_reabrir,
            self.btn_confirmar_cancelar_ag, self.btn_toggle_edit_form,
            self.edit_agendamento_widget_content, self.btn_toggle_reagendar_form,
            self.reagendar_widget_content, self.btn_marcar_improdutiva
        ]

        # Oculta todos os widgets de ação permanentes (exceto o placeholder inicialmente)
        for pw_widget in permanent_action_widgets:
            if pw_widget != self.details_action_placeholder: # Não oculta o placeholder aqui
                 pw_widget.hide()

        # Limpa quaisquer widgets "temporários" (como labels de informação do item anterior) do layout.
        # Itera de trás para frente para evitar problemas com índices ao remover itens.
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            widget = item.widget()
            # Se o widget não estiver na lista de permanentes, é um widget de informação temporário.
            if widget and widget not in permanent_action_widgets:
                layout.takeAt(i) # Remove do layout
                widget.setParent(None) # Remove parentesco
                widget.deleteLater() # Deleta

        if not self.current_agenda_item_data: # Se nenhum item da agenda está selecionado
            self.details_action_placeholder.show() # Mostra o placeholder
            # Garante que os botões de toggle (editar/reagendar) estejam desmarcados
            if hasattr(self, 'btn_toggle_edit_form'): self.btn_toggle_edit_form.setChecked(False)
            if hasattr(self, 'btn_toggle_reagendar_form'): self.btn_toggle_reagendar_form.setChecked(False)
            return

        # Se um item está selecionado, oculta o placeholder e mostra os detalhes/ações.
        self.details_action_placeholder.hide()

        item_data = self.current_agenda_item_data # Dados do item da agenda selecionado
        status = item_data.get('tipo_vistoria', 'LIVRE') # Status/tipo do item (LIVRE, FECHADO, ENTRADA, etc.)
        disponivel = item_data.get('disponivel', True) # Se o slot de agenda está marcado como disponível
        data_f = helpers.formatar_data_para_exibicao(item_data['data'])
        hora_f = helpers.formatar_horario_para_exibicao(item_data['horario'])

        # --- Adiciona informações do item selecionado ao painel ---
        title_label_text = f"<b>Detalhes: {data_f} às {hora_f}</b>"
        title_info_label = QLabel(title_label_text) # Label com data e hora
        title_info_label.setStyleSheet("font-size: 14px; margin-bottom: 5px; font-weight: bold;")
        layout.insertWidget(0, title_info_label) # Insere no topo do painel de ações

        info_text_list = [f"<b>Status:</b> {status.upper()}"] # Lista para construir o texto de informações

        # Adiciona informações específicas com base no status
        if status == 'FECHADO':
            motivo = "Não informado"
            try: # Tenta buscar o motivo do fechamento no banco
                conn = agenda_model.conectar_banco()
                cursor = conn.cursor()
                cursor.execute("SELECT motivo FROM horarios_fechados WHERE agenda_id = ?", (item_data['id_agenda'],))
                res_motivo = cursor.fetchone()
                if res_motivo and res_motivo[0]: motivo = res_motivo[0]
                conn.close()
            except Exception as e: print(f"Erro ao buscar motivo do fechamento: {e}")
            info_text_list.append(f"<b>Motivo:</b> {motivo}")
        elif status == 'IMPRODUTIVA':
            motivo_improd, valor_cobranca_improd = "Não informado", 0.0
            try: # Tenta buscar dados da vistoria improdutiva
                conn = agenda_model.conectar_banco()
                cursor = conn.cursor()
                cursor.execute("SELECT motivo_improdutividade, valor_cobranca FROM vistorias_improdutivas WHERE agenda_id_original = ?", (item_data['id_agenda'],))
                res_improd = cursor.fetchone()
                if res_improd: motivo_improd, valor_cobranca_improd = res_improd[0], res_improd[1]
                conn.close()
            except Exception as e: print(f"Erro ao buscar dados da vistoria improdutiva: {e}")
            info_text_list.append(f"<b>Motivo Improd.:</b> {motivo_improd}")
            info_text_list.append(f"<b>Valor Cobrado:</b> R$ {valor_cobranca_improd:.2f}")
        elif status in ['ENTRADA', 'SAIDA', 'CONFERENCIA']: # Se for um agendamento ativo
            imovel_id, cliente_id = item_data.get('imovel_id'), item_data.get('cliente_id')
            if imovel_id: # Busca e exibe informações do imóvel
                imovel_info = imovel_model.obter_imovel_por_id(imovel_id)
                if imovel_info:
                    info_text_list.append(f"<b>Cód. Imóvel:</b> {imovel_info.get('cod_imovel', 'N/D')}")
                    info_text_list.append(f"<b>Endereço:</b> {imovel_info.get('endereco', 'N/D')}")
                    mapa_mobilia = {"sem_mobilia": "Sem Mobília", "semi_mobiliado": "Semi-Mobiliado", "mobiliado": "Mobiliado"}
                    status_mobilia_db = imovel_info.get('mobiliado', 'N/D')
                    status_mobilia_display = mapa_mobilia.get(status_mobilia_db, status_mobilia_db)
                    info_text_list.append(f"<b>Mobília:</b> {status_mobilia_display}")
                    if imovel_info.get('imobiliaria_id'): # Busca e exibe nome da imobiliária
                        imob_info = imobiliaria_model.obter_imobiliaria_por_id(imovel_info.get('imobiliaria_id'))
                        if imob_info: info_text_list.append(f"<b>Imobiliária:</b> {imob_info.get('nome', 'N/D')}")
            if cliente_id: # Busca e exibe nome do cliente
                cliente_info = usuario_model.obter_cliente_por_id(cliente_id)
                if cliente_info: info_text_list.append(f"<b>Cliente:</b> {cliente_info.get('nome', 'N/D')}")

        info_label_widget = QLabel("<br>".join(info_text_list)) # Cria QLabel com todas as informações (HTML para quebras de linha)
        info_label_widget.setWordWrap(True)
        layout.insertWidget(1, info_label_widget) # Insere abaixo do título de data/hora

        separator = self._criar_separador_horizontal() # Separador visual
        layout.insertWidget(2, separator)

        action_section_label = QLabel() # Label para o título da seção de ações
        action_section_label.setStyleSheet("font-weight: bold;")
        layout.insertWidget(3, action_section_label)

        # --- Mostra os botões de ação relevantes para o status do item ---
        if status == 'LIVRE' and disponivel:
            action_section_label.setText("<b>Ações para Horário Livre:</b>")
            self.fechar_horario_widget_content.show() # Mostra formulário para fechar horário
        elif status == 'FECHADO':
            action_section_label.setText("<b>Ações para Horário Fechado:</b>")
            self.btn_confirmar_reabrir.show() # Mostra botão para reabrir
        elif status in ['ENTRADA', 'SAIDA', 'CONFERENCIA'] and not disponivel: # Agendamento ativo
            action_section_label.setText("<b>Ações para Agendamento Ativo:</b>")
            self.btn_confirmar_cancelar_ag.show() # Botão para cancelar
            self.btn_toggle_edit_form.show() # Botão para mostrar/ocultar form de edição
            self.btn_toggle_reagendar_form.show() # Botão para mostrar/ocultar form de reagendamento
            self.btn_marcar_improdutiva.show() # Botão para marcar como improdutiva
        else: # Nenhum estado conhecido ou ação aplicável
            action_section_label.setText("<b>Ações não disponíveis para este status.</b>")

        # Garante que os formulários de edição/reagendamento comecem ocultos
        self.btn_toggle_edit_form.setChecked(False) # Desmarca o botão (se estava marcado)
        self.btn_toggle_reagendar_form.setChecked(False)
        self.edit_agendamento_widget_content.hide() # Oculta o formulário de edição
        self.reagendar_widget_content.hide() # Oculta o formulário de reagendamento


    def _toggle_inline_widget(self, show: bool, widget_to_toggle: QWidget, setup_function: Optional[callable] = None) -> None:
        """
        Mostra ou oculta um widget (geralmente um formulário inline).
        Se `show` for True, também pode chamar uma função `setup_function` para preencher o widget.
        Garante que apenas um dos formulários (edição ou reagendamento) esteja visível por vez.

        Args:
            show (bool): True para mostrar, False para ocultar.
            widget_to_toggle (QWidget): O widget a ser mostrado/ocultado.
            setup_function (Optional[callable]): Função a ser chamada para configurar/preencher o widget antes de mostrá-lo.
        """
        if show:
            # Se for para mostrar o formulário de edição, oculta o de reagendamento (e vice-versa)
            if widget_to_toggle == self.edit_agendamento_widget_content:
                self.reagendar_widget_content.hide()
                self.btn_toggle_reagendar_form.setChecked(False) # Desmarca o outro botão de toggle
            elif widget_to_toggle == self.reagendar_widget_content:
                self.edit_agendamento_widget_content.hide()
                self.btn_toggle_edit_form.setChecked(False)

            if setup_function: # Se uma função de setup foi passada (ex: para preencher campos)
                setup_function()
            widget_to_toggle.show() # Mostra o widget
        else:
            widget_to_toggle.hide() # Oculta o widget

    def _preencher_form_edicao_agendamento(self) -> None:
        """
        Preenche os campos do formulário de edição de agendamento com os dados
        do item da agenda atualmente selecionado.
        """
        if not self.current_agenda_item_data: return # Sai se nenhum item selecionado

        item_data = self.current_agenda_item_data # Dados do agendamento atual

        # Preenche os campos do formulário de edição
        self.edit_cod_imovel_input.setText(item_data.get('cod_imovel', ''))
        self.edit_endereco_input.setText(item_data.get('endereco_imovel', ''))
        self.edit_cep_input.setText(item_data.get('cep', '') if item_data.get('cep') else "")
        self.edit_referencia_input.setText(item_data.get('referencia', '') if item_data.get('referencia') else "")

        tamanho_val = item_data.get('tamanho') # Tamanho pode ser float
        self.edit_tamanho_input.setText(str(tamanho_val) if tamanho_val is not None else "")

        # Obtém o status de mobília do imóvel (precisa buscar do modelo de imóvel)
        imovel_id = item_data.get('imovel_id')
        mobiliado_status = 'sem_mobilia' # Padrão
        if imovel_id:
            imovel_info = imovel_model.obter_imovel_por_id(imovel_id)
            if imovel_info:
                mobiliado_status = imovel_info.get('mobiliado', 'sem_mobilia')

        # Seleciona o item correto no QComboBox de mobília
        idx_mobilia = self.edit_tipo_mobilia_combo.findText(mobiliado_status, Qt.MatchFixedString)
        self.edit_tipo_mobilia_combo.setCurrentIndex(idx_mobilia if idx_mobilia >= 0 else 0)

        # Seleciona o item correto no QComboBox de tipo de vistoria
        tipo_vistoria_status = item_data.get('tipo_vistoria', 'ENTRADA')
        idx_tipo_vist = self.edit_tipo_vistoria_combo.findText(tipo_vistoria_status, Qt.MatchFixedString)
        self.edit_tipo_vistoria_combo.setCurrentIndex(idx_tipo_vist if idx_tipo_vist >=0 else 0)


    def _preencher_form_reagendamento(self) -> None:
        """
        Prepara o formulário de reagendamento.
        Define a data inicial para a data atual e carrega os horários livres para essa data.
        """
        if not self.current_agenda_item_data: return
        self.reagendar_data_input.setDate(QDate.currentDate()) # Define data para hoje
        self._load_horarios_para_reagendamento() # Carrega horários livres para a data selecionada

    def _load_horarios_para_reagendamento(self) -> None:
        """
        Carrega os horários livres do vistoriador selecionado para a data
        especificada no QDateEdit do formulário de reagendamento.
        Popula o QComboBox de horários para reagendamento.
        """
        if not self.selected_vistoriador_id: # Se nenhum vistoriador principal está selecionado na view
            self.reagendar_horario_combo.clear()
            self.reagendar_horario_combo.addItem("--Vistoriador não selecionado--", None)
            self.btn_confirmar_reagendamento.setEnabled(False)
            return

        self.reagendar_horario_combo.clear() # Limpa horários antigos
        self.reagendar_horario_combo.addItem("--Selecione Novo Horário--", None) # Placeholder
        self.btn_confirmar_reagendamento.setEnabled(False) # Desabilita botão de confirmar

        data_selecionada_qdate = self.reagendar_data_input.date() # Pega a data do QDateEdit
        data_selecionada_str = data_selecionada_qdate.toString("yyyy-MM-dd") # Formata para o banco

        # Busca horários livres para o vistoriador e data
        horarios_livres = self.agenda_controller.listar_horarios_do_vistoriador(
            vistoriador_id=self.selected_vistoriador_id,
            data_inicio=data_selecionada_str,
            data_fim=data_selecionada_str, # Mesma data para buscar apenas um dia
            apenas_disponiveis=True
        )
        for horario_data in horarios_livres:
            # Não adiciona o horário original da vistoria que está sendo reagendada, caso seja no mesmo dia.
            # Isso evita que o usuário tente reagendar para o mesmo slot que está desocupando.
            if self.current_agenda_item_data and \
               horario_data['id_agenda'] == self.current_agenda_item_data['id_agenda']:
                continue # Pula o horário original
            self.reagendar_horario_combo.addItem(f"{horario_data['horario']}", horario_data['id_agenda'])


    def _carregar_agenda_do_vistoriador(self) -> None:
        """
        Carrega a lista de itens da agenda (agendamentos, horários livres/fechados)
        para o vistoriador atualmente selecionado, aplicando os filtros de período e status.
        Popula o QListWidget `list_widget_agenda_vistoriador`.
        """
        self.list_widget_agenda_vistoriador.clear() # Limpa a lista

        if not self.selected_vistoriador_id: # Se nenhum vistoriador selecionado no combo principal
            no_item_msg = QListWidgetItem("Nenhum vistoriador selecionado.")
            no_item_msg.setTextAlignment(Qt.AlignCenter)
            no_item_msg.setFlags(Qt.NoItemFlags) # Item não selecionável
            self.list_widget_agenda_vistoriador.addItem(no_item_msg)
            self.current_agenda_item_data = None # Reseta seleção de item da agenda
            self._populate_details_action_panel() # Atualiza painel de ações para mostrar placeholder
            return

        # Obtém os filtros selecionados
        filtro_periodo_str = self.combo_filtro_periodo_agenda.currentText()
        filtro_status_str = self.combo_filtro_status_agenda.currentText()

        # Converte o filtro de status de texto para os parâmetros booleanos esperados pelo controller
        apenas_disponiveis_param = (filtro_status_str == "Livre")
        apenas_agendados_param = (filtro_status_str == "Agendado")
        incluir_fechados_param = (filtro_status_str == "Fechado" or filtro_status_str == "Todos Status")
        incluir_improdutivas_param = (filtro_status_str == "Improdutiva" or filtro_status_str == "Todos Status")

        if filtro_status_str == "Todos Status": # Ajusta flags para "Todos Status"
            apenas_disponiveis_param = False
            apenas_agendados_param = False
            # Ao listar "Todos Status", queremos ver livres, agendados, fechados e improdutivas.
            # A lógica do controller precisa ser ajustada ou aqui precisamos de mais flags.
            # Assumindo que o controller lida bem com essas flags:
            # Se "Todos Status", o controller deve buscar tudo que não seja apenas_disponiveis=True ou apenas_agendados=True
            # e que se encaixe nos incluir_fechados/incluir_improdutivas.
            # Para simplificar, listar_horarios_do_vistoriador deveria ter um modo "geral"
            # ou ser chamado múltiplas vezes com filtros diferentes.
            # A implementação atual do controller pode precisar de revisão para o filtro "Todos Status".
            # Por ora, o código abaixo tenta passar flags que façam sentido.
            # Se apenas_disponiveis e apenas_agendados são False, e incluir_fechados/improdutivas são True,
            # o controller deveria buscar tudo.

        # Obtém as datas de início e fim com base no filtro de período
        data_inicio, data_fim = helpers.obter_datas_para_filtro_periodo(filtro_periodo_str)

        # Busca os itens da agenda
        agenda_items = self.agenda_controller.listar_horarios_do_vistoriador(
            vistoriador_id=self.selected_vistoriador_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            apenas_disponiveis=apenas_disponiveis_param,
            apenas_agendados=apenas_agendados_param,
            incluir_fechados=incluir_fechados_param,
            incluir_improdutivas=incluir_improdutivas_param
        )

        if not agenda_items: # Se não houver itens para os filtros
            no_item_msg = QListWidgetItem("Nenhum item na agenda para os filtros selecionados.")
            no_item_msg.setTextAlignment(Qt.AlignCenter)
            no_item_msg.setFlags(Qt.NoItemFlags)
            self.list_widget_agenda_vistoriador.addItem(no_item_msg)
            self.current_agenda_item_data = None
            self._populate_details_action_panel()
            return

        # Popula a lista com os itens encontrados
        for item_data in agenda_items:
            data_f = helpers.formatar_data_para_exibicao(item_data['data'])
            hora_f = helpers.formatar_horario_para_exibicao(item_data['horario'])
            dia_semana = helpers.traduzir_dia_semana(datetime.datetime.strptime(item_data['data'], "%Y-%m-%d").weekday(), abreviado=True)

            # Define o texto e a cor do status
            status_str = "Indefinido"
            status_color = styles.COLOR_TEXT_SECONDARY # Cor padrão

            if item_data['tipo_vistoria'] == 'LIVRE' and item_data['disponivel']:
                status_str = "LIVRE"
                status_color = styles.COLOR_ACCENT_PRIMARY # Verde para livre
            elif item_data['tipo_vistoria'] == 'FECHADO':
                status_str = "FECHADO"
                status_color = styles.COLOR_DANGER # Vermelho para fechado
            elif item_data['tipo_vistoria'] == 'IMPRODUTIVA':
                status_str = "IMPRODUTIVA"
                status_color = "#FFA500" # Laranja para improdutiva
            elif item_data['tipo_vistoria'] in ['ENTRADA', 'SAIDA', 'CONFERENCIA'] and not item_data['disponivel']:
                status_str = f"AGENDADO ({item_data['tipo_vistoria']})"
                status_color = "#DAA520" # Um tom de amarelo/dourado para agendado
            # Pode haver outros estados ou combinações
            else:
                status_str = f"{item_data['tipo_vistoria']} (Disp: {item_data['disponivel']})"


            item_text = f"{dia_semana} {data_f} às {hora_f}  -  Status: {status_str}"
            # Se for um agendamento, adiciona informações do imóvel e cliente
            if item_data.get('imovel_id'): # Checa se tem imovel_id (indica agendamento)
                cod_imovel = item_data.get('cod_imovel', 'N/D') # Pega o código do imóvel dos dados do item
                nome_cliente = item_data.get('nome_cliente', 'N/D') # Pega nome do cliente
                item_text += f"\nImóvel: {cod_imovel} | Cliente: {nome_cliente}" # Adiciona à string do item

            list_item = QListWidgetItem(item_text)
            list_item.setData(Qt.UserRole, item_data) # Armazena todos os dados do item no QListWidgetItem
            list_item.setForeground(QColor(status_color)) # Define a cor do texto
            # Ajusta a altura do item se tiver mais de uma linha (por causa do \n)
            list_item.setSizeHint(QSize(0, 45 if '\n' not in item_text else 65 ))
            self.list_widget_agenda_vistoriador.addItem(list_item)

        # Tenta selecionar o primeiro item da lista automaticamente após carregar,
        # mas apenas se a lista não estiver vazia e o primeiro item for válido.
        if self.list_widget_agenda_vistoriador.count() > 0:
             first_item = self.list_widget_agenda_vistoriador.item(0)
             if first_item and first_item.data(Qt.UserRole) is not None: # Se o primeiro item tem dados válidos
                 # Usa QTimer.singleShot para garantir que a seleção ocorra após a QListWidget
                 # ter processado completamente a adição de itens e estiver pronta para ter um item selecionado.
                 QTimer.singleShot(0, lambda item_to_select=first_item: self._selecionar_primeiro_item_agenda(item_to_select))
             else: # Primeiro item é um placeholder ou inválido
                self.current_agenda_item_data = None
                self._populate_details_action_panel() # Mostra placeholder no painel de ações
        else: # Lista está vazia (após filtros, nenhum item encontrado)
            self.current_agenda_item_data = None
            self._populate_details_action_panel()


    def _selecionar_primeiro_item_agenda(self, item_to_select: QListWidgetItem) -> None:
        """
        Seleciona o item fornecido na lista de agenda.
        Chamado via QTimer para garantir que ocorra no momento certo do ciclo de eventos Qt.

        Args:
            item_to_select (QListWidgetItem): O item a ser selecionado.
        """
        if self.list_widget_agenda_vistoriador.count() > 0 and item_to_select and \
           self.list_widget_agenda_vistoriador.row(item_to_select) != -1: # Verifica se o item ainda existe na lista
            self.list_widget_agenda_vistoriador.setCurrentItem(item_to_select) # Define como item atual
            self._on_agenda_list_item_selected(item_to_select) # Chama o handler de seleção
        elif self.list_widget_agenda_vistoriador.count() == 0: # Se, nesse meio tempo, a lista ficou vazia
            self.current_agenda_item_data = None
            self._populate_details_action_panel() # Mostra placeholder


    def _on_agenda_list_item_selected(self, item: QListWidgetItem) -> None:
        """
        Chamado quando um item na `list_widget_agenda_vistoriador` é clicado/selecionado.

        Atualiza `current_agenda_item_data` e o painel de detalhes/ações.

        Args:
            item (QListWidgetItem): O item da lista que foi selecionado.
        """
        if item is None or item.data(Qt.UserRole) is None: # Se o item for inválido ou placeholder
            self.current_agenda_item_data = None
        else:
            self.current_agenda_item_data = item.data(Qt.UserRole) # Armazena os dados do item selecionado

        self._populate_details_action_panel() # Atualiza o painel de ações para refletir a seleção


    def _handle_fechar_horario_action(self) -> None:
        """
        Manipula a ação de fechar um horário livre.
        Pede um motivo e chama o controller.
        """
        if not self.current_agenda_item_data or not self.selected_vistoriador_id:
            QMessageBox.warning(self, "Erro", "Nenhum horário selecionado ou vistoriador não identificado.")
            return

        id_agenda = self.current_agenda_item_data['id_agenda']
        motivo = self.motivo_fechamento_input.text().strip()
        if not motivo:
            QMessageBox.warning(self, "Motivo Necessário", "Por favor, insira um motivo para fechar o horário.")
            self.motivo_fechamento_input.setFocus()
            return

        # Chama o controller para fechar o horário
        resultado = self.agenda_controller.fechar_horario_manualmente(id_agenda, motivo, self.selected_vistoriador_id)
        if resultado['success']:
            QMessageBox.information(self, "Sucesso", resultado['message'])
            self._carregar_agenda_do_vistoriador() # Recarrega a lista
        else:
            QMessageBox.warning(self, "Erro", resultado['message'])
        self.motivo_fechamento_input.clear() # Limpa o campo de motivo


    def _handle_reabrir_horario_action(self) -> None:
        """
        Manipula a ação de reabrir um horário que estava fechado.
        Pede confirmação e chama o controller.
        """
        if not self.current_agenda_item_data or not self.selected_vistoriador_id:
            QMessageBox.warning(self, "Erro", "Nenhum horário selecionado ou vistoriador não identificado.")
            return

        id_agenda = self.current_agenda_item_data['id_agenda']
        confirm = QMessageBox.question(self, "Confirmar Reabertura",
                                       f"Tem certeza que deseja reabrir o horário selecionado?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            resultado = self.agenda_controller.reabrir_horario_fechado(id_agenda, self.selected_vistoriador_id)
            if resultado['success']:
                QMessageBox.information(self, "Sucesso", resultado['message'])
                self._carregar_agenda_do_vistoriador() # Recarrega
            else:
                QMessageBox.warning(self, "Erro", resultado['message'])


    def _handle_cancelar_agendamento_action(self) -> None:
        """
        Manipula a ação de cancelar uma vistoria agendada.
        Pede confirmação e chama o controller.
        """
        if not self.current_agenda_item_data:
            QMessageBox.warning(self, "Erro", "Nenhum agendamento selecionado.")
            return

        id_agenda = self.current_agenda_item_data['id_agenda']
        cliente_id = self.current_agenda_item_data.get('cliente_id') # Precisa do ID do cliente para o controller
        if not cliente_id:
             QMessageBox.warning(self, "Erro", "ID do cliente não encontrado para este agendamento. Não é possível cancelar.")
             return

        confirm = QMessageBox.question(self, "Confirmar Cancelamento",
                                       f"Tem certeza que deseja cancelar esta vistoria?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            resultado = self.agenda_controller.cancelar_vistoria_agendada(id_agenda, cliente_id)
            if resultado['success']:
                QMessageBox.information(self, "Sucesso", resultado['message'])
                self._carregar_agenda_do_vistoriador() # Recarrega
            else:
                QMessageBox.warning(self, "Erro ao Cancelar", resultado['message'])

    def _handle_marcar_improdutiva_action(self) -> None:
        """
        Manipula a ação de marcar uma vistoria agendada como improdutiva.
        Abre um diálogo para coletar motivo e valor, depois chama o controller.
        """
        if not self.current_agenda_item_data or not self.selected_vistoriador_id:
            QMessageBox.warning(self, "Erro", "Nenhum agendamento selecionado para marcar como improdutivo.")
            return

        agenda_data = self.current_agenda_item_data
        # Verifica se é um agendamento ativo (ENTRADA, SAIDA, CONFERENCIA) e não disponível (ou seja, ocupado)
        if not (agenda_data.get('tipo_vistoria') in ['ENTRADA', 'SAIDA', 'CONFERENCIA'] and not agenda_data.get('disponivel')):
            QMessageBox.information(self, "Ação Inválida", "Apenas vistorias agendadas e ativas (Entrada, Saída, Conferência) podem ser marcadas como improdutivas.")
            return

        dialog = MarcarImprodutivaDialog(agenda_data, self) # Cria e mostra o diálogo
        if dialog.exec_() == QDialog.Accepted: # Se o usuário confirmou no diálogo
            improdutiva_data = dialog.get_data() # Pega os dados do diálogo (motivo, valor)
            if improdutiva_data:
                imovel_id = agenda_data.get('imovel_id')
                imobiliaria_id_do_imovel = None
                if imovel_id: # Tenta obter a imobiliária do imóvel, se houver
                    imovel_atual = imovel_model.obter_imovel_por_id(imovel_id)
                    if imovel_atual:
                        imobiliaria_id_do_imovel = imovel_atual.get('imobiliaria_id')

                cliente_id = agenda_data.get('cliente_id')
                if not cliente_id: # Cliente é essencial para a lógica de improdutividade
                    QMessageBox.warning(self, "Erro", "ID do cliente não encontrado para este agendamento. Não é possível marcar como improdutiva.")
                    return

                # Chama o controller para registrar a improdutividade
                resultado = self.admin_controller.marcar_vistoria_como_improdutiva(
                    agenda_id=agenda_data['id_agenda'],
                    cliente_id=cliente_id,
                    imovel_id=imovel_id,
                    imobiliaria_id=imobiliaria_id_do_imovel, # Pode ser None
                    data_vistoria_original=agenda_data['data'],
                    horario_vistoria_original=agenda_data['horario'],
                    motivo=improdutiva_data['motivo'],
                    valor_cobranca=improdutiva_data['valor_cobranca']
                )
                if resultado['success']:
                    QMessageBox.information(self, "Sucesso", resultado['message'])
                    self._carregar_agenda_do_vistoriador() # Recarrega
                else:
                    QMessageBox.warning(self, "Erro ao Marcar Improdutiva", resultado['message'])


    def _handle_salvar_edicao_agendamento_action(self) -> None:
        """
        Manipula a ação de salvar as alterações feitas no formulário de edição de agendamento.
        Atualiza os dados do imóvel e, se necessário, o tipo de vistoria na agenda.
        """
        if not self.current_agenda_item_data or not self.current_agenda_item_data.get('imovel_id'):
            QMessageBox.warning(self, "Erro", "Nenhum agendamento ou imóvel selecionado para edição.")
            return

        # Coleta os dados do formulário de edição
        imovel_id_original = self.current_agenda_item_data['imovel_id']
        novo_cod_imovel = self.edit_cod_imovel_input.text().strip()
        novo_endereco = self.edit_endereco_input.text().strip()
        novo_cep = self.edit_cep_input.text().replace("-","").strip() or None # Remove máscara e usa None se vazio
        novo_referencia = self.edit_referencia_input.text().strip() or None
        novo_tamanho_str = self.edit_tamanho_input.text().replace(',', '.').strip() # Garante ponto decimal
        novo_mobiliado = self.edit_tipo_mobilia_combo.currentText()
        novo_tipo_vistoria_agenda = self.edit_tipo_vistoria_combo.currentText() # Novo tipo de vistoria para a AGENDA

        # Validações
        if not all([novo_cod_imovel, novo_endereco, novo_tamanho_str]):
            QMessageBox.warning(self, "Campos Obrigatórios", "Código do imóvel, endereço e tamanho são obrigatórios.")
            return
        try:
            novo_tamanho = float(novo_tamanho_str)
            if novo_tamanho <=0: raise ValueError("Tamanho deve ser positivo")
        except ValueError as e_val:
            QMessageBox.warning(self, "Dado Inválido", f"Tamanho do imóvel inválido: {e_val}")
            return

        # Obtém dados atuais do imóvel para manter cliente_id e imobiliaria_id
        imovel_atual_data = imovel_model.obter_imovel_por_id(imovel_id_original)
        if not imovel_atual_data:
            QMessageBox.warning(self, "Erro", "Imóvel original não encontrado no banco de dados.")
            return

        # Monta o dicionário de dados para atualização do imóvel
        imovel_updates = {
            'cod_imovel': novo_cod_imovel, 'endereco': novo_endereco, 'cep': novo_cep,
            'referencia': novo_referencia, 'tamanho': novo_tamanho, 'mobiliado': novo_mobiliado,
            'cliente_id': imovel_atual_data['cliente_id'], # Mantém o cliente original
            'imobiliaria_id': imovel_atual_data['imobiliaria_id'] # Mantém a imobiliária original
        }

        # Atualiza o imóvel no banco
        sucesso_update_imovel = imovel_model.atualizar_imovel(imovel_id_original, **imovel_updates)

        if not sucesso_update_imovel:
            # A mensagem de erro específica do model já deve ter sido logada no console.
            QMessageBox.warning(self, "Erro na Atualização", "Falha ao atualizar os dados do imóvel. Verifique o console para detalhes.")
            return

        # Se o tipo de vistoria na agenda também mudou, atualiza-o
        id_agenda = self.current_agenda_item_data['id_agenda']
        tipo_vistoria_original_agenda = self.current_agenda_item_data['tipo_vistoria']

        if tipo_vistoria_original_agenda != novo_tipo_vistoria_agenda:
            try:
                conn = agenda_model.conectar_banco()
                cursor = conn.cursor()
                cursor.execute("UPDATE agenda SET tipo = ? WHERE id = ?",
                               (novo_tipo_vistoria_agenda, id_agenda))
                conn.commit()
                conn.close()
                print(f"Tipo de vistoria do agendamento ID {id_agenda} atualizado para {novo_tipo_vistoria_agenda}.")
            except Exception as e_agenda_update:
                QMessageBox.warning(self, "Erro", f"Falha ao atualizar o tipo da vistoria na agenda: {e_agenda_update}")
                # Considerar se deve reverter a atualização do imóvel aqui ou logar o erro.
                # Por ora, a atualização do imóvel permanece.
                return # Não continua se a atualização da agenda falhar

        QMessageBox.information(self, "Sucesso", "Dados da vistoria atualizados!")
        self._carregar_agenda_do_vistoriador() # Recarrega a lista
        self.btn_toggle_edit_form.setChecked(False) # Oculta o formulário de edição


    def _handle_reagendar_action(self) -> None:
        """
        Manipula a ação de reagendar uma vistoria.
        Cancela a vistoria original e a agenda para o novo horário selecionado.
        """
        if not self.current_agenda_item_data or not self.selected_vistoriador_id:
            QMessageBox.warning(self, "Erro", "Agendamento original ou vistoriador não identificado.")
            return

        novo_id_agenda_selecionado_para_reag = self.reagendar_horario_combo.currentData()
        if novo_id_agenda_selecionado_para_reag is None: # Nenhum novo horário selecionado
            QMessageBox.warning(self, "Seleção Necessária", "Por favor, selecione um novo horário livre para o reagendamento.")
            return

        # Dados da vistoria original
        id_agenda_original = self.current_agenda_item_data['id_agenda']
        imovel_id_original = self.current_agenda_item_data['imovel_id']
        cliente_id_original = self.current_agenda_item_data.get('cliente_id')
        tipo_vistoria_atual_original = self.current_agenda_item_data['tipo_vistoria']

        if not cliente_id_original:
            QMessageBox.warning(self, "Erro", "Não foi possível identificar o cliente do agendamento original.")
            return
        if not imovel_id_original:
            QMessageBox.warning(self, "Erro", "Não foi possível identificar o imóvel do agendamento original.")
            return

        confirm_reag = QMessageBox.question(self, "Confirmar Reagendamento",
                                           f"Isso cancelará a vistoria original e a agendará para o novo horário selecionado.\n\nDeseja continuar?",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm_reag == QMessageBox.No:
            return

        # 1. Cancela a vistoria original
        res_cancel = self.agenda_controller.cancelar_vistoria_agendada(id_agenda_original, cliente_id_original)
        if not res_cancel['success']:
            QMessageBox.warning(self, "Erro no Reagendamento", f"Não foi possível cancelar a vistoria original: {res_cancel['message']}\nO reagendamento foi abortado.")
            self._carregar_agenda_do_vistoriador() # Recarrega para mostrar o estado atual
            return

        # 2. Verifica se o imóvel ainda existe (deve existir, pois cancelar_vistoria não o remove)
        imovel_para_reagendar = imovel_model.obter_imovel_por_id(imovel_id_original)
        if not imovel_para_reagendar:
            # Este é um estado inesperado e crítico.
            QMessageBox.critical(self, "Erro Crítico", f"O imóvel ID {imovel_id_original} não foi encontrado após o cancelamento da vistoria original. Não é possível reagendar.")
            self._carregar_agenda_do_vistoriador()
            return

        # 3. Agenda a vistoria no novo horário
        res_agendar = self.agenda_controller.finalizar_agendamento_vistoria(
            id_agenda_selecionada=novo_id_agenda_selecionado_para_reag, # ID do novo slot de agenda
            imovel_id=imovel_id_original, # ID do mesmo imóvel
            tipo_vistoria=tipo_vistoria_atual_original, # Mantém o tipo de vistoria original
            forcar_agendamento_unico=False # Assume que o novo slot é válido (já filtrado por disponibilidade)
        )

        if res_agendar['success']:
            QMessageBox.information(self, "Sucesso", f"Vistoria reagendada com sucesso para o novo horário!\n{res_agendar['message']}")
        else:
            # Se falhou ao agendar no novo slot (ex: slot ficou indisponível entre a seleção e a confirmação)
            QMessageBox.warning(self, "Erro no Reagendamento", f"Não foi possível agendar no novo horário: {res_agendar['message']}\nA vistoria original foi cancelada. Por favor, tente agendar manualmente se necessário ou verifique a disponibilidade.")

        self._carregar_agenda_do_vistoriador() # Recarrega a lista
        self.btn_toggle_reagendar_form.setChecked(False) # Oculta o formulário de reagendamento


    def _setup_disponibilidade_tab_content(self, parent_tab_widget: QWidget) -> None:
        """
        Configura o conteúdo da aba "Configurar Disponibilidade".

        Permite adicionar/remover horários fixos e adicionar horários avulsos.

        Args:
            parent_tab_widget (QWidget): O widget da aba onde o conteúdo será inserido.
        """
        tab_layout = self._rebuild_widget_layout(parent_tab_widget, QVBoxLayout, default_spacing=20)
        tab_layout.setAlignment(Qt.AlignTop) # Alinha ao topo

        # --- Grupo para Horários Fixos ---
        fixed_hours_group = QGroupBox("Horários de Trabalho Fixos")
        fixed_hours_group.setStyleSheet(styles.GROUP_BOX_TITLE_STYLE)
        fixed_hours_content_layout = QVBoxLayout() # Layout interno do grupo
        fixed_hours_group.setLayout(fixed_hours_content_layout)
        fixed_hours_content_layout.setSpacing(10)

        fixed_hours_content_layout.addWidget(QLabel("Horários Fixos Atuais:"))
        self.lista_horarios_fixos_atuais = QListWidget() # Lista para mostrar horários fixos
        self.lista_horarios_fixos_atuais.setMinimumHeight(120)
        self.lista_horarios_fixos_atuais.setMaximumHeight(200) # Limita altura
        self.lista_horarios_fixos_atuais.setStyleSheet(f"QListWidget {{background-color: {styles.COLOR_BACKGROUND_INPUT};}}")
        fixed_hours_content_layout.addWidget(self.lista_horarios_fixos_atuais)

        btn_remover_fixo = QPushButton("Remover Horário Fixo Selecionado")
        btn_remover_fixo.setStyleSheet(styles.DANGER_BUTTON_STYLE)
        btn_remover_fixo.clicked.connect(self._handle_remover_horario_fixo_action)
        fixed_hours_content_layout.addWidget(btn_remover_fixo)

        fixed_hours_content_layout.addWidget(self._criar_separador_horizontal()) # Separador

        # Formulário para adicionar novo horário fixo
        add_fixed_form = QFormLayout()
        add_fixed_form.setSpacing(10)
        self.combo_dias_semana_fixo = QComboBox() # Selecionar dia da semana
        self.combo_dias_semana_fixo.addItems([
            "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
            "Sexta-feira", "Sábado", "Domingo"
        ])
        add_fixed_form.addRow("Adicionar para o Dia:", self.combo_dias_semana_fixo)
        self.horario_fixo_input_novo = QLineEdit() # Input para o horário (HH:MM)
        self.horario_fixo_input_novo.setPlaceholderText("HH:MM (Ex: 09:00)")
        self.horario_fixo_input_novo.setInputMask("##:##") # Máscara para HH:MM
        add_fixed_form.addRow("Novo Horário Fixo:", self.horario_fixo_input_novo)
        btn_add_fixo = QPushButton("Adicionar Horário Fixo")
        btn_add_fixo.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        btn_add_fixo.clicked.connect(self._handle_adicionar_horario_fixo_action)
        add_fixed_form.addRow(btn_add_fixo)
        fixed_hours_content_layout.addLayout(add_fixed_form)
        tab_layout.addWidget(fixed_hours_group)

        # --- Grupo para Horários Avulsos ---
        adhoc_hours_group = QGroupBox("Adicionar Disponibilidade Avulsa na Agenda")
        adhoc_hours_group.setStyleSheet(styles.GROUP_BOX_TITLE_STYLE)
        adhoc_hours_content_layout = QFormLayout() # Layout interno do grupo
        adhoc_hours_group.setLayout(adhoc_hours_content_layout)
        adhoc_hours_content_layout.setSpacing(10)

        self.data_avulsa_input_novo = QDateEdit(QDate.currentDate()) # Selecionar data
        self.data_avulsa_input_novo.setCalendarPopup(True)
        self.data_avulsa_input_novo.setDisplayFormat("dd/MM/yyyy")
        adhoc_hours_content_layout.addRow("Data:", self.data_avulsa_input_novo)

        self.hora_avulsa_input_novo = QLineEdit() # Input para horário avulso (HH:MM)
        self.hora_avulsa_input_novo.setPlaceholderText("HH:MM (Ex: 14:30)")
        self.hora_avulsa_input_novo.setInputMask("##:##")
        adhoc_hours_content_layout.addRow("Hora:", self.hora_avulsa_input_novo)

        btn_add_avulso = QPushButton("Adicionar Horário Avulso na Agenda")
        btn_add_avulso.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        btn_add_avulso.clicked.connect(self._handle_adicionar_horario_avulso_action)
        adhoc_hours_content_layout.addRow(btn_add_avulso)
        tab_layout.addWidget(adhoc_hours_group)

        # Botão para gerar/atualizar a agenda com base nos horários fixos (ação global)
        btn_gerar_agenda = QPushButton("Gerar/Atualizar Agenda (com base nos horários fixos)")
        btn_gerar_agenda.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        btn_gerar_agenda.setFixedHeight(40)
        btn_gerar_agenda.setToolTip("Popula a agenda com os horários fixos definidos para todos os vistoriadores.")
        btn_gerar_agenda.clicked.connect(self._handle_gerar_agenda_action)
        tab_layout.addWidget(btn_gerar_agenda, 0, Qt.AlignCenter) # Adiciona com alinhamento central

        tab_layout.addStretch() # Empurra conteúdo para cima


    def _carregar_horarios_fixos_atuais(self) -> None:
        """
        Carrega e exibe os horários de trabalho fixos do vistoriador selecionado.
        """
        self.lista_horarios_fixos_atuais.clear() # Limpa lista
        if not self.selected_vistoriador_id: return # Sai se nenhum vistoriador selecionado

        horarios = self.admin_controller.listar_horarios_fixos_de_vistoriador(self.selected_vistoriador_id)
        if not horarios:
            self.lista_horarios_fixos_atuais.addItem("Nenhum horário fixo cadastrado.")
            return

        for hf_data in horarios: # Itera sobre os horários fixos
            dia_num_str = hf_data['dia_semana'] # Dia da semana como string numérica (ex: '1' para Segunda)
            # Mapeia o número do dia para o nome por extenso
            map_db_to_display_day = {'1': 'Segunda-feira', '2': 'Terça-feira', '3': 'Quarta-feira',
                                     '4': 'Quinta-feira', '5': 'Sexta-feira', '6': 'Sábado', '0': 'Domingo'}
            dia_display = map_db_to_display_day.get(dia_num_str, f"Dia ({dia_num_str}) Inválido")

            horario_formatado = helpers.formatar_horario_para_exibicao(hf_data['horario'])
            item_text = f"{dia_display} às {horario_formatado}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, hf_data) # Armazena os dados completos do horário fixo no item
            self.lista_horarios_fixos_atuais.addItem(item)


    def _handle_adicionar_horario_fixo_action(self) -> None:
        """
        Manipula a ação de adicionar um novo horário fixo para o vistoriador.
        """
        if not self.selected_vistoriador_id:
            QMessageBox.warning(self, "Erro", "Nenhum vistoriador selecionado.")
            return

        # Mapeia o nome do dia selecionado no combo para o valor numérico do banco
        map_display_to_db_day = {'Segunda-feira': '1', 'Terça-feira': '2', 'Quarta-feira': '3',
                                 'Quinta-feira': '4', 'Sexta-feira': '5', 'Sábado': '6', 'Domingo': '0'}
        dia_semana_display = self.combo_dias_semana_fixo.currentText()
        dia_semana_db_val = map_display_to_db_day[dia_semana_display]

        horario_str = self.horario_fixo_input_novo.text().strip() # Pega o horário do input

        # Valida o formato do horário
        if not validators.is_valid_date_format(horario_str, "%H:%M", allow_empty=False):
            QMessageBox.warning(self, "Formato Inválido", "Horário deve ser no formato HH:MM (ex: 09:00).")
            return

        # Chama o controller para adicionar
        resultado = self.admin_controller.adicionar_horarios_fixos_para_vistoriador(
            self.selected_vistoriador_id, [dia_semana_db_val], [horario_str] # Controller espera listas
        )
        if resultado['success']:
            QMessageBox.information(self, "Sucesso", resultado['message'])
            self._carregar_horarios_fixos_atuais() # Recarrega a lista de horários fixos
            self.horario_fixo_input_novo.clear() # Limpa o campo de input
        else:
            QMessageBox.warning(self, "Erro", resultado['message'])


    def _handle_remover_horario_fixo_action(self) -> None:
        """
        Manipula a ação de remover um horário fixo selecionado da lista.
        """
        if not self.selected_vistoriador_id:
            QMessageBox.warning(self, "Erro", "Nenhum vistoriador selecionado.")
            return

        selected_item = self.lista_horarios_fixos_atuais.currentItem() # Pega o item selecionado
        if not selected_item:
            QMessageBox.warning(self, "Seleção Necessária", "Selecione um horário fixo da lista para remover.")
            return

        hf_data = selected_item.data(Qt.UserRole) # Pega os dados do horário fixo armazenados no item
        dia_semana_db_val = hf_data['dia_semana']
        horario_str = hf_data['horario']

        confirm = QMessageBox.question(self, "Confirmar Remoção",
                                       f"Tem certeza que deseja remover o horário fixo: {selected_item.text()}?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            resultado = self.admin_controller.remover_horario_fixo_vistoriador(
                self.selected_vistoriador_id, dia_semana_db_val, horario_str
            )
            if resultado['success']:
                QMessageBox.information(self, "Sucesso", resultado['message'])
                self._carregar_horarios_fixos_atuais() # Recarrega
            else:
                QMessageBox.warning(self, "Erro", resultado['message'])

    def _handle_adicionar_horario_avulso_action(self) -> None:
        """
        Manipula a ação de adicionar um horário de disponibilidade avulso na agenda do vistoriador.
        """
        if not self.selected_vistoriador_id:
            QMessageBox.warning(self, "Erro", "Nenhum vistoriador selecionado.")
            return

        data_qdate = self.data_avulsa_input_novo.date() # Pega a data do QDateEdit
        data_str_ddmmyyyy = data_qdate.toString("dd/MM/yyyy") # Formata para dd/MM/yyyy
        hora_str = self.hora_avulsa_input_novo.text().strip() # Pega a hora do input

        # Valida formato da hora
        if not validators.is_valid_date_format(hora_str, "%H:%M", allow_empty=False):
            QMessageBox.warning(self, "Formato Inválido", "Hora avulsa deve ser no formato HH:MM (ex: 14:30).")
            return

        # Chama o controller para adicionar o horário avulso
        resultado = self.admin_controller.adicionar_horario_avulso_para_vistoriador(
            self.selected_vistoriador_id, data_str_ddmmyyyy, hora_str
        )
        if resultado['success']:
            QMessageBox.information(self, "Sucesso", resultado['message'])
            self.hora_avulsa_input_novo.clear() # Limpa o campo de hora
            # Se a aba de agenda estiver visível, recarrega-a para mostrar o novo horário avulso
            if hasattr(self, 'tab_widget') and self.tab_widget.currentIndex() == 0:
                self._carregar_agenda_do_vistoriador()
        else:
            QMessageBox.warning(self, "Erro", resultado['message'])


    def _handle_gerar_agenda_action(self) -> None:
        """
        Manipula a ação de disparar a geração/atualização da agenda para todos
        os vistoriadores com base em seus horários fixos.
        """
        confirm = QMessageBox.question(self, "Gerar Agenda Automática",
                                       "Isso irá popular a agenda com base nos horários fixos definidos para todos os vistoriadores. Horários já existentes na agenda não serão duplicados.\n\nDeseja continuar?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm == QMessageBox.Yes:
            resultado = self.agenda_controller.disparar_geracao_agenda_automatica()
            if resultado['success']:
                QMessageBox.information(self, "Sucesso", resultado['message'])
                # Se um vistoriador estiver selecionado e a aba de agenda estiver visível, recarrega
                if self.selected_vistoriador_id and hasattr(self, 'tab_widget') and self.tab_widget.currentIndex() == 0:
                    self._carregar_agenda_do_vistoriador()
            else:
                QMessageBox.warning(self, "Erro", resultado['message'])

    def _criar_separador_horizontal(self) -> QFrame:
        """
        Cria um widget QFrame para ser usado como separador visual horizontal.

        Returns:
            QFrame: O widget separador configurado.
        """
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine) # Linha horizontal
        separator.setFrameShadow(QFrame.Sunken) # Efeito de sombra
        separator.setStyleSheet(f"border-color: {styles.COLOR_BORDER_MEDIUM}; margin-top: 5px; margin-bottom: 5px;") # Estilo
        return separator
