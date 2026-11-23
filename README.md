# FinGuard - Triagem Inteligente de Reclamações Financeiras

> **Nível 1 - Classificador Inteligente** | Solução full-stack local para triagem e análise automatizada de reclamações de clientes de instituições financeiras.

---

## 📋 Visão Geral

O **FinGuard** é uma aplicação web full-stack que recebe reclamações em texto livre (via chatbot individual ou importação em lote via CSV) e utiliza um Provedor de LLM com RAG local para classificar, resumir e priorizar os atendimentos, alimentando dinamicamente um Dashboard gerencial.

O frontend é escrito em **HTML, CSS e JavaScript puro** (sem React, sem npm, sem etapa de build) e é servido pelo próprio backend FastAPI. Para rodar a solução completa basta **Python**.

### ✨ Funcionalidades Principais

| Funcionalidade | Descrição |
|----------------|-----------|
| 🤖 **Chatbot Interativo** | Recebe texto livre e retorna análise estruturada imediata |
| 📊 **Processamento em Lote (CSV)** | Suporta dataset de ~500 reclamações com concorrência controlada |
| 🛡️ **Ofuscação de Palavras Impróprias** | Remove/sanitiza termos ofensivos no campo `resumo` |
| 📤 **Exportação Múltipla** | JSON, CSV e HTML consolidado com gráficos Chart.js |
| 🏠 **100% Local** | Sem dependência de nuvem - SQLite local, processamento local |

---

## 🛠️ Stack Tecnológica

### Backend
| Tecnologia | Versão | Uso |
|------------|--------|-----|
| **Python** | 3.12+ | Linguagem principal |
| **FastAPI** | 0.109.0 | Framework web assíncrono (também serve o frontend) |
| **Uvicorn** | 0.27.0 | Servidor ASGI |
| **Pydantic** | 2.5.3 | Validação e serialização |
| **Pandas** | 2.1.4 | Manipulação de CSV/JSON |
| **SQLite** | Built-in | Persistência local |
| **httpx** | 0.26.0 | Cliente HTTP assíncrono para LLM |
| **truststore** | >=0.9.0 | Usa os certificados do sistema operacional no HTTPS (redes com proxy corporativo) |
| **python-dotenv** | 1.0.0 | Variáveis de ambiente |
| **OpenRouter API** | - | Integração LLM (modelo gratuito) |

### Frontend (`frontend/`)
| Tecnologia | Uso |
|------------|-----|
| **HTML5** | Estrutura da página única |
| **CSS3** | Estilização com variáveis CSS (tema claro/escuro), Flexbox e Grid |
| **JavaScript (ES5+/DOM)** | Lógica, componentes e renderização, sem frameworks |
| **Fetch API** | Comunicação com o backend |
| **SVG nativo** | Gráficos (donut e barras) desenhados à mão, sem bibliotecas |

> Nenhuma dependência de frontend: sem `node_modules`, sem bundler, sem CDN. Funciona offline.

---

## 📁 Estrutura do Projeto

```
challange/
├── README.md                 # Este arquivo
├── spec.md                   # Especificação técnica completa
├── challange.pdf             # Documento original do desafio
├── data.csv                  # Dataset de exemplo (~500 reclamações)
├── backend/
│   ├── main.py               # Entrada FastAPI, rotas HTTP, CORS e hospedagem do frontend
│   ├── schemas.py            # Modelos Pydantic e Enums
│   ├── llm_service.py        # Integração LLM + RAG (política interna)
│   ├── sanitizer.py          # Filtro de palavras impróprias
│   ├── repository.py         # Camada SQLite (thread-safe)
│   ├── exporter.py           # Gerador de relatórios (JSON/CSV/HTML)
│   ├── politica_interna.txt  # Contexto para RAG local
│   ├── pyproject.toml        # Configuração do projeto (uv)
│   ├── requirements.txt      # Dependências pip
│   ├── uv.lock               # Lock file do uv
│   ├── reclamacoes.db        # Banco SQLite (criado automaticamente)
│   └── .env                  # Variáveis de ambiente (não versionado)
└── frontend/                  # Frontend em JavaScript puro
    ├── index.html            # Página única; carrega CSS e scripts
    ├── favicon.svg
    ├── css/
    │   └── styles.css        # Estilos globais, temas claro/escuro, componentes
    └── js/
        ├── utils.js          # Helpers de DOM (sem innerHTML com dados) e ícones SVG
        ├── api.js            # Cliente da API (fetch)
        ├── theme.js          # Tema claro/escuro (localStorage)
        ├── charts.js         # Gráficos SVG: donut, barras horizontais e verticais
        ├── header.js         # Título + ações (Importar/Exportar/Atualizar/Limpar/Tema)
        ├── chat.js           # Interface do chatbot
        ├── dashboard.js      # KPIs + gráficos
        ├── table.js          # Tabela com busca, filtros, ordenação e paginação
        └── app.js            # Montagem do layout, abas e atualização entre painéis
```

---

## 🚀 Como Executar Localmente

### Pré-requisitos
- **Python 3.12+** (recomendado usar `uv` ou `venv`)
- Um navegador moderno
- **Não é necessário** Node.js nem npm

> **Atenção à versão do Python:** as dependências estão fixadas em versões antigas (ex.: `pandas==2.1.4` → `numpy==1.26.4`) que não têm pacotes pré-compilados para Python muito recente (3.14+). Nesse caso o `uv`/`pip` tenta compilar do código-fonte e falha sem um compilador C. Use **Python 3.12**: `uv python install 3.12 && uv python pin 3.12`.

---

### 1. Backend + Frontend (um único processo)

```bash
# Entrar no diretório do backend
cd backend

# Opção A: Usando uv (recomendado - mais rápido)
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Opção B: Usando venv + pip tradicional
python -m venv .venv
source .venv/bin/activate     # Linux/Mac
# .venv\Scripts\Activate.ps1  # Windows (PowerShell)
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Acesse a aplicação em: **http://localhost:8000/app/**

> **Nota:** O backend roda em `http://localhost:8000`
> - **Aplicação (frontend):** `http://localhost:8000/app/`
> - Documentação Swagger: `http://localhost:8000/docs`
> - Documentação ReDoc: `http://localhost:8000/redoc`

#### Variáveis de Ambiente (Backend)
Crie um arquivo `.env` na pasta `backend/`:
```env
# OpenRouter API Key (obrigatório para LLM real)
# Obtenha em: https://openrouter.ai/keys
OPEN_ROUTER_KEY=sua_chave_aqui

# Opcional: caminho de um bundle de CA (.pem) a ser usado na validação HTTPS.
# Útil em redes corporativas com inspeção SSL. Se omitido, usa o repositório
# de certificados do sistema operacional (truststore).
# LLM_CA_BUNDLE=C:\caminho\ca-corporativa.pem
```

> O modelo está definido em `backend/llm_service.py` (`nvidia/nemotron-3-ultra-550b-a55b:free`). Para trocar, altere `self.model` nesse arquivo.

> **Sem API Key:** O sistema usa classificação **mock** baseada em palavras-chave (funciona offline para desenvolvimento/testes).

---

### 2. Formas alternativas de abrir o frontend

O frontend é estático, então há mais de uma forma de abri-lo (o backend precisa estar rodando em todas):

| Forma | Como | Observação |
|-------|------|------------|
| **Servido pelo FastAPI** (padrão) | `http://localhost:8000/app/` | Mesma origem, sem CORS |
| **Arquivo local** | Abrir `frontend/index.html` no navegador | Usa `http://localhost:8000/api` |
| **Servidor estático Python** | `cd frontend && python -m http.server 5500` → `http://localhost:5500` | Usa `http://localhost:8000/api` (CORS já liberado) |

O endereço da API é decidido em [frontend/js/api.js](frontend/js/api.js): se a página for servida pela porta 8000 usa o caminho relativo `/api`; caso contrário aponta para `http://localhost:8000/api`.

---

## 📡 API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/` | Health check básico |
| `GET` | `/health` | Status da API |
| `GET` | `/app/` | Interface web (frontend estático) |
| `POST` | `/api/classify` | Classifica uma reclamação individual |
| `POST` | `/api/upload-csv` | Processa CSV em lote (concorrência = 5) |
| `GET` | `/api/tickets` | Lista todas as reclamações processadas |
| `GET` | `/api/metrics` | Métricas agregadas para Dashboard |
| `GET` | `/api/export?format=json\|csv\|html` | Exporta dados no formato solicitado |
| `DELETE` | `/api/tickets` | Remove todas as reclamações (testes) |

### Exemplos de Uso

#### Classificar Reclamação Individual
```bash
curl -X POST http://localhost:8000/api/classify \
  -H "Content-Type: application/json" \
  -d '{"texto": "Fui cobrado indevidamente na anuidade do cartão de crédito"}'
```

#### Upload CSV
```bash
curl -X POST http://localhost:8000/api/upload-csv \
  -F "file=@data.csv"
```

#### Exportar HTML
```bash
curl http://localhost:8000/api/export?format=html -o relatorio.html
```

---

## 🎯 Classificações Suportadas

### Categorias
- `Cobrança Indevida`
- `Atendimento`
- `Fraude/Segurança` ⚠️ (Destaque visual vermelho)
- `Produto/Serviço`
- `Cancelamento`
- `Outros`

### Produtos
- `Cartão de Crédito`
- `Conta Corrente`
- `Empréstimo`
- `Investimentos`
- `Seguros`
- `Não Identificado`

### Sentimentos
- `Positivo` 🟢
- `Neutro` ⚪
- `Negativo` 🟠
- `Crítico` 🔴

### Urgências
- `Baixa` 🟢
- `Média` 🟡
- `Alta` 🟠
- `Crítica` 🔴 (Destaque visual vermelho)

---

## 🔧 Detalhes de Implementação

### Backend - Arquitetura em Camadas

```
main.py (Rotas HTTP + arquivos estáticos do frontend)
    │
    ├── llm_service.py (Orquestração LLM + RAG)
    │       │
    │       ├── politica_interna.txt (Contexto injetado no prompt)
    │       └── sanitizer.py (Ofuscação de termos ofensivos)
    │
    ├── repository.py (SQLite thread-safe)
    │       └── reclamacoes.db (Persistência local)
    │
    └── exporter.py (JSON/CSV/HTML com Chart.js)
```

### RAG Local (Política Interna)
O `politica_interna.txt` é pequeno (poucos KB) e é lido pelo `llm_service.py` e **injetado integralmente** no prompt do sistema a cada classificação. Por ser um documento curto, optou-se por essa injeção direta de contexto em vez de uma etapa de indexação/recuperação (chunking, embeddings), mantendo a solução simples e 100% local. Caso a política cresça a ponto de não caber no contexto do modelo, o ponto de evolução é recuperar apenas as seções relevantes (por exemplo, com BM25 ou embeddings) antes de montar o prompt.

### Concorrência no Processamento em Lote
- Usa `asyncio.Semaphore(5)` para limitar requisições simultâneas à LLM
- Processa linhas do CSV em paralelo com `asyncio.gather()`
- Retry automático (1x) em caso de falha de parsing JSON

### Sanitização de Texto
- Regex compilada para performance
- Lista extensível de termos ofensivos (`sanitizer.py`)
- Substituição padrão: `[REMOVIDO]`

### Frontend - Split View (Tela Única)
```
┌─────────────────────────────────────────────────────────┐
│ Header (Título + Export/Upload/Limpar + Theme Toggle)   │
├──────────────────┬──────────────────────────────────────┤
│                  │                                      │
│   Chat           │     Dashboard / Tabela               │
│   (Esquerda)     │     (Direita - Abas)                 │
│                  │                                      │
│  - Input texto   │  - KPIs (Total, Críticas, etc.)      │
│  - Histórico     │  - Gráficos SVG                      │
│  - Loading       │  - Tabela com filtros/busca          │
│                  │                                      │
└──────────────────┴──────────────────────────────────────┘
```

### Organização do Frontend em JavaScript Puro
- **Scripts clássicos** (sem ES modules) carregados em ordem pelo `index.html`, o que permite abrir o arquivo direto do disco (`file://`). Todos compartilham o namespace global `window.FG`.
- **Componentes como funções**: `createHeader()`, `createChat()`, `createDashboard()` e `createTable()` constroem e retornam elementos DOM, mantendo o estado em variáveis locais (closures).
- **Segurança**: os elementos são criados via `document.createElement` e `textContent` (helper `FG.el`). Conteúdo vindo de reclamações ou da LLM nunca é inserido com `innerHTML`, evitando XSS.
- **Gráficos**: [frontend/js/charts.js](frontend/js/charts.js) gera SVG (donut, barras horizontais e verticais) com tooltip; são redesenhados ao redimensionar a janela.
- **Tema**: classe `dark` no `<html>` + variáveis CSS; a preferência fica em `localStorage` e é aplicada antes da primeira renderização (sem "flash").

### Sincronização entre Painéis
- A função `refresh()` em `app.js` recarrega a aba ativa (Dashboard ou Tabela)
- É chamada após: nova análise no chat, upload de CSV, limpeza e clique em "Atualizar"
- Ao trocar de aba, os dados da aba são recarregados

---

## 📊 Dataset de Exemplo

O projeto inclui **`data.csv`**: ~500 reclamações simuladas com colunas `id`, `data_reclamacao`, `canal`, `texto_reclamacao`, `produto`, `status`.

Use o botão **"Importar CSV"** no Header para processar o dataset de exemplo.

---

## 🧪 Testes

Atualmente o projeto **não possui testes automatizados**. As dependências de teste (`pytest`, `pytest-asyncio`) estão declaradas em `pyproject.toml`, e a configuração aponta para a pasta `backend/tests/` (ainda não criada).

Verificação manual sugerida:
1. Subir o backend e abrir `http://localhost:8000/app/`
2. Enviar uma reclamação no chat e conferir badges e resumo
3. Importar o `data.csv` e conferir Dashboard e Tabela
4. Exportar JSON, CSV e HTML

---

## 🐛 Troubleshooting

### Backend não inicia / falha ao instalar dependências
```bash
# Verificar Python version
python --version  # Deve ser 3.12.x

# Reinstalar dependências
uv sync --frozen
# ou
pip install -r requirements.txt --force-reinstall
```

Erro `Failed to build numpy` / `Unknown compiler(s)`: o Python é novo demais para as versões fixadas. Use Python 3.12 (`uv python install 3.12 && uv python pin 3.12`, depois recrie o `.venv`).

### Ativar o ambiente virtual no Windows
No PowerShell use `.venv\Scripts\Activate.ps1` (não é um comando do `uv`). Ou ignore a ativação e use `uv run ...`.

### Frontend não conecta no Backend
1. Verifique se o backend roda na porta 8000: `curl http://localhost:8000/health`
2. Prefira abrir pela URL `http://localhost:8000/app/`
3. Se abriu por outro servidor/arquivo, confira `API_BASE_URL` em `frontend/js/api.js`
4. CORS já está liberado no `main.py` (`allow_origins=["*"]`)
5. Abra o console do navegador (F12) para ver erros de rede ou de script

### Erro de LLM (401/402/429)
- Verifique `OPEN_ROUTER_KEY` no `.env`
- Sem key válida → usa **mock automático** (logs mostram `[LLM] Usando classificação mock`)
- Rate limit → fallback automático para mock

### Erro `CERTIFICATE_VERIFY_FAILED` ao chamar a LLM
Comum em redes corporativas com inspeção SSL (a CA da empresa não está no `certifi`). O backend já usa o repositório de certificados do sistema via `truststore`; confirme que ele está instalado (`uv sync`). Se persistir, defina `LLM_CA_BUNDLE` no `.env` com o `.pem` da CA da empresa. **Não** desative a verificação SSL.

### Banco SQLite corrompido
```bash
cd backend
rm reclamacoes.db  # Será recriado automaticamente na próxima execução
```

---

## 📝 Licença

Projeto desenvolvido para fins educacionais/demonstração - Desafio FinGuard Nível 1.

---

## 🤝 Contribuição

1. Fork o projeto
2. Crie branch: `git checkout -b feature/nova-funcionalidade`
3. Commit: `git commit -m 'feat: adiciona nova funcionalidade'`
4. Push: `git push origin feature/nova-funcionalidade`
5. Abra Pull Request

---

## 📞 Suporte

- **Issues**: Reporte bugs ou sugira melhorias
- **Documentação técnica**: Veja `spec.md` para especificação completa
- **Swagger UI**: `http://localhost:8000/docs` (com backend rodando)

---

**Desenvolvido com ❤️ usando FastAPI + HTML/CSS/JavaScript puro + LLM**
