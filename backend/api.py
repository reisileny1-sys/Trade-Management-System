"""API FastAPI da Quitanda da Liro e servidor do front-end estático."""

from __future__ import annotations

import base64
import binascii
import re
import secrets
import sys
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

_BACKEND = Path(__file__).resolve().parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import auth
import banco
import pedidos
from config import CATEGORIAS, LOJA, STATUS_LABEL

RAIZ = _BACKEND.parent
FRONTEND = RAIZ / "frontend"
HOST = "127.0.0.1"
PORTA = 8000


class ErroApi(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


app = FastAPI(
    title="API da Quitanda da Liro",
    description="Catálogo, usuários, autenticação e pedidos usando SQLite.",
    version="1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(ErroApi)
async def tratar_erro_api(_request: Request, exc: ErroApi) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"erro": exc.mensagem})


@app.exception_handler(HTTPException)
async def tratar_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
    mensagem = exc.detail if isinstance(exc.detail, str) else "Erro na requisição."
    return JSONResponse(status_code=exc.status_code, content={"erro": mensagem})


@app.on_event("startup")
def inicializar() -> None:
    banco.inicializar_banco()


def _token(authorization: str | None, cookie: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip() or None
    if cookie:
        for parte in cookie.split(";"):
            if parte.strip().startswith("token="):
                return parte.strip().split("=", 1)[1].strip() or None
    return None


def _exigir_usuario(
    authorization: str | None = Header(default=None),
    cookie: str | None = Header(default=None),
) -> dict:
    usuario = auth.usuario_por_token(_token(authorization, cookie))
    if usuario is None:
        raise ErroApi(401, "Faça login para continuar.")
    return usuario


def _exigir_admin(usuario: dict) -> dict:
    if usuario.get("perfil") != "admin":
        raise ErroApi(403, "Acesso restrito à administração.")
    return usuario


def _produto_publico(produto: dict) -> dict:
    return {
        "id": produto["id"],
        "nome": produto["nome"],
        "categoria": produto["categoria"],
        "preco": produto["preco"],
        "unidade_medida": produto["unidade_medida"],
        "descricao": produto.get("descricao") or "",
        "imagem": produto.get("imagem") or "",
    }


def _salvar_imagem(corpo: dict, obrigatoria: bool = False) -> str | None:
    dados = (corpo.get("imagem_data") or "").strip()
    if dados:
        correspondencia = re.fullmatch(
            r"data:(image/(?:jpeg|png|webp|gif));base64,(.+)",
            dados,
        )
        if not correspondencia:
            raise ErroApi(400, "Envie uma imagem JPEG, PNG, WEBP ou GIF válida.")
        mime, conteudo = correspondencia.groups()
        try:
            bruto = base64.b64decode(conteudo, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ErroApi(400, "Não foi possível ler a imagem enviada.") from exc
        if len(bruto) > 5 * 1024 * 1024:
            raise ErroApi(400, "A imagem deve ter no máximo 5 MB.")
        extensao = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
        }[mime]
        nome = f"produto-{secrets.token_hex(8)}.{extensao}"
        pasta = FRONTEND / "assets" / "images"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / nome).write_bytes(bruto)
        return nome

    imagem = (corpo.get("imagem") or "").strip()
    if imagem:
        caminho = Path(imagem)
        if caminho.name != imagem or caminho.suffix.lower() not in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
            ".svg",
        }:
            raise ErroApi(400, "Referência de imagem inválida.")
        return imagem
    if obrigatoria:
        raise ErroApi(400, "Selecione uma imagem do produto.")
    return None


async def _ler_corpo(request: Request) -> dict:
    try:
        corpo = await request.json()
    except Exception as exc:
        raise ErroApi(400, "JSON inválido.") from exc
    if not isinstance(corpo, dict):
        raise ErroApi(400, "O corpo deve ser um objeto JSON.")
    return corpo


def _validar_produto(corpo: dict) -> float:
    obrigatorios = ("nome", "categoria", "preco", "unidade_medida")
    if any(not str(corpo.get(campo, "")).strip() for campo in obrigatorios):
        raise ErroApi(400, "Preencha nome, categoria, preço e unidade.")
    try:
        corpo["categoria"] = banco.normalizar_categoria(corpo["categoria"])
    except ValueError as exc:
        raise ErroApi(400, str(exc)) from exc
    try:
        preco = float(corpo["preco"])
    except (TypeError, ValueError) as exc:
        raise ErroApi(400, "Preço inválido.") from exc
    if preco <= 0:
        raise ErroApi(400, "Preço deve ser maior que zero.")
    return preco


@app.get("/api/loja")
def loja() -> dict:
    return {"loja": LOJA, "categorias": CATEGORIAS, "status": STATUS_LABEL}


@app.get("/api/produtos")
def listar_produtos(nome: str | None = None, categoria: str | None = None) -> dict:
    lista = banco.buscar_produtos(nome, categoria)
    return {"produtos": [_produto_publico(produto) for produto in lista]}


@app.get("/api/produtos/{produto_id}")
def obter_produto(produto_id: int) -> dict:
    produto = banco.buscar_produto(produto_id)
    if produto is None:
        raise ErroApi(404, "Produto não encontrado.")
    return {"produto": _produto_publico(produto)}


@app.put("/api/produtos/{produto_id}")
@app.patch("/api/produtos/{produto_id}")
async def atualizar_produto(
    produto_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
    cookie: str | None = Header(default=None),
) -> dict:
    _exigir_admin(_exigir_usuario(authorization, cookie))
    corpo = await _ler_corpo(request)
    preco = _validar_produto(corpo)
    imagem = _salvar_imagem(corpo)
    ok = banco.atualizar_produto(
        produto_id,
        corpo["nome"].strip(),
        corpo["categoria"].strip(),
        preco,
        corpo["unidade_medida"].strip(),
        (corpo.get("descricao") or "").strip() or None,
        imagem,
    )
    if not ok:
        raise ErroApi(404, "Produto não encontrado.")
    produto = banco.buscar_produto(produto_id)
    return {"produto": _produto_publico(produto)}


@app.delete("/api/produtos/{produto_id}")
def remover_produto(
    produto_id: int,
    authorization: str | None = Header(default=None),
    cookie: str | None = Header(default=None),
) -> dict:
    _exigir_admin(_exigir_usuario(authorization, cookie))
    if not banco.remover_produto(produto_id):
        raise ErroApi(404, "Produto não encontrado.")
    return {"ok": True}


@app.post("/api/usuarios", status_code=201)
async def cadastrar(request: Request) -> dict:
    corpo = await _ler_corpo(request)
    nome = (corpo.get("nome_completo") or "").strip()
    senha = corpo.get("senha") or ""
    confirmacao = corpo.get("confirmacao_senha") or ""
    if not nome:
        raise ErroApi(400, "Informe o nome completo.")
    if not auth.cpf_valido(corpo.get("cpf") or ""):
        raise ErroApi(400, "CPF inválido.")
    if len(auth.normalizar_celular(corpo.get("celular") or "")) < 10:
        raise ErroApi(400, "Celular inválido.")
    if not auth.email_valido(corpo.get("email") or ""):
        raise ErroApi(400, "E-mail inválido.")
    if len(senha) < 6:
        raise ErroApi(400, "A senha deve ter pelo menos 6 caracteres.")
    if senha != confirmacao:
        raise ErroApi(400, "As senhas não coincidem.")
    try:
        usuario = auth.criar_usuario(
            nome,
            corpo.get("cpf") or "",
            corpo.get("celular") or "",
            corpo.get("email") or "",
            senha,
        )
    except ValueError as exc:
        raise ErroApi(409, str(exc)) from exc
    token = auth.criar_sessao(usuario["id"])
    return {"usuario": usuario, "token": token}


@app.post("/api/login")
async def login(request: Request) -> dict:
    corpo = await _ler_corpo(request)
    usuario = auth.autenticar(corpo.get("email") or "", corpo.get("senha") or "")
    if usuario is None:
        raise ErroApi(401, "E-mail ou senha incorretos.")
    token = auth.criar_sessao(usuario["id"])
    return {"usuario": usuario, "token": token}


@app.post("/api/logout")
def logout(
    authorization: str | None = Header(default=None),
    cookie: str | None = Header(default=None),
) -> dict:
    auth.encerrar_sessao(_token(authorization, cookie))
    return {"ok": True}


@app.get("/api/me")
def obter_perfil(
    authorization: str | None = Header(default=None),
    cookie: str | None = Header(default=None),
) -> dict:
    return {"usuario": _exigir_usuario(authorization, cookie)}


@app.put("/api/me")
async def atualizar_perfil(
    request: Request,
    authorization: str | None = Header(default=None),
    cookie: str | None = Header(default=None),
) -> dict:
    usuario = _exigir_usuario(authorization, cookie)
    corpo = await _ler_corpo(request)
    try:
        atualizado = auth.atualizar_perfil(
            usuario["id"],
            corpo.get("nome_completo") or usuario["nome_completo"],
            corpo.get("celular") or usuario["celular"],
            corpo.get("email") or usuario["email"],
        )
    except ValueError as exc:
        raise ErroApi(400, str(exc)) from exc
    return {"usuario": atualizado}


@app.post("/api/pedidos", status_code=201)
async def criar_pedido(
    request: Request,
    authorization: str | None = Header(default=None),
    cookie: str | None = Header(default=None),
) -> dict:
    usuario = _exigir_usuario(authorization, cookie)
    corpo = await _ler_corpo(request)
    itens = corpo.get("itens") or []
    if not isinstance(itens, list):
        raise ErroApi(400, "Itens inválidos.")
    try:
        pedido_criado = pedidos.criar_pedido(
            usuario["id"],
            itens,
            corpo.get("chave_idempotencia"),
        )
    except ValueError as exc:
        raise ErroApi(400, str(exc)) from exc
    return {"pedido": pedido_criado}


@app.get("/api/pedidos")
def listar_pedidos(
    authorization: str | None = Header(default=None),
    cookie: str | None = Header(default=None),
) -> dict:
    usuario = _exigir_usuario(authorization, cookie)
    return {"pedidos": pedidos.listar_pedidos_usuario(usuario["id"])}


@app.get("/api/pedidos/{pedido_id}")
def detalhar_pedido(
    pedido_id: int,
    authorization: str | None = Header(default=None),
    cookie: str | None = Header(default=None),
) -> dict:
    usuario = _exigir_usuario(authorization, cookie)
    try:
        pedido_detalhado = pedidos.detalhar_pedido(pedido_id)
    except ValueError as exc:
        raise ErroApi(404, str(exc)) from exc
    if pedido_detalhado["usuario_id"] != usuario["id"] and usuario.get("perfil") != "admin":
        raise ErroApi(403, "Você só pode consultar os seus pedidos.")
    return {"pedido": pedido_detalhado}


@app.patch("/api/pedidos/{pedido_id}/status")
async def atualizar_status_pedido(
    pedido_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
    cookie: str | None = Header(default=None),
) -> dict:
    _exigir_admin(_exigir_usuario(authorization, cookie))
    corpo = await _ler_corpo(request)
    try:
        pedido_atualizado = pedidos.atualizar_status(
            pedido_id,
            corpo.get("status") or "",
        )
    except ValueError as exc:
        raise ErroApi(400, str(exc)) from exc
    return {"pedido": pedido_atualizado}


@app.get("/api/admin/pedidos")
def listar_todos_pedidos(
    authorization: str | None = Header(default=None),
    cookie: str | None = Header(default=None),
) -> dict:
    _exigir_admin(_exigir_usuario(authorization, cookie))
    return {"pedidos": pedidos.listar_todos_pedidos()}


@app.post("/api/produtos")
async def criar_produto_fastapi(
    request: Request,
    authorization: str | None = Header(default=None),
    cookie: str | None = Header(default=None),
) -> dict:
    _exigir_admin(_exigir_usuario(authorization, cookie))
    corpo = await _ler_corpo(request)
    preco = _validar_produto(corpo)
    imagem = _salvar_imagem(corpo, obrigatoria=True)
    novo_id = banco.inserir_produto(
        corpo["nome"].strip(),
        corpo["categoria"].strip(),
        preco,
        corpo["unidade_medida"].strip(),
        (corpo.get("descricao") or "").strip() or None,
        imagem,
    )
    produto = banco.buscar_produto(novo_id)
    return {"produto": _produto_publico(produto)}


@app.get("/{caminho:path}")
def servir_frontend(caminho: str) -> FileResponse:
    relativo = caminho or "index.html"
    alvo = (FRONTEND / relativo).resolve()
    raiz = FRONTEND.resolve()
    if raiz not in alvo.parents and alvo != raiz:
        raise ErroApi(403, "Caminho inválido.")
    if alvo.is_dir():
        alvo = alvo / "index.html"
    if not alvo.is_file():
        raise ErroApi(404, "Arquivo não encontrado.")
    return FileResponse(alvo)


def main() -> None:
    import uvicorn

    print(f"Quitanda da Liro em http://{HOST}:{PORTA}")
    print("API em /api | Documentação em /docs")
    uvicorn.run(app, host=HOST, port=PORTA, reload=False)


if __name__ == "__main__":
    main()
