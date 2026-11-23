from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import uuid
from datetime import datetime
import pandas as pd
import io
import logging
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env
load_dotenv()

# Configurar logging com data/hora local
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("backend.log", encoding="utf-8"),
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


app = FastAPI(
    title="FinGuard API",
    description="API para triagem inteligente de reclamações financeiras",
    version="1.0.0"
)

# CORS para permitir frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return {"status": "ok"}


@app.post("/api/classify", response_model=ClassifyResponse)
async def classificar_reclamacao(input_data: ReclamacaoInput):
    """
    Classifica uma única reclamação via chatbot.
    Recebe texto livre e retorna análise estruturada.
    """
    try:
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
    except Exception as e:
        return ClassifyResponse(success=False, error=str(e))


@app.post("/api/upload-csv", response_model=BatchResponse)
async def upload_csv(file: UploadFile = File(...)):
    """
    Processa arquivo CSV em lote com concorrência controlada.
    Espera colunas: id, data_reclamacao, canal, texto_reclamacao, produto, status
    """
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Arquivo deve ser CSV")
        
        # Ler CSV
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        # Validar colunas obrigatórias
        colunas_esperadas = ['id', 'data_reclamacao', 'canal', 'texto_reclamacao', 'produto', 'status']
        for col in colunas_esperadas:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Coluna obrigatória ausente: {col}")
        
        # Processar com concorrência limitada
        async def processar_linha(row):
            async with SEMAPHORE:
                try:
                    texto = str(row['texto_reclamacao']).strip()
                    if not texto or texto.lower() == 'nan':
                        return {"id": row['id'], "sucesso": False, "erro": "Texto vazio"}
                    
                    analise = await llm_service.classificar_reclamacao(texto)
                    
                    if not analise:
                        return {"id": row['id'], "sucesso": False, "erro": "Falha na classificação"}
                    
                    analise.id = str(row['id'])
                    analise.texto_original = texto
                    analise.data_registro = str(row['data_reclamacao'])
                    analise.canal = str(row['canal'])
                    
                    repository.salvar(analise)
                    return {"id": row['id'], "sucesso": True}
                except Exception as e:
                    return {"id": row['id'], "sucesso": False, "erro": str(e)}
        
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


# Serve o frontend em JavaScript puro (../frontjs) em http://localhost:8000/app/
FRONTJS_DIR = Path(__file__).resolve().parent.parent / "frontjs"
if FRONTJS_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=FRONTJS_DIR, html=True), name="frontjs")


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