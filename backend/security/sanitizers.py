"""Sanitização de texto vindo do cliente (camada 2)."""
import html
import re
import unicodedata

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​-‏‪-‮⁠﻿]")
_TAGS = re.compile(r"<[^>]*>")
_FORMULA_PREFIX = ("=", "+", "-", "@", "\t", "\r")


def clean_text(value, max_length: int) -> str:
    """Normaliza Unicode, remove caracteres de controle/invisíveis e limita o tamanho."""
    value = unicodedata.normalize("NFKC", str(value))
    value = _CONTROL.sub("", value)
    return value.strip()[:max_length]


def strip_html(value: str) -> str:
    """Remove tags HTML e decodifica entidades; sobras de < e > são descartadas."""
    previous = None
    while previous != value:  # repete: '<<b>script>' etc.
        previous = value
        value = _TAGS.sub("", value)
    return html.unescape(value).replace("<", "").replace(">", "")


def clean_field(value, max_length: int = 100) -> str:
    """Campo curto de metadado (id, canal, data): texto simples sem HTML."""
    return strip_html(clean_text(value, max_length))


def neutralize_csv_formula(value):
    """Evita CSV injection ao exportar para planilhas."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIX):
        return "'" + value
    return value
