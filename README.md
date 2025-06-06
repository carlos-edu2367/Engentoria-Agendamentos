# Engentoria - Sistema de Agendamentos de Vistoria

Este é um sistema de desktop para agendamento de vistorias e controle de vistoriadores, desenvolvido em Python com PyQt5.

## Funcionalidades Principais

* Login de usuários (Administradores, Vistoriadores).
* Painel Administrativo:
  * Cadastro de clientes, imobiliárias e vistoriadores.
  * Remoção de entidades.
  * Geração de relatórios.
* Gerenciamento de Agenda (para Admins):
  * Visualização de horários disponíveis.
  * Agendamento de vistorias associando clientes, imobiliárias e imóveis.
* Agenda do Vistoriador:
  * Visualização dos seus agendamentos e horários livres.
* Gerenciamento de Vistoriadores (para Admins):
  * Visualização e gestão da agenda de cada vistoriador.
  * Configuração da disponibilidade (horários fixos e avulsos).
  * Marcação de vistorias como improdutivas.

## Tecnologias Utilizadas

* **Linguagem:** Python 3
* **Interface Gráfica:** PyQt5
* **Banco de Dados:** SQLite (projeção para futura implementação de postgrees)

## Como Executar

1. **Pré-requisitos:**
   * Python 3.12
   * Pip (gerenciador de pacotes Python)
2. **Clone o repositório (após subir no GitHub):**
   ```bash
   git clone https://github.com/carlos-edu2367/Engentoria-Agendamentos.git
   ```
3. **(Opcional, mas recomendado) Crie e ative um ambiente virtual:**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```
4. **Instale as dependências:**
   ```bash
   pip install pandas openpyxl pyqt5
   ```
5. **Execute a aplicação:**
   ```bash
   python app.py
   ```

E-mail e senha padrão:

*admin@adm.com*

*123123*

## Estrutura do Projeto

engentoria/
├── app.py # Ponto de entrada da aplicação
├── controllers/ # Lógica de controle
├── models/ # Lógica de dados e interação com banco
├── views/ # Componentes da interface gráfica
├── utils/ # Utilitários (estilos, validadores, helpers)
├── .gitignore
├── README.md
└── requirements.txt
