/* Aba Dashboard: KPIs + gráficos a partir de /metrics. */
(function () {
  var el = FG.el, icon = FG.icon;

  var PALETTE = {
    categoria: ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16'],
    produto: ['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444']
  };
  // Cores por nome (assim "Crítica" é sempre vermelho, independente da ordem da API)
  var URGENCIA_COLORS = { 'Baixa': '#16a34a', 'Média': '#d97706', 'Alta': '#ea580c', 'Crítica': '#dc2626' };
  var SENTIMENTO_COLORS = { 'Positivo': '#10b981', 'Neutro': '#6b7280', 'Negativo': '#ef4444', 'Crítico': '#dc2626' };
  var URGENCIA_ORDER = ['Baixa', 'Média', 'Alta', 'Crítica'];
  var FALLBACK = '#94a3b8';

  function toSeries(obj, palette, byName) {
    return Object.keys(obj || {}).map(function (name, i) {
      return { name: name, value: obj[name], color: byName ? (byName[name] || FALLBACK) : palette[i % palette.length] };
    });
  }

  function createDashboard() {
    var root = el('div', { class: 'dash' });
    var chartJobs = []; // funções que redesenham os gráficos (resize)
    var loadSeq = 0;    // descarta respostas antigas se houver cargas concorrentes

    function title() {
      return el('h2', { class: 'panel-title' }, icon('trendingUp'), 'Dashboard Gerencial');
    }

    function renderSkeleton() {
      FG.clear(root);
      root.appendChild(el('div', { class: 'dash-head' }, title(),
        el('button', { class: 'btn btn-ghost btn-icon', disabled: true }, icon('refresh', '', 'spin'))));
      var kpis = el('div', { class: 'kpi-grid' }, [1, 2, 3, 4].map(function () { return el('div', { class: 'skeleton', style: { height: '6rem' } }); }));
      var charts = el('div', { class: 'chart-grid' }, [1, 2, 3, 4].map(function () { return el('div', { class: 'skeleton', style: { height: '18rem' } }); }));
      root.appendChild(kpis);
      root.appendChild(charts);
    }

    function renderError(message) {
      FG.clear(root);
      root.appendChild(el('div', { class: 'dash-head' }, title()));
      root.appendChild(el('div', { class: 'center-fill' },
        el('div', { class: 'error-box' },
          icon('alertTriangle', 'lg'), el('p', null, message),
          el('button', { class: 'btn btn-primary', onclick: load }, 'Tentar novamente'))));
    }

    function kpiCard(label, value, variant, iconName) {
      return el('div', { class: 'card card-hover' },
        el('div', { class: 'kpi' },
          el('div', null,
            el('p', { class: 'kpi-label' }, label),
            el('p', { class: 'kpi-value' }, String(value))),
          el('div', { class: 'kpi-icon ' + variant }, icon(iconName, 'md'))));
    }

    function chartCard(titleText) {
      var box = el('div', { class: 'chart-box' });
      return { box: box, card: el('div', { class: 'card card-hover' }, el('h3', null, titleText), box) };
    }

    function renderData(m) {
      FG.clear(root);
      chartJobs = [];

      var categoria = toSeries(m.por_categoria, PALETTE.categoria);
      var produto = toSeries(m.por_produto, PALETTE.produto);
      var sentimento = toSeries(m.por_sentimento, null, SENTIMENTO_COLORS);
      var urgencia = toSeries(m.por_urgencia, null, URGENCIA_COLORS).sort(function (a, b) {
        var ia = URGENCIA_ORDER.indexOf(a.name), ib = URGENCIA_ORDER.indexOf(b.name);
        return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
      });

      root.appendChild(el('div', { class: 'dash-head' }, title(),
        el('button', { class: 'btn btn-ghost btn-icon', title: 'Atualizar', onclick: load }, icon('refresh'))));

      root.appendChild(el('div', { class: 'kpi-grid' },
        kpiCard('Total de Reclamações', m.total, 'blue', 'users'),
        kpiCard('Categorias Únicas', Object.keys(m.por_categoria || {}).length, 'purple', 'trendingUp'),
        kpiCard('Fraude/Segurança', (m.por_categoria || {})['Fraude/Segurança'] || 0, 'red', 'alertTriangle'),
        kpiCard('Urgência Crítica', (m.por_urgencia || {})['Crítica'] || 0, 'orange', 'clock')));

      var c1 = chartCard('Por Categoria'), c2 = chartCard('Por Produto'),
          c3 = chartCard('Por Sentimento'), c4 = chartCard('Por Urgência');
      root.appendChild(el('div', { class: 'chart-grid' }, c1.card, c2.card, c3.card, c4.card));

      root.appendChild(el('div', { class: 'card legend-card' },
        el('h3', null, icon('alertTriangle', 'sm', 'text-warning'), 'Legenda de Urgência'),
        el('div', { class: 'legend-items' },
          ['Crítica', 'Alta', 'Média', 'Baixa'].map(function (n) {
            return el('span', { class: 'legend-item' },
              el('span', { class: 'dot', style: { backgroundColor: URGENCIA_COLORS[n] } }), n);
          }))));

      // Gráficos precisam do container no DOM para medir a largura
      chartJobs = [
        function () { FG.charts.donut(c1.box, categoria); },
        function () { FG.charts.barsHorizontal(c2.box, produto); },
        function () { FG.charts.donut(c3.box, sentimento); },
        function () { FG.charts.barsVertical(c4.box, urgencia); }
      ];
      drawCharts();
    }

    function drawCharts() { chartJobs.forEach(function (job) { job(); }); }

    function load() {
      var seq = ++loadSeq;
      renderSkeleton();
      FG.api.obterMetricas().then(function (m) {
        if (seq === loadSeq) renderData(m);
      }).catch(function (err) {
        console.error('Erro ao carregar métricas:', err);
        if (seq === loadSeq) renderError('Falha ao carregar dados do dashboard');
      });
    }

    // Redesenha ao redimensionar a janela ou ao trocar de tema (cores vêm de CSS vars)
    var resizeTimer = null;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () { if (root.offsetParent) drawCharts(); }, 150);
    });

    return { element: root, load: load, redraw: drawCharts };
  }

  FG.createDashboard = createDashboard;
})();
