import json
import os
import asyncio
import logging
import math
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit
import httpx
from schemas import (
    ReclamacaoAnalise,
    CategoriaEnum,
    ProdutoEnum,
    SentimentoEnum,
    UrgenciaEnum,
)
from sanitizer import sanitizar_resumo

logger = logging.getLogger("finguard")


class LLMService:
    def __init__(self):
        self.realm = os.getenv("STACKSPOT_REALM", "").strip()
        self.client_id = os.getenv("STACKSPOT_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("STACKSPOT_CLIENT_SECRET", "").strip()
        self.agent_url = os.getenv("STACKSPOT_AGENT_URL", "").strip()
        self._token = None
        self._expires_at = 0.0
        self._token_lock = asyncio.Lock()
        self.politica_interna = self._carregar_politica_interna()

    def _carregar_politica_interna(self) -> str:
        """Carrega a política interna do arquivo local."""
        try:
            with Path(__file__).with_name("politica_interna.txt").open("r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "Política interna não encontrada. Use as diretrizes padrão."

    def _construir_prompt(self, texto_reclamacao: str) -> str:
        """Constrói o prompt do sistema com a política interna injetada."""
        return f"""Você é o FinGuard, um assistente especializado em análise e triagem de reclamações de instituições financeiras.
Sua tarefa é analisar o texto da reclamação fornecido e retornar EXCLUSIVAMENTE um objeto JSON estruturado.

Diretrizes da Política Interna:
<politica_interna>
{self.politica_interna}
</politica_interna>

Regras de Classificação:
1. Categoria: Escolha exatamente uma entre: ["Cobrança Indevida", "Atendimento", "Fraude/Segurança", "Produto/Serviço", "Cancelamento", "Outros"].
2. Produto: Escolha exatamente um entre: ["Cartão de Crédito", "Conta Corrente", "Empréstimo", "Investimentos", "Seguros", "Não Identificado"].
3. Sentimento: Escolha entre: ["Positivo", "Neutro", "Negativo", "Crítico"].
4. Urgencia: Escolha entre: ["Baixa", "Média", "Alta", "Crítica"].
5. Resumo: Escreva um resumo conciso (2 a 3 linhas) em linguagem formal e padronizada. NUNCA inclua palavras impróprias ou ofensivas.

Saída esperada: Responda APENAS com o JSON no formato:
{{
  "categoria": "...",
  "produto": "...",
  "sentimento": "...",
  "urgencia": "...",
  "resumo": "..."
}}

Texto da reclamação para análise:
{texto_reclamacao}"""

    async def classificar_reclamacao(
        self, texto: str, max_retries: int = 1
    ) -> Optional[ReclamacaoAnalise]:
        """
        Classifica uma reclamação usando o agente StackSpot.

        Args:
            texto: Texto da reclamação
            max_retries: Número máximo de tentativas se o parsing falhar

        Returns:
            ReclamacaoAnalise ou None se falhar
        """
        if not all((self.realm, self.client_id, self.client_secret, self.agent_url)):
            logger.error("[LLM] Configuração StackSpot incompleta.")
            return None
        url = urlsplit(self.agent_url)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.realm) or url.scheme != "https" or not url.hostname or url.username or url.password:
            logger.error("[LLM] Configuração StackSpot inválida.")
            return None

        prompt = self._construir_prompt(texto)

        for tentativa in range(max_retries + 1):
            try:
                resultado = await self._chamar_llm(prompt)
                if resultado:
                    # Sanitizar o resumo
                    resultado.resumo = sanitizar_resumo(resultado.resumo)
                    return resultado
            except (httpx.HTTPError, ValueError, TypeError, KeyError) as erro:
                logger.warning("[LLM] Tentativa %d falhou (%s).", tentativa + 1, type(erro).__name__)
            if tentativa < max_retries:
                await asyncio.sleep(1)

        return None

    async def _obter_token(self, client: httpx.AsyncClient) -> str:
        async with self._token_lock:
            if self._token and time.monotonic() < self._expires_at:
                return self._token
            inicio = time.monotonic()
            response = await client.post(
                f"https://idm.stackspot.com/{self.realm}/oidc/oauth/token",
                data={"grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self.client_secret},
                timeout=60.0,
            )
            response.raise_for_status()
            dados = response.json()
            token = dados["access_token"]
            validade = float(dados["expires_in"])
            if not isinstance(token, str) or not token.strip() or not math.isfinite(validade) or validade <= 0:
                raise ValueError("Token StackSpot inválido.")
            self._token = token
            self._expires_at = inicio + validade - min(30, validade * 0.1)
            return token

    async def _invalidar_token(self, token: str) -> None:
        async with self._token_lock:
            if self._token == token:
                self._token = None
                self._expires_at = 0.0

    @staticmethod
    def _extrair_classificacao(resposta) -> dict:
        campos = {"categoria", "produto", "sentimento", "urgencia", "resumo"}
        valor = resposta
        for _ in range(8):
            if isinstance(valor, dict):
                if campos.issubset(valor):
                    return valor
                for chave in ("message", "response", "result", "content", "text"):
                    if chave in valor and valor[chave] is not None:
                        valor = valor[chave]
                        break
                else:
                    raise ValueError("Resposta StackSpot sem classificação.")
            elif isinstance(valor, str):
                texto = valor.strip()
                bloco = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", texto, re.IGNORECASE | re.DOTALL)
                valor = json.loads(bloco.group(1) if bloco else texto)
            else:
                raise ValueError("Formato de resposta StackSpot inválido.")
        raise ValueError("Resposta StackSpot contém aninhamento excessivo.")

    async def _chamar_llm(self, prompt: str) -> Optional[ReclamacaoAnalise]:
        """Chama o agente StackSpot em modo não streaming."""
        payload = {
            "streaming": False,
            "user_prompt": prompt,
            "stackspot_knowledge": True,
            "return_ks_in_response": False,
            "deep_search_ks": False,
        }
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=False) as client:
            for tentativa in range(2):
                token = await self._obter_token(client)
                response = await client.post(self.agent_url, headers={"Authorization": f"Bearer {token}"}, json=payload)
                if response.status_code == 401 and tentativa == 0:
                    await self._invalidar_token(token)
                    continue
                response.raise_for_status()
                dados = self._extrair_classificacao(response.json())
                return self._parsear_resposta(json.dumps(dados, ensure_ascii=False))
        return None

    def _parsear_resposta(self, content: str) -> Optional[ReclamacaoAnalise]:
        """Parseia a resposta JSON da LLM."""
        try:
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            dados = json.loads(content)

            categoria = CategoriaEnum(dados["categoria"])
            produto = ProdutoEnum(dados["produto"])
            sentimento = SentimentoEnum(dados["sentimento"])
            urgencia = UrgenciaEnum(dados["urgencia"])
            resumo = dados["resumo"]
            if not isinstance(resumo, str) or not resumo.strip():
                raise ValueError("Resumo inválido.")

            return ReclamacaoAnalise(
                id="",  # Será preenchido pelo chamador
                texto_original="",  # Será preenchido pelo chamador
                categoria=categoria,
                produto=produto,
                sentimento=sentimento,
                urgencia=urgencia,
                resumo=resumo,
            )
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            logger.warning("[LLM] Resposta StackSpot inválida.")
            return None

# Instância global
llm_service = LLMService()
