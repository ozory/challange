# FinGuard - Análise de Segurança e Arquitetura Plug-and-Play

> Este documento descreve propostas e exemplos históricos. O serviço atual utiliza StackSpot AI e não utiliza fallback de classificação mock; os trechos de código abaixo não devem ser interpretados como implementação ativa.

## Visão Geral

Este documento descreve uma arquitetura de segurança em **4 camadas** (Frontend → Backend → LLM Input → LLM Output) projetada para ser **plug-and-play**, permitindo que cada camada seja habilitada/desabilitada independentemente via configuração.

---

## Arquitetura de Camadas de Segurança

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLUXO DE DADOS COM SEGURANÇA                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   FRONTEND   │────▶│   BACKEND    │────▶│   LLM INPUT  │────▶│  LLM OUTPUT  │
│  (Camada 1)  │     │  (Camada 2)  │     │  (Camada 3)  │     │  (Camada 4)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
      │                    │                    │                    │
      ▼                    ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MIDDLEWARE DE SEGURANÇA PLUG-AND-PLAY                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │  Validação  │ │  Sanitização│ │ Rate Limit  │ │   Auditoria │          │
│  │  de Schema  │ │  de Input   │ │  / DDoS     │ │  & Logs     │          │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## CAMADA 1: Frontend (Client-Side Validation)

### Objetivo
Primeira linha de defesa - validação imediata, UX responsiva, redução de carga no backend.

### Implementação Plug-and-Play

```javascript
// frontend/src/security/validationRules.js
export const validationRules = {
  // Configuração centralizada - fácil de modificar
  reclamacao: {
    texto: {
      required: true,
      minLength: 10,
      maxLength: 5000,
      // Padrões perigosos a bloquear no frontend
      forbiddenPatterns: [
        /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,  // XSS
        /javascript:/gi,                                        // XSS
        /on\w+\s*=/gi,                                          // Event handlers
        /data:text\/html/gi,                                    // Data URI XSS
        /vbscript:/gi,                                          // VBScript
        /expression\s*\(/gi,                                    // CSS expression
        /<\s*iframe/gi,                                         // Iframe injection
        /<\s*object/gi,                                         // Object injection
        /<\s*embed/gi,                                          // Embed injection
      ],
      // Palavras que indicam possível injection
      suspiciousKeywords: [
        'union select', 'drop table', 'insert into', 'delete from',
        'update set', 'alter table', 'create table', 'exec ',
        'execute ', 'sp_', 'xp_', '--', ';--', '/*', '*/',
        '@@version', 'waitfor delay', 'benchmark(', 'sleep(',
      ]
    }
  },
  
  csvUpload: {
    maxFileSize: 10 * 1024 * 1024, // 10MB
    allowedTypes: ['text/csv', 'application/csv'],
    maxRows: 1000,
    requiredColumns: ['id', 'data_reclamacao', 'canal', 'texto_reclamacao', 'produto', 'status']
  }
};

// Validador reutilizável
export class FrontendValidator {
  constructor(rules = validationRules) {
    this.rules = rules;
    this.enabled = true; // Pode ser desabilitado via config
  }
  
  validate(field, value, ruleSet) {
    if (!this.enabled) return { valid: true, errors: [] };
    
    const rules = this.rules[ruleSet]?.[field];
    if (!rules) return { valid: true, errors: [] };
    
    const errors = [];
    
    if (rules.required && (!value || !value.trim())) {
      errors.push(`${field} é obrigatório`);
    }
    
    if (value && rules.minLength && value.length < rules.minLength) {
      errors.push(`${field} deve ter pelo menos ${rules.minLength} caracteres`);
    }
    
    if (value && rules.maxLength && value.length > rules.maxLength) {
      errors.push(`${field} deve ter no máximo ${rules.maxLength} caracteres`);
    }
    
    // Verificar padrões perigosos
    if (value && rules.forbiddenPatterns) {
      for (const pattern of rules.forbiddenPatterns) {
        if (pattern.test(value)) {
          errors.push(`${field} contém padrão não permitido`);
          // Log de segurança
          this.logSecurityEvent('FORBIDDEN_PATTERN', { field, pattern: pattern.source });
          break;
        }
      }
    }
    
    // Verificar palavras suspeitas
    if (value && rules.suspiciousKeywords) {
      const lowerValue = value.toLowerCase();
      for (const keyword of rules.suspiciousKeywords) {
        if (lowerValue.includes(keyword.toLowerCase())) {
          errors.push(`${field} contém conteúdo suspeito`);
          this.logSecurityEvent('SUSPICIOUS_KEYWORD', { field, keyword });
          break;
        }
      }
    }
    
    return { valid: errors.length === 0, errors };
  }
  
  validateCSV(file) {
    if (!this.enabled) return { valid: true, errors: [] };
    
    const rules = this.rules.csvUpload;
    const errors = [];
    
    if (file.size > rules.maxFileSize) {
      errors.push(`Arquivo muito grande. Máximo: ${rules.maxFileSize / 1024 / 1024}MB`);
    }
    
    if (!rules.allowedTypes.includes(file.type)) {
      errors.push('Tipo de arquivo não permitido. Apenas CSV.');
    }
    
    return { valid: errors.length === 0, errors };
  }
  
  logSecurityEvent(type, details) {
    // Enviar para backend de auditoria (non-blocking)
    fetch('/api/security/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type,
        details,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href
      })
    }).catch(() => {}); // Silencioso
  }
  
  // Método para habilitar/desabilitar (plug-and-play)
  setEnabled(enabled) {
    this.enabled = enabled;
  }
}
```

### Integração no ChatPanel

```javascript
// frontend/src/components/ChatPanel.jsx - Adicionar validação
import { FrontendValidator, validationRules } from '../security/validationRules';

const validator = new FrontendValidator(validationRules);

// No handleSubmit:
const handleSubmit = async (e) => {
  e.preventDefault();
  if (!mensagem.trim() || enviando) return;

  // VALIDAÇÃO FRONTEND
  const validation = validator.validate('texto', mensagem.trim(), 'reclamacao');
  if (!validation.valid) {
    setErro(validation.errors.join(', '));
    return;
  }
  
  // Sanitizar antes de enviar (defesa em profundidade)
  const sanitized = sanitizeInput(mensagem.trim());
  // ... resto do código
};
```

---

## CAMADA 2: Backend (Server-Side Validation & Protection)

### Objetivo
Validação autoritária, rate limiting, proteção contra DDoS, headers de segurança.

### Estrutura Plug-and-Play

```
backend/
├── security/
│   ├── __init__.py
│   ├── config.py              # Configuração centralizada
│   ├── middleware.py          # Middlewares de segurança
│   ├── validators.py          # Validadores Pydantic customizados
│   ├── sanitizers.py          # Sanitizadores de input
│   ├── rate_limiter.py        # Rate limiting com Redis/memória
│   ├── audit_logger.py        # Logger de eventos de segurança
│   └── exceptions.py          # Exceções de segurança customizadas
```

### Configuração Centralizada

```python
# backend/security/config.py
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class SecurityLevel(str, Enum):
    DISABLED = "disabled"
    BASIC = "basic"
    STRICT = "strict"
    PARANOID = "paranoid"

class SecurityConfig(BaseModel):
    # Controle global - pode desabilitar tudo
    enabled: bool = True
    level: SecurityLevel = SecurityLevel.STRICT
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10
    rate_limit_by_ip: bool = True
    rate_limit_by_user: bool = False  # Para futuro com auth
    
    # Request Size Limits
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    max_json_size: int = 1 * 1024 * 1024      # 1MB
    max_csv_rows: int = 1000
    
    # Input Validation
    validate_input_enabled: bool = True
    strict_schema_validation: bool = True
    reject_unknown_fields: bool = True
    
    # Sanitization
    sanitize_input_enabled: bool = True
    sanitize_html: bool = True
    sanitize_sql: bool = True
    sanitize_prompt_injection: bool = True
    
    # CORS
    cors_enabled: bool = True
    cors_allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    cors_allow_credentials: bool = True
    
    # Security Headers
    security_headers_enabled: bool = True
    csp_policy: str = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' http://localhost:8000;"
    hsts_enabled: bool = True
    hsts_max_age: int = 31536000
    frame_options: str = "DENY"
    content_type_options: str = "nosniff"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "geolocation=(), microphone=(), camera=()"
    
    # SQL Injection Protection
    sql_protection_enabled: bool = True
    log_sql_errors: bool = True
    
    # Prompt Injection Protection
    prompt_injection_protection_enabled: bool = True
    max_prompt_length: int = 8000
    forbidden_prompt_patterns: List[str] = [
        r"ignore\s+previous\s+instructions",
        r"disregard\s+the\s+above",
        r"forget\s+everything",
        r"new\s+instructions?:",
        r"system\s+prompt",
        r"you\s+are\s+now",
        r"act\s+as\s+",
        r"pretend\s+to\s+be",
        r"roleplay\s+as",
        r"simulate\s+",
        r"<\|.*?\|>",  # Special tokens
        r"\[INST\].*?\[/INST\]",
        r"<<SYS>>.*?<</SYS>>",
    ]
    
    # Audit Logging
    audit_log_enabled: bool = True
    audit_log_level: str = "WARNING"  # DEBUG, INFO, WARNING, ERROR
    audit_log_file: str = "security_audit.log"
    audit_log_max_size: int = 10 * 1024 * 1024  # 10MB
    audit_log_backup_count: int = 5
    
    # LLM Output Validation
    validate_llm_output_enabled: bool = True
    llm_output_max_length: int = 2000
    llm_allowed_categories: List[str] = [
        "Cobrança Indevida", "Atendimento", "Fraude/Segurança",
        "Produto/Serviço", "Cancelamento", "Outros"
    ]
    llm_allowed_products: List[str] = [
        "Cartão de Crédito", "Conta Corrente", "Empréstimo",
        "Investimentos", "Seguros", "Não Identificado"
    ]
    llm_allowed_sentiments: List[str] = [
        "Positivo", "Neutro", "Negativo", "Crítico"
    ]
    llm_allowed_urgencies: List[str] = [
        "Baixa", "Média", "Alta", "Crítica"
    ]

# Instância global configurável
security_config = SecurityConfig()

# Função para carregar de variáveis de ambiente
def load_security_config_from_env() -> SecurityConfig:
    import os
    return SecurityConfig(
        enabled=os.getenv("SECURITY_ENABLED", "true").lower() == "true",
        level=SecurityLevel(os.getenv("SECURITY_LEVEL", "strict")),
        rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
        rate_limit_requests_per_minute=int(os.getenv("RATE_LIMIT_RPM", "60")),
        cors_allowed_origins=os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(","),
        # ... outros campos
    )
```

### Middleware de Segurança Principal

```python
# backend/security/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
import time
import logging
from typing import Callable, Optional
import re

from .config import security_config
from .rate_limiter import rate_limiter
from .audit_logger import audit_logger
from .sanitizers import sanitize_request_body, sanitize_query_params
from .validators import validate_request_schema

logger = logging.getLogger("finguard.security")

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware principal de segurança - plug-and-play via security_config
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.enabled = security_config.enabled
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)
        
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        path = request.url.path
        method = request.method
        
        try:
            # 1. Rate Limiting
            if security_config.rate_limit_enabled:
                rate_limit_result = await rate_limiter.check_limit(
                    client_ip, path, method
                )
                if not rate_limit_result.allowed:
                    audit_logger.log_security_event(
                        "RATE_LIMIT_EXCEEDED",
                        {"ip": client_ip, "path": path, "method": method},
                        severity="WARNING"
                    )
                    return JSONResponse(
                        status_code=429,
                        content={
                            "success": False,
                            "error": "Rate limit exceeded. Please slow down.",
                            "retry_after": rate_limit_result.retry_after
                        },
                        headers={"Retry-After": str(rate_limit_result.retry_after)}
                    )
            
            # 2. Request Size Validation
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > security_config.max_request_size:
                audit_logger.log_security_event(
                    "REQUEST_TOO_LARGE",
                    {"ip": client_ip, "size": content_length, "max": security_config.max_request_size},
                    severity="WARNING"
                )
                return JSONResponse(
                    status_code=413,
                    content={"success": False, "error": "Request entity too large"}
                )
            
            # 3. Sanitize Query Parameters
            if security_config.sanitize_input_enabled:
                sanitized_query = sanitize_query_params(dict(request.query_params))
                request._query_params = sanitized_query
            
            # 4. Sanitize Request Body (para POST/PUT/PATCH)
            if method in ("POST", "PUT", "PATCH") and security_config.sanitize_input_enabled:
                body = await request.body()
                if body:
                    sanitized_body = sanitize_request_body(body, request.headers.get("content-type", ""))
                    # Recriar request com body sanitizado
                    request._body = sanitized_body
            
            # 5. Schema Validation (para endpoints conhecidos)
            if security_config.validate_input_enabled and path in self._get_validated_paths():
                validation_result = await validate_request_schema(request, path)
                if not validation_result.valid:
                    audit_logger.log_security_event(
                        "SCHEMA_VALIDATION_FAILED",
                        {"ip": client_ip, "path": path, "errors": validation_result.errors},
                        severity="WARNING"
                    )
                    return JSONResponse(
                        status_code=400,
                        content={
                            "success": False,
                            "error": "Invalid request format",
                            "details": validation_result.errors
                        }
                    )
            
            # Processar request
            response = await call_next(request)
            
            # 6. Security Headers
            if security_config.security_headers_enabled:
                self._add_security_headers(response)
            
            # 7. Log successful request (auditoria)
            duration = time.time() - start_time
            audit_logger.log_request(
                ip=client_ip,
                method=method,
                path=path,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            audit_logger.log_security_event(
                "MIDDLEWARE_ERROR",
                {"ip": client_ip, "path": path, "error": str(e)},
                severity="ERROR"
            )
            logger.exception("Security middleware error")
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Internal security error"}
            )
    
    def _get_client_ip(self, request: Request) -> str:
        # Verificar headers de proxy
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"
    
    def _get_validated_paths(self) -> set:
        return {
            "/api/classify",
            "/api/upload-csv",
            "/api/export",
        }
    
    def _add_security_headers(self, response: Response):
        response.headers["X-Content-Type-Options"] = security_config.content_type_options
        response.headers["X-Frame-Options"] = security_config.frame_options
        response.headers["Referrer-Policy"] = security_config.referrer_policy
        response.headers["Permissions-Policy"] = security_config.permissions_policy
        
        if security_config.hsts_enabled:
            response.headers["Strict-Transport-Security"] = f"max-age={security_config.hsts_max_age}; includeSubDomains"
        
        if security_config.csp_policy:
            response.headers["Content-Security-Policy"] = security_config.csp_policy


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """CORS restritivo e configurável"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.enabled = security_config.cors_enabled
        self.allowed_origins = set(security_config.cors_allowed_origins)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)
        
        origin = request.headers.get("origin")
        
        # Preflight
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)
        
        # Verificar origin
        if origin and origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
            response.headers["Access-Control-Max-Age"] = "86400"
        elif origin:
            # Origin não permitido - log de segurança
            audit_logger.log_security_event(
                "CORS_ORIGIN_REJECTED",
                {"origin": origin, "path": request.url.path, "ip": self._get_client_ip(request)},
                severity="WARNING"
            )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
```

### Rate Limiter (Memória + Redis opcional)

```python
# backend/security/rate_limiter.py
import time
import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional
import threading

from .config import security_config

@dataclass
class RateLimitResult:
    allowed: bool
    retry_after: int
    remaining: int
    limit: int

class TokenBucketRateLimiter:
    """
    Rate limiter com Token Bucket algorithm.
    Plug-and-play: pode usar memória local ou Redis.
    """
    
    def __init__(self):
        self.enabled = security_config.rate_limit_enabled
        self.requests_per_minute = security_config.rate_limit_requests_per_minute
        self.burst = security_config.rate_limit_burst
        self.by_ip = security_config.rate_limit_by_ip
        
        # Armazenamento em memória (thread-safe)
        self._buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(self.requests_per_minute, self.burst)
        )
        self._lock = threading.RLock()
        
        # Para Redis (futuro)
        self._redis_client = None
    
    async def check_limit(self, identifier: str, path: str, method: str) -> RateLimitResult:
        if not self.enabled:
            return RateLimitResult(True, 0, self.requests_per_minute, self.requests_per_minute)
        
        # Chave composta: ip:path:method para granularidade
        key = f"{identifier}:{path}:{method}"
        
        with self._lock:
            bucket = self._buckets[key]
            allowed = bucket.consume(1)
            
            return RateLimitResult(
                allowed=allowed,
                retry_after=int(bucket.time_until_ready()) if not allowed else 0,
                remaining=bucket.tokens,
                limit=self.requests_per_minute
            )
    
    def reset(self, identifier: str = None):
        """Reset para testes ou admin"""
        with self._lock:
            if identifier:
                keys_to_remove = [k for k in self._buckets if k.startswith(identifier)]
                for k in keys_to_remove:
                    del self._buckets[k]
            else:
                self._buckets.clear()


class TokenBucket:
    def __init__(self, rate_per_minute: int, burst: int):
        self.rate = rate_per_minute / 60.0  # tokens por segundo
        self.capacity = burst
        self.tokens = float(burst)
        self.last_update = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def time_until_ready(self) -> float:
        if self.tokens >= 1:
            return 0
        return (1 - self.tokens) / self.rate


# Instância global
rate_limiter = TokenBucketRateLimiter()
```

### Sanitizadores de Input

```python
# backend/security/sanitizers.py
import re
import html
import json
from typing import Any, Dict, List, Union
from .config import security_config

# Padrões de SQL Injection
SQL_INJECTION_PATTERNS = [
    r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
    r"(--|#|/\*|\*/)",
    r"(\b(or|and)\b\s+\d+\s*=\s*\d+)",
    r"(\b(or|and)\b\s+['\"]\w+['\"]\s*=\s*['\"]\w+['\"])",
    r"(waitfor\s+delay)",
    r"(benchmark\s*\()",
    r"(sleep\s*\()",
    r"(@@version)",
    r"(sp_|xp_)",
    r"(information_schema)",
    r"(sys\.tables)",
    r"(pg_sleep)",
    r"(dbms_pipe)",
]

# Padrões de Prompt Injection
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"disregard\s+the\s+above",
    r"forget\s+everything",
    r"new\s+instructions?:",
    r"system\s+prompt",
    r"you\s+are\s+now",
    r"act\s+as\s+",
    r"pretend\s+to\s+be",
    r"roleplay\s+as",
    r"simulate\s+",
    r"<\|.*?\|>",
    r"\[INST\].*?\[/INST\]",
    r"<<SYS>>.*?<</SYS>>",
    r"###\s*(instruction|system|user|assistant)",
    r"<\|im_start\|>.*?<\|im_end\|>",
]

# Compilar regex para performance
SQL_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE) for p in SQL_INJECTION_PATTERNS]
PROMPT_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS]


def sanitize_string(value: str, context: str = "general") -> str:
    """
    Sanitiza uma string baseado no contexto.
    Contextos: 'general', 'sql', 'prompt', 'html', 'filename'
    """
    if not isinstance(value, str):
        return value
    
    result = value
    
    # HTML encoding (sempre aplicar)
    if security_config.sanitize_html:
        result = html.escape(result, quote=True)
    
    # SQL Injection protection
    if context in ("sql", "general") and security_config.sanitize_sql:
        for pattern in SQL_PATTERNS_COMPILED:
            result = pattern.sub("[BLOCKED]", result)
    
    # Prompt Injection protection
    if context in ("prompt", "general") and security_config.sanitize_prompt_injection:
        for pattern in PROMPT_PATTERNS_COMPILED:
            result = pattern.sub("[BLOCKED]", result)
    
    # Limitar tamanho
    max_len = security_config.max_prompt_length if context == "prompt" else 10000
    if len(result) > max_len:
        result = result[:max_len] + "...[TRUNCATED]"
    
    return result


def sanitize_request_body(body: bytes, content_type: str) -> bytes:
    """Sanitiza body da request baseado no content-type"""
    if not body:
        return body
    
    try:
        if "application/json" in content_type:
            data = json.loads(body.decode("utf-8"))
            sanitized = _sanitize_json_object(data)
            return json.dumps(sanitized, ensure_ascii=False).encode("utf-8")
        elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
            # Para form data, decodificar e sanitizar campos de texto
            # Implementação simplificada - em produção usar python-multipart
            return body
    except Exception:
        # Se falhar, retornar original (fail-open para não quebrar)
        pass
    
    return body


def sanitize_query_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitiza query parameters"""
    sanitized = {}
    for key, value in params.items():
        sanitized_key = sanitize_string(str(key), "general")
        if isinstance(value, list):
            sanitized[sanitized_key] = [sanitize_string(str(v), "general") for v in value]
        else:
            sanitized[sanitized_key] = sanitize_string(str(value), "general")
    return sanitized


def _sanitize_json_object(obj: Any, path: str = "") -> Any:
    """Recursivamente sanitiza objeto JSON"""
    if isinstance(obj, str):
        # Detectar contexto pelo path
        context = "prompt" if "prompt" in path.lower() or "texto" in path.lower() else "general"
        return sanitize_string(obj, context)
    elif isinstance(obj, dict):
        return {sanitize_string(k, "general"): _sanitize_json_object(v, f"{path}.{k}") for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_json_object(item, f"{path}[{i}]") for i, item in enumerate(obj)]
    return obj


def detect_injection_attempt(value: str, context: str = "general") -> List[str]:
    """Detecta tentativas de injection e retorna lista de padrões encontrados"""
    if not isinstance(value, str):
        return []
    
    detected = []
    lower_value = value.lower()
    
    if context in ("sql", "general"):
        for pattern in SQL_PATTERNS_COMPILED:
            if pattern.search(value):
                detected.append(f"SQL_INJECTION: {pattern.pattern}")
    
    if context in ("prompt", "general"):
        for pattern in PROMPT_PATTERNS_COMPILED:
            if pattern.search(value):
                detected.append(f"PROMPT_INJECTION: {pattern.pattern}")
    
    return detected
```

### Validadores de Schema (Pydantic)

```python
# backend/security/validators.py
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Any
from .config import security_config
from .sanitizers import detect_injection_attempt, sanitize_string

class ValidatedReclamacaoInput(BaseModel):
    """Schema validado para /api/classify"""
    texto: str
    
    @field_validator("texto")
    @classmethod
    def validate_texto(cls, v: str) -> str:
        if not security_config.validate_input_enabled:
            return v
        
        # Verificar tamanho
        if len(v) < 10:
            raise ValueError("Texto muito curto (mínimo 10 caracteres)")
        if len(v) > 5000:
            raise ValueError("Texto muito longo (máximo 5000 caracteres)")
        
        # Detectar injection
        injections = detect_injection_attempt(v, "prompt")
        if injections:
            # Log mas não bloquear (sanitização fará a limpeza)
            from .audit_logger import audit_logger
            audit_logger.log_security_event(
                "INJECTION_DETECTED_INPUT",
                {"field": "texto", "patterns": injections, "length": len(v)},
                severity="WARNING"
            )
        
        return v
    
    @model_validator(mode="after")
    def check_unknown_fields(self):
        if security_config.reject_unknown_fields:
            # Pydantic v2 já rejeita campos extras por default com extra="forbid"
            pass
        return self


class ValidatedCSVUpload(BaseModel):
    """Validação para upload CSV"""
    # Validação feita no endpoint via pandas
    pass


def validate_request_schema(request, path: str):
    """Valida request contra schema conhecido"""
    from dataclasses import dataclass
    
    @dataclass
    class ValidationResult:
        valid: bool
        errors: List[str]
    
    if path == "/api/classify":
        try:
            # Body já foi parseado pelo FastAPI
            # A validação Pydantic acontece automaticamente
            return ValidationResult(True, [])
        except Exception as e:
            return ValidationResult(False, [str(e)])
    
    return ValidationResult(True, [])
```

### Audit Logger

```python
# backend/security/audit_logger.py
import logging
import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import security_config

class SecurityAuditLogger:
    """Logger de auditoria de segurança - thread-safe, rotação de arquivos"""
    
    def __init__(self):
        self.enabled = security_config.audit_log_enabled
        self.logger = self._setup_logger()
        self._lock = threading.Lock()
    
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("finguard.security.audit")
        logger.setLevel(getattr(logging, security_config.audit_log_level))
        logger.propagate = False
        
        # Handler com rotação
        log_path = Path(security_config.audit_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        handler = RotatingFileHandler(
            log_path,
            maxBytes=security_config.audit_log_max_size,
            backupCount=security_config.audit_log_backup_count,
            encoding="utf-8"
        )
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def log_security_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        severity: str = "INFO",
        ip: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Log de evento de segurança"""
        if not self.enabled:
            return
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "details": details,
            "ip": ip,
            "user_id": user_id
        }
        
        with self._lock:
            log_level = getattr(logging, severity.upper(), logging.INFO)
            self.logger.log(log_level, json.dumps(event, ensure_ascii=False))
    
    def log_request(
        self,
        ip: str,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        user_id: Optional[str] = None
    ):
        """Log de request HTTP"""
        if not self.enabled:
            return
        
        # Log apenas requests suspeitos ou erros
        if status_code >= 400 or duration > 5.0:
            self.log_security_event(
                "HTTP_REQUEST",
                {
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2)
                },
                severity="WARNING" if status_code >= 400 else "INFO",
                ip=ip,
                user_id=user_id
            )
    
    def log_llm_interaction(
        self,
        ip: str,
        prompt_length: int,
        response_valid: bool,
        validation_errors: Optional[list] = None,
        model_used: Optional[str] = None
    ):
        """Log de interação com LLM"""
        if not self.enabled:
            return
        
        self.log_security_event(
            "LLM_INTERACTION",
            {
                "prompt_length": prompt_length,
                "response_valid": response_valid,
                "validation_errors": validation_errors or [],
                "model_used": model_used
            },
            severity="INFO" if response_valid else "WARNING",
            ip=ip
        )


# Instância global
audit_logger = SecurityAuditLogger()
```

---

## CAMADA 3: LLM Input Sanitization (Prompt Protection)

### Objetivo
Proteger contra **Prompt Injection** - ataques onde o usuário manipula o prompt para alterar comportamento da LLM.

### Implementação

```python
# backend/security/llm_input_guard.py
import re
from typing import Tuple, List
from dataclasses import dataclass
from .config import security_config
from .audit_logger import audit_logger

@dataclass
class PromptGuardResult:
    safe: bool
    sanitized_prompt: str
    detected_threats: List[str]
    risk_score: int  # 0-100

class LLMInputGuard:
    """
    Guardião de entrada para LLM - protege contra prompt injection.
    Plug-and-play via security_config.
    """
    
    def __init__(self):
        self.enabled = security_config.prompt_injection_protection_enabled
        self.max_length = security_config.max_prompt_length
        self.forbidden_patterns = security_config.forbidden_prompt_patterns
        self._compiled_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.forbidden_patterns]
    
    def analyze_prompt(self, prompt: str, user_ip: str = "unknown") -> PromptGuardResult:
        """Analisa prompt em busca de ameaças"""
        if not self.enabled:
            return PromptGuardResult(True, prompt, [], 0)
        
        detected = []
        risk_score = 0
        
        # 1. Verificar tamanho
        if len(prompt) > self.max_length:
            detected.append(f"PROMPT_TOO_LONG: {len(prompt)} > {self.max_length}")
            risk_score += 30
        
        # 2. Verificar padrões proibidos
        for pattern in self._compiled_patterns:
            matches = pattern.findall(prompt)
            if matches:
                detected.append(f"FORBIDDEN_PATTERN: {pattern.pattern}")
                risk_score += 20
        
        # 3. Heurísticas adicionais
        risk_score += self._heuristic_analysis(prompt, detected)
        
        # 4. Sanitizar
        sanitized = self._sanitize_prompt(prompt)
        
        # 5. Determinar se é seguro
        safe = risk_score < 50  # Threshold configurável
        
        # Log
        if detected:
            audit_logger.log_security_event(
                "PROMPT_INJECTION_ATTEMPT",
                {
                    "detected_threats": detected,
                    "risk_score": risk_score,
                    "prompt_length": len(prompt),
                    "safe": safe
                },
                severity="WARNING" if not safe else "INFO",
                ip=user_ip
            )
        
        return PromptGuardResult(safe, sanitized, detected, risk_score)
    
    def _heuristic_analysis(self, prompt: str, detected: List[str]) -> int:
        """Análise heurística de risco"""
        score = 0
        lower = prompt.lower()
        
        # Múltiplas instruções contraditórias
        instruction_count = lower.count("instru") + lower.count("instruction")
        if instruction_count > 3:
            detected.append("MULTIPLE_INSTRUCTIONS")
            score += 15
        
        # Tentativa de extrair system prompt
        if any(kw in lower for kw in ["system prompt", "system message", "initial prompt", "your instructions"]):
            detected.append("SYSTEM_PROMPT_EXTRACTION")
            score += 25
        
        # Roleplay/impersonation
        if any(kw in lower for kw in ["act as", "pretend to be", "roleplay", "simulate", "you are now"]):
            detected.append("ROLEPLAY_ATTEMPT")
            score += 20
        
        # Encoding/obfuscation
        if any(kw in prompt for kw in ["\\x", "\\u", "%", "&#", "base64", "rot13"]):
            detected.append("OBFUSCATION_DETECTED")
            score += 15
        
        # Repetição excessiva (tentativa de encher contexto)
        words = prompt.split()
        if len(words) > 100:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                detected.append("REPETITION_ATTACK")
                score += 20
        
        return min(score, 50)  # Cap no heurístico
    
    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitiza prompt removendo/neutralizando ameaças"""
        result = prompt
        
        # Remover padrões perigosos
        for pattern in self._compiled_patterns:
            result = pattern.sub("[REMOVIDO - PROMPT INJECTION]", result)
        
        # Truncar se muito longo
        if len(result) > self.max_length:
            result = result[:self.max_length] + "... [TRUNCADO]"
        
        return result


# Instância global
llm_input_guard = LLMInputGuard()
```

### Integração no llm_service.py

```python
# backend/llm_service.py - Modificar classificar_reclamacao
from security.llm_input_guard import llm_input_guard
from security.audit_logger import audit_logger

async def classificar_reclamacao(self, texto: str, max_retries: int = 1) -> Optional[ReclamacaoAnalise]:
    # ... código existente ...
    
    # ANTES de construir prompt - validar input do usuário
    guard_result = llm_input_guard.analyze_prompt(texto, user_ip="from_request_context")
    
    if not guard_result.safe:
        # Log e usar classificação mock como fallback seguro
        logger.warning(f"[LLM] Prompt rejeitado por segurança: {guard_result.detected_threats}")
        audit_logger.log_security_event(
            "LLM_PROMPT_REJECTED",
            {"threats": guard_result.detected_threats, "risk_score": guard_result.risk_score},
            severity="WARNING"
        )
        return self._classificacao_mock(texto)
    
    # Usar prompt sanitizado
    prompt = self._construir_prompt(guard_result.sanitized_prompt)
    
    # ... resto do código ...
```

---

## CAMADA 4: LLM Output Validation

### Objetivo
Validar e sanitizar a resposta da LLM antes de processar/salvar - protege contra:
- JSON malformado
- Valores fora do enum esperado
- Injection no resumo (XSS, SQL)
- Respostas muito longas
- Alucinações perigosas

### Implementação

```python
# backend/security/llm_output_validator.py
import json
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from .config import security_config
from .sanitizers import sanitize_string, detect_injection_attempt
from .audit_logger import audit_logger
from schemas import ReclamacaoAnalise, CategoriaEnum, ProdutoEnum, SentimentoEnum, UrgenciaEnum

@dataclass
class LLMOutputValidationResult:
    valid: bool
    data: Optional[ReclamacaoAnalise]
    errors: List[str]
    warnings: List[str]
    sanitized: bool

class LLMOutputValidator:
    """
    Validador de saída da LLM - garante que resposta está no formato esperado
    e não contém conteúdo perigoso.
    """
    
    def __init__(self):
        self.enabled = security_config.validate_llm_output_enabled
        self.max_length = security_config.llm_output_max_length
        self.allowed_categories = set(security_config.llm_allowed_categories)
        self.allowed_products = set(security_config.llm_allowed_products)
        self.allowed_sentiments = set(security_config.llm_allowed_sentiments)
        self.allowed_urgencies = set(security_config.llm_allowed_urgencies)
    
    def validate(self, llm_response: str, user_ip: str = "unknown") -> LLMOutputValidationResult:
        """Valida resposta completa da LLM"""
        if not self.enabled:
            # Parse básico sem validação
            return self._basic_parse(llm_response)
        
        errors = []
        warnings = []
        sanitized = False
        
        # 1. Verificar tamanho
        if len(llm_response) > self.max_length:
            errors.append(f"Response too long: {len(llm_response)} > {self.max_length}")
            llm_response = llm_response[:self.max_length]
            sanitized = True
        
        # 2. Parse JSON
        try:
            parsed = self._parse_json(llm_response)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {str(e)}")
            audit_logger.log_security_event(
                "LLM_INVALID_JSON",
                {"error": str(e), "response_preview": llm_response[:200]},
                severity="WARNING",
                ip=user_ip
            )
            return LLMOutputValidationResult(False, None, errors, warnings, sanitized)
        
        # 3. Validar campos obrigatórios
        required_fields = ["categoria", "produto", "sentimento", "urgencia", "resumo"]
        for field in required_fields:
            if field not in parsed:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return LLMOutputValidationResult(False, None, errors, warnings, sanitized)
        
        # 4. Validar enums
        categoria = parsed["categoria"]
        if categoria not in self.allowed_categories:
            errors.append(f"Invalid categoria: {categoria}. Allowed: {self.allowed_categories}")
            # Tentar corrigir
            categoria = self._find_closest_match(categoria, self.allowed_categories)
            if categoria:
                warnings.append(f"Corrected categoria to: {categoria}")
                sanitized = True
        
        produto = parsed["produto"]
        if produto not in self.allowed_products:
            errors.append(f"Invalid produto: {produto}. Allowed: {self.allowed_products}")
            produto = self._find_closest_match(produto, self.allowed_products)
            if produto:
                warnings.append(f"Corrected produto to: {produto}")
                sanitized = True
        
        sentimento = parsed["sentimento"]
        if sentimento not in self.allowed_sentiments:
            errors.append(f"Invalid sentimento: {sentimento}. Allowed: {self.allowed_sentiments}")
            sentimento = self._find_closest_match(sentimento, self.allowed_sentiments)
            if sentimento:
                warnings.append(f"Corrected sentimento to: {sentimento}")
                sanitized = True
        
        urgencia = parsed["urgencia"]
        if urgencia not in self.allowed_urgencies:
            errors.append(f"Invalid urgencia: {urgencia}. Allowed: {self.allowed_urgencies}")
            urgencia = self._find_closest_match(urgencia, self.allowed_urgencies)
            if urgencia:
                warnings.append(f"Corrected urgencia to: {urgencia}")
                sanitized = True
        
        # 5. Validar e sanitizar resumo
        resumo = parsed["resumo"]
        if not isinstance(resumo, str):
            errors.append("Resumo must be a string")
            resumo = "Resumo não disponível"
            sanitized = True
        elif len(resumo) > 500:
            warnings.append("Resumo truncado para 500 caracteres")
            resumo = resumo[:500]
            sanitized = True
        
        # Sanitizar resumo (XSS, SQL, profanidade)
        original_resumo = resumo
        resumo = sanitize_string(resumo, "general")
        if resumo != original_resumo:
            sanitized = True
            warnings.append("Resumo sanitizado (conteúdo perigoso removido)")
        
        # Detectar injection no resumo
        injections = detect_injection_attempt(resumo, "general")
        if injections:
            warnings.append(f"Injection patterns detected and neutralized in resumo")
            sanitized = True
        
        # 6. Construir objeto validado
        if errors:
            return LLMOutputValidationResult(False, None, errors, warnings, sanitized)
        
        try:
            analise = ReclamacaoAnalise(
                id="",  # Preenchido pelo caller
                texto_original="",  # Preenchido pelo caller
                categoria=CategoriaEnum(categoria),
                produto=ProdutoEnum(produto),
                sentimento=SentimentoEnum(sentimento),
                urgencia=UrgenciaEnum(urgencia),
                resumo=resumo
            )
            
            # Log sucesso
            audit_logger.log_llm_interaction(
                ip=user_ip,
                prompt_length=0,  # Não temos aqui
                response_valid=True,
                validation_errors=warnings if warnings else None
            )
            
            return LLMOutputValidationResult(True, analise, [], warnings, sanitized)
            
        except Exception as e:
            errors.append(f"Failed to create ReclamacaoAnalise: {str(e)}")
            return LLMOutputValidationResult(False, None, errors, warnings, sanitized)
    
    def _parse_json(self, content: str) -> Dict[str, Any]:
        """Parse JSON robusto - extrai JSON de markdown se necessário"""
        content = content.strip()
        
        # Remover markdown code fences
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        return json.loads(content)
    
    def _basic_parse(self, content: str) -> LLMOutputValidationResult:
        """Parse básico sem validação (fallback)"""
        try:
            parsed = self._parse_json(content)
            analise = ReclamacaoAnalise(
                id="",
                texto_original="",
                categoria=CategoriaEnum(parsed.get("categoria", "Outros")),
                produto=ProdutoEnum(parsed.get("produto", "Não Identificado")),
                sentimento=SentimentoEnum(parsed.get("sentimento", "Neutro")),
                urgencia=UrgenciaEnum(parsed.get("urgencia", "Baixa")),
                resumo=parsed.get("resumo", "Resumo não disponível")
            )
            return LLMOutputValidationResult(True, analise, [], [], False)
        except Exception as e:
            return LLMOutputValidationResult(False, None, [str(e)], [], False)
    
    def _find_closest_match(self, value: str, allowed: set) -> Optional[str]:
        """Encontra correspondência mais próxima (case-insensitive)"""
        lower_value = value.lower().strip()
        for allowed_val in allowed:
            if allowed_val.lower() == lower_value:
                return allowed_val
            # Match parcial
            if lower_value in allowed_val.lower() or allowed_val.lower() in lower_value:
                return allowed_val
        return None


# Instância global
llm_output_validator = LLMOutputValidator()
```

### Integração no llm_service.py (parsear_resposta)

```python
# backend/llm_service.py - Modificar _parsear_resposta
from security.llm_output_validator import llm_output_validator

def _parsear_resposta(self, content: str) -> Optional[ReclamacaoAnalise]:
    """Parseia a resposta JSON da LLM com validação de segurança"""
    try:
        # Usar validador de segurança
        result = llm_output_validator.validate(content, user_ip="from_context")
        
        if result.valid and result.data:
            if result.warnings:
                logger.warning(f"[LLM] Output validation warnings: {result.warnings}")
            if result.sanitized:
                logger.info("[LLM] Output was sanitized")
            return result.data
        
        # Log erros
        for error in result.errors:
            logger.error(f"[LLM] Output validation error: {error}")
        
        return None
        
    except Exception as e:
        logger.error(f"Erro ao parsear resposta da LLM: {e}")
        return None
```

---

## INTEGRAÇÃO COMPLETA NO MAIN.PY

```python
# backend/main.py - Adicionar middlewares de segurança
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from security.middleware import SecurityMiddleware, CORSSecurityMiddleware
from security.config import security_config, load_security_config_from_env

# Carregar config de segurança
security_config = load_security_config_from_env()

app = FastAPI(
    title="FinGuard API",
    description="API para triagem inteligente de reclamações financeiras",
    version="1.0.0"
)

# 1. Security Middleware (primeiro - processa tudo)
app.add_middleware(SecurityMiddleware)

# 2. CORS Security Middleware (depois do security)
app.add_middleware(CORSSecurityMiddleware)

# 3. CORS padrão do FastAPI (para compatibilidade)
if security_config.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=security_config.cors_allowed_origins,
        allow_credentials=security_config.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        max_age=86400,
    )

# ... resto do código ...
```

---

## CONFIGURAÇÃO VIA VARIÁVEIS DE AMBIENTE (.env)

```bash
# backend/.env.security
# ===========================================
# CONFIGURAÇÃO DE SEGURANÇA - PLUG-AND-PLAY
# ===========================================

# Controle Global
SECURITY_ENABLED=true
SECURITY_LEVEL=strict  # disabled, basic, strict, paranoid

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_RPM=60
RATE_LIMIT_BURST=10

# Request Limits
MAX_REQUEST_SIZE=10485760
MAX_JSON_SIZE=1048576
MAX_CSV_ROWS=1000

# Input Validation
VALIDATE_INPUT_ENABLED=true
STRICT_SCHEMA_VALIDATION=true
REJECT_UNKNOWN_FIELDS=true

# Sanitization
SANITIZE_INPUT_ENABLED=true
SANITIZE_HTML=true
SANITIZE_SQL=true
SANITIZE_PROMPT_INJECTION=true

# CORS
CORS_ENABLED=true
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
CORS_ALLOW_CREDENTIALS=true

# Security Headers
SECURITY_HEADERS_ENABLED=true
HSTS_ENABLED=true
HSTS_MAX_AGE=31536000
FRAME_OPTIONS=DENY
CSP_POLICY="default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' http://localhost:8000;"

# SQL Protection
SQL_PROTECTION_ENABLED=true
LOG_SQL_ERRORS=true

# Prompt Injection
PROMPT_INJECTION_PROTECTION_ENABLED=true
MAX_PROMPT_LENGTH=8000

# Audit Logging
AUDIT_LOG_ENABLED=true
AUDIT_LOG_LEVEL=WARNING
AUDIT_LOG_FILE=security_audit.log
AUDIT_LOG_MAX_SIZE=10485760
AUDIT_LOG_BACKUP_COUNT=5

# LLM Output Validation
VALIDATE_LLM_OUTPUT_ENABLED=true
LLM_OUTPUT_MAX_LENGTH=2000
```

---

## COMO APRESENTAR NA DEMONSTRAÇÃO

### Slide 1: Arquitetura de Segurança em 4 Camadas
```
┌─────────────────────────────────────────────────────────────┐
│                    FINEGUARD - SEGURANÇA                    │
│                  Arquitetura Plug-and-Play                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  FRONTEND   │─▶│  BACKEND    │─▶│  LLM INPUT  │─▶│ LLM OUTPUT  │
│  (Camada 1) │  │  (Camada 2) │  │  (Camada 3) │  │  (Camada 4) │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
     │               │               │               │
     ▼               ▼               ▼               ▼
Validação      Rate Limit      Prompt Guard    Schema Validation
Sanitização    Security        Injection       Enum Validation
XSS Protection Headers         Detection       Sanitização
                                      Heuristics    Auditoria
```

### Slide 2: Plug-and-Play - Uma Linha para Habilitar/Desabilitar
```python
# Tudo configurável via .env - ZERO código alterado
SECURITY_ENABLED=true           # Liga/desliga tudo
SECURITY_LEVEL=strict           # basic, strict, paranoid
RATE_LIMIT_ENABLED=true         # Rate limiting
PROMPT_INJECTION_PROTECTION_ENABLED=true  # Prompt guard
VALIDATE_LLM_OUTPUT_ENABLED=true          # Output validator
```

### Slide 3: Demonstração de Ataques Bloqueados
| Ataque | Camada | Resultado |
|--------|--------|-----------|
| `<script>alert(1)</script>` | Frontend + Backend | Bloqueado + Sanitizado |
| `'; DROP TABLE users; --` | Backend (SQL) | Detectado + Neutralizado |
| `Ignore previous instructions...` | LLM Input (Camada 3) | Detectado (risk_score: 70) → Mock |
| `{"categoria": "HACKED", "resumo": "<script>..."}` | LLM Output (Camada 4) | Rejeitado + Valores corrigidos |

### Slide 4: Auditoria Completa
```json
// security_audit.log - Rastreabilidade total
{
  "timestamp": "2024-01-15T10:30:45",
  "event_type": "PROMPT_INJECTION_ATTEMPT",
  "severity": "WARNING",
  "details": {
    "detected_threats": ["ROLEPLAY_ATTEMPT", "SYSTEM_PROMPT_EXTRACTION"],
    "risk_score": 65,
    "safe": false
  },
  "ip": "192.168.1.100"
}
```

---

## CHECKLIST DE IMPLEMENTAÇÃO

### Fase 1: Backend Core (Prioridade Alta)
- [ ] Criar pasta `backend/security/`
- [ ] Implementar `config.py` com SecurityConfig
- [ ] Implementar `middleware.py` (SecurityMiddleware + CORSSecurityMiddleware)
- [ ] Implementar `rate_limiter.py` (TokenBucket)
- [ ] Implementar `sanitizers.py` (SQL, Prompt, HTML, XSS)
- [ ] Implementar `validators.py` (Pydantic schemas)
- [ ] Implementar `audit_logger.py` (RotatingFileHandler)
- [ ] Implementar `llm_input_guard.py` (Prompt injection protection)
- [ ] Implementar `llm_output_validator.py` (Schema + enum validation)
- [ ] Integrar no `main.py` (middlewares)
- [ ] Integrar no `llm_service.py` (input guard + output validator)
- [ ] Criar `.env.security` exemplo

### Fase 2: Frontend (Prioridade Média)
- [ ] Criar `frontend/src/security/validationRules.js`
- [ ] Criar `frontend/src/security/FrontendValidator.js`
- [ ] Integrar no `ChatPanel.jsx`
- [ ] Integrar no `TicketTable.jsx` (upload CSV)
- [ ] Adicionar endpoint `/api/security/log` no backend para receber logs do frontend

### Fase 3: Testes e Validação (Prioridade Alta)
- [ ] Testes de SQL Injection
- [ ] Testes de Prompt Injection
- [ ] Testes de XSS
- [ ] Testes de Rate Limiting
- [ ] Testes de CORS
- [ ] Testes de Security Headers
- [ ] Testes de LLM Output Validation
- [ ] Cenários de ataque combinados

### Fase 4: Documentação para Apresentação
- [ ] Diagrama de arquitetura
- [ ] Tabela de ataques bloqueados
- [ ] Exemplos de logs de auditoria
- [ ] Guia de configuração (.env)
- [ ] Demo script

---

## DEPENDÊNCIAS ADICIONAIS NECESSÁRIAS

```txt
# backend/requirements-security.txt
# Adicionar ao requirements.txt principal
slowapi==0.1.9          # Rate limiting avançado (opcional, alternativa ao nosso)
python-multipart==0.0.6 # Já existe
# Para Redis rate limiting (futuro):
# redis==5.0.1
# aioredis==2.0.1
```

---

## CONCLUSÃO

Esta arquitetura fornece:

1. **Defesa em Profundidade**: 4 camadas independentes
2. **Plug-and-Play**: Tudo configurável via `.env` sem mudar código
3. **Auditoria Completa**: Logs estruturados para compliance
4. **Performance**: Rate limiting com Token Bucket, sanitização otimizada
5. **Flexibilidade**: Cada camada pode ser ajustada independentemente
6. **Apresentável**: Diagramas claros, métricas de ataques bloqueados, logs reais

O apresentador pode demonstrar:
- Configuração via `.env` (ligar/desligar camadas)
- Logs de auditoria em tempo real
- Tentativas de ataque bloqueadas
- Fallback seguro (mock) quando LLM é perigoso