import { Search, Filter, ChevronDown, ChevronUp, Download, AlertTriangle, RefreshCw, X } from 'lucide-react';
import { useState, useEffect, useMemo } from 'react';
import { listarReclamacoes, exportarDados } from '../services/api';

export default function TicketTable({ onRefresh }) {
  const [reclamacoes, setReclamacoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filtroTexto, setFiltroTexto] = useState('');
  const [filtroCategoria, setFiltroCategoria] = useState('todas');
  const [filtroProduto, setFiltroProduto] = useState('todos');
  const [filtroSentimento, setFiltroSentimento] = useState('todos');
  const [filtroUrgencia, setFiltroUrgencia] = useState('todas');
  const [ordenacao, setOrdenacao] = useState({ campo: 'data_registro', direcao: 'desc' });
  const [paginaAtual, setPaginaAtual] = useState(1);
  const itensPorPagina = 10;

  const carregarReclamacoes = async () => {
    try {
      const data = await listarReclamacoes();
      setReclamacoes(data);
      setPaginaAtual(1);
      setError(null);
    } catch (err) {
      console.error('Erro ao carregar reclamações:', err);
      setError('Falha ao carregar reclamações');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // This effect synchronizes with external API
    // eslint-disable-next-line react/set-state-in-effect
    setLoading(true);
    carregarReclamacoes();
  }, [onRefresh]);

  // Obter valores únicos para filtros
  const categoriasUnicas = useMemo(() => 
    [...new Set(reclamacoes.map(r => r.categoria))].sort(), [reclamacoes]
  );
  const produtosUnicos = useMemo(() => 
    [...new Set(reclamacoes.map(r => r.produto))].sort(), [reclamacoes]
  );
  const sentimentosUnicos = useMemo(() => 
    [...new Set(reclamacoes.map(r => r.sentimento))].sort(), [reclamacoes]
  );
  const urgenciasUnicas = useMemo(() => 
    [...new Set(reclamacoes.map(r => r.urgencia))].sort(), [reclamacoes]
  );

  // Filtrar e ordenar
  const reclamacoesFiltradas = useMemo(() => {
    return reclamacoes.filter(r => {
      const matchTexto = !filtroTexto || 
        r.texto_original.toLowerCase().includes(filtroTexto.toLowerCase()) ||
        r.id.toLowerCase().includes(filtroTexto.toLowerCase()) ||
        r.resumo.toLowerCase().includes(filtroTexto.toLowerCase());
      
      const matchCategoria = filtroCategoria === 'todas' || r.categoria === filtroCategoria;
      const matchProduto = filtroProduto === 'todos' || r.produto === filtroProduto;
      const matchSentimento = filtroSentimento === 'todos' || r.sentimento === filtroSentimento;
      const matchUrgencia = filtroUrgencia === 'todas' || r.urgencia === filtroUrgencia;
      
      return matchTexto && matchCategoria && matchProduto && matchSentimento && matchUrgencia;
    }).sort((a, b) => {
      let valorA = a[ordenacao.campo];
      let valorB = b[ordenacao.campo];
      
      if (typeof valorA === 'string') {
        valorA = valorA.toLowerCase();
        valorB = valorB.toLowerCase();
      }
      
      if (valorA < valorB) return ordenacao.direcao === 'asc' ? -1 : 1;
      if (valorA > valorB) return ordenacao.direcao === 'asc' ? 1 : -1;
      return 0;
    });
  }, [reclamacoes, filtroTexto, filtroCategoria, filtroProduto, filtroSentimento, filtroUrgencia, ordenacao]);

  // Paginação
  const totalPaginas = Math.ceil(reclamacoesFiltradas.length / itensPorPagina);
  const reclamacoesPagina = reclamacoesFiltradas.slice(
    (paginaAtual - 1) * itensPorPagina,
    paginaAtual * itensPorPagina
  );

  const handleOrdenar = (campo) => {
    setOrdenacao(prev => ({
      campo,
      direcao: prev.campo === campo && prev.direcao === 'asc' ? 'desc' : 'asc'
    }));
  };

  const getUrgenciaBadge = (urgencia) => {
    const styles = {
      'Crítica': 'badge badge-danger',
      'Alta': 'badge badge-warning',
      'Média': 'badge badge-warning',
      'Baixa': 'badge badge-success',
    };
    return styles[urgencia] || 'badge';
  };

  const getSentimentoBadge = (sentimento) => {
    const styles = {
      'Positivo': 'badge badge-success',
      'Neutro': 'badge',
      'Negativo': 'badge badge-danger',
      'Crítico': 'badge badge-danger',
    };
    return styles[sentimento] || 'badge';
  };

  const getCategoriaBadge = (categoria) => {
    if (categoria === 'Fraude/Segurança') return 'badge badge-danger';
    return 'badge badge-primary';
  };

  const formatarData = (dataStr) => {
    if (!dataStr) return 'N/A';
    try {
      const data = new Date(dataStr);
      return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch {
      return dataStr;
    }
  };

  const handleExport = async (format) => {
    try {
      const blob = await exportarDados(format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reclamacoes.${format === 'html' ? 'html' : format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Erro na exportação:', error);
      alert('Erro ao exportar dados');
    }
  };

  const clearFilters = () => {
    setFiltroTexto('');
    setFiltroCategoria('todas');
    setFiltroProduto('todos');
    setFiltroSentimento('todos');
    setFiltroUrgencia('todas');
  };

  const hasActiveFilters = filtroTexto || filtroCategoria !== 'todas' || filtroProduto !== 'todos' || filtroSentimento !== 'todos' || filtroUrgencia !== 'todas';

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b border-[var(--color-border-primary)] bg-[var(--color-bg-secondary)]">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
            <svg className="w-5 h-5 text-[var(--color-accent-primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            Tabela de Reclamações
          </h2>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-pulse space-y-4 w-full max-w-4xl px-4">
            {[1,2,3,4,5].map(i => <div key={i} className="skeleton h-12 rounded-lg"></div>)}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col h-full p-6">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-[var(--color-danger)]">
            <AlertTriangle className="w-12 h-12 mx-auto mb-3" />
            <p className="text-[var(--color-text-secondary)]">{error}</p>
            <button onClick={carregarReclamacoes} className="mt-4 btn btn-primary">
              Tentar novamente
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0 bg-[var(--color-bg-primary)]">
      {/* Header com filtros */}
      <div className="p-4 border-b border-[var(--color-border-primary)] bg-[var(--color-bg-secondary)]">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
            <svg className="w-5 h-5 text-[var(--color-accent-primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            Tabela de Reclamações
          </h2>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport('json')}
              className="btn btn-secondary px-3 py-2 text-sm font-medium flex items-center gap-1.5"
            >
              <Download className="w-4 h-4" />
              JSON
            </button>
            <button
              onClick={() => handleExport('csv')}
              className="btn btn-secondary px-3 py-2 text-sm font-medium flex items-center gap-1.5"
            >
              <Download className="w-4 h-4" />
              CSV
            </button>
            <button
              onClick={() => handleExport('html')}
              className="btn btn-secondary px-3 py-2 text-sm font-medium flex items-center gap-1.5"
            >
              <Download className="w-4 h-4" />
              HTML
            </button>
            <button
              onClick={carregarReclamacoes}
              className="btn btn-ghost p-2"
              title="Atualizar"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Filtros */}
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-muted)]" />
              <input
                type="text"
                placeholder="Buscar por ID, texto, resumo..."
                value={filtroTexto}
                onChange={(e) => setFiltroTexto(e.target.value)}
                className="input pl-10"
              />
              {filtroTexto && (
                <button
                  onClick={() => setFiltroTexto('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            
            <select
              value={filtroCategoria}
              onChange={(e) => setFiltroCategoria(e.target.value)}
              className="input min-w-[150px]"
            >
              <option value="todas">Todas Categorias</option>
              {categoriasUnicas.map(cat => <option key={cat} value={cat}>{cat}</option>)}
            </select>

            <select
              value={filtroProduto}
              onChange={(e) => setFiltroProduto(e.target.value)}
              className="input min-w-[150px]"
            >
              <option value="todos">Todos Produtos</option>
              {produtosUnicos.map(prod => <option key={prod} value={prod}>{prod}</option>)}
            </select>

            <select
              value={filtroSentimento}
              onChange={(e) => setFiltroSentimento(e.target.value)}
              className="input min-w-[130px]"
            >
              <option value="todos">Todos Sentimentos</option>
              {sentimentosUnicos.map(sent => <option key={sent} value={sent}>{sent}</option>)}
            </select>

            <select
              value={filtroUrgencia}
              onChange={(e) => setFiltroUrgencia(e.target.value)}
              className="input min-w-[130px]"
            >
              <option value="todas">Todas Urgências</option>
              {urgenciasUnicas.map(urg => <option key={urg} value={urg}>{urg}</option>)}
            </select>
          </div>

          {hasActiveFilters && (
            <div className="flex items-center justify-between pt-2 border-t border-[var(--color-border-primary)]">
              <p className="text-sm text-[var(--color-text-muted)]">
                {reclamacoesFiltradas.length} de {reclamacoes.length} reclamações
              </p>
              <button
                onClick={clearFilters}
                className="btn btn-ghost text-sm px-3 py-1.5 flex items-center gap-1.5"
              >
                <Filter className="w-4 h-4" />
                Limpar filtros
              </button>
            </div>
          )}
          
          {!hasActiveFilters && (
            <p className="text-sm text-[var(--color-text-muted)]">
              {reclamacoesFiltradas.length} de {reclamacoes.length} reclamações
            </p>
          )}
        </div>
      </div>

      {/* Tabela com paginação fixa no rodapé */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {reclamacoesFiltradas.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="empty-state">
              <svg className="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-[var(--color-text-muted)]">Nenhuma reclamação encontrada com os filtros atuais</p>
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-x-auto overflow-y-auto min-h-0">
              <table className="table">
                <thead>
                  <tr>
                    {[
                      { key: 'id', label: 'ID' },
                      { key: 'data_registro', label: 'Data' },
                      { key: 'canal', label: 'Canal' },
                      { key: 'categoria', label: 'Categoria' },
                      { key: 'produto', label: 'Produto' },
                      { key: 'sentimento', label: 'Sentimento' },
                      { key: 'urgencia', label: 'Urgência' },
                      { key: 'resumo', label: 'Resumo' },
                    ].map(col => (
                      <th
                        key={col.key}
                        onClick={() => handleOrdenar(col.key)}
                        className="cursor-pointer select-none hover:bg-[var(--color-bg-hover)]"
                      >
                        <div className="flex items-center gap-1">
                          {col.label}
                          {ordenacao.campo === col.key && (
                            ordenacao.direcao === 'asc' ? <ChevronUp className="w-4 h-4 text-[var(--color-accent-primary)]" /> : <ChevronDown className="w-4 h-4 text-[var(--color-accent-primary)]" />
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {reclamacoesPagina.map((r, index) => (
                    <tr 
                      key={r.id} 
                      className={r.categoria === 'Fraude/Segurança' ? 'bg-[var(--color-danger)]/5' : index % 2 === 0 ? '' : 'bg-[var(--color-bg-tertiary)]/50'}
                    >
                      <td className="font-mono text-xs text-[var(--color-text-primary)]">{r.id}</td>
                      <td className="text-[var(--color-text-secondary)]">{formatarData(r.data_registro)}</td>
                      <td className="text-[var(--color-text-secondary)]">{r.canal || 'N/A'}</td>
                      <td className="font-medium text-[var(--color-text-primary)]">
                        <span className={getCategoriaBadge(r.categoria)}>
                          {r.categoria === 'Fraude/Segurança' && (
                            <>
                              <AlertTriangle className="w-3 h-3 inline-block mr-1" />
                            </>
                          )}
                          {r.categoria}
                        </span>
                      </td>
                      <td className="text-[var(--color-text-secondary)]">{r.produto}</td>
                      <td>
                        <span className={getSentimentoBadge(r.sentimento)}>
                          {r.sentimento}
                        </span>
                      </td>
                      <td>
                        <span className={getUrgenciaBadge(r.urgencia)}>
                          {r.urgencia}
                        </span>
                      </td>
                      <td className="text-[var(--color-text-secondary)] max-w-xs truncate" title={r.resumo}>
                        {r.resumo}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Paginação fixa no rodapé da tabela */}
            {totalPaginas > 1 && (
              <div className="flex-shrink-0 p-3 border-t border-[var(--color-border-primary)] bg-[var(--color-bg-secondary)]/95 backdrop-blur-sm flex items-center justify-between">
                <p className="text-sm text-[var(--color-text-muted)]">
                  Página {paginaAtual} de {totalPaginas}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPaginaAtual(p => Math.max(1, p - 1))}
                    disabled={paginaAtual === 1}
                    className="btn btn-secondary px-3 py-1.5 text-sm font-medium flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <ChevronDown className="w-4 h-4 rotate-180" />
                    Anterior
                  </button>
                  <button
                    onClick={() => setPaginaAtual(p => Math.min(totalPaginas, p + 1))}
                    disabled={paginaAtual === totalPaginas}
                    className="btn btn-secondary px-3 py-1.5 text-sm font-medium flex items-center gap-1.5 disabled:opacity-50"
                  >
                    Próxima
                    <ChevronDown className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}