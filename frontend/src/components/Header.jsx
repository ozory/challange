import { Upload, Download, Trash2, RefreshCw, Shield } from 'lucide-react';
import { useState } from 'react';
import { uploadCSV, exportarDados, limparReclamacoes, obterMetricas } from '../services/api';
import ThemeToggle from './ThemeToggle';

export default function Header({ onUploadSuccess, onClearData, onRefresh }) {
  const [uploading, setUploading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [clearing, setClearing] = useState(false);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    try {
      const result = await uploadCSV(file);
      if (result.success) {
        alert(`Processamento concluído: ${result.processados} processados, ${result.erros} erros`);
        onUploadSuccess?.();
      } else {
        alert('Erro no processamento do CSV');
      }
    } catch (error) {
      console.error('Erro no upload:', error);
      alert('Erro ao fazer upload do arquivo');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleExport = async (format) => {
    setExporting(true);
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
    } finally {
      setExporting(false);
    }
  };

  const handleClear = async () => {
    if (!window.confirm('Tem certeza que deseja remover TODAS as reclamações? Esta ação não pode ser desfeita.')) {
      return;
    }

    setClearing(true);
    try {
      await limparReclamacoes();
      alert('Todas as reclamações foram removidas');
      onClearData?.();
    } catch (error) {
      console.error('Erro ao limpar:', error);
      alert('Erro ao limpar dados');
    } finally {
      setClearing(false);
    }
  };

  const handleRefresh = async () => {
    try {
      await obterMetricas();
      onRefresh?.();
    } catch (error) {
      console.error('Erro ao atualizar:', error);
    }
  };

  return (
    <header className="border-b border-[var(--color-border-primary)] px-4 py-3 glass sticky top-0 z-50">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-[var(--color-accent-primary)] to-[var(--color-accent-secondary)] rounded-xl flex items-center justify-center shadow-lg">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[var(--color-text-primary)] gradient-text">FinGuard</h1>
            <p className="text-xs text-[var(--color-text-muted)]">Triagem Inteligente de Reclamações</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <label className="cursor-pointer group">
            <input
              type="file"
              accept=".csv"
              onChange={handleFileUpload}
              className="sr-only"
              disabled={uploading}
            />
            <button
              type="button"
              className="btn btn-primary px-4 py-2 text-sm font-medium flex items-center gap-2 group-hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={uploading}
            >
              <Upload className="w-4 h-4" />
              <span>{uploading ? 'Processando...' : 'Importar CSV'}</span>
            </button>
          </label>

          <div className="hidden sm:flex items-center gap-1 border-l border-[var(--color-border-primary)] pl-3">
            <button
              onClick={() => handleExport('json')}
              disabled={exporting}
              className="btn btn-secondary px-3 py-2 text-sm font-medium flex items-center gap-1.5 disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              JSON
            </button>
            <button
              onClick={() => handleExport('csv')}
              disabled={exporting}
              className="btn btn-secondary px-3 py-2 text-sm font-medium flex items-center gap-1.5 disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              CSV
            </button>
            <button
              onClick={() => handleExport('html')}
              disabled={exporting}
              className="btn btn-secondary px-3 py-2 text-sm font-medium flex items-center gap-1.5 disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              HTML
            </button>
          </div>

          <button
            onClick={handleRefresh}
            className="btn btn-ghost p-2"
            title="Atualizar dados"
          >
            <RefreshCw className="w-5 h-5" />
          </button>

          <button
            onClick={handleClear}
            disabled={clearing}
            className="btn btn-ghost p-2 text-[var(--color-danger)] hover:bg-[var(--color-danger)]/10"
            title="Limpar todos os dados"
          >
            <Trash2 className="w-5 h-5" />
          </button>

          <div className="w-px h-6 bg-[var(--color-border-primary)] mx-1" />

          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}