# engentoria/utils/validators.py
import re # Módulo para operações com expressões regulares
import datetime # Módulo para manipulação de datas e horas
from typing import Optional # Para anotações de tipo opcionais

def is_valid_email(email: str) -> bool:
    """
    Verifica se uma string fornecida é um endereço de e-mail sintaticamente válido
    utilizando uma expressão regular comum.

    Esta validação verifica o formato do e-mail, mas não garante que o e-mail
    realmente exista ou esteja ativo.

    Args:
        email (str): A string do e-mail a ser validada.

    Returns:
        bool: True se a string corresponder ao padrão de e-mail, False caso contrário.
              Retorna False também se a entrada for None ou uma string vazia.
    """
    if not email: # --> Se o e-mail for None ou uma string vazia, é inválido.
        return False

    # Expressão Regular (regex) para validar o formato de e-mail:
    # ^                                      --> Início da string.
    # [a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+       --> Parte local do e-mail (antes do @):
    #                                            Permite letras, números e um conjunto de caracteres especiais. O '+' indica uma ou mais ocorrências.
    # (?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)* --> Permite subpartes na parte local separadas por pontos (ex: nome.sobrenome).
    #                                            (?:...) é um grupo de não captura. '*' indica zero ou mais ocorrências.
    # @                                      --> O símbolo '@', separador obrigatório.
    # (?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+ --> Domínio principal e subdomínios (ex: exemplo.com, sub.exemplo.co.uk):
    #                                            [a-zA-Z0-9]             --> Deve começar com letra ou número.
    #                                            (?:[a-zA-Z0-9-]*[a-zA-Z0-9])? --> Permite letras, números ou hífens no meio, terminando com letra ou número. '?' torna opcional.
    #                                            \.                     --> Literalmente um ponto.
    #                                            O '+' no final do grupo garante que haja pelo menos um componente de domínio (ex: 'com').
    # [a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])? --> Top-Level Domain (TLD) (ex: com, org, br).
    # $                                      --> Fim da string.
    pattern = r"^[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$"
    
    # re.match() tenta encontrar o padrão no início da string.
    # Se houver uma correspondência, retorna um objeto match; caso contrário, retorna None.
    return re.match(pattern, email) is not None

def is_valid_password(password: str, min_length: int = 6,
                      require_uppercase: bool = False,
                      require_lowercase: bool = False,
                      require_digit: bool = False,
                      require_special_char: bool = False) -> bool:
    """
    Verifica se uma senha atende a um conjunto de critérios de complexidade definidos.

    Args:
        password (str): A senha a ser validada.
        min_length (int): O comprimento mínimo exigido para a senha. Padrão é 6.
        require_uppercase (bool): Se True, a senha deve conter pelo menos uma letra maiúscula. Padrão False.
        require_lowercase (bool): Se True, a senha deve conter pelo menos uma letra minúscula. Padrão False.
        require_digit (bool): Se True, a senha deve conter pelo menos um dígito numérico. Padrão False.
        require_special_char (bool): Se True, a senha deve conter pelo menos um caractere especial
                                     (do conjunto !@#$%^&*()_+\-=[\]{};':"\\|,.<>\/?`~). Padrão False.

    Returns:
        bool: True se a senha atender a todos os critérios especificados, False caso contrário.
              Retorna False também se a senha for None.
    """
    if not password: # --> Senha não pode ser None
        return False
    if len(password) < min_length: # --> Verifica o comprimento mínimo
        return False
    if require_uppercase and not re.search(r"[A-Z]", password): # --> Procura por letra maiúscula
        return False
    if require_lowercase and not re.search(r"[a-z]", password): # --> Procura por letra minúscula
        return False
    if require_digit and not re.search(r"[0-9]", password): # --> Procura por dígito
        return False
    # --> Procura por um caractere especial. O conjunto de caracteres especiais pode ser ajustado.
    if require_special_char and not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", password):
        return False
    return True # --> Se passou por todas as verificações, a senha é válida

def clean_phone(phone: Optional[str]) -> str:
    """
    Remove todos os caracteres não numéricos de uma string de número de telefone.

    Útil para padronizar números de telefone antes de validar ou armazenar.

    Args:
        phone (Optional[str]): A string do número de telefone, que pode conter
                               caracteres como '(', ')', '-', ' '. Pode ser None.

    Returns:
        str: Uma string contendo apenas os dígitos do número de telefone.
             Retorna uma string vazia se a entrada for None.
    """
    if phone is None:
        return ""
    # re.sub(r'\D', '', phone) substitui qualquer caractere que NÃO seja um dígito (\D)
    # por uma string vazia ('').
    return re.sub(r'\D', '', phone)

def is_valid_phone(phone: Optional[str], allow_empty: bool = True) -> bool:
    """
    Verifica se uma string representa um número de telefone brasileiro válido,
    após uma limpeza básica (remoção de não dígitos).

    A validação é simplificada, verificando apenas o comprimento comum de números
    brasileiros com DDD (10 ou 11 dígitos).

    Args:
        phone (Optional[str]): O número de telefone a ser validado. Pode conter formatação.
        allow_empty (bool): Se True (padrão), considera uma string vazia ou None como válida
                            (útil para campos de telefone opcionais).

    Returns:
        bool: True se o número de telefone for considerado válido ou se for permitido vazio e estiver vazio.
              False caso contrário.
    """
    if phone is None or not phone.strip(): # .strip() remove espaços em branco no início e fim
        return allow_empty # --> Se vazio/None, retorna o valor de allow_empty

    cleaned_phone_number = clean_phone(phone) # --> Remove caracteres não numéricos

    # Verifica se o número limpo tem 10 dígitos (fixo com DDD) ou 11 dígitos (celular com DDD).
    # Ex: 6233334444 (10 dígitos), 62999998888 (11 dígitos).
    if 10 <= len(cleaned_phone_number) <= 11:
        # Uma validação mais rigorosa poderia verificar o prefixo do DDD,
        # ou se o nono dígito (para celulares) é '9'.
        # Exemplo (comentado) de verificação de DDD (simplificado):
        # ddd_part = int(cleaned_phone_number[:2])
        # if not (11 <= ddd_part <= 99): # Intervalo de DDDs brasileiros (aproximado)
        #     return False
        return True
    return False # --> Se não atender aos critérios de comprimento, é inválido.

def is_valid_cep(cep: Optional[str], allow_empty: bool = True) -> bool:
    """
    Verifica se uma string representa um CEP (Código de Endereçamento Postal)
    brasileiro válido, considerando os formatos "XXXXX-XXX" ou "XXXXXXXX".

    Args:
        cep (Optional[str]): A string do CEP a ser validada.
        allow_empty (bool): Se True (padrão), considera None ou string vazia como válido.

    Returns:
        bool: True se o CEP for válido ou se for permitido vazio e estiver vazio.
              False caso contrário.
    """
    if cep is None or not cep.strip():
        return allow_empty

    # Tentativa 1: Validar o formato "XXXXXXXX" (apenas dígitos)
    cleaned_cep_digits_only = re.sub(r'\D', '', cep) # Remove todos os não dígitos
    if len(cleaned_cep_digits_only) == 8 and cleaned_cep_digits_only.isdigit():
        return True

    # Tentativa 2: Validar o formato "XXXXX-XXX"
    # ^\d{5}   --> Início da string, seguido por exatamente 5 dígitos.
    # -        --> Um hífen literal.
    # \d{3}$   --> Exatamente 3 dígitos, seguido pelo fim da string.
    pattern_formatted = r"^\d{5}-\d{3}$"
    return re.match(pattern_formatted, cep) is not None

def is_positive_float_or_int(value_str: Optional[str], allow_zero: bool = False) -> bool:
    """
    Verifica se uma string pode ser convertida para um número (float ou int)
    e se esse número é positivo (ou não negativo, se `allow_zero` for True).

    Aceita tanto ponto (.) quanto vírgula (,) como separador decimal.

    Args:
        value_str (Optional[str]): A string a ser validada.
        allow_zero (bool): Se True, permite que o valor seja zero. Padrão é False (exige > 0).

    Returns:
        bool: True se a string representa um número positivo (ou não negativo) válido,
              False caso contrário ou se a string for None/vazia.
    """
    if value_str is None or not value_str.strip(): # --> Entrada não pode ser nula ou vazia
        return False
    try:
        # Substitui vírgula por ponto para padronizar o separador decimal antes de converter para float.
        standardized_value_str = value_str.replace(',', '.')
        numeric_value = float(standardized_value_str) # --> Tenta converter para float

        if allow_zero:
            return numeric_value >= 0 # --> Permite zero
        return numeric_value > 0    # --> Exige estritamente positivo
    except ValueError:
        # A conversão para float falhou (ex: a string não é um número válido como "abc")
        return False

def is_not_empty(value: Optional[str]) -> bool:
    """
    Verifica se uma string não é None e não consiste apenas em espaços em branco.

    Args:
        value (Optional[str]): A string a ser verificada.

    Returns:
        bool: True se a string tiver algum conteúdo visível, False caso contrário.
    """
    # bool(value.strip()) é True se, após remover espaços, a string não for vazia.
    return value is not None and bool(value.strip())

def is_valid_date_format(date_str: Optional[str], date_format: str = "%d/%m/%Y", allow_empty: bool = True) -> bool:
    """
    Verifica se uma string de data corresponde a um formato de data especificado.

    Args:
        date_str (Optional[str]): A string da data a ser validada.
        date_format (str): O formato de data esperado, usando as diretivas de `strptime`
                           (ex: "%d/%m/%Y" para DD/MM/YYYY). Padrão é "%d/%m/%Y".
        allow_empty (bool): Se True (padrão), considera None ou string vazia como válida.

    Returns:
        bool: True se a string da data corresponder ao formato ou se for permitido vazio
              e estiver vazia. False caso contrário.
    """
    if date_str is None or not date_str.strip():
        return allow_empty # --> Se vazio/None, retorna o valor de allow_empty

    try:
        # datetime.datetime.strptime tenta parsear a string de data de acordo com o formato.
        # Se o parse for bem-sucedido, a data é válida no formato especificado.
        # Se falhar, levanta um ValueError.
        datetime.datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        # A string não corresponde ao formato de data esperado.
        return False

# Exemplos de outros validadores que poderiam ser adicionados:
# def validar_cpf(cpf: str) -> bool: ...
# def validar_cnpj(cnpj: str) -> bool: ...
# def validar_formato_horario(horario_str: str, formato: str = "%H:%M") -> bool: ...


# Bloco para testes rápidos quando o script é executado diretamente
if __name__ == '__main__':
    print("--- Testes de Validadores ---")

    print("\n-- Validação de E-mail --")
    print(f"Email 'teste@exemplo.com' é válido? {is_valid_email('teste@exemplo.com')}") # Esperado: True
    print(f"Email 'teste@exemplo' é válido? {is_valid_email('teste@exemplo')}")         # Esperado: False
    print(f"Email 'teste@exemplo.co.uk' é válido? {is_valid_email('teste@exemplo.co.uk')}")# Esperado: True
    print(f"Email '' (vazio) é válido? {is_valid_email('')}")                           # Esperado: False
    print(f"Email None é válido? {is_valid_email(None)}")                             # Esperado: False (implicitamente, pois 'not email' será True)

    print("\n-- Validação de Senha --")
    print(f"Senha '12345' (min 6): {is_valid_password('12345', min_length=6)}") # Esperado: False
    print(f"Senha '123456' (min 6): {is_valid_password('123456', min_length=6)}") # Esperado: True
    print(f"Senha 'Senha1' (min 6, Upper, lower): {is_valid_password('Senha1', min_length=6, require_uppercase=True, require_lowercase=True)}") # Esperado: True
    print(f"Senha 'senha' (min 6, exige Upper): {is_valid_password('senha', min_length=6, require_uppercase=True)}") # Esperado: False
    print(f"Senha 'SenhaForte123!' (todos critérios): {is_valid_password('SenhaForte123!', min_length=8, require_uppercase=True, require_lowercase=True, require_digit=True, require_special_char=True)}") # Esperado: True

    print("\n-- Validação de Telefone --")
    print(f"Telefone '(62) 99999-8888': {is_valid_phone('(62) 99999-8888')}") # Esperado: True
    print(f"Telefone '62999998888': {is_valid_phone('62999998888')}")         # Esperado: True
    print(f"Telefone '6233334444': {is_valid_phone('6233334444')}")           # Esperado: True
    print(f"Telefone '123' (inválido): {is_valid_phone('123')}")                 # Esperado: False
    print(f"Telefone '' (vazio, allow_empty=True): {is_valid_phone('')}")       # Esperado: True
    print(f"Telefone None (allow_empty=True): {is_valid_phone(None)}")           # Esperado: True
    print(f"Telefone '' (vazio, allow_empty=False): {is_valid_phone('', allow_empty=False)}") # Esperado: False

    print("\n-- Validação de CEP --")
    print(f"CEP '74000-000': {is_valid_cep('74000-000')}")       # Esperado: True
    print(f"CEP '74000000': {is_valid_cep('74000000')}")         # Esperado: True
    print(f"CEP '7400-000' (inválido): {is_valid_cep('7400-000')}")# Esperado: False
    print(f"CEP '' (vazio, allow_empty=True): {is_valid_cep('')}") # Esperado: True

    print("\n-- Validação de Float/Int Positivo --")
    print(f"Valor '10.5': {is_positive_float_or_int('10.5')}")        # Esperado: True
    print(f"Valor '10,5': {is_positive_float_or_int('10,5')}")        # Esperado: True
    print(f"Valor '10': {is_positive_float_or_int('10')}")            # Esperado: True
    print(f"Valor '0' (allow_zero=False): {is_positive_float_or_int('0')}") # Esperado: False
    print(f"Valor '0' (allow_zero=True): {is_positive_float_or_int('0', allow_zero=True)}") # Esperado: True
    print(f"Valor '-5.5': {is_positive_float_or_int('-5.5')}")      # Esperado: False
    print(f"Valor 'texto' (inválido): {is_positive_float_or_int('texto')}") # Esperado: False

    print("\n-- Validação de Não Vazio --")
    print(f"String '  ' não está vazia? {is_not_empty('  ')}")       # Esperado: False
    print(f"String 'texto' não está vazia? {is_not_empty('texto')}") # Esperado: True
    print(f"String None não está vazia? {is_not_empty(None)}")       # Esperado: False

    print("\n-- Validação de Formato de Data --")
    print(f"Data '03/06/2025' (formato DD/MM/YYYY): {is_valid_date_format('03/06/2025')}") # Esperado: True
    print(f"Data '2025-06-03' (formato DD/MM/YYYY): {is_valid_date_format('2025-06-03')}") # Esperado: False
    print(f"Data '2025-06-03' (formato YYYY-MM-DD): {is_valid_date_format('2025-06-03', date_format='%Y-%m-%d')}") # Esperado: True
    print(f"Data '3/6/2025' (formato DD/MM/YYYY): {is_valid_date_format('3/6/2025')}") # Esperado: False (precisa de zeros à esquerda)
    print(f"Data '31/02/2025' (inválida): {is_valid_date_format('31/02/2025')}")   # Esperado: False
    print(f"Data '' (vazia, allow_empty=True): {is_valid_date_format('')}")       # Esperado: True
    print(f"Data '' (vazia, allow_empty=False): {is_valid_date_format('', allow_empty=False)}") # Esperado: False
