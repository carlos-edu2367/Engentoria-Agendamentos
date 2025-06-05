# engentoria/utils/helpers.py
import datetime
from typing import Optional, Tuple
import logging

# --- Funções de Formatação de Data ---

def formatar_data_para_exibicao(data_iso: Optional[str]) -> str:
    """
    Converte uma data do formato ISO (YYYY-MM-DD) para o formato de exibição brasileiro (DD/MM/YYYY).

    Se a entrada for None, uma string vazia, ou se a conversão falhar, retorna uma string vazia.
    Também tenta retornar a própria string de entrada se ela já estiver no formato DD/MM/YYYY.

    Args:
        data_iso (Optional[str]): A string da data no formato "YYYY-MM-DD" ou já em "DD/MM/YYYY".
                                  Pode ser None.

    Returns:
        str: A data formatada como "DD/MM/YYYY" ou uma string vazia em caso de falha ou entrada nula.
    """
    if not data_iso: # --> Verifica se a entrada é None ou vazia
        return ""
    try:
        # Tenta converter de YYYY-MM-DD para DD/MM/YYYY
        data_obj = datetime.datetime.strptime(data_iso, "%Y-%m-%d")
        return data_obj.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        # Se a conversão falhar, verifica se a string já está no formato DD/MM/YYYY
        # Isso adiciona uma flexibilidade para aceitar datas já formatadas.
        if isinstance(data_iso, str) and len(data_iso) == 10 and data_iso[2] == '/' and data_iso[5] == '/':
            try:
                # Valida se a string no formato DD/MM/YYYY é uma data válida
                datetime.datetime.strptime(data_iso, "%d/%m/%Y")
                return data_iso # --> Retorna a própria string se já estiver no formato correto e for válida
            except ValueError:
                return "" # --> Formato DD/MM/YYYY mas data inválida (ex: 31/02/2023)
        return "" # --> Retorna vazio para outros casos de erro ou formato inesperado

def formatar_data_para_banco(data_exibicao: Optional[str]) -> Optional[str]:
    """
    Converte uma data do formato de exibição brasileiro (DD/MM/YYYY) para o formato ISO (YYYY-MM-DD),
    que é geralmente preferido para armazenamento em bancos de dados.

    Se a entrada for None, uma string vazia, ou se a conversão falhar, retorna None.
    Também tenta retornar a própria string de entrada se ela já estiver no formato YYYY-MM-DD.

    Args:
        data_exibicao (Optional[str]): A string da data no formato "DD/MM/YYYY" ou já em "YYYY-MM-DD".
                                     Pode ser None.

    Returns:
        Optional[str]: A data formatada como "YYYY-MM-DD" ou None em caso de falha ou entrada nula.
    """
    if not data_exibicao: # --> Verifica se a entrada é None ou vazia
        return None
    try:
        # Tenta converter de DD/MM/YYYY para YYYY-MM-DD
        data_obj = datetime.datetime.strptime(data_exibicao, "%d/%m/%Y")
        return data_obj.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        # Se a conversão falhar, verifica se a string já está no formato YYYY-MM-DD
        if isinstance(data_exibicao, str) and len(data_exibicao) == 10 and data_exibicao[4] == '-' and data_exibicao[7] == '-':
            try:
                # Valida se a string no formato YYYY-MM-DD é uma data válida
                datetime.datetime.strptime(data_exibicao, "%Y-%m-%d")
                return data_exibicao # --> Retorna a própria string se já estiver no formato correto e for válida
            except ValueError:
                return None # --> Formato YYYY-MM-DD mas data inválida
        return None # --> Retorna None para outros casos de erro ou formato inesperado

def formatar_horario_para_exibicao(horario_db: Optional[str]) -> str:
    """
    Formata uma string de horário do banco de dados (que pode ser "HH:MM" ou "HH:MM:SS")
    para um formato de exibição simplificado ("HH:MM").

    Args:
        horario_db (Optional[str]): A string de horário como armazenada no banco.
                                  Pode ser None.

    Returns:
        str: O horário formatado como "HH:MM". Retorna a string original se a entrada
             for None, vazia ou não puder ser parseada para um dos formatos esperados.
             Isso difere das funções de data, que retornam string vazia ou None em caso de falha.
             A intenção aqui pode ser exibir o dado "como está" se a formatação específica falhar.
    """
    if not horario_db:
        return "" # --> Retorna string vazia para None ou horário vazio.

    parsed_time_obj: Optional[datetime.time] = None
    try:
        # Verifica o comprimento da string para tentar o parse mais apropriado.
        if len(horario_db) == 8 and horario_db[2] == ':' and horario_db[5] == ':': # Formato HH:MM:SS
            parsed_time_obj = datetime.datetime.strptime(horario_db, "%H:%M:%S").time()
        elif len(horario_db) == 5 and horario_db[2] == ':': # Formato HH:MM
            parsed_time_obj = datetime.datetime.strptime(horario_db, "%H:%M").time()

        if parsed_time_obj:
            return parsed_time_obj.strftime("%H:%M") # --> Formata para HH:MM
        
        # Se não correspondeu a nenhum formato esperado mas não levantou ValueError (ex: string 'Invalido')
        # retorna a string original. Isso pode ser ajustado para retornar "" se for preferível.
        return horario_db
    except (ValueError, TypeError):
        # Se o parsing falhar (ex: string 'abc' ou formato numérico incorreto)
        return horario_db # --> Retorna a string original em caso de erro de parsing

# --- Funções de Tradução e Formatação de Texto ---

def traduzir_dia_semana(dia_ingles_ou_numero_weekday: any, abreviado: bool = False) -> str:
    """
    Traduz o nome de um dia da semana do inglês para o português, ou converte
    um número de dia da semana (onde Segunda-feira=0, ..., Domingo=6, conforme
    `datetime.weekday()`) para seu nome em português.

    Args:
        dia_ingles_ou_numero_weekday (any): O nome do dia em inglês (ex: "Monday")
                                           ou o número do dia da semana (0-6).
        abreviado (bool): Se True, retorna o nome abreviado do dia (ex: "Seg").
                          Se False (padrão), retorna o nome completo (ex: "Segunda-feira").

    Returns:
        str: O nome do dia da semana em português (completo ou abreviado).
             Retorna a entrada original convertida para string se não houver tradução.
    """
    # Mapas para tradução dos dias da semana
    mapa_dias_completos = {
        "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
        "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo",
        0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", # Padrão datetime.weekday()
        3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"
    }
    mapa_dias_abreviados = {
        "Monday": "Seg", "Tuesday": "Ter", "Wednesday": "Qua",
        "Thursday": "Qui", "Friday": "Sex", "Saturday": "Sáb", "Sunday": "Dom",
        0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"
    }

    chave_de_busca = dia_ingles_ou_numero_weekday
    if isinstance(dia_ingles_ou_numero_weekday, str):
        # Padroniza a string de entrada para ter a primeira letra maiúscula e o resto minúsculo,
        # para corresponder às chaves do mapa (ex: "monday" -> "Monday").
        chave_de_busca = dia_ingles_ou_numero_weekday.capitalize()

    if abreviado:
        # Usa o mapa de nomes abreviados. Se a chave não for encontrada, retorna a chave original como string.
        return mapa_dias_abreviados.get(chave_de_busca, str(dia_ingles_ou_numero_weekday))
    # Usa o mapa de nomes completos.
    return mapa_dias_completos.get(chave_de_busca, str(dia_ingles_ou_numero_weekday))

def formatar_valor_monetario(valor: Optional[float]) -> str:
    """
    Formata um valor numérico (float) para uma representação de string monetária
    no padrão brasileiro (R$ 1.234,56).

    Args:
        valor (Optional[float]): O valor numérico a ser formatado. Pode ser None.

    Returns:
        str: A string formatada como valor monetário (ex: "R$ 1.234,56").
             Retorna "R$ 0,00" se o valor for None.
             Retorna "R$ N/A" se ocorrer um erro na formatação (improvável com float).
    """
    if valor is None:
        return "R$ 0,00"
    try:
        # Formata o float para ter duas casas decimais e separador de milhares.
        # A formatação `:,.2f` usa vírgula como separador de milhar e ponto como decimal (padrão US).
        # Ex: 1234.56 -> "1,234.56"
        valor_formatado_inicial = f"{valor:,.2f}"
        # Substitui temporariamente a vírgula do milhar por 'X' para não conflitar com a substituição do decimal.
        # Substitui o ponto decimal por vírgula.
        # Substitui 'X' (milhar temporário) por ponto.
        # Resultado: "1.234,56"
        return f"R$ {valor_formatado_inicial.replace(',', 'X').replace('.', ',').replace('X', '.')}"
    except (ValueError, TypeError): # Erro na formatação (pouco provável para float)
        return "R$ N/A"

# --- Funções de Lógica de Filtro de Data ---

def obter_datas_para_filtro_periodo(filtro_texto: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Interpreta uma string de filtro de período (ex: "Hoje", "Esta semana", "01/01/2023 - 31/01/2023")
    e retorna uma tupla com as datas de início e fim correspondentes no formato "YYYY-MM-DD".

    Esta função é útil para traduzir seleções de período amigáveis ao usuário em datas
    que podem ser usadas em queries SQL.

    Args:
        filtro_texto (str): A string que descreve o período desejado.
            Valores predefinidos: "Hoje", "Amanhã", "Esta semana", "Próximas 2 semanas",
                                 "Últimos 5 dias", "Últimos 15 dias", "Mês Atual", "Mês Anterior",
                                 "Todos os horários", "Todos os agendamentos", "Todo o período".
            Também aceita um intervalo no formato "DD/MM/YYYY - DD/MM/YYYY".

    Returns:
        Tuple[Optional[str], Optional[str]]: Uma tupla contendo (data_inicio, data_fim).
            As datas são strings no formato "YYYY-MM-DD".
            Retorna (None, None) se o filtro_texto for para "todos" ou se não puder ser
            interpretado como um período válido (o que significa sem filtro de data).
    """
    hoje = datetime.date.today() # --> Data atual
    data_inicio_obj: Optional[datetime.date] = None # --> Data de início como objeto datetime.date
    data_fim_obj: Optional[datetime.date] = None   # --> Data de fim como objeto datetime.date

    # Lógica para interpretar os filtros de texto predefinidos
    if filtro_texto == "Hoje":
        data_inicio_obj = hoje
        data_fim_obj = hoje
    elif filtro_texto == "Amanhã":
        amanha = hoje + datetime.timedelta(days=1)
        data_inicio_obj = amanha
        data_fim_obj = amanha
    elif filtro_texto == "Esta semana":
        # Início da semana (Segunda-feira, pois hoje.weekday() é 0 para Segunda)
        data_inicio_obj = hoje - datetime.timedelta(days=hoje.weekday())
        # Fim da semana (Domingo)
        data_fim_obj = data_inicio_obj + datetime.timedelta(days=6)
    elif filtro_texto == "Próximas 2 semanas":
        data_inicio_obj = hoje # Começa de hoje
        # Fim da segunda semana a partir do início da semana atual
        data_fim_obj = (hoje - datetime.timedelta(days=hoje.weekday())) + datetime.timedelta(days=13) # (Início da semana atual) + 13 dias
    elif filtro_texto == "Últimos 5 dias":
        data_inicio_obj = hoje - datetime.timedelta(days=4) # Inclui hoje, então 4 dias atrás
        data_fim_obj = hoje
    elif filtro_texto == "Últimos 15 dias":
        data_inicio_obj = hoje - datetime.timedelta(days=14) # Inclui hoje
        data_fim_obj = hoje
    elif filtro_texto == "Mês Atual":
        data_inicio_obj = hoje.replace(day=1) # Primeiro dia do mês atual
        # Último dia do mês atual: vai para o primeiro dia do próximo mês e subtrai um dia.
        if hoje.month == 12: # Tratamento para Dezembro
            data_fim_obj = hoje.replace(year=hoje.year + 1, month=1, day=1) - datetime.timedelta(days=1)
        else:
            data_fim_obj = hoje.replace(month=hoje.month + 1, day=1) - datetime.timedelta(days=1)
    elif filtro_texto == "Mês Anterior":
        primeiro_dia_mes_atual = hoje.replace(day=1)
        data_fim_obj = primeiro_dia_mes_atual - datetime.timedelta(days=1) # Último dia do mês anterior
        data_inicio_obj = data_fim_obj.replace(day=1) # Primeiro dia do mês anterior
    elif filtro_texto in ["Todos os horários", "Todos os agendamentos", "Todo o período"]:
        # Se o filtro indica para não aplicar restrição de data, retorna None para início e fim.
        return None, None
    else:
        # Tenta interpretar o filtro_texto como um intervalo de datas no formato "DD/MM/YYYY - DD/MM/YYYY"
        try:
            if " - " in filtro_texto:
                inicio_str, fim_str = filtro_texto.split(" - ")
                data_inicio_obj = datetime.datetime.strptime(inicio_str.strip(), "%d/%m/%Y").date()
                data_fim_obj = datetime.datetime.strptime(fim_str.strip(), "%d/%m/%Y").date()
            # Se não for um dos predefinidos e nem um intervalo reconhecido,
            # assume-se que não há filtro de data a ser aplicado.
            # Um log aqui ajuda a identificar filtros não manipulados.
        except ValueError:
            logging.debug(f"Formato de filtro de data não reconhecido ou inválido: '{filtro_texto}'. Nenhum filtro de data será aplicado.")
            return None, None # --> Indica que não há filtro de data

    # Formata as datas de objeto para string "YYYY-MM-DD" se existirem, caso contrário, retorna None.
    data_inicio_str = data_inicio_obj.strftime("%Y-%m-%d") if data_inicio_obj else None
    data_fim_str = data_fim_obj.strftime("%Y-%m-%d") if data_fim_obj else None

    return data_inicio_str, data_fim_str


# Bloco para testes rápidos quando o script é executado diretamente
if __name__ == '__main__':
    print("--- Testes de Helpers ---")

    print("\n-- Formatação de Data --")
    print(f"Data ISO '2023-10-26' para Exibição: {formatar_data_para_exibicao('2023-10-26')}") # Esperado: 26/10/2023
    print(f"Data Exibição '26/10/2023' para Exibição: {formatar_data_para_exibicao('26/10/2023')}") # Esperado: 26/10/2023
    print(f"Data ISO 'invalida' para Exibição: {formatar_data_para_exibicao('invalida')}")       # Esperado: ""
    print(f"Data None para Exibição: {formatar_data_para_exibicao(None)}")                   # Esperado: ""
    print(f"Data Exibição '26/10/2023' para Banco: {formatar_data_para_banco('26/10/2023')}") # Esperado: 2023-10-26
    print(f"Data Banco '2023-10-26' para Banco: {formatar_data_para_banco('2023-10-26')}")   # Esperado: 2023-10-26
    print(f"Data Exibição 'invalida' para Banco: {formatar_data_para_banco('invalida')}")     # Esperado: None
    print(f"Data None para Banco: {formatar_data_para_banco(None)}")                     # Esperado: None

    print("\n-- Formatação de Horário --")
    print(f"Horário DB '14:30:00' para Exibição: {formatar_horario_para_exibicao('14:30:00')}") # Esperado: 14:30
    print(f"Horário DB '09:05' para Exibição: {formatar_horario_para_exibicao('09:05')}")     # Esperado: 09:05
    print(f"Horário DB 'invalido' para Exibição: {formatar_horario_para_exibicao('invalido')}") # Esperado: invalido
    print(f"Horário DB None para Exibição: {formatar_horario_para_exibicao(None)}")           # Esperado: "" (ou o original, dependendo da impl)

    print("\n-- Tradução Dia Semana --")
    print(f"Dia 'Monday' completo: {traduzir_dia_semana('Monday')}")         # Esperado: Segunda-feira
    print(f"Dia 0 (weekday) completo: {traduzir_dia_semana(0)}")              # Esperado: Segunda-feira
    print(f"Dia 'friday' abreviado: {traduzir_dia_semana('friday', True)}")    # Esperado: Sex
    print(f"Dia 6 (weekday) abreviado: {traduzir_dia_semana(6, True)}")        # Esperado: Dom
    print(f"Dia 'InvalidDay' completo: {traduzir_dia_semana('InvalidDay')}") # Esperado: InvalidDay

    print("\n-- Formatação Valor Monetário --")
    print(f"Valor 1234.56: {formatar_valor_monetario(1234.56)}")  # Esperado: R$ 1.234,56
    print(f"Valor 0: {formatar_valor_monetario(0)}")              # Esperado: R$ 0,00
    print(f"Valor 75.0: {formatar_valor_monetario(75.0)}")          # Esperado: R$ 75,00
    print(f"Valor None: {formatar_valor_monetario(None)}")        # Esperado: R$ 0,00

    print("\n-- Obter Datas para Filtro de Período --")
    print(f"Filtro 'Hoje': {obter_datas_para_filtro_periodo('Hoje')}")
    print(f"Filtro 'Esta semana': {obter_datas_para_filtro_periodo('Esta semana')}")
    print(f"Filtro 'Próximas 2 semanas': {obter_datas_para_filtro_periodo('Próximas 2 semanas')}")
    print(f"Filtro 'Últimos 5 dias': {obter_datas_para_filtro_periodo('Últimos 5 dias')}")
    print(f"Filtro 'Mês Atual': {obter_datas_para_filtro_periodo('Mês Atual')}")
    print(f"Filtro 'Mês Anterior': {obter_datas_para_filtro_periodo('Mês Anterior')}")
    print(f"Filtro 'Todo o período': {obter_datas_para_filtro_periodo('Todo o período')}") # Esperado: (None, None)
    print(f"Filtro '01/05/2024 - 31/05/2024': {obter_datas_para_filtro_periodo('01/05/2024 - 31/05/2024')}")
    print(f"Filtro 'Texto Inválido': {obter_datas_para_filtro_periodo('Texto Inválido')}") # Esperado: (None, None)
