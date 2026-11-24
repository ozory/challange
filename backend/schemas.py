from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from security.config import security_config


class CategoriaEnum(str, Enum):
    COBRANCA_INDEVIDA = "Cobrança Indevida"
    ATENDIMENTO = "Atendimento"
    FRAUDE_SEGURANCA = "Fraude/Segurança"
    PRODUTO_SERVICO = "Produto/Serviço"
    CANCELAMENTO = "Cancelamento"
    OUTROS = "Outros"


class ProdutoEnum(str, Enum):
    CARTAO_CREDITO = "Cartão de Crédito"
    CONTA_CORRENTE = "Conta Corrente"
    EMPRESTIMO = "Empréstimo"
    INVESTIMENTOS = "Investimentos"
    SEGUROS = "Seguros"
    NAO_IDENTIFICADO = "Não Identificado"


class SentimentoEnum(str, Enum):
    POSITIVO = "Positivo"
    NEUTRO = "Neutro"
    NEGATIVO = "Negativo"
    CRITICO = "Crítico"


class UrgenciaEnum(str, Enum):
    BAIXA = "Baixa"
    MEDIA = "Média"
    ALTA = "Alta"
    CRITICA = "Crítica"


class ReclamacaoInput(BaseModel):
    texto: str = Field(max_length=security_config.max_text_length * 2)  # teto duro; guard faz o resto


class ReclamacaoAnalise(BaseModel):
    id: str = Field(description="Identificador único da reclamação")
    texto_original: str
    categoria: CategoriaEnum
    produto: ProdutoEnum
    sentimento: SentimentoEnum
    urgencia: UrgenciaEnum
    resumo: str = Field(description="Resumo de 2-3 linhas sem palavras impróprias")
    data_registro: Optional[str] = None
    canal: Optional[str] = None


class ReclamacaoCSV(BaseModel):
    id: str
    data_reclamacao: str
    canal: str
    texto_reclamacao: str
    produto: str
    status: str


class MetricasResponse(BaseModel):
    total: int
    por_categoria: dict
    por_produto: dict
    por_sentimento: dict
    por_urgencia: dict


class ExportRequest(BaseModel):
    format: str = "json"  # json, csv, html