import io
import json
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

import httpx


repositorio = Mock()
modulo_repositorio = types.ModuleType("repository")
modulo_repositorio.repository = repositorio
repositorio_anterior = sys.modules.get("repository")
sys.modules["repository"] = modulo_repositorio
try:
    with patch("dotenv.load_dotenv"), patch("dotenv.dotenv_values", return_value={}):
        import main
finally:
    if repositorio_anterior is None:
        sys.modules.pop("repository", None)
    else:
        sys.modules["repository"] = repositorio_anterior

from schemas import ReclamacaoAnalise
from llm_service import LLMService


class StackSpotApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        repositorio.reset_mock()
        patcher = patch.object(main, "repository", repositorio)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.analise = ReclamacaoAnalise(
            id="", texto_original="", categoria="Atendimento", produto="Conta Corrente",
            sentimento="Negativo", urgencia="Alta", resumo="Cliente relata demora.\nSolicita providências.",
        )

    async def test_classificacao_persiste_resultado_stackspot(self):
        with patch.object(main.llm_service, "classificar_reclamacao", new_callable=AsyncMock, return_value=self.analise):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://testserver") as cliente:
                resposta = await cliente.post("/api/classify", json={"texto": "Demora no atendimento"})
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()["success"], resposta.json())
        self.assertEqual(resposta.json()["data"]["categoria"], "Atendimento")
        repositorio.salvar.assert_called_once()

    async def test_rota_usa_agente_stackspot_com_http_simulado(self):
        ambiente = {
            "STACKSPOT_REALM": "teste", "STACKSPOT_CLIENT_ID": "id",
            "STACKSPOT_CLIENT_SECRET": "segredo", "STACKSPOT_AGENT_URL": "https://example.test/agent/chat",
        }
        chamadas = []

        def responder(requisicao):
            chamadas.append(requisicao)
            if "oidc/oauth/token" in str(requisicao.url):
                return httpx.Response(200, json={"access_token": "token", "expires_in": 3600})
            return httpx.Response(200, json={"result": json.dumps({
                "categoria": "Atendimento", "produto": "Conta Corrente", "sentimento": "Negativo",
                "urgencia": "Alta", "resumo": "Cliente relata demora.\nSolicita providências.",
            })})

        cliente_original = httpx.AsyncClient
        cliente_api = cliente_original(transport=httpx.ASGITransport(app=main.app), base_url="http://testserver")
        with patch.dict(os.environ, ambiente), patch.object(main, "llm_service", LLMService()), \
             patch("llm_service.httpx.AsyncClient", side_effect=lambda **kwargs: cliente_original(
                 transport=httpx.MockTransport(responder), **kwargs,
             )):
            async with cliente_api:
                resposta = await cliente_api.post("/api/classify", json={"texto": "Demora no atendimento"})
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()["success"])
        self.assertEqual(resposta.json()["data"]["categoria"], "Atendimento")
        self.assertEqual(len(chamadas), 2)
        self.assertEqual(chamadas[1].headers["Authorization"], "Bearer token")
        repositorio.salvar.assert_called_once()

    async def test_falha_stackspot_nao_persiste_classificacao(self):
        with patch.object(main.llm_service, "classificar_reclamacao", new_callable=AsyncMock, return_value=None):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://testserver") as cliente:
                resposta = await cliente.post("/api/classify", json={"texto": "Demora no atendimento"})
        self.assertEqual(resposta.status_code, 500)
        repositorio.salvar.assert_not_called()

    async def test_lote_contabiliza_falhas_sem_resultados_ficticios(self):
        conteudo = b'id,data_reclamacao,canal,texto_reclamacao,produto,status\n1,2026,SAC,Demora,Conta,Aberta\n2,2026,SAC,Cobranca,Conta,Aberta\n'
        with patch.object(main.llm_service, "classificar_reclamacao", new_callable=AsyncMock, side_effect=[self.analise, None]):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://testserver") as cliente:
                resposta = await cliente.post("/api/upload-csv", files={"file": ("dados.csv", io.BytesIO(conteudo), "text/csv")})
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(resposta.json()["processados"], 1)
        self.assertEqual(resposta.json()["erros"], 1)
        repositorio.salvar.assert_called_once()


class DiagnosticoEFrontendTests(unittest.IsolatedAsyncioTestCase):
    async def obter(self, caminho):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://testserver") as cliente:
            return await cliente.get(caminho)

    async def test_health_reporta_stackspot_sem_segredos(self):
        ambiente = {
            "STACKSPOT_REALM": "teste", "STACKSPOT_CLIENT_ID": "id",
            "STACKSPOT_CLIENT_SECRET": "segredo-super", "STACKSPOT_AGENT_ID": "01ABC",
            "STACKSPOT_AGENT_URL": "",
        }
        with patch.dict(os.environ, ambiente), patch.object(main, "llm_service", LLMService()):
            resposta = await self.obter("/health")
        corpo = resposta.json()
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(corpo["status"], "ok")
        self.assertEqual(corpo["llm"]["provedor"], "StackSpot AI")
        self.assertEqual(corpo["llm"]["agent_id"], "01ABC")
        self.assertIn("genai-inference-app.stackspot.com", corpo["llm"]["endpoint"])
        self.assertIn("idm.stackspot.com", corpo["llm"]["token_url"])
        self.assertNotIn("segredo-super", resposta.text)

    async def test_health_degradado_quando_falta_configuracao(self):
        vazio = {chave: "" for chave in (
            "STACKSPOT_REALM", "STACKSPOT_CLIENT_ID", "STACKSPOT_CLIENT_SECRET",
            "STACKSPOT_AGENT_ID", "STACKSPOT_AGENT_URL",
        )}
        with patch.dict(os.environ, vazio), patch.object(main, "llm_service", LLMService()):
            resposta = await self.obter("/health")
        self.assertEqual(resposta.json()["status"], "degraded")
        self.assertFalse(resposta.json()["llm"]["configurado"])

    async def test_frontend_continua_servido_em_app(self):
        rotas = [rota.path for rota in main.app.routes]
        self.assertIn("/app", rotas)
        resposta = await self.obter("/app/")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("text/html", resposta.headers["content-type"])

if __name__ == "__main__":
    unittest.main()