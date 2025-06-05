# engentoria/utils/cleanup_routines.py
import logging
# Importa os módulos de modelo necessários para acessar as funções de banco de dados.
# Presume-se que 'models' é um pacote acessível a partir deste local.
from models import agenda_model, imovel_model

# Configuração básica do logging para este módulo.
# Isso permite que o módulo registre informações sobre seu progresso e quaisquer erros encontrados.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def executar_limpeza_inicial_banco(meses_antiguidade_agendamentos: int = 3):
    """
    Executa rotinas de limpeza no banco de dados, geralmente na inicialização do sistema.

    Esta função orquestra duas principais operações de limpeza:
    1. Deleção de agendamentos antigos: Remove registros da tabela 'agenda' que são mais
       antigos que um número especificado de meses. Consequentemente, dados relacionados
       a esses agendamentos (como imóveis e, potencialmente, clientes, dependendo da
       lógica em `agenda_model.deletar_agendamentos_antigos_e_dados_relacionados`)
       podem também ser afetados ou removidos.
    2. Deleção de imóveis órfãos: Remove imóveis da tabela 'imoveis' que não estão
       referenciados em nenhuma entrada ativa da tabela 'agenda'. Isso ajuda a manter
       a base de dados limpa de registros de imóveis que não têm mais utilidade
       no contexto de agendamentos.

    Args:
        meses_antiguidade_agendamentos (int): O número de meses que define o quão antigo
            um agendamento deve ser para ser considerado para deleção.
            O valor padrão é 3 meses.

    Returns:
        None: A função não retorna valores diretamente, mas registra informações
              sobre o processo de limpeza usando o módulo logging.

    Atenção:
        A deleção de dados, especialmente a que envolve cascata (como a potencial
        deleção de clientes), deve ser tratada com cuidado. É crucial entender
        as regras de `ON DELETE` definidas no esquema do banco de dados e nas
        funções dos modelos chamadas.
    """
    logging.info("--- Iniciando Rotina de Limpeza do Banco de Dados ---")

    # --- Etapa 1: Deletar agendamentos antigos e seus dados relacionados ---
    logging.info(f"Iniciando limpeza de agendamentos com mais de {meses_antiguidade_agendamentos} meses de antiguidade...")
    try:
        # Chama a função do 'agenda_model' para realizar a limpeza dos agendamentos.
        # Esta função é responsável por identificar e remover os agendamentos antigos
        # e, potencialmente, dados dependentes como imóveis e clientes,
        # conforme a lógica implementada em `agenda_model`.
        # --> resultados_limpeza_ag: Dicionário contendo contagens de itens deletados.
        resultados_limpeza_ag = agenda_model.deletar_agendamentos_antigos_e_dados_relacionados(meses_antiguidade_agendamentos)
        logging.info(f"Limpeza de agendamentos antigos concluída. Resultados: {resultados_limpeza_ag}")
    except Exception as e:
        # Captura exceções gerais que podem ocorrer durante a limpeza dos agendamentos.
        logging.error(f"Erro crítico durante a limpeza de agendamentos antigos: {e}", exc_info=True) # exc_info=True inclui o traceback no log

    # --- Etapa 2: Deletar imóveis que se tornaram órfãos ou já estavam órfãos ---
    # Um imóvel é considerado órfão se não estiver associado a nenhum agendamento.
    logging.info("Iniciando limpeza de imóveis órfãos (imóveis sem agendamentos associados)...")
    try:
        # Chama a função do 'imovel_model' para encontrar e deletar imóveis órfãos.
        # --> num_imoveis_orfaos_deletados: Contagem de imóveis órfãos removidos.
        num_imoveis_orfaos_deletados = imovel_model.deletar_imoveis_orfaos()
        logging.info(f"Limpeza de imóveis órfãos concluída. Total de imóveis órfãos deletados: {num_imoveis_orfaos_deletados}")
    except Exception as e:
        # Captura exceções gerais que podem ocorrer durante a limpeza dos imóveis órfãos.
        logging.error(f"Erro crítico durante a limpeza de imóveis órfãos: {e}", exc_info=True)

    logging.info("--- Rotina de Limpeza do Banco de Dados Concluída ---")

# Bloco de execução principal: executado apenas quando o script é rodado diretamente.
# Útil para testar a rotina de limpeza de forma isolada.
if __name__ == '__main__':
    # Configuração do ambiente para teste:
    # Garante que o interpretador Python consiga encontrar o pacote 'models'
    # ajustando o sys.path se necessário.
    import os
    import sys
    # --> current_dir_test: Diretório onde este script (cleanup_routines.py) está localizado.
    current_dir_test = os.path.dirname(os.path.abspath(__file__))
    # --> project_root_test: Supõe-se que a pasta 'utils' está dentro da pasta do projeto,
    #    então o diretório pai de 'utils' (current_dir_test) seria a raiz do projeto
    #    onde o pacote 'models' reside.
    project_root_test = os.path.dirname(current_dir_test)
    if project_root_test not in sys.path:
        sys.path.insert(0, project_root_test)

    # Importa a função para criar tabelas, assegurando que a estrutura do banco exista para o teste.
    from models.database import criar_tabelas
    print("Criando tabelas para teste de limpeza (se não existirem)...")
    criar_tabelas() # Garante que o banco e as tabelas estejam configurados.

    # Comentário: Para um teste eficaz, seria ideal popular o banco de dados
    # com dados de exemplo antes de executar a limpeza. Por exemplo:
    # - Agendamentos com datas antigas.
    # - Imóveis sem agendamentos associados.
    # Exemplo:
    # from models import agenda_model, imovel_model, usuario_model, imobiliaria_model
    # # Cadastrar um vistoriador, cliente, imobiliaria e imóvel de teste.
    # id_vist = usuario_model.cadastrar_usuario("Vist Teste Limpeza", "vist.limpeza@teste.com", "123", "vistoriador")
    # id_cli = usuario_model.cadastrar_cliente("Cli Teste Limpeza", "cli.limpeza@teste.com")
    # id_imob = imobiliaria_model.cadastrar_imobiliaria("Imob Limpeza", 1,1,1)
    # if id_cli and id_imob:
    #    id_imovel_antigo = imovel_model.cadastrar_imovel("IMVANTIGO", id_cli, id_imob, "Rua Antiga", 50)
    #    id_imovel_orfao = imovel_model.cadastrar_imovel("IMVORFAO", id_cli, id_imob, "Rua Orfa", 60)
    #    if id_vist and id_imovel_antigo:
    #       # Adicionar um agendamento antigo (ex: 4 meses atrás)
    #       data_antiga = (datetime.date.today() - datetime.timedelta(days=4*30)).strftime("%Y-%m-%d")
    #       agenda_model.adicionar_entrada_agenda_unica(id_vist, data_antiga, "10:00", tipo="ENTRADA", imovel_id=id_imovel_antigo, disponivel=False)

    print("\nExecutando rotina de limpeza com antiguidade de 1 mês para agendamentos...")
    # Chama a função principal de limpeza, testando com um período de 1 mês para agendamentos.
    executar_limpeza_inicial_banco(meses_antiguidade_agendamentos=1)
    print("\nRotina de limpeza finalizada. Verifique os logs e o estado do banco de dados.")

