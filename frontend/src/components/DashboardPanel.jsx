import {
  BarChart, Bar, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { TrendingUp, Users, AlertTriangle, Clock, RefreshCw, TrendingDown, Target } from 'lucide-react';
import { obterMetricas } from '../services/api';
import { useState, useEffect, useMemo } from 'react';

// Modern color palette that works in both light and dark themes
const CHART_COLORS = {
  categoria: ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16'],
  produto: ['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'],
  sentimento: ['#10b981', '#6b7280', '#ef4444', '#dc2626'],
  urgencia: ['#16a34a', '#d97706', '#ea580c', '#dc2626'],
};

const KPI_ICONS = {
  blue: { icon: Users, bg: 'bg-blue-500/10', color: 'text-blue-500' },
  purple: { icon: TrendingUp, bg: 'bg-purple-500/10', color: 'text-purple-500' },
  red: { icon: AlertTriangle, bg: 'bg-red-500/10', color: 'text-red-500' },
  orange: { icon: Clock, bg: 'bg-orange-500/10', color: 'text-orange-500' },
  green: { icon: Target, bg: 'bg-green-500/10', color: 'text-green-500' },
};

export default function DashboardPanel({ onRefresh }) {
  const [metricas, setMetricas] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const carregarMetricas = async () => {
    try {
      const data = await obterMetricas();
      setMetricas(data);
      setError(null);
    } catch (err) {
      console.error('Erro ao carregar métricas:', err);
      setError('Falha ao carregar dados do dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // This effect synchronizes with external API
    // eslint-disable-next-line react/set-state-in-effect
    setLoading(true);
    carregarMetricas();
  }, [onRefresh]);

  // Preparar dados para gráficos
  const chartData = useMemo(() => {
    if (!metricas) return null;
    
    return {
      categoria: Object.entries(metricas.por_categoria).map(([name, value], i) => ({
        name, value, color: CHART_COLORS.categoria[i % CHART_COLORS.categoria.length]
      })),
      produto: Object.entries(metricas.por_produto).map(([name, value], i) => ({
        name, value, color: CHART_COLORS.produto[i % CHART_COLORS.produto.length]
      })),
      sentimento: Object.entries(metricas.por_sentimento).map(([name, value], i) => ({
        name, value, color: CHART_COLORS.sentimento[i % CHART_COLORS.sentimento.length]
      })),
      urgencia: Object.entries(metricas.por_urgencia).map(([name, value], i) => ({
        name, value, color: CHART_COLORS.urgencia[i % CHART_COLORS.urgencia.length]
      })),
    };
  }, [metricas]);

  const kpiData = useMemo(() => {
    if (!metricas) return [];
    
    return [
      { 
        label: 'Total de Reclamações', 
        value: metricas.total, 
        variant: 'blue',
        trend: '+12%',
        trendUp: true
      },
      { 
        label: 'Categorias Únicas', 
        value: Object.keys(metricas.por_categoria).length, 
        variant: 'purple',
        trend: '+2',
        trendUp: true
      },
      { 
        label: 'Fraude/Segurança', 
        value: metricas.por_categoria['Fraude/Segurança'] || 0, 
        variant: 'red',
        trend: '-5%',
        trendUp: false
      },
      { 
        label: 'Urgência Crítica', 
        value: metricas.por_urgencia['Crítica'] || 0, 
        variant: 'orange',
        trend: '+3',
        trendUp: true
      },
    ];
  }, [metricas]);

  if (loading) {
    return (
      <div className="flex flex-col h-full p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-[var(--color-accent-primary)]" />
            Dashboard Gerencial
          </h2>
          <button
            onClick={carregarMetricas}
            disabled={loading}
            className="btn btn-ghost p-2"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-pulse space-y-4 w-full max-w-4xl">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[1,2,3,4].map(i => <div key={i} className="skeleton h-24 rounded-xl"></div>)}
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
              {[1,2,3,4].map(i => <div key={i} className="skeleton h-72 rounded-xl"></div>)}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col h-full p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-[var(--color-accent-primary)]" />
            Dashboard Gerencial
          </h2>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-[var(--color-danger)]">
            <AlertTriangle className="w-12 h-12 mx-auto mb-3" />
            <p className="text-[var(--color-text-secondary)]">{error}</p>
            <button onClick={carregarMetricas} className="mt-4 btn btn-primary">
              Tentar novamente
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!metricas || !chartData) {
    return null;
  }

  return (
    <div className="flex flex-col h-full min-h-0 p-6 bg-[var(--color-bg-primary)] overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-[var(--color-accent-primary)]" />
          Dashboard Gerencial
        </h2>
        <button
          onClick={carregarMetricas}
          className="btn btn-ghost p-2"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        {kpiData.map((kpi, index) => (
          <KPICard key={index} {...kpi} />
        ))}
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Categoria - Donut */}
        <ChartCard title="Por Categoria">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartData.categoria}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={100}
                paddingAngle={3}
                dataKey="value"
                nameKey="name"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(1)}%`}
                labelLine={false}
              >
                {chartData.categoria.map((_, i) => (
                  <Cell key={`cell-cat-${i}`} fill={CHART_COLORS.categoria[i % CHART_COLORS.categoria.length]} />
                ))}
              </Pie>
              <Tooltip 
                formatter={(value) => [value, 'reclamações']}
                contentStyle={{
                  backgroundColor: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border-primary)',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-lg)',
                }}
              />
              <Legend 
                wrapperStyle={{ paddingTop: '20px' }}
                formatter={(value) => value}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Produto - Bar Horizontal */}
        <ChartCard title="Por Produto">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData.produto} layout="vertical" margin={{ left: 20, right: 20, top: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border-primary)" />
              <XAxis 
                type="number" 
                tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis 
                dataKey="name" 
                type="category" 
                width={140} 
                tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip 
                formatter={(value) => [value, 'reclamações']}
                contentStyle={{
                  backgroundColor: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border-primary)',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-lg)',
                }}
              />
              <Bar 
                dataKey="value" 
                radius={[0, 6, 6, 0]} 
                maxBarSize={36}
              >
                {chartData.produto.map((_, i) => (
                  <Cell key={`cell-prod-${i}`} fill={CHART_COLORS.produto[i % CHART_COLORS.produto.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Sentimento - Pie */}
        <ChartCard title="Por Sentimento">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartData.sentimento}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={100}
                paddingAngle={3}
                dataKey="value"
                nameKey="name"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(1)}%`}
                labelLine={false}
              >
                {chartData.sentimento.map((_, i) => (
                  <Cell key={`cell-sent-${i}`} fill={CHART_COLORS.sentimento[i % CHART_COLORS.sentimento.length]} />
                ))}
              </Pie>
              <Tooltip 
                formatter={(value) => [value, 'reclamações']}
                contentStyle={{
                  backgroundColor: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border-primary)',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-lg)',
                }}
              />
              <Legend 
                wrapperStyle={{ paddingTop: '20px' }}
                formatter={(value) => value}
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Urgência - Bar */}
        <ChartCard title="Por Urgência">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData.urgencia} margin={{ left: 20, right: 20, top: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-primary)" horizontal={false} />
              <XAxis 
                dataKey="name" 
                tick={{ fill: 'var(--color-text-muted)', fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis 
                tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip 
                formatter={(value) => [value, 'reclamações']}
                contentStyle={{
                  backgroundColor: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border-primary)',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-lg)',
                }}
              />
              <Bar 
                dataKey="value" 
                radius={[6, 6, 0, 0]} 
                maxBarSize={48}
              >
                {chartData.urgencia.map((_, i) => (
                  <Cell key={`cell-urg-${i}`} fill={CHART_COLORS.urgencia[i % CHART_COLORS.urgencia.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Legenda de Urgência */}
      <UrgenciaLegend />
    </div>
  );
}

function KPICard({ label, value, variant, trend, trendUp }) {
  const { icon: Icon, bg, color } = KPI_ICONS[variant] || KPI_ICONS.blue;

  return (
    <div className="card-hover bg-[var(--color-bg-secondary)] rounded-xl p-5 border border-[var(--color-border-primary)] shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-1">{label}</p>
          <p className="text-3xl font-bold text-[var(--color-text-primary)]">{value}</p>
          <div className="flex items-center gap-1.5 mt-2">
            <span className={`text-xs font-medium ${trendUp ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'}`}>
              {trendUp ? <TrendingUp className="w-3 h-3 inline-block" /> : <TrendingDown className="w-3 h-3 inline-block" />}
              {trend}
            </span>
            <span className="text-xs text-[var(--color-text-muted)]">vs mês anterior</span>
          </div>
        </div>
        <div className={`p-3 rounded-xl ${bg} ${color}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="card-hover bg-[var(--color-bg-secondary)] rounded-xl p-5 border border-[var(--color-border-primary)] shadow-sm">
      <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-4">{title}</h3>
      <div className="h-72">{children}</div>
    </div>
  );
}

function UrgenciaLegend() {
  const items = [
    { label: 'Crítica', color: CHART_COLORS.urgencia[0] },
    { label: 'Alta', color: CHART_COLORS.urgencia[1] },
    { label: 'Média', color: CHART_COLORS.urgencia[2] },
    { label: 'Baixa', color: CHART_COLORS.urgencia[3] },
  ];

  return (
    <div className="bg-[var(--color-bg-secondary)] rounded-xl p-5 border border-[var(--color-border-primary)] shadow-sm">
      <h3 className="text-sm font-medium text-[var(--color-text-primary)] mb-4 flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-[var(--color-warning)]" />
        Legenda de Urgência
      </h3>
      <div className="flex flex-wrap gap-4 sm:gap-6">
        {items.map((item) => (
          <span key={item.label} className="flex items-center gap-2 text-sm">
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
            <span className="text-[var(--color-text-secondary)]">{item.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
}