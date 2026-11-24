from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
import pandas as pd
import io
import logging
import os
import sys
from dotenv import dotenv_values, load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")
arquivo_compartilhado = os.getenv("STACKSPOT_ENV_FILE", "").strip()
if arquivo_compartilhado:
    caminho = Path(arquivo_compartilhado).expanduser()
    if not caminho.is_absolute():
        caminho = BACKEND_DIR / caminho
    valores = dotenv_values(caminho)
    for nome in ("STACKSPOT_REALM", "STACKSPOT_CLIENT_ID", "STACKSPOT_CLIENT_SECRET",
                 "STACKSPOT_AGENT_ID", "STACKSPOT_AGENT_URL"):
        if not os.environ.get(nome) and valores.get(nome):
            os.environ[nome] = valores[nome]

# Configurar logging com data/hora local.
# O arquivo fica junto do backend (independe do diretório de execução) e aceita override por env.
APP_LOG_FILE = Path(os.getenv("APP_LOG_FILE", "").strip() or BACKEND_DIR / "backend.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(APP_LOG_FILE, encoding="utf-8"),
    ],
)

logger = logging.getLogger("finguard")

from schemas import (
    ReclamacaoInput, ReclamacaoAnalise, ReclamacaoCSV, 
    MetricasResponse, CategoriaEnum, ProdutoEnum, 
    SentimentoEnum, UrgenciaEnum, ExportRequest
)
from llm_service import llm_service
from repository import repository
from exporter import exporter
from sanitizer import sanitizar_resumo
from security.config import security_config as sec
from security.middleware import SecurityMiddleware, client_ip
from security.exceptions import SecurityViolation
from security.sanitizers import clean_text, clean_field
from security.audit_logger import log_event
from security.pii_masker import mask_pii


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Deixa explícito no log qual provedor de LLM está ativo e se o .env está completo."""
    cfg = llm_service.resumo_configuracao()
    logger.info("[LLM] Provedor: %s", cfg["provedor"])
    logger.info("[LLM] Agente: %s", cfg["agent_id"])
    logger.info("[LLM] Endpoint de inferência: %s", cfg["endpoint"])
    logger.info("[LLM] Endpoint de autenticação: %s", cfg["token_url"])
    problemas = llm_service.problemas_de_configuracao()
    if problemas:
        logger.error("[LLM] StackSpot indisponível: %s. Ajuste o backend/.env antes de classificar.",
                     "; ".join(problemas))
    else:
        logger.info("[LLM] Credenciais StackSpot carregadas; classificação habilitada.")
    logger.info("[APP] Log da aplicação: %s", APP_LOG_FILE)
    logger.info("[APP] Frontend servido em /app")
    yield


app = FastAPI(
    title="FinGuard API",
    description="API para triagem inteligente de reclamações financeiras",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS para permitir frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=sec.cors_origins,  # CORS_ORIGINS no .env
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)
# Camada 2: headers de segurança, rate limit e limite de tamanho (adicionado por último = mais externo)
app.add_middleware(SecurityMiddleware)


# Semaphore para limitar concorrência no processamento em lote
SEMAPHORE = asyncio.Semaphore(5)


class ClassifyResponse(BaseModel):
    success: bool
    data: Optional[ReclamacaoAnalise] = None
    error: Optional[str] = None


class BatchResponse(BaseModel):
    success: bool
    processados: int
    erros: int
    detalhes: List[dict]


@app.get("/")
async def root():
    return {"message": "FinGuard API - Triagem Inteligente de Reclamações", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Saúde da API e estado da integração com a StackSpot (sem expor segredos)."""
    llm = llm_service.resumo_configuracao()
    return {
        "status": "ok" if llm["configurado"] else "degraded",
        "llm": llm,
        "frontend": "/app",
    }


@app.post("/api/classify", response_model=ClassifyResponse)
async def classificar_reclamacao(input_data: ReclamacaoInput):
    """
    Classifica uma única reclamação via chatbot.
    Recebe texto livre e retorna análise estruturada.
    """
    try:
        if sec.layer(sec.backend_enabled):
            input_data.texto = mask_pii(clean_text(input_data.texto, sec.max_text_length))
        if not input_data.texto or not input_data.texto.strip():
            raise HTTPException(status_code=400, detail="Texto da reclamação não pode ser vazio")
        
        # Gerar ID único
        reclamacao_id = f"REC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # Classificar via LLM
        analise = await llm_service.classificar_reclamacao(input_data.texto.strip())
        
        if not analise:
            raise HTTPException(status_code=500, detail="Falha na classificação da reclamação")
        
        # Preencher campos obrigatórios
        analise.id = reclamacao_id
        analise.texto_original = input_data.texto.strip()
        analise.data_registro = datetime.now().isoformat()
        analise.canal = "Chatbot"
        
        # Salvar no repositório
        repository.salvar(analise)
        
        return ClassifyResponse(success=True, data=analise)
    
    except HTTPException:
        raise
    except SecurityViolation as e:
        raise HTTPException(status_code=400, detail=e.public_message)
    except Exception as e:
        logger.exception("Erro ao classificar")
        return ClassifyResponse(success=False, error="Erro interno ao classificar a reclamação")


@app.post("/api/upload-csv", response_model=BatchResponse)
async def upload_csv(file: UploadFile = File(...)):
    """
    Processa arquivo CSV em lote com concorrência controlada.
    Espera colunas: id, data_reclamacao, canal, texto_reclamacao, produto, status
    """
    try:
        if not (file.filename or "").lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail="Arquivo deve ser CSV")
        
        # Ler CSV (com teto de tamanho, independente do Content-Length)
        content = await file.read(sec.max_request_bytes + 1)
        if len(content) > sec.max_request_bytes:
            log_event("CSV_TOO_LARGE", "backend", filename=file.filename)
            raise HTTPException(status_code=413, detail="Arquivo CSV muito grande")
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception:
            raise HTTPException(status_code=400, detail="CSV inválido ou corrompido")
        if len(df) > sec.max_csv_rows:
            log_event("CSV_TOO_MANY_ROWS", "backend", rows=len(df))
            raise HTTPException(status_code=413, detail=f"CSV excede o limite de {sec.max_csv_rows} linhas")
        
        # Validar colunas obrigatórias
        colunas_esperadas = ['id', 'data_reclamacao', 'canal', 'texto_reclamacao', 'produto', 'status']
        for col in colunas_esperadas:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Coluna obrigatória ausente: {col}")
        
        # Processar com concorrência limitada
        async def processar_linha(row):
            async with SEMAPHORE:
                try:
                    texto = mask_pii(str(row['texto_reclamacao']).strip())
                    if not texto or texto.lower() == 'nan':
                        return {"id": row['id'], "sucesso": False, "erro": "Texto vazio"}
                    
                    analise = await llm_service.classificar_reclamacao(texto)
                    
                    if not analise:
                        return {"id": row['id'], "sucesso": False, "erro": "Falha na classificação"}
                    
                    analise.id = clean_field(row['id'], 64)
                    analise.texto_original = clean_text(texto, sec.max_text_length)
                    analise.data_registro = clean_field(row['data_reclamacao'], 64)
                    analise.canal = clean_field(row['canal'], 64)
                    
                    repository.salvar(analise)
                    return {"id": row['id'], "sucesso": True}
                except SecurityViolation as e:
                    return {"id": row['id'], "sucesso": False, "erro": e.public_message}
                except Exception:
                    logger.exception("Erro ao processar linha do CSV")
                    return {"id": row['id'], "sucesso": False, "erro": "Erro ao processar linha"}
        
        # Executar processamento paralelo
        tarefas = [processar_linha(row) for _, row in df.iterrows()]
        resultados = await asyncio.gather(*tarefas)
        
        processados = sum(1 for r in resultados if r["sucesso"])
        erros = sum(1 for r in resultados if not r["sucesso"])
        
        return BatchResponse(
            success=True,
            processados=processados,
            erros=erros,
            detalhes=resultados
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar CSV: {str(e)}")


class FrontendSecurityEvent(BaseModel):
    type: str
    detail: Optional[str] = None


_FRONTEND_EVENTS = {"FORBIDDEN_INPUT", "TEXT_TOO_LONG", "SUSPICIOUS_PATTERN", "CSV_REJECTED"}


@app.post("/api/security/log", status_code=204)
async def registrar_evento_frontend(event: FrontendSecurityEvent, request: Request):
    """Recebe eventos bloqueados pela camada 1 (apenas tipos conhecidos, texto truncado)."""
    if event.type in _FRONTEND_EVENTS:
        log_event(event.type, "frontend", ip=client_ip(request), detail=(event.detail or "")[:100])


@app.get("/api/tickets", response_model=List[ReclamacaoAnalise])
async def listar_reclamacoes():
    """Retorna todas as reclamações processadas."""
    try:
        reclamacoes = repository.buscar_todas()
        return reclamacoes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics", response_model=MetricasResponse)
async def obter_metricas():
    """Retorna métricas agregadas para o Dashboard."""
    try:
        metricas = repository.obter_metricas()
        return metricas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export")
async def exportar_dados(format: str = Query("json", enum=["json", "csv", "html"])):
    """Exporta dados processados em JSON, CSV ou HTML."""
    try:
        reclamacoes = repository.buscar_todas()
        
        if format == "json":
            content = exporter.to_json(reclamacoes)
            media_type = "application/json"
            filename = "reclamacoes.json"
        elif format == "csv":
            content = exporter.to_csv(reclamacoes)
            media_type = "text/csv"
            filename = "reclamacoes.csv"
        elif format == "html":
            content = exporter.to_html(reclamacoes)
            media_type = "text/html"
            filename = "relatorio.html"
        else:
            raise HTTPException(status_code=400, detail="Formato inválido")
        
        return StreamingResponse(
            io.BytesIO(content.encode('utf-8')),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/tickets")
async def limpar_reclamacoes():
    """Remove todas as reclamações (útil para testes)."""
    try:
        repository.limpar_tudo()
        return {"success": True, "message": "Todas as reclamações foram removidas"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve o frontend em JavaScript puro (../frontend) em http://localhost:8000/app/
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    # Configurar uvicorn para usar nosso logger
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["access"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_config=log_config
    )