/* Motor da apresentação: navegação, fragments, escala 16:9, notas, visão geral e cronômetro. */
(function () {
  var stage = document.getElementById('stage');
  var slides = [].slice.call(document.querySelectorAll('.slide'));
  var progress = document.getElementById('progress');
  var counter = document.getElementById('counter');
  var notes = document.getElementById('notes');
  var overview = document.getElementById('overview');
  var timerEl = document.getElementById('timer');
  var cur = 0, step = 0;

  function frags(i) { return [].slice.call(slides[i].querySelectorAll('[data-step]')); }
  function maxStep(i) {
    return frags(i).reduce(function (m, f) { return Math.max(m, +f.dataset.step); }, 0);
  }

  function render(enter) {
    slides.forEach(function (s, i) {
      s.classList.toggle('active', i === cur);
      s.classList.toggle('past', i < cur);
    });
    frags(cur).forEach(function (f) {
      var on = +f.dataset.step <= step;
      if (on && !f.classList.contains('in')) {
        f.classList.add('in');
        f.dispatchEvent(new CustomEvent('fragment:in', { bubbles: true }));
      } else if (!on) f.classList.remove('in');
    });
    progress.style.width = ((cur + 1) / slides.length * 100) + '%';
    counter.textContent = (cur + 1) + ' / ' + slides.length;
    var n = slides[cur].querySelector('.notes');
    notes.textContent = '';
    var b = document.createElement('b');
    b.textContent = (cur + 1) + '. ' + slides[cur].dataset.title + ': ';
    notes.appendChild(b);
    notes.appendChild(document.createTextNode(n ? n.textContent : ''));
    if (history.replaceState) history.replaceState(null, '', '#' + (cur + 1));
    if (enter) document.dispatchEvent(new CustomEvent('slide:enter', { detail: { index: cur, el: slides[cur] } }));
  }

  function go(i, s) {
    if (i < 0 || i >= slides.length) return;
    var changed = i !== cur;
    if (changed) frags(cur).forEach(function (f) { f.classList.remove('in'); });
    cur = i; step = s === 'end' ? maxStep(i) : (s || 0);
    render(changed);
  }
  function next() { if (step < maxStep(cur)) { step++; render(false); } else go(cur + 1); }
  function prev() { if (step > 0) { step--; render(false); } else go(cur - 1, 'end'); }

  function fit() {
    var k = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.transform = 'translate(-50%,-50%) scale(' + k + ')';
  }

  // Visão geral
  slides.forEach(function (s, i) {
    var b = document.createElement('button');
    var num = document.createElement('span');
    num.textContent = i + 1;
    b.appendChild(num);
    b.appendChild(document.createTextNode(s.dataset.title));
    b.onclick = function () { overview.classList.remove('show'); go(i); };
    overview.appendChild(b);
  });
  function toggleOverview() {
    overview.classList.toggle('show');
    [].forEach.call(overview.children, function (b, i) { b.classList.toggle('cur', i === cur); });
  }

  // Cronômetro (5 min)
  var t0 = null, acc = 0, tick = null;
  function drawTimer() {
    var sec = Math.floor((acc + (t0 ? Date.now() - t0 : 0)) / 1000);
    timerEl.textContent = String(Math.floor(sec / 60)).padStart(2, '0') + ':' + String(sec % 60).padStart(2, '0');
    timerEl.classList.toggle('warn', sec >= 240 && sec < 300);
    timerEl.classList.toggle('over', sec >= 300);
  }
  function toggleTimer() {
    timerEl.classList.add('show');
    if (t0) { acc += Date.now() - t0; t0 = null; clearInterval(tick); }
    else { t0 = Date.now(); tick = setInterval(drawTimer, 250); }
    drawTimer();
  }
  function resetTimer() { acc = 0; t0 = t0 ? Date.now() : null; drawTimer(); }

  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    var k = e.key;
    if (k === 'ArrowRight' || k === ' ' || k === 'PageDown' || k === 'Enter') { e.preventDefault(); next(); }
    else if (k === 'ArrowLeft' || k === 'PageUp' || k === 'Backspace') { e.preventDefault(); prev(); }
    else if (k === 'Home') go(0);
    else if (k === 'End') go(slides.length - 1, 'end');
    else if (k === 'n' || k === 'N') notes.classList.toggle('show');
    else if (k === 'o' || k === 'O' || (k === 'Escape' && overview.classList.contains('show'))) toggleOverview();
    else if (k === 'f' || k === 'F') {
      if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen();
    }
    else if (k === 't' || k === 'T') toggleTimer();
    else if (k === 'r' || k === 'R') resetTimer();
  });

  document.addEventListener('click', function (e) {
    if (e.target.closest('button, a, .overview, .notes-panel')) return;
    if (e.clientX < innerWidth * 0.25) prev(); else next();
  });

  var tx = null;
  document.addEventListener('touchstart', function (e) { tx = e.touches[0].clientX; }, { passive: true });
  document.addEventListener('touchend', function (e) {
    if (tx === null) return;
    var dx = e.changedTouches[0].clientX - tx;
    if (Math.abs(dx) > 50) { if (dx < 0) next(); else prev(); }
    tx = null;
  });

  addEventListener('resize', fit);
  setTimeout(function () { document.getElementById('hint').classList.add('hide'); }, 5000);

  fit();
  var start = parseInt(location.hash.slice(1), 10);
  cur = start >= 1 && start <= slides.length ? start - 1 : 0;
  if (/[?&]all/.test(location.search)) step = maxStep(cur); // modo de revisão: mostra todos os fragments
  render(true);
})();
