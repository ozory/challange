# Especificação Técnica de Desenvolvimento: FinGuard (Nível 1 - Classificador Inteligente)

## 1. Visão Geral e Objetivo do Negócio
O **FinGuard** é uma solução para triagem inteligente de reclamações de clientes de uma instituição financeira. No **Nível 1 (Básico)**, o objetivo é construir uma aplicação web full-stack local e ágil que receba reclamações em texto livre (via chatbot individual ou importação em lote via CSV) e utilize um Provedor de LLM com RAG local para classificar e resumir os atendimentos, alimentando dinamicamente um Dashboard gerencial.

### Escopo e Validações Obrigatórias do Desafio (4h)
1. **Chatbot Interativo:** Receber texto livre e retornar análise estruturada imediata.
2. **Processamento em Lote (CSV):** Suportar o dataset simulated de ~500 reclamações (`id`, `data_reclamacao`, `canal`, `texto_reclamacao`, `produto`, `status`).
3. **Ofuscação de Palavras Impróprias:** Garantir a remoção/ofuscação de termos ofensivos no campo `resumo`.
4. **Exportação de Resultados:** Permitir exportar dados processados em `.json`, `.csv` e um documento `.html` consolidado contendo gráficos.
5. **Execução 100% Local:** Sem persistência de dados em buckets ou serviços em nuvem (ex: AWS S3).

---

## 2. Stack Tecnológica e Requisitos Técnicos

### Backend
* **Linguagem:** Python 3.11+
* **Framework Web:** `FastAPI` (desempenho alto, tipagem com Pydantic e documentação automática Swagger)
* **Integração LLM:** `boto3` (AWS Bedrock — modelos recomendados: *Amazon Nova Micro* ou *Claude 3.5 Haiku* por latência e custo) ou **SDK Iara**
* **Manipulação de Dados:** `pandas` (para parsing de CSV/JSON)
* **Persistência Local:** SQLite (via SQLAlchemy ou Peewee) ou arquivo JSON local *thread-safe*

### Frontend
* **Framework:** ReactJS (Vite)
* **Estilização:** Tailwind CSS (para prototipagem rápida e responsiva)
* **Visualização de Dados:** `recharts` ou `chart.js` (para o Dashboard)
* **Ícones:** `lucide-react`

---

## 3. Esquemas de Dados e Contratos de API

### 3.1. Schemas de Saída Estruturada (Pydantic Models)

```python
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

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
```

---

## 4. Arquitetura do Backend (`/backend`)

### Estrutura de Pastas
```text
backend/
├── main.py              # Entrada FastAPI, CORS e rotas HTTP
├── schemas.py           # Definições Pydantic e Enums
├── llm_service.py       # Integração Bedrock/Iara + Injeção de Contexto (RAG local)
├── sanitizer.py         # Filtro para ofuscação de palavras impróprias
├── repository.py        # Camada de banco de dados local (SQLite / JSON)
├── exporter.py          # Gerador de relatórios (JSON, CSV, HTML com Chart.js)
├── requirements.txt     # Dependências (fastapi, uvicorn, boto3, pandas, pydantic)
└── politica_interna.txt # Documento de contexto para RAG local
```

### Detalhamento dos Componentes

1. **`llm_service.py` (Orquestração e Prompt):**
   * Lê a `politica_interna.txt` localmente e injeta no prompt do sistema.
   * Força resposta estritamente em formato JSON compatível com o schema `ReclamacaoAnalise`.
   * Inclui tratamento de exceção com 1 tentativa de retry caso o parsing de JSON falhe.

2. **`sanitizer.py` (Ofuscação de Termos Ofensivos):**
   * Função utilitária com regex/lista de termos conhecidos para sanitizar a string do `resumo` retornada pela LLM (ex: substituindo por `[REMOVIDO]` ou `****`).

3. **Endpoints da API:**
   * `POST /api/classify` — Recebe `{"texto": "..."}`, classifica individualmente via chat, salva e retorna o resultado.
   * `POST /api/upload-csv` — Recebe upload do arquivo `.csv`, lê com Pandas, dispara a classificação concorrente (com limite de concorrência usando `asyncio.Semaphore(5)`) e salva os registros.
   * `GET /api/tickets` — Retorna a lista de todas as reclamações processadas.
   * `GET /api/metrics` — Retorna os contadores e agrupa dados por Categoria, Produto, Sentimento e Urgência para o Dashboard.
   * `GET /api/export?format={json|csv|html}` — Gera e retorna o arquivo solicitado para download.

---

## 5. Arquitetura do Frontend (`/frontend`)

### Estrutura de Componentes
O frontend deve ser construído em **tela única dividida (Split View)** para agilidade de desenvolvimento e excelente apresentação ao vivo:

```text
frontend/src/
├── services/api.js          # Métodos Axios/Fetch para comunicação com o Backend
├── components/
│   ├── Header.jsx           # Título da aplicação e ações de Exportação/Upload
│   ├── ChatPanel.jsx        # Interface do Chatbot para input manual de texto e exibições
│   ├── DashboardPanel.jsx   # Indicadores (KPIs) + Gráficos (Categorias, Produtos, Urgências)
│   └── TicketTable.jsx      # Tabela com filtro e busca de reclamações processadas
└── App.jsx                  # Estado global e sincronização dinâmica
```

### Regras de Interface e UX
* **Sincronização em Tempo Real:** Sempre que uma reclamação é enviada via Chat ou lote CSV, os componentes `DashboardPanel` e `TicketTable` atualizam seus estados automaticamente.
* **Destaques Visuais:** Reclamações com `urgencia: "Crítica"` ou `categoria: "Fraude/Segurança"` devem exibir badges em vermelho para destaque visual imediato.
* **Loading States:** Exibir spinners ou barras de progresso ao processar o arquivo CSV ou aguardar a resposta da LLM.

---

## 6. Prompt do Sistema (`System Prompt`)

```text
Você é o FinGuard, um assistente especializado em análise e triagem de reclamações de instituições financeiras.
Sua tarefa é analisar o texto da reclamação fornecido e retornar EXCLUSIVAMENTE um objeto JSON estruturado.

Diretrizes da Política Interna:
<politica_interna>
{CONTEUDO_DO_ARQUIVO_POLITICA_INTERNA}
</politica_interna>

Regras de Classificação:
1. Categoria: Escolha exatamente uma entre: ["Cobrança Indevida", "Atendimento", "Fraude/Segurança", "Produto/Serviço", "Cancelamento", "Outros"].
2. Produto: Escolha exatamente um entre: ["Cartão de Crédito", "Conta Corrente", "Empréstimo", "Investimentos", "Seguros", "Não Identificado"].
3. Sentimento: Escolha entre: ["Positivo", "Neutro", "Negativo", "Crítico"].
4. Urgencia: Escolha entre: ["Baixa", "Média", "Alta", "Crítica"].
5. Resumo: Escreva um resumo conciso (2 a 3 linhas) em linguagem formal e padronizada. NUNCA inclua palavras impróprias ou ofensivas.

Saída esperada: Responda APENAS com o JSON no formato:
{
  "categoria": "...",
  "produto": "...",
  "sentimento": "...",
  "urgencia": "...",
  "resumo": "..."
}
```

---

## 7. Instruções de Desenvolvimento para Agentes de Código

Se for utilizar assistentes baseados em IA para codificar este projeto:
1. **Passo 1 (Backend Core):** Crie a estrutura de diretórios e implemente `schemas.py`, `sanitizer.py` e `llm_service.py` primeiro. Teste a chamada da LLM via script simples.
2. **Passo 2 (FastAPI Endpoints):** Crie `main.py` com suporte a CORS (`allow_origins=["*"]`) e implemente as rotas `/api/classify` e `/api/metrics`.
3. **Passo 3 (Processamento em Lote & Exportação):** Implemente a rota `/api/upload-csv` e a geração do relatório visual HTML estático.
4. **Passo 4 (Frontend UI):** Monte a interface em ReactJS criando a visualização lado a lado (Chat à esquerda, Dashboard/Tabela à direita).