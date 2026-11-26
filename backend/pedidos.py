"""Pedidos e itens, com transação e validação de preços no servidor."""

from __future__ import annotations

from datetime import datetime, timezone

import banco
from config import STATUS_LABEL, STATUS_ORDEM

STATUS_VALIDOS = set(STATUS_LABEL)


def criar_pedido(usuario_id: int, itens_entrada: list[dict], chave_idempotencia: str | None) -> dict:
    if not itens_entrada:
        raise ValueError("O pedido precisa de pelo menos um item.")

    conexao = banco.conectar()
    try:
        if chave_idempotencia:
            existente = conexao.execute(
                "SELECT id FROM pedidos WHERE chave_idempotencia = ?",
                (chave_idempotencia,),
            ).fetchone()
            if existente:
                return detalhar_pedido(existente["id"], conexao)

        itens_gravar = []
        total = 0.0
        for bruto in itens_entrada:
            try:
                produto_id = int(bruto.get("produto_id"))
                quantidade = float(bruto.get("quantidade"))
            except (TypeError, ValueError):
                raise ValueError("Item inválido: informe produto_id e quantidade numéricos.") from None
            if quantidade <= 0:
                raise ValueError("A quantidade deve ser maior que zero.")
            produto = conexao.execute(
                "SELECT * FROM produtos WHERE id = ? AND ativo = 1", (produto_id,)
            ).fetchone()
            if produto is None:
                raise ValueError(f"Produto {produto_id} não encontrado.")
            preco = float(produto["preco"])
            subtotal = round(preco * quantidade, 2)
            total += subtotal
            itens_gravar.append(
                {
                    "produto_id": produto_id,
                    "quantidade": quantidade,
                    "preco_unitario": preco,
                    "subtotal": subtotal,
                }
            )

        total = round(total, 2)
        agora = datetime.now(timezone.utc).isoformat()
        cursor = conexao.execute(
            """
            INSERT INTO pedidos
                (usuario_id, data_realizacao, valor_total, status, chave_idempotencia)
            VALUES (?, ?, ?, 'realizado', ?)
            """,
            (usuario_id, agora, total, chave_idempotencia),
        )
        pedido_id = cursor.lastrowid
        for item in itens_gravar:
            conexao.execute(
                """
                INSERT INTO itens_pedido
                    (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    pedido_id,
                    item["produto_id"],
                    item["quantidade"],
                    item["preco_unitario"],
                    item["subtotal"],
                ),
            )
        conexao.commit()
        return detalhar_pedido(pedido_id, conexao)
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def _montar_pedido(linha, conexao) -> dict:
    usuario = conexao.execute(
        "SELECT nome_completo, email FROM usuarios WHERE id = ?",
        (linha["usuario_id"],),
    ).fetchone()
    itens = conexao.execute(
        """
        SELECT i.id, i.produto_id, i.quantidade, i.preco_unitario, i.subtotal,
               p.nome, p.categoria, p.unidade_medida, p.imagem
        FROM itens_pedido i
        JOIN produtos p ON p.id = i.produto_id
        WHERE i.pedido_id = ?
        ORDER BY i.id
        """,
        (linha["id"],),
    ).fetchall()
    status = linha["status"]
    return {
        "id": linha["id"],
        "usuario_id": linha["usuario_id"],
        "cliente_nome": usuario["nome_completo"] if usuario else "Cliente não encontrado",
        "cliente_email": usuario["email"] if usuario else "",
        "data_realizacao": linha["data_realizacao"],
        "valor_total": linha["valor_total"],
        "status": status,
        "status_label": STATUS_LABEL.get(status, status),
        "pagamento": "PIX, cartão ou dinheiro na retirada",
        "recebimento": "Retirada na loja",
        "itens": [dict(item) for item in itens],
        "etapas": _etapas(status),
    }


def _etapas(status: str) -> list[dict]:
    if status == "cancelado":
        return [{"chave": "cancelado", "label": "Cancelado", "estado": "atual"}]
    encontrado = False
    etapas = []
    for chave in STATUS_ORDEM:
        if chave == status and not encontrado:
            estado = "atual"
            encontrado = True
        elif not encontrado:
            estado = "concluida"
        else:
            estado = "pendente"
        etapas.append({"chave": chave, "label": STATUS_LABEL[chave], "estado": estado})
    return etapas


def detalhar_pedido(pedido_id: int, conexao=None) -> dict:
    propria = conexao is None
    if propria:
        conexao = banco.conectar()
    try:
        linha = conexao.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
        if linha is None:
            raise ValueError("Pedido não encontrado.")
        return _montar_pedido(linha, conexao)
    finally:
        if propria:
            conexao.close()


def listar_pedidos_usuario(usuario_id: int) -> list[dict]:
    conexao = banco.conectar()
    linhas = conexao.execute(
        "SELECT * FROM pedidos WHERE usuario_id = ? ORDER BY id DESC",
        (usuario_id,),
    ).fetchall()
    pedidos = [_montar_pedido(linha, conexao) for linha in linhas]
    conexao.close()
    return pedidos


def listar_todos_pedidos() -> list[dict]:
    conexao = banco.conectar()
    linhas = conexao.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
    pedidos = [_montar_pedido(linha, conexao) for linha in linhas]
    conexao.close()
    return pedidos


def atualizar_status(pedido_id: int, novo_status: str) -> dict:
    if novo_status not in STATUS_VALIDOS:
        raise ValueError("Status inválido.")
    conexao = banco.conectar()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        atual = conexao.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
        if atual is None:
            raise ValueError("Pedido não encontrado.")
        if atual["status"] == "cancelado":
            raise ValueError("Pedido cancelado não pode ter o status alterado.")
        if atual["status"] == "retirado" and novo_status == "cancelado":
            raise ValueError("Pedido já retirado não pode ser cancelado.")
        conexao.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
        conexao.commit()
        return detalhar_pedido(pedido_id, conexao)
    finally:
        conexao.close()


def cancelar_pedido(pedido_id: int, usuario_id: int) -> dict:
    conexao = banco.conectar()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        atual = conexao.execute(
            "SELECT usuario_id, status FROM pedidos WHERE id = ?",
            (pedido_id,),
        ).fetchone()
        if atual is None:
            raise LookupError("Pedido não encontrado.")
        if atual["usuario_id"] != usuario_id:
            raise PermissionError("Você só pode cancelar os seus pedidos.")
        if atual["status"] == "cancelado":
            raise ValueError("Este pedido já foi cancelado.")
        if atual["status"] == "retirado":
            raise ValueError("Pedido já retirado não pode ser cancelado.")

        conexao.execute(
            "UPDATE pedidos SET status = 'cancelado' WHERE id = ? AND usuario_id = ?",
            (pedido_id, usuario_id),
        )
        conexao.commit()
        return detalhar_pedido(pedido_id, conexao)
    finally:
        conexao.close()
