"""Segurança em 4 camadas do FinGuard (plug-and-play via variáveis de ambiente).

1. Frontend      -> frontend/js/security.js
2. Backend       -> middleware.py, sanitizers.py, rate_limiter.py, audit_logger.py
3. Entrada LLM   -> llm_input_guard.py
4. Saída LLM     -> llm_output_validator.py
"""
from .config import security_config
from .exceptions import SecurityViolation
