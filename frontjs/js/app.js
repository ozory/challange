/* Montagem da aplicação: layout, abas e atualização entre painéis. */
(function () {
  var el = FG.el;

  var dashboard = FG.createDashboard();
  var table = FG.createTable();
  var activeTab = 'dashboard';

  var tabContent = el('div', { class: 'tab-content' });
  var tabButtons = {};

  function refresh() {
    (activeTab === 'dashboard' ? dashboard : table).load();
  }

  function setTab(name) {
    activeTab = name;
    Object.keys(tabButtons).forEach(function (k) {
      var on = k === name;
      tabButtons[k].classList.toggle('active', on);
      tabButtons[k].setAttribute('aria-selected', on);
    });
    FG.clear(tabContent);
    var view = name === 'dashboard' ? dashboard : table;
    tabContent.appendChild(view.element);
    view.load(); // recarrega ao entrar na aba (mesmo comportamento do front React)
  }

  function tab(name, label) {
    var b = el('button', { class: 'tab', role: 'tab', onclick: function () { setTab(name); } }, label);
    tabButtons[name] = b;
    return b;
  }

  var app = el('div', { class: 'app' },
    FG.createHeader(refresh),
    el('div', { class: 'main' },
      el('div', { class: 'chat-col' }, FG.createChat(refresh)),
      el('div', { class: 'content-col' },
        el('nav', { class: 'tabs', role: 'tablist' },
          tab('dashboard', 'Dashboard'), tab('tabela', 'Tabela de Reclamações')),
        tabContent)));

  document.getElementById('app').appendChild(app);
  setTab('dashboard');
})();
