# Quitanda da Liro

Aplicação web de venda presencial para uma quitanda. O sistema permite consultar produtos, montar um carrinho, cadastrar uma conta, entrar no perfil, criar pedidos e acompanhar o andamento da retirada.

O pagamento não ocorre pela internet: PIX, cartão ou dinheiro são pagos no caixa da loja. Não há entrega em domicílio.

## Funcionalidades

- Catálogo público de hortifrúti, bebidas e produtos de limpeza
- Pesquisa de produtos por nome e categoria
- Carrinho de compras no navegador
- Cadastro, login, perfil e encerramento de sessão
- Criação de pedidos com cálculo de valores no servidor
- Consulta de pedidos pelo cliente
- Área administrativa para cadastrar produtos e alterar o status dos pedidos
- Persistência dos dados em SQLite
- Documentação automática das rotas em Swagger UI

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Interface web | HTML5, CSS3 e JavaScript |
| API | Python 3.13, FastAPI |
| Servidor HTTP | Uvicorn |
| Banco de dados | SQLite |
| Gerenciamento do projeto | pyproject.toml e uv |
| Interface da API | Swagger UI em /docs |

## Pré-requisitos

- Python 3.13 recomendado
- git
- Navegador web moderno
- uv recomendado, mas não obrigatório

Para Windows com bloqueio do executável python.exe, o launcher py pode ser usado.

## Como rodar
### Servidor principal

Com uv:

uv run python backend/api.py
Ou, após ativar o ambiente virtual:

python backend/api.py
No Windows:

py backend/api.py
Depois, acesse:

- Site: http://127.0.0.1:8000
- Catálogo: http://127.0.0.1:8000/pages/produtos.html
- Documentação da API: http://127.0.0.1:8000/docs
- Documentação JSON: http://127.0.0.1:8000/openapi.json

Não abra os arquivos HTML diretamente pelo explorador. O servidor é necessário para disponibilizar a API, autenticação, carrinho e pedidos.

Para interromper o servidor, use Ctrl+C no terminal.

### Menu de terminal

O CRUD original também está disponível no terminal:

python backend/menu.py
## Contas disponíveis

Na primeira execução de um banco vazio, o sistema cria duas contas para testes.

### Administrador

- E-mail: admin@quitandaliro.local
- Senha: AdminLiro123
- Área administrativa: http://127.0.0.1:8000/pages/admin.html

O administrador pode cadastrar produtos e atualizar o status dos pedidos.

### Cliente

- E-mail: cliente@quitandaliro.local
- Senha: Cliente123

As senhas são credenciais locais de desenvolvimento. Em produção, devem ser alteradas e o sistema deve usar configuração segura de ambientes.

## Fluxo de uso

1. Abra o site pela URL local do servidor.
2. Consulte os produtos no catálogo.
3. Adicione itens ao carrinho.
4. Faça cadastro ou login.
5. Confirme o pedido na página de checkout.
6. Consulte o pedido em Meus pedidos.
7. Pague no caixa no momento da retirada.
8. Use a área administrativa para preparar o pedido e indicar quando ele estiver disponível ou retirado.

## Status dos pedidos

1. realizado — Pedido realizado
2. em_preparacao — Em preparação
3. aguardando_retirada — Aguardando retirada na loja
4. retirado — Pedido retirado
5. cancelado — Pedido cancelado

Não existe entrega em domicílio.

## Arquitetura

Navegador
   |
   | HTTP/JSON
   v
FastAPI + Uvicorn
   |
   +--> SQLite
   |
   +--> Frontend estático
O [frontend](frontend/) envia requisições às rotas /api usando os arquivos JavaScript. A API valida os dados, autentica usuários e executa as operações no banco. Os módulos [backend/banco.py](backend/banco.py), [backend/auth.py](backend/auth.py) e [backend/pedidos.py](backend/pedidos.py) concentram o acesso ao SQLite e às regras de negócio.

## Estrutura do repositório

`text
crud-quitanda-liro/
├── backend/
│   ├── api.py                 # Aplicação FastAPI e rotas HTTP
│   ├── auth.py                # Usuários, senhas e sessões
│   ├── banco.py               # Conexão SQLite e operações de produtos
│   ├── pedidos.py             # Criação e consulta de pedidos
│   ├── config.py              # Dados da loja, categorias e status
│   ├── menu.py                # CRUD disponível no terminal
│   ├── requirements.txt       # Dependências opcionais para pip
│   └── database/
│       ├── quitanda.db        # Banco local
│       └── MIGRACOES.md       # Histórico das alterações do banco
├── frontend/
│   ├── index.html             # Página inicial
│   ├── assets/                # Imagens e ícones
│   ├── css/                   # Estilos do site
│   ├── js/                    # Comunicação com API e comportamento das páginas
│   └── pages/                 # Páginas de login, carrinho, pedidos e administração
├── src/quitanda_liro/
│   └── init.py            # Entrada do pacote distribuível
├── pyproject.toml             # Metadados e dependências do projeto
├── uv.lock                    # Dependências resolvidas pelo uv
└── README.md                  # Manual e apresentação do projeto

## Banco de dados

O banco oficial é criado ou reutilizado em [backend/database/quitanda.db](backend/database/quitanda.db).

Na primeira execução:

1. O sistema procura pelo banco oficial.
2. Caso ele não exista, tenta copiar um arquivo legado `quitanda.db` da raiz.
3. Cria as tabelas necessárias caso ainda não existam.
4. Mantém os produtos já cadastrados.
5. Cria o catálogo inicial apenas quando não houver produtos.
6. Cria o administrador e o cliente padrão quando não houver usuários.

O modelo inclui tabelas para produtos, usuários, sessões, pedidos, itens de pedidos e histórico de migrações. Consulte [backend/database/MIGRACOES.md](backend/database/MIGRACOES.md) para o detalhamento.

## Documentação

A documentação interativa do servidor permite consultar e testar os endpoints, parâmetros e modelos da API diretamente no navegador.

### Como abrir o Swagger UI

1. Inicie o servidor principal:

   
bash
   uv run python backend/api.py
  

2. Aguarde aparecer no terminal a mensagem informando que o Uvicorn está executando em `http://127.0.0.1:8000`.
3. Abra o navegador.
4. Digite o seguinte endereço na barra de endereços:

   
text
   http://127.0.0.1:8000/docs
  

5. Pressione `Enter`.

O Swagger UI deve aparecer com os grupos de rotas disponíveis, como **loja**, **produtos**, **usuários** e **pedidos**. Para testar uma rota:

1. Expanda o grupo e a rota desejada.
2. Clique em **Try it out**.
3. Preencha os parâmetros ou o corpo da requisição, quando necessário.
4. Clique em **Execute**.
5. Consulte a resposta, o código HTTP e o exemplo retornado pela API.

Para testar rotas protegidas, faça login antes e informe o token recebido no campo **Authorize** do Swagger UI.

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json
- Migrações do banco: [backend/database/MIGRACOES.md](backend/database/MIGRACOES.md)

Principais grupos de rotas:

| Grupo | Exemplos |
|---|---|
| Loja | `GET /api/loja` |
| Produtos | `GET /api/produtos`, `POST /api/produtos` |
| Usuários | `POST /api/usuarios`, `POST /api/login`, `POST /api/logout` |
| Perfil | `GET /api/me`, `PUT /api/me` |
| Pedidos | `GET /api/pedidos`, `POST /api/pedidos` |
| Administração | `GET /api/admin/pedidos`, `PATCH /api/pedidos/{id}/status` |

As operações administrativas exigem uma sessão autenticada com perfil `admin`.

## Dicas de desenvolvimento

Com o servidor ativo, alterações em arquivos Python normalmente exigem reiniciar o processo. Para revisar a sintaxe do backend:

bash
uv run python -m compileall -q backend src

Para executar diretamente pela aplicação declarada no projeto:

bash
uv run quitanda-liro
`

## Limitações conhecidas
- O servidor usa SQLite, adequado para desenvolvimento e aplicações locais de baixo volume.
- A aplicação não processa pagamentos online.
- A aplicação não realiza entrega em domicílio.
- O projeto não inclui implantação em nuvem ou Docker.
- Os dados de loja exibidos em backend/config.py são exemplos e devem ser substituídos antes de uso real.
