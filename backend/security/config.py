"""Configuração central. Cada camada liga/desliga por variável de ambiente."""
import os
from dataclasses import dataclass, field
from typing import List


def _bool(name: str, default: bool = True) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _list(name: str, default: str) -> List[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


@dataclass
class SecurityConfig:
    # Chave geral
    enabled: bool = field(default_factory=lambda: _bool("SECURITY_ENABLED"))

    # Camada 2 - backend
    backend_enabled: bool = field(default_factory=lambda: _bool("SECURITY_BACKEND_ENABLED"))
    rate_limit_enabled: bool = field(default_factory=lambda: _bool("RATE_LIMIT_ENABLED"))
    rate_limit_per_minute: int = field(default_factory=lambda: _int("RATE_LIMIT_PER_MINUTE", 120))
    rate_limit_llm_per_minute: int = field(default_factory=lambda: _int("RATE_LIMIT_LLM_PER_MINUTE", 20))
    max_request_bytes: int = field(default_factory=lambda: _int("MAX_REQUEST_BYTES", 5 * 1024 * 1024))
    max_text_length: int = field(default_factory=lambda: _int("MAX_TEXT_LENGTH", 2000))
    max_csv_rows: int = field(default_factory=lambda: _int("MAX_CSV_ROWS", 1000))
    cors_origins: List[str] = field(default_factory=lambda: _list(
        "CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"))
    audit_log_file: str = field(default_factory=lambda: os.getenv("AUDIT_LOG_FILE", "security_audit.log"))

    # Mascaramento de PII (CPF, CNPJ, cartão, e-mail, telefone) - usado em várias camadas
    pii_masking_enabled: bool = field(default_factory=lambda: _bool("PII_MASKING_ENABLED"))

    # Camada 3 - entrada da LLM
    llm_input_guard_enabled: bool = field(default_factory=lambda: _bool("LLM_INPUT_GUARD_ENABLED"))

    # Camada 4 - saída da LLM
    llm_output_validator_enabled: bool = field(default_factory=lambda: _bool("LLM_OUTPUT_VALIDATOR_ENABLED"))
    max_summary_length: int = field(default_factory=lambda: _int("MAX_SUMMARY_LENGTH", 500))

    def layer(self, flag: bool) -> bool:
        return self.enabled and flag


security_config = SecurityConfig()
