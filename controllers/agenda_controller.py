# engentoria/controllers/agenda_controller.py

# Importações de modelos de dados
from models import agenda_model, imovel_model, usuario_model, imobiliaria_model
# Importações de utilitários (validadores e helpers)
from utils import validators, helpers
# Importações para tipagem estática
from typing import Dict, Any, Optional, List, Tuple
# Importação do módulo datetime para manipulação de datas e horas (usado no bloco de teste __main__)
import datetime

# A importação do AdminController é utilizada apenas no bloco de teste `if __name__ == '__main__'`
# para facilitar a criação de dados de teste. Se não fosse pelo teste, poderia ser removida
# para reduzir o acoplamento entre controladores.
from controllers.admin_controller import AdminController

class AgendaController:
    """
    Controlador para gerenciar todas as funcionalidades relacionadas à agenda de vistorias.

    Esta classe é responsável por:
    - Listar horários disponíveis para agendamento e agendamentos existentes.
    - Coordenar o processo de agendamento de novas vistorias, incluindo o cadastro de imóveis.
    - Processar o cancelamento de vistorias agendadas.
    - Gerenciar o estado dos horários na agenda (fechar, reabrir) por administradores ou vistoriadores.
    - Lidar com a adição de horários fixos de trabalho para vistoriadores e disparar
      a geração automática da agenda com base nesses horários.
    """

    def __init__(self):
        """
        Construtor da classe AgendaController.
        Atualmente, não necessita de inicializações complexas.
        """
        pass # Nenhuma inicialização específica requerida no momento

    # --- Seção: Listagem de Horários da Agenda ---
    def listar_horarios_para_agendamento_geral(self, filtro_periodo: str = "Todos os horários") -> List[Dict[str, Any]]:
        """
        Lista os horários disponíveis na agenda para novos agendamentos.

        Utiliza um filtro de período para delimitar a busca (ex: "Hoje", "Esta semana").
        Por padrão, busca em "Todos os horários" futuros disponíveis.

        Args:
            filtro_periodo (str): String que define o intervalo de datas para a busca.
                                  Opções comuns: "Hoje", "Amanhã", "Esta semana", "Próxima semana",
                                  "Este mês", "Todos os horários".

        Returns:
            List[Dict[str, Any]]: Uma lista de dicionários, onde cada dicionário representa
                                  um horário disponível na agenda. Retorna lista vazia se
                                  nenhum horário disponível for encontrado no período.
        """
        # `obter_datas_para_filtro_periodo` converte a string do filtro em datas de início e fim
        data_inicio, data_fim = helpers.obter_datas_para_filtro_periodo(filtro_periodo)
        # Chama a função do modelo para buscar os horários, especificando `apenas_disponiveis=True`
        return agenda_model.listar_horarios_agenda(
            data_inicio=data_inicio,
            data_fim=data_fim,
            apenas_disponiveis=True # Filtro crucial para esta função
        )

    def listar_agendamentos_para_cancelamento(self, filtro_periodo: str = "Todos os agendamentos") -> List[Dict[str, Any]]:
        """
        Lista os horários que já possuem vistorias agendadas, para fins de visualização ou cancelamento.

        Args:
            filtro_periodo (str): String que define o intervalo de datas para a busca
                                  dos agendamentos.

        Returns:
            List[Dict[str, Any]]: Uma lista de dicionários, cada um representando um
                                  agendamento existente.
        """
        data_inicio, data_fim = helpers.obter_datas_para_filtro_periodo(filtro_periodo)
        # Chama a função do modelo, especificando `apenas_agendados=True`
        return agenda_model.listar_horarios_agenda(
            data_inicio=data_inicio,
            data_fim=data_fim,
            apenas_agendados=True # Filtro para retornar apenas horários ocupados
        )

    # --- Seção: Processo de Agendamento de Vistoria ---
    def obter_clientes_para_selecao(self) -> List[Dict[str, Any]]:
        """
        Busca e retorna uma lista de todos os clientes cadastrados.

        Utilizado geralmente em interfaces de usuário para permitir a seleção
        de um cliente ao realizar um novo agendamento.

        Returns:
            List[Dict[str, Any]]: Lista de clientes.
        """
        return usuario_model.listar_todos_clientes()

    def obter_imobiliarias_para_selecao(self) -> List[Dict[str, Any]]:
        """
        Busca e retorna uma lista de todas as imobiliárias cadastradas.

        Utilizado em interfaces para permitir a seleção de uma imobiliária
        associada a um novo agendamento ou cadastro de imóvel.

        Returns:
            List[Dict[str, Any]]: Lista de imobiliárias.
        """
        return imobiliaria_model.listar_todas_imobiliarias()

    def cadastrar_imovel_para_agendamento(self, cod_imovel: str, cliente_id: int, imobiliaria_id: int,
                                          endereco: str, tamanho_str: str, cep: Optional[str] = None,
                                          referencia: Optional[str] = None, mobiliado: str = 'sem_mobilia') -> Dict[str, Any]:
        """
        Valida os dados e cadastra um novo imóvel no sistema.

        Este método é tipicamente chamado como uma etapa preliminar ao agendamento
        de uma vistoria, caso o imóvel ainda não esteja registrado.

        Args:
            cod_imovel (str): Código único de identificação do imóvel.
            cliente_id (int): ID do cliente proprietário ou responsável pelo imóvel.
            imobiliaria_id (int): ID da imobiliária associada ao imóvel (se houver).
            endereco (str): Endereço completo do imóvel.
            tamanho_str (str): Tamanho do imóvel em metros quadrados (como string, ex: "75.5").
            cep (Optional[str]): CEP do imóvel.
            referencia (Optional[str]): Ponto de referência ou complemento do endereço.
            mobiliado (str): Estado de mobília do imóvel ('sem_mobilia', 'semi_mobiliado', 'mobiliado').

        Returns:
            Dict[str, Any]: Dicionário contendo:
                'success' (bool): True se o cadastro for bem-sucedido.
                'message' (str): Mensagem de status.
                'imovel_id' (Optional[int]): ID do imóvel cadastrado, se sucesso.
        """
        # Validação de campos obrigatórios
        if not validators.is_not_empty(cod_imovel) or not validators.is_not_empty(endereco) \
           or not validators.is_not_empty(tamanho_str):
            return {'success': False, 'message': "Código do imóvel, endereço e tamanho são obrigatórios."}

        # Validação se o tamanho é um número positivo
        if not validators.is_positive_float_or_int(tamanho_str):
            return {'success': False, 'message': "Tamanho do imóvel deve ser um número positivo."}
        
        try:
            # Converte a string de tamanho para float, permitindo vírgula como decimal
            tamanho = float(tamanho_str.replace(',', '.'))
        except ValueError:
             return {'success': False, 'message': "Formato inválido para o tamanho do imóvel."}

        # Validação do formato do CEP, se fornecido
        if cep and not validators.is_valid_cep(cep, allow_empty=False): # `allow_empty=False` pois se `cep` existe, não deve ser string vazia.
            return {'success': False, 'message': "Formato de CEP inválido."}

        # Tentativa de cadastrar o imóvel através do modelo
        imovel_id = imovel_model.cadastrar_imovel(
            cod_imovel=cod_imovel, cliente_id=cliente_id, imobiliaria_id=imobiliaria_id,
            endereco=endereco, tamanho=tamanho, cep=cep, referencia=referencia, mobiliado=mobiliado
        )

        if imovel_id:
            return {'success': True, 'message': "Imóvel cadastrado com sucesso.", 'imovel_id': imovel_id}
        else:
            # A falha pode ocorrer por diversas razões, como código de imóvel duplicado (se houver tal restrição no modelo)
            return {'success': False, 'message': "Não foi possível cadastrar o imóvel. Verifique o código do imóvel ou outros dados."}


    def finalizar_agendamento_vistoria(self,
                                       id_agenda_selecionada: int,
                                       tipo_vistoria: str,
                                       imovel_id: int,
                                       forcar_agendamento_unico: bool = False
                                       ) -> Dict[str, Any]:
        """
        Conclui o processo de agendamento de uma vistoria para um imóvel já cadastrado
        em um horário específico da agenda.

        Args:
            id_agenda_selecionada (int): ID da entrada na tabela 'agenda' que representa o horário escolhido.
            tipo_vistoria (str): Tipo da vistoria a ser agendada (ex: 'ENTRADA', 'SAIDA', 'CONFERENCIA').
            imovel_id (int): ID do imóvel (previamente cadastrado) para o qual a vistoria será agendada.
            forcar_agendamento_unico (bool): Se True, ignora algumas regras de verificação de horário duplo
                                            (usar com cautela, pode ser para casos específicos).

        Returns:
            Dict[str, Any]: Dicionário com o resultado da operação:
                'success' (bool): True se o agendamento foi bem-sucedido.
                'message' (str): Mensagem de status.
                'imovel_id' (Optional[int]): Retorna o ID do imóvel para confirmação ou uso posterior.
        """
        # Validação dos parâmetros obrigatórios
        if not all([id_agenda_selecionada, tipo_vistoria, imovel_id]): # `all` verifica se todos são "truthy"
            return {'success': False, 'message': "ID do horário, tipo de vistoria e ID do imóvel são obrigatórios."}
        
        # Validação do tipo de vistoria permitido
        if tipo_vistoria not in ['ENTRADA', 'SAIDA', 'CONFERENCIA']:
             return {'success': False, 'message': "Tipo de vistoria inválido."}
        
        # Chama o modelo para efetivar o agendamento
        sucesso_agendamento, mensagem_agendamento = agenda_model.agendar_vistoria_em_horario(
            id_agenda=id_agenda_selecionada,
            imovel_id=imovel_id,
            tipo_vistoria_agendada=tipo_vistoria,
            ignorar_regras_horario_duplo=forcar_agendamento_unico # Permite flexibilidade controlada
        )

        if not sucesso_agendamento:
            # A `mensagem_agendamento` vinda do modelo deve explicar o motivo da falha
            # (ex: horário indisponível, imóvel já com vistoria marcada próxima, etc.)
            return {'success': False, 'message': f"Falha ao agendar: {mensagem_agendamento}"}

        # Retorna sucesso com a mensagem do modelo e o ID do imóvel agendado
        return {'success': True, 'message': f"Agendamento realizado com sucesso! {mensagem_agendamento}", 'imovel_id': imovel_id}


    # --- Seção: Cancelamento de Agendamento ---
    def cancelar_vistoria_agendada(self, id_agenda: int, id_cliente_responsavel: int) -> Dict[str, Any]:
        """
        Cancela uma vistoria que estava previamente agendada.

        Args:
            id_agenda (int): ID da entrada na agenda correspondente à vistoria a ser cancelada.
            id_cliente_responsavel (int): ID do cliente que solicitou o cancelamento ou ao qual
                                          a vistoria estava associada. Pode ser usado para
                                          registro ou lógica de negócio (ex: cobrança de taxa).

        Returns:
            Dict[str, Any]: Dicionário com o resultado da operação.
        """
        # Validação dos IDs
        if not id_agenda or not id_cliente_responsavel:
             return {'success': False, 'message': "ID do agendamento e ID do cliente são obrigatórios."}

        # Chama o modelo para processar o cancelamento
        sucesso, mensagem = agenda_model.cancelar_agendamento_vistoria(id_agenda, id_cliente_responsavel)
        return {'success': sucesso, 'message': mensagem}

    # --- Seção: Gerenciamento de Horários da Agenda (Visão Admin/Vistoriador) ---
    def listar_horarios_do_vistoriador(self, vistoriador_id: int,
                                       filtro_periodo: str = "Todos os horários",
                                       apenas_agendados: bool = False,
                                       apenas_disponiveis: bool = False,
                                       incluir_fechados: bool = False,
                                       incluir_improdutivas: bool = False, # Parâmetro para incluir vistorias marcadas como improdutivas
                                       data_inicio: Optional[str] = None,  # Permite especificar data de início diretamente
                                       data_fim: Optional[str] = None      # Permite especificar data de fim diretamente
                                       ) -> List[Dict[str, Any]]:
        """
        Lista os horários da agenda para um vistoriador específico, com múltiplos filtros.

        Este método é flexível e pode ser usado tanto pelo VistoriadorController (para
        visualizar sua própria agenda) quanto pelo AdminController (para ver a agenda
        de qualquer vistoriador).

        Args:
            vistoriador_id (int): ID do vistoriador cuja agenda será listada.
            filtro_periodo (str): Filtro de período textual (ex: "Hoje", "Esta semana").
                                  Usado se `data_inicio` e `data_fim` não forem fornecidos.
            apenas_agendados (bool): Se True, retorna apenas horários com vistorias agendadas.
            apenas_disponiveis (bool): Se True, retorna apenas horários livres.
            incluir_fechados (bool): Se True, inclui horários que foram manualmente fechados.
            incluir_improdutivas (bool): Se True, inclui vistorias que foram marcadas como improdutivas.
            data_inicio (Optional[str]): Data de início no formato "YYYY-MM-DD" ou "DD/MM/YYYY"
                                         (será normalizado). Prevalece sobre `filtro_periodo`.
            data_fim (Optional[str]): Data de fim no formato "YYYY-MM-DD" ou "DD/MM/YYYY".
                                      Prevalece sobre `filtro_periodo`.

        Returns:
            List[Dict[str, Any]]: Lista de horários da agenda conforme os filtros.
        """
        # Determina as datas de início e fim para o filtro
        if data_inicio is None and data_fim is None:
            # Se datas explícitas não são dadas, usa o filtro de período textual
            data_inicio_derivada, data_fim_derivada = helpers.obter_datas_para_filtro_periodo(filtro_periodo)
        else:
            # Se datas explícitas são fornecidas, elas têm prioridade.
            # Elas podem estar em formatos diferentes (DD/MM/YYYY ou YYYY-MM-DD),
            # `listar_horarios_agenda` no modelo deve ser capaz de lidar com isso ou
            # precisaríamos normalizá-las aqui antes de passar para o modelo.
            # Assumindo que `listar_horarios_agenda` ou uma camada inferior normaliza.
            data_inicio_derivada = data_inicio
            data_fim_derivada = data_fim

        # Chama o modelo para buscar os horários da agenda com todos os filtros aplicados
        return agenda_model.listar_horarios_agenda(
            vistoriador_id=vistoriador_id,
            data_inicio=data_inicio_derivada,
            data_fim=data_fim_derivada,
            apenas_disponiveis=apenas_disponiveis,
            apenas_agendados=apenas_agendados,
            incluir_fechados=incluir_fechados,
            incluir_improdutivas=incluir_improdutivas # Repassa o novo parâmetro para o modelo
        )

    def fechar_horario_manualmente(self, id_agenda: int, motivo: str, vistoriador_id_responsavel: int) -> Dict[str, Any]:
        """
        Marca um horário específico da agenda como 'FECHADO'.

        Isso impede que o horário seja usado para novos agendamentos e pode ser
        utilizado por um vistoriador para bloquear um horário por motivos pessoais
        ou por um administrador para gerenciar a agenda.

        Args:
            id_agenda (int): ID da entrada na agenda a ser fechada.
            motivo (str): Justificativa para o fechamento do horário.
            vistoriador_id_responsavel (int): ID do vistoriador (ou admin com ID de usuário)
                                              que está realizando a ação.

        Returns:
            Dict[str, Any]: Dicionário com o resultado da operação.
        """
        # Validação de campos obrigatórios
        if not id_agenda or not vistoriador_id_responsavel:
            return {'success': False, 'message': "ID do horário e ID do vistoriador são obrigatórios."}
        if not validators.is_not_empty(motivo): # O motivo é essencial para o registro
            return {'success': False, 'message': "O motivo do fechamento é obrigatório."}

        # Chama o modelo para fechar o horário
        sucesso, mensagem = agenda_model.fechar_horario_agenda(id_agenda, motivo, vistoriador_id_responsavel)
        return {'success': sucesso, 'message': mensagem}

    def reabrir_horario_fechado(self, id_agenda: int, vistoriador_id_responsavel: int) -> Dict[str, Any]:
        """
        Reverte um horário que foi manualmente fechado, tornando-o disponível novamente.

        Args:
            id_agenda (int): ID da entrada na agenda a ser reaberta.
            vistoriador_id_responsavel (int): ID do usuário que está realizando a reabertura.

        Returns:
            Dict[str, Any]: Dicionário com o resultado da operação.
        """
        if not id_agenda or not vistoriador_id_responsavel:
            return {'success': False, 'message': "ID do horário e ID do vistoriador são obrigatórios."}
            
        # Chama o modelo para reabrir o horário
        sucesso, mensagem = agenda_model.reabrir_horario_agenda(id_agenda, vistoriador_id_responsavel)
        return {'success': sucesso, 'message': mensagem}

    def listar_horarios_fechados_do_vistoriador(self, vistoriador_id: int) -> List[Dict[str, Any]]:
        """
        Lista todos os horários que foram manualmente fechados por/para um vistoriador específico.

        Args:
            vistoriador_id (int): ID do vistoriador.

        Returns:
            List[Dict[str, Any]]: Lista de horários fechados.
        """
        # A lógica de filtragem por 'FECHADO' e 'vistoriador_id' está no modelo.
        return agenda_model.listar_horarios_fechados_por_vistoriador(vistoriador_id)

    # --- Seção: Gerenciamento de Horários Fixos e Geração da Agenda Base ---
    def adicionar_horarios_fixos(self, vistoriador_id: int, dias_semana: List[str], horarios: List[str]) -> Dict[str, Any]:
        """
        Adiciona ou atualiza os horários de trabalho fixos para um vistoriador.

        Estes horários são a base para a geração automática da agenda de disponibilidade.
        Este método é um wrapper para a funcionalidade já presente em `AdminController`,
        mas pode ser chamado internamente ou por outras partes do sistema que tenham
        acesso ao `AgendaController`.

        Args:
            vistoriador_id (int): ID do vistoriador.
            dias_semana (List[str]): Lista de nomes dos dias da semana (ex: "Segunda-feira").
                                     O modelo converterá para representação numérica.
            horarios (List[str]): Lista de horários no formato "HH:MM".

        Returns:
            Dict[str, Any]: Dicionário com o resultado da operação.
        """
        # Validações básicas
        if not vistoriador_id or not dias_semana or not horarios:
            return {'success': False, 'message': "ID do vistoriador, dias da semana e horários são obrigatórios."}
        
        # Chama o modelo para cadastrar os horários fixos
        sucesso = agenda_model.cadastrar_horarios_fixos_vistoriador(vistoriador_id, dias_semana, horarios)
        if sucesso:
            # Se os horários fixos foram alterados com sucesso,
            # é importante disparar a regeneração da agenda base para refletir essas mudanças.
            self.disparar_geracao_agenda_automatica() # Chama o método local para regenerar
            return {'success': True, 'message': "Horários fixos cadastrados e agenda atualizada."}
        else:
            # A falha pode ser por horários já existentes ou erro interno no modelo
            return {'success': False, 'message': "Não foi possível cadastrar os horários fixos (verifique se já existem ou houve um erro)."}

    def disparar_geracao_agenda_automatica(self, semanas_a_frente: int = 4) -> Dict[str, Any]:
        """
        Inicia o processo de geração ou atualização da agenda de horários disponíveis.

        Esta função utiliza os horários fixos cadastrados para os vistoriadores
        e preenche a tabela 'agenda' com entradas disponíveis para as próximas semanas.

        Args:
            semanas_a_frente (int): Número de semanas no futuro para as quais a agenda
                                    deve ser gerada/preenchida. Padrão é 4 semanas.

        Returns:
            Dict[str, Any]: Dicionário com o resultado da operação.
        """
        # Chama a função do modelo que contém a lógica principal de geração da agenda
        sucesso = agenda_model.gerar_agenda_baseada_em_horarios_fixos(semanas_a_frente)
        if sucesso:
            return {'success': True, 'message': "Geração/Atualização da agenda concluída."}
        else:
            return {'success': False, 'message': "Erro durante a geração/atualização da agenda."}


# Bloco de execução para testes rápidos do controlador
if __name__ == '__main__':
    agenda_ctrl = AgendaController()
    admin_ctrl = AdminController() # Usado para criar dados de teste (clientes, imobiliárias)
    
    print("\n--- Testando Fluxo de Agendamento com Cadastro de Imóvel Separado ---")
    # Tenta obter dados existentes ou recém-criados para o teste
    clientes = admin_ctrl.listar_todos_clientes_admin()
    if not clientes: # Se não houver clientes, cadastra um de teste
        admin_ctrl.cadastrar_novo_cliente("Cliente Teste Agenda", "cliente.agenda@teste.com")
        clientes = admin_ctrl.listar_todos_clientes_admin()

    imobiliarias = admin_ctrl.listar_todas_imobiliarias_admin()
    if not imobiliarias: # Se não houver imobiliárias, cadastra uma de teste
        admin_ctrl.cadastrar_nova_imobiliaria("Imob Teste Agenda", "10", "12", "15")
        imobiliarias = admin_ctrl.listar_todas_imobiliarias_admin()
    
    # Para testar agendamento, precisamos de horários disponíveis.
    # Primeiro, garantir que haja um vistoriador com horários fixos.
    vistoriadores = admin_ctrl.listar_todos_vistoriadores()
    id_vist_teste = None
    if vistoriadores:
        id_vist_teste = vistoriadores[0]['id']
        # Adiciona horários fixos para este vistoriador, se ainda não tiver muitos, para garantir disponibilidade
        # (Esta lógica de "se não tiver muitos" é simplificada, idealmente verificaria horários específicos)
        horarios_fixos_existentes = admin_ctrl.listar_horarios_fixos_de_vistoriador(id_vist_teste)
        if len(horarios_fixos_existentes) < 2:
             admin_ctrl.adicionar_horarios_fixos_para_vistoriador(
                id_vist_teste, ["Segunda-feira"], ["09:00", "10:00"]
            )
    else: # Se não houver vistoriador, cadastra um
        res_cad_vist = admin_ctrl.cadastrar_novo_vistoriador("Vist Teste Agenda", "vist.agenda@teste.com", "123456", "123456")
        if res_cad_vist['success']:
            id_vist_teste = res_cad_vist['id']
            admin_ctrl.adicionar_horarios_fixos_para_vistoriador(
                id_vist_teste, ["Terça-feira"], ["14:00", "15:00"]
            )
            
    if id_vist_teste:
         # Dispara a geração da agenda para garantir que os horários fixos sejam refletidos
        print(f"Disparando geração de agenda para vistoriador ID {id_vist_teste}...")
        agenda_ctrl.disparar_geracao_agenda_automatica()


    # Agora, tenta listar horários disponíveis
    horarios_disponiveis = agenda_ctrl.listar_horarios_para_agendamento_geral("Esta semana")
    if not horarios_disponiveis: # Tenta próxima semana se esta não tiver
        horarios_disponiveis = agenda_ctrl.listar_horarios_para_agendamento_geral("Próxima semana")


    if clientes and imobiliarias and horarios_disponiveis:
        cliente_teste = clientes[0]
        imobiliaria_teste = imobiliarias[0]
        horario_teste = horarios_disponiveis[0] # Pega o primeiro horário disponível encontrado
        
        # Cria um código de imóvel único para o teste
        cod_imovel_unico = f"VIEWTEST{datetime.datetime.now().strftime('%H%M%S%f')[-6:]}" # Sufixo para unicidade

        print(f"\nCliente para teste: {cliente_teste['nome']} (ID: {cliente_teste['id']})")
        print(f"Imobiliária para teste: {imobiliaria_teste['nome']} (ID: {imobiliaria_teste['id']})")
        print(f"Horário para teste: ID Agenda {horario_teste['id_agenda']} em {horario_teste['data']} às {horario_teste['horario']} com Vist. ID {horario_teste['vistoriador_id']}")

        print(f"\n1. Cadastrando imóvel '{cod_imovel_unico}' para cliente ID {cliente_teste['id']} e imobiliária ID {imobiliaria_teste['id']}")
        
        res_cad_imovel = agenda_ctrl.cadastrar_imovel_para_agendamento(
            cod_imovel=cod_imovel_unico,
            cliente_id=cliente_teste['id'],
            imobiliaria_id=imobiliaria_teste['id'],
            endereco="Rua da View de Teste Agendamento, 789",
            tamanho_str="65,5", # Testando com vírgula
            cep="74001001", # CEP de exemplo
            mobiliado="semi_mobiliado",
            referencia="Próximo ao parque de testes"
        )
        print(f"--> Resultado cadastro imóvel: {res_cad_imovel}")

        if res_cad_imovel['success']:
            imovel_id_criado = res_cad_imovel['imovel_id']
            print(f"\n2. Imóvel ID {imovel_id_criado} cadastrado. Tentando agendar vistoria de ENTRADA no horário ID {horario_teste['id_agenda']}...")

            resultado_final = agenda_ctrl.finalizar_agendamento_vistoria(
                id_agenda_selecionada=horario_teste['id_agenda'],
                tipo_vistoria="ENTRADA",
                imovel_id=imovel_id_criado
            )
            print(f"--> Resultado finalização agendamento: {resultado_final}")

            if resultado_final['success']:
                print("\n--- Agendamento realizado com sucesso! Verificando lista de agendamentos para cancelamento...")
                agendamentos_cancel = agenda_ctrl.listar_agendamentos_para_cancelamento("Esta semana") # ou filtro do horário_teste
                ag_realizado = next((ag for ag in agendamentos_cancel if ag['id_agenda'] == horario_teste['id_agenda']), None)
                if ag_realizado:
                    print(f"Agendamento encontrado: {ag_realizado}")
                    print(f"\n3. Tentando cancelar o agendamento ID {ag_realizado['id_agenda']}...")
                    res_cancel = agenda_ctrl.cancelar_vistoria_agendada(ag_realizado['id_agenda'], cliente_teste['id'])
                    print(f"--> Resultado cancelamento: {res_cancel}")
                else:
                    print("ERRO: Agendamento recém-criado não encontrado na lista para cancelamento.")
        else:
            print("Falha ao cadastrar imóvel, agendamento não prosseguiu.")
    else:
        print("\n--- FIM DOS TESTES ---")
        if not clientes: print("❌ Dados insuficientes para teste: Nenhum cliente encontrado ou cadastrado.")
        if not imobiliarias: print("❌ Dados insuficientes para teste: Nenhuma imobiliária encontrada ou cadastrada.")
        if not horarios_disponiveis: print("❌ Dados insuficientes para teste: Nenhum horário disponível encontrado. Verifique cadastro de vistoriadores, horários fixos e geração da agenda.")

    pass

