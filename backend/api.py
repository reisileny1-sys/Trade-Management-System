"""API HTTP da Quitanda da Liro. Serve JSON em /api e o front-end estático."""

from __future__ import annotations

import json
import mimetypes
import base64
import binascii
import re
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_BACKEND = Path(__file__).resolve().parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import auth
import banco
import pedidos
from config import CATEGORIAS, LOJA, STATUS_LABEL

RAIZ = Path(__file__).resolve().parent.parent
FRONTEND = RAIZ / "frontend"
HOST = "127.0.0.1"
PORTA = 8000


class ErroApi(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


def _ler_json(handler: BaseHTTPRequestHandler) -> dict:
    tamanho = int(handler.headers.get("Content-Length", "0") or 0)
    if tamanho == 0:
        return {}
    bruto = handler.rfile.read(tamanho)
    try:
        dados = json.loads(bruto.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ErroApi(400, "JSON inválido.") from exc
    if not isinstance(dados, dict):
        raise ErroApi(400, "O corpo deve ser um objeto JSON.")
    return dados


def _token(handler: BaseHTTPRequestHandler) -> str | None:
    header = handler.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip() or None
    cookie = handler.headers.get("Cookie", "")
    for parte in cookie.split(";"):
        if parte.strip().startswith("token="):
            return parte.strip().split("=", 1)[1].strip() or None
    return None


def _exigir_usuario(handler: BaseHTTPRequestHandler) -> dict:
    usuario = auth.usuario_por_token(_token(handler))
    if usuario is None:
        raise ErroApi(401, "Faça login para continuar.")
    return usuario


def _exigir_admin(handler: BaseHTTPRequestHandler) -> dict:
    usuario = _exigir_usuario(handler)
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
            r"data:(image/(?:jpeg|png|webp|gif));base64,(.+)", dados
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
        (FRONTEND / "assets" / "images").mkdir(parents=True, exist_ok=True)
        (FRONTEND / "assets" / "images" / nome).write_bytes(bruto)
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


class Manipulador(BaseHTTPRequestHandler):
    def log_message(self, formato: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), formato % args))

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "*"))
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        self.send_header("Access-Control-Allow-Credentials", "true")

    def _json(self, status: int, corpo: dict) -> None:
        payload = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self._cors()
        self.end_headers()
        self.wfile.write(payload)

    def _arquivo_estatico(self, caminho: Path) -> None:
        if not caminho.exists() or not caminho.is_file():
            self._json(404, {"erro": "Arquivo não encontrado."})
            return
        tipo, _ = mimetypes.guess_type(str(caminho))
        dados = caminho.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", tipo or "application/octet-stream")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        self._despachar("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._despachar("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._despachar("PUT")

    def do_PATCH(self) -> None:  # noqa: N802
        self._despachar("PATCH")

    def do_DELETE(self) -> None:  # noqa: N802
        self._despachar("DELETE")

    def _despachar(self, metodo: str) -> None:
        try:
            parsed = urlparse(self.path)
            caminho = parsed.path
            query = {k: v[0] if v else "" for k, v in parse_qs(parsed.query).items()}
            if caminho.startswith("/api/"):
                self._api(metodo, caminho, query)
                return
            self._front(caminho)
        except ErroApi as exc:
            self._json(exc.status, {"erro": exc.mensagem})
        except ValueError as exc:
            self._json(400, {"erro": str(exc)})
        except Exception:
            self._json(500, {"erro": "Erro interno do servidor."})

    def _front(self, caminho: str) -> None:
        relativo = caminho.lstrip("/") or "index.html"
        alvo = (FRONTEND / relativo).resolve()
        if FRONTEND.resolve() not in alvo.parents and alvo != FRONTEND.resolve():
            raise ErroApi(403, "Caminho inválido.")
        if alvo.is_dir():
            alvo = alvo / "index.html"
        self._arquivo_estatico(alvo)

    def _api(self, metodo: str, caminho: str, query: dict) -> None:
        partes = [p for p in caminho.split("/") if p]
        # partes[0] == 'api'
        recurso = partes[1] if len(partes) > 1 else ""
        resto = partes[2:]

        if recurso == "loja" and metodo == "GET":
            self._json(
                200, {"loja": LOJA, "categorias": CATEGORIAS, "status": STATUS_LABEL}
            )
            return

        if recurso == "produtos":
            self._produtos(metodo, resto, query)
            return
        if recurso == "usuarios" and metodo == "POST":
            self._cadastrar()
            return
        if recurso == "login" and metodo == "POST":
            self._login()
            return
        if recurso == "logout" and metodo == "POST":
            self._logout()
            return
        if recurso == "me":
            self._me(metodo)
            return
        if recurso == "pedidos":
            self._pedidos(metodo, resto)
            return
        if recurso == "admin" and resto[:1] == ["pedidos"]:
            self._admin_pedidos(metodo, resto[1:])
            return
        raise ErroApi(404, "Rota não encontrada.")

    def _produtos(self, metodo: str, resto: list[str], query: dict) -> None:
        if metodo == "GET" and not resto:
            lista = banco.buscar_produtos(query.get("nome"), query.get("categoria"))
            self._json(200, {"produtos": [_produto_publico(p) for p in lista]})
            return
        if metodo == "GET" and len(resto) == 1:
            produto = banco.buscar_produto(int(resto[0]))
            if produto is None:
                raise ErroApi(404, "Produto não encontrado.")
            self._json(200, {"produto": _produto_publico(produto)})
            return
        if metodo == "POST" and not resto:
            _exigir_admin(self)
            corpo = _ler_json(self)
            self._validar_produto(corpo)
            imagem = _salvar_imagem(corpo, obrigatoria=True)
            novo_id = banco.inserir_produto(
                corpo["nome"].strip(),
                corpo["categoria"].strip(),
                corpo["preco"],
                corpo["unidade_medida"].strip(),
                (corpo.get("descricao") or "").strip() or None,
                imagem,
            )
            produto = banco.buscar_produto(novo_id)
            self._json(201, {"produto": _produto_publico(produto)})
            return
        if metodo == "PUT" and len(resto) == 1:
            _exigir_admin(self)
            corpo = _ler_json(self)
            self._validar_produto(corpo)
            imagem = _salvar_imagem(corpo)
            ok = banco.atualizar_produto(
                int(resto[0]),
                corpo["nome"].strip(),
                corpo["categoria"].strip(),
                corpo["preco"],
                corpo["unidade_medida"].strip(),
                (corpo.get("descricao") or "").strip() or None,
                imagem,
            )
            if not ok:
                raise ErroApi(404, "Produto não encontrado.")
            produto = banco.buscar_produto(int(resto[0]))
            self._json(200, {"produto": _produto_publico(produto)})
            return
        if metodo == "DELETE" and len(resto) == 1:
            _exigir_admin(self)
            if not banco.remover_produto(int(resto[0])):
                raise ErroApi(404, "Produto não encontrado.")
            self._json(200, {"ok": True})
            return
        raise ErroApi(404, "Rota de produtos não encontrada.")

    def _validar_produto(self, corpo: dict) -> None:
        obrigatorios = ("nome", "categoria", "preco", "unidade_medida")
        if any(not str(corpo.get(c, "")).strip() for c in obrigatorios):
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
        corpo["preco"] = preco

    def _cadastrar(self) -> None:
        corpo = _ler_json(self)
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
        self._json(201, {"usuario": usuario, "token": token})

    def _login(self) -> None:
        corpo = _ler_json(self)
        usuario = auth.autenticar(corpo.get("email") or "", corpo.get("senha") or "")
        if usuario is None:
            raise ErroApi(401, "E-mail ou senha incorretos.")
        token = auth.criar_sessao(usuario["id"])
        self._json(200, {"usuario": usuario, "token": token})

    def _logout(self) -> None:
        auth.encerrar_sessao(_token(self))
        self._json(200, {"ok": True})

    def _me(self, metodo: str) -> None:
        usuario = _exigir_usuario(self)
        if metodo == "GET":
            self._json(200, {"usuario": usuario})
            return
        if metodo == "PUT":
            corpo = _ler_json(self)
            try:
                atualizado = auth.atualizar_perfil(
                    usuario["id"],
                    corpo.get("nome_completo") or usuario["nome_completo"],
                    corpo.get("celular") or usuario["celular"],
                    corpo.get("email") or usuario["email"],
                )
            except ValueError as exc:
                raise ErroApi(400, str(exc)) from exc
            self._json(200, {"usuario": atualizado})
            return
        raise ErroApi(405, "Método não permitido.")

    def _pedidos(self, metodo: str, resto: list[str]) -> None:
        usuario = _exigir_usuario(self)
        if metodo == "POST" and not resto:
            corpo = _ler_json(self)
            itens = corpo.get("itens") or []
            if not isinstance(itens, list):
                raise ErroApi(400, "Itens inválidos.")
            try:
                pedido = pedidos.criar_pedido(
                    usuario["id"], itens, corpo.get("chave_idempotencia")
                )
            except ValueError as exc:
                raise ErroApi(400, str(exc)) from exc
            self._json(201, {"pedido": pedido})
            return
        if metodo == "GET" and not resto:
            self._json(200, {"pedidos": pedidos.listar_pedidos_usuario(usuario["id"])})
            return
        if metodo == "GET" and len(resto) == 1:
            try:
                pedido = pedidos.detalhar_pedido(int(resto[0]))
            except ValueError as exc:
                raise ErroApi(404, str(exc)) from exc
            if (
                pedido["usuario_id"] != usuario["id"]
                and usuario.get("perfil") != "admin"
            ):
                raise ErroApi(403, "Você só pode consultar os seus pedidos.")
            self._json(200, {"pedido": pedido})
            return
        if metodo == "PATCH" and len(resto) == 2 and resto[1] == "status":
            _exigir_admin(self)
            corpo = _ler_json(self)
            try:
                pedido = pedidos.atualizar_status(
                    int(resto[0]), corpo.get("status") or ""
                )
            except ValueError as exc:
                raise ErroApi(400, str(exc)) from exc
            self._json(200, {"pedido": pedido})
            return
        raise ErroApi(404, "Rota de pedidos não encontrada.")

    def _admin_pedidos(self, metodo: str, resto: list[str]) -> None:
        _exigir_admin(self)
        if metodo == "GET" and not resto:
            self._json(200, {"pedidos": pedidos.listar_todos_pedidos()})
            return
        raise ErroApi(404, "Rota administrativa não encontrada.")


def main() -> None:
    banco.inicializar_banco()
    servidor = ThreadingHTTPServer((HOST, PORTA), Manipulador)
    print(f"Quitanda da Liro em http://{HOST}:{PORTA}")
    print("API em /api  |  menu de produtos: python menu.py")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
        servidor.server_close()


if __name__ == "__main__":
    main()
