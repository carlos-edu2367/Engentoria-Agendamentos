# engentoria/utils/styles.py
"""
Este módulo define constantes de cores, fontes e folhas de estilo (stylesheets)
utilizadas para padronizar a aparência da interface gráfica da aplicação Engentoria,
provavelmente construída com PyQt ou PySide.

A estrutura visa facilitar a manutenção e a consistência visual em toda a aplicação,
seguindo um tema escuro similar ao de aplicações como Spotify.

As seções principais incluem:
- Definições de Cores Base: Paleta de cores para fundos, textos, bordas e acentos.
- Estilo Base Global (STYLESHEET_BASE_DARK): Uma folha de estilo CSS-like que se aplica
  a widgets comuns como QWidget, QLabel, QLineEdit, QPushButton, etc.
- Funções Geradoras de Estilo de Botão: Funções para criar estilos específicos para
  botões (primário, secundário, perigo, texto).
- Estilos Específicos para Componentes: Estilos customizados para labels de título,
  mensagens de erro, widgets da barra lateral, itens de lista, etc.
"""

# --- Definições de Cores Base ---
# Estas variáveis armazenam códigos hexadecimais para as cores usadas na UI.
# A nomeclatura tenta indicar o uso da cor (ex: BACKGROUND, TEXT, ACCENT) e sua variante (ex: DARK, MEDIUM, PRIMARY).

# Cores de Fundo
COLOR_BACKGROUND_DARK = "#121212"    # Fundo principal escuro
COLOR_BACKGROUND_MEDIUM = "#181818"  # Fundo intermediário, para painéis ou seções
COLOR_BACKGROUND_LIGHT = "#282828"   # Fundo mais claro, para hover ou elementos destacados
COLOR_BACKGROUND_INPUT = "#333333"   # Fundo para campos de entrada (QLineEdit, QTextEdit)

# Cores de Borda
COLOR_BORDER_DARK = "#282828"        # Borda escura, sutil
COLOR_BORDER_MEDIUM = "#555555"      # Borda de tonalidade média
COLOR_BORDER_HIGHLIGHT = "#1DB954"   # Borda para destacar foco ou seleção (verde)

# Cores de Texto
COLOR_TEXT_PRIMARY = "#FFFFFF"       # Cor principal do texto (branco)
COLOR_TEXT_SECONDARY = "#B3B3B3"     # Cor secundária do texto (cinza claro)
COLOR_TEXT_DISABLED = "#777777"      # Cor do texto para widgets desabilitados (cinza escuro)

# Cores de Acento (usadas para botões, ícones, destaques)
COLOR_ACCENT_PRIMARY = "#1DB954"     # Cor de acento primária (verde Spotify)
COLOR_ACCENT_PRIMARY_HOVER = "#1ED760" # Variação para hover do acento primário
COLOR_ACCENT_PRIMARY_PRESSED = "#1AA34A" # Variação para estado pressionado do acento primário

COLOR_ACCENT_SECONDARY = "#535353"   # Cor de acento secundária (cinza)
COLOR_ACCENT_SECONDARY_HOVER = "#616161"
COLOR_ACCENT_SECONDARY_PRESSED = "#424242"

# Cores para Ações Destrutivas ou de Alerta
COLOR_DANGER = "#F44336"             # Cor para indicar perigo ou erro (vermelho)
COLOR_DANGER_HOVER = "#E53935"
COLOR_DANGER_PRESSED = "#D32F2F"

# Cor para Sucesso (reutiliza a cor de acento primária)
COLOR_SUCCESS = COLOR_ACCENT_PRIMARY

# Definição da Família de Fontes Principal
FONT_FAMILY_PRIMARY = "'Segoe UI', Arial, sans-serif" # Fonte padrão, com fallbacks

# --- Estilo Base Global (Dark Theme) ---
# STYLESHEET_BASE_DARK é uma string multilinhas contendo regras de estilo CSS-like
# que são aplicadas globalmente aos widgets da aplicação Qt.
STYLESHEET_BASE_DARK = f"""
    /* Estilo padrão para todos os QWidgets */
    QWidget {{
        background-color: {COLOR_BACKGROUND_DARK};
        color: {COLOR_TEXT_PRIMARY};
        font-family: {FONT_FAMILY_PRIMARY};
    }}
    /* Estilo específico para QMainWindow e QDialog */
    QMainWindow, QDialog {{
        background-color: {COLOR_BACKGROUND_DARK};
    }}
    /* Estilo para QLabels */
    QLabel {{
        font-size: 15px;
        padding: 2px;
        background-color: transparent; /* Labels geralmente não têm fundo próprio */
    }}
    /* Estilo para campos de entrada de texto e ComboBox */
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{
        background-color: {COLOR_BACKGROUND_INPUT};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_MEDIUM};
        border-radius: 5px; /* Cantos arredondados */
        padding: 8px 10px; /* Espaçamento interno */
        font-size: 14px;
    }}
    /* Estilo para campos de entrada quando em foco */
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 1px solid {COLOR_BORDER_HIGHLIGHT}; /* Borda verde ao focar */
    }}
    /* Estilo para campos de entrada desabilitados */
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled {{
        background-color: {COLOR_ACCENT_SECONDARY};
        color: {COLOR_TEXT_DISABLED};
        border: 1px solid {COLOR_BORDER_DARK};
    }}
    /* Estilo para a seta dropdown do QComboBox */
    QComboBox::drop-down {{
        border: none;
        background-color: transparent;
        width: 20px;
    }}
    QComboBox::down-arrow {{
        /* Aqui poderia ser definida uma imagem customizada para a seta.
           Ex: image: url(caminho/para/sua/seta_baixo.png); */
    }}
    /* Estilo base para QPushButtons */
    QPushButton {{
        border-radius: 5px;
        padding: 10px 15px;
        font-size: 14px;
        font-weight: bold;
        color: {COLOR_TEXT_PRIMARY};
        /* O background-color específico virá de estilos mais granulares (PRIMARY_BUTTON_STYLE, etc.) */
    }}
    QPushButton:disabled {{
        background-color: {COLOR_ACCENT_SECONDARY_PRESSED};
        color: {COLOR_TEXT_DISABLED};
    }}
    /* Estilo para QListWidget */
    QListWidget {{
        background-color: {COLOR_BACKGROUND_MEDIUM};
        border: 1px solid {COLOR_BORDER_DARK};
        border-radius: 5px;
        padding: 0px; /* Padding do item controla o espaçamento interno */
        font-size: 15px;
        outline: 0; /* Remove a borda de foco padrão */
    }}
    QListWidget::item {{
        padding: 10px 12px;
        border-bottom: 1px solid {COLOR_BACKGROUND_LIGHT}; /* Linha separadora entre itens */
        color: {COLOR_TEXT_SECONDARY};
    }}
    QListWidget::item:alternate {{ /* Estilo para linhas alternadas, se ativado */
        background-color: {COLOR_BACKGROUND_DARK};
    }}
    QListWidget::item:selected {{ /* Item selecionado */
        background-color: {COLOR_ACCENT_PRIMARY};
        color: {COLOR_TEXT_PRIMARY};
        border-radius: 4px; /* Arredondamento leve para o item selecionado */
    }}
    QListWidget::item:hover {{ /* Item sob o cursor do mouse */
        background-color: {COLOR_BACKGROUND_LIGHT};
        color: {COLOR_TEXT_PRIMARY};
    }}
    /* Estilo para QScrollBar vertical (usada em QListWidget, QTextEdit, etc.) */
    QScrollBar:vertical {{
        border: none;
        background: {COLOR_BACKGROUND_LIGHT};
        width: 10px; /* Largura da barra de rolagem */
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:vertical {{ /* O "pegador" da barra de rolagem */
        background: {COLOR_ACCENT_SECONDARY};
        min-height: 25px; /* Altura mínima do pegador */
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLOR_ACCENT_SECONDARY_HOVER};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ /* As setas de linha (geralmente ocultas) */
        height: 0px;
        background: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ /* As áreas de página (clicar aqui move uma página) */
        background: none;
    }}
    /* Estilo para QStackedWidget (usado para alternar entre "páginas" da UI) */
    QStackedWidget {{
        padding: 15px; /* Espaçamento interno para o conteúdo da página ativa */
        background-color: {COLOR_BACKGROUND_DARK}; /* Garante que o fundo seja consistente */
    }}
    /* Estilo para labels dentro de um QFormLayout (comum em formulários) */
    QFormLayout QLabel {{
        font-size: 14px;
        color: {COLOR_TEXT_SECONDARY};
        padding-top: 5px; /* Alinhamento vertical com o campo de entrada */
    }}
    /* Estilo para QCheckBox */
    QCheckBox {{
        spacing: 5px; /* Espaço entre o indicador e o texto */
        font-size: 14px;
    }}
    QCheckBox::indicator {{ /* A "caixinha" do checkbox */
        width: 16px;
        height: 16px;
        border: 1px solid {COLOR_BORDER_MEDIUM};
        border-radius: 3px;
        background-color: {COLOR_BACKGROUND_INPUT};
    }}
    QCheckBox::indicator:checked {{ /* Indicador quando marcado */
        background-color: {COLOR_ACCENT_PRIMARY};
        border: 1px solid {COLOR_ACCENT_PRIMARY_HOVER};
        /* Aqui poderia ser uma imagem de checkmark:
           image: url(path/to/your/checkmark.png); */
    }}
    QCheckBox::indicator:disabled {{
        background-color: {COLOR_ACCENT_SECONDARY};
        border: 1px solid {COLOR_BORDER_DARK};
    }}
    /* Estilo para um QFrame nomeado 'styledPanel' (usado para painéis com estilo customizado) */
    QFrame#styledPanel {{
        border: 1px solid {COLOR_BORDER_DARK};
        border-radius: 5px;
        background-color: {COLOR_BACKGROUND_MEDIUM};
        padding: 10px;
    }}
"""

# --- Estilos de Botão Funcionais ---
# Estas são funções auxiliares para gerar strings de stylesheet para botões
# com diferentes aparências e comportamentos (cor de fundo, hover, pressionado).

def get_button_style(bg_color: str, hover_color: str, pressed_color: str,
                     text_color: str = COLOR_TEXT_PRIMARY,
                     padding: str = "10px 15px", font_size: str = "14px",
                     border_radius: str = "5px", min_width: str = "100px",
                     disabled_bg_color: str = COLOR_ACCENT_SECONDARY_PRESSED,
                     disabled_text_color: str = COLOR_TEXT_DISABLED) -> str:
    """
    Gera uma string de stylesheet para um QPushButton com base nos parâmetros fornecidos.

    Args:
        bg_color (str): Cor de fundo normal do botão.
        hover_color (str): Cor de fundo quando o mouse está sobre o botão.
        pressed_color (str): Cor de fundo quando o botão está pressionado.
        text_color (str): Cor do texto do botão.
        padding (str): Espaçamento interno do botão (CSS-like).
        font_size (str): Tamanho da fonte do botão.
        border_radius (str): Raio da borda para cantos arredondados.
        min_width (str): Largura mínima do botão.
        disabled_bg_color (str): Cor de fundo do botão desabilitado.
        disabled_text_color (str): Cor do texto do botão desabilitado.

    Returns:
        str: A string de stylesheet formatada para o botão.
    """
    return f"""
        QPushButton {{
            background-color: {bg_color};
            color: {text_color};
            border: none; /* Remove a borda padrão do sistema */
            padding: {padding};
            font-size: {font_size};
            font-weight: bold;
            border-radius: {border_radius};
            min-width: {min_width}; /* Garante uma largura mínima consistente */
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
        QPushButton:pressed {{
            background-color: {pressed_color};
        }}
        QPushButton:disabled {{
            background-color: {disabled_bg_color};
            color: {disabled_text_color};
        }}
    """

# Estilo para botões primários (ex: "Salvar", "Confirmar")
PRIMARY_BUTTON_STYLE = get_button_style(
    bg_color=COLOR_ACCENT_PRIMARY,
    hover_color=COLOR_ACCENT_PRIMARY_HOVER,
    pressed_color=COLOR_ACCENT_PRIMARY_PRESSED,
    padding="12px 20px",       # Padding maior
    font_size="15px",          # Fonte um pouco maior
    border_radius="25px",      # Bordas bem arredondadas (estilo "pílula")
    min_width="180px"          # Largura mínima generosa
)

# Estilo para botões secundários (ex: "Cancelar", "Voltar")
SECONDARY_BUTTON_STYLE = get_button_style(
    bg_color=COLOR_ACCENT_SECONDARY,
    hover_color=COLOR_ACCENT_SECONDARY_HOVER,
    pressed_color=COLOR_ACCENT_SECONDARY_PRESSED,
    min_width="120px"
)

# Estilo para botões de perigo (ex: "Deletar", "Excluir")
DANGER_BUTTON_STYLE = get_button_style(
    bg_color=COLOR_DANGER,
    hover_color=COLOR_DANGER_HOVER,
    pressed_color=COLOR_DANGER_PRESSED,
    min_width="120px"
)

# Estilo para botões que se parecem com links de texto
TEXT_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: transparent; /* Sem fundo */
        border: none; /* Sem borda */
        color: {COLOR_ACCENT_PRIMARY}; /* Cor de acento para o texto */
        font-size: 14px;
        font-weight: normal; /* Fonte normal, não bold */
        text-align: center;
        padding: 5px;
        min-width: auto; /* Largura se ajusta ao texto */
    }}
    QPushButton:hover {{
        color: {COLOR_ACCENT_PRIMARY_HOVER};
        text-decoration: underline; /* Sublinhado no hover, como um link */
    }}
    QPushButton:pressed {{
        color: {COLOR_ACCENT_PRIMARY_PRESSED};
    }}
"""

# --- Estilos de Labels Específicos ---
# Utilizados para dar destaque e formatação a títulos e mensagens.

# Estilo para o título principal da tela de login
LOGIN_TITLE_STYLE = f"""
    QLabel {{
        font-size: 28px;
        font-weight: bold;
        color: {COLOR_ACCENT_PRIMARY}; /* Cor de acento para destaque */
        padding-bottom: 20px; /* Espaço abaixo do título */
        qproperty-alignment: 'AlignCenter'; /* Alinhamento centralizado */
    }}
"""

# Estilo para títulos de página
PAGE_TITLE_STYLE = f"""
    QLabel {{
        font-size: 22px;
        font-weight: bold;
        color: {COLOR_TEXT_PRIMARY};
        padding-bottom: 8px;
        border-bottom: 1px solid {COLOR_BORDER_MEDIUM}; /* Linha sutil abaixo do título */
        margin-bottom: 15px; /* Espaço abaixo da linha */
        qproperty-alignment: 'AlignCenter';
    }}
"""

# Estilo para subtítulos ou seções menores
SUBTITLE_LABEL_STYLE = f"""
    QLabel {{
        font-size: 18px;
        font-weight: bold;
        color: {COLOR_TEXT_SECONDARY};
        padding-top: 5px;
        padding-bottom: 10px;
        qproperty-alignment: 'AlignCenter';
        border-bottom: 1px dashed {COLOR_BORDER_DARK}; /* Linha tracejada */
        margin-bottom: 10px;
    }}
"""

# Estilo para títulos em diálogos/pop-ups
DIALOG_TITLE_STYLE = f"""
    QLabel {{
        font-size: 20px;
        font-weight: bold;
        color: {COLOR_ACCENT_PRIMARY};
        padding-bottom: 10px;
        qproperty-alignment: 'AlignCenter';
    }}
"""

# Estilo para mensagens de erro
ERROR_MESSAGE_STYLE = f"""
    QLabel {{
        color: {COLOR_DANGER}; /* Cor vermelha para erros */
        font-size: 13px;
        padding-top: 5px;
        qproperty-alignment: 'AlignCenter';
        font-weight: bold; /* Destaca a mensagem de erro */
    }}
"""

# Estilo para textos informativos gerais
INFO_TEXT_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 13px;
    }}
"""

# Estilo para texto de rodapé
FOOTER_TEXT_STYLE = f"""
    QLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-size: 12px;
        padding-top: 20px;
        qproperty-alignment: 'AlignCenter';
    }}
"""

# --- Estilos de Componentes de UI Específicos ---

# Estilo para o widget da barra lateral (Sidebar)
SIDEBAR_WIDGET_STYLE = f"""
    QWidget#sidebarWidget {{ /* Seletor por objectName para aplicar apenas a este widget */
        background-color: {COLOR_BACKGROUND_MEDIUM};
        padding: 15px 8px;
        border-right: 1px solid {COLOR_BORDER_DARK}; /* Linha divisória à direita */
        min-width: 180px; /* Largura mínima da barra lateral */
        max-width: 220px; /* Largura máxima da barra lateral */
    }}
"""

# Estilo para botões dentro da barra lateral (usados para navegação)
SIDEBAR_BUTTON_STYLE = f"""
    QPushButton {{
        border: none;
        text-align: left; /* Alinha o texto do botão à esquerda */
        padding: 12px 15px;
        font-size: 15px;
        color: {COLOR_TEXT_SECONDARY};
        border-radius: 5px;
        background-color: transparent; /* Fundo transparente por padrão */
        font-weight: normal; /* Fonte normal, não bold por padrão */
    }}
    QPushButton:hover {{
        background-color: {COLOR_BACKGROUND_LIGHT};
        color: {COLOR_TEXT_PRIMARY};
    }}
    QPushButton:checked {{ /* Estilo para o botão selecionado/ativo */
        background-color: {COLOR_BACKGROUND_INPUT};
        color: {COLOR_ACCENT_PRIMARY};
        font-weight: bold; /* Destaca o botão ativo */
    }}
    QPushButton:checked:hover {{
        background-color: {COLOR_BACKGROUND_LIGHT}; /* Mantém o hover, mas com cor de texto de acento */
        color: {COLOR_ACCENT_PRIMARY_HOVER};
    }}
"""

# Estilos alternativos para itens selecionados em QListWidget (verde e vermelho)
LIST_WIDGET_ITEM_SELECTED_GREEN = f"""
    QListWidget::item:selected {{
        background-color: {COLOR_ACCENT_PRIMARY}; /* Verde para seleção "positiva" */
        color: {COLOR_TEXT_PRIMARY};
        border-radius: 4px;
    }}
    QListWidget::item:selected:hover {{ /* Para manter a cor de seleção no hover */
        background-color: {COLOR_ACCENT_PRIMARY_HOVER};
    }}
"""

LIST_WIDGET_ITEM_SELECTED_RED = f"""
    QListWidget::item:selected {{
        background-color: {COLOR_DANGER}; /* Vermelho para seleção "negativa" ou de alerta */
        color: {COLOR_TEXT_PRIMARY};
        border-radius: 4px;
    }}
    QListWidget::item:selected:hover {{
        background-color: {COLOR_DANGER_HOVER};
    }}
"""

# Estilo específico para campos de entrada na tela de login (pode ser mais destacado)
LOGIN_INPUT_STYLE = f"""
    QLineEdit {{
        background-color: {COLOR_BACKGROUND_INPUT};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_MEDIUM};
        border-radius: 5px;
        padding: 12px; /* Padding maior para campos de login */
        font-size: 14px;
    }}
    QLineEdit:focus {{
        border: 1px solid {COLOR_BORDER_HIGHLIGHT};
    }}
"""

# Estilo para QFrame genérico (usado como painel ou container)
PANEL_STYLE = f"""
    QFrame {{
        border: 1px solid {COLOR_BORDER_DARK};
        border-radius: 5px;
        background-color: {COLOR_BACKGROUND_MEDIUM};
        padding: 10px;
    }}
    QFrame#transparentPanel {{ /* Variação para painéis sem estilo próprio de fundo/borda */
        border: none;
        background-color: transparent;
        padding: 0px;
    }}
"""

# Estilo para QGroupBox, focando em destacar o título
GROUP_BOX_TITLE_STYLE = f"""
    QGroupBox {{
        font-size: 18px; /* Tamanho da fonte para o conteúdo dentro do GroupBox, não o título */
        font-weight: bold; /* Esta propriedade aqui pode não afetar o título diretamente */
        color: {COLOR_TEXT_PRIMARY}; /* Cor do texto para o conteúdo do GroupBox */
        margin-top: 10px; /* Espaço acima da borda do GroupBox */
        border: 1px solid {COLOR_BORDER_DARK};
        border-radius: 5px;
        background-color: {COLOR_BACKGROUND_MEDIUM}; /* Fundo da área do GroupBox */
        padding-top: 20px; /* Espaçamento para o título não sobrepor o conteúdo */
        padding-left: 10px;
        padding-right: 10px;
        padding-bottom: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; /* Define a origem do posicionamento do título */
        subcontrol-position: top center; /* Posiciona o título no centro superior */
        padding: 0 3px; /* Pequeno padding horizontal para o texto do título */
        background-color: {COLOR_BACKGROUND_MEDIUM}; /* Fundo atrás do texto do título, para cobrir a borda */
        color: {COLOR_ACCENT_PRIMARY}; /* Cor do texto do título */
        font-size: 16px; /* Ajuste específico para o tamanho da fonte do título do GroupBox */
        font-weight: bold; /* Garante que o título seja em negrito */
    }}
"""
