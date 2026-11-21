"""Compatibilidade com o CRUD original na raiz do projeto."""

import importlib.util
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))
_caminho = _backend / "banco.py"
_spec = importlib.util.spec_from_file_location("quitanda_backend_banco", _caminho)
_modulo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_modulo)

globals().update({nome: getattr(_modulo, nome) for nome in dir(_modulo) if not nome.startswith("_")})
