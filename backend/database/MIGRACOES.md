# Alterações no banco `quitanda.db`

O arquivo original `quitanda.db` não estava versionado (constava no `.gitignore`).
A tabela `produtos` foi recriada com os mesmos campos do `backend/banco.py` inicial:

- `id`, `nome`, `categoria`, `preco`, `unidade_medida`

Ampliações controladas (sem substituir a tabela de produtos):

1. Colunas em `produtos`: `descricao`, `imagem`, `ativo`
2. Tabela `usuarios` (cadastro, login e perfil)
3. Tabela `sessoes` (tokens de autenticação)
4. Tabela `pedidos`
5. Tabela `itens_pedido`
6. Tabela `schema_migracoes` (histórico das alterações)

Relacionamentos:

- `sessoes.usuario_id` → `usuarios.id`
- `pedidos.usuario_id` → `usuarios.id`
- `itens_pedido.pedido_id` → `pedidos.id`
- `itens_pedido.produto_id` → `produtos.id`

Produtos excluídos ficam com `ativo = 0`: não aparecem no catálogo nem podem ser
adicionados a novos pedidos, mas continuam disponíveis para os pedidos antigos.

Na inicialização, o catálogo inicial é sincronizado pelo nome: produtos existentes
do catálogo são reativados e os itens iniciais ausentes são inseridos como ativos.
Itens cadastrados pelo usuário continuam preservados e não são removidos.

O arquivo oficial fica em `backend/database/quitanda.db`. Na primeira execução,
se o banco legado `quitanda.db` existir na raiz e o arquivo oficial ainda não
existir, ele é copiado para esse diretório sem apagar os dados.
A carga inicial de produtos só ocorre quando a tabela está vazia.
