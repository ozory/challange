"""Camada 4: valida e sanitiza o que a LLM devolve antes de salvar/exibir."""
import re

from .audit_logger import log_event
from .pii_masker import mask_pii
from .config import security_config as cfg
from .sanitizers import clean_text, strip_html

_ALLOWED_KEYS = {"categoria", "produto", "sentimento", "urgencia", "resumo"}
_URL = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)
_LEAK_MARKERS = re.compile(
    r"(politica_interna|system prompt|prompt do sistema|instru(c|ç)(ões|oes) internas|"
    r"sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,}|"
    r"STACKSPOT_CLIENT_SECRET|STACKSPOT_CLIENT_ID|client_secret)", re.IGNORECASE)

FALLBACK_SUMMARY = "Resumo indisponível: conteúdo gerado foi descartado por política de segurança."


def validate_llm_dict(dados) -> dict:
    """O JSON da LLM deve ser um objeto; chaves inesperadas são descartadas."""
    if not isinstance(dados, dict):
        raise ValueError("Resposta da LLM não é um objeto JSON")
    if not cfg.layer(cfg.llm_output_validator_enabled):
        return dados
    extras = set(dados) - _ALLOWED_KEYS
    if extras:
        log_event("LLM_OUTPUT_EXTRA_KEYS", "llm_output", keys=",".join(sorted(map(str, extras))))
    return {k: v for k, v in dados.items() if k in _ALLOWED_KEYS}


def validate_summary(resumo) -> str:
    if not cfg.layer(cfg.llm_output_validator_enabled):
        return resumo if isinstance(resumo, str) else str(resumo)

    if not isinstance(resumo, str):
        log_event("LLM_OUTPUT_BAD_TYPE", "llm_output", type=type(resumo).__name__)
        return FALLBACK_SUMMARY

    original = resumo
    resumo = clean_text(strip_html(resumo), cfg.max_summary_length)
    resumo = _URL.sub("[link removido]", resumo)
    resumo = mask_pii(resumo)  # a LLM pode repetir/inventar dados pessoais no resumo

    if not resumo or _LEAK_MARKERS.search(resumo):
        log_event("LLM_OUTPUT_LEAK_BLOCKED", "llm_output", preview=original)
        return FALLBACK_SUMMARY
    if resumo != original.strip():
        log_event("LLM_OUTPUT_SANITIZED", "llm_output", before_len=len(original), after_len=len(resumo))
    return resumo
