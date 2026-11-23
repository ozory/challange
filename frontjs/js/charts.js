/* Gráficos SVG feitos à mão (donut, barras horizontais e verticais). */
(function () {
  var el = FG.el, svg = FG.svg;

  /* ---------- Tooltip compartilhado ---------- */
  var tip = null;
  function getTip() {
    if (!tip) {
      tip = el('div', { class: 'chart-tooltip' });
      document.body.appendChild(tip);
    }
    return tip;
  }
  function showTip(evt, text) {
    var t = getTip();
    t.textContent = text;
    t.classList.add('visible');
    var x = Math.min(evt.clientX + 14, window.innerWidth - t.offsetWidth - 8);
    t.style.left = x + 'px';
    t.style.top = (evt.clientY + 14) + 'px';
  }
  function hideTip() { if (tip) tip.classList.remove('visible'); }

  function bindTip(node, label, value) {
    var text = label + ': ' + value + ' reclamações';
    node.addEventListener('mousemove', function (e) { showTip(e, text); });
    node.addEventListener('mouseleave', hideTip);
  }

  function polar(cx, cy, r, angle) {
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
  }

  function emptyMessage(w, h) {
    return svg('text', { x: w / 2, y: h / 2, 'text-anchor': 'middle', fill: 'var(--color-text-muted)', 'font-size': 13 }, 'Sem dados');
  }

  /**
   * Donut. data: [{name, value, color}] ; container: elemento já no DOM.
   * Legenda em HTML abaixo do anel, com percentuais.
   */
  function donut(container, data) {
    FG.clear(container);
    var items = data.filter(function (d) { return d.value > 0; });
    var total = items.reduce(function (s, d) { return s + d.value; }, 0);
    var w = container.clientWidth || 300;
    var h = Math.max(150, (container.clientHeight || 288) - 54);
    var cx = w / 2, cy = h / 2;
    var outer = Math.min(w, h) / 2 - 6, inner = outer * 0.7;
    var r = (outer + inner) / 2, thick = outer - inner;

    var s = svg('svg', { class: 'chart-svg', width: w, height: h, viewBox: '0 0 ' + w + ' ' + h });
    if (!total) {
      s.appendChild(emptyMessage(w, h));
    } else if (items.length === 1) {
      var c = svg('circle', { class: 'slice', cx: cx, cy: cy, r: r, fill: 'none', stroke: items[0].color, 'stroke-width': thick });
      bindTip(c, items[0].name, items[0].value);
      s.appendChild(c);
    } else {
      var gap = 3 * Math.PI / 180; // paddingAngle
      var angle = -Math.PI / 2;
      items.forEach(function (d) {
        var sweep = (d.value / total) * 2 * Math.PI;
        var a0 = angle + gap / 2, a1 = angle + sweep - gap / 2;
        angle += sweep;
        if (a1 <= a0) return;
        var p0 = polar(cx, cy, r, a0), p1 = polar(cx, cy, r, a1);
        var large = (a1 - a0) > Math.PI ? 1 : 0;
        var path = svg('path', {
          class: 'slice',
          d: 'M ' + p0[0] + ' ' + p0[1] + ' A ' + r + ' ' + r + ' 0 ' + large + ' 1 ' + p1[0] + ' ' + p1[1],
          fill: 'none', stroke: d.color, 'stroke-width': thick
        });
        bindTip(path, d.name, d.value);
        s.appendChild(path);
      });
    }
    // Total no centro
    s.appendChild(svg('text', { x: cx, y: cy - 2, 'text-anchor': 'middle', 'font-size': 26, 'font-weight': 700, fill: 'var(--color-text-primary)' }, String(total)));
    s.appendChild(svg('text', { x: cx, y: cy + 16, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--color-text-muted)' }, 'total'));
    container.appendChild(s);

    container.appendChild(el('div', { class: 'chart-legend' },
      items.map(function (d) {
        var pct = total ? (d.value / total * 100).toFixed(1) : '0.0';
        return el('span', null, el('span', { class: 'dot', style: { backgroundColor: d.color } }), d.name + ' ' + pct + '%');
      })
    ));
  }

  /** Escala "bonita" para o eixo numérico: devolve {max, step}. */
  function niceScale(maxVal) {
    if (maxVal <= 0) return { max: 1, step: 1 };
    var rough = maxVal / 4;
    var mag = Math.pow(10, Math.floor(Math.log10(rough)));
    var norm = rough / mag;
    var step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * mag;
    return { max: Math.ceil(maxVal / step) * step, step: step };
  }

  /** Barras horizontais (categorias no eixo Y). */
  function barsHorizontal(container, data) {
    FG.clear(container);
    var w = container.clientWidth || 300, h = container.clientHeight || 288;
    var m = { l: 150, r: 20, t: 10, b: 28 };
    var pw = Math.max(40, w - m.l - m.r), ph = h - m.t - m.b;
    var scale = niceScale(Math.max.apply(null, data.map(function (d) { return d.value; }).concat([0])));
    var s = svg('svg', { class: 'chart-svg', width: w, height: h, viewBox: '0 0 ' + w + ' ' + h });
    if (!data.length) s.appendChild(emptyMessage(w, h));

    for (var v = 0; v <= scale.max + 1e-9; v += scale.step) { // grade vertical + rótulos X
      var x = m.l + (v / scale.max) * pw;
      s.appendChild(svg('line', { x1: x, x2: x, y1: m.t, y2: m.t + ph, stroke: 'var(--color-border-primary)', 'stroke-dasharray': '3 3' }));
      s.appendChild(svg('text', { x: x, y: h - 8, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--color-text-muted)' }, String(v)));
    }
    var band = ph / Math.max(data.length, 1), barH = Math.min(36, band * 0.7);
    data.forEach(function (d, i) {
      var y = m.t + i * band + (band - barH) / 2, bw = (d.value / scale.max) * pw;
      s.appendChild(svg('text', { x: m.l - 10, y: y + barH / 2 + 4, 'text-anchor': 'end', 'font-size': 12, fill: 'var(--color-text-secondary)' }, d.name));
      if (bw > 0) {
        var rr = Math.min(6, bw, barH / 2);
        var bar = svg('path', {
          class: 'bar', fill: d.color,
          d: 'M ' + m.l + ' ' + y + ' H ' + (m.l + bw - rr) + ' Q ' + (m.l + bw) + ' ' + y + ' ' + (m.l + bw) + ' ' + (y + rr) +
             ' V ' + (y + barH - rr) + ' Q ' + (m.l + bw) + ' ' + (y + barH) + ' ' + (m.l + bw - rr) + ' ' + (y + barH) + ' H ' + m.l + ' Z'
        });
        bindTip(bar, d.name, d.value);
        s.appendChild(bar);
      }
    });
    container.appendChild(s);
  }

  /** Barras verticais (categorias no eixo X). */
  function barsVertical(container, data) {
    FG.clear(container);
    var w = container.clientWidth || 300, h = container.clientHeight || 288;
    var m = { l: 40, r: 20, t: 10, b: 30 };
    var pw = Math.max(40, w - m.l - m.r), ph = h - m.t - m.b;
    var scale = niceScale(Math.max.apply(null, data.map(function (d) { return d.value; }).concat([0])));
    var s = svg('svg', { class: 'chart-svg', width: w, height: h, viewBox: '0 0 ' + w + ' ' + h });
    if (!data.length) s.appendChild(emptyMessage(w, h));

    for (var v = 0; v <= scale.max + 1e-9; v += scale.step) { // grade horizontal + rótulos Y
      var y = m.t + ph - (v / scale.max) * ph;
      s.appendChild(svg('line', { x1: m.l, x2: m.l + pw, y1: y, y2: y, stroke: 'var(--color-border-primary)', 'stroke-dasharray': '3 3' }));
      s.appendChild(svg('text', { x: m.l - 8, y: y + 4, 'text-anchor': 'end', 'font-size': 11, fill: 'var(--color-text-muted)' }, String(v)));
    }
    var band = pw / Math.max(data.length, 1), barW = Math.min(48, band * 0.7);
    data.forEach(function (d, i) {
      var x = m.l + i * band + (band - barW) / 2, bh = (d.value / scale.max) * ph, y0 = m.t + ph;
      s.appendChild(svg('text', { x: x + barW / 2, y: h - 8, 'text-anchor': 'middle', 'font-size': 12, fill: 'var(--color-text-muted)' }, d.name));
      if (bh > 0) {
        var rr = Math.min(6, barW / 2, bh);
        var bar = svg('path', {
          class: 'bar', fill: d.color,
          d: 'M ' + x + ' ' + y0 + ' V ' + (y0 - bh + rr) + ' Q ' + x + ' ' + (y0 - bh) + ' ' + (x + rr) + ' ' + (y0 - bh) +
             ' H ' + (x + barW - rr) + ' Q ' + (x + barW) + ' ' + (y0 - bh) + ' ' + (x + barW) + ' ' + (y0 - bh + rr) + ' V ' + y0 + ' Z'
        });
        bindTip(bar, d.name, d.value);
        s.appendChild(bar);
      }
    });
    container.appendChild(s);
  }

  FG.charts = { donut: donut, barsHorizontal: barsHorizontal, barsVertical: barsVertical, hideTip: hideTip };
})();
