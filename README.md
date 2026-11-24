# FinGuard - Triagem Inteligente de Reclamações Financeiras

> **Nível 1 - Classificador Inteligente** | Solução full-stack local para triagem e análise automatizada de reclamações de clientes de instituições financeiras.

---

## 📋 Visão Geral

O **FinGuard** é uma aplicação web full-stack que recebe reclamações em texto livre (via chatbot individual ou importação em lote via CSV) e utiliza a StackSpot AI com a política interna local como contexto para classificar, resumir e priorizar os atendimentos, alimentando dinamicamente um Dashboard gerencial.

### ✨ Funcionalidades Principais

| Funcionalidade | Descrição |
|----------------|-----------|
| 🤖 **Chatbot Interativo** | Recebe texto livre e retorna análise estruturada imediata |
| 📊 **Processamento em Lote (CSV)** | Suporta dataset de ~500 reclamações com concorrência controlada |
| 🛡️ **Ofuscação de Palavras Impróprias** | Remove/sanitiza termos ofensivos no campo `resumo` |
| 📤 **Exportação Múltipla** | JSON, CSV e HTML consolidado com gráficos Chart.js |
| 🏠 **Persistência local** | SQLite e arquivos de exportação permanecem locais; a inferência usa a API StackSpot |

---

## 🛠️ Stack Tecnológica

### Backend
| Tecnologia | Versão | Uso |
|------------|--------|-----|
| **Python** | 3.12+ | Linguagem principal |
| **FastAPI** | 0.109.0 | Framework web assíncrono |
| **Uvicorn** | 0.27.0 | Servidor ASGI |
| **Pydantic** | 2.5.3 | Validação e serialização |
| **Pandas** | 2.1.4 | Manipulação de CSV/JSON |
| **SQLite** | Built-in | Persistência local |
| **httpx** | 0.26.0 | Cliente HTTP assíncrono para LLM |
| **python-dotenv** | 1.0.0 | Variáveis de ambiente |
| **StackSpot AI** | REST | Agente de classificação e Knowledge Source |

### Frontend
| Tecnologia | Versão | Uso |
|------------|--------|-----|
| **React** | 19.3.1 | Framework UI |
| **Vite** | 8.3.6 | Build tool & dev server |
| **Tailwind CSS** | 4.3.5 | Estilização utilitária |
| **Recharts** | 3.11.0 | Visualização de dados |
| **Lucide React** | 1.78.0 | Ícones |
| **Axios** | 1.21.1 | Cliente HTTP |
| **Oxlint** | 1.90.0 | Linting rápido |

---

## 📁 Estrutura do Projeto

```
challange/
├── README.md                 # Este arquivo
├── spec.md                   # Especificação técnica completa
├── challange.pdf             # Documento original do desafio
├── data.csv                  # Dataset de exemplo (~500 reclamações)
├── reclamacoes.json          # Dados de exemplo em JSON
├── backend/
│   ├── main.py               # Entrada FastAPI, rotas HTTP, CORS
│   ├── schemas.py            # Modelos Pydantic e Enums
│   ├── llm_service.py        # StackSpot REST + contexto da política interna
│   ├── sanitizer.py          # Filtro de palavras impróprias
│   ├── repository.py         # Camada SQLite (thread-safe)
│   ├── exporter.py           # Gerador de relatórios (JSON/CSV/HTML)
│   ├── politica_interna.txt  # Contexto para RAG local
│   ├── pyproject.toml        # Configuração do projeto (uv/poetry)
│   ├── requirements.txt      # Dependências pip
│   ├── uv.lock               # Lock file do uv
│   ├── reclamacoes.db        # Banco SQLite (criado automaticamente)
│   └── .env                  # Variáveis de ambiente (não versionado)
└── frontend/
    ├── index.html            # Entry point HTML
    ├── package.json          # Dependências npm
    ├── vite.config.js        # Configuração Vite + Tailwind
    ├── .oxlintrc.json        # Configuração Oxlint
    ├── public/               # Assets estáticos
    └── src/
        ├── main.jsx          # Bootstrap React
        ├── App.jsx           # Componente raiz + estado global
        ├── index.css         # Estilos globais + Tailwind
        ├── services/
        │   └── api.js        # Cliente Axios para API
        ├── components/
        │   ├── Header.jsx    # Título + ações (Export/Upload/Limpar)
        │   ├── ChatPanel.jsx # Interface do chatbot
        │   ├── DashboardPanel.jsx # KPIs + Gráficos (Recharts)
        │   ├── TicketTable.jsx    # Tabela com filtros/busca
        │   └── ThemeToggle.jsx    # Toggle dark/light mode
        └── context/
            └── ThemeContext.jsx   # Contexto de tema
```

---

## 🚀 Como Executar Localmente

### Pré-requisitos
- **Python 3.12+** (recomendado usar `uv` ou `venv`)
- **Node.js 18+** e **npm**
- **Git** (opcional)

---

### 1. Backend (FastAPI)

```bash
# Entrar no diretório do backend
cd backend

# Opção A: Usando uv (recomendado - mais rápido)
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Opção B: Usando venv + pip tradicional
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

> **Nota:** O backend roda em `http://localhost:8000`
> - Documentação Swagger: `http://localhost:8000/docs`
> - Documentação ReDoc: `http://localhost:8000/redoc`

#### Variáveis de Ambiente (Backend)
Crie um arquivo `.env` na pasta `backend/` com as credenciais do agente autorizado:
```env
STACKSPOT_REALM=seu_realm
STACKSPOT_CLIENT_ID=seu_client_id
STACKSPOT_CLIENT_SECRET=seu_client_secret
STACKSPOT_AGENT_URL=https://genai-inference-app.stackspot.com/v1/agent/SEU_AGENT_ID/chat
```

Na mesma máquina com o projeto `finguard-nivel1`, é possível reutilizar sua configuração sem copiar o segredo:

```env
STACKSPOT_ENV_FILE=../../finguard-nivel1/.env
```

O caminho é relativo à pasta `backend/`; valores preenchidos no ambiente ou no `.env` do backend têm prioridade. Não versione nem compartilhe arquivos com credenciais. O arquivo `backend/.env.example` contém um modelo sem segredos.

A autenticação usa OAuth2 client credentials, com token em memória e renovação ao expirar ou após HTTP 401. O agente é chamado em modo não streaming, com `stackspot_knowledge` habilitado. Sem configuração válida ou em caso de falha, a classificação é informada como erro; não há fallback fictício.

> A reclamação e o conteúdo da política local são enviados à StackSpot. Use somente dados e ambientes autorizados para o desafio; o armazenamento local não torna a inferência offline.

---

### 2. Frontend (React + Vite)

```bash
# Em outro terminal, entrar no diretório do frontend
cd frontend

# Instalar dependências
npm install

# Iniciar servidor de desenvolvimento
npm run dev
```

> **Nota:** O frontend roda em `http://localhost:5173` (ou porta indicada pelo Vite)

#### Build de Produção
```bash
npm run build
npm run preview  # Visualizar build local
```

---

### 3. Executar Tudo Junto (Desenvolvimento)

```bash
# Terminal 1 - Backend
cd backend && uv run uvicorn main:app --reload

# Terminal 2 - Frontend
cd frontend && npm run dev
```

Acesse: **http://localhost:5173** (frontend) → comunica com **http://localhost:8000** (backend)

---

## 📡 API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/` | Health check básico |
| `GET` | `/health` | Status da API |
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
main.py (Rotas HTTP)
    │
    ├── llm_service.py (StackSpot REST + contexto local)
    │       │
    │       ├── politica_interna.txt (Contexto injetado no prompt)
    │       └── sanitizer.py (Ofuscação de termos ofensivos)
    │
    ├── repository.py (SQLite thread-safe)
    │       └── reclamacoes.db (Persistência local)
    │
    └── exporter.py (JSON/CSV/HTML com Chart.js)
```

### Concorrência no Processamento em Lote
- Usa `asyncio.Semaphore(5)` para limitar requisições simultâneas à LLM
- Processa linhas do CSV em paralelo com `asyncio.gather()`
- Uma nova tentativa em caso de falha na inferência ou parsing; um HTTP 401 também renova o token

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
│   ChatPanel      │     DashboardPanel / TicketTable     │
│   (Esquerda)     │     (Direita - Abas)                 │
│                  │                                      │
│  - Input texto   │  - KPIs (Total, Críticas, etc.)      │
│  - Histórico     │  - Gráficos (Recharts)               │
│  - Loading       │  - Tabela com filtros/busca          │
│                  │                                      │
└──────────────────┴──────────────────────────────────────┘
```

### Sincronização em Tempo Real
- `refreshKey` no `App.jsx` força re-render dos painéis
- `triggerRefresh()` chamado após: nova análise, upload CSV, limpeza, exportação
- Dashboard e Tabela atualizam automaticamente

---

## 📊 Dataset de Exemplo

O projeto inclui:
- **`data.csv`** - ~500 reclamações simuladas com colunas: `id`, `data_reclamacao`, `canal`, `texto_reclamacao`, `produto`, `status`
- **`reclamacoes.json`** - Mesmo dataset em JSON

Use o botão **"Importar CSV"** no Header para processar o dataset de exemplo.

---

## 🧪 Testes

### Backend
```bash
cd backend
python -m unittest discover -s tests -v
```

### Frontend (Lint)
```bash
cd frontend
npm run lint
```

---

## 🐛 Troubleshooting

### Backend não inicia
```bash
# Verificar Python version
python --version  # Deve ser 3.12+

# Reinstalar dependências
uv sync --frozen
# ou
pip install -r requirements.txt --force-reinstall
```

### Frontend não conecta no Backend
1. Verifique se backend roda na porta 8000: `curl http://localhost:8000/health`
2. Verifique CORS no `main.py` - `allow_origins=["*"]` já configurado
3. Confira `API_BASE_URL` em `frontend/src/services/api.js`

### Erro na StackSpot (401/403/429)
- Confira `STACKSPOT_REALM`, `STACKSPOT_CLIENT_ID`, `STACKSPOT_CLIENT_SECRET` e `STACKSPOT_AGENT_URL` no ambiente autorizado.
- Para `STACKSPOT_ENV_FILE`, confirme que o caminho relativo ao backend existe e que o processo tem permissão de leitura.
- Verifique as permissões do agente, a conectividade e os limites de uso. Falhas não são convertidas em classificação simulada.

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

**Desenvolvido com ❤️ usando FastAPI + React + LLM Local**