from security.llm_input_guard import guard_input
from security.llm_output_validator import validate_summary
from security.pii_masker import mask_pii_text as mask


def test_cpf_formatado_e_valido():
    assert mask("CPF 529.143.780-66") == "CPF [CPF]"
    assert mask("CPF 52998224725") == "CPF [CPF]"  # só dígitos, dígito verificador válido


def test_outros_dados():
    assert mask("a.b@x.com.br") == "[EMAIL]"
    assert mask("cartão 4111 1111 1111 1111") == "cartão [CARTAO]"
    assert mask("11.222.333/0001-81") == "[CNPJ]"
    assert mask("(31) 99876-5432") == "[TELEFONE]"


def test_nao_mascara_valores_monetarios_nem_protocolos():
    t = "R$ 45.000,00 e R$ 212,00, protocolo 20261124001"
    assert mask(t) == t


def test_idempotente():
    t = mask("CPF 529.143.780-66")
    assert mask(t) == t


def test_camadas_3_e_4():
    assert "529.143.780-66" not in guard_input("meu CPF 529.143.780-66, compra indevida")
    assert "529.143.780-66" not in validate_summary("Cliente 529.143.780-66 relata fraude")
