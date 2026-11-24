"""Mascaramento de dados pessoais (PII): CPF, CNPJ, cartão, e-mail e telefone.

Usado em várias camadas (backend, entrada/saída da LLM e log de auditoria).
É idempotente: aplicar duas vezes no mesmo texto não muda o resultado.
"""
import re

from .config import security_config as cfg

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_CNPJ = re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)")
_CPF_FMT = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")  # formatado: mascara sempre
_CPF = re.compile(r"(?<!\d)\d{11}(?!\d)")  # só dígitos: exige dígito verificador válido
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_PHONE = re.compile(r"(?<!\d)(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)(?:9\s?)?\d{4}[-\s]?\d{4}(?!\d)")


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def valid_cpf(value: str) -> bool:
    d = _digits(value)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        s = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if int(d[n]) != (s * 10 % 11) % 10:
            return False
    return True


def valid_cnpj(value: str) -> bool:
    d = _digits(value)
    if len(d) != 14 or d == d[0] * 14:
        return False
    for n, w in ((12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]), (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])):
        r = sum(int(d[i]) * w[i] for i in range(n)) % 11
        if int(d[n]) != (0 if r < 2 else 11 - r):
            return False
    return True


def valid_luhn(value: str) -> bool:
    d = _digits(value)
    if not 13 <= len(d) <= 19:
        return False
    total = 0
    for i, ch in enumerate(reversed(d)):
        n = int(ch)
        if i % 2:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
    return total % 10 == 0


def _sub(pattern, token, text, check=None):
    def repl(m):
        return token if (check is None or check(m.group())) else m.group()
    return pattern.sub(repl, text)


def mask_pii_text(text: str) -> str:
    """Substitui PII por tokens ([CPF], [CNPJ], [CARTAO], [EMAIL], [TELEFONE])."""
    if not isinstance(text, str) or not text:
        return text
    text = _sub(_EMAIL, "[EMAIL]", text)
    text = _sub(_CNPJ, "[CNPJ]", text, valid_cnpj)
    text = _sub(_CPF_FMT, "[CPF]", text)
    text = _sub(_CPF, "[CPF]", text, valid_cpf)
    text = _sub(_CARD, "[CARTAO]", text, valid_luhn)
    text = _sub(_PHONE, "[TELEFONE]", text)
    return text


def mask_pii(text: str) -> str:
    """Igual a mask_pii_text, respeitando a chave PII_MASKING_ENABLED."""
    if not cfg.layer(cfg.pii_masking_enabled):
        return text
    return mask_pii_text(text)
