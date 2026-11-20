"""Gera o ZIP do projeto, sem .venv nem .git."""

from pathlib import Path
import zipfile

RAIZ = Path(__file__).resolve().parent
DESTINO = RAIZ.parent / "quitanda-da-liro-completo.zip"
IGNORAR = {".venv", ".git", "__pycache__"}


def incluir(caminho: Path) -> bool:
    return not any(parte in IGNORAR for parte in caminho.parts)


def main() -> None:
    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED) as arquivo:
        for item in RAIZ.rglob("*"):
            if item.is_file() and incluir(item.relative_to(RAIZ)):
                arquivo.write(item, Path("quitanda-da-liro") / item.relative_to(RAIZ))
    print(f"ZIP criado em {DESTINO}")


if __name__ == "__main__":
    main()
