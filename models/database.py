# engentoria/models/database.py
import sqlite3 # Biblioteca para interagir com bancos de dados SQLite
import hashlib # Biblioteca para criar hashes (usado para senhas)
import os # Biblioteca para interagir com o sistema operacional (ex: caminhos de arquivo)

# Nome do arquivo do banco de dados
DB_NAME = "engentoria.db"
# Diretório base do projeto (assume-se que a pasta 'models' está um nível abaixo da raiz 'engentoria')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Caminho completo para o arquivo do banco de dados
DB_PATH = os.path.join(BASE_DIR, DB_NAME)


def conectar_banco() -> sqlite3.Connection:
    """
    Estabelece e retorna uma conexão com o banco de dados SQLite.

    O arquivo do banco de dados (`engentoria.db`) será localizado no diretório
    raiz do projeto. Se o arquivo não existir, o SQLite o criará automaticamente
    na primeira conexão.

    Returns:
        sqlite3.Connection: Objeto de conexão com o banco de dados.
    """
    # sqlite3.connect() abre uma conexão com o arquivo SQLite especificado por DB_PATH.
    # Se o arquivo não existir, ele será criado.
    return sqlite3.connect(DB_PATH)

def hash_senha(senha: str) -> str:
    """
    Gera um hash SHA-256 para uma senha fornecida.

    Args:
        senha (str): A senha em texto plano a ser criptografada.

    Returns:
        str: A representação hexadecimal do hash SHA-256 da senha.
    """
    # A senha é primeiro codificada para UTF-8 (bytes).
    # hashlib.sha256() cria um objeto hash SHA-256.
    # .hexdigest() retorna a string hexadecimal do hash.
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

def _table_has_column(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    """
    Verifica se uma tabela específica no banco de dados possui uma determinada coluna.
    Função auxiliar interna (prefixo '_').

    Args:
        cursor (sqlite3.Cursor): O cursor da conexão com o banco de dados.
        table_name (str): O nome da tabela a ser verificada.
        column_name (str): O nome da coluna a ser procurada.

    Returns:
        bool: True se a coluna existir na tabela, False caso contrário.
    """
    # PRAGMA table_info(nome_da_tabela) retorna metadados sobre as colunas da tabela.
    cursor.execute(f"PRAGMA table_info({table_name})")
    # Extrai os nomes das colunas (o segundo elemento, índice 1, de cada tupla retornada).
    columns = [info[1] for info in cursor.fetchall()]
    # Verifica se a `column_name` está na lista de colunas encontradas.
    return column_name in columns

def criar_tabelas():
    """
    Cria todas as tabelas necessárias para o sistema no banco de dados SQLite,
    se elas ainda não existirem. Também tenta adicionar colunas que possam
    estar faltando em tabelas existentes (migrações simples).

    As tabelas criadas são:
    - usuarios: Armazena dados de administradores e vistoriadores.
    - clientes: Armazena dados de clientes.
    - imobiliarias: Armazena dados de imobiliárias e seus valores base.
    - imoveis: Armazena dados dos imóveis, associados a clientes e imobiliárias.
    - agenda: Gerencia os horários de vistoria, associados a vistoriadores e imóveis.
    - horarios_fixos: Define os horários de trabalho padrão dos vistoriadores.
    - horarios_fechados: Registra horários específicos que foram manualmente fechados.
    - vistorias_improdutivas: Registra vistorias que não puderam ser realizadas e geraram cobrança.

    A função ativa o suporte a chaves estrangeiras (FOREIGN KEYS) para garantir
    a integridade referencial entre as tabelas.
    """
    conexao = conectar_banco() # Obtém uma conexão com o banco
    cursor = conexao.cursor() # Cria um cursor para executar comandos SQL
    
    # Habilita o suporte a chaves estrangeiras para esta conexão.
    # É importante para manter a integridade dos dados (ex: não permitir
    # um imovel_id na agenda que não exista na tabela imoveis).
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Tabela de Usuários (para administradores e vistoriadores)
    # - id: Chave primária autoincrementável.
    # - nome: Nome do usuário.
    # - email: E-mail do usuário, deve ser único (usado para login).
    # - telefone1, telefone2: Contatos telefônicos opcionais.
    # - tipo: Define se o usuário é 'adm' (administrador) ou 'vistoriador'.
    # - senha: Senha criptografada do usuário.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        telefone1 TEXT,
        telefone2 TEXT,
        tipo TEXT NOT NULL CHECK(tipo IN ('adm', 'vistoriador')),
        senha TEXT NOT NULL
    );
    """)

    # Tabela de Clientes
    # - id: Chave primária.
    # - nome, email: Informações básicas do cliente.
    # - telefone1, telefone2: Contatos opcionais.
    # - saldo_devedor_total: Acumula valores devidos pelo cliente (ex: por vistorias improdutivas).
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL,
        telefone1 TEXT,
        telefone2 TEXT,
        saldo_devedor_total REAL DEFAULT 0.0
    );
    """)

    # Tabela de Imobiliárias
    # - id: Chave primária.
    # - nome: Nome da imobiliária, deve ser único.
    # - valor_sem_mobilia, valor_semi_mobiliado, valor_mobiliado: Valores base por m²
    #   usados para calcular o custo da vistoria de um imóvel associado a esta imobiliária.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS imobiliarias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        valor_sem_mobilia REAL NOT NULL DEFAULT 0.0,
        valor_semi_mobiliado REAL NOT NULL DEFAULT 0.0,
        valor_mobiliado REAL NOT NULL DEFAULT 0.0
    );
    """)

    # Tabela de Imóveis
    # - id: Chave primária.
    # - cod_imovel: Código de identificação do imóvel (pode ser um código da imobiliária).
    # - cliente_id: Chave estrangeira para a tabela 'clientes'. ON DELETE CASCADE significa
    #   que se um cliente for deletado, todos os seus imóveis também serão.
    # - imobiliaria_id: Chave estrangeira para 'imobiliarias'. ON DELETE RESTRICT impede
    #   que uma imobiliária seja deletada se houver imóveis associados a ela.
    # - endereco, cep, referencia: Detalhes de localização.
    # - tamanho: Tamanho do imóvel em m².
    # - mobiliado: Estado de mobília ('sem_mobilia', 'semi_mobiliado', 'mobiliado').
    # - valor: Valor base da vistoria para este imóvel, calculado com base no tamanho,
    #   tipo de mobília e valores da imobiliária associada.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS imoveis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cod_imovel TEXT NOT NULL,
        cliente_id INTEGER NOT NULL,
        imobiliaria_id INTEGER NOT NULL,
        endereco TEXT NOT NULL,
        cep TEXT,
        referencia TEXT,
        tamanho REAL NOT NULL DEFAULT 0.0,
        mobiliado TEXT DEFAULT 'sem_mobilia' CHECK(mobiliado IN ('sem_mobilia', 'semi_mobiliado', 'mobiliado')),
        valor REAL NOT NULL DEFAULT 0.0,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
        FOREIGN KEY (imobiliaria_id) REFERENCES imobiliarias(id) ON DELETE RESTRICT
    );
    """)
    # Verificação e adição da coluna 'cod_imovel' se ela não existir (para compatibilidade com esquemas antigos)
    if not _table_has_column(cursor, "imoveis", "cod_imovel"):
        print("INFO: Adicionando coluna 'cod_imovel' à tabela 'imoveis' (tentativa)...")
        try:
            # Adiciona a coluna. Não se preocupa com NOT NULL ou UNIQUE aqui para evitar falhas
            # em bancos já existentes com dados. Idealmente, migrações mais robustas seriam usadas.
            cursor.execute("ALTER TABLE imoveis ADD COLUMN cod_imovel TEXT")
            print("INFO: Coluna 'cod_imovel' adicionada. Considere adicionar um índice UNIQUE se necessário e se não existir.")
        except sqlite3.OperationalError as e:
            # Pode falhar se a coluna já existir (apesar da verificação) ou outro erro.
            print(f"AVISO: Não foi possível adicionar 'cod_imovel' a 'imoveis' (pode já existir ou outro erro): {e}")


    # Tabela da Agenda
    # - id: Chave primária.
    # - imovel_id: Chave estrangeira para 'imoveis'. ON DELETE SET NULL define imovel_id como NULL
    #   se o imóvel associado for deletado (o horário na agenda permanece, mas sem imóvel).
    # - vistoriador_id: Chave estrangeira para 'usuarios'. ON DELETE CASCADE deleta entradas da agenda
    #   se o vistoriador associado for removido.
    # - data, horario: Data e hora da vistoria/disponibilidade.
    # - disponivel: Booleano indicando se o horário está livre (1) ou ocupado (0).
    # - tipo: Estado do horário ('LIVRE', 'ENTRADA', 'SAIDA', 'CONFERENCIA', 'FECHADO', 'IMPRODUTIVA').
    # - UNIQUE (vistoriador_id, data, horario): Garante que um vistoriador não pode ter
    #   duas entradas na agenda para o mesmo dia e horário.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agenda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        imovel_id INTEGER,
        vistoriador_id INTEGER NOT NULL,
        data DATE NOT NULL,
        horario TEXT NOT NULL,
        disponivel BOOLEAN DEFAULT 1,
        tipo TEXT DEFAULT 'LIVRE' CHECK(tipo IN ('ENTRADA', 'SAIDA', 'CONFERENCIA', 'FECHADO', 'LIVRE', 'IMPRODUTIVA')),
        UNIQUE (vistoriador_id, data, horario),
        FOREIGN KEY (imovel_id) REFERENCES imoveis(id) ON DELETE SET NULL,
        FOREIGN KEY (vistoriador_id) REFERENCES usuarios(id) ON DELETE CASCADE
    );
    """)
    # Verificação e adição da coluna 'tipo' na tabela 'agenda' (migração simples)
    if not _table_has_column(cursor, "agenda", "tipo"):
        print("INFO: Adicionando coluna 'tipo' à tabela 'agenda'...")
        try:
            cursor.execute("ALTER TABLE agenda ADD COLUMN tipo TEXT DEFAULT 'LIVRE' NOT NULL CHECK(tipo IN ('ENTRADA', 'SAIDA', 'CONFERENCIA', 'FECHADO', 'LIVRE', 'IMPRODUTIVA'))")
        except sqlite3.OperationalError as e:
             print(f"AVISO: Não foi possível adicionar 'tipo' a 'agenda' (pode já existir ou outro erro): {e}")


    # Tabela de Horários Fixos de Trabalho dos Vistoriadores
    # - id: Chave primária.
    # - vistoriador_id: Chave estrangeira para 'usuarios'.
    # - dia_semana: Representação numérica do dia da semana (ex: '0' para Domingo, ..., '6' para Sábado).
    #   A convenção exata (0=Dom ou 0=Seg) depende de como é usada com `datetime.weekday()` ou `isoweekday()`.
    # - horario: Horário fixo de trabalho (ex: "09:00").
    # - UNIQUE (vistoriador_id, dia_semana, horario): Garante que um vistoriador não tenha
    #   o mesmo horário fixo duplicado para o mesmo dia da semana.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS horarios_fixos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vistoriador_id INTEGER NOT NULL,
        dia_semana TEXT NOT NULL CHECK(dia_semana IN ('0','1','2','3','4','5','6')),
        horario TEXT NOT NULL,
        UNIQUE (vistoriador_id, dia_semana, horario),
        FOREIGN KEY (vistoriador_id) REFERENCES usuarios(id) ON DELETE CASCADE
    );
    """)

    # Tabela de Horários Fechados Manualmente
    # - id: Chave primária.
    # - agenda_id: Chave estrangeira para 'agenda', deve ser única (um horário na agenda só pode
    #   ser fechado uma vez com um motivo). ON DELETE CASCADE remove o registro de fechamento
    #   se a entrada correspondente na agenda for deletada.
    # - motivo: Justificativa para o fechamento do horário.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS horarios_fechados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agenda_id INTEGER UNIQUE NOT NULL,
        motivo TEXT,
        FOREIGN KEY (agenda_id) REFERENCES agenda(id) ON DELETE CASCADE
    );
    """)

    # Tabela de Vistorias Improdutivas
    # Registra informações sobre vistorias que foram agendadas mas não ocorreram,
    # gerando possível cobrança para o cliente e remuneração para o vistoriador.
    # - id: Chave primária.
    # - agenda_id_original: ID da entrada na tabela 'agenda' que era a vistoria original.
    #   ON DELETE RESTRICT impede que a entrada original na agenda seja deletada enquanto
    #   houver um registro de vistoria improdutiva associado (importante para histórico e auditoria).
    # - cliente_id: Cliente responsável. ON DELETE CASCADE (se o cliente for deletado, as improdutivas dele também são).
    # - imovel_id, imobiliaria_id: IDs opcionais do imóvel e imobiliária. ON DELETE SET NULL.
    # - data_marcacao: Data em que a vistoria foi marcada como improdutiva.
    # - data_vistoria_original, horario_vistoria_original: Data/hora da vistoria que não ocorreu.
    # - motivo_improdutividade: Causa da improdutividade.
    # - valor_cobranca: Valor cobrado do cliente.
    # - valor_para_vistoriador: Valor a ser pago ao vistoriador pela disponibilidade/deslocamento.
    # - pago: Booleano indicando se a cobrança foi paga pelo cliente.
    # - data_pagamento: Data do pagamento, se ocorrido.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vistorias_improdutivas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agenda_id_original INTEGER NOT NULL, 
        cliente_id INTEGER NOT NULL,
        imovel_id INTEGER,
        imobiliaria_id INTEGER,
        data_marcacao DATE NOT NULL,
        data_vistoria_original DATE NOT NULL,
        horario_vistoria_original TEXT NOT NULL,
        motivo_improdutividade TEXT NOT NULL,
        valor_cobranca REAL NOT NULL,
        valor_para_vistoriador REAL,
        pago BOOLEAN DEFAULT 0,
        data_pagamento DATE,
        FOREIGN KEY (agenda_id_original) REFERENCES agenda(id) ON DELETE RESTRICT, -- Mantido RESTRICT
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
        FOREIGN KEY (imovel_id) REFERENCES imoveis(id) ON DELETE SET NULL,
        FOREIGN KEY (imobiliaria_id) REFERENCES imobiliarias(id) ON DELETE SET NULL
    );
    """)
    # Verificação e adição da coluna 'valor_para_vistoriador' (migração simples)
    if not _table_has_column(cursor, "vistorias_improdutivas", "valor_para_vistoriador"):
        print("INFO: Adicionando coluna 'valor_para_vistoriador' à tabela 'vistorias_improdutivas'...")
        try:
            cursor.execute("ALTER TABLE vistorias_improdutivas ADD COLUMN valor_para_vistoriador REAL")
            print("INFO: Coluna 'valor_para_vistoriador' adicionada.")
        except sqlite3.OperationalError as e:
            print(f"AVISO: Não foi possível adicionar 'valor_para_vistoriador' (pode já existir ou outro erro): {e}")

    # Salva todas as alterações no banco de dados
    conexao.commit()
    # Fecha a conexão
    conexao.close()
    print("Tabelas verificadas/criadas/atualizadas com sucesso.")

# Bloco executado se o script `database.py` for rodado diretamente.
# Útil para inicializar o banco de dados pela primeira vez ou verificar sua criação.
if __name__ == '__main__':
    print(f"Tentando criar/verificar o banco de dados em: {DB_PATH}")
    # Verifica se o arquivo do banco de dados já existe no caminho esperado.
    if os.path.exists(DB_PATH):
        print(f"O arquivo de banco de dados '{DB_NAME}' já existe em: {BASE_DIR}")
    else:
        print(f"O arquivo de banco de dados '{DB_NAME}' não existe em {BASE_DIR}, será criado.")
    
    # Chama a função principal para criar/verificar as tabelas.
    criar_tabelas()
    print(f"Processo de criação/verificação de tabelas concluído. Verifique o arquivo '{DB_NAME}' em: {BASE_DIR}")

