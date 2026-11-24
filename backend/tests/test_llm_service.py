import asyncio
import json
import os
import unittest
from urllib.parse import parse_qs
from unittest.mock import patch

import httpx

from llm_service import LLMService


class StackSpotTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        ambiente = patch.dict(os.environ, {
            "STACKSPOT_REALM": "teste",
            "STACKSPOT_CLIENT_ID": "id-teste",
            "STACKSPOT_CLIENT_SECRET": "segredo-teste",
            "STACKSPOT_AGENT_URL": "https://example.test/agent/chat",
        })
        ambiente.start()
        self.addCleanup(ambiente.stop)
        self.servico = LLMService()
        self.classificacao = {
            "categoria": "Atendimento", "produto": "Conta Corrente", "sentimento": "Negativo",
            "urgencia": "Alta", "resumo": "Cliente relata demora.\nSolicita providências.",
        }
        self.chamadas = []
        self.responder = self.responder_padrao
        cliente_original = httpx.AsyncClient
        cliente = patch("llm_service.httpx.AsyncClient", side_effect=lambda **kwargs: cliente_original(
            transport=httpx.MockTransport(self.requisitar), **kwargs,
        ))
        cliente.start()
        self.addCleanup(cliente.stop)

    def requisitar(self, requisicao):
        self.chamadas.append(requisicao)
        return self.responder(requisicao)

    def responder_padrao(self, requisicao):
        if "oidc/oauth/token" in str(requisicao.url):
            return httpx.Response(200, json={"access_token": "token-teste", "expires_in": 3600})
        return httpx.Response(200, json={"message": json.dumps(self.classificacao, ensure_ascii=False)})

    async def test_payload_oauth_e_reutilizacao_do_token(self):
        primeiro = await self.servico.classificar_reclamacao("Demora no atendimento", max_retries=0)
        segundo = await self.servico.classificar_reclamacao("Outro atendimento", max_retries=0)
        self.assertEqual(primeiro.categoria.value, "Atendimento")
        self.assertEqual(segundo.produto.value, "Conta Corrente")
        self.assertEqual(len(self.chamadas), 3)
        autenticacao = self.chamadas[0]
        self.assertEqual(str(autenticacao.url), "https://idm.stackspot.com/teste/oidc/oauth/token")
        self.assertEqual(parse_qs(autenticacao.content.decode())["grant_type"], ["client_credentials"])
        self.assertEqual(self.chamadas[1].headers["Authorization"], "Bearer token-teste")
        payload = json.loads(self.chamadas[1].content)
        self.assertEqual(set(payload), {"streaming", "user_prompt", "stackspot_knowledge", "return_ks_in_response", "deep_search_ks"})
        self.assertFalse(payload["streaming"])
        self.assertTrue(payload["stackspot_knowledge"])
        self.assertFalse(payload["return_ks_in_response"])
        self.assertFalse(payload["deep_search_ks"])
        self.assertIn("Demora no atendimento", payload["user_prompt"])
        self.assertIn(self.servico.politica_interna, payload["user_prompt"])

    async def test_renovacao_por_401_e_expiracao(self):
        autenticacoes = 0

        def responder(requisicao):
            nonlocal autenticacoes
            if "oidc/oauth/token" in str(requisicao.url):
                autenticacoes += 1
                return httpx.Response(200, json={"access_token": f"token-{autenticacoes}", "expires_in": 3600})
            if requisicao.headers["Authorization"] == "Bearer token-1":
                return httpx.Response(401)
            return httpx.Response(200, json={"response": {"message": "```json\n" + json.dumps(self.classificacao) + "\n```"}})

        self.responder = responder
        self.assertIsNotNone(await self.servico.classificar_reclamacao("Atendimento", max_retries=0))
        self.assertEqual(autenticacoes, 2)
        self.assertEqual(self.chamadas[-1].headers["Authorization"], "Bearer token-2")
        self.servico._expires_at = 0
        self.assertIsNotNone(await self.servico.classificar_reclamacao("Atendimento", max_retries=0))
        self.assertEqual(autenticacoes, 3)

    async def test_classificacoes_concorrentes_compartilham_token(self):
        resultados = await asyncio.gather(*(self.servico.classificar_reclamacao(f"Atendimento {indice}", max_retries=0) for indice in range(5)))
        self.assertTrue(all(resultados))
        self.assertEqual(sum("oidc/oauth/token" in str(chamada.url) for chamada in self.chamadas), 1)

    async def test_falhas_nao_geram_classificacao_simulada(self):
        self.responder = lambda requisicao: httpx.Response(500, text="erro privado")
        with self.assertLogs("finguard", level="WARNING") as logs:
            resultado = await self.servico.classificar_reclamacao("Atendimento", max_retries=0)
        self.assertIsNone(resultado)
        self.assertNotIn("erro privado", " ".join(logs.output))
        self.servico.client_secret = ""
        self.assertIsNone(await self.servico.classificar_reclamacao("Atendimento", max_retries=0))

    async def test_segundo_401_nao_gera_resultado_ficticio(self):
        def responder(requisicao):
            if "oidc/oauth/token" in str(requisicao.url):
                return httpx.Response(200, json={"access_token": "token", "expires_in": 3600})
            return httpx.Response(401)
        self.responder = responder
        self.assertIsNone(await self.servico.classificar_reclamacao("Atendimento", max_retries=0))
        self.assertEqual(len(self.chamadas), 4)

    async def test_configuracao_invalida_nao_faz_requisicao(self):
        self.servico.agent_url = "http://example.test/agent"
        self.assertIsNone(await self.servico.classificar_reclamacao("Atendimento", max_retries=0))
        self.assertEqual(self.chamadas, [])

    async def test_resposta_invalida_e_sanitizacao(self):
        self.classificacao["resumo"] = "Cliente descreve merda.\nSolicita atendimento."
        resultado = await self.servico.classificar_reclamacao("Atendimento", max_retries=0)
        self.assertNotIn("merda", resultado.resumo)
        self.classificacao["categoria"] = "Desconhecida"
        self.assertIsNone(await self.servico.classificar_reclamacao("Atendimento", max_retries=0))

    def test_variantes_de_envelope(self):
        for chave in ("message", "response", "result"):
            with self.subTest(chave=chave):
                texto = "```json\n" + json.dumps(self.classificacao) + "\n```"
                self.assertEqual(self.servico._extrair_classificacao({chave: texto}), self.classificacao)
        with self.assertRaises(ValueError):
            self.servico._extrair_classificacao({"message": "sem JSON"})


class ConfiguracaoStackSpotTests(unittest.TestCase):
    def construir(self, **ambiente):
        base = {chave: "" for chave in (
            "STACKSPOT_REALM", "STACKSPOT_CLIENT_ID", "STACKSPOT_CLIENT_SECRET",
            "STACKSPOT_AGENT_ID", "STACKSPOT_AGENT_URL",
        )}
        base.update(ambiente)
        with patch.dict(os.environ, base):
            return LLMService()

    def test_agent_id_monta_a_url_padrao_de_inferencia(self):
        servico = self.construir(
            STACKSPOT_REALM="realm", STACKSPOT_CLIENT_ID="id",
            STACKSPOT_CLIENT_SECRET="segredo", STACKSPOT_AGENT_ID="01ABCDEF",
        )
        self.assertEqual(
            servico.agent_url,
            "https://genai-inference-app.stackspot.com/v1/agent/01ABCDEF/chat",
        )
        self.assertEqual(servico.token_url, "https://idm.stackspot.com/realm/oidc/oauth/token")
        self.assertTrue(servico.configurado)

    def test_agent_url_tem_precedencia_e_fornece_o_agent_id(self):
        servico = self.construir(
            STACKSPOT_REALM="realm", STACKSPOT_CLIENT_ID="id", STACKSPOT_CLIENT_SECRET="segredo",
            STACKSPOT_AGENT_ID="ignorado-nao", STACKSPOT_AGENT_URL="https://example.test/v1/agent/XYZ/chat",
        )
        self.assertEqual(servico.agent_url, "https://example.test/v1/agent/XYZ/chat")
        self.assertEqual(servico.agent_id, "ignorado-nao")
        semIdExplicito = self.construir(
            STACKSPOT_REALM="realm", STACKSPOT_CLIENT_ID="id", STACKSPOT_CLIENT_SECRET="segredo",
            STACKSPOT_AGENT_URL="https://example.test/v1/agent/XYZ/chat",
        )
        self.assertEqual(semIdExplicito.agent_id, "XYZ")

    def test_problemas_listam_variaveis_sem_expor_segredos(self):
        servico = self.construir(STACKSPOT_AGENT_ID="01ABC")
        problemas = servico.problemas_de_configuracao()
        self.assertFalse(servico.configurado)
        self.assertIn("STACKSPOT_REALM ausente", problemas)
        self.assertIn("STACKSPOT_CLIENT_ID ausente", problemas)
        self.assertIn("STACKSPOT_CLIENT_SECRET ausente", problemas)
        self.assertNotIn("STACKSPOT_AGENT_URL (ou STACKSPOT_AGENT_ID) ausente", problemas)

    def test_agent_id_malicioso_nao_vira_url(self):
        servico = self.construir(
            STACKSPOT_REALM="realm", STACKSPOT_CLIENT_ID="id", STACKSPOT_CLIENT_SECRET="segredo",
            STACKSPOT_AGENT_ID="../../evil.test/x",
        )
        self.assertEqual(servico.agent_url, "")
        self.assertIn("STACKSPOT_AGENT_URL (ou STACKSPOT_AGENT_ID) ausente", servico.problemas_de_configuracao())

    def test_resumo_nao_contem_segredos(self):
        servico = self.construir(
            STACKSPOT_REALM="realm", STACKSPOT_CLIENT_ID="id-publico",
            STACKSPOT_CLIENT_SECRET="segredo-super", STACKSPOT_AGENT_ID="01ABC",
        )
        resumo = json.dumps(servico.resumo_configuracao())
        self.assertNotIn("segredo-super", resumo)
        self.assertNotIn("id-publico", resumo)
        self.assertTrue(servico.resumo_configuracao()["client_secret_definido"])
        self.assertEqual(servico.resumo_configuracao()["provedor"], "StackSpot AI")

if __name__ == "__main__":
    unittest.main()