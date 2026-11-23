import re
from typing import List

# Lista de palavras impróprias/termos ofensivos para ofuscação
PALAVRAS_IMPROPRIAS = [
    r'\bmerda\b', r'\bporra\b', r'\bcaralho\b', r'\bputa\b', r'\bfoda\b',
    r'\bputo\b', r'\bporcaria\b', r'\bpalhaçada\b', r'\bmerda\b',
    r'\bcaramba\b', r'\bdesgraça\b', r'\binferno\b', r'\bdiabo\b',
    r'\bputa\b', r'\bputaria\b', r'\bviado\b', r'\bveado\b',
    r'\bcorno\b', r'\bchifre\b', r'\bimbecil\b', r'\bidota\b',
    r'\bcretino\b', r'\babestado\b', r'\blixo\b', r'\besgoto\b',
    r'\bnojo\b', r'\bnojento\b', r'\bpodre\b', r'\blixo\b',
    r'\bcu\b', r'\bbuceta\b', r'\bpau\b', r'\brola\b',
    r'\bpiroca\b', r'\bcacete\b', r'\bcaralho\b', r'\bporra\b',
    r'\bputa\b', r'\bputa\b', r'\bputa\b'
]

# Compilar regex para performance
PADROES_COMPILADOS = [re.compile(padrao, re.IGNORECASE) for padrao in PALAVRAS_IMPROPRIAS]


def ofuscar_palavras_improprias(texto: str, substituicao: str = "[REMOVIDO]") -> str:
    """
    Ofusca palavras impróprias no texto substituindo por [REMOVIDO] ou ***.
    
    Args:
        texto: Texto a ser sanitizado
        substituicao: String para substituir palavras impróprias
        
    Returns:
        Texto com palavras impróprias ofuscadas
    """
    if not texto:
        return texto
    
    resultado = texto
    for padrao in PADROES_COMPILADOS:
        resultado = padrao.sub(substituicao, resultado)
    
    return resultado


def sanitizar_resumo(resumo: str) -> str:
    """
    Sanitiza especificamente o campo resumo, garantindo que não contenha
    palavras impróprias.
    
    Args:
        resumo: Resumo gerado pela LLM
        
    Returns:
        Resumo sanitizado
    """
    return ofuscar_palavras_improprias(resumo, "[REMOVIDO]")


def adicionar_palavra_impropria(palavra: str) -> None:
    """
    Adiciona uma nova palavra à lista de palavras impróprias.
    
    Args:
        palavra: Palavra a ser adicionada (será escapada para regex)
    """
    padrao = r'\b' + re.escape(palavra) + r'\b'
    PALAVRAS_IMPROPRIAS.append(padrao)
    PADROES_COMPILADOS.append(re.compile(padrao, re.IGNORECASE))