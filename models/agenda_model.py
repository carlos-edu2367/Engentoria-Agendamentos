# engentoria/models/agenda_model.py
import sqlite3 # Biblioteca para interagir com bancos de dados SQLite
import datetime as dt # Biblioteca para manipulação de datas e horas
import pandas as pd # Biblioteca para manipulação de dados, especialmente para relatórios
from .database import conectar_banco # Função para conectar ao banco de dados (do mesmo pacote)
# Importações de outros modelos para funcionalidades interdependentes:
# - imovel_model: para regras de horários, obter dados do imóvel, calcular valor, deletar imóvel.
# - usuario_model: para deletar cliente.
from .imovel_model import regras_necessita_dois_horarios, obter_imovel_por_id, calcular_valor_vistoriador, listar_todos_imoveis, deletar_imovel_por_id as deletar_imovel_associado
from .usuario_model import deletar_cliente_por_id, obter_cliente_por_id
from typing import Optional, List, Dict, Any, Tuple # Tipos para anotações estáticas
import logging # Biblioteca para logging de eventos e erros

# Configuração básica do logging para registrar informações, avisos e erros.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def deletar_agendamentos_antigos_e_dados_relacionados(meses_antiguidade: int = 3) -> Dict[str, int]:
    """
    Deleta agendamentos da tabela 'agenda' mais antigos que um número especificado de meses.

    Antes de deletar uma entrada da agenda, esta função tenta:
    1. Deletar registros correspondentes na tabela 'vistorias_improdutivas'
       (devido à constraint ON DELETE RESTRICT na FK `vistorias_improdutivas.agenda_id_original`).
    Após deletar a entrada da agenda:
    2. Deleta o imóvel associado (se houver) através de `deletar_imovel_associado`.
    3. Se o imóvel foi deletado e tinha um cliente associado, tenta deletar o cliente
       através de `deletar_cliente_por_id`. Esta é uma ação potencialmente destrutiva.

    As deleções em `horarios_fechados` são tratadas por ON DELETE CASCADE na FK `agenda_id`.

    Args:
        meses_antiguidade (int): Número de meses para definir o quão antigo um agendamento
                                 deve ser para ser considerado para deleção. Padrão é 3 meses.

    Returns:
        Dict[str, int]: Um dicionário contendo a contagem de cada tipo de item deletado
                        e o número de erros encontrados durante a deleção de agendamentos.
                        Ex: {'agendamentos_deletados': X, 'vistorias_improdutivas_deletadas': Y, ...}
    """
    # Dicionário para armazenar contagens das deleções e erros
    contadores = {
        'agendamentos_deletados': 0,
        'vistorias_improdutivas_deletadas': 0,
        'imoveis_deletados': 0,
        'clientes_deletados': 0,
        'erros_delecao_agendamento': 0
    }
    conexao = None # Inicializa a variável de conexão
    try:
        conexao = conectar_banco() # Estabelece conexão com o banco
        cursor = conexao.cursor() # Cria um cursor para executar queries
        cursor.execute("PRAGMA foreign_keys = ON;") # Garante que as chaves estrangeiras sejam respeitadas

        # Calcula a data limite para deleção (N meses atrás a partir de hoje)
        # Aproximação de meses como 30 dias cada
        data_limite = dt.date.today() - dt.timedelta(days=meses_antiguidade * 30)
        data_limite_str = data_limite.strftime("%Y-%m-%d") # Formata a data para a query SQL
        logging.info(f"Rotina de limpeza: Deletando agendamentos anteriores a {data_limite_str}.")

        # 1. Encontrar agendamentos antigos e seus imóveis/clientes associados
        # Seleciona IDs de agenda, imóvel e cliente para agendamentos mais antigos que a data_limite.
        cursor.execute("""
            SELECT a.id as agenda_id, a.imovel_id, i.cliente_id
            FROM agenda a
            LEFT JOIN imoveis i ON a.imovel_id = i.id
            WHERE a.data < ?
        """, (data_limite_str,))
        agendamentos_antigos = cursor.fetchall() # Coleta todos os resultados

        if not agendamentos_antigos:
            logging.info("Nenhum agendamento antigo encontrado para deletar.")
            return contadores # Retorna contadores zerados se não houver nada a fazer

        logging.info(f"Encontrados {len(agendamentos_antigos)} agendamentos antigos para processar.")

        # Itera sobre cada agendamento antigo encontrado
        for agenda_id, imovel_id, cliente_id in agendamentos_antigos:
            logging.info(f"Processando agendamento ID: {agenda_id}, Imóvel ID: {imovel_id}, Cliente ID: {cliente_id}")
            
            try:
                # 2. Tentar deletar vistorias improdutivas associadas ao agendamento
                # A FK em `vistorias_improdutivas.agenda_id_original` é ON DELETE RESTRICT.
                # Portanto, é necessário deletar estas entradas antes de deletar o agendamento da `agenda`.
                cursor.execute("DELETE FROM vistorias_improdutivas WHERE agenda_id_original = ?", (agenda_id,))
                if cursor.rowcount > 0: # Se alguma linha foi afetada (deletada)
                    contadores['vistorias_improdutivas_deletadas'] += cursor.rowcount
                    logging.info(f"  {cursor.rowcount} vistoria(s) improdutiva(s) associada(s) ao agendamento ID {agenda_id} deletada(s).")

                # 3. Tentar deletar o agendamento da tabela 'agenda'
                # A FK `horarios_fechados.agenda_id` para `agenda.id` é ON DELETE CASCADE,
                # então entradas em `horarios_fechados` serão deletadas automaticamente.
                cursor.execute("DELETE FROM agenda WHERE id = ?", (agenda_id,))
                
                if cursor.rowcount > 0: # Se o agendamento foi efetivamente deletado
                    contadores['agendamentos_deletados'] += 1
                    logging.info(f"  Agendamento ID {agenda_id} deletado.")

                    # 4. Se o agendamento foi deletado e tinha um imóvel associado
                    if imovel_id:
                        # Deleta o imóvel associado. A função `deletar_imovel_associado` (alias para `deletar_imovel_por_id`)
                        # deve lidar com suas próprias FKs (ex: `agenda.imovel_id` que é ON DELETE SET NULL).
                        # Passa a conexão existente para reuso dentro da mesma transação (se `deletar_imovel_associado` suportar).
                        if deletar_imovel_associado(imovel_id, conexao_existente=conexao):
                            contadores['imoveis_deletados'] += 1
                            logging.info(f"    Imóvel ID {imovel_id} associado ao agendamento antigo deletado.")
                            
                            # 5. Se o imóvel foi deletado e tinha um cliente associado
                            # Esta é uma ação agressiva: deletar o cliente se seu (único?) imóvel associado a um agendamento antigo foi deletado.
                            # Considerar se esta é a lógica desejada.
                            if cliente_id:
                                # Verifica se o cliente ainda existe antes de tentar deletar,
                                # para evitar erros ou contagem dupla se já foi deletado por outro processo.
                                cursor.execute("SELECT 1 FROM clientes WHERE id = ?", (cliente_id,))
                                if cursor.fetchone(): # Se o cliente ainda existe
                                    # `deletar_cliente_por_id` deve lidar com FKs (ex: `imoveis.cliente_id` é ON DELETE CASCADE).
                                    if deletar_cliente_por_id(cliente_id, conexao_existente=conexao):
                                        contadores['clientes_deletados'] += 1
                                        logging.info(f"      Cliente ID {cliente_id} associado ao imóvel deletado.")
                                    else:
                                        logging.warning(f"      Falha ao deletar cliente ID {cliente_id} (pode ter outras dependências não CASCADE).")
                                else:
                                    logging.info(f"      Cliente ID {cliente_id} já não existia ou foi deletado anteriormente.")
                        else:
                            logging.warning(f"    Falha ao deletar imóvel ID {imovel_id} associado ao agendamento antigo.")
                else:
                    # Agendamento não deletado (pode já ter sido deletado em iteração anterior ou erro)
                    logging.warning(f"  Agendamento ID {agenda_id} não pode ser deletado (ou já foi deletado).")

            except sqlite3.IntegrityError as e: # Captura erros de integridade específicos do SQLite
                contadores['erros_delecao_agendamento'] += 1
                logging.error(f"  Erro de integridade ao tentar deletar agendamento ID {agenda_id} ou seus relacionados: {e}")
                # Não faz rollback aqui para permitir que outras deleções prossigam.
                # Idealmente, cada "unidade de trabalho" (deleção de um agendamento e seus dependentes)
                # poderia ser uma transação separada.
            except Exception as e_gen: # Captura outros erros genéricos
                contadores['erros_delecao_agendamento'] += 1
                logging.error(f"  Erro geral ao processar agendamento ID {agenda_id}: {e_gen}", exc_info=True)
        
        conexao.commit() # Confirma todas as deleções bem-sucedidas no banco
        logging.info(f"Limpeza de agendamentos antigos concluída. Resumo: {contadores}")

    except Exception as e: # Erro na configuração da função ou conexão
        logging.error(f"Erro geral na função deletar_agendamentos_antigos_e_dados_relacionados: {e}", exc_info=True)
        if conexao:
            conexao.rollback() # Desfaz quaisquer alterações se um erro maior ocorreu
    finally:
        if conexao:
            conexao.close() # Garante que a conexão seja fechada
    return contadores


def registrar_vistoria_improdutiva(
    agenda_id_original: int,
    cliente_id: int,
    imovel_id: Optional[int], # ID do imóvel pode ser opcional se a vistoria não estava atrelada a um específico
    imobiliaria_id: Optional[int], # ID da imobiliária também pode ser opcional
    data_vistoria_original_str: str, # Data em que a vistoria deveria ter ocorrido
    horario_vistoria_original_str: str, # Horário em que a vistoria deveria ter ocorrido
    motivo: str, # Motivo pelo qual a vistoria foi improdutiva
    valor_cobranca: float # Valor a ser cobrado do cliente pela improdutividade
) -> Tuple[bool, str]:
    """
    Registra uma vistoria como improdutiva no sistema.

    Esta função executa as seguintes ações:
    1. Insere um novo registro na tabela `vistorias_improdutivas`, incluindo o
       cálculo do valor a ser pago ao vistoriador (30% do `valor_cobranca`).
    2. Atualiza o `saldo_devedor_total` do cliente na tabela `clientes`, somando o `valor_cobranca`.
    3. Atualiza o `tipo` da entrada original na tabela `agenda` para 'IMPRODUTIVA' e a marca
       como não disponível (`disponivel = 0`), se ela não for 'LIVRE', 'FECHADO' ou já 'IMPRODUTIVA'.

    Args:
        agenda_id_original (int): ID da entrada na tabela `agenda` que corresponde à vistoria original.
        cliente_id (int): ID do cliente responsável.
        imovel_id (Optional[int]): ID do imóvel associado, se houver.
        imobiliaria_id (Optional[int]): ID da imobiliária associada, se houver.
        data_vistoria_original_str (str): Data da vistoria original (formato "YYYY-MM-DD").
        horario_vistoria_original_str (str): Horário da vistoria original (formato "HH:MM").
        motivo (str): Descrição do motivo da improdutividade.
        valor_cobranca (float): Valor a ser cobrado do cliente.

    Returns:
        Tuple[bool, str]: Uma tupla contendo:
            - bool: True se o registro foi bem-sucedido, False caso contrário.
            - str: Mensagem de status descrevendo o resultado da operação.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;") # Ativa chaves estrangeiras

        # Data em que a vistoria está sendo marcada como improdutiva (hoje)
        data_marcacao_str = dt.date.today().strftime("%Y-%m-%d")
        
        # Calcula o valor a ser repassado ao vistoriador (30% do valor da cobrança ao cliente)
        valor_para_vistoriador_calc = round(valor_cobranca * 0.30, 2)
        # Logging para depuração do cálculo
        logging.debug(f"Calculando valor para vistoriador (improdutiva): {valor_cobranca} * 0.30 = {valor_para_vistoriador_calc}")

        # 1. Insere o registro na tabela `vistorias_improdutivas`
        # O campo 'pago' é definido como 0 (False) por padrão.
        cursor.execute("""
            INSERT INTO vistorias_improdutivas (
                agenda_id_original, cliente_id, imovel_id, imobiliaria_id,
                data_marcacao, data_vistoria_original, horario_vistoria_original,
                motivo_improdutividade, valor_cobranca, valor_para_vistoriador, pago
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            agenda_id_original, cliente_id, imovel_id, imobiliaria_id,
            data_marcacao_str, data_vistoria_original_str, horario_vistoria_original_str,
            motivo, valor_cobranca, valor_para_vistoriador_calc # Salva o valor calculado para o vistoriador
        ))
        id_improdutiva = cursor.lastrowid # Obtém o ID do registro recém-inserido

        # 2. Atualiza o saldo devedor do cliente
        # COALESCE(saldo_devedor_total, 0) trata casos onde o saldo pode ser NULL, convertendo para 0 antes de somar.
        cursor.execute("""
            UPDATE clientes
            SET saldo_devedor_total = COALESCE(saldo_devedor_total, 0) + ?
            WHERE id = ?
        """, (valor_cobranca, cliente_id))

        # 3. Atualiza o status do agendamento original na tabela `agenda`
        # Define o tipo como 'IMPRODUTIVA' e `disponivel = 0`.
        # A condição `tipo NOT IN ('LIVRE', 'FECHADO', 'IMPRODUTIVA')` previne que horários
        # que já não são vistorias ativas (ex: um horário livre ou já fechado) sejam indevidamente alterados.
        cursor.execute("""
            UPDATE agenda
            SET tipo = 'IMPRODUTIVA', disponivel = 0
            WHERE id = ? AND tipo NOT IN ('LIVRE', 'FECHADO', 'IMPRODUTIVA')
        """, (agenda_id_original,))
        
        if cursor.rowcount == 0: # Se nenhuma linha na `agenda` foi atualizada
            # Isso pode ocorrer se o horário original já era 'LIVRE', 'FECHADO' ou já 'IMPRODUTIVA'.
            # A interface de usuário (View/Controller) deveria idealmente prevenir a tentativa de marcar
            # tais horários como improdutivos, mas um log aqui é útil.
            logging.warning(f"Agendamento ID {agenda_id_original} não pôde ser marcado como IMPRODUTIVA (status atual pode impedir ou já é IMPRODUTIVA).")

        conexao.commit() # Confirma as alterações no banco
        # Mensagem de sucesso detalhada
        msg = (f"✅ Vistoria ID {agenda_id_original} marcada como improdutiva (ID Improd.: {id_improdutiva}).\n"
               f"Cobrança de R${valor_cobranca:.2f} registrada para cliente ID {cliente_id}.\n"
               f"Valor para vistoriador: R${valor_para_vistoriador_calc:.2f}.\n"
               f"Saldo do cliente atualizado.")
        logging.info(msg)
        return True, msg
    except sqlite3.IntegrityError as ie: # Erro de integridade (ex: FK não encontrada)
        logging.error(f"Erro de integridade ao registrar vistoria improdutiva para agenda ID {agenda_id_original}: {ie}")
        if conexao:
            conexao.rollback()
        return False, f"Erro de integridade: {ie}"
    except Exception as e: # Outros erros
        logging.error(f"Erro ao registrar vistoria improdutiva para agenda ID {agenda_id_original}: {e}", exc_info=True)
        if conexao:
            conexao.rollback()
        return False, f"Erro ao registrar vistoria improdutiva: {e}"
    finally:
        if conexao:
            conexao.close()

# --- Funções de Gerenciamento de Horários Fixos dos Vistoriadores ---
def cadastrar_horarios_fixos_vistoriador(vistoriador_id: int, dias_semana_num_str: List[str], horarios_str_lista: List[str]) -> bool:
    """
    Cadastra múltiplos horários de trabalho fixos para um vistoriador.

    Os horários fixos definem a disponibilidade padrão do vistoriador e são usados
    para gerar automaticamente as entradas na tabela `agenda`.

    Args:
        vistoriador_id (int): ID do vistoriador.
        dias_semana_num_str (List[str]): Lista de strings representando os dias da semana
                                         (ex: '0' para Domingo, '1' para Segunda, ..., '6' para Sábado).
                                         A convenção exata do número para dia deve ser consistente
                                         com `datetime.weekday()` ou `isoweekday()` conforme usado na
                                         geração da agenda.
        horarios_str_lista (List[str]): Lista de strings de horários no formato "HH:MM" (ex: "09:00", "14:30").

    Returns:
        bool: True se pelo menos um novo horário fixo foi adicionado, False caso contrário
              (ou se ocorrer um erro).
    """
    # Validação básica dos argumentos
    if not vistoriador_id or not dias_semana_num_str or not horarios_str_lista:
        logging.warning("Vistoriador ID, dias da semana e horários são obrigatórios para cadastrar horários fixos.")
        return False
        
    conexao = None
    horarios_adicionados_count = 0 # Contador para novos horários efetivamente adicionados
    # Mapa para traduzir número do dia para nome (usado em logs)
    dias_map_nomes = {'0': 'Domingo', '1': 'Segunda-feira', '2': 'Terça-feira', '3': 'Quarta-feira', '4': 'Quinta-feira', '5': 'Sexta-feira', '6': 'Sábado'}

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        # Itera sobre cada dia da semana fornecido
        for dia_num_str_atual in dias_semana_num_str:
            # Valida se o número do dia é um dos permitidos ('0' a '6')
            if dia_num_str_atual not in dias_map_nomes:
                logging.warning(f"Dia da semana inválido fornecido: '{dia_num_str_atual}'. Ignorando.")
                continue # Pula para o próximo dia

            # Itera sobre cada horário fornecido para o dia atual
            for horario_str_atual in horarios_str_lista:
                try:
                    # Valida o formato do horário (HH:MM)
                    dt.datetime.strptime(horario_str_atual, "%H:%M")
                except ValueError:
                    logging.warning(f"Formato de horário inválido: '{horario_str_atual}'. Ignorando para o dia {dias_map_nomes.get(dia_num_str_atual, dia_num_str_atual)}.")
                    continue # Pula para o próximo horário

                # Tenta inserir o horário fixo no banco de dados
                # A tabela `horarios_fixos` tem uma constraint UNIQUE em (vistoriador_id, dia_semana, horario)
                # para evitar duplicatas.
                try:
                    cursor.execute("INSERT INTO horarios_fixos (vistoriador_id, dia_semana, horario) VALUES (?, ?, ?)",
                                   (vistoriador_id, dia_num_str_atual, horario_str_atual))
                    horarios_adicionados_count += 1 # Incrementa se a inserção foi bem-sucedida
                except sqlite3.IntegrityError:
                    # Ocorre se o horário fixo já existir (devido à constraint UNIQUE)
                    logging.info(f"Horário fixo já existente (ou conflito): Vist. ID {vistoriador_id}, Dia {dias_map_nomes.get(dia_num_str_atual, dia_num_str_atual)}, Hora {horario_str_atual}")
                except Exception as e_inner: # Outro erro durante a inserção
                    logging.error(f"Erro ao inserir horário fixo ({dias_map_nomes.get(dia_num_str_atual, dia_num_str_atual)}, {horario_str_atual}) para Vist. ID {vistoriador_id}: {e_inner}")
        
        # Se algum horário foi adicionado, commita as alterações
        if horarios_adicionados_count > 0:
            conexao.commit()
            logging.info(f"{horarios_adicionados_count} horários fixos adicionados para o vistoriador ID {vistoriador_id}.")
        else:
            logging.info(f"Nenhum novo horário fixo foi adicionado para o vistoriador ID {vistoriador_id} (podem já existir ou dados inválidos).")
        
        return horarios_adicionados_count > 0 # Retorna True se houve sucesso em adicionar pelo menos um
    except Exception as e: # Erro geral na função
        logging.error(f"Erro ao cadastrar horários fixos para vistoriador ID {vistoriador_id}: {e}", exc_info=True)
        if conexao: conexao.rollback()
        return False
    finally:
        if conexao: conexao.close()

def remover_horario_fixo_especifico(vistoriador_id: int, dia_semana_num_str: str, horario_str: str) -> bool:
    """
    Remove um horário de trabalho fixo específico de um vistoriador.

    Args:
        vistoriador_id (int): ID do vistoriador.
        dia_semana_num_str (str): String do número do dia da semana (ex: '0'-'6').
        horario_str (str): Horário a ser removido (formato "HH:MM").

    Returns:
        bool: True se o horário foi removido com sucesso, False caso contrário.
    """
    if not vistoriador_id or not dia_semana_num_str or not horario_str:
        logging.warning("Vistoriador ID, dia da semana e horário são obrigatórios para remoção de horário fixo.")
        return False
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM horarios_fixos WHERE vistoriador_id = ? AND dia_semana = ? AND horario = ?",
                       (vistoriador_id, dia_semana_num_str, horario_str))
        conexao.commit()
        if cursor.rowcount > 0: # `rowcount` indica o número de linhas afetadas
            logging.info(f"Horário fixo (Dia: {dia_semana_num_str}, Hora: {horario_str}) removido para o vistoriador ID {vistoriador_id}.")
            return True
        else:
            logging.info(f"Nenhum horário fixo correspondente (Dia: {dia_semana_num_str}, Hora: {horario_str}) encontrado para remover para o vistoriador ID {vistoriador_id}.")
            return False # Horário não existia ou não pertencia ao vistoriador
    except Exception as e:
        logging.error(f"Erro ao remover horário fixo específico para Vist. ID {vistoriador_id}: {e}", exc_info=True)
        if conexao: conexao.rollback()
        return False
    finally:
        if conexao: conexao.close()

def listar_horarios_fixos_por_vistoriador(vistoriador_id: int) -> List[Dict[str, str]]:
    """
    Lista todos os horários de trabalho fixos de um vistoriador específico.

    Args:
        vistoriador_id (int): ID do vistoriador.

    Returns:
        List[Dict[str, str]]: Uma lista de dicionários, cada um contendo 'dia_semana' (str numérica)
                               e 'horario' (str "HH:MM"). Retorna lista vazia em caso de erro
                               ou se não houver horários.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Ordena por dia da semana e depois por horário para uma listagem consistente
        cursor.execute("SELECT dia_semana, horario FROM horarios_fixos WHERE vistoriador_id = ? ORDER BY dia_semana, horario", (vistoriador_id,))
        fixos_db = cursor.fetchall() # Lista de tuplas
        # Converte a lista de tuplas em uma lista de dicionários para facilitar o uso
        return [{'dia_semana': row[0], 'horario': row[1]} for row in fixos_db]
    except Exception as e:
        logging.error(f"Erro ao listar horários fixos do vistoriador ID {vistoriador_id}: {e}", exc_info=True)
        return [] # Retorna lista vazia em caso de erro
    finally:
        if conexao: conexao.close()

def adicionar_entrada_agenda_unica(vistoriador_id: int, data_str_ymd: str, horario_str_hm: str,
                                   tipo: str = 'LIVRE', disponivel: bool = True,
                                   imovel_id: Optional[int] = None) -> Tuple[bool, str]:
    """
    Adiciona uma entrada avulsa na tabela `agenda` para um vistoriador.

    Pode ser usado para adicionar disponibilidade extra ou um agendamento direto
    (embora agendamentos geralmente passem por `agendar_vistoria_em_horario`).

    Args:
        vistoriador_id (int): ID do vistoriador.
        data_str_ymd (str): Data no formato "YYYY-MM-DD".
        horario_str_hm (str): Horário no formato "HH:MM".
        tipo (str): Tipo da entrada na agenda (padrão 'LIVRE').
        disponivel (bool): Se o horário está disponível (padrão True).
        imovel_id (Optional[int]): ID do imóvel, se já for um agendamento direto.

    Returns:
        Tuple[bool, str]: (sucesso, mensagem de status).
    """
    # Validações dos argumentos
    if not all([vistoriador_id, data_str_ymd, horario_str_hm]):
        return False, "Vistoriador ID, data e horário são obrigatórios para adicionar entrada na agenda."
    try:
        # Valida o formato da data e do horário
        dt.datetime.strptime(data_str_ymd, "%Y-%m-%d")
        dt.datetime.strptime(horario_str_hm, "%H:%M")
    except ValueError:
        return False, "Formato de data (YYYY-MM-DD) ou horário (HH:MM) inválido."
        
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Insere a nova entrada na agenda.
        # A tabela `agenda` tem UNIQUE (vistoriador_id, data, horario).
        cursor.execute("INSERT INTO agenda (vistoriador_id, data, horario, disponivel, tipo, imovel_id) VALUES (?, ?, ?, ?, ?, ?)",
                       (vistoriador_id, data_str_ymd, horario_str_hm, 1 if disponivel else 0, tipo, imovel_id))
        conexao.commit()
        id_agenda = cursor.lastrowid # ID da entrada recém-criada
        return True, f"Horário avulso (ID Agenda: {id_agenda}) adicionado para {data_str_ymd} às {horario_str_hm} para o vistoriador ID {vistoriador_id}."
    except sqlite3.IntegrityError: # Ocorre se já existe uma entrada para mesmo vistoriador, data e hora
        return False, f"Este horário ({data_str_ymd} às {horario_str_hm}) já existe na agenda para este vistoriador."
    except Exception as e:
        if conexao: conexao.rollback()
        logging.error(f"Erro ao adicionar horário avulso na agenda para Vist. ID {vistoriador_id}: {e}", exc_info=True)
        return False, f"Erro ao adicionar horário avulso na agenda: {e}"
    finally:
        if conexao: conexao.close()

def gerar_agenda_baseada_em_horarios_fixos(semanas_a_frente: int = 4) -> bool:
    """
    Popula a tabela `agenda` com horários disponíveis baseados nos `horarios_fixos`
    dos vistoriadores para um número especificado de semanas à frente.

    Verifica se já existe uma entrada para o vistoriador, data e horário antes de inserir,
    usando "INSERT OR IGNORE" para evitar duplicatas e erros.

    Args:
        semanas_a_frente (int): Número de semanas futuras para as quais a agenda será gerada. Padrão 4.

    Returns:
        bool: True se o processo foi concluído (mesmo que nenhuma nova entrada seja criada),
              False se ocorreu um erro grave.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Busca IDs de todos os vistoriadores que possuem horários fixos cadastrados
        cursor.execute("SELECT DISTINCT vistoriador_id FROM horarios_fixos")
        vistoriadores_ids = [row[0] for row in cursor.fetchall()]

        if not vistoriadores_ids:
            logging.info("Nenhum vistoriador com horários fixos cadastrados para gerar agenda.")
            return True # Considera sucesso, pois não há o que fazer

        hoje = dt.date.today() # Data atual
        entradas_criadas = 0 # Contador de novas entradas na agenda

        # Itera sobre cada vistoriador que tem horários fixos
        for vist_id_atual in vistoriadores_ids:
            # Busca os horários fixos específicos deste vistoriador
            cursor.execute("SELECT dia_semana, horario FROM horarios_fixos WHERE vistoriador_id = ?", (vist_id_atual,))
            horarios_fixos_do_vistoriador = cursor.fetchall()

            # Itera sobre os próximos N dias (semanas_a_frente * 7)
            for i in range(semanas_a_frente * 7):
                data_iteracao = hoje + dt.timedelta(days=i) # Calcula a data futura
                # Converte o dia da semana da data_iteracao para o formato numérico string ('0'-'6')
                # Usando isoweekday(): 1 (Segunda) a 7 (Domingo). Ajusta para 0 (Domingo) a 6 (Sábado)
                # se a convenção de `horarios_fixos.dia_semana` for 0=Dom, 1=Seg, ...
                # Se `horarios_fixos.dia_semana` é 0=Seg, 1=Ter, ..., 6=Dom, então:
                # dia_semana_sqlite_num_str = str(data_iteracao.weekday()) # weekday(): 0 (Segunda) a 6 (Domingo)
                # Assumindo que a convenção no DB para dia_semana é:
                # 0=Dom, 1=Seg, ..., 6=Sab. Python: date.weekday() é 0=Seg..6=Dom. date.isoweekday() é 1=Seg..7=Dom.
                # Se `dia_semana` na DB é 0-6 (Seg-Dom), usamos `data_iteracao.weekday()`
                # Se `dia_semana` na DB é 0-6 (Dom-Sab), usamos `(data_iteracao.isoweekday() % 7)`
                dia_semana_iteracao_num_str = str(data_iteracao.isoweekday() % 7) # Converte para 0 (Domingo) a 6 (Sábado)

                # Compara com os horários fixos do vistoriador
                for dia_fixo_db_num_str, horario_fixo_str_db in horarios_fixos_do_vistoriador:
                    if dia_fixo_db_num_str == dia_semana_iteracao_num_str: # Se o dia da semana bate
                        data_formatada_db = data_iteracao.strftime("%Y-%m-%d") # Formato YYYY-MM-DD
                        try:
                            # Tenta inserir na agenda. "INSERT OR IGNORE" previne erro se a entrada já existir
                            # (devido à constraint UNIQUE na agenda).
                            cursor.execute("""
                                INSERT OR IGNORE INTO agenda 
                                (vistoriador_id, data, horario, disponivel, imovel_id, tipo) 
                                VALUES (?, ?, ?, 1, NULL, 'LIVRE')
                            """, (vist_id_atual, data_formatada_db, horario_fixo_str_db))
                            if cursor.rowcount > 0: # Se uma nova linha foi inserida
                                entradas_criadas +=1
                        except Exception as e_inner: # Erro específico na inserção (improvável com OR IGNORE, mas por segurança)
                            logging.error(f"Erro ao tentar inserir na agenda para vist. {vist_id_atual} em {data_formatada_db} {horario_fixo_str_db}: {e_inner}")
        
        if entradas_criadas > 0:
            conexao.commit() # Salva as novas entradas criadas
            logging.info(f"Agenda gerada/atualizada com {entradas_criadas} novas entradas.")
        else:
            logging.info("Nenhuma nova entrada necessária na agenda (pode já estar atualizada ou sem horários fixos aplicáveis no período).")
        return True # Processo concluído
    except Exception as e:
        logging.error(f"Erro geral ao gerar agenda baseada em horários fixos: {e}", exc_info=True)
        if conexao: conexao.rollback()
        return False # Indica falha
    finally:
        if conexao: conexao.close()

def listar_horarios_agenda(
    vistoriador_id: Optional[int] = None,
    data_inicio: Optional[str] = None, # Formato YYYY-MM-DD ou DD/MM/YYYY (helper deve normalizar)
    data_fim: Optional[str] = None,    # Formato YYYY-MM-DD ou DD/MM/YYYY (helper deve normalizar)
    apenas_disponiveis: Optional[bool] = None, # True para listar apenas horários com status 'LIVRE' e disponivel=1
    apenas_agendados: Optional[bool] = None,   # True para listar apenas horários com vistorias (ENTRADA, SAIDA, CONFERENCIA)
    incluir_fechados: bool = False,         # True para incluir horários com tipo 'FECHADO'
    incluir_improdutivas: bool = False      # True para incluir horários com tipo 'IMPRODUTIVA'
) -> List[Dict[str, Any]]:
    """
    Lista horários da agenda com base em múltiplos filtros.

    Permite filtrar por vistoriador, período de datas, e status/tipo do horário
    (disponível, agendado, fechado, improdutivo).
    Junta dados das tabelas agenda, usuarios (vistoriador), imoveis, clientes (do imóvel) e
    imobiliarias (do imóvel) para fornecer informações detalhadas.

    Args:
        vistoriador_id (Optional[int]): ID do vistoriador para filtrar. Se None, lista para todos.
        data_inicio (Optional[str]): Data de início do período (formato "YYYY-MM-DD").
        data_fim (Optional[str]): Data de fim do período (formato "YYYY-MM-DD").
        apenas_disponiveis (Optional[bool]): Filtra por horários disponíveis (tipo 'LIVRE').
        apenas_agendados (Optional[bool]): Filtra por horários com vistorias agendadas.
        incluir_fechados (bool): Inclui horários marcados como 'FECHADO'.
        incluir_improdutivas (bool): Inclui vistorias marcadas como 'IMPRODUTIVA'.

    Returns:
        List[Dict[str, Any]]: Uma lista de dicionários, cada um representando um item da agenda
                               com detalhes do vistoriador, imóvel, cliente e imobiliária.
    """
    # Query base selecionando todos os campos necessários e fazendo os JOINs
    query = """
        SELECT a.id, a.data, a.horario, a.disponivel, a.tipo, a.imovel_id,
               u.nome as nome_vistoriador, a.vistoriador_id,
               i.cod_imovel, i.endereco as endereco_imovel, i.cep as cep_imovel,
               i.referencia as referencia_imovel, i.tamanho as tamanho_imovel, i.mobiliado as mobiliado_imovel,
               c.nome as nome_cliente, c.id as cliente_id, c.email as email_cliente,
               imob.nome as nome_imobiliaria, imob.id as imobiliaria_id_imovel
        FROM agenda a
        JOIN usuarios u ON a.vistoriador_id = u.id /* Informações do vistoriador */
        LEFT JOIN imoveis i ON a.imovel_id = i.id /* Informações do imóvel, se houver */
        LEFT JOIN clientes c ON i.cliente_id = c.id /* Informações do cliente do imóvel, se houver */
        LEFT JOIN imobiliarias imob ON i.imobiliaria_id = imob.id /* Informações da imobiliária do imóvel, se houver */
        WHERE 1=1 /* Condição base para facilitar a adição de ANDs */
    """
    params = [] # Lista para armazenar os parâmetros da query

    # Adiciona filtro por ID do vistoriador, se fornecido
    if vistoriador_id is not None:
        query += " AND a.vistoriador_id = ?"
        params.append(vistoriador_id)

    # Lógica para filtro de datas:
    # Se data_inicio e data_fim não são fornecidos, e estamos buscando disponíveis ou agendados,
    # por padrão, filtramos por datas a partir de hoje.
    if data_inicio is None and data_fim is None:
        if apenas_disponiveis or apenas_agendados:
            data_hoje_str = dt.date.today().strftime("%Y-%m-%d")
            query += " AND a.data >= ?" # Filtra para hoje ou datas futuras
            params.append(data_hoje_str)
    else: # Se datas específicas são fornecidas
        if data_inicio:
            query += " AND a.data >= ?"
            params.append(data_inicio)
        if data_fim:
            query += " AND a.data <= ?"
            params.append(data_fim)

    # Constrói as condições de status/tipo do horário
    status_conditions = []
    if apenas_disponiveis:
        status_conditions.append(" (a.disponivel = 1 AND a.tipo = 'LIVRE') ")
    if apenas_agendados: # Vistorias ativas
        status_conditions.append(" (a.disponivel = 0 AND a.tipo IN ('ENTRADA', 'SAIDA', 'CONFERENCIA')) ")
    if incluir_fechados:
        status_conditions.append(" (a.tipo = 'FECHADO') ")
    if incluir_improdutivas:
        status_conditions.append(" (a.tipo = 'IMPRODUTIVA') ")

    # Adiciona as condições de status à query principal se alguma foi definida
    if status_conditions:
        query += " AND (" + " OR ".join(status_conditions) + ")"
    else: 
        # Comportamento padrão se nenhum filtro de status específico for marcado:
        # Se NÃO estamos buscando `apenas_disponiveis` (ou seja, `apenas_disponiveis` é False ou None),
        # por padrão, não mostramos os horários 'LIVRE', a menos que outro filtro os inclua.
        # Isso evita listar todos os horários livres futuros por default quando nenhum filtro é ativo.
        if not apenas_disponiveis : 
             query += " AND a.tipo != 'LIVRE' "


    # Ordenação dos resultados
    query += " ORDER BY a.data ASC, a.horario ASC, u.nome ASC"
    
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute(query, tuple(params)) # Executa a query com os parâmetros
        horarios_db = cursor.fetchall() # Lista de tuplas
        colunas = [desc[0] for desc in cursor.description] # Nomes das colunas
        
        # Converte a lista de tuplas em uma lista de dicionários
        lista_horarios = []
        for row_tuple in horarios_db:
            dict_row = dict(zip(colunas, row_tuple)) # Mapeia nome da coluna para valor
            # Monta o dicionário final com chaves mais amigáveis/consistentes
            lista_horarios.append({
                'id_agenda': dict_row['id'], 'data': dict_row['data'], 'horario': dict_row['horario'],
                'disponivel': bool(dict_row['disponivel']), 'tipo_vistoria': dict_row['tipo'], # 'tipo' da agenda é o tipo da vistoria se agendado
                'imovel_id': dict_row['imovel_id'],
                'nome_vistoriador': dict_row['nome_vistoriador'], 'vistoriador_id': dict_row['vistoriador_id'],
                'cod_imovel': dict_row.get('cod_imovel'), 'endereco_imovel': dict_row.get('endereco_imovel'),
                'cep': dict_row.get('cep_imovel'), 'referencia': dict_row.get('referencia_imovel'),
                'tamanho': dict_row.get('tamanho_imovel'), 'mobiliado': dict_row.get('mobiliado_imovel'),
                'nome_cliente': dict_row.get('nome_cliente'), 'cliente_id': dict_row.get('cliente_id'),
                'email_cliente': dict_row.get('email_cliente'),
                'nome_imobiliaria': dict_row.get('nome_imobiliaria'),
                'imobiliaria_id_imovel': dict_row.get('imobiliaria_id_imovel')
            })
        return lista_horarios
    except Exception as e:
        logging.error(f"Erro ao listar horários da agenda: {e}", exc_info=True)
        return []
    finally:
        if conexao: conexao.close()

def agendar_vistoria_em_horario(
    id_agenda: int, # ID do slot de horário na tabela 'agenda' a ser usado
    imovel_id: int, # ID do imóvel para o qual a vistoria está sendo agendada
    tipo_vistoria_agendada: str, # 'ENTRADA', 'SAIDA', ou 'CONFERENCIA'
    ignorar_regras_horario_duplo: bool = False # Flag para forçar agendamento em um slot único mesmo se dois forem necessários
) -> Tuple[bool, str]:
    """
    Agenda uma vistoria em um ou mais slots de horário na tabela `agenda`.

    Verifica se o horário principal está disponível e é do tipo 'LIVRE'.
    Consulta as regras do imóvel (`regras_necessita_dois_horarios`) para determinar
    se um segundo slot de horário consecutivo é necessário.
    Se dois horários são necessários e `ignorar_regras_horario_duplo` é False,
    tenta encontrar e reservar um segundo slot disponível no mesmo período (manhã/tarde)
    do mesmo vistoriador no mesmo dia.
    Atualiza os slots da agenda marcando-os como não disponíveis (`disponivel = 0`),
    associando o `imovel_id` e definindo o `tipo` da vistoria.

    Args:
        id_agenda (int): ID da entrada principal na `agenda` selecionada para a vistoria.
        imovel_id (int): ID do imóvel a ser vistoriado.
        tipo_vistoria_agendada (str): Tipo da vistoria ('ENTRADA', 'SAIDA', 'CONFERENCIA').
        ignorar_regras_horario_duplo (bool): Se True, permite agendar em um único slot
                                             mesmo que as regras indiquem a necessidade de dois.

    Returns:
        Tuple[bool, str]: (sucesso, mensagem de status).
    """
    # Validação do tipo de vistoria
    if tipo_vistoria_agendada not in ['ENTRADA', 'SAIDA', 'CONFERENCIA']:
        return False, "Tipo de vistoria inválido."
        
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;") # Ativa FKs

        # 1. Verifica se o horário principal (id_agenda) está disponível e é 'LIVRE'
        cursor.execute("SELECT id, vistoriador_id, data, horario FROM agenda WHERE id = ? AND disponivel = 1 AND tipo = 'LIVRE'", (id_agenda,))
        horario_principal_db = cursor.fetchone()
        if not horario_principal_db:
            return False, "Horário principal selecionado não está disponível ou não é do tipo 'LIVRE'."
        
        id_agenda_principal, vist_id, data_vist_str, horario_vist_principal_str = horario_principal_db

        # 2. Verifica se são necessários dois horários para esta vistoria/imóvel
        necessita_dois_slots = regras_necessita_dois_horarios(imovel_id, tipo_vistoria_agendada)
        
        ids_dos_slots_para_reservar = [id_agenda_principal] # Começa com o slot principal
        id_agenda_secundario_encontrado = None # Para armazenar o ID do segundo slot, se encontrado

        # 3. Se dois slots são necessários E não estamos forçando agendamento único:
        if necessita_dois_slots and not ignorar_regras_horario_duplo:
            # Converte o horário principal para objeto datetime para facilitar a comparação de período (manhã/tarde)
            horario_principal_dt_obj = dt.datetime.strptime(horario_vist_principal_str, "%H:%M")
            # Determina se o horário principal é de manhã (< 12h) ou tarde (>= 12h)
            periodo_principal = 'manha' if horario_principal_dt_obj.hour < 12 else 'tarde'

            # Busca por um slot secundário disponível para o mesmo vistoriador, no mesmo dia,
            # em horário posterior ao principal, e que seja 'LIVRE'.
            cursor.execute("""
                SELECT id, horario FROM agenda 
                WHERE vistoriador_id = ? AND data = ? AND horario > ? AND disponivel = 1 AND tipo = 'LIVRE' 
                ORDER BY horario ASC
            """, (vist_id, data_vist_str, horario_vist_principal_str))
            possiveis_slots_secundarios = cursor.fetchall()

            # Itera sobre os possíveis slots secundários para encontrar um no mesmo período (manhã/tarde)
            for id_sec, horario_sec_str_db in possiveis_slots_secundarios:
                horario_secundario_dt_obj = dt.datetime.strptime(horario_sec_str_db, "%H:%M")
                periodo_secundario = 'manha' if horario_secundario_dt_obj.hour < 12 else 'tarde'
                if periodo_secundario == periodo_principal: # Se encontrou um slot no mesmo período
                    id_agenda_secundario_encontrado = id_sec
                    break # Para de procurar, já encontrou o primeiro adequado
            
            if not id_agenda_secundario_encontrado:
                # Se necessita de dois slots mas não encontrou um segundo adequado
                return False, "Necessita de dois horários para esta vistoria, mas não há um segundo slot consecutivo disponível no mesmo período (manhã/tarde)."
            
            # Adiciona o ID do slot secundário à lista de slots a serem reservados
            ids_dos_slots_para_reservar.append(id_agenda_secundario_encontrado)
        
        elif necessita_dois_slots and ignorar_regras_horario_duplo:
            # Log se o agendamento está sendo forçado em um único slot
            logging.info(f"Agendamento para imóvel ID {imovel_id} (tipo: {tipo_vistoria_agendada}) necessitaria de dois slots, mas foi forçado em um único slot (ID Agenda: {id_agenda_principal}).")

        # 4. Atualiza todos os slots selecionados (um ou dois) na tabela 'agenda'
        for id_slot_agenda_atualizar in ids_dos_slots_para_reservar:
            cursor.execute("UPDATE agenda SET disponivel = 0, imovel_id = ?, tipo = ? WHERE id = ?", 
                           (imovel_id, tipo_vistoria_agendada, id_slot_agenda_atualizar))
        
        conexao.commit() # Confirma as atualizações
        
        msg_sucesso = f"Vistoria '{tipo_vistoria_agendada}' para imóvel ID {imovel_id} agendada com sucesso no(s) horário(s) ID(s) da agenda: {ids_dos_slots_para_reservar}."
        if necessita_dois_slots and ignorar_regras_horario_duplo and not id_agenda_secundario_encontrado:
             msg_sucesso += " (Atenção: Agendamento forçado em um único slot, embora dois fossem indicados pelas regras.)"
        
        logging.info(msg_sucesso)
        return True, msg_sucesso
        
    except Exception as e:
        if conexao: conexao.rollback()
        logging.error(f"Erro ao agendar vistoria para imóvel ID {imovel_id} no horário ID {id_agenda}: {e}", exc_info=True)
        return False, f"Erro ao agendar vistoria: {e}"
    finally:
        if conexao: conexao.close()

def cancelar_agendamento_vistoria(id_agenda_principal: int, id_cliente_responsavel: int) -> Tuple[bool, str]:
    """
    Cancela uma vistoria agendada, liberando o(s) horário(s) na agenda.

    Se a vistoria original ocupava dois slots (devido às regras do imóvel),
    esta função tenta identificar e liberar ambos os slots.

    Args:
        id_agenda_principal (int): ID da entrada na tabela `agenda` que corresponde ao horário principal
                                   da vistoria a ser cancelada.
        id_cliente_responsavel (int): ID do cliente associado à vistoria (usado para logs/auditoria,
                                      não diretamente para a lógica de cancelamento aqui).

    Returns:
        Tuple[bool, str]: (sucesso, mensagem de status).
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # 1. Busca dados do agendamento principal para verificar se ele é cancelável
        #    e para obter informações necessárias para encontrar um possível segundo slot.
        cursor.execute("""
            SELECT a.imovel_id, a.data, a.horario, a.tipo, a.vistoriador_id, i.cod_imovel 
            FROM agenda a 
            LEFT JOIN imoveis i ON a.imovel_id = i.id 
            WHERE a.id = ? AND a.disponivel = 0 AND a.tipo IN ('ENTRADA', 'SAIDA', 'CONFERENCIA')
        """, (id_agenda_principal,))
        agendamento_db = cursor.fetchone()

        if not agendamento_db:
            return False, "Agendamento não encontrado, já está livre/fechado, é improdutivo, ou não é uma vistoria ativa passível de cancelamento."
        
        imovel_id, data_ag_str, hora_ag_principal_str, tipo_ag, vist_id, cod_imovel = agendamento_db
        
        slots_a_liberar_ids = [id_agenda_principal] # Começa com o slot principal

        # 2. Se a vistoria tinha um imóvel e as regras indicam que ocupava dois slots:
        if imovel_id and regras_necessita_dois_horarios(imovel_id, tipo_ag):
            # Tenta encontrar o segundo slot que foi agendado junto com o principal.
            # O segundo slot teria o mesmo vistoriador, data, imóvel, tipo de vistoria,
            # status não disponível, e estaria em um horário adjacente no mesmo período.

            # Procura por um slot ANTERIOR no mesmo período
            cursor.execute("""
                SELECT id, horario FROM agenda 
                WHERE vistoriador_id = ? AND data = ? AND horario < ? AND imovel_id = ? AND tipo = ? AND disponivel = 0 
                ORDER BY horario DESC LIMIT 1
            """, (vist_id, data_ag_str, hora_ag_principal_str, imovel_id, tipo_ag))
            slot_anterior_info = cursor.fetchone()
            
            if slot_anterior_info:
                id_slot_anterior, horario_anterior_str = slot_anterior_info
                # Verifica se o slot anterior está no mesmo período (manhã/tarde)
                horario_anterior_dt_obj = dt.datetime.strptime(horario_anterior_str, "%H:%M")
                periodo_principal_dt_obj = dt.datetime.strptime(hora_ag_principal_str, "%H:%M")
                if (horario_anterior_dt_obj.hour < 12) == (periodo_principal_dt_obj.hour < 12) and id_slot_anterior not in slots_a_liberar_ids:
                    slots_a_liberar_ids.append(id_slot_anterior)

            # Procura por um slot POSTERIOR no mesmo período
            cursor.execute("""
                SELECT id, horario FROM agenda 
                WHERE vistoriador_id = ? AND data = ? AND horario > ? AND imovel_id = ? AND tipo = ? AND disponivel = 0 
                ORDER BY horario ASC LIMIT 1
            """, (vist_id, data_ag_str, hora_ag_principal_str, imovel_id, tipo_ag))
            slot_posterior_info = cursor.fetchone()

            if slot_posterior_info:
                id_slot_posterior, horario_posterior_str = slot_posterior_info
                 # Verifica se o slot posterior está no mesmo período (manhã/tarde)
                horario_posterior_dt_obj = dt.datetime.strptime(horario_posterior_str, "%H:%M")
                periodo_principal_dt_obj = dt.datetime.strptime(hora_ag_principal_str, "%H:%M")
                if (horario_posterior_dt_obj.hour < 12) == (periodo_principal_dt_obj.hour < 12) and id_slot_posterior not in slots_a_liberar_ids:
                    slots_a_liberar_ids.append(id_slot_posterior)
            
            # Garante que não haja duplicatas (embora a lógica de adicionar 'if not in' já previna)
            slots_a_liberar_ids = list(set(slots_a_liberar_ids))


        # 3. Libera todos os slots identificados
        for slot_id_atual in slots_a_liberar_ids:
            # Reseta o slot para 'LIVRE', disponível, e remove a associação com o imóvel
            cursor.execute("UPDATE agenda SET disponivel = 1, imovel_id = NULL, tipo = 'LIVRE' WHERE id = ?", (slot_id_atual,))
        
        conexao.commit()
        logging.info(f"Agendamento(s) para imóvel '{cod_imovel or 'N/A'}' nos slots de agenda ID(s) {slots_a_liberar_ids} cancelado(s) e horário(s) liberado(s). Solicitado por cliente ID {id_cliente_responsavel}.")
        return True, f"Agendamento(s) ID(s) da agenda {slots_a_liberar_ids} para imóvel '{cod_imovel or 'N/A'}' cancelado(s) e horário(s) liberado(s)."
        
    except Exception as e:
        if conexao: conexao.rollback()
        logging.error(f"Erro ao cancelar agendamento ID {id_agenda_principal}: {e}", exc_info=True)
        return False, f"Erro ao cancelar agendamento: {e}"
    finally:
        if conexao: conexao.close()

def fechar_horario_agenda(id_agenda: int, motivo: str, vistoriador_id_responsavel_fechamento: int) -> Tuple[bool, str]:
    """
    Marca um horário específico da agenda como 'FECHADO'.

    Um horário só pode ser fechado se pertencer ao `vistoriador_id_responsavel_fechamento`,
    estiver atualmente 'LIVRE' e disponível.
    Registra o motivo do fechamento na tabela `horarios_fechados`.

    Args:
        id_agenda (int): ID da entrada na agenda a ser fechada.
        motivo (str): Justificativa para o fechamento.
        vistoriador_id_responsavel_fechamento (int): ID do vistoriador (ou admin) que está fechando o horário.
                                                     A verificação de permissão (se admin pode fechar para qualquer
                                                     vistoriador) deve ser feita na camada de Controller.
                                                     Este modelo assume que `vistoriador_id_responsavel_fechamento`
                                                     deve ser o `vistoriador_id` do slot da agenda.

    Returns:
        Tuple[bool, str]: (sucesso, mensagem de status).
    """
    if not motivo: # Motivo é obrigatório
        return False, "Motivo do fechamento é obrigatório."
        
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Verifica se o horário pode ser fechado: pertence ao vistoriador, está livre e disponível
        cursor.execute("""
            SELECT id FROM agenda 
            WHERE id = ? AND vistoriador_id = ? AND disponivel = 1 AND tipo = 'LIVRE'
        """, (id_agenda, vistoriador_id_responsavel_fechamento))
        horario_db = cursor.fetchone()

        if not horario_db:
            return False, "Horário não encontrado, já está ocupado/fechado, não é do tipo 'LIVRE', ou não pertence ao vistoriador especificado."

        # Atualiza a agenda para 'FECHADO' e não disponível
        cursor.execute("UPDATE agenda SET disponivel = 0, tipo = 'FECHADO', imovel_id = NULL WHERE id = ?", (id_agenda,))
        # Insere o motivo na tabela `horarios_fechados`
        cursor.execute("INSERT INTO horarios_fechados (agenda_id, motivo) VALUES (?, ?)", (id_agenda, motivo))
        
        conexao.commit()
        logging.info(f"Horário ID {id_agenda} do vistoriador ID {vistoriador_id_responsavel_fechamento} fechado. Motivo: {motivo}")
        return True, f"Horário ID {id_agenda} fechado com sucesso. Motivo: {motivo}"
        
    except sqlite3.IntegrityError:
        # Pode ocorrer se já houver uma entrada em `horarios_fechados` para este `agenda_id` (devido ao UNIQUE)
        # ou se a atualização da agenda falhar por algum motivo de integridade inesperado.
        logging.warning(f"Aviso: Horário ID {id_agenda} já parece estar registrado como fechado ou houve uma falha de integridade ao inserir motivo.")
        # Tenta garantir que o status na agenda seja 'FECHADO' mesmo que a inserção do motivo falhe (ou já exista)
        if conexao: # Garante que há conexão para executar o update de fallback
            cursor.execute("UPDATE agenda SET disponivel = 0, tipo = 'FECHADO', imovel_id = NULL WHERE id = ? AND tipo != 'FECHADO'", (id_agenda,))
            conexao.commit() # Tenta commitar a atualização do status da agenda
        return False, f"Horário ID {id_agenda} já estava fechado ou ocorreu um erro de integridade ao registrar o motivo."
    except Exception as e:
        if conexao: conexao.rollback()
        logging.error(f"Erro ao fechar horário ID {id_agenda}: {e}", exc_info=True)
        return False, f"Erro ao fechar horário: {e}"
    finally:
        if conexao: conexao.close()

def reabrir_horario_agenda(id_agenda: int, vistoriador_id_responsavel_reabertura: int) -> Tuple[bool, str]:
    """
    Reabre um horário na agenda que estava marcado como 'FECHADO'.

    Verifica se o horário pertence ao `vistoriador_id_responsavel_reabertura` e está 'FECHADO'.
    Remove o registro da tabela `horarios_fechados` e atualiza a entrada na `agenda`
    para 'LIVRE' e disponível.

    Args:
        id_agenda (int): ID da entrada na agenda a ser reaberta.
        vistoriador_id_responsavel_reabertura (int): ID do vistoriador (ou admin) realizando a ação.
                                                     Similar à função `fechar_horario_agenda`, a checagem de
                                                     permissão mais ampla (admin para qualquer vistoriador)
                                                     seria no Controller.

    Returns:
        Tuple[bool, str]: (sucesso, mensagem de status).
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Verifica se o horário está realmente 'FECHADO' e pertence ao vistoriador
        cursor.execute("""
            SELECT id FROM agenda 
            WHERE id = ? AND vistoriador_id = ? AND tipo = 'FECHADO'
        """, (id_agenda, vistoriador_id_responsavel_reabertura))
        horario_db = cursor.fetchone()

        if not horario_db:
            return False, "Horário não está 'FECHADO', não foi encontrado para este vistoriador, ou não pertence ao vistoriador especificado."

        # Remove da tabela `horarios_fechados` (ON DELETE CASCADE da agenda também trataria, mas explícito é bom)
        cursor.execute("DELETE FROM horarios_fechados WHERE agenda_id = ?", (id_agenda,))
        # Atualiza a agenda para 'LIVRE' e disponível
        cursor.execute("UPDATE agenda SET disponivel = 1, tipo = 'LIVRE' WHERE id = ?", (id_agenda,))
        
        conexao.commit()
        
        if cursor.rowcount > 0 : # Se a agenda foi atualizada
            logging.info(f"Horário ID {id_agenda} do vistoriador ID {vistoriador_id_responsavel_reabertura} reaberto com sucesso.")
            return True, f"Horário ID {id_agenda} reaberto com sucesso."
        else:
            # Caso estranho: DELETE em horarios_fechados pode ter funcionado, mas UPDATE na agenda não afetou linhas.
            # Verifica o estado atual para dar uma mensagem mais precisa.
            logging.warning(f"Tentativa de reabrir horário ID {id_agenda}, mas o estado da agenda pode não ter sido alterado como esperado.")
            cursor.execute("SELECT tipo FROM agenda WHERE id = ?", (id_agenda,))
            tipo_atual_na_agenda = cursor.fetchone()
            if tipo_atual_na_agenda and tipo_atual_na_agenda[0] == 'LIVRE':
                # Provavelmente o DELETE em horarios_fechados ocorreu, e a agenda já estava LIVRE,
                # ou o UPDATE não registrou rowcount mas funcionou.
                logging.info(f"Horário ID {id_agenda} já se encontra como 'LIVRE'. Reabertura considerada bem-sucedida (entrada em horarios_fechados removida se existia).")
                return True, f"Horário ID {id_agenda} reaberto com sucesso (entrada em horarios_fechados pode não ter existido ou foi removida)."
            else:
                # Se não está LIVRE após a tentativa, algo deu errado.
                if conexao: conexao.rollback() # Garante rollback se o estado é inconsistente
                return False, f"Não foi possível reabrir o horário ID {id_agenda} (estado inconsistente ou não alterado)."
    except Exception as e:
        if conexao: conexao.rollback()
        logging.error(f"Erro ao reabrir horário ID {id_agenda}: {e}", exc_info=True)
        return False, f"Erro ao reabrir horário: {e}"
    finally:
        if conexao: conexao.close()

def listar_horarios_fechados_por_vistoriador(vistoriador_id: int) -> List[Dict[str, Any]]:
    """
    Lista todos os horários que foram manualmente fechados por um vistoriador específico.

    Args:
        vistoriador_id (int): ID do vistoriador.

    Returns:
        List[Dict[str, Any]]: Lista de dicionários, cada um contendo 'id_agenda', 'data',
                               'horario' e 'motivo' do fechamento.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Junta `agenda` com `horarios_fechados` para obter o motivo e detalhes do horário
        cursor.execute("""
            SELECT a.id, a.data, a.horario, hf.motivo 
            FROM agenda a 
            JOIN horarios_fechados hf ON a.id = hf.agenda_id 
            WHERE a.vistoriador_id = ? AND a.tipo = 'FECHADO' 
            ORDER BY a.data, a.horario
        """, (vistoriador_id,))
        fechados_db = cursor.fetchall()
        return [{'id_agenda': row[0], 'data': row[1], 'horario': row[2], 'motivo': row[3]} for row in fechados_db]
    except Exception as e:
        logging.error(f"Erro ao listar horários fechados do vistoriador ID {vistoriador_id}: {e}", exc_info=True)
        return []
    finally:
        if conexao: conexao.close()

# --- Funções para Geração de Relatórios de Vistorias (Entrada/Saída) ---

def _executar_query_relatorio_vistoria(query: str, params: tuple) -> pd.DataFrame:
    """
    Função auxiliar interna para executar uma query SQL de relatório e retornar um DataFrame pandas.
    Também aplica o cálculo do "Valor Vistoriador (R$)" ao DataFrame resultante.

    Args:
        query (str): A string da query SQL.
        params (tuple): Tupla de parâmetros para a query SQL.

    Returns:
        pd.DataFrame: DataFrame com os resultados da query, incluindo a coluna calculada
                      "Valor Vistoriador (R$)" ou um DataFrame vazio em caso de erro.
    """
    conexao = None
    logging.debug(f"Executando query de relatório: {query} com parâmetros: {params}")
    try:
        conexao = conectar_banco()
        # Usa pandas para ler diretamente o resultado da query SQL em um DataFrame
        df = pd.read_sql_query(query, conexao, params=params)
        logging.debug(f"Query de relatório retornou {len(df)} linhas.")
        
        if not df.empty:
            # Calcula a coluna "Valor Vistoriador (R$)" aplicando a função `calcular_valor_vistoriador`
            # a cada linha do DataFrame.
            # As colunas "Tipo Mobília" e "Tipo Vistoria Agenda" são usadas para este cálculo
            # e depois podem ser removidas do DataFrame final se não forem necessárias no relatório.
            df["Valor Vistoriador (R$)"] = df.apply(
                lambda row: calcular_valor_vistoriador(
                    tamanho_m2=row["Tamanho (m2)"], # A query já nomeia como "Tamanho (m2)"
                    mobiliado_status=row["Tipo Mobília"],
                    tipo_vistoria_agenda=row["Tipo Vistoria Agenda"]
                ), axis=1 # `axis=1` para aplicar a função por linha
            )
            # Remove colunas auxiliares usadas apenas para o cálculo, se não forem desejadas no relatório final.
            # `errors='ignore'` previne erro se as colunas não existirem (embora devam existir pela query).
            df = df.drop(columns=["Tipo Mobília", "Tipo Vistoria Agenda"], errors='ignore')
        return df
    except Exception as e:
        logging.error(f"Erro ao executar query de relatório de vistoria ou calcular valor do vistoriador: {e}", exc_info=True)
        return pd.DataFrame() # Retorna DataFrame vazio em caso de erro
    finally:
        if conexao: conexao.close()

# As funções seguintes constroem e executam queries SQL para diferentes tipos de relatórios de vistoria.
# Todas utilizam `_executar_query_relatorio_vistoria` para processamento.

def obter_dados_relatorio_entrada_geral(data_inicio: str, data_fim: str) -> pd.DataFrame:
    """Relatório geral de vistorias de ENTRADA dentro de um período."""
    query = """
        SELECT
            strftime('%d/%m/%Y', a.data) AS "Data Vistoria", /* Formata data para DD/MM/YYYY */
            a.horario AS "Horário",
            u.nome AS "Vistoriador",
            i.cod_imovel AS "Cód. Imóvel",
            i.endereco AS "Endereço",
            i.tamanho AS "Tamanho (m2)",      /* Para cálculo e exibição */
            c.nome AS "Cliente",
            imob.nome AS "Imobiliária",
            i.valor AS "Valor Base (R$)",     /* Valor base da Engentoria para a vistoria */
            i.mobiliado AS "Tipo Mobília",    /* Usado para cálculo do valor do vistoriador */
            a.tipo AS "Tipo Vistoria Agenda"  /* Usado para cálculo do valor do vistoriador */
        FROM agenda a
        JOIN usuarios u ON a.vistoriador_id = u.id
        LEFT JOIN imoveis i ON a.imovel_id = i.id
        LEFT JOIN clientes c ON i.cliente_id = c.id
        LEFT JOIN imobiliarias imob ON i.imobiliaria_id = imob.id
        WHERE a.tipo = 'ENTRADA' AND a.data BETWEEN ? AND ? /* Filtra por tipo ENTRADA e período */
        ORDER BY a.data, a.horario
    """
    return _executar_query_relatorio_vistoria(query, (data_inicio, data_fim))

def obter_dados_relatorio_saida_geral(data_inicio: str, data_fim: str) -> pd.DataFrame:
    """Relatório geral de vistorias de SAIDA dentro de um período."""
    query = """
        SELECT
            strftime('%d/%m/%Y', a.data) AS "Data Vistoria",
            a.horario AS "Horário",
            u.nome AS "Vistoriador",
            i.cod_imovel AS "Cód. Imóvel",
            i.endereco AS "Endereço",
            i.tamanho AS "Tamanho (m2)",
            c.nome AS "Cliente",
            imob.nome AS "Imobiliária",
            i.valor AS "Valor Base (R$)",
            i.mobiliado AS "Tipo Mobília",
            a.tipo AS "Tipo Vistoria Agenda"
        FROM agenda a
        JOIN usuarios u ON a.vistoriador_id = u.id
        LEFT JOIN imoveis i ON a.imovel_id = i.id
        LEFT JOIN clientes c ON i.cliente_id = c.id
        LEFT JOIN imobiliarias imob ON i.imobiliaria_id = imob.id
        WHERE a.tipo = 'SAIDA' AND a.data BETWEEN ? AND ? /* Filtra por tipo SAIDA e período */
        ORDER BY a.data, a.horario
    """
    return _executar_query_relatorio_vistoria(query, (data_inicio, data_fim))

def obter_dados_relatorio_entrada_por_vistoriador(data_inicio: str, data_fim: str, vistoriador_id: int) -> pd.DataFrame:
    """Relatório de vistorias de ENTRADA para um vistoriador específico, dentro de um período."""
    query = """
        SELECT
            strftime('%d/%m/%Y', a.data) AS "Data Vistoria",
            a.horario AS "Horário",
            /* u.nome AS "Vistoriador", -- Removido pois já estamos filtrando por vistoriador */
            i.cod_imovel AS "Cód. Imóvel",
            i.endereco AS "Endereço",
            i.tamanho AS "Tamanho (m2)",
            c.nome AS "Cliente",
            imob.nome AS "Imobiliária",
            i.valor AS "Valor Base (R$)",
            i.mobiliado AS "Tipo Mobília",
            a.tipo AS "Tipo Vistoria Agenda"
        FROM agenda a
        /* JOIN usuarios u ON a.vistoriador_id = u.id -- Join com usuarios não é estritamente necessário se não exibir o nome */
        LEFT JOIN imoveis i ON a.imovel_id = i.id
        LEFT JOIN clientes c ON i.cliente_id = c.id
        LEFT JOIN imobiliarias imob ON i.imobiliaria_id = imob.id
        WHERE a.tipo = 'ENTRADA' AND a.vistoriador_id = ? AND a.data BETWEEN ? AND ? /* Filtra por vistoriador_id */
        ORDER BY a.data, a.horario
    """
    return _executar_query_relatorio_vistoria(query, (vistoriador_id, data_inicio, data_fim))

def obter_dados_relatorio_saida_por_vistoriador(data_inicio: str, data_fim: str, vistoriador_id: int) -> pd.DataFrame:
    """Relatório de vistorias de SAIDA para um vistoriador específico, dentro de um período."""
    query = """
        SELECT
            strftime('%d/%m/%Y', a.data) AS "Data Vistoria",
            a.horario AS "Horário",
            i.cod_imovel AS "Cód. Imóvel",
            i.endereco AS "Endereço",
            i.tamanho AS "Tamanho (m2)",
            c.nome AS "Cliente",
            imob.nome AS "Imobiliária",
            i.valor AS "Valor Base (R$)",
            i.mobiliado AS "Tipo Mobília",
            a.tipo AS "Tipo Vistoria Agenda"
        FROM agenda a
        LEFT JOIN imoveis i ON a.imovel_id = i.id
        LEFT JOIN clientes c ON i.cliente_id = c.id
        LEFT JOIN imobiliarias imob ON i.imobiliaria_id = imob.id
        WHERE a.tipo = 'SAIDA' AND a.vistoriador_id = ? AND a.data BETWEEN ? AND ?
        ORDER BY a.data, a.horario
    """
    return _executar_query_relatorio_vistoria(query, (vistoriador_id, data_inicio, data_fim))

def obter_dados_relatorio_entrada_por_imobiliaria(data_inicio: str, data_fim: str, imobiliaria_id: int) -> pd.DataFrame:
    """Relatório de vistorias de ENTRADA para uma imobiliária específica, dentro de um período."""
    query = """
        SELECT
            strftime('%d/%m/%Y', a.data) AS "Data Vistoria",
            a.horario AS "Horário",
            u.nome AS "Vistoriador",
            i.cod_imovel AS "Cód. Imóvel",
            i.endereco AS "Endereço",
            i.tamanho AS "Tamanho (m2)",
            c.nome AS "Cliente",
            /* imob.nome AS "Imobiliária", -- Removido pois já estamos filtrando por imobiliária */
            i.valor AS "Valor Base (R$)",
            i.mobiliado AS "Tipo Mobília",
            a.tipo AS "Tipo Vistoria Agenda"
        FROM agenda a
        JOIN usuarios u ON a.vistoriador_id = u.id
        LEFT JOIN imoveis i ON a.imovel_id = i.id
        LEFT JOIN clientes c ON i.cliente_id = c.id
        /* LEFT JOIN imobiliarias imob ON i.imobiliaria_id = imob.id -- Join não estritamente necessário se não exibir o nome */
        WHERE a.tipo = 'ENTRADA' AND i.imobiliaria_id = ? AND a.data BETWEEN ? AND ? /* Filtra por imobiliaria_id do imóvel */
        ORDER BY a.data, a.horario
    """
    return _executar_query_relatorio_vistoria(query, (imobiliaria_id, data_inicio, data_fim))

def obter_dados_relatorio_saida_por_imobiliaria(data_inicio: str, data_fim: str, imobiliaria_id: int) -> pd.DataFrame:
    """Relatório de vistorias de SAIDA para uma imobiliária específica, dentro de um período."""
    query = """
        SELECT
            strftime('%d/%m/%Y', a.data) AS "Data Vistoria",
            a.horario AS "Horário",
            u.nome AS "Vistoriador",
            i.cod_imovel AS "Cód. Imóvel",
            i.endereco AS "Endereço",
            i.tamanho AS "Tamanho (m2)",
            c.nome AS "Cliente",
            i.valor AS "Valor Base (R$)",
            i.mobiliado AS "Tipo Mobília",
            a.tipo AS "Tipo Vistoria Agenda"
        FROM agenda a
        JOIN usuarios u ON a.vistoriador_id = u.id
        LEFT JOIN imoveis i ON a.imovel_id = i.id
        LEFT JOIN clientes c ON i.cliente_id = c.id
        WHERE a.tipo = 'SAIDA' AND i.imobiliaria_id = ? AND a.data BETWEEN ? AND ?
        ORDER BY a.data, a.horario
    """
    return _executar_query_relatorio_vistoria(query, (imobiliaria_id, data_inicio, data_fim))

# Bloco para testes rápidos do model (executado quando o script é rodado diretamente)
if __name__ == '__main__':
    # Importações necessárias para os testes, podem precisar de ajuste de caminho se rodar fora do contexto do projeto
    from .database import criar_tabelas
    from .usuario_model import cadastrar_usuario as cadastrar_user_teste, listar_usuarios_por_tipo, listar_todos_clientes, cadastrar_cliente
    from .imovel_model import cadastrar_imovel as cadastrar_imov_teste # Alias para evitar conflito de nome
    from .imobiliaria_model import cadastrar_imobiliaria as cadastrar_imob_teste, listar_todas_imobiliarias
    
    # Garante que as tabelas do banco de dados existam para os testes
    logging.info("Inicializando ambiente de teste para agenda_model...")
    criar_tabelas()
    logging.info("Tabelas verificadas/criadas.")

    print("\n--- Testando Model Agenda (com Vistorias Improdutivas e Valor Vistoriador) ---")

    # Adicionar dados de teste se necessário (vistoriadores, clientes, imobiliárias, imóveis, horários fixos)
    # Exemplo:
    # 1. Cadastrar Vistoriador de Teste
    id_vist_teste = None
    vistoriadores_teste = listar_usuarios_por_tipo('vistoriador')
    if not vistoriadores_teste:
        id_vist_teste = cadastrar_user_teste("Vistoriador Agenda Teste", "vist.agenda@test.com", "senha123", "vistoriador")
        if id_vist_teste:
            logging.info(f"Vistoriador de teste (ID: {id_vist_teste}) criado.")
            # Adicionar horários fixos para ele
            cadastrar_horarios_fixos_vistoriador(id_vist_teste, ['1', '3'], ["09:00", "10:00", "14:00"]) # Seg, Qua
            gerar_agenda_baseada_em_horarios_fixos() # Gerar agenda com base nesses horários
    else:
        id_vist_teste = vistoriadores_teste[0]['id'] # Usa o primeiro vistoriador existente
        logging.info(f"Usando vistoriador existente para teste (ID: {id_vist_teste}).")
        # Garante que ele tenha alguns horários fixos e agenda gerada
        if not listar_horarios_fixos_por_vistoriador(id_vist_teste):
            cadastrar_horarios_fixos_vistoriador(id_vist_teste, ['2'], ["11:00", "15:00"]) # Terça
            gerar_agenda_baseada_em_horarios_fixos()


    # 2. Cadastrar Cliente de Teste
    id_cli_teste = None
    clientes_teste = listar_todos_clientes()
    if not clientes_teste:
        id_cli_teste = cadastrar_cliente("Cliente Agenda Teste", "cliente.agenda@test.com", saldo_devedor_total=0.0)
        if id_cli_teste: logging.info(f"Cliente de teste (ID: {id_cli_teste}) criado.")
    else:
        id_cli_teste = clientes_teste[0]['id']
        logging.info(f"Usando cliente existente para teste (ID: {id_cli_teste}).")

    # 3. Cadastrar Imobiliária de Teste
    id_imob_teste = None
    imobs_teste = listar_todas_imobiliarias()
    if not imobs_teste:
        id_imob_teste = cadastrar_imob_teste("Imob Agenda Teste", 10, 12, 15) # Valores por m2
        if id_imob_teste: logging.info(f"Imobiliária de teste (ID: {id_imob_teste}) criada.")
    else:
        id_imob_teste = imobs_teste[0]['id']
        logging.info(f"Usando imobiliária existente para teste (ID: {id_imob_teste}).")
        
    # 4. Cadastrar Imóvel de Teste (se todos os IDs acima foram obtidos)
    id_imovel_teste = None
    if id_cli_teste and id_imob_teste:
        # Verifica se já existe um imóvel para este cliente para não duplicar indefinidamente em testes
        imoveis_do_cliente = pd.DataFrame(listar_todos_imoveis()) # Usando a função mais completa
        if not imoveis_do_cliente.empty and id_cli_teste in imoveis_do_cliente['cliente_id'].values:
             id_imovel_teste = imoveis_do_cliente[imoveis_do_cliente['cliente_id'] == id_cli_teste]['id'].iloc[0]
             logging.info(f"Usando imóvel existente (ID: {id_imovel_teste}) para o cliente de teste.")
        else:
            id_imovel_teste = cadastrar_imov_teste(
                cod_imovel=f"AGTST{dt.datetime.now().second}", # Código de imóvel único
                cliente_id=id_cli_teste, 
                imobiliaria_id=id_imob_teste,
                endereco="Rua dos Testes Agendados, 123",
                tamanho=80.0, # m2
                mobiliado='semi_mobiliado'
            )
            if id_imovel_teste: logging.info(f"Imóvel de teste (ID: {id_imovel_teste}) criado.")

    # Teste de agendamento e vistorias improdutivas
    if id_vist_teste and id_imovel_teste and id_cli_teste:
        logging.info("\n--- Testando Agendamento e Vistoria Improdutiva ---")
        # Listar horários disponíveis para o vistoriador de teste
        horarios_disp = listar_horarios_agenda(vistoriador_id=id_vist_teste, apenas_disponiveis=True)
        if horarios_disp:
            horario_para_agendar = horarios_disp[0] # Pega o primeiro disponível
            id_agenda_teste = horario_para_agendar['id_agenda']
            data_orig_teste = horario_para_agendar['data']
            hora_orig_teste = horario_para_agendar['horario']
            
            logging.info(f"Tentando agendar vistoria de ENTRADA para imóvel ID {id_imovel_teste} no horário ID {id_agenda_teste}...")
            sucesso_ag, msg_ag = agendar_vistoria_em_horario(id_agenda_teste, id_imovel_teste, "ENTRADA")
            logging.info(f"Resultado Agendamento: {sucesso_ag} - {msg_ag}")

            if sucesso_ag:
                logging.info(f"Agendamento realizado. Agora, marcando como improdutiva...")
                sucesso_imp, msg_imp = registrar_vistoria_improdutiva(
                    agenda_id_original=id_agenda_teste,
                    cliente_id=id_cli_teste,
                    imovel_id=id_imovel_teste,
                    imobiliaria_id=id_imob_teste, # Supondo que a imobiliária do imóvel é a da cobrança
                    data_vistoria_original_str=data_orig_teste,
                    horario_vistoria_original_str=hora_orig_teste,
                    motivo="Cliente não compareceu (TESTE MODELO)",
                    valor_cobranca=75.50
                )
                logging.info(f"Resultado Vistoria Improdutiva: {sucesso_imp} - {msg_imp}")
                
                # Verificar se o saldo do cliente foi atualizado
                cliente_atualizado = obter_cliente_por_id(id_cli_teste) # Reimportar obter_cliente_por_id de usuario_model
                if cliente_atualizado:
                    logging.info(f"Saldo devedor do cliente ID {id_cli_teste} após improdutiva: R$ {cliente_atualizado['saldo_devedor_total']:.2f}")

                # Testar cancelamento do agendamento que agora é 'IMPRODUTIVA' (deve falhar)
                logging.info(f"Tentando cancelar o agendamento ID {id_agenda_teste} (que agora é IMPRODUTIVA)...")
                sucesso_cancel_imp, msg_cancel_imp = cancelar_agendamento_vistoria(id_agenda_teste, id_cli_teste)
                logging.info(f"Resultado Cancelamento de Improdutiva: {sucesso_cancel_imp} - {msg_cancel_imp}")
                if not sucesso_cancel_imp:
                    logging.info("--> Falha ao cancelar vistoria improdutiva, como esperado.")

        else:
            logging.warning(f"Nenhum horário disponível encontrado para o vistoriador de teste ID {id_vist_teste} para testar agendamento.")
    else:
        logging.warning("Dados insuficientes (vistoriador, imóvel ou cliente de teste) para executar teste de agendamento e improdutiva.")
    
    # Teste da função de deleção de agendamentos antigos
    logging.info("\n--- Testando Deleção de Agendamentos Antigos ---")
    # Para testar, seria preciso ter agendamentos antigos no banco.
    # Ex: adicionar_entrada_agenda_unica(id_vist_teste, "2023-01-01", "10:00", tipo="ENTRADA", disponivel=False, imovel_id=id_imovel_teste)
    # E depois chamar:
    # contagem_delecao = deletar_agendamentos_antigos_e_dados_relacionados(meses_antiguidade=6)
    # logging.info(f"Resultado da deleção de agendamentos antigos: {contagem_delecao}")
    logging.info("Teste de deleção de agendamentos antigos não executado em detalhe (requer dados antigos específicos).")


    logging.info("\n--- Fim dos testes agenda_model.py ---")

