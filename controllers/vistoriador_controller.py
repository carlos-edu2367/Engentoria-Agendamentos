# engentoria/controllers/vistoriador_controller.py

# Importações de modelos de dados necessários para as operações do controlador
from models import usuario_model, agenda_model
# Importação de funções auxiliares, especificamente para converter filtros de período em datas
from utils import helpers # Para obter_datas_para_filtro_periodo
# Importações para tipagem estática, melhorando a legibilidade e robustez do código
from typing import Dict, Any, Optional, List

# Importações condicionais e configuração de sys.path para o bloco de teste `if __name__ == '__main__'`
# Isso permite que o script de teste encontre outros módulos do projeto quando executado diretamente.
import sys
import os
# Obtém o diretório do arquivo atual e o diretório raiz do projeto
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) # Assume que 'controllers' está um nível abaixo da raiz do projeto
# Adiciona a raiz do projeto ao sys.path se ainda não estiver lá
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importações específicas para o bloco de teste `if __name__ == '__main__'`
if __name__ == '__main__':
    from controllers.admin_controller import AdminController # Para criar/gerenciar dados de teste
    # A importação de `criar_tabelas` dependeria da estrutura do seu módulo de banco de dados.
    # Se `database.py` contiver essa função, o import seria `from models.database import criar_tabelas`.
    # Supondo que exista para fins de configuração de teste:
    try:
        from models.database import criar_tabelas
    except ImportError:
        # Define uma função dummy se não existir, para que o teste não quebre apenas por isso.
        def criar_tabelas():
            print("AVISO: Função 'criar_tabelas' não encontrada no models.database. Testes podem não ter o DB configurado.")
            pass


class VistoriadorController:
    """
    Controlador para funcionalidades específicas de um usuário vistoriador logado.

    Esta classe armazena o ID do vistoriador logado e fornece métodos para
    acessar informações e realizar ações pertinentes a esse vistoriador, como:
    - Obter dados do seu perfil.
    - Listar sua agenda de vistorias (agendadas, disponíveis, fechadas, improdutivas).
    - Listar seus horários de trabalho fixos.
    """

    def __init__(self, vistoriador_id: int):
        """
        Construtor do VistoriadorController.

        Armazena o ID do vistoriador que utilizará este controlador.
        Valida se o ID fornecido é um inteiro positivo.

        Args:
            vistoriador_id (int): O ID do vistoriador logado.
                                  Este ID é usado em todas as operações subsequentes
                                  para filtrar dados e aplicar permissões.

        Raises:
            ValueError: Se o `vistoriador_id` não for um inteiro válido ou for menor/igual a zero.
        """
        # Validação crucial: o ID do vistoriador deve ser válido para o controlador funcionar.
        if not isinstance(vistoriador_id, int) or vistoriador_id <= 0:
            # Uma exceção é levantada aqui porque um ID inválido torna o controlador inutilizável.
            raise ValueError("ID do vistoriador inválido fornecido ao VistoriadorController.")
        self.vistoriador_id: int = vistoriador_id # Armazena o ID do vistoriador para uso nos métodos

        # Comentário sobre acoplamento e alternativas de design:
        # Poderíamos instanciar outros controllers aqui se precisarmos de suas funcionalidades
        # Por exemplo: self.agenda_ctrl = AgendaController() (se AgendaController não precisasse de ID no construtor)
        # Contudo, para manter o acoplamento baixo entre controllers, opta-se por:
        # 1. Chamar funções de modelo diretamente (como `agenda_model.listar_horarios_agenda`).
        # 2. Se a lógica for complexa e reutilizada, a View (camada de apresentação)
        #    pode instanciar e coordenar múltiplos controllers.
        # Esta abordagem evita dependências circulares e mantém os controllers mais focados.

    def obter_meu_perfil(self) -> Optional[Dict[str, Any]]:
        """
        Busca e retorna os dados de perfil do vistoriador logado.

        Utiliza o `vistoriador_id` armazenado na instância para consultar o modelo.
        Verifica se o usuário encontrado é realmente do tipo 'vistoriador'.

        Returns:
            Optional[Dict[str, Any]]: Um dicionário com os dados do perfil do vistoriador
                                      (ex: id, nome, email, tipo, telefones) se encontrado
                                      e for do tipo correto. Retorna None se o usuário
                                      não for encontrado ou não for um vistoriador.
        """
        # Busca o usuário pelo ID armazenado na instância, usando a função do modelo de usuário
        perfil = usuario_model.obter_usuario_por_id(self.vistoriador_id)

        # Verifica se o perfil foi encontrado e se o tipo do usuário é 'vistoriador'
        if perfil and perfil.get('tipo') == 'vistoriador':
            return perfil # Retorna os dados do perfil se tudo estiver correto
        elif perfil:
            # Log de aviso caso o ID corresponda a um usuário, mas este não seja um vistoriador.
            # Isso pode indicar um erro na lógica de atribuição do ID ou no fluxo de autenticação.
            print(f"⚠️ AVISO: Usuário ID {self.vistoriador_id} encontrado, mas não é do tipo 'vistoriador'. Tipo: {perfil.get('tipo')}")
            return None # Ou poderia levantar um erro de permissão, dependendo da política do sistema.
        
        # Se o perfil não foi encontrado (usuario_model.obter_usuario_por_id retornou None)
        print(f"ℹ️ INFO: Perfil não encontrado para o vistoriador ID {self.vistoriador_id}.")
        return None

    def obter_minha_agenda_detalhada(self, filtro_periodo: str = "Todos os agendamentos",
                                     apenas_agendados: bool = False,
                                     apenas_disponiveis: bool = False,
                                     incluir_fechados: bool = False,
                                     incluir_improdutivas: bool = False) -> List[Dict[str, Any]]:
        """
        Lista os horários da agenda (agendados, disponíveis, fechados ou improdutivos)
        para o vistoriador logado, com base nos filtros fornecidos.

        Args:
            filtro_periodo (str): Define o intervalo de datas para a busca.
                                  Exemplos: "Hoje", "Amanhã", "Esta semana", "Todos os agendamentos".
                                  O helper `obter_datas_para_filtro_periodo` traduz essa string.
            apenas_agendados (bool): Se True, retorna apenas vistorias que já foram agendadas.
            apenas_disponiveis (bool): Se True, retorna apenas horários livres e disponíveis para agendamento.
            incluir_fechados (bool): Se True, inclui na lista os horários que foram manualmente marcados como 'FECHADO'.
            incluir_improdutivas (bool): Se True, inclui na lista as vistorias que foram marcadas como improdutivas.

        Returns:
            List[Dict[str, Any]]: Uma lista de dicionários, onde cada dicionário representa
                                  um item da agenda do vistoriador, conforme os filtros aplicados.
                                  Retorna uma lista vazia se nenhum item correspondente for encontrado.
        """
        # Converte o filtro de período textual (ex: "Hoje") em datas de início e fim concretas
        data_inicio, data_fim = helpers.obter_datas_para_filtro_periodo(filtro_periodo)
        
        # Chama a função do modelo `agenda_model` para buscar os horários da agenda.
        # Todos os filtros, incluindo `vistoriador_id`, são passados para a camada de modelo,
        # que é responsável por construir a consulta SQL apropriada.
        return agenda_model.listar_horarios_agenda(
            vistoriador_id=self.vistoriador_id, # Filtra crucialmente pela agenda do vistoriador logado
            data_inicio=data_inicio,
            data_fim=data_fim,
            apenas_disponiveis=apenas_disponiveis,
            apenas_agendados=apenas_agendados,
            incluir_fechados=incluir_fechados,
            incluir_improdutivas=incluir_improdutivas # Filtro para vistorias improdutivas
        )

    def obter_meus_horarios_fixos(self) -> List[Dict[str, str]]:
        """
        Lista os horários de trabalho fixos cadastrados para o vistoriador logado.

        Horários fixos são a base para a geração automática da agenda de disponibilidade
        do vistoriador. Por exemplo: "Segunda-feira às 09:00 e 10:00", "Terça-feira às 14:00".

        Returns:
            List[Dict[str, str]]: Uma lista de dicionários, cada um representando um horário fixo.
                                  Cada dicionário contém 'dia_semana' (representação numérica, 0-6,
                                  onde 0 pode ser Domingo ou Segunda, dependendo da convenção do `date.weekday()`)
                                  e 'horario' (no formato "HH:MM").
                                  Retorna uma lista vazia se o vistoriador não tiver horários fixos cadastrados.
        """
        # Delega a busca diretamente para a função correspondente no modelo da agenda,
        # passando o ID do vistoriador logado.
        return agenda_model.listar_horarios_fixos_por_vistoriador(self.vistoriador_id)

    

# Bloco de execução principal (`if __name__ == '__main__'`), usado para testes rápidos e
# demonstração do controlador. Este bloco só é executado quando o script
# `vistoriador_controller.py` é rodado diretamente (ex: `python vistoriador_controller.py`).
if __name__ == '__main__':
    # --- Configuração Inicial para Testes ---
    # Para testar este controller de forma isolada, precisamos de um `vistoriador_id` válido.
    # Em um cenário de aplicação real, este ID seria obtido após o processo de login
    # (gerenciado pelo AuthController) e passado para a instanciação do VistoriadorController.

    # Tenta criar as tabelas do banco de dados, se a função existir.
    # É uma boa prática para garantir que o ambiente de teste esteja minimamente configurado.
    print("INFO: Tentando configurar o ambiente de teste...")
    criar_tabelas() 

    # Instancia o AdminController para auxiliar na criação ou listagem de vistoriadores
    # que serão usados nos testes. Esta é uma conveniência para o script de teste
    # e não reflete necessariamente como os controllers interagiriam em produção.
    admin_ctrl = AdminController() # Supondo que AdminController não requer argumentos no construtor.
    
    id_vist_teste = None # Variável para armazenar o ID do vistoriador de teste.
    nome_vist_teste = "Vistoriador Padrão para Testes" # Nome padrão para o vistoriador de teste.

    # 1. Tenta encontrar um vistoriador existente para usar nos testes.
    vistoriadores_existentes = admin_ctrl.listar_todos_vistoriadores()
    if vistoriadores_existentes:
        primeiro_vistoriador = vistoriadores_existentes[0] # Pega o primeiro da lista.
        id_vist_teste = primeiro_vistoriador['id']
        nome_vist_teste = primeiro_vistoriador['nome']
        print(f"INFO: Usando vistoriador existente para teste: ID {id_vist_teste}, Nome: '{nome_vist_teste}'")
    else:
        # 2. Se nenhum vistoriador existir, tenta cadastrar um novo para os testes.
        print("INFO: Nenhum vistoriador encontrado. Tentando cadastrar um novo para teste...")
        email_unico_teste = f"vist.teste.{os.urandom(4).hex()}@example.com" # Gera email único para evitar conflitos.
        resultado_cadastro = admin_ctrl.cadastrar_novo_vistoriador(
            nome=nome_vist_teste,
            email=email_unico_teste,
            senha="password123", # Senha de teste.
            confirma_senha="password123"
        )
        if resultado_cadastro.get('success'):
            id_vist_teste = resultado_cadastro['id']
            print(f"INFO: Vistoriador de teste cadastrado com sucesso: ID {id_vist_teste}, Nome: '{nome_vist_teste}', Email: '{email_unico_teste}'")
        else:
            print(f"ERRO: Não foi possível cadastrar um vistoriador de teste. Mensagem: {resultado_cadastro.get('message')}")
            print("ERRO: Testes do VistoriadorController não podem prosseguir sem um vistoriador.")
            id_vist_teste = None # Garante que os testes não rodem se o cadastro falhar.

    # --- Execução dos Testes do VistoriadorController ---
    if id_vist_teste: # Prossegue com os testes apenas se um ID de vistoriador válido foi obtido.
        print(f"\n--- Iniciando testes para Vistoriador ID: {id_vist_teste} ('{nome_vist_teste}') ---")
        try:
            # Instancia o VistoriadorController com o ID obtido.
            vist_ctrl = VistoriadorController(vistoriador_id=id_vist_teste)
        except ValueError as e:
            print(f"ERRO CRÍTICO ao instanciar VistoriadorController: {e}")
            # Interrompe os testes se o controller não puder ser instanciado (ex: ID inválido, embora já validado acima).
            sys.exit(1) # Termina o script com código de erro.

        # Teste 1: Obter perfil do vistoriador.
        print("\n--- Teste 1: Obter Perfil do Vistoriador ---")
        perfil = vist_ctrl.obter_meu_perfil()
        if perfil:
            print(f"  Perfil Obtido: ID: {perfil.get('id')}, Nome: {perfil.get('nome')}, Email: {perfil.get('email')}, Tipo: {perfil.get('tipo')}")
        else:
            print(f"  ERRO: Não foi possível obter o perfil do vistoriador ID {id_vist_teste}.")

        # Preparação para testes de agenda: Adicionar horários fixos se não existirem.
        # Esta etapa é importante para que os testes de listagem de agenda tenham dados para mostrar.
        if not vist_ctrl.obter_meus_horarios_fixos():
            print(f"\nINFO: Vistoriador ID {id_vist_teste} não possui horários fixos. Adicionando alguns para teste...")
            dias_semana_teste = ["Segunda-feira", "Quarta-feira", "Sexta-feira"]
            horarios_teste = ["09:00", "10:00", "11:00", "14:00", "15:00"]
            # Utiliza o AdminController para adicionar horários, pois o VistoriadorController não tem essa responsabilidade.
            res_add_horarios = admin_ctrl.adicionar_horarios_fixos_para_vistoriador(
                vistoriador_id=id_vist_teste,
                dias_semana=dias_semana_teste,
                horarios_str_lista=horarios_teste
            )
            if res_add_horarios.get('success'):
                print(f"  Horários fixos adicionados para ID {id_vist_teste}: {res_add_horarios.get('message')}")
                # É crucial que a agenda seja (re)gerada após adicionar/alterar horários fixos.
                # A função `adicionar_horarios_fixos_para_vistoriador` no AdminController já chama
                # `agenda_model.gerar_agenda_baseada_em_horarios_fixos()`.
                # Se não chamasse, seria necessário fazer aqui:
                # print("  INFO: Solicitando regeneração da agenda base...")
                # agenda_model.gerar_agenda_baseada_em_horarios_fixos()
            else:
                print(f"  ERRO: Falha ao adicionar horários fixos: {res_add_horarios.get('message')}")

        # Teste 2: Obter horários fixos do vistoriador.
        print("\n--- Teste 2: Obter Horários Fixos do Vistoriador ---")
        horarios_fixos = vist_ctrl.obter_meus_horarios_fixos()
        if horarios_fixos:
            print(f"  Horários fixos para '{nome_vist_teste}' (ID: {id_vist_teste}):")
            for hf in horarios_fixos:
                # `helpers.traduzir_dia_semana` converte o número do dia (0-6) para nome (Dom, Seg, ...).
                dia_traduzido = helpers.traduzir_dia_semana(hf.get('dia_semana', -1)) # Usar get com default
                print(f"    - Dia: {dia_traduzido} (Num: {hf.get('dia_semana')}), Horário: {hf.get('horario')}")
        else:
            print(f"  Nenhum horário fixo cadastrado para o vistoriador ID {id_vist_teste}.")

        # Teste 3: Obter agendamentos (vistorias marcadas) para "Hoje".
        print("\n--- Teste 3: Listar Agendamentos do Vistoriador (Filtro: Hoje) ---")
        agendamentos_hoje = vist_ctrl.obter_minha_agenda_detalhada(filtro_periodo="Hoje", apenas_agendados=True)
        if agendamentos_hoje:
            print(f"  Agendamentos para '{nome_vist_teste}' hoje:")
            for ag in agendamentos_hoje:
                print(f"    ID Agenda: {ag.get('id_agenda')}, Data: {ag.get('data')}, Hora: {ag.get('horario')}, Tipo: {ag.get('tipo_vistoria')}, Imóvel Cód: {ag.get('cod_imovel', 'N/A')}, Cliente: {ag.get('nome_cliente', 'N/A')}")
        else:
            print(f"  Nenhum agendamento encontrado para '{nome_vist_teste}' hoje.")

        # Teste 4: Obter horários disponíveis para "Esta semana".
        print("\n--- Teste 4: Listar Horários Disponíveis do Vistoriador (Filtro: Esta Semana) ---")
        disponiveis_semana = vist_ctrl.obter_minha_agenda_detalhada(filtro_periodo="Esta semana", apenas_disponiveis=True)
        if disponiveis_semana:
            print(f"  Horários disponíveis para '{nome_vist_teste}' esta semana:")
            for disp in disponiveis_semana:
                print(f"    ID Agenda: {disp.get('id_agenda')}, Data: {disp.get('data')}, Hora: {disp.get('horario')}")
        else:
            print(f"  Nenhum horário disponível encontrado para '{nome_vist_teste}' esta semana.")
            print(f"    (Isso pode ser normal se todos os horários fixos já estiverem agendados, se a agenda não foi gerada para este período, ou se não há horários fixos nesta semana.)")

        # Teste 5: Listar todos os tipos de horários (disponíveis, agendados, fechados, improdutivos) para o "Próximo mês".
        print("\n--- Teste 5: Listar Todos os Tipos de Horários do Vistoriador (Filtro: Próximo Mês) ---")
        todos_horarios_prox_mes = vist_ctrl.obter_minha_agenda_detalhada(
            filtro_periodo="Próximo mês", # Pode ser um período maior para pegar mais dados.
            apenas_agendados=False,      # Não filtrar por agendados apenas.
            apenas_disponiveis=False,    # Não filtrar por disponíveis apenas.
            incluir_fechados=True,       # Incluir horários fechados.
            incluir_improdutivas=True    # Incluir vistorias improdutivas.
        )
        if todos_horarios_prox_mes:
            print(f"  Todos os tipos de horários para '{nome_vist_teste}' no próximo mês:")
            for item_agenda in todos_horarios_prox_mes:
                # Constrói uma string de informações de status para melhor visualização.
                status_info = f"Status Agenda: {item_agenda.get('status_agenda', 'N/A')}"
                if item_agenda.get('tipo_vistoria'):
                    status_info += f", Tipo Vistoria: {item_agenda['tipo_vistoria']}"
                if item_agenda.get('motivo_fechamento'):
                     status_info += f", Motivo Fechamento: '{item_agenda['motivo_fechamento']}'"
                if item_agenda.get('motivo_improdutiva'): # Supondo que este campo exista para improdutivas
                     status_info += f", Motivo Improdutiva: '{item_agenda['motivo_improdutiva']}'"
                print(f"    ID: {item_agenda.get('id_agenda')}, Data: {item_agenda.get('data')}, Hora: {item_agenda.get('horario')}, {status_info}")
        else:
            print(f"  Nenhum horário (de qualquer tipo) encontrado para '{nome_vist_teste}' no próximo mês.")
            print(f"    (Verifique se horários fixos existem e se a agenda foi gerada para este período.)")
            
        print(f"\n--- Fim dos testes para Vistoriador ID: {id_vist_teste} ('{nome_vist_teste}') ---")
    else:
        # Mensagem se os testes não puderam ser executados por falta de um vistoriador.
        print("\nINFO: Testes do VistoriadorController não executados devido à falha na obtenção ou criação de um vistoriador de teste.")

