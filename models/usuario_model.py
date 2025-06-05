# engentoria/models/usuario_model.py

import sqlite3
import datetime as dt
import pandas as pd
import logging

# Tentativa de importação relativa para uso dentro do pacote
try:
    from .database import conectar_banco, hash_senha
except ImportError:
    # Bloco de fallback para permitir execução direta do script (ex: para testes isolados)
    # Isso ajusta o sys.path para encontrar o módulo 'models' no diretório pai
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from models.database import conectar_banco, hash_senha, criar_tabelas

from typing import Optional, Tuple, List, Dict, Any # Tipos para anotações estáticas, melhorando a legibilidade e manutenção

# Configuração básica do logging para registrar eventos e erros do módulo
# Nível INFO: Registra mensagens informativas, avisos e erros.
# Formato: Inclui timestamp, nível do log e a mensagem.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def deletar_cliente_por_id(cliente_id: int, conexao_existente: Optional[sqlite3.Connection] = None) -> bool:
    """
    Deleta um cliente específico do banco de dados pelo seu ID.

    Esta função lida com a deleção de um cliente e, devido às configurações
    de chave estrangeira `ON DELETE CASCADE` nas tabelas 'imoveis' e 'vistorias_improdutivas',
    os registros associados nessas tabelas também serão automaticamente excluídos.

    A função pode operar com uma conexão de banco de dados existente (útil para transações)
    ou criar e gerenciar sua própria conexão.

    Args:
        cliente_id (int): O ID do cliente a ser deletado.
        conexao_existente (Optional[sqlite3.Connection]): Uma conexão SQLite existente.
            Se None, uma nova conexão será criada e gerenciada internamente.

    Returns:
        bool: True se o cliente e seus dados associados foram deletados com sucesso.
              False se o cliente não foi encontrado, ou se ocorreu um erro durante a deleção.

    Raises:
        sqlite3.IntegrityError: Pode ser levantada se houver uma restrição de chave estrangeira
            inesperada (não CASCADE) que impeça a deleção.
        Exception: Para outros erros inesperados durante a operação no banco de dados.

    Atenção:
        A exclusão de clientes é uma operação destrutiva e pode ter implicações
        significativas nos dados. Use com extrema cautela.
    """
    conexao_interna = False # Flag para indicar se a conexão foi criada nesta função
    if conexao_existente is None:
        conexao = conectar_banco() # --> Cria uma nova conexão se nenhuma foi passada
        conexao_interna = True
    else:
        conexao = conexao_existente # --> Usa a conexão SQLite fornecida

    try:
        cursor = conexao.cursor() # --> Objeto cursor para executar comandos SQL
        cursor.execute("PRAGMA foreign_keys = ON;") # --> Garante que as constraints de FK sejam respeitadas

        # Etapa 1: Verificar se o cliente existe antes de tentar deletar
        # Isso evita erros desnecessários e permite um feedback mais preciso.
        cursor.execute("SELECT nome FROM clientes WHERE id = ?", (cliente_id,))
        cliente_data = cursor.fetchone() # --> Tenta buscar o nome do cliente

        if not cliente_data:
            logging.info(f"ℹ️ Cliente ID {cliente_id} não encontrado para deleção.")
            return False # Cliente não existe, então a "deleção" não ocorreu neste contexto

        nome_cliente_deletado = cliente_data[0] # --> Nome do cliente para logging
        logging.warning(f"⚠️ Tentativa de deletar cliente ID {cliente_id} (Nome: {nome_cliente_deletado}). Esta ação é destrutiva e deletará imóveis e vistorias improdutivas associadas devido ao ON DELETE CASCADE.")

        # Etapa 2: Executar a deleção do cliente
        # A deleção em cascata (CASCADE) configurada no banco de dados para as tabelas
        # 'imoveis' (via cliente_id) e 'vistorias_improdutivas' (via cliente_id)
        # será acionada aqui.
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))

        if conexao_interna:
            conexao.commit() # --> Confirma a transação se a conexão foi criada aqui

        # Etapa 3: Verificar o resultado da deleção
        if cursor.rowcount > 0: # --> rowcount indica o número de linhas afetadas pela última query
            logging.info(f"✅ Cliente ID {cliente_id} (Nome: {nome_cliente_deletado}) e seus dados associados (imóveis, vistorias improdutivas) foram deletados com sucesso.")
            return True
        else:
            # Esta condição é improvável se o cliente foi encontrado no SELECT anterior,
            # a menos que haja uma condição de corrida (raro em SQLite single-user) ou
            # se a deleção falhou silenciosamente por algum motivo não capturado como erro.
            logging.warning(f"⚠️ Cliente ID {cliente_id} (Nome: {nome_cliente_deletado}) foi encontrado mas não deletado (rowcount=0). Verifique o estado do banco.")
            return False

    except sqlite3.IntegrityError as e:
        # Este erro ocorreria se alguma outra tabela tivesse uma FK para 'clientes'
        # com `ON DELETE RESTRICT` ou `ON DELETE NO ACTION` e houvesse registros dependentes.
        logging.error(f"❌ Erro de integridade ao tentar deletar cliente ID {cliente_id}: {e}. Verifique se existem outras dependências não configuradas com CASCADE ou SET NULL.")
        if conexao_interna and conexao:
            conexao.rollback() # --> Desfaz a transação em caso de erro, se gerenciada internamente
        return False
    except Exception as e:
        logging.error(f"❌ Erro inesperado ao deletar cliente ID {cliente_id}: {e}", exc_info=True) # exc_info=True inclui o traceback no log
        if conexao_interna and conexao:
            conexao.rollback()
        return False
    finally:
        if conexao_interna and conexao:
            conexao.close() # --> Fecha a conexão se foi criada nesta função

# --- Funções relacionadas a Usuários (Administradores e Vistoriadores) ---
def cadastrar_usuario(nome: str, email: str, senha: str, tipo: str, telefone1: Optional[str] = None, telefone2: Optional[str] = None) -> Optional[int]:
    """
    Cadastra um novo usuário (administrador ou vistoriador) no sistema.

    A senha fornecida é criptografada usando SHA-256 antes de ser armazenada.
    O tipo de usuário deve ser 'adm' ou 'vistoriador'.

    Args:
        nome (str): Nome completo do usuário.
        email (str): Endereço de e-mail do usuário. Deve ser único no sistema.
        senha (str): Senha em texto plano para o usuário.
        tipo (str): Tipo de usuário. Valores permitidos: 'adm' ou 'vistoriador'.
        telefone1 (Optional[str]): Primeiro número de telefone (opcional).
        telefone2 (Optional[str]): Segundo número de telefone (opcional).

    Returns:
        Optional[int]: O ID do usuário recém-cadastrado em caso de sucesso.
                       Retorna None se o cadastro falhar (ex: e-mail duplicado, tipo inválido).
    """
    # Validação do tipo de usuário
    if tipo not in ['adm', 'vistoriador']:
        logging.warning(f"Tentativa de cadastrar usuário com tipo inválido: '{tipo}'. Permitidos: 'adm', 'vistoriador'.")
        print("❌ Tipo de usuário inválido. Use 'adm' ou 'vistoriador'.") # Mensagem para o usuário final/console
        return None

    senha_hashed = hash_senha(senha) # --> Criptografa a senha antes de armazenar
    conexao = None # --> Inicializa a variável de conexão
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Query SQL para inserir o novo usuário
        cursor.execute("""
            INSERT INTO usuarios (nome, email, telefone1, telefone2, tipo, senha)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nome, email, telefone1, telefone2, tipo, senha_hashed))
        conexao.commit() # --> Salva as alterações no banco
        user_id = cursor.lastrowid # --> Obtém o ID do usuário recém-inserido
        logging.info(f"✅ Usuário '{nome}' (Tipo: {tipo}, Email: {email}) cadastrado com sucesso! ID: {user_id}")
        print(f"✅ Usuário '{nome}' ({tipo}) cadastrado com sucesso! ID: {user_id}")
        return user_id
    except sqlite3.IntegrityError:
        # Este erro é esperado se a constraint UNIQUE no campo 'email' for violada.
        logging.warning(f"Falha ao cadastrar usuário: O e-mail '{email}' já existe no sistema.")
        print(f"⚠️ Erro: O e-mail '{email}' já está cadastrado.")
        return None
    except Exception as e:
        logging.error(f"❌ Erro inesperado ao cadastrar usuário '{nome}' (Email: {email}): {e}", exc_info=True)
        print(f"❌ Erro inesperado ao cadastrar usuário: {e}")
        if conexao:
            conexao.rollback() # --> Desfaz alterações em caso de erro na transação
        return None
    finally:
        if conexao:
            conexao.close() # --> Garante que a conexão seja fechada

def login_usuario(email: str, senha: str) -> Optional[Tuple[int, str]]:
    """
    Autentica um usuário com base no e-mail e senha fornecidos.

    Compara o hash da senha fornecida com o hash armazenado no banco de dados.

    Args:
        email (str): E-mail do usuário que está tentando fazer login.
        senha (str): Senha em texto plano fornecida pelo usuário.

    Returns:
        Optional[Tuple[int, str]]: Uma tupla contendo o ID do usuário e o seu tipo (ex: (1, 'adm'))
                                   em caso de login bem-sucedido.
                                   Retorna None se o usuário não for encontrado, a senha estiver
                                   incorreta, ou ocorrer um erro.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Busca o usuário pelo e-mail para obter ID, senha armazenada e tipo
        cursor.execute("SELECT id, senha, tipo FROM usuarios WHERE email = ?", (email,))
        usuario_db_data = cursor.fetchone() # --> Tupla (id, senha_hash, tipo) ou None

        if usuario_db_data:
            id_usuario, senha_armazenada_hash, tipo_usuario = usuario_db_data # --> Desempacota os dados do usuário

            senha_fornecida_hash = hash_senha(senha) # --> Calcula o hash da senha fornecida

            # Compara o hash da senha fornecida com o hash armazenado
            if senha_fornecida_hash == senha_armazenada_hash:
                logging.info(f"✅ Login bem-sucedido para usuário '{email}'. ID: {id_usuario}, Tipo: {tipo_usuario}")
                print(f"✅ Login bem-sucedido para {email}! ID: {id_usuario}, Tipo: {tipo_usuario}")
                return id_usuario, tipo_usuario # --> Retorna ID e tipo do usuário
            else:
                logging.warning(f"Tentativa de login falhou para '{email}': Senha incorreta.")
                print(f"❌ Senha incorreta para o usuário {email}.")
                return None # --> Senha incorreta
        else:
            logging.info(f"Tentativa de login falhou: Usuário com e-mail '{email}' não encontrado.")
            print(f"❌ Usuário com e-mail {email} não encontrado.")
            return None # --> Usuário não encontrado
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o processo de login para o e-mail '{email}': {e}", exc_info=True)
        print(f"❌ Erro inesperado durante o login: {e}")
        return None
    finally:
        if conexao:
            conexao.close()

def redefinir_senha_usuario(email: str, nova_senha: str) -> bool:
    """
    Redefine a senha de um usuário existente.

    Args:
        email (str): E-mail do usuário cuja senha será redefinida.
        nova_senha (str): A nova senha em texto plano.

    Returns:
        bool: True se a senha foi redefinida com sucesso.
              False se o usuário não foi encontrado, a atualização falhou, ou ocorreu um erro.
    """
    nova_senha_hashed = hash_senha(nova_senha) # --> Gera o hash da nova senha
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        # Primeiro, verifica se o usuário existe
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
        usuario_db = cursor.fetchone()

        if usuario_db:
            # Se o usuário existe, atualiza a senha
            cursor.execute("UPDATE usuarios SET senha = ? WHERE email = ?", (nova_senha_hashed, email))
            conexao.commit()

            if cursor.rowcount > 0: # --> Verifica se a atualização afetou alguma linha
                logging.info(f"✅ Senha para o usuário '{email}' redefinida com sucesso.")
                print(f"✅ Senha para o usuário {email} redefinida com sucesso!")
                return True
            else:
                # Isso pode acontecer se, por algum motivo, a query UPDATE não afetar linhas
                # (ex: condição WHERE não correspondeu, o que não deveria ocorrer se o SELECT anterior funcionou).
                logging.warning(f"⚠️ Não foi possível atualizar a senha para '{email}' (nenhuma linha afetada no UPDATE), embora o usuário tenha sido encontrado.")
                print(f"⚠️ Não foi possível atualizar a senha para {email} (nenhuma linha afetada).")
                return False
        else:
            logging.info(f"Tentativa de redefinir senha falhou: Usuário com e-mail '{email}' não encontrado.")
            print(f"❌ Usuário com e-mail {email} não encontrado para redefinição de senha.")
            return False
    except Exception as e:
        logging.error(f"❌ Erro inesperado ao tentar redefinir a senha para o e-mail '{email}': {e}", exc_info=True)
        print(f"❌ Erro inesperado ao redefinir senha: {e}")
        if conexao:
            conexao.rollback()
        return False
    finally:
        if conexao:
            conexao.close()

def listar_usuarios_por_tipo(tipo_usuario: str) -> List[Dict[str, Any]]:
    """
    Lista todos os usuários de um determinado tipo (ex: 'adm' ou 'vistoriador').

    Args:
        tipo_usuario (str): O tipo de usuário a ser listado ('adm' ou 'vistoriador').

    Returns:
        List[Dict[str, Any]]: Uma lista de dicionários, onde cada dicionário representa
                               um usuário (com 'id', 'nome', 'email').
                               Retorna uma lista vazia se o tipo for inválido, nenhum usuário
                               for encontrado, ou em caso de erro.
    """
    # Validação do tipo de usuário
    if tipo_usuario not in ['adm', 'vistoriador']:
        logging.warning(f"Tentativa de listar usuários com tipo inválido: '{tipo_usuario}'.")
        print(f"❌ Tipo de usuário inválido para listagem: {tipo_usuario}")
        return []

    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Seleciona ID, nome e e-mail dos usuários filtrando pelo tipo e ordenando por nome
        cursor.execute("SELECT id, nome, email FROM usuarios WHERE tipo = ? ORDER BY nome ASC", (tipo_usuario,))
        usuarios_db_list = cursor.fetchall() # --> Lista de tuplas (id, nome, email)

        # Converte a lista de tuplas em uma lista de dicionários para facilitar o uso
        lista_de_usuarios_formatada = [{'id': row[0], 'nome': row[1], 'email': row[2]} for row in usuarios_db_list]
        
        if not lista_de_usuarios_formatada:
            logging.info(f"Nenhum usuário do tipo '{tipo_usuario}' encontrado.")
        return lista_de_usuarios_formatada
    except Exception as e:
        logging.error(f"❌ Erro ao listar usuários do tipo '{tipo_usuario}': {e}", exc_info=True)
        print(f"❌ Erro ao listar usuários do tipo '{tipo_usuario}': {e}")
        return []
    finally:
        if conexao:
            conexao.close()

def deletar_usuario(usuario_id: int) -> bool:
    """
    Deleta um usuário específico do sistema pelo seu ID.

    Atenção: Se o usuário for um vistoriador com agendamentos ou horários fixos
    associados, a deleção pode ser impedida por constraints de chave estrangeira
    (ON DELETE RESTRICT) ou pode causar a deleção em cascata (ON DELETE CASCADE)
    desses registros dependentes, dependendo da configuração do banco.
    No esquema atual:
    - `agenda.vistoriador_id` tem `ON DELETE CASCADE`.
    - `horarios_fixos.vistoriador_id` tem `ON DELETE CASCADE`.
    Portanto, deletar um vistoriador removerá suas entradas na agenda e seus horários fixos.

    Args:
        usuario_id (int): O ID do usuário a ser deletado.

    Returns:
        bool: True se o usuário foi deletado com sucesso.
              False se o usuário não foi encontrado, a deleção falhou devido a
              restrições de integridade, ou ocorreu outro erro.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;") # --> Garante a verificação de FKs

        # Antes de deletar, seria bom obter o nome e tipo para logging, se necessário.
        # user_info = obter_usuario_por_id(usuario_id) # Chamaria a função abaixo

        cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        conexao.commit()

        if cursor.rowcount > 0:
            logging.info(f"✅ Usuário ID {usuario_id} e seus dados associados (agenda, horários fixos) deletados com sucesso.")
            print(f"✅ Usuário ID {usuario_id} deletado com sucesso.")
            return True
        else:
            logging.info(f"⚠️ Usuário ID {usuario_id} não encontrado para deleção.")
            print(f"⚠️ Usuário ID {usuario_id} não encontrado para deleção.")
            return False
    except sqlite3.IntegrityError as e:
        # Este erro pode ocorrer se houver alguma outra dependência não prevista
        # com ON DELETE RESTRICT.
        logging.error(f"❌ Erro de integridade ao deletar usuário ID {usuario_id}: {e}. Verifique se existem dependências não tratadas por CASCADE (ex: em tabelas não diretamente ligadas a agendamentos).")
        print(f"❌ Erro de integridade ao deletar usuário ID {usuario_id}: {e}. Verifique dependências.")
        return False
    except Exception as e:
        logging.error(f"❌ Erro inesperado ao deletar usuário ID {usuario_id}: {e}", exc_info=True)
        print(f"❌ Erro ao deletar usuário ID {usuario_id}: {e}")
        if conexao:
            conexao.rollback()
        return False
    finally:
        if conexao:
            conexao.close()

def obter_usuario_por_id(usuario_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca e retorna os dados de um usuário específico com base no seu ID.

    Args:
        usuario_id (int): O ID do usuário a ser pesquisado.

    Returns:
        Optional[Dict[str, Any]]: Um dicionário contendo os dados do usuário
                                   (id, nome, email, tipo, telefone1, telefone2)
                                   se ele for encontrado. Retorna None caso contrário.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Seleciona os campos relevantes do usuário
        cursor.execute("SELECT id, nome, email, tipo, telefone1, telefone2 FROM usuarios WHERE id = ?", (usuario_id,))
        usuario_db_tuple = cursor.fetchone() # --> Tupla com os dados ou None

        if usuario_db_tuple:
            # Converte a tupla em um dicionário para facilitar o acesso aos campos
            usuario_formatado = {
                'id': usuario_db_tuple[0],
                'nome': usuario_db_tuple[1],
                'email': usuario_db_tuple[2],
                'tipo': usuario_db_tuple[3],
                'telefone1': usuario_db_tuple[4],
                'telefone2': usuario_db_tuple[5]
            }
            return usuario_formatado
        else:
            logging.info(f"Usuário com ID {usuario_id} não encontrado.")
            return None
    except Exception as e:
        logging.error(f"❌ Erro ao obter usuário ID {usuario_id}: {e}", exc_info=True)
        print(f"❌ Erro ao obter usuário ID {usuario_id}: {e}")
        return None
    finally:
        if conexao:
            conexao.close()

# --- Funções relacionadas a Clientes ---
def cadastrar_cliente(nome: str, email: str, telefone1: Optional[str] = None, telefone2: Optional[str] = None, saldo_devedor_total: float = 0.0) -> Optional[int]:
    """
    Cadastra um novo cliente no sistema.

    Args:
        nome (str): Nome completo do cliente. Campo obrigatório.
        email (str): Endereço de e-mail do cliente. Campo obrigatório.
                     (Considerar adicionar uma constraint UNIQUE no banco se o e-mail do cliente também deve ser único).
        telefone1 (Optional[str]): Primeiro número de telefone (opcional).
        telefone2 (Optional[str]): Segundo número de telefone (opcional).
        saldo_devedor_total (float): Saldo devedor inicial do cliente. Padrão é 0.0.

    Returns:
        Optional[int]: O ID do cliente recém-cadastrado em caso de sucesso.
                       Retorna None se o cadastro falhar (ex: campos obrigatórios faltando).
    """
    # Validação de campos obrigatórios
    if not nome or not email:
        logging.warning("Tentativa de cadastrar cliente sem nome ou e-mail. Ambos são obrigatórios.")
        print("❌ Nome e E-mail do cliente são obrigatórios.")
        return None

    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Query SQL para inserir o novo cliente
        cursor.execute("""
            INSERT INTO clientes (nome, email, telefone1, telefone2, saldo_devedor_total)
            VALUES (?, ?, ?, ?, ?)
        """, (nome, email, telefone1, telefone2, saldo_devedor_total))
        conexao.commit()
        cliente_id = cursor.lastrowid # --> ID do cliente recém-criado
        logging.info(f"✅ Cliente '{nome}' (Email: {email}) cadastrado com sucesso! ID: {cliente_id}")
        print(f"✅ Cliente '{nome}' cadastrado com sucesso! ID: {cliente_id}")
        return cliente_id
    except sqlite3.IntegrityError as ie: # Se houver constraints UNIQUE (ex: no email)
        logging.warning(f"Erro de integridade ao cadastrar cliente '{nome}' (Email: {email}): {ie}. Possível e-mail duplicado se UNIQUE.")
        print(f"❌ Erro de integridade ao cadastrar cliente: {ie}. Verifique se o e-mail já existe.")
        return None
    except Exception as e:
        logging.error(f"❌ Erro inesperado ao cadastrar cliente '{nome}' (Email: {email}): {e}", exc_info=True)
        print(f"❌ Erro inesperado ao cadastrar cliente: {e}")
        if conexao:
            conexao.rollback()
        return None
    finally:
        if conexao:
            conexao.close()

def listar_todos_clientes() -> List[Dict[str, Any]]:
    """
    Lista todos os clientes cadastrados no sistema, ordenados alfabeticamente pelo nome.

    Returns:
        List[Dict[str, Any]]: Uma lista de dicionários, onde cada dicionário representa
                               os dados de um cliente (id, nome, email, telefones, saldo).
                               Retorna uma lista vazia se nenhum cliente for encontrado
                               ou em caso de erro.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Seleciona todos os campos dos clientes, ordenando por nome
        cursor.execute("""
            SELECT id, nome, email, telefone1, telefone2, saldo_devedor_total
            FROM clientes
            ORDER BY nome ASC
        """)
        clientes_db_list = cursor.fetchall() # --> Lista de tuplas

        # Converte para lista de dicionários
        lista_de_clientes_formatada = [
            {
                'id': row[0],
                'nome': row[1],
                'email': row[2],
                'telefone1': row[3],
                'telefone2': row[4],
                'saldo_devedor_total': row[5]
            }
            for row in clientes_db_list
        ]
        if not lista_de_clientes_formatada:
            logging.info("Nenhum cliente encontrado no sistema.")
        return lista_de_clientes_formatada
    except Exception as e:
        logging.error(f"❌ Erro ao listar todos os clientes: {e}", exc_info=True)
        print(f"❌ Erro ao listar clientes: {e}")
        return []
    finally:
        if conexao:
            conexao.close()

def obter_cliente_por_id(cliente_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca e retorna os dados de um cliente específico com base no seu ID.

    Args:
        cliente_id (int): O ID do cliente a ser pesquisado.

    Returns:
        Optional[Dict[str, Any]]: Um dicionário contendo os dados do cliente
                                   se ele for encontrado. Retorna None caso contrário.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("""
            SELECT id, nome, email, telefone1, telefone2, saldo_devedor_total
            FROM clientes
            WHERE id = ?
        """, (cliente_id,))
        cliente_db_tuple = cursor.fetchone()

        if cliente_db_tuple:
            cliente_formatado = {
                'id': cliente_db_tuple[0],
                'nome': cliente_db_tuple[1],
                'email': cliente_db_tuple[2],
                'telefone1': cliente_db_tuple[3],
                'telefone2': cliente_db_tuple[4],
                'saldo_devedor_total': cliente_db_tuple[5]
            }
            return cliente_formatado
        else:
            logging.info(f"Cliente com ID {cliente_id} não encontrado.")
            return None
    except Exception as e:
        logging.error(f"❌ Erro ao obter cliente ID {cliente_id}: {e}", exc_info=True)
        print(f"❌ Erro ao obter cliente ID {cliente_id}: {e}")
        return None
    finally:
        if conexao:
            conexao.close()

# --- Função para Relatório de Devedores (baseado em Vistorias Improdutivas) ---
def obter_dados_clientes_devedores(
    data_inicio_marcacao: Optional[str] = None, # Formato 'YYYY-MM-DD'
    data_fim_marcacao: Optional[str] = None,    # Formato 'YYYY-MM-DD'
    imobiliaria_id_filtro: Optional[int] = None,
    apenas_nao_pagos: bool = True
) -> pd.DataFrame:
    """
    Gera um relatório de clientes com cobranças de vistorias improdutivas.

    A função busca registros na tabela `vistorias_improdutivas` e junta com dados
    das tabelas `clientes`, `imoveis` e `imobiliarias` para fornecer um relatório detalhado.
    Permite filtrar por:
    - Período da data em que a vistoria foi marcada como improdutiva.
    - Imobiliária associada à cobrança (se houver).
    - Status de pagamento da cobrança (padrão: apenas não pagos).

    Args:
        data_inicio_marcacao (Optional[str]): Data de início (formato 'YYYY-MM-DD') do período
                                              de marcação da improdutividade.
        data_fim_marcacao (Optional[str]): Data de fim (formato 'YYYY-MM-DD') do período
                                           de marcação da improdutividade.
        imobiliaria_id_filtro (Optional[int]): ID da imobiliária para filtrar as cobranças.
                                               Se None ou 0, não filtra por imobiliária.
        apenas_nao_pagos (bool): Se True (padrão), lista apenas cobranças não pagas.
                                 Se False, lista todas as cobranças (pagas e não pagas).

    Returns:
        pd.DataFrame: Um DataFrame do Pandas contendo os dados do relatório.
                      As colunas incluem informações da cobrança, cliente, imóvel (se houver),
                      imobiliária (se houver), e status de pagamento.
                      Retorna um DataFrame vazio em caso de erro.
    """
    # Query base para selecionar os dados necessários para o relatório
    # Utiliza LEFT JOIN para incluir imóveis e imobiliárias mesmo que não estejam associados
    # a todas as vistorias improdutivas (ex: uma improdutiva pode não ter imovel_id).
    query = """
        SELECT
            vi.id AS id_cobranca_improdutiva,    -- ID da cobrança na tabela vistorias_improdutivas
            c.id AS cliente_id,                  -- ID do cliente
            c.nome AS "Nome Cliente",            -- Nome do cliente
            c.email AS "Email Cliente",          -- Email do cliente
            c.telefone1 AS "Telefone Cliente",   -- Telefone do cliente
            vi.valor_cobranca AS "Valor Cobrança (R$)", -- Valor cobrado do cliente
            vi.valor_para_vistoriador AS "Valor Vistoriador (R$)", -- Valor repassado ao vistoriador
            strftime('%d/%m/%Y', vi.data_marcacao) AS "Data Marcação Improd.", -- Data da marcação formatada
            strftime('%d/%m/%Y', vi.data_vistoria_original) AS "Data Vistoria Original", -- Data original formatada
            vi.horario_vistoria_original AS "Horário Vistoria Original", -- Horário original
            im.cod_imovel AS "Cód. Imóvel",      -- Código do imóvel, se houver
            im.endereco AS "Endereço Imóvel",    -- Endereço do imóvel, se houver
            imob.nome AS "Imobiliária (da Cobrança)", -- Nome da imobiliária da cobrança, se houver
            vi.motivo_improdutividade AS "Motivo Improdutividade", -- Motivo
            CASE vi.pago WHEN 0 THEN 'Não' ELSE 'Sim' END AS "Pago?" -- Status de pagamento
        FROM vistorias_improdutivas vi
        JOIN clientes c ON vi.cliente_id = c.id  -- Junta com clientes (obrigatório)
        LEFT JOIN imoveis im ON vi.imovel_id = im.id -- Junta com imóveis (opcional)
        LEFT JOIN imobiliarias imob ON vi.imobiliaria_id = imob.id -- Junta com imobiliárias (opcional)
        WHERE 1=1  -- Cláusula base para facilitar a adição de filtros AND
    """
    params = [] # Lista para armazenar os parâmetros da query SQL

    # Adiciona filtros dinamicamente com base nos argumentos da função
    if apenas_nao_pagos:
        query += " AND vi.pago = 0" # Filtra por cobranças não pagas

    if data_inicio_marcacao:
        query += " AND vi.data_marcacao >= ?"
        params.append(data_inicio_marcacao)
    if data_fim_marcacao:
        query += " AND vi.data_marcacao <= ?"
        params.append(data_fim_marcacao)

    # Filtra por imobiliária se um ID válido for fornecido
    if imobiliaria_id_filtro is not None and imobiliaria_id_filtro > 0:
        query += " AND vi.imobiliaria_id = ?"
        params.append(imobiliaria_id_filtro)

    # Ordena os resultados pela data da marcação (mais recentes primeiro) e depois pelo nome do cliente
    query += " ORDER BY vi.data_marcacao DESC, c.nome ASC"

    conexao = None
    try:
        conexao = conectar_banco()
        # pd.read_sql_query executa a query e retorna os resultados diretamente em um DataFrame
        df_relatorio = pd.read_sql_query(query, conexao, params=tuple(params))
        if df_relatorio.empty:
            logging.info("Nenhuma vistoria improdutiva encontrada para os filtros aplicados.")
        return df_relatorio
    except Exception as e:
        logging.error(f"❌ Erro ao obter dados do relatório de clientes devedores (vistorias improdutivas): {e}", exc_info=True)
        print(f"❌ Erro ao obter dados de vistorias improdutivas (clientes devedores): {e}")
        return pd.DataFrame() # Retorna DataFrame vazio em caso de erro
    finally:
        if conexao:
            conexao.close()


# Bloco principal para execução de testes quando o script é rodado diretamente
if __name__ == '__main__':
    # Tentativa de importar criar_tabelas para inicializar o banco para os testes
    try:
        # Esta importação assume que o script está sendo executado como parte do pacote 'models'
        from models.database import criar_tabelas
    except ImportError:
        # Fallback para execução direta (ex: python engentoria/models/usuario_model.py)
        # Adiciona o diretório pai ao sys.path para permitir a importação de 'models.database'
        print("AVISO: Falha ao importar 'models.database' diretamente no __main__. Tentando importação alternativa...")
        import sys
        import os
        # Obtém o diretório do arquivo atual (ex: .../engentoria/models)
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        # Obtém o diretório pai (ex: .../engentoria)
        project_root_dir = os.path.dirname(current_script_dir)
        # Adiciona o diretório raiz do projeto ao path para encontrar o pacote 'models'
        if project_root_dir not in sys.path:
            sys.path.append(project_root_dir)
        from models.database import criar_tabelas # Agora deve encontrar 'models.database'

    print("\n--- Testando Model Usuário (com foco em Clientes e Vistorias Improdutivas) ---")
    try:
        criar_tabelas() # Garante que a estrutura do banco de dados esteja pronta
        print("Estrutura do banco de dados verificada/criada.")
    except NameError: # Se criar_tabelas não foi importado corretamente
        print("ERRO CRÍTICO: A função criar_tabelas() não está definida. Verifique as importações e o caminho do script.")
        exit() # Encerra o script de teste se não puder criar/verificar tabelas

    # Teste: Cadastrar um cliente para os testes
    print("\n1. Cadastrando cliente de teste...")
    cliente_id_teste = cadastrar_cliente("Cliente Teste Devedor", "devedor@teste.com", "62999998888", saldo_devedor_total=50.0)
    if cliente_id_teste:
        print(f"Cliente de teste cadastrado com ID: {cliente_id_teste}")

        # Teste: Listar todos os clientes
        print("\n2. Listando todos os clientes:")
        clientes_listados = listar_todos_clientes()
        if clientes_listados:
            for cliente in clientes_listados:
                print(f"  -> ID: {cliente['id']}, Nome: {cliente['nome']}, Saldo: R${cliente.get('saldo_devedor_total', 0.0):.2f}")
        else:
            print("  Nenhum cliente encontrado.")

        # Teste: Obter cliente por ID
        print(f"\n3. Obtendo cliente de teste ID {cliente_id_teste}:")
        cliente_obtido = obter_cliente_por_id(cliente_id_teste)
        if cliente_obtido:
            print(f"  -> Dados do cliente: {cliente_obtido}")
        else:
            print("  Cliente de teste não encontrado (inesperado).")
    else:
        print("Falha ao cadastrar cliente de teste. Alguns testes subsequentes podem ser afetados.")

    # Teste: Obter dados de clientes devedores (vistorias improdutivas)
    # Para este teste funcionar completamente, precisaríamos de dados na tabela 'vistorias_improdutivas'.
    # Como este model não cadastra vistorias improdutivas diretamente (isso é feito em agenda_model),
    # vamos apenas chamar a função para verificar se ela executa sem erros.
    print("\n4. Obtendo relatório de clientes devedores (vistorias improdutivas não pagas):")
    df_devedores_nao_pagos = obter_dados_clientes_devedores(apenas_nao_pagos=True)
    if not df_devedores_nao_pagos.empty:
        print("Clientes com Cobranças de Improdutividade Não Pagas Encontrados:")
        # .to_string() é usado para exibir o DataFrame completo no console
        print(df_devedores_nao_pagos.to_string())
    else:
        print("Nenhum cliente com cobranças de improdutividade não pagas encontrado (ou tabela vazia).")

    # Teste de deleção de cliente (se um cliente foi cadastrado)
    if cliente_id_teste:
        print(f"\n5. Tentando deletar o cliente de teste ID {cliente_id_teste}:")
        # Para testar o CASCADE, seria preciso cadastrar imóveis e vistorias improdutivas para este cliente.
        # Por simplicidade, apenas testamos a deleção do cliente.
        sucesso_delecao_cliente = deletar_cliente_por_id(cliente_id_teste)
        if sucesso_delecao_cliente:
            print(f"  Cliente ID {cliente_id_teste} deletado com sucesso.")
            cliente_apos_delecao = obter_cliente_por_id(cliente_id_teste)
            if not cliente_apos_delecao:
                print("  Verificação: Cliente não encontrado após deleção, como esperado.")
            else:
                print("  AVISO: Cliente ainda encontrado após tentativa de deleção.")
        else:
            print(f"  Falha ao deletar cliente ID {cliente_id_teste}.")
    
    print("\n--- Fim dos testes do usuario_model.py ---")
