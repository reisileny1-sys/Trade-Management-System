"""Autenticação, hash de senha e sessões."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

import banco

ITERACOES = 120_000
DURACAO_SESSAO = timedelta(days=7)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_senha(senha: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    derivado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), ITERACOES)
    return f"{salt}${derivado.hex()}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        salt, _ = senha_hash.split("$", 1)
    except ValueError:
        return False
    candidato = hash_senha(senha, salt)
    return hmac.compare_digest(candidato, senha_hash)


def normalizar_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", cpf or "")


def normalizar_celular(celular: str) -> str:
    return re.sub(r"\D", "", celular or "")


def cpf_valido(cpf: str) -> bool:
    numeros = normalizar_cpf(cpf)
    if len(numeros) != 11 or numeros == numeros[0] * 11:
        return False
    def digito(base: str, peso_inicial: int) -> str:
        soma = sum(int(d) * peso for d, peso in zip(base, range(peso_inicial, 1, -1)))
        resto = (soma * 10) % 11
        return "0" if resto == 10 else str(resto)
    d1 = digito(numeros[:9], 10)
    d2 = digito(numeros[:9] + d1, 11)
    return numeros[-2:] == d1 + d2


def email_valido(email: str) -> bool:
    return bool(EMAIL_RE.match((email or "").strip().lower()))


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def criar_usuario(
    nome_completo: str,
    cpf: str,
    celular: str,
    email: str,
    senha: str,
    perfil: str = "cliente",
) -> dict:
    cpf_n = normalizar_cpf(cpf)
    email_n = email.strip().lower()
    conexao = banco.conectar()
    try:
        existe = conexao.execute(
            "SELECT id FROM usuarios WHERE cpf = ? OR email = ?",
            (cpf_n, email_n),
        ).fetchone()
        if existe:
            raise ValueError("CPF ou e-mail já cadastrado.")
        cursor = conexao.execute(
            """
            INSERT INTO usuarios
                (nome_completo, cpf, celular, email, senha_hash, perfil, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome_completo.strip(),
                cpf_n,
                normalizar_celular(celular),
                email_n,
                hash_senha(senha),
                perfil,
                _agora().isoformat(),
            ),
        )
        conexao.commit()
        return obter_usuario(cursor.lastrowid)
    finally:
        conexao.close()


def obter_usuario(usuario_id: int) -> dict | None:
    conexao = banco.conectar()
    linha = conexao.execute(
        "SELECT id, nome_completo, cpf, celular, email, perfil, criado_em FROM usuarios WHERE id = ?",
        (usuario_id,),
    ).fetchone()
    conexao.close()
    return dict(linha) if linha else None


def autenticar(email: str, senha: str) -> dict | None:
    conexao = banco.conectar()
    linha = conexao.execute(
        "SELECT * FROM usuarios WHERE email = ?",
        (email.strip().lower(),),
    ).fetchone()
    conexao.close()
    if linha is None or not verificar_senha(senha, linha["senha_hash"]):
        return None
    return obter_usuario(linha["id"])


def criar_sessao(usuario_id: int) -> str:
    token = secrets.token_urlsafe(32)
    agora = _agora()
    conexao = banco.conectar()
    conexao.execute(
        "INSERT INTO sessoes (usuario_id, token, criado_em, expira_em) VALUES (?, ?, ?, ?)",
        (usuario_id, token, agora.isoformat(), (agora + DURACAO_SESSAO).isoformat()),
    )
    conexao.commit()
    conexao.close()
    return token


def usuario_por_token(token: str | None) -> dict | None:
    if not token:
        return None
    conexao = banco.conectar()
    linha = conexao.execute(
        """
        SELECT u.id, u.nome_completo, u.cpf, u.celular, u.email, u.perfil, u.criado_em, s.expira_em
        FROM sessoes s
        JOIN usuarios u ON u.id = s.usuario_id
        WHERE s.token = ?
        """,
        (token,),
    ).fetchone()
    if linha is None:
        conexao.close()
        return None
    expira = datetime.fromisoformat(linha["expira_em"])
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    if expira < _agora():
        conexao.execute("DELETE FROM sessoes WHERE token = ?", (token,))
        conexao.commit()
        conexao.close()
        return None
    conexao.close()
    dados = dict(linha)
    dados.pop("expira_em", None)
    return dados


def encerrar_sessao(token: str | None) -> None:
    if not token:
        return
    conexao = banco.conectar()
    conexao.execute("DELETE FROM sessoes WHERE token = ?", (token,))
    conexao.commit()
    conexao.close()


def atualizar_perfil(usuario_id: int, nome_completo: str, celular: str, email: str) -> dict:
    email_n = email.strip().lower()
    if not email_valido(email_n):
        raise ValueError("E-mail inválido.")
    conexao = banco.conectar()
    conflito = conexao.execute(
        "SELECT id FROM usuarios WHERE email = ? AND id <> ?",
        (email_n, usuario_id),
    ).fetchone()
    if conflito:
        conexao.close()
        raise ValueError("E-mail já utilizado por outra conta.")
    conexao.execute(
        "UPDATE usuarios SET nome_completo = ?, celular = ?, email = ? WHERE id = ?",
        (nome_completo.strip(), normalizar_celular(celular), email_n, usuario_id),
    )
    conexao.commit()
    conexao.close()
    usuario = obter_usuario(usuario_id)
    if usuario is None:
        raise ValueError("Usuário não encontrado.")
    return usuario
