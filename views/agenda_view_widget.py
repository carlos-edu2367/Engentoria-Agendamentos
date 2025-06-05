# engentoria/views/agenda_view_widget.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QComboBox, QLineEdit, QFormLayout, QMessageBox,
    QStackedWidget, QScrollArea, QFrame, QDialog, QTextEdit, QCheckBox,
    QApplication, QMainWindow, QCompleter
)
from PyQt5.QtGui import QFont, QColor, QIcon, QDoubleValidator
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QStringListModel
import datetime

from controllers.agenda_controller import AgendaController
from controllers.admin_controller import AdminController # Usado para buscar clientes/imobiliárias, pode ser refatorado no controller da agenda
from utils import styles, validators, helpers
from typing import Optional, Dict, Any, List

class AgendaViewWidget(QWidget):
    """
    Widget para a página de Gerenciamento de Agenda.

    Permite que usuários (administradores ou com permissão) visualizem horários
    disponíveis, selecionem clientes, imobiliárias e cadastrem os dados
    de um imóvel para finalizar um agendamento de vistoria.
    Utiliza um QStackedWidget para navegar entre as etapas do agendamento.
    """
    navegacao_solicitada = pyqtSignal(int) # Sinal para navegação (se usado externamente)

    def __init__(self, user_id: int, user_type: str, parent: Optional[QWidget] = None):
        """
        Construtor da AgendaViewWidget.

        Args:
            user_id (int): ID do usuário logado.
            user_type (str): Tipo do usuário logado.
            parent (Optional[QWidget]): Widget pai, se houver.
        """
        super().__init__(parent)
        self.user_id = user_id # ID do usuário que está realizando o agendamento
        self.user_type = user_type # Tipo do usuário (ex: 'adm')
        self.agenda_controller = AgendaController() # Controller para lógica de agendamentos
        self.admin_controller = AdminController() # Controller para buscar entidades como clientes e imobiliárias

        # --- Atributos para armazenar seleções durante o fluxo de agendamento ---
        self.id_horario_selecionado: Optional[int] = None # ID do slot de agenda escolhido
        self.id_cliente_selecionado: Optional[int] = None # ID do cliente selecionado para o agendamento
        self.id_imobiliaria_selecionada: Optional[int] = None # ID da imobiliária selecionada
        self.dados_novo_imovel: Optional[Dict[str, Any]] = None # Dados do imóvel (não usado diretamente, o cadastro é feito em etapas)
        self.clientes_data_list: List[Dict[str, Any]] = [] # Cache da lista de clientes para o QCompleter

        self._init_ui()

    def _init_ui(self) -> None:
        """
        Inicializa a interface do usuário principal da agenda.

        Configura o layout, o título e o QStackedWidget que gerencia
        as diferentes páginas/etapas do processo de agendamento.
        """
        self.main_layout = QVBoxLayout(self) # Layout principal vertical
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        self.main_layout.setAlignment(Qt.AlignTop)

        title_label = QLabel("Gerenciamento de Agenda")
        title_label.setStyleSheet(styles.PAGE_TITLE_STYLE)
        self.main_layout.addWidget(title_label)

        # QStackedWidget para alternar entre a lista de horários e o formulário de agendamento
        self.view_stack = QStackedWidget()
        self.main_layout.addWidget(self.view_stack)

        # Página 1: Lista de horários disponíveis
        self.pagina_lista_horarios = QWidget()
        self._setup_pagina_lista_horarios() # Configura o conteúdo desta página
        self.view_stack.addWidget(self.pagina_lista_horarios)

        # Página 2: Formulário de múltiplas etapas para o agendamento
        self.pagina_form_agendamento = QWidget()
        self._setup_pagina_form_agendamento() # Configura o conteúdo desta página
        self.view_stack.addWidget(self.pagina_form_agendamento)

        self.view_stack.setCurrentWidget(self.pagina_lista_horarios) # Começa mostrando a lista de horários
        self._carregar_horarios_disponiveis() # Carrega os dados iniciais da lista

    def _setup_pagina_lista_horarios(self) -> None:
        """
        Configura a interface da página que exibe a lista de horários disponíveis.

        Inclui filtros por período, a lista de horários e um botão para prosseguir.
        """
        layout_lista = QVBoxLayout(self.pagina_lista_horarios) # Layout para esta página
        layout_lista.setSpacing(15)

        # Barra de filtros
        filter_bar = QHBoxLayout()
        lbl_filtro_horarios = QLabel("Filtrar Horários Por Período:")
        lbl_filtro_horarios.setStyleSheet(styles.INFO_TEXT_STYLE)
        self.combo_filtro_periodo_horarios = QComboBox()
        self.combo_filtro_periodo_horarios.addItems([
            "Todos os horários", "Hoje", "Amanhã", "Esta semana", "Próximas 2 semanas"
        ])
        self.combo_filtro_periodo_horarios.currentIndexChanged.connect(self._carregar_horarios_disponiveis) # Recarrega ao mudar filtro
        btn_atualizar_horarios = QPushButton("🔄 Atualizar")
        btn_atualizar_horarios.setStyleSheet(styles.SECONDARY_BUTTON_STYLE)
        btn_atualizar_horarios.clicked.connect(self._carregar_horarios_disponiveis) # Botão de atualização manual
        filter_bar.addWidget(lbl_filtro_horarios)
        filter_bar.addWidget(self.combo_filtro_periodo_horarios)
        filter_bar.addStretch()
        filter_bar.addWidget(btn_atualizar_horarios)
        layout_lista.addLayout(filter_bar)

        # Lista de horários
        self.lista_horarios_widget = QListWidget()
        self.lista_horarios_widget.setStyleSheet(styles.LIST_WIDGET_ITEM_SELECTED_GREEN) # Estilo para item selecionado
        self.lista_horarios_widget.itemClicked.connect(self._on_horario_selecionado_lista) # Ao clicar, armazena o ID
        layout_lista.addWidget(self.lista_horarios_widget)

        # Botão para iniciar o agendamento
        self.btn_iniciar_agendamento = QPushButton(" Prosseguir para Agendamento")
        self.btn_iniciar_agendamento.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        self.btn_iniciar_agendamento.setEnabled(False) # Habilitado apenas quando um horário é selecionado
        self.btn_iniciar_agendamento.clicked.connect(self._iniciar_fluxo_agendamento)
        layout_lista.addWidget(self.btn_iniciar_agendamento, alignment=Qt.AlignRight)

    def _carregar_horarios_disponiveis(self) -> None:
        """
        Carrega os horários disponíveis do controller e os exibe na lista.

        Aplica o filtro de período selecionado no QComboBox.
        """
        self.lista_horarios_widget.clear()
        self.id_horario_selecionado = None # Reseta a seleção
        self.btn_iniciar_agendamento.setEnabled(False) # Desabilita o botão de prosseguir

        filtro = self.combo_filtro_periodo_horarios.currentText() # Obtém o filtro selecionado
        horarios = self.agenda_controller.listar_horarios_para_agendamento_geral(filtro_periodo=filtro)

        if not horarios:
            self.lista_horarios_widget.addItem("Nenhum horário disponível para o período selecionado.")
            return

        for horario_data in horarios:
            data_formatada = helpers.formatar_data_para_exibicao(horario_data['data'])
            dia_semana = helpers.traduzir_dia_semana(datetime.datetime.strptime(horario_data['data'], "%Y-%m-%d").strftime("%A"), abreviado=True)
            texto_item = (f"{dia_semana} {data_formatada} às {horario_data['horario']} "
                          f"(Vistoriador: {horario_data['nome_vistoriador']})")
            item = QListWidgetItem(texto_item)
            item.setData(Qt.UserRole, horario_data['id_agenda']) # Armazena o ID da agenda no item
            self.lista_horarios_widget.addItem(item)

    def _on_horario_selecionado_lista(self, item: QListWidgetItem) -> None:
        """
        Chamado quando um item da lista de horários é clicado.

        Armazena o ID do horário selecionado e habilita o botão de prosseguir.

        Args:
            item (QListWidgetItem): O item da lista que foi clicado.
        """
        self.id_horario_selecionado = item.data(Qt.UserRole)
        self.btn_iniciar_agendamento.setEnabled(True)
        print(f"Horário ID {self.id_horario_selecionado} selecionado.")

    def _iniciar_fluxo_agendamento(self) -> None:
        """
        Inicia o fluxo de agendamento após um horário ser selecionado.

        Muda para a página de formulário e redefine os IDs de cliente e imobiliária.
        """
        if self.id_horario_selecionado is None:
            QMessageBox.warning(self, "Seleção Necessária", "Por favor, selecione um horário da lista.")
            return

        # Reseta seleções anteriores de outras etapas
        self.id_cliente_selecionado = None
        self.id_imobiliaria_selecionada = None
        self.dados_novo_imovel = None # Não é usado diretamente, mas para consistência

        self.view_stack.setCurrentWidget(self.pagina_form_agendamento) # Muda para a página do formulário
        self.form_agendamento_stack.setCurrentIndex(0) # Garante que o formulário comece na primeira etapa (seleção de cliente)
        self._carregar_clientes_para_selecao() # Carrega os clientes para a primeira etapa

    def _setup_pagina_form_agendamento(self) -> None:
        """
        Configura a página que contém o formulário de múltiplas etapas (QStackedWidget).
        """
        layout_form_principal = QVBoxLayout(self.pagina_form_agendamento)
        # Este QStackedWidget interno gerenciará as etapas do formulário: cliente, imobiliária, imóvel.
        self.form_agendamento_stack = QStackedWidget()
        layout_form_principal.addWidget(self.form_agendamento_stack)

        # Cria e adiciona cada etapa ao stack do formulário
        self.etapa_cliente_widget = self._criar_etapa_selecao_cliente()
        self.form_agendamento_stack.addWidget(self.etapa_cliente_widget)

        self.etapa_imobiliaria_widget = self._criar_etapa_selecao_imobiliaria()
        self.form_agendamento_stack.addWidget(self.etapa_imobiliaria_widget)

        self.etapa_imovel_widget = self._criar_etapa_cadastro_imovel()
        self.form_agendamento_stack.addWidget(self.etapa_imovel_widget)

    def _criar_etapa_selecao_cliente(self) -> QWidget:
        """
        Cria o widget para a primeira etapa do formulário: Seleção de Cliente.

        Returns:
            QWidget: O widget configurado para esta etapa.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        lbl_etapa_cliente = QLabel("Etapa 1: Selecionar Cliente")
        lbl_etapa_cliente.setStyleSheet(styles.SUBTITLE_LABEL_STYLE)
        layout.addWidget(lbl_etapa_cliente)

        # QComboBox para seleção/pesquisa de clientes
        self.combo_clientes_agendamento = QComboBox()
        self.combo_clientes_agendamento.setEditable(True) # Permite digitação para pesquisa
        self.combo_clientes_agendamento.setInsertPolicy(QComboBox.NoInsert) # Não insere texto digitado como novo item
        self.combo_clientes_agendamento.lineEdit().setPlaceholderText("Digite para pesquisar o cliente...")

        # Configuração do QCompleter para auto-completar a pesquisa de clientes
        self.client_completer_model = QStringListModel()
        self.client_completer = QCompleter(self.client_completer_model, self)
        self.client_completer.setCaseSensitivity(Qt.CaseInsensitive) # Ignora maiúsculas/minúsculas
        self.client_completer.setFilterMode(Qt.MatchContains) # Procura texto em qualquer parte
        self.combo_clientes_agendamento.setCompleter(self.client_completer)

        # Conecta o sinal 'activated' que é emitido quando um item é selecionado (clique ou Enter)
        self.combo_clientes_agendamento.activated[str].connect(self._on_cliente_selecionado_combo)

        layout.addWidget(QLabel("Selecione ou Pesquise o Cliente:"))
        layout.addWidget(self.combo_clientes_agendamento)

        # Botões de navegação da etapa
        btn_proximo_cliente = QPushButton("Próximo ")
        btn_proximo_cliente.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        btn_proximo_cliente.clicked.connect(self._avancar_para_etapa_imobiliaria)

        btn_voltar_lista_horarios = QPushButton(" Voltar para Horários")
        btn_voltar_lista_horarios.setStyleSheet(styles.SECONDARY_BUTTON_STYLE)
        btn_voltar_lista_horarios.clicked.connect(self._voltar_para_lista_horarios)

        botoes_layout = QHBoxLayout()
        botoes_layout.addWidget(btn_voltar_lista_horarios)
        botoes_layout.addStretch()
        botoes_layout.addWidget(btn_proximo_cliente)
        layout.addLayout(botoes_layout)
        layout.addStretch() # Empurra conteúdo para cima
        return widget

    def _carregar_clientes_para_selecao(self) -> None:
        """
        Carrega a lista de clientes do controller e popula o QComboBox e o QCompleter.
        """
        self.clientes_data_list = self.agenda_controller.obter_clientes_para_selecao()

        self.combo_clientes_agendamento.blockSignals(True) # Evita disparar sinais durante o preenchimento
        self.combo_clientes_agendamento.clear() # Limpa itens antigos

        client_display_list = [] # Lista de strings para o QCompleter
        self.combo_clientes_agendamento.addItem("-- Selecione ou Pesquise --", None) # Item placeholder
        for cliente in self.clientes_data_list:
            display_text = f"{cliente['nome']} (Email: {cliente['email']})"
            self.combo_clientes_agendamento.addItem(display_text, cliente['id']) # Texto e ID do cliente
            client_display_list.append(display_text)

        self.client_completer_model.setStringList(client_display_list) # Define os dados do QCompleter
        self.id_cliente_selecionado = None # Reseta a seleção
        self.combo_clientes_agendamento.setCurrentIndex(0) # Seleciona o placeholder
        self.combo_clientes_agendamento.lineEdit().setText("") # Limpa o texto do editor do combo
        self.combo_clientes_agendamento.blockSignals(False) # Reabilita sinais

    def _on_cliente_selecionado_combo(self, text: str) -> None:
        """
        Chamado quando um cliente é selecionado no QComboBox (via clique ou completer).

        Args:
            text (str): O texto do item selecionado no QComboBox.
        """
        current_index = self.combo_clientes_agendamento.findText(text)
        if current_index != -1 and self.combo_clientes_agendamento.itemData(current_index) is not None:
            # Garante que não é o item placeholder "-- Selecione ou Pesquise --"
            self.id_cliente_selecionado = self.combo_clientes_agendamento.itemData(current_index)
            # Garante que o texto exibido no QLineEdit do combo seja o texto completo do item selecionado,
            # especialmente útil se o usuário selecionou via completer com texto parcial.
            self.combo_clientes_agendamento.setCurrentText(self.combo_clientes_agendamento.itemText(current_index))
            print(f"Cliente ID {self.id_cliente_selecionado} selecionado via combo/completer: {text}")
        else:
            # Se o texto não corresponde a um item válido (ex: usuário digitou algo novo e não selecionou do completer)
            # ou se o placeholder foi "ativado" (pouco comum com 'activated', mais com 'currentIndexChanged').
            self.id_cliente_selecionado = None
            # Não limpa o texto do QLineEdit aqui, pois o usuário pode ainda estar digitando.
            # A validação final e a obtenção do ID, se o usuário digitou um nome completo,
            # ocorrerá no método _avancar_para_etapa_imobiliaria.
            print(f"Texto no combo de cliente alterado/selecionado: {text}, ID do cliente atualmente selecionado: {self.id_cliente_selecionado}")


    def _avancar_para_etapa_imobiliaria(self) -> None:
        """
        Valida a seleção do cliente e avança para a etapa de seleção de imobiliária.

        Se o usuário digitou um nome completo que corresponde a um cliente,
        tenta obter o ID desse cliente.
        """
        # Se um ID de cliente já foi definido (por exemplo, por uma seleção explícita no dropdown do QComboBox
        # ou via QCompleter que disparou _on_cliente_selecionado_combo), usa esse ID.
        if self.id_cliente_selecionado is not None:
            # Verifica se o texto atual no QLineEdit do combo corresponde ao item do id_cliente_selecionado.
            # Isso é uma segurança, caso o usuário tenha selecionado um item e depois editado o texto sem selecionar outro.
            idx_stored_id = self.combo_clientes_agendamento.findData(self.id_cliente_selecionado)
            if idx_stored_id != -1 and self.combo_clientes_agendamento.itemText(idx_stored_id) == self.combo_clientes_agendamento.lineEdit().text():
                pass # O ID armazenado e o texto são consistentes.
            else:
                # O texto foi alterado após uma seleção. Tentaremos revalidar pelo texto.
                self.id_cliente_selecionado = None # Invalida o ID antigo.

        # Se o id_cliente_selecionado ainda é None (nenhuma seleção válida via dropdown/completer ou invalidado acima),
        # tenta encontrar um cliente cujo texto de exibição corresponda exatamente ao que está no QLineEdit do combo.
        if self.id_cliente_selecionado is None:
            current_text_in_editor = self.combo_clientes_agendamento.lineEdit().text()
            found_match = False
            for cliente_data in self.clientes_data_list: # Itera sobre a lista de dados dos clientes (cache)
                display_text_for_cliente = f"{cliente_data['nome']} (Email: {cliente_data['email']})"
                if display_text_for_cliente == current_text_in_editor:
                    self.id_cliente_selecionado = cliente_data['id']
                    # Se encontrou, atualiza o índice do combo para refletir essa "seleção por texto"
                    # Isso garante que combo_clientes_agendamento.currentData() retornaria o ID correto.
                    idx = self.combo_clientes_agendamento.findText(display_text_for_cliente)
                    if idx != -1:
                        self.combo_clientes_agendamento.setCurrentIndex(idx)
                    found_match = True
                    break
            if not found_match:
                QMessageBox.warning(self, "Seleção Necessária", "Por favor, selecione um cliente válido da lista ou da pesquisa.")
                self.combo_clientes_agendamento.lineEdit().selectAll()
                self.combo_clientes_agendamento.lineEdit().setFocus()
                return

        # Se chegou aqui, self.id_cliente_selecionado deve ser válido.
        print(f"Cliente ID {self.id_cliente_selecionado} confirmado para avançar.")
        self.form_agendamento_stack.setCurrentIndex(1) # Vai para a etapa de imobiliária
        self._carregar_imobiliarias_para_selecao()


    def _criar_etapa_selecao_imobiliaria(self) -> QWidget:
        """
        Cria o widget para a segunda etapa do formulário: Seleção de Imobiliária.

        Returns:
            QWidget: O widget configurado para esta etapa.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)

        lbl_etapa_imobiliaria = QLabel("Etapa 2: Selecionar Imobiliária")
        lbl_etapa_imobiliaria.setStyleSheet(styles.SUBTITLE_LABEL_STYLE)
        layout.addWidget(lbl_etapa_imobiliaria)

        self.combo_imobiliarias_agendamento = QComboBox()
        layout.addWidget(QLabel("Selecione a Imobiliária:"))
        layout.addWidget(self.combo_imobiliarias_agendamento)

        # Botões de navegação
        btn_proximo_imob = QPushButton("Próximo ")
        btn_proximo_imob.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        btn_proximo_imob.clicked.connect(self._avancar_para_etapa_imovel)

        btn_voltar_cliente = QPushButton(" Voltar para Cliente")
        btn_voltar_cliente.setStyleSheet(styles.SECONDARY_BUTTON_STYLE)
        btn_voltar_cliente.clicked.connect(lambda: self.form_agendamento_stack.setCurrentIndex(0)) # Volta para etapa anterior

        botoes_layout = QHBoxLayout()
        botoes_layout.addWidget(btn_voltar_cliente)
        botoes_layout.addStretch()
        botoes_layout.addWidget(btn_proximo_imob)
        layout.addLayout(botoes_layout)
        layout.addStretch()
        return widget

    def _carregar_imobiliarias_para_selecao(self) -> None:
        """
        Carrega a lista de imobiliárias do controller e popula o QComboBox.
        """
        self.combo_imobiliarias_agendamento.clear()
        self.combo_imobiliarias_agendamento.addItem("-- Selecione uma Imobiliária --", None) # Placeholder
        imobiliarias = self.agenda_controller.obter_imobiliarias_para_selecao() # Busca dados do controller
        for imob in imobiliarias:
            self.combo_imobiliarias_agendamento.addItem(imob['nome'], imob['id']) # Texto e ID

    def _avancar_para_etapa_imovel(self) -> None:
        """
        Valida a seleção da imobiliária e avança para a etapa de cadastro do imóvel.
        """
        self.id_imobiliaria_selecionada = self.combo_imobiliarias_agendamento.currentData() # Pega o ID do item selecionado
        if self.id_imobiliaria_selecionada is None:
            QMessageBox.warning(self, "Seleção Necessária", "Por favor, selecione uma imobiliária.")
            return

        print(f"Imobiliária ID {self.id_imobiliaria_selecionada} selecionada.")
        self.form_agendamento_stack.setCurrentIndex(2) # Avança para a etapa de cadastro do imóvel

        # Limpa os campos do formulário do imóvel para nova entrada
        self.cod_imovel_input.clear()
        self.endereco_input.clear()
        self.cep_input.clear()
        self.referencia_input.clear()
        self.tamanho_input.clear()
        self.tipo_mobilia_combo.setCurrentIndex(0) # Reseta para o primeiro item
        self.tipo_vistoria_combo.setCurrentIndex(0) # Reseta para o primeiro item

    def _criar_etapa_cadastro_imovel(self) -> QWidget:
        """
        Cria o widget para a terceira etapa do formulário: Dados do Imóvel e Vistoria.

        Usa um QScrollArea para acomodar todos os campos caso a tela seja pequena.

        Returns:
            QWidget: O widget configurado para esta etapa.
        """
        widget = QWidget() # Widget principal da etapa
        main_layout_etapa = QVBoxLayout(widget) # Layout principal para o título e o scroll area

        lbl_etapa_imovel = QLabel("Etapa 3: Dados do Imóvel e Vistoria")
        lbl_etapa_imovel.setStyleSheet(styles.SUBTITLE_LABEL_STYLE)
        main_layout_etapa.addWidget(lbl_etapa_imovel)

        # ScrollArea para o formulário
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True) # Permite que o widget interno redimensione com o scroll area
        scroll_area.setStyleSheet("QScrollArea { border: none; }") # Remove bordas padrão

        content_widget = QWidget() # Widget que irá DENTRO do scroll area e conterá o QFormLayout
        layout = QFormLayout(content_widget) # Layout para os campos do formulário (label: input)
        layout.setSpacing(15)
        layout.setContentsMargins(10,10,10,10)

        # Campos do formulário
        self.cod_imovel_input = QLineEdit()
        self.cod_imovel_input.setPlaceholderText("Código único do imóvel (Ex: APT101)")
        layout.addRow("Código do Imóvel:*", self.cod_imovel_input)

        self.endereco_input = QLineEdit()
        self.endereco_input.setPlaceholderText("Rua, Número, Bairro, Cidade")
        layout.addRow("Endereço Completo:*", self.endereco_input)

        self.cep_input = QLineEdit()
        self.cep_input.setPlaceholderText("XXXXX-XXX (Opcional)")
        # self.cep_input.setInputMask("00000-000;_") # Exemplo de máscara de CEP
        layout.addRow("CEP:", self.cep_input)

        self.referencia_input = QLineEdit()
        self.referencia_input.setPlaceholderText("Próximo ao shopping, etc. (Opcional)")
        layout.addRow("Ponto de Referência:", self.referencia_input)

        self.tamanho_input = QLineEdit()
        self.tamanho_input.setPlaceholderText("Ex: 75.5 (em m²)")
        self.tamanho_input.setValidator(QDoubleValidator(0.01, 99999.99, 2)) # Validador para float positivo com 2 casas decimais
        layout.addRow("Tamanho (m²):*", self.tamanho_input)

        self.tipo_mobilia_combo = QComboBox()
        self.tipo_mobilia_combo.addItems(["sem_mobilia", "semi_mobiliado", "mobiliado"])
        layout.addRow("Tipo de Mobília:", self.tipo_mobilia_combo)

        self.tipo_vistoria_combo = QComboBox()
        self.tipo_vistoria_combo.addItems(["ENTRADA", "SAIDA", "CONFERENCIA"]) # Tipos de vistoria
        layout.addRow("Tipo de Vistoria:*", self.tipo_vistoria_combo)

        self.check_forcar_agendamento = QCheckBox("Forçar agendamento em horário único (se necessário)")
        self.check_forcar_agendamento.setStyleSheet("QCheckBox { font-size: 13px; }") # Estilo para o checkbox
        layout.addRow("", self.check_forcar_agendamento) # Adiciona o checkbox (sem label na frente)

        scroll_area.setWidget(content_widget) # Define o widget com o formulário DENTRO do scroll area
        main_layout_etapa.addWidget(scroll_area) # Adiciona o scroll area ao layout principal da etapa

        # Botões de ação
        btn_confirmar_agendamento = QPushButton(" Confirmar Agendamento")
        btn_confirmar_agendamento.setStyleSheet(styles.PRIMARY_BUTTON_STYLE)
        btn_confirmar_agendamento.clicked.connect(self._submeter_agendamento_final)

        btn_voltar_imobiliaria = QPushButton(" Voltar para Imobiliária")
        btn_voltar_imobiliaria.setStyleSheet(styles.SECONDARY_BUTTON_STYLE)
        btn_voltar_imobiliaria.clicked.connect(lambda: self.form_agendamento_stack.setCurrentIndex(1)) # Volta para etapa anterior

        botoes_layout = QHBoxLayout()
        botoes_layout.addWidget(btn_voltar_imobiliaria)
        botoes_layout.addStretch()
        botoes_layout.addWidget(btn_confirmar_agendamento)
        main_layout_etapa.addLayout(botoes_layout)

        return widget

    def _submeter_agendamento_final(self) -> None:
        """
        Coleta os dados do formulário do imóvel, valida-os, cadastra o imóvel (se novo)
        e finaliza o agendamento da vistoria.
        """
        # Coleta dos dados dos inputs
        cod_imovel = self.cod_imovel_input.text().strip()
        endereco = self.endereco_input.text().strip()
        cep = self.cep_input.text().strip()
        referencia = self.referencia_input.text().strip()
        tamanho_str = self.tamanho_input.text().strip().replace(',', '.') # Garante ponto decimal
        mobiliado = self.tipo_mobilia_combo.currentText()
        tipo_vistoria = self.tipo_vistoria_combo.currentText()
        forcar_unico = self.check_forcar_agendamento.isChecked()

        # Validações básicas
        if not cod_imovel or not endereco or not tamanho_str or not tipo_vistoria:
            QMessageBox.warning(self, "Campos Obrigatórios", "Código do imóvel, endereço, tamanho e tipo de vistoria são obrigatórios.")
            return
        if not validators.is_positive_float_or_int(tamanho_str): # Usando helper de validação
            QMessageBox.warning(self, "Dado Inválido", "Tamanho do imóvel deve ser um número positivo.")
            return

        print("Tentando cadastrar imóvel para agendamento...")
        # Tenta cadastrar o imóvel. O controller pode verificar se já existe um imóvel com o mesmo código
        # e cliente/imobiliária para evitar duplicatas ou permitir atualização.
        resultado_cad_imovel = self.agenda_controller.cadastrar_imovel_para_agendamento(
            cod_imovel=cod_imovel, cliente_id=self.id_cliente_selecionado,
            imobiliaria_id=self.id_imobiliaria_selecionada, endereco=endereco,
            tamanho_str=tamanho_str, cep=cep if cep else None, # Envia None se CEP estiver vazio
            referencia=referencia if referencia else None, # Envia None se referencia estiver vazia
            mobiliado=mobiliado
        )

        if not resultado_cad_imovel['success']:
            QMessageBox.warning(self, "Erro ao Cadastrar Imóvel", resultado_cad_imovel['message'])
            return

        id_imovel_cadastrado = resultado_cad_imovel['imovel_id'] # Pega o ID do imóvel (novo ou existente)
        print(f"Imóvel ID {id_imovel_cadastrado} cadastrado/obtido.")

        print(f"Finalizando agendamento para horário ID {self.id_horario_selecionado}, imóvel ID {id_imovel_cadastrado}...")
        # Chama o controller para finalizar o agendamento com todos os IDs coletados
        resultado_final = self.agenda_controller.finalizar_agendamento_vistoria(
            id_agenda_selecionada=self.id_horario_selecionado,
            imovel_id=id_imovel_cadastrado,
            tipo_vistoria=tipo_vistoria,
            forcar_agendamento_unico=forcar_unico
        )

        if resultado_final['success']:
            QMessageBox.information(self, "Sucesso", resultado_final['message'])
            self._voltar_para_lista_horarios() # Volta para a tela inicial da agenda
        else:
            QMessageBox.warning(self, "Erro no Agendamento", resultado_final['message'])

    def _voltar_para_lista_horarios(self) -> None:
        """
        Retorna para a página de lista de horários e recarrega os dados.
        """
        self.view_stack.setCurrentWidget(self.pagina_lista_horarios) # Muda para a página de lista
        self._carregar_horarios_disponiveis() # Atualiza a lista de horários


# Bloco para testar este widget isoladamente
if __name__ == '__main__':
    import sys
    import os
    # Adiciona o diretório raiz ao sys.path para encontrar os módulos
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Importações para setup do banco e dados de teste
    from models.database import criar_tabelas
    from models import usuario_model # Usado para criar clientes e vistoriadores de teste
    from models import imobiliaria_model # Usado para criar imobiliárias de teste
    from models import agenda_model # Usado para criar horários de teste

    criar_tabelas() # Garante que o banco e as tabelas existam

    # --- Criação de dados de TESTE ---
    # Tenta obter ou criar um vistoriador de teste
    id_vist_teste = None
    usuarios_vist = usuario_model.listar_usuarios_por_tipo('vistoriador')
    if usuarios_vist:
        id_vist_teste = usuarios_vist[0]['id'] # Pega o primeiro vistoriador existente
    else:
        # Cadastra um novo vistoriador se não houver nenhum
        id_vist_teste = usuario_model.cadastrar_usuario("Vist. Teste Agenda", "vist.agenda@teste.com", "123456", "vistoriador")

    if id_vist_teste:
        # Garante que o vistoriador de teste tenha horários fixos
        if not agenda_model.listar_horarios_fixos_por_vistoriador(id_vist_teste):
            agenda_model.cadastrar_horarios_fixos_vistoriador(id_vist_teste, ['1','3','5'], ['09:00', '10:00', '14:00']) # Ex: Seg, Qua, Sex
        agenda_model.gerar_agenda_baseada_em_horarios_fixos() # Gera a agenda (slots de horários)

    # Garante que existam clientes para seleção
    if not usuario_model.listar_todos_clientes():
        usuario_model.cadastrar_cliente("Cliente Padrão Agenda", "cliente.agenda@teste.com")
        usuario_model.cadastrar_cliente("Cliente Alfa Teste", "alfa@teste.com")
        usuario_model.cadastrar_cliente("Cliente Beta Pesquisa", "beta@pesquisa.com")
        usuario_model.cadastrar_cliente("Cliente Omega Final", "omega@final.com")

    # Garante que existam imobiliárias para seleção
    if not imobiliaria_model.listar_todas_imobiliarias():
        imobiliaria_model.cadastrar_imobiliaria("Imob Padrão Agenda", 10,12,15) # Nome e valores m2

    app = QApplication(sys.argv)
    # Instancia o widget da agenda para teste (simulando um usuário administrador)
    agenda_view = AgendaViewWidget(user_id=1, user_type='adm')

    # Cria uma janela principal temporária para exibir o widget
    main_window_temp = QMainWindow()
    main_window_temp.setCentralWidget(agenda_view)
    main_window_temp.setWindowTitle("Teste Agenda View Widget")
    main_window_temp.setGeometry(100, 100, 800, 600) # Posição e tamanho da janela
    main_window_temp.show()

    sys.exit(app.exec_())
