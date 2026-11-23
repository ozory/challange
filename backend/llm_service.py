import json
import os
import asyncio
import logging
import ssl
from typing import Optional
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


def _criar_contexto_ssl():
    """
    Define em quem o httpx confia ao validar o HTTPS.

    Redes corporativas costumam reassinar o tráfego com uma CA própria, instalada no
    repositório de certificados do sistema mas ausente do `certifi` (usado por padrão).
    Ordem de preferência:
      1. LLM_CA_BUNDLE=<caminho .pem>  -> bundle de CA explícito
      2. truststore                    -> repositório de certificados do SO (Windows/macOS)
      3. padrão do httpx (certifi)
    """
    ca_bundle = os.getenv("LLM_CA_BUNDLE")
    if ca_bundle:
        return ssl.create_default_context(cafile=ca_bundle)
    try:
        import truststore
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        logger.warning("[LLM] 'truststore' não instalado; usando certificados do certifi")
        return True


class LLMService:
    def __init__(self):
        self.api_key = os.getenv("OPEN_ROUTER_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        # Modelo gratuito válido no OpenRouter (NVIDIA Nemotron 3 Ultra)
        self.model = "nvidia/nemotron-3-ultra-550b-a55b:free"
        self.politica_interna = self._carregar_politica_interna()

    def _carregar_politica_interna(self) -> str:
        """Carrega a política interna do arquivo local."""
        try:
            with open("politica_interna.txt", "r", encoding="utf-8") as f:
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
        Classifica uma reclamação usando a LLM com fallback para mock.

        Args:
            texto: Texto da reclamação
            max_retries: Número máximo de tentativas se o parsing falhar

        Returns:
            ReclamacaoAnalise ou None se falhar
        """
        # Se não tem API key, usa mock direto
        if not self.api_key:
            logger.info("[LLM] Sem API key configurada - usando classificação mock")
            return self._classificacao_mock(texto)

        prompt = self._construir_prompt(texto)

        for tentativa in range(max_retries + 1):
            try:
                resultado = await self._chamar_llm(prompt)
                if resultado:
                    # Sanitizar o resumo
                    resultado.resumo = sanitizar_resumo(resultado.resumo)
                    return resultado
            except Exception as e:
                logger.error(f"[LLM] Tentativa {tentativa + 1} falhou: {e}")
                # Se for erro de rate limit, quota, ou modelo não encontrado, cai para mock
                if "429" in str(e) or "402" in str(e) or "404" in str(e) or "quota" in str(e).lower():
                    logger.warning(f"[LLM] Fallback para classificação mock devido a limite da API (modelo: {self.model})")
                    return self._classificacao_mock(texto)
                if tentativa == max_retries:
                    # Última tentativa falhou - usa mock como fallback final
                    logger.warning("Todas as tentativas falharam, usando mock como fallback")
                    return self._classificacao_mock(texto)
                await asyncio.sleep(1)  # Pequeno delay antes de retry

        return None

    async def _chamar_llm(self, prompt: str) -> Optional[ReclamacaoAnalise]:
        """Chama a API da LLM via OpenRouter."""
        logger.info(f"[LLM] Modelo em uso: {self.model}")
        logger.info(f"[LLM] Endpoint: {self.base_url}/chat/completions")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "FinGuard",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Você é um classificador de reclamações financeiras. Responda APENAS com JSON válido.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 500,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=30.0, verify=_criar_contexto_ssl()) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=payload
            )
            logger.info(f"[LLM] Response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()

            # Log do modelo efetivamente usado (pode diferir do solicitado se houver fallback)
            model_used = data.get("model", self.model)
            logger.info(f"[LLM] Modelo efetivamente usado: {model_used}")

            content = data["choices"][0]["message"]["content"]
            return self._parsear_resposta(content)

    def _parsear_resposta(self, content: str) -> Optional[ReclamacaoAnalise]:
        """Parseia a resposta JSON da LLM."""
        try:
            # Tentar extrair JSON se houver texto extra
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            dados = json.loads(content)

            # Validar enums
            categoria = CategoriaEnum(dados.get("categoria", "Outros"))
            produto = ProdutoEnum(dados.get("produto", "Não Identificado"))
            sentimento = SentimentoEnum(dados.get("sentimento", "Neutro"))
            urgencia = UrgenciaEnum(dados.get("urgencia", "Baixa"))
            resumo = dados.get("resumo", "Resumo não disponível")

            return ReclamacaoAnalise(
                id="",  # Será preenchido pelo chamador
                texto_original="",  # Será preenchido pelo chamador
                categoria=categoria,
                produto=produto,
                sentimento=sentimento,
                urgencia=urgencia,
                resumo=resumo,
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Erro ao parsear resposta da LLM: {e}")
            logger.debug(f"Conteúdo recebido: {content}")
            return None

    def _classificacao_mock(self, texto: str) -> ReclamacaoAnalise:
        """Classificação mock para desenvolvimento sem API key."""
        logger.info(f"[LLM] Usando classificação mock (modelo solicitado: {self.model})")
        texto_lower = texto.lower()

        # Lógica simples baseada em palavras-chave
        if any(
            p in texto_lower
            for p in [
                "fraude",
                "não autoriz",
                "acessou minha conta",
                "vazou",
                "golpe",
                "transação que eu não fiz",
            ]
        ):
            categoria = CategoriaEnum.FRAUDE_SEGURANCA
            urgencia = UrgenciaEnum.CRITICA
            sentimento = SentimentoEnum.CRITICO
        elif any(
            p in texto_lower
            for p in [
                "cobrança indevida",
                "taxa não informada",
                "juros errado",
                "anuidade",
                "cobraram",
                "reajuste sem aviso",
            ]
        ):
            categoria = CategoriaEnum.COBRANCA_INDEVIDA
            urgencia = UrgenciaEnum.ALTA
            sentimento = SentimentoEnum.NEGATIVO
        elif any(
            p in texto_lower
            for p in ["cancelamento", "cancelar", "cancelei", "não existe mais"]
        ):
            categoria = CategoriaEnum.CANCELAMENTO
            urgencia = UrgenciaEnum.MEDIA
            sentimento = SentimentoEnum.NEGATIVO
        elif any(
            p in texto_lower
            for p in [
                "atendimento",
                "transferido",
                "espera",
                "atendente",
                "sac",
                "ouvidoria",
                "ninguém resolve",
            ]
        ):
            categoria = CategoriaEnum.ATENDIMENTO
            urgencia = UrgenciaEnum.MEDIA
            sentimento = SentimentoEnum.NEGATIVO
        elif any(
            p in texto_lower
            for p in [
                "app não funciona",
                "pix não funciona",
                "erro no aplicativo",
                "sistema fora do ar",
            ]
        ):
            categoria = CategoriaEnum.PRODUTO_SERVICO
            urgencia = UrgenciaEnum.MEDIA
            sentimento = SentimentoEnum.NEGATIVO
        else:
            categoria = CategoriaEnum.OUTROS
            urgencia = UrgenciaEnum.BAIXA
            sentimento = SentimentoEnum.NEUTRO

        # Determinar produto
        if any(p in texto_lower for p in ["cartão", "fatura", "anuidade", "limite"]):
            produto = ProdutoEnum.CARTAO_CREDITO
        elif any(
            p in texto_lower
            for p in [
                "conta corrente",
                "pix",
                "transferência",
                "tarifa",
                "pacote digital",
            ]
        ):
            produto = ProdutoEnum.CONTA_CORRENTE
        elif any(
            p in texto_lower for p in ["empréstimo", "parcela", "juros", "contratei"]
        ):
            produto = ProdutoEnum.EMPRESTIMO
        elif any(
            p in texto_lower
            for p in [
                "investimento",
                "fundo",
                "taxa de performance",
                "rentabilidade",
                "resgate",
            ]
        ):
            produto = ProdutoEnum.INVESTIMENTOS
        elif any(
            p in texto_lower
            for p in [
                "seguro",
                "apólice",
                "cobertura",
                "sinistro",
                "beneficiário",
                "seguro de vida",
                "seguro residencial",
            ]
        ):
            produto = ProdutoEnum.SEGUROS
        else:
            produto = ProdutoEnum.NAO_IDENTIFICADO

        # Gerar resumo simples
        resumo = f"Cliente relata {categoria.value.lower()} relacionado a {produto.value.lower()}. "
        if "desesperado" in texto_lower or "imploro" in texto_lower:
            resumo += "Situação de urgência financeira crítica."
        elif (
            "advogado" in texto_lower
            or "procon" in texto_lower
            or "banco central" in texto_lower
        ):
            resumo += "Cliente ameaça medidas legais/regulatórias."
        else:
            resumo += "Aguardando resolução."

        return ReclamacaoAnalise(
            id="",
            texto_original=texto,
            categoria=categoria,
            produto=produto,
            sentimento=sentimento,
            urgencia=urgencia,
            resumo=sanitizar_resumo(resumo),
        )


# Instância global
llm_service = LLMService()
