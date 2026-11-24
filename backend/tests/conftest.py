"""Isola os logs da suíte: nada é escrito em backend.log / security_audit.log reais.

Precisa rodar antes da importação dos módulos de teste, pois `security.config` e o
logging de `main` leem esses caminhos uma única vez, no import.
"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_LOGS = Path(tempfile.mkdtemp(prefix="finguard-testes-"))
os.environ.setdefault("APP_LOG_FILE", str(_LOGS / "backend.log"))
os.environ.setdefault("AUDIT_LOG_FILE", str(_LOGS / "security_audit.log"))
