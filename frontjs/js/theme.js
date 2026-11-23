/* Tema claro/escuro, persistido em localStorage. */
(function () {
  var listeners = [];

  function current() {
    return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
  }

  function set(theme) {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('theme', theme);
    listeners.forEach(function (fn) { fn(theme); });
  }

  window.FG = window.FG || {};
  window.FG.theme = {
    current: current,
    isDark: function () { return current() === 'dark'; },
    toggle: function () { set(current() === 'light' ? 'dark' : 'light'); },
    onChange: function (fn) { listeners.push(fn); }
  };
})();
