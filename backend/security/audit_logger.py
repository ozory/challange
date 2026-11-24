"""Log de auditoria em JSON lines, com rotação. Strings longas são truncadas."""
import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from .config import security_config
from .pii_masker import mask_pii

_logger = logging.getLogger("finguard.audit")
_logger.setLevel(logging.INFO)
_logger.propagate = False
if not _logger.handlers:
    _h = RotatingFileHandler(security_config.audit_log_file, maxBytes=2_000_000,
                             backupCount=3, encoding="utf-8")
    _h.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_h)


def log_event(event: str, layer: str, **details) -> None:
    """Registra um evento de segurança (evita log flooding truncando textos)."""
    clean = {k: (mask_pii(v)[:200] if isinstance(v, str) else v) for k, v in details.items()}
    _logger.info(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "layer": layer,
        **clean,
    }, ensure_ascii=False))
