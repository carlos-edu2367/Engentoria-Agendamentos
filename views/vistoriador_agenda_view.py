# engentoria/views/vistoriador_agenda_view.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QComboBox, QScrollArea, QFrame, QMessageBox, QInputDialog,
    QTextEdit # Adicionado QTextEdit
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, QSize

from controllers.vistoriador_controller import VistoriadorController
from controllers.agenda_controller import AgendaController # Para fechar horário, se permitido
from utils import styles, helpers
import datetime # Para formatação de data/hora e manipulação de datas
from typing import List, Dict, Any, Optional

class VistoriadorAgendaViewWidget(QWidget):
    """
    Widget para a página de visualização da agenda e informações do Vistoriador.

    Exibe os próximos agendamentos do vistoriador e seus horários disponíveis.
    Permite filtrar ambos por período.
    Poderia, opcionalmente, permitir que o vistoriador fechasse seus próprios horários livres.
    """
    def __init__(self, user_id: int, user_type: str, parent: Optional[QWidget] = None):
        """
        Construtor da VistoriadorAgendaViewWidget.

        Args:
            user_id (int): ID do vistoriador logado.
            user_type (str): Tipo do usuário (deve ser 'vistoriador').
            parent (Optional[QWidget]): Widget pai, se houver.
        """
        super().__init__(parent)
        self.user_id = user_id # ID do vistoriador logado
        self.user_type = user_type # Tipo do usuário

        # Verificação de segurança: esta view é apenas para vistoriadores
        if self.user_type != 'vistoriador':
            self._show_error_page("Acesso não permitido para este tipo de usuário.")
            return

        self.vistoriador_controller = VistoriadorController(self.user_id)
        # Se o vistoriador puder fechar horários, precisaria do AgendaController
        # self.agenda_controller = AgendaController() # Descomente se necessário
        self._init_ui()
        self._carregar_dados_iniciais() # Carrega os dados da agenda ao iniciar

    def _show_error_page(self, message: str) -> None:
        """
        Exibe uma mensagem de erro centralizada se a view não puder ser carregada corretamente
        (ex: usuário não é vistoriador).
        """
        layout = QVBoxLayout(self)
        error_label = QLabel(message)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet(styles.ERROR_MESSAGE_STYLE)
        layout.addWidget(error_label)
        self.setLayout(layout)

    def _init_ui(self) -> None:
        """
        Inicializa a interface do usuário da página da agenda do vistoriador.
        """
        self.main_layout = QVBoxLayout(self) # Layout principal vertical
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)
        self.main_layout.setAlignment(Qt.AlignTop)

        # Título da Página com o nome do vistoriador
        perfil = self.vistoriador_controller.obter_meu_perfil() # Busca dados do perfil
        nome_vistoriador = perfil['nome'] if perfil else "Vistoriador"
        title_label = QLabel(f"Minha Agenda - {nome_vistoriador}")
        title_label.setStyleSheet(styles.PAGE_TITLE_STYLE)
        self.main_layout.addWidget(title_label)

        # Layout para dividir a tela em duas colunas (agendamentos e disponíveis)
        content_splitter_layout = QHBoxLayout()
        content_splitter_layout.setSpacing(20)

        # --- Painel de Agendamentos (Esquerda) ---
        agendamentos_panel = QFrame()
        agendamentos_panel.setFrameShape(QFrame.StyledPanel) # Para aplicar bordas/estilos
        agendamentos_panel.setStyleSheet(f"QFrame {{ border: 1px solid {styles.COLOR_BORDER_DARK}; border-radius: 5px; background-color: {styles.COLOR_BACKGROUND_MEDIUM};}}")
        agendamentos_layout = QVBoxLayout(agendamentos_panel) # Layout interno do painel
        agendamentos_layout.setContentsMargins(15,15,15,15)
        agendamentos_layout.setSpacing(10)

        lbl_meus_agendamentos = QLabel("Meus Próximos Agendamentos")
        lbl_meus_agendamentos.setStyleSheet(styles.SUBTITLE_LABEL_STYLE)
        agendamentos_layout.addWidget(lbl_meus_agendamentos)

        # Filtro por período para agendamentos
        self.combo_filtro_agendamentos_vist = QComboBox()
        self.combo_filtro_agendamentos_vist.addItems(["Próximos 7 dias", "Hoje", "Amanhã", "Esta semana", "Próximas 2 semanas", "Todos os agendamentos"])
        self.combo_filtro_agendamentos_vist.currentIndexChanged.connect(self._carregar_meus_agendamentos) # Recarrega ao mudar filtro
        agendamentos_layout.addWidget(self.combo_filtro_agendamentos_vist)

        self.lista_meus_agendamentos = QListWidget() # Lista para exibir os agendamentos
        self.lista_meus_agendamentos.setStyleSheet(f"""
            QListWidget {{
                background-color: {styles.COLOR_BACKGROUND_INPUT};
                border: 1px solid {styles.COLOR_BORDER_MEDIUM};
                border-radius: 5px; padding: 0px; font-size: 14px; outline: 0;
            }}
            QListWidget::item {{
                padding: 10px 8px; border-bottom: 1px solid {styles.COLOR_BORDER_DARK};
                color: {styles.COLOR_TEXT_SECONDARY}; border-radius: 4px;
            }}
            QListWidget::item:alternate {{ background-color: {styles.COLOR_BACKGROUND_LIGHT}; }}
            QListWidget::item:selected {{
                background-color: {styles.COLOR_ACCENT_PRIMARY_PRESSED}; color: {styles.COLOR_TEXT_PRIMARY};
                font-weight: bold;
            }}
            QListWidget::item:hover {{
                background-color: {styles.COLOR_ACCENT_SECONDARY_HOVER}; color: {styles.COLOR_TEXT_PRIMARY};
            }}
        """)
        self.lista_meus_agendamentos.itemClicked.connect(self._on_agendamento_selected) # Conecta o clique do item
        agendamentos_layout.addWidget(self.lista_meus_agendamentos)

        content_splitter_layout.addWidget(agendamentos_panel, 1) # Ocupa metade do espaço (fator 1)

        # --- Painel de Detalhes do Agendamento (Direita) ---
        self.detalhes_agendamento_panel = QFrame()
        self.detalhes_agendamento_panel.setFrameShape(QFrame.StyledPanel)
        self.detalhes_agendamento_panel.setStyleSheet(f"QFrame {{ border: 1px solid {styles.COLOR_BORDER_DARK}; border-radius: 5px; background-color: {styles.COLOR_BACKGROUND_MEDIUM};}}")
        detalhes_layout = QVBoxLayout(self.detalhes_agendamento_panel)
        detalhes_layout.setContentsMargins(15,15,15,15)
        detalhes_layout.setSpacing(10)

        lbl_detalhes_titulo = QLabel("Detalhes do Agendamento")
        lbl_detalhes_titulo.setStyleSheet(styles.SUBTITLE_LABEL_STYLE)
        detalhes_layout.addWidget(lbl_detalhes_titulo)

        self.detalhes_agendamento_text_edit = QTextEdit()
        self.detalhes_agendamento_text_edit.setReadOnly(True) # Apenas leitura
        self.detalhes_agendamento_text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {styles.COLOR_BACKGROUND_INPUT};
                color: {styles.COLOR_TEXT_PRIMARY};
                border: 1px solid {styles.COLOR_BORDER_MEDIUM};
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }}
        """)
        detalhes_layout.addWidget(self.detalhes_agendamento_text_edit)

        # Placeholder inicial para o painel de detalhes
        self.detalhes_placeholder_label = QLabel("Selecione um agendamento para ver os detalhes.")
        self.detalhes_placeholder_label.setAlignment(Qt.AlignCenter)
        self.detalhes_placeholder_label.setStyleSheet(f"color: {styles.COLOR_TEXT_SECONDARY}; font-size: 14px;")
        detalhes_layout.addWidget(self.detalhes_placeholder_label)

        self.detalhes_agendamento_text_edit.hide() # Esconde o QTextEdit inicialmente
        
        content_splitter_layout.addWidget(self.detalhes_agendamento_panel, 1) # Ocupa a outra metade (fator 1)

        self.main_layout.addLayout(content_splitter_layout) # Adiciona o layout das duas colunas

        # Botão para atualizar ambas as listas
        btn_atualizar_tudo = QPushButton(" Atualizar Minha Agenda")
        btn_atualizar_tudo.setStyleSheet(styles.SECONDARY_BUTTON_STYLE)
        btn_atualizar_tudo.clicked.connect(self._carregar_dados_iniciais)
        self.main_layout.addWidget(btn_atualizar_tudo, 0, Qt.AlignCenter) # Centralizado abaixo das listas


    def _carregar_dados_iniciais(self) -> None:
        """
        Carrega (ou recarrega) os dados das listas de agendamentos e horários disponíveis.
        """
        self._carregar_meus_agendamentos()
        # Limpa o painel de detalhes ao recarregar a lista
        self.detalhes_agendamento_text_edit.clear()
        self.detalhes_agendamento_text_edit.hide()
        self.detalhes_placeholder_label.show()


    def _carregar_meus_agendamentos(self) -> None:
        """
        Carrega os agendamentos do vistoriador logado do controller e os exibe na lista.
        Aplica o filtro de período selecionado.
        """
        self.lista_meus_agendamentos.clear() # Limpa a lista antes de popular
        filtro = self.combo_filtro_agendamentos_vist.currentText() # Pega o filtro de período

        # O controller.obter_minha_agenda_detalhada já usa o helpers.obter_datas_para_filtro_periodo,
        # então podemos passar o texto do filtro diretamente.
        agendamentos = self.vistoriador_controller.obter_minha_agenda_detalhada(
            filtro_periodo=filtro,
            apenas_agendados=True # Queremos apenas os que são agendamentos
        )

        if not agendamentos:
            self.lista_meus_agendamentos.addItem("Nenhum agendamento encontrado.")
            return

        for ag in agendamentos: # Itera sobre os agendamentos retornados
            data_f = helpers.formatar_data_para_exibicao(ag['data'])
            hora_f = helpers.formatar_horario_para_exibicao(ag['horario'])
            dia_semana = helpers.traduzir_dia_semana(datetime.datetime.strptime(ag['data'], "%Y-%m-%d").weekday(), abreviado=True)

            # Monta um texto resumido para o item da lista
            texto_item_resumido = (
                f"{dia_semana} {data_f} às {hora_f} - {ag['tipo_vistoria'].upper()}\n"
                f"Imóvel: {ag.get('cod_imovel', 'N/D')} | Cliente: {ag.get('nome_cliente', 'N/D')}"
            )
            
            item = QListWidgetItem(texto_item_resumido)
            item.setData(Qt.UserRole, ag) # Armazena TODOS os dados do agendamento no item
            # Não define setSizeHint aqui, permitindo que o QListWidget gerencie a altura automaticamente.
            self.lista_meus_agendamentos.addItem(item)


    def _on_agendamento_selected(self, item: QListWidgetItem) -> None:
        """
        Chamado quando um item da lista de agendamentos é selecionado.
        Exibe os detalhes completos do agendamento no QTextEdit.
        """
        ag_data = item.data(Qt.UserRole) # Recupera todos os dados do agendamento

        if not ag_data: # Se por algum motivo não houver dados
            self.detalhes_agendamento_text_edit.clear()
            self.detalhes_agendamento_text_edit.hide()
            self.detalhes_placeholder_label.show()
            return

        # Formata os detalhes para exibição no QTextEdit
        data_f = helpers.formatar_data_para_exibicao(ag_data.get('data', 'N/A'))
        hora_f = helpers.formatar_horario_para_exibicao(ag_data.get('horario', 'N/A'))
        dia_semana = helpers.traduzir_dia_semana(datetime.datetime.strptime(ag_data.get('data'), "%Y-%m-%d").weekday(), abreviado=False) # Completo

        detalhes_completos = (
            f"<b>Tipo de Vistoria:</b> {ag_data.get('tipo_vistoria', 'N/D').upper()}<br>"
            f"<b>Data:</b> {dia_semana}, {data_f} às {hora_f}<br>"
            f"<b>Vistoriador:</b> {ag_data.get('nome_vistoriador', 'N/D')}<br>"
            f"<br>"
            f"<b>--- Detalhes do Imóvel ---</b><br>"
            f"<b>Código:</b> {ag_data.get('cod_imovel', 'N/D')}<br>"
            f"<b>Endereço:</b> {ag_data.get('endereco_imovel', 'N/D')}<br>"
            f"<b>CEP:</b> {ag_data.get('cep', 'N/D')}<br>"
            f"<b>Referência:</b> {ag_data.get('referencia', 'N/D')}<br>"
            f"<b>Tamanho:</b> {ag_data.get('tamanho', 'N/D')}m²<br>"
            f"<b>Mobília:</b> {ag_data.get('mobiliado', 'N/D').replace('_', ' ').title()}<br>" # Formata para leitura
            f"<b>Imobiliária:</b> {ag_data.get('nome_imobiliaria', 'N/D')}<br>"
            f"<br>"
            f"<b>--- Detalhes do Cliente ---</b><br>"
            f"<b>Nome:</b> {ag_data.get('nome_cliente', 'N/D')}<br>"
            f"<b>Email:</b> {ag_data.get('email_cliente', 'N/D')}"
        )

        self.detalhes_agendamento_text_edit.setHtml(detalhes_completos) # Define o HTML no QTextEdit
        self.detalhes_placeholder_label.hide() # Esconde o placeholder
        self.detalhes_agendamento_text_edit.show() # Mostra o QTextEdit


    def _carregar_meus_horarios_disponiveis(self) -> None:
        """
        Carrega os horários disponíveis do vistoriador logado e os exibe na lista.
        Aplica o filtro de período selecionado.
        """
        self.lista_meus_horarios_disponiveis.clear() # Limpa a lista
        # Se o botão de fechar horário existir, desabilita-o inicialmente
        # if hasattr(self, 'btn_fechar_meu_horario'): self.btn_fechar_meu_horario.setEnabled(False)

        filtro = self.combo_filtro_disponiveis_vist.currentText() # Pega o filtro de período

        horarios = self.vistoriador_controller.obter_minha_agenda_detalhada(
            filtro_periodo=filtro,
            apenas_disponiveis=True # Queremos apenas os horários livres
        )

        if not horarios:
            self.lista_meus_horarios_disponiveis.addItem("Nenhum horário disponível encontrado.")
            return

        for h in horarios: # Itera sobre os horários disponíveis
            data_f = helpers.formatar_data_para_exibicao(h['data'])
            hora_f = helpers.formatar_horario_para_exibicao(h['horario'])
            dia_semana = helpers.traduzir_dia_semana(datetime.datetime.strptime(h['data'], "%Y-%m-%d").weekday(), abreviado=True)

            item = QListWidgetItem(f"{dia_semana} {data_f} às {hora_f}")
            item.setData(Qt.UserRole, h['id_agenda']) # Armazena o ID da agenda (do horário livre)
            self.lista_meus_horarios_disponiveis.addItem(item)

    # --- Função de Ação Opcional: Fechar Horário ---
    # Descomente e adapte se o vistoriador tiver permissão para fechar seus próprios horários.
    # def _abrir_dialogo_fechar_horario(self) -> None:
    #     """
    #     Abre um diálogo para o vistoriador inserir o motivo do fechamento de um horário.
    #     """
    #     item_selecionado = self.lista_meus_horarios_disponiveis.currentItem()
    #     if not item_selecionado or not item_selecionado.data(Qt.UserRole):
    #         QMessageBox.warning(self, "Seleção Necessária", "Selecione um horário disponível para fechar.")
    #         return

    #     id_agenda_para_fechar = item_selecionado.data(Qt.UserRole)
    #     # Pede o motivo ao usuário usando um QInputDialog
    #     motivo, ok = QInputDialog.getText(self, "Fechar Horário", "Motivo do fechamento:")

    #     if ok and motivo.strip(): # Se o usuário confirmou e inseriu um motivo
    #         # Aqui, a lógica para fechar o horário seria chamada.
    #         # O VistoriadorController poderia ter um método que chama o AgendaController,
    #         # ou esta view poderia ter uma instância do AgendaController.
    #         # Exemplo:
    #         # if not hasattr(self, 'agenda_controller'): self.agenda_controller = AgendaController()
    #         # resultado = self.agenda_controller.fechar_horario_manualmente(
    #         # id_agenda_para_fechar, motivo, self.user_id # Passa o ID do vistoriador logado
    #         # )
    #         # if resultado['success']:
    #         #     QMessageBox.information(self, "Sucesso", resultado['message'])
    #         #     self._carregar_meus_horarios_disponiveis() # Recarrega a lista
    #         # else:
    #         #     QMessageBox.warning(self, "Erro", resultado['message'])
    #         print(f"Simulando fechamento do horário ID {id_agenda_para_fechar} com motivo: {motivo} pelo vistoriador ID {self.user_id}")
    #         QMessageBox.information(self, "Simulação", "Funcionalidade de fechar horário pelo vistoriador a ser implementada no controller.")
    #         self._carregar_meus_horarios_disponiveis() # Recarrega para refletir a mudança (simulada)
    #     elif ok and not motivo.strip(): # Se o usuário confirmou mas não inseriu motivo
    #         QMessageBox.warning(self, "Motivo Necessário", "O motivo do fechamento é obrigatório.")


# Bloco para testar esta view isoladamente
if __name__ == '__main__':
    import sys
    import os
    # Adiciona o diretório raiz ao sys.path para encontrar os módulos
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from PyQt5.QtWidgets import QApplication, QMainWindow # Importações para o teste
    # Importações para setup do banco e dados de teste
    from models.database import criar_tabelas
    from models import usuario_model, agenda_model, imovel_model, imobiliaria_model # Para popular dados de teste

    criar_tabelas() # Garante que o banco e as tabelas existam

    # --- Criação de dados de TESTE para um vistoriador ---
    id_vist_teste_view = None
    vists = usuario_model.listar_usuarios_por_tipo('vistoriador') # Tenta pegar um vistoriador existente
    if vists:
        id_vist_teste_view = vists[0]['id']
        print(f"Usando vistoriador existente para teste: ID {id_vist_teste_view}, Nome: {vists[0]['nome']}")
    else:
        # Se não houver, cadastra um novo
        id_vist_teste_view = usuario_model.cadastrar_usuario("Vistoriador Teste View", "vist.view@teste.com", "senha123", "vistoriador")
        if id_vist_teste_view:
            print(f"Cadastrado novo vistoriador para teste: ID {id_vist_teste_view}")

    if id_vist_teste_view:
        # Garante que o vistoriador de teste tenha horários fixos e agenda gerada
        if not agenda_model.listar_horarios_fixos_por_vistoriador(id_vist_teste_view):
            agenda_model.cadastrar_horarios_fixos_vistoriador(id_vist_teste_view, ['1','2','3'], ['09:00', '14:00']) # Ex: Seg, Ter, Qua
        agenda_model.gerar_agenda_baseada_em_horarios_fixos() # Gera a agenda (slots)
        
        # --- Criar dados de agendamento para teste ---
        id_cli_teste = usuario_model.cadastrar_cliente("Cliente Teste VistView", "cliente.vistview@teste.com")
        id_imob_teste = imobiliaria_model.cadastrar_imobiliaria("Imob Teste VistView", 10, 12, 15)
        
        if id_cli_teste and id_imob_teste:
            id_imovel_teste = imovel_model.cadastrar_imovel(
                cod_imovel="IMV-VV-001",
                cliente_id=id_cli_teste,
                imobiliaria_id=id_imob_teste,
                endereco="Rua da Vistoria, 123",
                tamanho=75.0,
                mobiliado="mobiliado",
                cep="74000-000",
                referencia="Próximo à praça"
            )
            if id_imovel_teste:
                # Encontrar um horário disponível para agendar
                horarios_disponiveis = agenda_model.listar_horarios_agenda(
                    vistoriador_id=id_vist_teste_view,
                    apenas_disponiveis=True,
                    data_inicio=datetime.date.today().strftime("%Y-%m-%d"),
                    data_fim=(datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
                )
                if horarios_disponiveis:
                    horario_para_agendar = horarios_disponiveis[0]
                    agenda_model.agendar_vistoria_em_horario(
                        id_agenda=horario_para_agendar['id_agenda'],
                        imovel_id=id_imovel_teste,
                        tipo_vistoria_agendada="ENTRADA"
                    )
                    print(f"Agendamento de ENTRADA criado para teste no imóvel ID {id_imovel_teste}.")
                else:
                    print("AVISO: Nenhum horário disponível encontrado para criar agendamento de teste.")
            else:
                print("ERRO: Falha ao cadastrar imóvel de teste.")
        else:
            print("ERRO: Falha ao cadastrar cliente ou imobiliária de teste.")
    else:
        print("ERRO: Não foi possível obter/criar um vistoriador para os testes.")
        sys.exit()


    app = QApplication(sys.argv)

    # Instancia a VistoriadorAgendaViewWidget, passando o ID e tipo do vistoriador de teste
    vist_view = VistoriadorAgendaViewWidget(user_id=id_vist_teste_view, user_type='vistoriador')

    # Cria uma janela principal temporária para exibir o widget
    main_window_temp = QMainWindow()
    main_window_temp.setCentralWidget(vist_view)
    main_window_temp.setWindowTitle("Teste Vistoriador Agenda View")
    main_window_temp.setGeometry(150, 150, 1000, 600) # Posição e tamanho da janela de teste
    main_window_temp.show()

    sys.exit(app.exec_())
