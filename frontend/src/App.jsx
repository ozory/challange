import { useState, useCallback } from 'react';
import Header from './components/Header';
import ChatPanel from './components/ChatPanel';
import DashboardPanel from './components/DashboardPanel';
import TicketTable from './components/TicketTable';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' ou 'tabela'
  const [refreshKey, setRefreshKey] = useState(0);

  const triggerRefresh = useCallback(() => {
    setRefreshKey(prev => prev + 1);
  }, []);

  const handleNewAnalysis = useCallback(() => {
    triggerRefresh();
  }, [triggerRefresh]);

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)] flex flex-col">
      <Header 
        onUploadSuccess={triggerRefresh}
        onClearData={triggerRefresh}
        onRefresh={triggerRefresh}
      />
      
      <div className="flex-1 flex overflow-hidden">
        {/* Painel Esquerdo - Chatbot */}
        <div className="w-full lg:w-96 xl:w-[380px] flex-shrink-0 border-r border-[var(--color-border-primary)]">
          <ChatPanel onNewAnalysis={handleNewAnalysis} />
        </div>

        {/* Painel Direito - Dashboard + Tabela */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Abas de navegação */}
          <div className="border-b border-[var(--color-border-primary)] bg-[var(--color-bg-secondary)] px-4">
            <nav className="flex gap-1" role="tablist">
              <button
                role="tab"
                aria-selected={activeTab === 'dashboard'}
                onClick={() => setActiveTab('dashboard')}
                className={`px-4 py-3 text-sm font-medium rounded-t-lg transition-colors relative ${
                  activeTab === 'dashboard'
                    ? 'text-[var(--color-accent-primary)]'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)]'
                }`}
              >
                Dashboard
                {activeTab === 'dashboard' && (
                  <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 bg-[var(--color-accent-primary)] rounded-full" />
                )}
              </button>
              <button
                role="tab"
                aria-selected={activeTab === 'tabela'}
                onClick={() => setActiveTab('tabela')}
                className={`px-4 py-3 text-sm font-medium rounded-t-lg transition-colors relative ${
                  activeTab === 'tabela'
                    ? 'text-[var(--color-accent-primary)]'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)]'
                }`}
              >
                Tabela de Reclamações
                {activeTab === 'tabela' && (
                  <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 bg-[var(--color-accent-primary)] rounded-full" />
                )}
              </button>
            </nav>
          </div>

          {/* Conteúdo das abas */}
          <div className="flex-1 min-h-0 overflow-hidden">
            {activeTab === 'dashboard' && (
              <DashboardPanel onRefresh={refreshKey} />
            )}
            {activeTab === 'tabela' && (
              <TicketTable onRefresh={refreshKey} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
