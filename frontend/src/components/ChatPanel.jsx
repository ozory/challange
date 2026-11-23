import { Send, Loader2, AlertCircle, Bot, MessageSquare } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { classificarReclamacao } from '../services/api';

export default function ChatPanel({ onNewAnalysis }) {
  const [mensagem, setMensagem] = useState('');
  const [historico, setHistorico] = useState([]);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [historico]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!mensagem.trim() || enviando) return;

    const texto = mensagem.trim();
    setMensagem('');
    setErro(null);
    setEnviando(true);

    // Adicionar mensagem do usuário ao histórico
    const userMsg = { tipo: 'user', texto, timestamp: new Date() };
    setHistorico(prev => [...prev, userMsg]);

    try {
      const result = await classificarReclamacao(texto);
      
      if (result.success && result.data) {
        // Adicionar resposta da IA ao histórico
        const aiMsg = { 
          tipo: 'ai', 
          data: result.data, 
          timestamp: new Date() 
        };
        setHistorico(prev => [...prev, aiMsg]);
        onNewAnalysis?.(result.data);
      } else {
        throw new Error(result.error || 'Erro na classificação');
      }
    } catch (error) {
      console.error('Erro:', error);
      setErro(error.message);
      const errorMsg = { 
        tipo: 'error', 
        texto: `Erro: ${error.message}`, 
        timestamp: new Date() 
      };
      setHistorico(prev => [...prev, errorMsg]);
    } finally {
      setEnviando(false);
    }
  };

  const formatarHora = (date) => {
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
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

  const getCategoriaBadge = () => 'badge badge-primary';
  const getProdutoBadge = () => 'badge badge-info';

  return (
    <div className="flex flex-col h-full min-h-0 bg-[var(--color-bg-primary)] border-r border-[var(--color-border-primary)]">
      <div className="p-4 border-b border-[var(--color-border-primary)] bg-[var(--color-bg-secondary)]">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
          <Bot className="w-5 h-5 text-[var(--color-accent-primary)]" />
          Chatbot de Triagem
        </h2>
        <p className="text-xs text-[var(--color-text-muted)] mt-1">Digite uma reclamação em texto livre para análise imediata</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4" ref={messagesEndRef}>
        {historico.length === 0 && (
          <div className="empty-state animate-fade-in">
            <MessageSquare className="w-16 h-16" />
            <p className="text-sm text-[var(--color-text-muted)]">Envie sua primeira reclamação para começar</p>
          </div>
        )}

        {historico.map((msg, index) => (
          <div key={index} className={`flex animate-fade-in ${msg.tipo === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] ${msg.tipo === 'user' ? 'order-2' : 'order-1'}`}>
              <div className={`flex items-start gap-2 ${msg.tipo === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  msg.tipo === 'user' 
                    ? 'bg-gradient-to-br from-[var(--color-accent-primary)] to-[var(--color-accent-secondary)] text-white' 
                    : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'
                }`}>
                  {msg.tipo === 'user' ? (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  ) : (
                    <Bot className="w-5 h-5" />
                  )}
                </div>
                <div className={`px-4 py-3 rounded-2xl ${
                  msg.tipo === 'user' 
                    ? 'bg-gradient-to-br from-[var(--color-accent-primary)] to-[var(--color-accent-secondary)] text-white rounded-br-none shadow-lg' 
                    : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-primary)] rounded-bl-none border border-[var(--color-border-primary)] shadow-sm'
                }`}>
                  {msg.tipo === 'user' ? (
                    <p className="text-sm whitespace-pre-wrap">{msg.texto}</p>
                  ) : msg.tipo === 'error' ? (
                    <div className="flex items-center gap-2 text-[var(--color-danger)] text-sm">
                      <AlertCircle className="w-4 h-4 flex-shrink-0" />
                      <span>{msg.texto}</span>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="flex flex-wrap gap-2">
                        <span className={getUrgenciaBadge(msg.data.urgencia)}>
                          {msg.data.urgencia}
                        </span>
                        <span className={getSentimentoBadge(msg.data.sentimento)}>
                          {msg.data.sentimento}
                        </span>
                        <span className={getCategoriaBadge()}>
                          {msg.data.categoria}
                        </span>
                        <span className={getProdutoBadge()}>
                          {msg.data.produto}
                        </span>
                      </div>
                      <p className="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap">{msg.data.resumo}</p>
                      <p className="text-xs text-[var(--color-text-muted)] font-mono">ID: {msg.data.id}</p>
                    </div>
                  )}
                </div>
              </div>
              <p className={`text-xs text-[var(--color-text-muted)] mt-1 ${msg.tipo === 'user' ? 'text-right pr-1' : 'pl-1'}`}>
                {formatarHora(msg.timestamp)}
              </p>
            </div>
          </div>
        ))}

        {enviando && (
          <div className="flex justify-start animate-fade-in">
            <div className="flex items-start gap-2">
              <div className="w-8 h-8 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center flex-shrink-0">
                <Bot className="w-5 h-5 text-[var(--color-text-secondary)]" />
              </div>
              <div className="px-4 py-3 bg-[var(--color-bg-secondary)] rounded-2xl rounded-bl-none border border-[var(--color-border-primary)] shadow-sm flex items-center gap-2">
                <Loader2 className="w-4 h-4 text-[var(--color-accent-primary)] animate-spin" />
                <span className="text-sm text-[var(--color-text-muted)]">Analisando...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {erro && (
        <div className="mx-4 mb-3 p-3 bg-[var(--color-danger)]/10 border border-[var(--color-danger)]/20 rounded-lg flex items-center gap-2 text-[var(--color-danger)] animate-slide-in">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm">{erro}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="p-4 bg-[var(--color-bg-secondary)] border-t border-[var(--color-border-primary)]">
        <div className="flex gap-2">
          <textarea
            value={mensagem}
            onChange={(e) => setMensagem(e.target.value)}
            placeholder="Digite a reclamação do cliente aqui..."
            rows={3}
            className="input flex-1 resize-none"
            disabled={enviando}
            style={{ minHeight: '80px' }}
          />
          <button
            type="submit"
            disabled={!mensagem.trim() || enviando}
            className="btn btn-primary px-4 py-3 flex items-center gap-2 whitespace-nowrap"
          >
            <Send className="w-5 h-5" />
            <span className="hidden sm:inline">Enviar</span>
          </button>
        </div>
        <p className="text-xs text-[var(--color-text-muted)] mt-2 text-center">
          Pressione Enter para enviar • Shift+Enter para nova linha
        </p>
      </form>
    </div>
  );
}