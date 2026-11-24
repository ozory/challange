/* Cabeçalho: importar CSV, exportar, atualizar, limpar e alternar tema. */
(function () {
  var el = FG.el, icon = FG.icon, api = FG.api;

  /** onRefresh: chamado após upload, limpeza ou clique em atualizar. */
  function createHeader(onRefresh) {
    var uploading = false, exporting = false, clearing = false;

    var fileInput = el('input', { type: 'file', accept: '.csv', class: 'sr-only', onchange: handleFileUpload });
    var uploadLabel = el('span', null, 'Importar CSV');
    var uploadBtn = el('button', { type: 'button', class: 'btn btn-primary', onclick: function () { fileInput.click(); } },
      icon('upload', 'sm'), uploadLabel);

    var exportBtns = ['json', 'csv', 'html'].map(function (fmt) {
      return el('button', { class: 'btn btn-secondary', onclick: function () { handleExport(fmt); } },
        icon('download', 'sm'), fmt.toUpperCase());
    });

    var clearBtn = el('button', { class: 'btn btn-ghost btn-icon danger', title: 'Limpar todos os dados', onclick: handleClear }, icon('trash'));
    var refreshBtn = el('button', { class: 'btn btn-ghost btn-icon', title: 'Atualizar dados', onclick: handleRefresh }, icon('refresh'));

    // Tema
    var themeBtn = el('button', { class: 'btn btn-ghost btn-icon', onclick: FG.theme.toggle });
    function renderTheme() {
      var dark = FG.theme.isDark();
      FG.clear(themeBtn);
      themeBtn.appendChild(icon(dark ? 'moon' : 'sun', '', null));
      themeBtn.firstChild.style.color = dark ? '#facc15' : '#fb923c';
      themeBtn.title = dark ? 'Tema escuro' : 'Tema claro';
      themeBtn.setAttribute('aria-label', dark ? 'Alternar para tema claro' : 'Alternar para tema escuro');
    }
    renderTheme();
    FG.theme.onChange(renderTheme);

    function setBusy() {
      fileInput.disabled = uploading;
      uploadBtn.disabled = uploading;
      uploadLabel.textContent = uploading ? 'Processando...' : 'Importar CSV';
      exportBtns.forEach(function (b) { b.disabled = exporting; });
      clearBtn.disabled = clearing;
    }

    function handleFileUpload() {
      var file = fileInput.files[0];
      if (!file) return;
      var check = FG.security.validateFile(file);
      if (!check.ok) { alert(check.error); fileInput.value = ''; return; }
      uploading = true; setBusy();
      api.uploadCSV(file).then(function (result) {
        if (result.success) {
          alert('Processamento concluído: ' + result.processados + ' processados, ' + result.erros + ' erros');
          onRefresh();
        } else {
          alert('Erro no processamento do CSV');
        }
      }).catch(function (err) {
        console.error('Erro no upload:', err);
        alert(err && err.message ? err.message : 'Erro ao fazer upload do arquivo');
      }).then(function () {
        uploading = false; setBusy();
        fileInput.value = '';
      });
    }

    function handleExport(format) {
      exporting = true; setBusy();
      api.exportarDados(format).then(function (blob) {
        FG.downloadBlob(blob, 'reclamacoes.' + format);
      }).catch(function (err) {
        console.error('Erro na exportação:', err);
        alert('Erro ao exportar dados');
      }).then(function () { exporting = false; setBusy(); });
    }

    function handleClear() {
      if (!window.confirm('Tem certeza que deseja remover TODAS as reclamações? Esta ação não pode ser desfeita.')) return;
      clearing = true; setBusy();
      api.limparReclamacoes().then(function () {
        alert('Todas as reclamações foram removidas');
        onRefresh();
      }).catch(function (err) {
        console.error('Erro ao limpar:', err);
        alert('Erro ao limpar dados');
      }).then(function () { clearing = false; setBusy(); });
    }

    function handleRefresh() {
      api.obterMetricas().then(onRefresh).catch(function (err) { console.error('Erro ao atualizar:', err); });
    }

    return el('header', { class: 'header' },
      el('div', { class: 'header-inner' },
        el('div', { class: 'brand' },
          el('div', { class: 'brand-logo' }, icon('shield', 'md')),
          el('div', null,
            el('h1', { class: 'gradient-text' }, 'FinGuard'),
            el('p', null, 'Triagem Inteligente de Reclamações'))),
        el('div', { class: 'header-actions' },
          fileInput, uploadBtn,
          el('div', { class: 'export-group' }, exportBtns),
          refreshBtn, //clearBtn,
          el('div', { class: 'divider-v' }),
          themeBtn)));
  }

  FG.createHeader = createHeader;
})();
