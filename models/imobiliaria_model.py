# engentoria/models/imobiliaria_model.py
import sqlite3 # Biblioteca para interagir com bancos de dados SQLite
from .database import conectar_banco # Importação da função de conexão do mesmo pacote 'models'
from typing import Optional, List, Dict, Any # Tipos para anotações estáticas, melhorando clareza

def cadastrar_imobiliaria(nome: str, valor_sem_mobilia: float, valor_semi_mobiliado: float, valor_mobiliado: float) -> Optional[int]:
    """
    Cadastra uma nova imobiliária no banco de dados.

    Args:
        nome (str): Nome da imobiliária. Este campo é obrigatório e deve ser único.
        valor_sem_mobilia (float): Valor por metro quadrado (m²) cobrado pela imobiliária
                                   para vistorias de imóveis sem mobília. Deve ser um número não negativo.
        valor_semi_mobiliado (float): Valor por m² para imóveis semi-mobiliados. Deve ser não negativo.
        valor_mobiliado (float): Valor por m² para imóveis completamente mobiliados. Deve ser não negativo.

    Returns:
        Optional[int]: O ID da imobiliária recém-cadastrada em caso de sucesso.
                       Retorna None se o cadastro falhar (ex: nome duplicado, valores inválidos).
    """
    # Validação dos dados de entrada
    if not nome: # Verifica se o nome foi fornecido
        print("❌ O nome da imobiliária é obrigatório.")
        return None
    # Verifica se os valores são numéricos (int ou float)
    if not isinstance(valor_sem_mobilia, (int, float)) or \
       not isinstance(valor_semi_mobiliado, (int, float)) or \
       not isinstance(valor_mobiliado, (int, float)):
        print("❌ Os valores por m² devem ser números.")
        return None
    # Verifica se os valores não são negativos
    if valor_sem_mobilia < 0 or valor_semi_mobiliado < 0 or valor_mobiliado < 0:
        print("❌ Os valores por m² não podem ser negativos.")
        return None

    conexao = None # Inicializa a variável de conexão
    try:
        conexao = conectar_banco() # Estabelece a conexão com o banco
        cursor = conexao.cursor() # Cria um cursor para executar comandos SQL
        # Query SQL para inserir uma nova imobiliária na tabela 'imobiliarias'
        cursor.execute("""
            INSERT INTO imobiliarias (nome, valor_sem_mobilia, valor_semi_mobiliado, valor_mobiliado)
            VALUES (?, ?, ?, ?)
        """, (nome, valor_sem_mobilia, valor_semi_mobiliado, valor_mobiliado))
        conexao.commit() # Confirma (salva) as alterações no banco
        imobiliaria_id = cursor.lastrowid # Obtém o ID da última linha inserida (ID da nova imobiliária)
        print(f"✅ Imobiliária '{nome}' cadastrada com sucesso! ID: {imobiliaria_id}")
        return imobiliaria_id
    except sqlite3.IntegrityError:
        # Este erro geralmente ocorre se a constraint UNIQUE (ex: no nome da imobiliária) for violada.
        print(f"⚠️ Erro: A imobiliária com o nome '{nome}' já está cadastrada.")
        return None
    except Exception as e: # Captura qualquer outra exceção que possa ocorrer
        print(f"❌ Erro inesperado ao cadastrar imobiliária: {e}")
        return None
    finally: # Bloco 'finally' é sempre executado, independentemente de exceções
        if conexao:
            conexao.close() # Garante que a conexão com o banco seja fechada

def listar_todas_imobiliarias() -> List[Dict[str, Any]]:
    """
    Lista todas as imobiliárias cadastradas no banco de dados, ordenadas alfabeticamente pelo nome.

    Returns:
        List[Dict[str, Any]]: Uma lista de dicionários, onde cada dicionário representa
                                os dados de uma imobiliária (id, nome, valores por m²).
                                Retorna uma lista vazia se nenhuma imobiliária for encontrada
                                ou em caso de erro na consulta.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Query SQL para selecionar todos os dados de todas as imobiliárias
        cursor.execute("""
            SELECT id, nome, valor_sem_mobilia, valor_semi_mobiliado, valor_mobiliado
            FROM imobiliarias
            ORDER BY nome ASC /* Ordena os resultados pelo nome da imobiliária */
        """)
        imobiliarias_db = cursor.fetchall() # Recupera todas as linhas do resultado da query
        
        # Converte a lista de tuplas (retorno do banco) em uma lista de dicionários
        # para facilitar o manuseio dos dados em outras partes do sistema.
        lista_imobiliarias = [
            {
                'id': row[0], # ID da imobiliária
                'nome': row[1], # Nome
                'valor_sem_mobilia': row[2], # Valor/m² sem mobília
                'valor_semi_mobiliado': row[3], # Valor/m² semi-mobiliado
                'valor_mobiliado': row[4] # Valor/m² mobiliado
            }
            for row in imobiliarias_db # Itera sobre cada linha (tupla) retornada do banco
        ]
        return lista_imobiliarias
    except Exception as e:
        print(f"❌ Erro ao listar imobiliárias: {e}")
        return [] # Retorna lista vazia em caso de erro
    finally:
        if conexao:
            conexao.close()

def obter_imobiliaria_por_id(imobiliaria_id: int) -> Optional[Dict[str, Any]]:
    """
    Busca e retorna os dados de uma imobiliária específica com base no seu ID.

    Args:
        imobiliaria_id (int): O ID da imobiliária a ser pesquisada.

    Returns:
        Optional[Dict[str, Any]]: Um dicionário contendo os dados da imobiliária
                                     se ela for encontrada. Retorna None se nenhuma
                                     imobiliária com o ID fornecido existir ou em caso de erro.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Query SQL para selecionar dados de uma imobiliária específica pelo ID
        cursor.execute("""
            SELECT id, nome, valor_sem_mobilia, valor_semi_mobiliado, valor_mobiliado
            FROM imobiliarias
            WHERE id = ? /* Cláusula WHERE para filtrar pelo ID fornecido */
        """, (imobiliaria_id,)) # O ID é passado como uma tupla de um elemento
        imobiliaria_db = cursor.fetchone() # Recupera uma única linha (ou None se não encontrar)
        
        if imobiliaria_db: # Se uma imobiliária foi encontrada
            # Converte a tupla do banco em um dicionário
            return {
                'id': imobiliaria_db[0],
                'nome': imobiliaria_db[1],
                'valor_sem_mobilia': imobiliaria_db[2],
                'valor_semi_mobiliado': imobiliaria_db[3],
                'valor_mobiliado': imobiliaria_db[4]
            }
        # Se não encontrou, loga uma informação (não é um erro crítico)
        print(f"ℹ️ Imobiliária com ID {imobiliaria_id} não encontrada.")
        return None
    except Exception as e:
        print(f"❌ Erro ao obter imobiliária ID {imobiliaria_id}: {e}")
        return None
    finally:
        if conexao:
            conexao.close()

def atualizar_imobiliaria(imobiliaria_id: int, nome: Optional[str] = None,
                          valor_sem_mobilia: Optional[float] = None,
                          valor_semi_mobiliado: Optional[float] = None,
                          valor_mobiliado: Optional[float] = None) -> bool:
    """
    Atualiza os dados de uma imobiliária existente no banco de dados.

    Apenas os campos que forem fornecidos (ou seja, não forem None) serão
    incluídos na instrução UPDATE.

    Args:
        imobiliaria_id (int): ID da imobiliária a ser atualizada.
        nome (Optional[str]): Novo nome para a imobiliária. Se None, não será alterado.
        valor_sem_mobilia (Optional[float]): Novo valor por m² para imóveis sem mobília.
        valor_semi_mobiliado (Optional[float]): Novo valor por m² para semi-mobiliados.
        valor_mobiliado (Optional[float]): Novo valor por m² para mobiliados.

    Returns:
        bool: True se a atualização for bem-sucedida e pelo menos uma linha for afetada.
              False se a imobiliária não for encontrada, nenhum dado válido for fornecido
              para atualização, ou ocorrer um erro.
    """
    # Listas para construir dinamicamente a parte SET da query SQL
    campos_para_atualizar = [] # Armazena strings como "nome = ?"
    valores_para_atualizar = [] # Armazena os valores correspondentes aos '?'

    # Verifica cada argumento opcional. Se foi fornecido, adiciona à query e aos valores.
    if nome is not None:
        if not nome.strip(): # Valida se o nome não é apenas espaços em branco
            print("❌ O nome da imobiliária não pode ser vazio.")
            return False
        campos_para_atualizar.append("nome = ?")
        valores_para_atualizar.append(nome)
    if valor_sem_mobilia is not None:
        if not isinstance(valor_sem_mobilia, (int, float)) or valor_sem_mobilia < 0:
            print("❌ Valor sem mobília inválido (deve ser número não negativo).")
            return False
        campos_para_atualizar.append("valor_sem_mobilia = ?")
        valores_para_atualizar.append(valor_sem_mobilia)
    if valor_semi_mobiliado is not None:
        if not isinstance(valor_semi_mobiliado, (int, float)) or valor_semi_mobiliado < 0:
            print("❌ Valor semi-mobiliado inválido (deve ser número não negativo).")
            return False
        campos_para_atualizar.append("valor_semi_mobiliado = ?")
        valores_para_atualizar.append(valor_semi_mobiliado)
    if valor_mobiliado is not None:
        if not isinstance(valor_mobiliado, (int, float)) or valor_mobiliado < 0:
            print("❌ Valor mobiliado inválido (deve ser número não negativo).")
            return False
        campos_para_atualizar.append("valor_mobiliado = ?")
        valores_para_atualizar.append(valor_mobiliado)

    # Se nenhuma informação foi fornecida para atualização, não faz nada.
    if not campos_para_atualizar:
        print("ℹ️ Nenhum dado fornecido para atualização da imobiliária.")
        # Retorna False pois nenhuma atualização foi realmente tentada/realizada.
        # Poderia retornar True se a intenção fosse "nenhum erro, mas nada a fazer".
        return False 

    # Constrói a string da cláusula SET (ex: "nome = ?, valor_mobiliado = ?")
    query_set_string = ", ".join(campos_para_atualizar)
    # Adiciona o ID da imobiliária ao final da lista de valores (para a cláusula WHERE)
    valores_para_atualizar.append(imobiliaria_id)

    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Executa a query UPDATE construída dinamicamente
        cursor.execute(f"UPDATE imobiliarias SET {query_set_string} WHERE id = ?", tuple(valores_para_atualizar))
        conexao.commit()
        
        # cursor.rowcount indica o número de linhas afetadas pela última operação.
        # Se for > 0, a atualização ocorreu.
        if cursor.rowcount > 0:
            print(f"✅ Imobiliária ID {imobiliaria_id} atualizada com sucesso.")
            return True
        else:
            # Se rowcount == 0, pode ser que a imobiliária com o ID não exista,
            # ou que os valores fornecidos eram idênticos aos já existentes no banco.
            print(f"⚠️ Imobiliária ID {imobiliaria_id} não encontrada para atualização ou nenhum dado foi efetivamente alterado.")
            return False
    except sqlite3.IntegrityError: # Ex: tentativa de atualizar nome para um que já existe (se nome é UNIQUE)
        print(f"⚠️ Erro de integridade: O nome '{nome}' já pode estar em uso por outra imobiliária.")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado ao atualizar imobiliária ID {imobiliaria_id}: {e}")
        return False
    finally:
        if conexao:
            conexao.close()

def deletar_imobiliaria(imobiliaria_id: int) -> bool:
    """
    Deleta uma imobiliária do banco de dados com base no seu ID.

    Importante: A tabela `imoveis` possui uma chave estrangeira para `imobiliarias(id)`
    com a restrição `ON DELETE RESTRICT`. Isso significa que uma imobiliária
    NÃO PODE ser deletada se houver qualquer imóvel associado a ela no banco de dados.
    Nesse caso, a operação de DELETE falhará com um `sqlite3.IntegrityError`.

    Args:
        imobiliaria_id (int): O ID da imobiliária a ser deletada.

    Returns:
        bool: True se a imobiliária foi deletada com sucesso.
              False se a imobiliária não foi encontrada, se houver imóveis associados
              (impedindo a deleção), ou se ocorrer outro erro.
    """
    conexao = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        # Ativa o PRAGMA foreign_keys para garantir que as restrições sejam verificadas.
        # Embora geralmente configurado na conexão, reiterar pode ser útil ou necessário
        # dependendo da configuração do driver/conexão.
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        cursor.execute("DELETE FROM imobiliarias WHERE id = ?", (imobiliaria_id,))
        conexao.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ Imobiliária ID {imobiliaria_id} deletada com sucesso.")
            return True
        else:
            print(f"⚠️ Imobiliária ID {imobiliaria_id} não encontrada para deleção.")
            return False # Imobiliária não existia
    except sqlite3.IntegrityError:
        # Este erro é esperado devido à constraint ON DELETE RESTRICT na tabela 'imoveis'
        # se existirem imóveis referenciando esta imobiliária.
        print(f"❌ Erro de Integridade: Não é possível deletar a imobiliária ID {imobiliaria_id} pois ela possui imóveis associados. Remova ou desassocie os imóveis primeiro.")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado ao deletar imobiliária ID {imobiliaria_id}: {e}")
        return False
    finally:
        if conexao:
            conexao.close()

# Bloco de exemplo de uso e teste do model.
# Este código só é executado quando o arquivo `imobiliaria_model.py` é rodado diretamente.
if __name__ == '__main__':
    # Importa a função `criar_tabelas` para garantir que a estrutura do banco exista para os testes.
    # (A importação relativa pode precisar de ajuste se rodar fora do contexto do projeto principal)
    try:
        from .database import criar_tabelas
    except ImportError: # Fallback para execução direta do script
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from models.database import criar_tabelas

    print("INFO: Preparando ambiente para testes do imobiliaria_model...")
    criar_tabelas() # Garante que as tabelas existam

    print("\n--- Testando Model Imobiliária ---")

    # Teste de cadastro de imobiliárias
    print("\n1. Testando cadastro de imobiliárias:")
    imob1_id = cadastrar_imobiliaria("Imobiliária Sol Nascente Teste", 10.0, 12.5, 15.0)
    imob2_id = cadastrar_imobiliaria("Imóveis & Cia Teste", 9.5, 11.0, 14.0)
    # Tentativa de cadastrar com nome duplicado (deve falhar e retornar None)
    cadastrar_imobiliaria("Imobiliária Sol Nascente Teste", 1,1,1) 

    # Teste de listagem de todas as imobiliárias
    print("\n2. Testando listagem de todas as imobiliárias:")
    imobiliarias = listar_todas_imobiliarias()
    if imobiliarias:
        for imob in imobiliarias:
            print(f"  -> {imob}")
    else:
        print("  Nenhuma imobiliária encontrada.")

    # Teste de obtenção de imobiliária por ID
    if imob1_id:
        print(f"\n3. Testando obtenção da Imobiliária ID {imob1_id}:")
        detalhe_imob1 = obter_imobiliaria_por_id(imob1_id)
        if detalhe_imob1:
            print(f"  -> {detalhe_imob1}")
        else:
            print(f"  Imobiliária ID {imob1_id} não encontrada (o que seria inesperado aqui).")

    # Teste de atualização de imobiliária
    if imob2_id:
        print(f"\n4. Testando atualização da Imobiliária ID {imob2_id}:")
        sucesso_att = atualizar_imobiliaria(imob2_id, nome="Imóveis & Companhia Teste Ltda", valor_mobiliado=14.75)
        if sucesso_att:
            print(f"  Após atualização: {obter_imobiliaria_por_id(imob2_id)}")
        else:
            print(f"  Falha ao atualizar imobiliária ID {imob2_id}.")
        # Tentativa de atualizar para um nome que já existe (se imob1_id for diferente e o nome for igual)
        if imob1_id and imob1_id != imob2_id: # Garante que estamos testando com IDs diferentes
             print(f"  Tentando atualizar ID {imob2_id} para nome duplicado ('Imobiliária Sol Nascente Teste')...")
             atualizar_imobiliaria(imob2_id, nome="Imobiliária Sol Nascente Teste")

    # Teste de deleção de imobiliária
    print("\n5. Testando deleção de imobiliária (sem imóveis associados):")
    # Cadastra uma imobiliária temporária para o teste de deleção
    imob_para_deletar_id = cadastrar_imobiliaria("Temporária Imóveis Teste", 5,5,5)
    if imob_para_deletar_id:
        print(f"  Tentando deletar Imobiliária ID {imob_para_deletar_id}...")
        deletado_sucesso = deletar_imobiliaria(imob_para_deletar_id)
        print(f"  Deleção bem-sucedida: {deletado_sucesso}")
        print(f"  Verificando Imobiliária ID {imob_para_deletar_id} após deleção: {obter_imobiliaria_por_id(imob_para_deletar_id)}")
    else:
        print("  Não foi possível cadastrar imobiliária temporária para teste de deleção.")

    # Teste de deleção de imobiliária com imóveis associados (espera-se falha)
    # Para este teste ser efetivo, seria necessário:
    # 1. Importar `imovel_model`.
    # 2. Cadastrar um cliente e um imóvel associados a `imob1_id`.
    # Ex: (requer imovel_model e usuario_model para cadastrar cliente)
    # from .usuario_model import cadastrar_cliente
    # from .imovel_model import cadastrar_imovel
    # cliente_teste_id = cadastrar_cliente("Cliente De Teste P/ Imob", "cli.del@teste.com")
    # if cliente_teste_id and imob1_id:
    #     cadastrar_imovel("IMVTESTDEL", cliente_teste_id, imob1_id, "End Teste Del", 50)
    print(f"\n6. Testando deleção da Imobiliária ID {imob1_id} (que pode ter imóveis associados):")
    if imob1_id:
        print(f"  (Nota: Este teste espera uma falha se existirem imóveis vinculados à Imobiliária ID {imob1_id} devido à restrição ON DELETE RESTRICT).")
        deletado_com_restricao = deletar_imobiliaria(imob1_id)
        print(f"  Tentativa de deleção da Imobiliária ID {imob1_id} resultou em: {deletado_com_restricao}")
        if not deletado_com_restricao:
            print("  --> Falha na deleção como esperado (ou imobiliária não existe mais).")
    else:
        print("  Imobiliária ID 'imob1_id' não definida para teste de deleção com restrição.")
    
    print("\n--- Fim dos testes do imobiliaria_model.py ---")

