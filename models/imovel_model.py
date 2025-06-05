# engentoria/models/imovel_model.py
import sqlite3 # Biblioteca para interagir com bancos de dados SQLite
from .database import conectar_banco # Função para conectar ao banco de dados (do mesmo pacote)
from .imobiliaria_model import obter_imobiliaria_por_id # Função para buscar dados da imobiliária associada
from typing import Optional, List, Dict, Any, Tuple # Tipos para anotações estáticas
import logging # Biblioteca para logging de eventos e erros

# Configuração básica do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def deletar_imovel_por_id(imovel_id: int, conexao_existente: Optional[sqlite3.Connection] = None) -> bool:
    """
    Deleta um imóvel específico do banco de dados utilizando o seu ID.

    Esta função permite o reuso de uma conexão SQLite existente, o que é útil
    para operações que fazem parte de uma transação maior ou para otimizar
    múltiplas chamadas ao banco.

    A tabela 'agenda' tem uma chave estrangeira 'imovel_id' com `ON DELETE SET NULL`.
    Isso significa que, ao deletar um imóvel, qualquer entrada na agenda que
    se referia a este imóvel terá seu `imovel_id` automaticamente definido como NULL.
    Da mesma forma, a tabela 'vistorias_improdutivas' tem `ON DELETE SET NULL` para `imovel_id`.

    Args:
        imovel_id (int): O ID do imóvel a ser deletado.
        conexao_existente (Optional[sqlite3.Connection]): Uma conexão SQLite existente.
                                                           Se None, uma nova conexão será criada e gerenciada internamente.

    Returns:
        bool: True se o imóvel foi deletado com sucesso (ou seja, pelo menos uma linha foi afetada).
              False se o imóvel não foi encontrado para deleção ou se ocorreu um erro.
    """
    conexao_interna = False # Flag para controlar se a conexão foi criada nesta função
    if conexao_existente is None:
        conexao = conectar_banco() # Cria nova conexão se nenhuma foi passada
        conexao_interna = True
    else:
        conexao = conexao_existente # Usa a conexão existente
    
    try:
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;") # Assegura que as restrições de FK sejam aplicadas

        # Executa o comando DELETE para remover o imóvel com o ID fornecido
        cursor.execute("DELETE FROM imoveis WHERE id = ?", (imovel_id,))
        
        if conexao_interna: # Só faz commit se a conexão foi criada e gerenciada aqui
            conexao.commit()

        if cursor.rowcount > 0: # Verifica se alguma linha foi afetada (ou seja, deletada)
            logging.info(f"✅ Imóvel ID {imovel_id} deletado com sucesso.")
            return True
        else:
            logging.info(f"ℹ️ Imóvel ID {imovel_id} não encontrado para deleção.")
            return False # Nenhuma linha afetada, imóvel não existia
    except sqlite3.IntegrityError as e:
        # Este erro ocorreria se houvesse uma FK para 'imoveis' com ON DELETE RESTRICT
        # em outra tabela que não foi prevista. No esquema atual, isso não deve acontecer
        # para as tabelas `agenda` e `vistorias_improdutivas` devido ao SET NULL.
        logging.error(f"❌ Erro de integridade ao deletar imóvel ID {imovel_id}: {e}")
        if conexao_interna and conexao:
            conexao.rollback()
        return False
    except Exception as e:
        logging.error(f"❌ Erro inesperado ao deletar imóvel ID {imovel_id}: {e}", exc_info=True)
        if conexao_interna and conexao:
            conexao.rollback()
        return False
    finally:
        if conexao_interna and conexao: # Fecha a conexão apenas se foi criada aqui
            conexao.close()


def deletar_imoveis_orfaos() -> int:
    """
    Identifica e deleta imóveis que não estão referenciados em nenhuma entrada
    da tabela 'agenda' (onde `agenda.imovel_id` seria igual a `imoveis.id`).

    Esta função é útil para limpeza de dados, removendo imóveis que podem
    ter sido cadastrados mas nunca agendados, ou cujos agendamentos foram
    posteriormente desvinculados (embora a lógica de desvinculação não seja
    explícita no esquema atual, `ON DELETE SET NULL` na agenda poderia criar órfãos
    se a entrada da agenda fosse deletada de outra forma que não pelo imóvel).

    Utiliza a função `deletar_imovel_por_id` para cada imóvel órfão encontrado,
    reutilizando a mesma conexão para otimizar o processo.

    Returns:
        int: O número de imóveis órfãos que foram deletados com sucesso.
    """
    deletados_count = 0 # Contador para imóveis deletados
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Query para encontrar IDs de imóveis que NÃO existem na coluna 'imovel_id' da tabela 'agenda'.
        # `DISTINCT imovel_id` é usado para otimizar o subselect.
        # `WHERE imovel_id IS NOT NULL` na subquery é importante para não considerar
        # entradas na agenda que já não têm imóvel associado como "protegendo" um imóvel.
        cursor.execute("""
            SELECT id FROM imoveis
            WHERE id NOT IN (SELECT DISTINCT imovel_id FROM agenda WHERE imovel_id IS NOT NULL)
        """)
        imoveis_orfaos_ids = [row[0] for row in cursor.fetchall()] # Lista de IDs dos imóveis órfãos

        if not imoveis_orfaos_ids:
            logging.info("Nenhum imóvel órfão encontrado para deletar.")
            return 0

        logging.info(f"Encontrados {len(imoveis_orfaos_ids)} imóveis órfãos para deletar: {imoveis_orfaos_ids}")

        # Itera sobre cada ID de imóvel órfão e tenta deletá-lo
        for imovel_id in imoveis_orfaos_ids:
            if deletar_imovel_por_id(imovel_id, conexao_existente=conexao): # Reusa a conexão
                deletados_count += 1
        
        if deletados_count > 0:
            conexao.commit() # Commita todas as deleções de uma vez
        
        logging.info(f"Total de {deletados_count} imóveis órfãos deletados.")

    except Exception as e:
        logging.error(f"Erro ao deletar imóveis órfãos: {e}", exc_info=True)
        if conexao:
            conexao.rollback()
    finally:
        if conexao:
            conexao.close()
    return deletados_count

def atualizar_estrutura_banco():
    """
    Verifica a estrutura das tabelas 'imoveis' e 'agenda' e tenta adicionar
    colunas que possam estar faltando, como 'cod_imovel' em 'imoveis' e 'tipo' em 'agenda'.

    Esta é uma forma simples de "migração" de esquema, útil durante o desenvolvimento
    para garantir que o banco de dados tenha as colunas esperadas.
    Em ambientes de produção, ferramentas de migração mais robustas (como Alembic)
    são geralmente preferidas.

    A função não lida com a criação de índices UNIQUE se eles não existirem,
    assumindo que a definição inicial da tabela já os inclui ou que seria
    uma correção manual.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        
        # --- Atualizar estrutura da tabela 'imoveis' ---
        cursor.execute("PRAGMA table_info(imoveis)") # Obtém informações das colunas da tabela
        colunas_imoveis = [info[1] for info in cursor.fetchall()] # Extrai apenas os nomes das colunas
        
        # Verifica se a coluna 'cod_imovel' existe
        if 'cod_imovel' not in colunas_imoveis:
            logging.info("Adicionando coluna 'cod_imovel' à tabela 'imoveis'...")
            cursor.execute("ALTER TABLE imoveis ADD COLUMN cod_imovel TEXT") # Adiciona a coluna
            conexao.commit() # Salva a alteração
            logging.info("Coluna 'cod_imovel' adicionada/verificada.")
        # Comentário sobre índice UNIQUE:
        # A adição de um índice UNIQUE em uma coluna existente com dados duplicados falharia.
        # A lógica para verificar e criar índices UNIQUE (ex: CREATE UNIQUE INDEX IF NOT EXISTS)
        # é mais complexa e omitida aqui por simplicidade, mas seria importante em um sistema real.

        # --- Atualizar estrutura da tabela 'agenda' ---
        cursor.execute("PRAGMA table_info(agenda)")
        colunas_agenda = [info[1] for info in cursor.fetchall()]

        # Verifica se a coluna 'tipo' existe
        if 'tipo' not in colunas_agenda:
            logging.info("Adicionando coluna 'tipo' à tabela 'agenda'...")
            # Adiciona a coluna com valor padrão e constraint CHECK
            cursor.execute("ALTER TABLE agenda ADD COLUMN tipo TEXT DEFAULT 'LIVRE' NOT NULL CHECK(tipo IN ('ENTRADA', 'SAIDA', 'CONFERENCIA', 'FECHADO', 'LIVRE', 'IMPRODUTIVA'))")
            conexao.commit()
            logging.info("Coluna 'tipo' adicionada/verificada na tabela 'agenda'.")

    except sqlite3.OperationalError as e:
        # Este erro pode ocorrer se a coluna já existe (apesar da verificação),
        # ou se houver um problema com o comando ALTER TABLE.
        logging.warning(f"Possível erro operacional ao atualizar estrutura do banco (pode ser normal se coluna já existe): {e}")
    except Exception as e:
        logging.error(f"ERRO: Erro inesperado ao atualizar estrutura do banco: {e}", exc_info=True)
    finally:
        if conexao:
            conexao.close()


def cadastrar_imovel(cod_imovel: str, cliente_id: int, imobiliaria_id: int,
                     endereco: str, tamanho: float,
                     cep: Optional[str] = None, referencia: Optional[str] = None,
                     mobiliado: str = 'sem_mobilia') -> Optional[int]:
    """
    Cadastra um novo imóvel no banco de dados.

    Calcula automaticamente o 'valor' da vistoria para o imóvel com base no seu tamanho,
    estado de mobília e nos valores por m² definidos na imobiliária associada.

    Args:
        cod_imovel (str): Código de identificação do imóvel (ex: da imobiliária).
        cliente_id (int): ID do cliente proprietário ou responsável pelo imóvel.
        imobiliaria_id (int): ID da imobiliária associada ao imóvel.
        endereco (str): Endereço completo do imóvel.
        tamanho (float): Tamanho do imóvel em metros quadrados (m²).
        cep (Optional[str]): CEP do imóvel.
        referencia (Optional[str]): Ponto de referência ou complemento do endereço.
        mobiliado (str): Estado de mobília. Valores permitidos: 'sem_mobilia' (padrão),
                         'semi_mobiliado', 'mobiliado'.

    Returns:
        Optional[int]: O ID do imóvel recém-cadastrado em caso de sucesso.
                       Retorna None se o cadastro falhar (ex: campos obrigatórios faltando,
                       imobiliária não encontrada, tipo de mobília inválido, erro de integridade).
    """
    # Validação de campos obrigatórios e tipo de dados
    if not all([cod_imovel, cliente_id, imobiliaria_id, endereco, isinstance(tamanho, (int, float))]):
        logging.warning("Campos obrigatórios (cod_imovel, cliente_id, imobiliaria_id, endereco, tamanho) devem ser preenchidos para cadastrar imóvel.")
        return None
    if tamanho <= 0:
        logging.warning("O tamanho do imóvel deve ser um valor positivo.")
        return None
    if mobiliado not in ['sem_mobilia', 'semi_mobiliado', 'mobiliado']:
        logging.warning(f"Tipo de mobília inválido: '{mobiliado}'. Use 'sem_mobilia', 'semi_mobiliado' ou 'mobiliado'.")
        return None

    # Busca dados da imobiliária para obter os valores por m²
    imobiliaria_data = obter_imobiliaria_por_id(imobiliaria_id)
    if not imobiliaria_data:
        logging.warning(f"Imobiliária com ID {imobiliaria_id} não encontrada para cadastro de imóvel.")
        return None

    # Determina o valor/m² com base no estado de mobília
    valor_m2_aplicavel = 0.0
    if mobiliado == 'sem_mobilia':
        valor_m2_aplicavel = imobiliaria_data['valor_sem_mobilia']
    elif mobiliado == 'semi_mobiliado':
        valor_m2_aplicavel = imobiliaria_data['valor_semi_mobiliado']
    elif mobiliado == 'mobiliado':
        valor_m2_aplicavel = imobiliaria_data['valor_mobiliado']

    # Calcula o valor base da vistoria para este imóvel (para a Engentoria)
    valor_calculado_vistoria_base = round(valor_m2_aplicavel * tamanho, 2)

    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Insere o novo imóvel na tabela 'imoveis'
        cursor.execute("""
            INSERT INTO imoveis (cod_imovel, cliente_id, imobiliaria_id, endereco, cep, referencia, tamanho, mobiliado, valor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cod_imovel, cliente_id, imobiliaria_id, endereco, cep, referencia, tamanho, mobiliado, valor_calculado_vistoria_base))
        conexao.commit()
        imovel_id = cursor.lastrowid # ID do imóvel inserido
        logging.info(f"✅ Imóvel '{cod_imovel}' cadastrado com sucesso! ID: {imovel_id}, Valor Vistoria (Base Engentoria): R${valor_calculado_vistoria_base:.2f}")
        return imovel_id
    except sqlite3.IntegrityError as e:
        # Verifica se o erro é devido à constraint UNIQUE no 'cod_imovel'
        # (A tabela 'imoveis' deveria ter UNIQUE(cod_imovel, imobiliaria_id) ou similar para ser mais robusto)
        # Assumindo que a falha é por 'cod_imovel' globalmente único ou dentro da mesma imobiliária.
        if "UNIQUE constraint failed: imoveis.cod_imovel" in str(e): # Ajustar se a constraint for diferente
            logging.warning(f"Erro: O código de imóvel '{cod_imovel}' já está cadastrado (possivelmente para esta imobiliária).")
        else:
            # Outro erro de integridade, como cliente_id ou imobiliaria_id não existentes.
            logging.warning(f"Erro de integridade ao cadastrar imóvel '{cod_imovel}': {e}")
        return None
    except Exception as e:
        logging.error(f"Erro inesperado ao cadastrar imóvel '{cod_imovel}': {e}", exc_info=True)
        return None
    finally:
        if conexao:
            conexao.close()

def listar_imoveis_por_cliente(cliente_id: int) -> List[Dict[str, Any]]:
    """
    Lista todos os imóveis associados a um cliente específico.

    Args:
        cliente_id (int): ID do cliente.

    Returns:
        List[Dict[str, Any]]: Lista de dicionários, cada um representando um imóvel do cliente.
                               Retorna lista vazia se o cliente não tiver imóveis ou em caso de erro.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Seleciona os imóveis filtrando por cliente_id
        cursor.execute("""
            SELECT id, cod_imovel, endereco, tamanho, mobiliado, valor, imobiliaria_id
            FROM imoveis
            WHERE cliente_id = ?
            ORDER BY cod_imovel ASC /* Ordena pelo código do imóvel */
        """, (cliente_id,))
        imoveis_db = cursor.fetchall()
        # Converte o resultado em lista de dicionários
        lista_imoveis = [
            {
                'id': row[0], 'cod_imovel': row[1], 'endereco': row[2],
                'tamanho': row[3], 'mobiliado': row[4], 'valor': row[5], # 'valor' é o valor base da vistoria Engentoria
                'imobiliaria_id': row[6]
            }
            for row in imoveis_db
        ]
        return lista_imoveis
    except Exception as e:
        logging.error(f"Erro ao listar imóveis do cliente ID {cliente_id}: {e}", exc_info=True)
        return []
    finally:
        if conexao:
            conexao.close()

def listar_todos_imoveis() -> List[Dict[str, Any]]:
    """
    Lista todos os imóveis cadastrados no sistema, juntando informações
    do cliente e da imobiliária associados.

    Returns:
        List[Dict[str, Any]]: Lista de dicionários, cada um representando um imóvel
                               com dados do cliente e da imobiliária.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Query que faz JOIN com as tabelas 'clientes' e 'imobiliarias'
        cursor.execute("""
            SELECT i.id, i.cod_imovel, i.endereco, i.tamanho, i.mobiliado, i.valor,
                   c.nome as cliente_nome, imob.nome as imobiliaria_nome, 
                   i.cliente_id, i.imobiliaria_id
            FROM imoveis i
            JOIN clientes c ON i.cliente_id = c.id
            JOIN imobiliarias imob ON i.imobiliaria_id = imob.id
            ORDER BY i.cod_imovel ASC
        """)
        imoveis_db = cursor.fetchall()
        lista_imoveis = [
            {
                'id': row[0], 'cod_imovel': row[1], 'endereco': row[2],
                'tamanho': row[3], 'mobiliado': row[4], 'valor': row[5],
                'cliente_nome': row[6], 'imobiliaria_nome': row[7],
                'cliente_id': row[8], 'imobiliaria_id': row[9]
            }
            for row in imoveis_db
        ]
        return lista_imoveis
    except Exception as e:
        logging.error(f"Erro ao listar todos os imóveis: {e}", exc_info=True)
        return []
    finally:
        if conexao:
            conexao.close()

def obter_imovel_por_id(imovel_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca e retorna os dados de um imóvel específico pelo seu ID.

    Args:
        imovel_id (int): O ID do imóvel a ser pesquisado.

    Returns:
        Optional[Dict[str, Any]]: Dicionário com os dados do imóvel se encontrado, None caso contrário.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("""
            SELECT id, cod_imovel, cliente_id, imobiliaria_id, endereco, cep,
                   referencia, tamanho, mobiliado, valor
            FROM imoveis
            WHERE id = ?
        """, (imovel_id,))
        imovel_db = cursor.fetchone()
        if imovel_db:
            return {
                'id': imovel_db[0], 'cod_imovel': imovel_db[1], 'cliente_id': imovel_db[2],
                'imobiliaria_id': imovel_db[3], 'endereco': imovel_db[4], 'cep': imovel_db[5],
                'referencia': imovel_db[6], 'tamanho': imovel_db[7], 'mobiliado': imovel_db[8],
                'valor': imovel_db[9] # Valor base da vistoria (Engentoria)
            }
        logging.info(f"Imóvel com ID {imovel_id} não encontrado.")
        return None
    except Exception as e:
        logging.error(f"Erro ao obter imóvel ID {imovel_id}: {e}", exc_info=True)
        return None
    finally:
        if conexao:
            conexao.close()

def obter_imovel_por_codigo(cod_imovel: str) -> Optional[Dict[str, Any]]:
    """
    Busca e retorna os dados de um imóvel específico pelo seu código de imóvel.
    Assume-se que `cod_imovel` pode não ser globalmente único, mas esta função
    retornará o primeiro encontrado. Para unicidade, idealmente a busca seria
    `cod_imovel` + `imobiliaria_id`.

    Args:
        cod_imovel (str): O código do imóvel.

    Returns:
        Optional[Dict[str, Any]]: Dicionário com os dados do imóvel se encontrado, None caso contrário.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("""
            SELECT id, cod_imovel, cliente_id, imobiliaria_id, endereco, cep,
                   referencia, tamanho, mobiliado, valor
            FROM imoveis
            WHERE cod_imovel = ? 
        """, (cod_imovel,)) # Adicionar `AND imobiliaria_id = ?` se necessário para unicidade
        imovel_db = cursor.fetchone()
        if imovel_db:
            return {
                'id': imovel_db[0], 'cod_imovel': imovel_db[1], 'cliente_id': imovel_db[2],
                'imobiliaria_id': imovel_db[3], 'endereco': imovel_db[4], 'cep': imovel_db[5],
                'referencia': imovel_db[6], 'tamanho': imovel_db[7], 'mobiliado': imovel_db[8],
                'valor': imovel_db[9]
            }
        logging.info(f"Imóvel com código '{cod_imovel}' não encontrado.")
        return None
    except Exception as e:
        logging.error(f"Erro ao obter imóvel pelo código '{cod_imovel}': {e}", exc_info=True)
        return None
    finally:
        if conexao:
            conexao.close()

def atualizar_imovel(imovel_id: int, **kwargs) -> bool:
    """
    Atualiza os dados de um imóvel existente.

    Permite a atualização de campos específicos passados através de `kwargs`.
    Se 'tamanho', 'mobiliado' ou 'imobiliaria_id' forem alterados, o campo 'valor'
    (valor base da vistoria para a Engentoria) é recalculado automaticamente.

    Args:
        imovel_id (int): ID do imóvel a ser atualizado.
        **kwargs: Argumentos nomeados representando os campos do imóvel a serem
                  atualizados e seus novos valores (ex: endereco="Nova Rua", tamanho=75.0).
                  Campos válidos: 'cod_imovel', 'cliente_id', 'imobiliaria_id', 'endereco',
                                 'cep', 'referencia', 'tamanho', 'mobiliado'.
                                 O campo 'valor' não deve ser passado diretamente se um dos
                                 campos que o afetam for alterado, pois será recalculado.

    Returns:
        bool: True se a atualização for bem-sucedida, False caso contrário.
    """
    # Obtém os dados atuais do imóvel para comparação e para ter os valores
    # caso nem todos os campos sejam fornecidos em kwargs.
    imovel_atual = obter_imovel_por_id(imovel_id)
    if not imovel_atual: # Imóvel não encontrado
        return False

    # Listas para construir a query SQL de atualização dinamicamente
    campos_para_atualizar_sql = [] # Ex: ["endereco = ?", "tamanho = ?"]
    valores_para_query = []     # Ex: ["Nova Rua", 75.0]
    
    # Flags e variáveis para recalcular o valor da vistoria se necessário
    recalcular_valor_base = False
    # Inicializa com os valores atuais do imóvel; serão atualizados se fornecidos em kwargs
    novo_tamanho = float(imovel_atual['tamanho'])
    nova_mobilia_status = imovel_atual['mobiliado']
    nova_imobiliaria_id = int(imovel_atual['imobiliaria_id'])

    # Campos permitidos para atualização via kwargs
    valid_fields_for_update = ['cod_imovel', 'cliente_id', 'imobiliaria_id', 'endereco', 'cep', 'referencia', 'tamanho', 'mobiliado']
    
    # Itera sobre os argumentos nomeados fornecidos
    for key, value in kwargs.items():
        if key in valid_fields_for_update:
            # Lógica específica para campos que afetam o 'valor' do imóvel
            if key == 'tamanho':
                try:
                    new_size_val = float(value)
                    if new_size_val <= 0:
                        logging.warning("O tamanho do imóvel para atualização deve ser um valor positivo.")
                        return False
                    if novo_tamanho != new_size_val: # Compara com o valor atual (já convertido para float)
                        recalcular_valor_base = True
                        novo_tamanho = new_size_val
                except ValueError:
                    logging.warning(f"Valor de tamanho inválido para atualização: {value}")
                    return False
            elif key == 'mobiliado':
                if value not in ['sem_mobilia', 'semi_mobiliado', 'mobiliado']:
                    logging.warning(f"Tipo de mobília inválido para atualização: '{value}'.")
                    return False
                if nova_mobilia_status != value:
                    recalcular_valor_base = True
                    nova_mobilia_status = value
            elif key == 'imobiliaria_id':
                try:
                    new_imob_id = int(value)
                    if nova_imobiliaria_id != new_imob_id:
                        recalcular_valor_base = True
                        nova_imobiliaria_id = new_imob_id
                except ValueError:
                    logging.warning(f"ID de imobiliária inválido para atualização: {value}")
                    return False
            
            # Adiciona o campo e o valor às listas para a query SQL
            campos_para_atualizar_sql.append(f"{key} = ?")
            valores_para_query.append(value)

    # Se nenhum campo válido foi fornecido para atualização
    if not campos_para_atualizar_sql:
        logging.info("Nenhum dado válido fornecido para atualização do imóvel ID {imovel_id}.")
        return False # Ou True, se "nenhuma alteração" for considerado sucesso.

    # Se o valor base da vistoria precisa ser recalculado
    if recalcular_valor_base:
        imobiliaria_data_para_recalculo = obter_imobiliaria_por_id(nova_imobiliaria_id)
        if not imobiliaria_data_para_recalculo:
            logging.warning(f"Imobiliária com ID {nova_imobiliaria_id} não encontrada para recálculo de valor do imóvel ID {imovel_id}.")
            return False # Não pode recalcular sem os dados da imobiliária
        
        valor_m2_recalculado = 0.0
        if nova_mobilia_status == 'sem_mobilia':
            valor_m2_recalculado = imobiliaria_data_para_recalculo['valor_sem_mobilia']
        elif nova_mobilia_status == 'semi_mobiliado':
            valor_m2_recalculado = imobiliaria_data_para_recalculo['valor_semi_mobiliado']
        elif nova_mobilia_status == 'mobiliado':
            valor_m2_recalculado = imobiliaria_data_para_recalculo['valor_mobiliado']
        
        novo_valor_base_calculado = round(valor_m2_recalculado * novo_tamanho, 2)
        
        # Verifica se 'valor' já está na lista de campos para ser atualizado (caso tenha sido passado em kwargs)
        # Se sim, atualiza seu valor na lista `valores_para_query`.
        # Se não, adiciona 'valor = ?' e o novo valor calculado.
        found_valor_field_in_sql = False
        for i, field_sql_expr in enumerate(campos_para_atualizar_sql):
            if field_sql_expr.startswith("valor ="):
                valores_para_query[i] = novo_valor_base_calculado # Sobrescreve valor passado em kwargs com o recalculado
                found_valor_field_in_sql = True
                break
        if not found_valor_field_in_sql: # Se 'valor' não foi passado em kwargs, adiciona o recalculado
            campos_para_atualizar_sql.append("valor = ?")
            valores_para_query.append(novo_valor_base_calculado)
        logging.info(f"Valor base da vistoria para imóvel ID {imovel_id} recalculado para: R${novo_valor_base_calculado:.2f}")

    # Constrói a string da cláusula SET (ex: "endereco = ?, tamanho = ?, valor = ?")
    query_set_string = ", ".join(campos_para_atualizar_sql)
    valores_para_query.append(imovel_id) # Adiciona o ID do imóvel para a cláusula WHERE

    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute(f"UPDATE imoveis SET {query_set_string} WHERE id = ?", tuple(valores_para_query))
        conexao.commit()
        if cursor.rowcount > 0:
            logging.info(f"✅ Imóvel ID {imovel_id} atualizado com sucesso.")
            return True
        else:
            # Se rowcount == 0, pode ser que os valores fornecidos sejam idênticos aos já existentes.
            logging.info(f"ℹ️ Nenhum dado foi efetivamente alterado para o imóvel ID {imovel_id} (ou imóvel não encontrado - embora verificado no início).")
            return True # Considera sucesso se os dados eram os mesmos e nenhuma alteração era necessária.
    except sqlite3.IntegrityError as e:
        # Ex: tentar mudar cod_imovel para um que já existe (se houver constraint UNIQUE)
        # ou FKs inválidas (cliente_id, imobiliaria_id não existentes).
        if "UNIQUE constraint failed: imoveis.cod_imovel" in str(e) and 'cod_imovel' in kwargs:
            logging.warning(f"Erro de integridade: O código de imóvel '{kwargs['cod_imovel']}' já está cadastrado.")
        else:
            logging.warning(f"Erro de integridade ao atualizar imóvel ID {imovel_id}: {e}")
        return False
    except Exception as e:
        logging.error(f"Erro inesperado ao atualizar imóvel ID {imovel_id}: {e}", exc_info=True)
        return False
    finally:
        if conexao:
            conexao.close()

def deletar_imovel(imovel_id: int) -> bool:
    """
    Função wrapper para `deletar_imovel_por_id`. 
    Mantida por compatibilidade se era chamada por outras partes do código anteriormente.
    Recomenda-se usar `deletar_imovel_por_id` diretamente se uma conexão existente
    precisar ser gerenciada.
    """
    # Chama a função mais detalhada que gerencia a conexão internamente por padrão.
    return deletar_imovel_por_id(imovel_id, conexao_existente=None)

# --- Funções de Lógica de Negócio (Regras Específicas do Sistema) ---

def regras_necessita_dois_horarios(imovel_id: int, tipo_vistoria: str) -> bool:
    """
    Determina se uma vistoria para um determinado imóvel necessita de dois horários
    na agenda com base no tamanho do imóvel e seu estado de mobília.

    Regras:
    - Vistorias do tipo 'CONFERENCIA' NUNCA necessitam de dois horários.
    - Para 'ENTRADA' ou 'SAIDA':
        - Imóveis com 100m² ou mais necessitam de dois horários.
        - Imóveis 'mobiliado' (totalmente mobiliados) necessitam de dois horários,
          independentemente do tamanho (exceto se for CONFERENCIA).

    Args:
        imovel_id (int): ID do imóvel.
        tipo_vistoria (str): Tipo da vistoria ('ENTRADA', 'SAIDA', 'CONFERENCIA').

    Returns:
        bool: True se dois horários são necessários, False caso contrário.
    """
    # Validação do tipo de vistoria
    if tipo_vistoria not in ['ENTRADA', 'SAIDA', 'CONFERENCIA']:
        logging.warning(f"Tipo de vistoria inválido '{tipo_vistoria}' fornecido para verificar regras de horários.")
        return False # Ou poderia levantar um erro

    # Regra específica para 'CONFERENCIA'
    if tipo_vistoria == "CONFERENCIA":
        return False # Conferências sempre usam um único horário

    # Busca os dados do imóvel para aplicar as regras
    imovel = obter_imovel_por_id(imovel_id)
    if not imovel:
        logging.warning(f"Imóvel ID {imovel_id} não encontrado ao verificar regras de necessidade de dois horários.")
        return False # Não pode determinar sem dados do imóvel

    tamanho_imovel = float(imovel['tamanho'])
    status_mobilia_imovel = imovel['mobiliado']

    # Aplica as regras:
    # 1. Se o tamanho for 100m² ou mais, necessita de dois horários.
    # 2. OU, se o imóvel for 'mobiliado', necessita de dois horários.
    if tamanho_imovel >= 100 or status_mobilia_imovel == "mobiliado":
        return True
    
    return False # Caso contrário, um horário é suficiente


def calcular_valor_final_vistoria(imovel_id: int, tipo_vistoria: str) -> Optional[float]:
    """
    Calcula o valor final da vistoria que a Engentoria cobra (valor base para o cliente).

    Este valor é derivado do campo `valor` armazenado na tabela `imoveis`
    (que por sua vez foi calculado no cadastro/atualização do imóvel com base no
    tamanho, mobília e tabela da imobiliária).
    Para vistorias do tipo 'CONFERENCIA', o valor é 50% do valor base do imóvel.
    Para 'ENTRADA' e 'SAIDA', é o valor base completo.

    Args:
        imovel_id (int): ID do imóvel.
        tipo_vistoria (str): Tipo da vistoria ('ENTRADA', 'SAIDA', 'CONFERENCIA').

    Returns:
        Optional[float]: O valor final calculado para a vistoria, arredondado para 2 casas decimais.
                         Retorna None se o imóvel não for encontrado ou o tipo de vistoria for inválido.
    """
    if tipo_vistoria not in ['ENTRADA', 'SAIDA', 'CONFERENCIA']:
        logging.warning(f"Tipo de vistoria inválido '{tipo_vistoria}' fornecido para cálculo de valor final.")
        return None

    imovel = obter_imovel_por_id(imovel_id)
    if not imovel:
        logging.warning(f"Imóvel ID {imovel_id} não encontrado para cálculo de valor final de vistoria.")
        return None

    valor_base_do_imovel = float(imovel['valor']) # Valor pré-calculado e armazenado no imóvel

    if tipo_vistoria == 'CONFERENCIA':
        return round(valor_base_do_imovel * 0.5, 2) # 50% para conferência
    else: # Para 'ENTRADA' ou 'SAIDA'
        return round(valor_base_do_imovel, 2) # Valor completo

def calcular_valor_vistoriador(tamanho_m2: float, mobiliado_status: str, tipo_vistoria_agenda: str) -> float:
    """
    Calcula o valor a ser pago ao vistoriador por uma vistoria específica.

    As regras de cálculo são baseadas no tamanho do imóvel (m²), no estado de mobília
    ('mobiliado', 'semi_mobiliado', 'sem_mobilia') e no tipo de vistoria agendada
    ('ENTRADA', 'SAIDA', 'CONFERENCIA').
    Vistorias de 'CONFERENCIA' pagam 50% do valor base calculado para o vistoriador.

    Args:
        tamanho_m2 (float): Tamanho do imóvel em metros quadrados.
        mobiliado_status (str): Estado de mobília do imóvel.
        tipo_vistoria_agenda (str): Tipo da vistoria ('ENTRADA', 'SAIDA', 'CONFERENCIA').

    Returns:
        float: O valor calculado a ser pago ao vistoriador, arredondado para 2 casas decimais.
               Retorna 0.0 se o tipo de mobília for desconhecido.
    """
    valor_base_para_vistoriador = 0.0 # Valor antes de aplicar fator de conferência

    # Lógica de cálculo baseada no estado de mobília e tamanho
    if mobiliado_status == 'mobiliado':
        if tamanho_m2 < 50:
            valor_base_para_vistoriador = 65.00
        elif 50 <= tamanho_m2 < 100: 
            valor_base_para_vistoriador = tamanho_m2 * 1.25
        elif 100 <= tamanho_m2 <= 140:
            valor_base_para_vistoriador = 125.00
        else: # Acima de 140m²
            valor_base_para_vistoriador = tamanho_m2 * 0.90
    elif mobiliado_status in ['sem_mobilia', 'semi_mobiliado']:
        if tamanho_m2 < 50:
            valor_base_para_vistoriador = 50.00
        elif 50 <= tamanho_m2 < 100:
            valor_base_para_vistoriador = tamanho_m2 * 1.00
        elif 100 <= tamanho_m2 <= 135:
            valor_base_para_vistoriador = 100.00
        else: # Acima de 135m²
            valor_base_para_vistoriador = tamanho_m2 * 0.75
    else:
        # Caso o status da mobília não seja um dos esperados
        logging.warning(f"Tipo de mobília desconhecido '{mobiliado_status}' recebido para cálculo do valor do vistoriador.")
        return 0.0 # Retorna 0 ou poderia levantar uma exceção

    # Aplica o redutor de 50% se a vistoria for do tipo 'CONFERENCIA'
    valor_final_para_vistoriador = 0.0
    if tipo_vistoria_agenda == 'CONFERENCIA':
        valor_final_para_vistoriador = valor_base_para_vistoriador * 0.5
    else: # Para 'ENTRADA' ou 'SAIDA', o valor base é o valor final
        valor_final_para_vistoriador = valor_base_para_vistoriador
        
    return round(valor_final_para_vistoriador, 2) # Arredonda para duas casas decimais


# Bloco de exemplo de uso e teste do model.
if __name__ == '__main__':
    # Importações para os testes, ajustando caminhos se necessário para execução direta
    try:
        from .database import criar_tabelas
        from .imobiliaria_model import cadastrar_imobiliaria as cadastrar_imob_teste
        from .usuario_model import cadastrar_cliente as cadastrar_cli_teste
    except ImportError:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from models.database import criar_tabelas
        from models.imobiliaria_model import cadastrar_imobiliaria as cadastrar_imob_teste
        from models.usuario_model import cadastrar_cliente as cadastrar_cli_teste


    logging.info("Preparando ambiente para testes do imovel_model...")
    criar_tabelas() # Garante que as tabelas existam

    print("\n--- Testando Model Imóvel (com cálculo de valor para vistoriador) ---")

    # Testes da função calcular_valor_vistoriador
    print("\n1. Testes da função calcular_valor_vistoriador:")
    print(f"  -> Valor Vistoriador (Mobiliado, 40m², ENTRADA): R$ {calcular_valor_vistoriador(40, 'mobiliado', 'ENTRADA')}") # Esperado 65.00
    print(f"  -> Valor Vistoriador (Mobiliado, 70m², SAIDA): R$ {calcular_valor_vistoriador(70, 'mobiliado', 'SAIDA')}")   # Esperado 70*1.25 = 87.50
    print(f"  -> Valor Vistoriador (Mobiliado, 120m², ENTRADA): R$ {calcular_valor_vistoriador(120, 'mobiliado', 'ENTRADA')}")# Esperado 125.00
    print(f"  -> Valor Vistoriador (Mobiliado, 150m², CONFERENCIA): R$ {calcular_valor_vistoriador(150, 'mobiliado', 'CONFERENCIA')}")# Esperado (150*0.90)*0.5 = 135*0.5 = 67.50

    print(f"  -> Valor Vistoriador (Sem Mobília, 30m², ENTRADA): R$ {calcular_valor_vistoriador(30, 'sem_mobilia', 'ENTRADA')}") # Esperado 50.00
    print(f"  -> Valor Vistoriador (Semi-Mobiliado, 80m², SAIDA): R$ {calcular_valor_vistoriador(80, 'semi_mobiliado', 'SAIDA')}")# Esperado 80*1.00 = 80.00
    print(f"  -> Valor Vistoriador (Sem Mobília, 110m², ENTRADA): R$ {calcular_valor_vistoriador(110, 'sem_mobilia', 'ENTRADA')}")# Esperado 100.00
    print(f"  -> Valor Vistoriador (Semi-Mobiliado, 200m², CONFERENCIA): R$ {calcular_valor_vistoriador(200, 'semi_mobiliado', 'CONFERENCIA')}")# Esperado (200*0.75)*0.5 = 150*0.5 = 75.00
    
    # Cadastrar dependências para teste de cadastro de imóvel
    print("\n2. Cadastrando dependências para teste de imóvel:")
    cliente_id_teste_imovel = cadastrar_cli_teste("Cliente Para Imóvel Teste", "cli.imovel@teste.com")
    imobiliaria_id_teste_imovel = cadastrar_imob_teste("Imobiliária Para Imóvel Teste", 10, 12, 15) # Valores fictícios

    imovel_id_cadastrado = None
    if cliente_id_teste_imovel and imobiliaria_id_teste_imovel:
        print("\n3. Testando cadastro de imóvel:")
        imovel_id_cadastrado = cadastrar_imovel(
            cod_imovel="IMVTEST001",
            cliente_id=cliente_id_teste_imovel,
            imobiliaria_id=imobiliaria_id_teste_imovel,
            endereco="Rua Teste Imóvel, 100",
            tamanho=70.0,
            mobiliado="semi_mobiliado",
            cep="74000-001"
        )
        if imovel_id_cadastrado:
            print(f"  Imóvel cadastrado com ID: {imovel_id_cadastrado}")
            # Testar obtenção do imóvel cadastrado
            print("  Verificando imóvel cadastrado...")
            imovel_obtido = obter_imovel_por_id(imovel_id_cadastrado)
            if imovel_obtido:
                print(f"  -> Dados do imóvel obtido: {imovel_obtido}")
                # Testar regra de dois horários
                print(f"  -> Necessita dois horários (ENTRADA): {regras_necessita_dois_horarios(imovel_id_cadastrado, 'ENTRADA')}") # 70m2, semi -> False
                print(f"  -> Necessita dois horários (CONFERENCIA): {regras_necessita_dois_horarios(imovel_id_cadastrado, 'CONFERENCIA')}") # False
                 # Testar cálculo do valor final da vistoria (Engentoria)
                print(f"  -> Valor Final Vistoria Engentoria (ENTRADA): R$ {calcular_valor_final_vistoria(imovel_id_cadastrado, 'ENTRADA')}")
                print(f"  -> Valor Final Vistoria Engentoria (CONFERENCIA): R$ {calcular_valor_final_vistoria(imovel_id_cadastrado, 'CONFERENCIA')}")


            print("\n4. Testando atualização do imóvel:")
            sucesso_update = atualizar_imovel(
                imovel_id_cadastrado,
                endereco="Rua Teste Imóvel Atualizada, 200",
                tamanho=110.0, # Alterando tamanho
                mobiliado="mobiliado" # Alterando mobília
            )
            if sucesso_update:
                print("  Imóvel atualizado com sucesso. Verificando dados atualizados e valor...")
                imovel_atualizado = obter_imovel_por_id(imovel_id_cadastrado)
                if imovel_atualizado:
                    print(f"  -> Dados atualizados: {imovel_atualizado}")
                    print(f"  -> Valor da vistoria (Engentoria) após atualização: R$ {imovel_atualizado.get('valor')}")
                    # Testar regra de dois horários novamente
                    print(f"  -> Necessita dois horários após att (ENTRADA): {regras_necessita_dois_horarios(imovel_id_cadastrado, 'ENTRADA')}") # 110m2, mobiliado -> True
            else:
                print("  Falha ao atualizar imóvel.")
    else:
        print("  Não foi possível cadastrar cliente ou imobiliária de teste, pulando testes de cadastro de imóvel.")

    # Teste de listagem
    print("\n5. Testando listagem de todos os imóveis:")
    todos_os_imoveis = listar_todos_imoveis()
    if todos_os_imoveis:
        print(f"  Total de imóveis encontrados: {len(todos_os_imoveis)}")
        # print(f"  Primeiro imóvel da lista: {todos_os_imoveis[0]}")
    else:
        print("  Nenhum imóvel encontrado.")

    # Teste de deleção (lembrar que ON DELETE SET NULL na agenda irá desvincular)
    if imovel_id_cadastrado:
        print(f"\n6. Testando deleção do imóvel ID {imovel_id_cadastrado}:")
        # Antes de deletar, poderia-se criar um agendamento para ver o SET NULL funcionando.
        # Por simplicidade, apenas deletamos.
        sucesso_delete = deletar_imovel(imovel_id_cadastrado)
        print(f"  Deleção bem-sucedida: {sucesso_delete}")
        print(f"  Verificando imóvel ID {imovel_id_cadastrado} após deleção: {obter_imovel_por_id(imovel_id_cadastrado)}")
    
    print("\n--- Fim dos testes do imovel_model.py ---")

