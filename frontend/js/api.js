/* Cliente da API FinGuard (fetch nativo). */
(function () {
  // Servido pelo próprio backend (porta 8000) -> caminho relativo.
  // Aberto via file:// ou outro servidor estático -> aponta para o backend local.
  var sameOrigin = location.protocol.indexOf('http') === 0 && location.port === '8000';
  var API_BASE_URL = sameOrigin ? '/api' : 'http://localhost:8000/api';

  function errorFromResponse(res) {
    return res.text().then(function (body) {
      var msg = 'Erro ' + res.status;
      try {
        var json = JSON.parse(body);
        if (typeof json.detail === 'string') msg = json.detail;
      } catch (e) { /* corpo não-JSON */ }
      throw new Error(msg);
    });
  }

  function request(path, options) {
    return fetch(API_BASE_URL + path, options).then(function (res) {
      if (!res.ok) return errorFromResponse(res);
      return res;
    });
  }

  function json(path, options) {
    return request(path, options).then(function (res) { return res.json(); });
  }

  var api = {
    classificarReclamacao: function (texto) {
      return json('/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: texto })
      });
    },
    uploadCSV: function (file) {
      var form = new FormData();
      form.append('file', file); // o navegador define o boundary do multipart
      return json('/upload-csv', { method: 'POST', body: form });
    },
    registrarEventoSeguranca: function (type, detail) {
      // Fire-and-forget: falha no log nunca deve afetar o usuário
      fetch(API_BASE_URL + '/security/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: type, detail: detail })
      }).catch(function () {});
    },
    listarReclamacoes: function () { return json('/tickets'); },
    obterMetricas: function () { return json('/metrics'); },
    exportarDados: function (format) {
      return request('/export?format=' + encodeURIComponent(format)).then(function (res) { return res.blob(); });
    },
    limparReclamacoes: function () { return json('/tickets', { method: 'DELETE' }); }
  };

  window.FG = window.FG || {};
  window.FG.api = api;
})();
