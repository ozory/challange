"""Camada 3: proteção do texto que vai para a LLM (prompt injection)."""
import re
from typing import Optional

from .audit_logger import log_event
from .config import security_config as cfg
from .exceptions import SecurityViolation
from .pii_masker import mask_pii
from .sanitizers import clean_text

# Padrões típicos de prompt injection (pt/en), aplicados sobre texto normalizado.
_INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r"ignor(e|a|ar)\s+(todas?\s+)?(as\s+|your\s+|all\s+|the\s+|suas\s+)*(instru|regras|diretriz|previous|prior|above|anterior)",
    r"(esque(c|ç)a|disregard|forget)\s+(tudo|todas?|all|your|as\s+instru|previous)",
    r"(novas?|new)\s+(instru(c|ç)(ões|oes)|instructions?)",
    r"\b(system|developer)\s*(prompt|message|role)\b",
    r"(prompt|instru(c|ç)(ões|oes))\s+(do\s+)?(sistema|interno|original)",
    r"(revele|mostre|exiba|reveal|show|print|repeat|repita)\s+.{0,30}(prompt|instru|pol(i|í)tica\s+interna|system)",
    r"voc(ê|e)\s+agora\s+(é|e|vai\s+ser)",
    r"\byou\s+are\s+now\b|\bact\s+as\b|\bpretend\s+to\b|\bjailbreak\b|\bDAN\s+mode\b",
    r"</?\s*(politica_interna|reclamacao|system|instructions?)\s*>",
    r"\[\s*/?\s*(INST|SYS)\s*\]|<\|(im_start|im_end|system)\|>",
]]


def detect_injection(text: str) -> Optional[str]:
    for p in _INJECTION_PATTERNS:
        if p.search(text):
            return p.pattern[:60]
    return None


def guard_input(text: str, source: str = "api") -> str:
    """Retorna o texto seguro para embutir no prompt ou levanta SecurityViolation."""
    if not cfg.layer(cfg.llm_input_guard_enabled):
        return text

    # Mascara PII antes de qualquer outra coisa: o que sai daqui vai para a LLM externa e para o log
    text = mask_pii(clean_text(text, cfg.max_text_length))
    if not text:
        raise SecurityViolation("EMPTY_INPUT", "Texto da reclamação não pode ser vazio")

    hit = detect_injection(text)
    if hit:
        log_event("PROMPT_INJECTION_BLOCKED", "llm_input", source=source, pattern=hit, preview=text)
        raise SecurityViolation(
            "PROMPT_INJECTION",
            "O texto contém instruções que não podem ser processadas. Descreva apenas a sua reclamação.")

    # Neutraliza qualquer tentativa de fechar o delimitador do prompt
    return text.replace("<", "‹").replace(">", "›")
