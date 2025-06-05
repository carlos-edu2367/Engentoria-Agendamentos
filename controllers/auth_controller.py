# engentoria/controllers/auth_controller.py

# Importa as funções necessárias do modelo de usuário para interagir com a camada de dados
from models.usuario_model import login_usuario, redefinir_senha_usuario

# Importa os validadores relevantes do módulo de utilitários
from utils.validators import is_valid_email, is_valid_password

# Importações para tipagem estática, melhorando a clareza e detecção de erros
from typing import Dict, Any, Optional, Tuple

class AuthController:
    """
    Controlador responsável pela lógica de autenticação de usuários e
    pelo processo de redefinição de senha.

    Esta classe lida com:
    - Processamento de tentativas de login.
    - Validação de credenciais.
    - Processamento de solicitações de redefinição de senha.
    - Validação de dados para redefinição de senha.
    """

    def __init__(self):
        """
        Construtor da classe AuthController.

        Neste momento, o construtor é simples e não requer injeção de dependências
        ou configurações complexas, pois as funções do modelo são importadas diretamente.
        """
        pass # Nenhuma inicialização específica é necessária no momento.

    def processar_login(self, email: str, senha: str) -> Dict[str, Any]:
        """
        Processa a tentativa de login de um usuário no sistema.

        Valida o formato do e-mail e verifica se a senha não está vazia.
        Em seguida, chama a função `login_usuario` do modelo para autenticar
        as credenciais contra o banco de dados.

        Args:
            email (str): O endereço de e-mail fornecido pelo usuário para login.
            senha (str): A senha fornecida pelo usuário.

        Returns:
            Dict[str, Any]: Um dicionário contendo o resultado da tentativa de login:
                'success' (bool): True se o login for bem-sucedido, False caso contrário.
                'message' (Optional[str]): Uma mensagem informativa sobre o resultado
                                           (ex: erro de formato, credenciais inválidas).
                'user_id' (Optional[int]): O ID do usuário, se o login for bem-sucedido.
                'user_type' (Optional[str]): O tipo do usuário (ex: 'adm', 'vistoriador'),
                                             se o login for bem-sucedido.
        """
        # 1. Validação básica dos campos de entrada (presença e formato)
        # Verifica se e-mail e senha foram fornecidos
        if not email or not senha:
            return {'success': False, 'message': "E-mail e senha são obrigatórios."}
        
        # Verifica se o e-mail fornecido possui um formato válido
        if not is_valid_email(email):
            return {'success': False, 'message': "Formato de e-mail inválido."}

        # (Opcional) Validação de formato de senha pode ser adicionada aqui,
        # como verificar se não é apenas espaços em branco, embora a validação
        # principal da senha ocorra na comparação com o hash no banco.

        # 2. Chamar a função do modelo para tentar realizar o login
        # A função `login_usuario` deve retornar o ID e o tipo do usuário em caso de sucesso,
        # ou None em caso de falha (usuário não encontrado ou senha incorreta).
        resultado_login: Optional[Tuple[int, str]] = login_usuario(email, senha)

        # 3. Processar o resultado retornado pelo modelo e preparar a resposta para a View
        if resultado_login:
            user_id, user_type = resultado_login # Desempacota o ID e o tipo do usuário
            return {
                'success': True,
                'user_id': user_id,
                'user_type': user_type,
                'message': "Login bem-sucedido!" # Mensagem de sucesso (opcional)
            }
        else:
            # Se `resultado_login` for None, as credenciais são inválidas.
            # O modelo `login_usuario` pode logar internamente a razão específica (não encontrado vs senha errada).
            # Para a interface do usuário, uma mensagem genérica é frequentemente preferível por segurança.
            return {'success': False, 'message': "E-mail ou senha incorretos."}

    def processar_redefinicao_senha(self, email: str, nova_senha: str, confirmacao_nova_senha: str) -> Dict[str, Any]:
        """
        Processa a tentativa de redefinição de senha para um usuário.

        Valida o formato do e-mail, verifica se a nova senha e sua confirmação
        coincidem, e se a nova senha atende aos critérios de segurança definidos
        (ex: comprimento mínimo).

        Args:
            email (str): O e-mail do usuário cuja senha será redefinida.
            nova_senha (str): A nova senha desejada pelo usuário.
            confirmacao_nova_senha (str): A confirmação da nova senha.

        Returns:
            Dict[str, Any]: Um dicionário contendo o resultado da tentativa de redefinição:
                'success' (bool): True se a senha for redefinida com sucesso, False caso contrário.
                'message' (str): Uma mensagem informativa sobre o resultado da operação.
        """
        # 1. Validação dos campos de entrada
        # Verifica se todos os campos necessários foram preenchidos
        if not email or not nova_senha or not confirmacao_nova_senha:
            return {'success': False, 'message': "Todos os campos são obrigatórios."}

        # Valida o formato do e-mail
        if not is_valid_email(email):
            return {'success': False, 'message': "Formato de e-mail inválido."}

        # Verifica se a nova senha e sua confirmação são idênticas
        if nova_senha != confirmacao_nova_senha:
            return {'success': False, 'message': "As senhas não coincidem."}

        # Validação de força/complexidade da nova senha
        # Exemplo: mínimo de 6 caracteres. Pode ser expandido com `is_valid_password`.
        if not is_valid_password(nova_senha, min_length=6):
            return {'success': False, 'message': "A nova senha deve ter pelo menos 6 caracteres."}
        
        # (Opcional) Exemplo de validação de senha mais complexa:
        # if not is_valid_password(nova_senha, min_length=8, require_uppercase=True, require_digit=True, require_special_char=True):
        #     return {'success': False, 'message': "A senha deve ter no mínimo 8 caracteres, incluindo maiúscula, número e caractere especial."}

        # 2. Chamar a função do modelo para tentar redefinir a senha
        # A função `redefinir_senha_usuario` deve retornar True em caso de sucesso, False caso contrário.
        sucesso_redefinicao: bool = redefinir_senha_usuario(email, nova_senha)

        # 3. Processar o resultado retornado pelo modelo e preparar a resposta
        if sucesso_redefinicao:
            return {'success': True, 'message': "Senha redefinida com sucesso!"}
        else:
            # A falha pode ocorrer se o e-mail não for encontrado no banco de dados
            # ou se houver algum erro durante a atualização da senha no modelo.
            # O modelo `redefinir_senha_usuario` pode logar detalhes do erro.
            return {'success': False, 'message': "Não foi possível redefinir a senha. Verifique o e-mail ou tente novamente mais tarde."}

# Bloco para execução de testes rápidos (não faz parte da lógica principal da classe)
if __name__ == '__main__':
    auth_ctrl = AuthController()
    print("AuthController instanciado. Descomente e adapte os testes abaixo.")

    # --- Exemplo de Teste de Login (requer um usuário cadastrado) ---
    # email_teste_login = "admin@example.com" # Substitua por um e-mail de teste válido
    # senha_teste_login = "admin123"       # Substitua pela senha correspondente
    # print(f"\nTentando login com E-mail: {email_teste_login}")
    # resultado_login = auth_ctrl.processar_login(email_teste_login, senha_teste_login)
    # print(f"--> Resultado do Login: {resultado_login}")
    # if resultado_login['success']:
    #     print(f"    ID do Usuário: {resultado_login['user_id']}, Tipo: {resultado_login['user_type']}")

    # --- Exemplo de Teste de Login com dados inválidos ---
    # print("\nTentando login com E-mail inválido:")
    # resultado_login_invalido = auth_ctrl.processar_login("emailinvalido", "senhaqualquer")
    # print(f"--> Resultado do Login Inválido: {resultado_login_invalido}")

    # print("\nTentando login com senha incorreta:")
    # resultado_login_senha_errada = auth_ctrl.processar_login(email_teste_login, "senhaerrada123")
    # print(f"--> Resultado do Login Senha Errada: {resultado_login_senha_errada}")


    # --- Exemplo de Teste de Redefinição de Senha (requer um usuário cadastrado) ---
    # email_teste_redefinicao = "vistoriador@example.com" # Substitua por um e-mail de teste válido
    # nova_senha_teste = "novaSenhaSegura456"
    # print(f"\nTentando redefinir senha para E-mail: {email_teste_redefinicao}")

    # # Teste com senhas não coincidentes
    # resultado_redefinicao_diff_pass = auth_ctrl.processar_redefinicao_senha(
    #     email_teste_redefinicao, nova_senha_teste, "outraSenha789"
    # )
    # print(f"--> Resultado Redefinição (senhas diferentes): {resultado_redefinicao_diff_pass}")

    # # Teste com senha fraca
    # resultado_redefinicao_weak_pass = auth_ctrl.processar_redefinicao_senha(
    #     email_teste_redefinicao, "123", "123"
    # )
    # print(f"--> Resultado Redefinição (senha fraca): {resultado_redefinicao_weak_pass}")
    
    # # Teste de redefinição bem-sucedida
    # resultado_redefinicao_ok = auth_ctrl.processar_redefinicao_senha(
    #     email_teste_redefinicao, nova_senha_teste, nova_senha_teste
    # )
    # print(f"--> Resultado Redefinição (OK): {resultado_redefinicao_ok}")

    # # Se a redefinição foi OK, tentar logar com a nova senha
    # if resultado_redefinicao_ok['success']:
    #     print(f"\nTentando login com a NOVA senha para {email_teste_redefinicao}...")
    #     resultado_login_nova_senha = auth_ctrl.processar_login(email_teste_redefinicao, nova_senha_teste)
    #     print(f"--> Resultado do Login com Nova Senha: {resultado_login_nova_senha}")

