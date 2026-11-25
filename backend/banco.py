"""Operações CRUD de produtos e inicialização do SQLite existente."""

from __future__ import annotations

import sqlite3
import sys
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import ADMIN_PADRAO, CATEGORIAS

RAIZ = BASE_DIR.parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

ARQUIVO_BANCO_PATH = DATABASE_DIR / "quitanda.db"
BANCO_LEGADO = RAIZ / "quitanda.db"

# Mantém os dados do arquivo legado na primeira execução, mas usa um único local oficial.
if not ARQUIVO_BANCO_PATH.exists() and BANCO_LEGADO.exists():
    shutil.copy2(BANCO_LEGADO, ARQUIVO_BANCO_PATH)

ARQUIVO_BANCO = str(ARQUIVO_BANCO_PATH)


def conectar():
    conexao = sqlite3.connect(ARQUIVO_BANCO)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_tabela():
    conexao = conectar()
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nome   TEXT NOT NULL,
            categoria   TEXT NOT NULL,
            preco REAL NOT NULL,
            unidade_medida  TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1
        )
        """)
    conexao.commit()
    conexao.close()


def _colunas(conexao, tabela: str) -> set[str]:
    linhas = conexao.execute(f"PRAGMA table_info({tabela})").fetchall()
    return {linha["name"] for linha in linhas}


def _registrar_migracao(conexao, descricao: str) -> None:
    conexao.execute(
        "INSERT INTO schema_migracoes (descricao, aplicado_em) VALUES (?, ?)",
        (descricao, datetime.now(timezone.utc).isoformat()),
    )


def inicializar_banco() -> None:
    """Amplia o banco existente sem apagar produtos."""
    criar_tabela()
    conexao = conectar()
    try:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS schema_migracoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT NOT NULL,
                aplicado_em TEXT NOT NULL
            )
            """)

        colunas_produto = _colunas(conexao, "produtos")
        if "descricao" not in colunas_produto:
            conexao.execute("ALTER TABLE produtos ADD COLUMN descricao TEXT")
            _registrar_migracao(conexao, "produtos: coluna descricao")
        if "imagem" not in colunas_produto:
            conexao.execute("ALTER TABLE produtos ADD COLUMN imagem TEXT")
            _registrar_migracao(conexao, "produtos: coluna imagem")
        if "ativo" not in colunas_produto:
            conexao.execute(
                "ALTER TABLE produtos ADD COLUMN ativo INTEGER NOT NULL DEFAULT 1"
            )
            _registrar_migracao(conexao, "produtos: coluna ativo")

        conexao.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_completo TEXT NOT NULL,
                cpf TEXT NOT NULL UNIQUE,
                celular TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                perfil TEXT NOT NULL DEFAULT 'cliente',
                criado_em TEXT NOT NULL
            )
            """)
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS sessoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                criado_em TEXT NOT NULL,
                expira_em TEXT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
            """)
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                data_realizacao TEXT NOT NULL,
                valor_total REAL NOT NULL,
                status TEXT NOT NULL,
                chave_idempotencia TEXT UNIQUE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
            """)
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS itens_pedido (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                produto_id INTEGER NOT NULL,
                quantidade REAL NOT NULL,
                preco_unitario REAL NOT NULL,
                subtotal REAL NOT NULL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
                FOREIGN KEY (produto_id) REFERENCES produtos(id)
            )
            """)

        existentes = {
            linha["descricao"]
            for linha in conexao.execute(
                "SELECT descricao FROM schema_migracoes"
            ).fetchall()
        }
        if "produtos: compatibilidade de imagens e categorias" not in existentes:
            _compatibilizar_catalogo(conexao)
            _registrar_migracao(
                conexao, "produtos: compatibilidade de imagens e categorias"
            )
        if "produtos: categorias padronizadas" not in existentes:
            _padronizar_categorias(conexao)
            _registrar_migracao(conexao, "produtos: categorias padronizadas")
        for descricao in (
            "tabela usuarios",
            "tabela sessoes",
            "tabela pedidos",
            "tabela itens_pedido",
        ):
            if descricao not in existentes:
                _registrar_migracao(conexao, descricao)

        _remover_produtos_inativos_svg(conexao)

        if "catalogo inicial: produtos ativos sincronizados" not in existentes:
            _popular_produtos_iniciais(conexao)
            _registrar_migracao(
                conexao,
                "catalogo inicial: produtos ativos sincronizados",
            )
        else:
            _popular_produtos_iniciais(conexao)

        if conexao.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"] == 0:
            from auth import hash_senha

            agora = datetime.now(timezone.utc).isoformat()
            conexao.execute(
                """
                INSERT INTO usuarios
                    (nome_completo, cpf, celular, email, senha_hash, perfil, criado_em)
                VALUES (?, ?, ?, ?, ?, 'admin', ?)
                """,
                (
                    ADMIN_PADRAO["nome_completo"],
                    ADMIN_PADRAO["cpf"],
                    ADMIN_PADRAO["celular"],
                    ADMIN_PADRAO["email"],
                    hash_senha(ADMIN_PADRAO["senha"]),
                    agora,
                ),
            )
            _registrar_migracao(conexao, "usuario administrador inicial")

        conexao.commit()
    finally:
        conexao.close()


def _compatibilizar_catalogo(conexao) -> None:
    imagens = (
        ("banana", "banana.svg"),
        ("água", "agua.svg"),
        ("agua", "agua.svg"),
        ("refrigerante", "refri.svg"),
        ("maçã", "maca.svg"),
        ("maca", "maca.svg"),
        ("tomate", "tomate.svg"),
        ("laranja", "laranja.svg"),
        ("limão", "limao.svg"),
        ("limao", "limao.svg"),
        ("mamão", "mamao.svg"),
        ("mamao", "mamao.svg"),
    )
    for termo, imagem in imagens:
        conexao.execute(
            """
            UPDATE produtos
            SET imagem = ?
            WHERE (imagem IS NULL OR imagem = '')
              AND LOWER(nome) LIKE ?
            """,
            (imagem, f"%{termo}%"),
        )
    conexao.execute("""
        UPDATE produtos
        SET imagem = 'cesta.svg'
        WHERE imagem IS NULL OR imagem = ''
        """)
    conexao.execute(
        "UPDATE produtos SET categoria = 'Bebidas' WHERE LOWER(categoria) = 'bebida'"
    )


def normalizar_categoria(categoria: str) -> str:
    chave = "".join(
        caractere
        for caractere in unicodedata.normalize(
            "NFD", str(categoria or "").strip().lower()
        )
        if unicodedata.category(caractere) != "Mn"
    )
    categorias = {
        "hortifruti": "Hortifruti",
        "bebida": "Bebidas",
        "bebidas": "Bebidas",
        "limpeza": "Limpeza",
    }
    try:
        return categorias[chave]
    except KeyError as exc:
        raise ValueError(
            "Categoria inválida. Use Hortifruti, Bebidas ou Limpeza."
        ) from exc


def _padronizar_categorias(conexao) -> None:
    for categoria_antiga, categoria_nova in (
        ("hortifrúti", "Hortifruti"),
        ("hortifruti", "Hortifruti"),
        ("bebida", "Bebidas"),
        ("bebidas", "Bebidas"),
        ("limpeza", "Limpeza"),
    ):
        conexao.execute(
            "UPDATE produtos SET categoria = ? WHERE LOWER(categoria) = ?",
            (categoria_nova, categoria_antiga),
        )


def _remover_produtos_inativos_svg(conexao) -> None:
    referenciados = conexao.execute("""
        SELECT p.id
        FROM produtos p
        WHERE p.ativo = 0
          AND LOWER(COALESCE(p.imagem, '')) LIKE '%.svg'
          AND EXISTS (
              SELECT 1 FROM itens_pedido i WHERE i.produto_id = p.id
          )
        """).fetchall()
    if referenciados:
        ids = ", ".join(str(linha["id"]) for linha in referenciados)
        raise ValueError(
            "Não é possível excluir produtos inativos com SVG ligados a pedidos: " + ids
        )
    conexao.execute("""
        DELETE FROM produtos
        WHERE ativo = 0
          AND LOWER(COALESCE(imagem, '')) LIKE '%.svg'
        """)


def _popular_produtos_iniciais(conexao) -> None:
    itens = [
        (
            "Banana prata",
            "Hortifruti",
            0.90,
            "200g",
            "Banana de polpa macia e sabor adocicado, ideal para consumo in natura e vitaminas.",
            "banana-prata.JPEG",
        ),
        (
            "Maçã gala",
            "Hortifruti",
            1.50,
            "200g",
            "Maçã de casca fina, polpa crocante e sabor levemente adocicado.",
            "maça-gala.JPEG",
        ),
        (
            "Laranja pera",
            "Hortifruti",
            0.88,
            "200g",
            "Laranja de sabor equilibrado e bastante suco, indicada para consumo e preparo de sucos naturais.",
            "laranja-pera.JPEG",
        ),
        (
            "Tomate italiano",
            "Hortifruti",
            1.85,
            "200g",
            "Tomate de formato alongado e polpa firme, ideal para molhos, refogados e saladas.",
            "tomate-italiano.jpg",
        ),
        (
            "Alface crespa",
            "Hortifruti",
            3.50,
            "unidade",
            "Folhas verdes e crocantes, indicada para saladas, sanduíches e acompanhamentos.",
            "alface-crespo.JPEG",
        ),
        (
            "Cenoura",
            "Hortifruti",
            1.30,
            "200g",
            "Raiz de textura firme e sabor levemente adocicado, ideal para saladas, sopas e refogados.",
            "cenoura.JPEG",
        ),
        (
            "Batata inglesa",
            "Hortifruti",
            1.75,
            "200g",
            "Batata de polpa macia após o cozimento, indicada para purês, assados, sopas e frituras.",
            "batata-inglesa.JPEG",
        ),
        (
            "Cebola",
            "Hortifruti",
            1.96,
            "200g",
            "Ingrediente versátil de sabor marcante, utilizado no preparo de temperos, molhos e refogados.",
            "cebola.JPEG",
        ),
        (
            "Limão tahiti",
            "Hortifruti",
            2.00,
            "200g",
            "Limão de sabor cítrico e suculento, ideal para sucos, temperos e bebidas.",
            "limao-tahiti.JPEG",
        ),
        (
            "Mamão formosa",
            "Hortifruti",
            5.60,
            "500g",
            "Fruta de polpa macia e sabor adocicado, ideal para consumo no café da manhã e sobremesas.",
            "mamao-formosa.jpg",
        ),
        (
            "Água mineral Indaiá 500 ml",
            "Bebidas",
            2.50,
            "unidade",
            "Água mineral natural sem gás, em embalagem prática de 500 ml para consumo diário.",
            "agua-mineral-500ml.JPEG",
        ),
        (
            "Suco de laranja Valle 1 L",
            "Bebidas",
            8.90,
            "1L",
            "Bebida à base de laranja, com sabor cítrico e refrescante, pronta para beber.",
            "suco-de-laranja-1L.jpeg",
        ),
        (
            "Refrigerante Guaraná 2 L",
            "Bebidas",
            9.90,
            "2L",
            "Refrigerante sabor guaraná, gaseificado e ideal para acompanhar refeições e lanches.",
            "refrigerante-2L.jpg",
        ),
        (
            "Água de coco Puro Coco 1 L",
            "Bebidas",
            7.50,
            "1L",
            "Bebida de água de coco, com sabor suave e refrescante, ideal para consumir gelada.",
            "agua-de-coco-1L.JPEG",
        ),
        (
            "Suco de uva Valle 1 L",
            "Bebidas",
            8.90,
            "1L",
            "Bebida de uva integral, com sabor intenso da fruta e sem adição de açúcar, conforme informações da marca.",
            "suco-de-uva-1L.jpg",
        ),
        (
            "Detergente Ype 500 ml",
            "Limpeza",
            3.20,
            "500ml",
            "Detergente líquido neutro indicado para lavar louças, removendo resíduos de gordura e alimentos.",
            "detergente-500ml.webp",
        ),
        (
            "Água sanitária Brilux 1 L",
            "Limpeza",
            4.80,
            "1L",
            "Produto à base de cloro indicado para alvejamento e higienização de superfícies, conforme as instruções do rótulo.",
            "agua-sanitaria-1L.jpg",
        ),
        (
            "Sabão em barra Bem-te-ve",
            "Limpeza",
            2.90,
            "unidade",
            "Sabão em barra indicado para a lavagem de roupas e limpeza de utensílios domésticos.",
            "sabao-em-barra.webp",
        ),
        (
            "Esponja dupla face Scotch-Brite",
            "Limpeza",
            1.80,
            "unidade",
            "Esponja com lado macio para limpeza delicada e lado abrasivo para remover sujeiras mais difíceis.",
            "esponja-dupla-face.webp",
        ),
        (
            "Desinfetante Suprema 2 L",
            "Limpeza",
            8.50,
            "2L",
            "Desinfetante líquido para limpeza de pisos e superfícies laváveis, deixando aroma agradável no ambiente.",
            "desinfetante-2L.webp",
        ),
    ]

    def chave_nome(nome: str) -> str:
        normalizado = unicodedata.normalize("NFKD", nome.strip().lower())
        return "".join(
            caractere
            for caractere in normalizado
            if unicodedata.category(caractere) != "Mn"
        )

    aliases = {
        chave_nome("Água mineral Indaiá 500 ml"): (chave_nome("Água mineral 500 ml"),),
        chave_nome("Suco de laranja Valle 1 L"): (chave_nome("Suco de laranja 1 L"),),
        chave_nome("Refrigerante Guaraná 2 L"): (
            chave_nome("Refrigerante 2 L"),
            chave_nome("Refrigerante"),
        ),
        chave_nome("Água de coco Puro Coco 1 L"): (chave_nome("Água de coco 1 L"),),
        chave_nome("Suco de uva Valle 1 L"): (chave_nome("Suco de uva 1 L"),),
        chave_nome("Detergente Ype 500 ml"): (chave_nome("Detergente 500 ml"),),
        chave_nome("Água sanitária Brilux 1 L"): (chave_nome("Água sanitária 1 L"),),
        chave_nome("Sabão em barra Bem-te-ve"): (chave_nome("Sabão em barra"),),
        chave_nome("Esponja dupla face Scotch-Brite"): (
            chave_nome("Esponja dupla face"),
        ),
        chave_nome("Desinfetante Suprema 2 L"): (chave_nome("Desinfetante 2 L"),),
    }

    linhas = conexao.execute(
        "SELECT id, nome FROM produtos ORDER BY ativo DESC, id"
    ).fetchall()
    existentes_por_nome = {}
    for linha in linhas:
        existentes_por_nome.setdefault(chave_nome(linha["nome"]), linha["id"])

    for nome, categoria, preco, unidade, descricao, imagem in itens:
        chave = chave_nome(nome)
        chaves_equivalentes = {chave, *aliases.get(chave, ())}
        produto_id = existentes_por_nome.get(chave)
        if produto_id is None:
            for alias in aliases.get(chave, ()):
                produto_id = existentes_por_nome.get(alias)
                if produto_id is not None:
                    break

        if produto_id is not None:
            conexao.execute(
                """
                UPDATE produtos
                SET nome = ?, categoria = ?, preco = ?, unidade_medida = ?,
                    descricao = ?, imagem = ?, ativo = 1
                WHERE id = ?
                """,
                (
                    nome,
                    categoria,
                    preco,
                    unidade,
                    descricao,
                    imagem,
                    produto_id,
                ),
            )
            duplicados = conexao.execute(
                "SELECT id, nome FROM produtos WHERE id <> ?",
                (produto_id,),
            ).fetchall()
            for duplicado in duplicados:
                if chave_nome(duplicado["nome"]) in chaves_equivalentes:
                    conexao.execute(
                        "UPDATE produtos SET ativo = 0 WHERE id = ?",
                        (duplicado["id"],),
                    )
            for chave_equivalente in chaves_equivalentes:
                existentes_por_nome[chave_equivalente] = produto_id
        else:
            cursor = conexao.execute(
                """
                INSERT INTO produtos
                    (nome, categoria, preco, unidade_medida, descricao, imagem, ativo)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (nome, categoria, preco, unidade, descricao, imagem),
            )
            for chave_equivalente in chaves_equivalentes:
                existentes_por_nome[chave_equivalente] = cursor.lastrowid


def inserir_produto(
    nome: str,
    categoria: str,
    preco: str | float,
    unidade_medida: str,
    descricao: str | None = None,
    imagem: str | None = None,
) -> int:
    categoria = normalizar_categoria(categoria)
    conexao = conectar()
    cursor = conexao.execute(
        """
        INSERT INTO produtos (nome, categoria, preco, unidade_medida, descricao, imagem)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (nome, categoria, float(preco), unidade_medida, descricao, imagem),
    )
    conexao.commit()
    novo_id = cursor.lastrowid
    conexao.close()
    return novo_id


def listar_produtos() -> list[dict]:
    conexao = conectar()
    linhas = conexao.execute(
        "SELECT * FROM produtos WHERE ativo = 1 ORDER BY categoria, nome"
    ).fetchall()
    conexao.close()
    return [dict(linha) for linha in linhas]


def buscar_produto(produto_id: int) -> dict | None:
    conexao = conectar()
    linha = conexao.execute(
        "SELECT * FROM produtos WHERE id = ? AND ativo = 1", (produto_id,)
    ).fetchone()
    conexao.close()
    if linha is None:
        return None
    return dict(linha)


def buscar_produtos(
    nome: str | None = None, categoria: str | None = None
) -> list[dict]:
    """Pesquisa produtos por nome e/ou categoria. Alias pedido pelo projeto."""
    conexao = conectar()
    sql = "SELECT * FROM produtos WHERE ativo = 1"
    params: list = []
    if nome:
        sql += " AND LOWER(nome) LIKE ?"
        params.append(f"%{nome.strip().lower()}%")
    if categoria:
        categoria = normalizar_categoria(categoria)
        sql += " AND LOWER(categoria) = ?"
        params.append(categoria.strip().lower())
    sql += " ORDER BY categoria, nome"
    linhas = conexao.execute(sql, params).fetchall()
    conexao.close()
    return [dict(linha) for linha in linhas]


def atualizar_produto(
    produto_id: int,
    nome: str,
    categoria: str,
    preco: str | float,
    unidade_medida: str,
    descricao: str | None = None,
    imagem: str | None = None,
) -> bool:
    categoria = normalizar_categoria(categoria)
    conexao = conectar()
    atual = conexao.execute(
        "SELECT * FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()
    if atual is None:
        conexao.close()
        return False
    dados = dict(atual)
    cursor = conexao.execute(
        """
        UPDATE produtos
        SET nome = ?, categoria = ?, preco = ?, unidade_medida = ?, descricao = ?, imagem = ?
        WHERE id = ?
        """,
        (
            nome,
            categoria,
            float(preco),
            unidade_medida,
            descricao if descricao is not None else dados.get("descricao"),
            imagem if imagem is not None else dados.get("imagem"),
            produto_id,
        ),
    )
    conexao.commit()
    alterou = cursor.rowcount > 0
    conexao.close()
    return alterou


def remover_produto(produto_id: int) -> bool:
    conexao = conectar()
    cursor = conexao.execute(
        "UPDATE produtos SET ativo = 0 WHERE id = ? AND ativo = 1",
        (produto_id,),
    )
    conexao.commit()
    removeu = cursor.rowcount > 0
    conexao.close()
    return removeu


def categorias_validas() -> list[str]:
    return list(CATEGORIAS)
