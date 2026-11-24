# Quitanda da Liro

Sistema web de compras com retirada presencial. O cliente consulta produtos, monta o carrinhos de compras, confirma o pedido na loja e acompanha o status até a retirada. Não há entrega em domicílio nem pagamento online.

## O que já existia // rever

- CRUD de produtos em Python (`banco.py` / `menu.py`)
- Tabela `produtos`: `id`, `nome`, `categoria`, `preco`, `unidade_medida`
- Banco SQLite em `backend/database/quitanda.db`, preservando o arquivo legado
  quando encontrado na raiz

## O que foi feito //// rever essa parte e retirar/alterar

- Correção do texto do menu (`Produto atualizado` / `Produto nao encontrado`)
- Função `buscar_produtos()` para pesquisa por nome e categoria, mantendo `buscar_produto(id)`
- `UPDATE` de produto sem vírgula inválida antes do `WHERE`
- Ampliação do mesmo SQLite com usuários, sessões, pedidos e itens
- API REST em Python (`backend/api.py`) servindo JSON e o front-end
- Site em HTML, CSS e JavaScript puros

Endereço, horário e telefone **não estavam no projeto original**. Ficam em `backend/config.py` para a tela de retirada.

## Como executar

Python 3.13 (ou 3.10+). Sem bibliotecas extras.

```bash
cd backend
python api.py
```

No Windows, se `python.exe` estiver bloqueado pela política de Controle de
Aplicativos, use o launcher do Python:

```bash
cd backend
py api.py
```

Se `py api.py` também for bloqueado, consulte o administrador do computador.
Não desative o Controle de Aplicativos ou o Defender sem autorização.

Abra http://127.0.0.1:8000

Não abra `frontend/index.html` diretamente pelo explorador de arquivos: as
páginas precisam ser acessadas pelo servidor Python para que a API, o login,
o carrinho e os pedidos funcionem corretamente.

Na primeira execução o sistema:

1. Usa `backend/database/quitanda.db`; se ele não existir, copia o `quitanda.db`
   legado da raiz antes de criar um banco novo
2. Mantém a tabela `produtos`
3. Cria as tabelas novas
4. Se não houver produtos, carrega um catálogo inicial
5. Cria o administrador padrão

Menu de terminal (CRUD original):

```bash
python menu.py
```

ou:

```bash
cd backend
python menu.py
```

## Conta administrativa

- E-mail: `admin@quitandaliro.local`
- Senha: `AdminLiro123`

Use essa conta em `/pages/admin.html` para cadastrar produtos e atualizar o status dos pedidos.

## Conta de cliente para testes

- E-mail: `cliente@quitandaliro.local`
- Senha: `Cliente123`

## Status dos pedidos

1. Pedido realizado
2. Em preparação
3. Aguardando retirada na loja
4. Pedido retirado
5. Cancelado (quando aplicável)

Não existe status de entrega em domicílio.

## Pagamento

PIX, cartão ou dinheiro **somente no caixa da loja**, na retirada. O site não coleta dados bancários.

## Estrutura

```text
crud-quitanda-liro/
├── banco.py / menu.py     # atalhos do CRUD original
├── backend/
│   ├── api.py
│   ├── banco.py
│   ├── menu.py
│   ├── auth.py
│   ├── pedidos.py
│   ├── config.py
│   └── database/
└── frontend/
```

Alterações do banco: `backend/database/MIGRACOES.md`.
