/* Aba Tabela: busca, filtros, ordenação e paginação sobre /tickets. */
(function () {
  var el = FG.el, icon = FG.icon;

  var COLUMNS = [
    { key: 'id', label: 'ID' }, { key: 'data_registro', label: 'Data' }, { key: 'canal', label: 'Canal' },
    { key: 'categoria', label: 'Categoria' }, { key: 'produto', label: 'Produto' },
    { key: 'sentimento', label: 'Sentimento' }, { key: 'urgencia', label: 'Urgência' }, { key: 'resumo', label: 'Resumo' }
  ];
  var PER_PAGE = 10;

  function formatarData(s) {
    if (!s) return 'N/A';
    var d = new Date(s);
    if (isNaN(d.getTime())) return s;
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  function createTable() {
    var all = [];
    var state = { texto: '', categoria: 'todas', produto: 'todos', sentimento: 'todos', urgencia: 'todas', campo: 'data_registro', dir: 'desc', pagina: 1 };
    var loadSeq = 0;

    var root = el('div', { class: 'tickets' });

    /* ---------- Cabeçalho com filtros (construído uma vez) ---------- */
    var searchInput = el('input', {
      type: 'text', class: 'input', placeholder: 'Buscar por ID, texto, resumo...',
      oninput: function () { state.texto = searchInput.value; state.pagina = 1; renderBody(); }
    });
    var clearSearch = el('button', { class: 'search-clear hidden', title: 'Limpar busca',
      onclick: function () { searchInput.value = ''; state.texto = ''; state.pagina = 1; renderBody(); searchInput.focus(); } }, icon('x', 'sm'));

    function makeSelect(field, allValue, allLabel) {
      var sel = el('select', { class: 'input', onchange: function () { state[field] = sel.value; state.pagina = 1; renderBody(); } });
      sel._all = { value: allValue, label: allLabel };
      return sel;
    }
    var selects = {
      categoria: makeSelect('categoria', 'todas', 'Todas Categorias'),
      produto: makeSelect('produto', 'todos', 'Todos Produtos'),
      sentimento: makeSelect('sentimento', 'todos', 'Todos Sentimentos'),
      urgencia: makeSelect('urgencia', 'todas', 'Todas Urgências')
    };

    function fillSelects() {
      Object.keys(selects).forEach(function (field) {
        var sel = selects[field];
        var values = Array.from(new Set(all.map(function (r) { return r[field]; }).filter(Boolean))).sort();
        if (state[field] !== sel._all.value && values.indexOf(state[field]) < 0) state[field] = sel._all.value;
        FG.clear(sel);
        sel.appendChild(el('option', { value: sel._all.value }, sel._all.label));
        values.forEach(function (v) { sel.appendChild(el('option', { value: v }, v)); });
        sel.value = state[field];
      });
    }

    var summary = el('div');

    function exportar(format) {
      FG.api.exportarDados(format).then(function (blob) {
        FG.downloadBlob(blob, 'reclamacoes.' + format);
      }).catch(function (err) {
        console.error('Erro na exportação:', err);
        alert('Erro ao exportar dados');
      });
    }

    var head = el('div', { class: 'tickets-head' },
      el('div', { class: 'tickets-title-row' },
        el('h2', { class: 'panel-title' }, icon('clipboard'), 'Tabela de Reclamações'),
        el('div', { class: 'tickets-actions' },
          ['json', 'csv', 'html'].map(function (f) {
            return el('button', { class: 'btn btn-secondary', onclick: function () { exportar(f); } }, icon('download', 'sm'), f.toUpperCase());
          }),
          el('button', { class: 'btn btn-ghost btn-icon', title: 'Atualizar', onclick: load }, icon('refresh')))),
      el('div', { class: 'filters' },
        el('div', { class: 'search-box' }, icon('search'), searchInput, clearSearch),
        selects.categoria, selects.produto, selects.sentimento, selects.urgencia),
      summary);

    var body = el('div', { class: 'tickets-body' });
    root.appendChild(head);
    root.appendChild(body);

    /* ---------- Lógica de filtro / ordenação ---------- */
    function filtered() {
      var q = state.texto.toLowerCase();
      return all.filter(function (r) {
        var okTexto = !q || (r.texto_original || '').toLowerCase().indexOf(q) >= 0 ||
          (r.id || '').toLowerCase().indexOf(q) >= 0 || (r.resumo || '').toLowerCase().indexOf(q) >= 0;
        return okTexto &&
          (state.categoria === 'todas' || r.categoria === state.categoria) &&
          (state.produto === 'todos' || r.produto === state.produto) &&
          (state.sentimento === 'todos' || r.sentimento === state.sentimento) &&
          (state.urgencia === 'todas' || r.urgencia === state.urgencia);
      }).sort(function (a, b) {
        var va = a[state.campo], vb = b[state.campo];
        va = va == null ? '' : va; vb = vb == null ? '' : vb;
        if (typeof va === 'string') va = va.toLowerCase();
        if (typeof vb === 'string') vb = vb.toLowerCase();
        if (va < vb) return state.dir === 'asc' ? -1 : 1;
        if (va > vb) return state.dir === 'asc' ? 1 : -1;
        return 0;
      });
    }

    function hasFilters() {
      return state.texto || state.categoria !== 'todas' || state.produto !== 'todos' ||
        state.sentimento !== 'todos' || state.urgencia !== 'todas';
    }

    function clearFilters() {
      state.texto = ''; state.categoria = 'todas'; state.produto = 'todos';
      state.sentimento = 'todos'; state.urgencia = 'todas'; state.pagina = 1;
      searchInput.value = '';
      Object.keys(selects).forEach(function (f) { selects[f].value = state[f]; });
      renderBody();
    }

    function sortBy(campo) {
      state.dir = state.campo === campo && state.dir === 'asc' ? 'desc' : 'asc';
      state.campo = campo;
      renderBody();
    }

    /* ---------- Renderização ---------- */
    function renderRow(r, i) {
      var fraude = r.categoria === 'Fraude/Segurança';
      return el('tr', { class: fraude ? 'fraud' : null },
        el('td', { class: 'id mono' }, r.id),
        el('td', null, formatarData(r.data_registro)),
        el('td', null, r.canal || 'N/A'),
        el('td', null, el('span', { class: fraude ? 'badge badge-danger' : 'badge badge-primary' },
          fraude ? icon('alertTriangle', 'xs') : null, r.categoria)),
        el('td', null, r.produto),
        el('td', null, el('span', { class: FG.sentimentoBadge(r.sentimento) }, r.sentimento)),
        el('td', null, el('span', { class: FG.urgenciaBadge(r.urgencia) }, r.urgencia)),
        el('td', { class: 'resumo', title: r.resumo }, r.resumo));
    }

    function renderBody() {
      var list = filtered();
      var totalPaginas = Math.ceil(list.length / PER_PAGE);
      if (state.pagina > totalPaginas) state.pagina = Math.max(1, totalPaginas);
      var pagina = list.slice((state.pagina - 1) * PER_PAGE, state.pagina * PER_PAGE);

      clearSearch.classList.toggle('hidden', !state.texto);

      // Resumo + "Limpar filtros"
      FG.clear(summary);
      var active = hasFilters();
      summary.className = 'filter-summary' + (active ? ' active' : '');
      summary.appendChild(el('p', { class: 'text-sm text-muted' }, list.length + ' de ' + all.length + ' reclamações'));
      if (active) {
        summary.appendChild(el('button', { class: 'btn btn-ghost btn-sm', onclick: clearFilters }, icon('filter', 'sm'), 'Limpar filtros'));
      }

      FG.clear(body);
      if (!list.length) {
        body.appendChild(el('div', { class: 'center-fill' },
          el('div', { class: 'empty-state' }, icon('fileText', 'xl'),
            el('p', null, 'Nenhuma reclamação encontrada com os filtros atuais'))));
        return;
      }

      var headRow = el('tr', null, COLUMNS.map(function (col) {
        var arrow = state.campo === col.key ? icon(state.dir === 'asc' ? 'chevronUp' : 'chevronDown') : null;
        return el('th', { onclick: function () { sortBy(col.key); } }, el('div', { class: 'th-inner' }, col.label, arrow));
      }));
      body.appendChild(el('div', { class: 'table-wrap' },
        el('table', { class: 'table' }, el('thead', null, headRow), el('tbody', null, pagina.map(renderRow)))));

      if (totalPaginas > 1) {
        var prev = el('button', { class: 'btn btn-secondary btn-sm', disabled: state.pagina === 1,
          onclick: function () { state.pagina--; renderBody(); } }, icon('chevronUp', 'sm', null), 'Anterior');
        var next = el('button', { class: 'btn btn-secondary btn-sm', disabled: state.pagina === totalPaginas,
          onclick: function () { state.pagina++; renderBody(); } }, 'Próxima', icon('chevronDown', 'sm'));
        prev.firstChild.style.transform = 'rotate(-90deg)';
        next.lastChild.style.transform = 'rotate(-90deg)';
        body.appendChild(el('div', { class: 'pagination' },
          el('p', { class: 'text-sm text-muted' }, 'Página ' + state.pagina + ' de ' + totalPaginas),
          el('div', { class: 'pagination-btns' }, prev, next)));
      }
    }

    function renderLoading() {
      FG.clear(body);
      body.appendChild(el('div', { class: 'center-fill' },
        el('div', { style: { width: '100%', maxWidth: '56rem', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' } },
          [1, 2, 3, 4, 5].map(function () { return el('div', { class: 'skeleton', style: { height: '3rem' } }); }))));
    }

    function renderError(msg) {
      FG.clear(body);
      body.appendChild(el('div', { class: 'center-fill' },
        el('div', { class: 'error-box' }, icon('alertTriangle', 'lg'), el('p', null, msg),
          el('button', { class: 'btn btn-primary', onclick: load }, 'Tentar novamente'))));
    }

    function load() {
      var seq = ++loadSeq;
      renderLoading();
      FG.api.listarReclamacoes().then(function (data) {
        if (seq !== loadSeq) return;
        all = data;
        state.pagina = 1;
        fillSelects();
        renderBody();
      }).catch(function (err) {
        console.error('Erro ao carregar reclamações:', err);
        if (seq === loadSeq) renderError('Falha ao carregar reclamações');
      });
    }

    return { element: root, load: load };
  }

  FG.createTable = createTable;
})();
