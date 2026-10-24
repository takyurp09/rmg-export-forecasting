/* Bangladesh garment exports dashboard. Data baked by scripts/build_site_data.py. */
(function () {
  'use strict';
  var C = { us: '#0072B2', eu: '#E69F00', off: '#D55E00', green: '#009E73', sky: '#56B4E9', muted: '#64748b', grid: '#e2e8f0', text: '#0f172a' };
  var PAL = ['#0072B2', '#E69F00', '#009E73', '#D55E00', '#56B4E9', '#CC79A7', '#F0E442', '#1f3b57', '#8c6d1f', '#4d8f7a', '#a24d2e', '#7f7f7f'];
  var D = {}, charts = {}, rendered = {};
  var mobile = function () { return window.innerWidth < 600; };

  // ---------- formatting ----------
  function bn(v, d) { return '$' + (v / 1e9).toFixed(d == null ? 2 : d) + 'bn'; }
  function pct(v, d, sign) { var s = (v * 100).toFixed(d == null ? 1 : d) + '%'; return (sign && v > 0 ? '+' : '') + s.replace('-', '−'); }
  function cls(v) { return v < 0 ? 'neg' : 'pos'; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function monthName(ym) { var m = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']; return m[+ym.slice(5, 7) - 1] + ' ' + ym.slice(0, 4); }
  function win(w) { var p = w.split(' to '); return monthName(p[0]) + ' to ' + monthName(p[1]); }

  function chart(id) {
    if (!charts[id]) charts[id] = echarts.init(document.getElementById(id), null, { renderer: 'canvas' });
    return charts[id];
  }
  var base = function () {
    return {
      textStyle: { fontFamily: 'Inter, system-ui, sans-serif', color: C.text },
      grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
      tooltip: { trigger: 'axis', confine: true },
      legend: { type: 'scroll', top: 0, left: 0, right: 0, textStyle: { color: C.muted } }
    };
  };
  // category month axis: ticks and labels only on January
  var xMonths = function (data, every) {
    var jan = function (i, v) { return v.slice(5, 7) === '01'; };
    return { type: 'category', data: data, boundaryGap: false, axisTick: { interval: jan },
      axisLabel: { color: C.muted, interval: function (i, v) { return jan(i, v) && (+v.slice(0, 4)) % (every || 1) === 0; }, formatter: function (v) { return v.slice(0, 4); } } };
  };
  var yBn = function (d) { return { type: 'value', axisLabel: { color: C.muted, formatter: function (v) { return '$' + (v / 1e9).toFixed(d == null ? 1 : d) + 'bn'; } }, splitLine: { lineStyle: { color: C.grid } } }; };

  // ---------- tabs ----------
  var tabs = Array.prototype.slice.call(document.querySelectorAll('[role="tab"]'));
  function show(tab) {
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute('aria-selected', on); t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
    });
    var key = tab.id.replace('tab-', '');
    if (!rendered[key]) { RENDER[key](); rendered[key] = true; }
    Object.keys(charts).forEach(function (k) { charts[k].resize(); });
    try { history.replaceState(null, '', '#' + key); } catch (e) {}
  }
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { show(t); });
    t.addEventListener('keydown', function (e) {
      var j = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : null;
      if (j == null) return;
      var n = tabs[(j + tabs.length) % tabs.length]; n.focus(); show(n);
    });
  });
  window.addEventListener("hashchange", function () { var t = tabFor(location.hash.slice(1)); if (t && t.getAttribute("aria-selected") !== "true") show(t); });
  var rt; window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(function () { Object.keys(charts).forEach(function (k) { charts[k].resize(); }); }, 120); });

  // ---------- Overview ----------
  function kpiCard(label, value, sub, color) {
    return '<div class="kpi" style="--kc:' + color + '"><div class="kpi-l">' + label + '</div><div class="kpi-v">' + value + '</div><div class="kpi-s">' + sub + '</div></div>';
  }
  function renderOverview() {
    var o = D.overview, u = o.kpi.US, e = o.kpi.EU;
    document.getElementById('kpis').innerHTML = [
      kpiCard('US, last 12 months', bn(u.last12), 'to ' + monthName(u.last12_end) + ' · <span class="' + cls(u.yoy) + '">' + pct(u.yoy, 1, true) + '</span> on prior 12m', C.us),
      kpiCard('EU27, last 12 months', bn(e.last12), 'to ' + monthName(e.last12_end) + ' · <span class="' + cls(e.yoy) + '">' + pct(e.yoy, 1, true) + '</span> on prior 12m', C.eu),
      kpiCard('2025 vs 2022 peak', '<span class="neg">' + pct(u.vs_peak) + '</span> <span class="pair">US</span>', 'EU27 <span class="neg">' + pct(e.vs_peak) + '</span> · US ' + bn(u.peak2022) + ' → ' + bn(u.y2025), C.off),
      kpiCard('Forecast, next 12 months', '<span class="' + cls(e.fc_change) + '">' + pct(e.fc_change, 1, true) + '</span> <span class="pair">EU</span>', 'EU27 ' + bn(e.next12) + ' · US ' + bn(u.next12) + ' (' + pct(u.fc_change, 1, true) + ')', C.green),
      kpiCard('Relative MASE', u.rel_mase.toFixed(2) + ' <span class="pair">US</span> ' + e.rel_mase.toFixed(2) + ' <span class="pair">EU</span>', 'Below 1 beats seasonal naive (' + u.model + ' US, ' + e.model + ' EU)', C.sky),
      kpiCard('Share of US apparel imports, 2025', o.share.US.share.toFixed(1) + '% <span class="pair">rank ' + o.share.US.rank + '</span>', 'Up from ' + o.share.US.s2010.toFixed(1) + '% in 2010 and ' + o.share.US.s2022.toFixed(1) + '% in 2022', C.us),
      kpiCard('Share of EU apparel imports, 2025', o.share.EU.share.toFixed(1) + '% <span class="pair">rank ' + o.share.EU.rank + '</span>', 'Down from ' + o.share.EU.s2022.toFixed(1) + '% in 2022 (' + o.share.EU.s2010.toFixed(1) + '% in 2010)', C.eu),
      kpiCard('EU 2023 fall, in euros', '<span class="neg">' + o.pv2023.value.toFixed(1).replace('-', '−') + '%</span>', 'Mostly volume: ' + o.pv2023.volume_pp.toFixed(1).replace('-', '−') + ' pp volume, ' + o.pv2023.price_pp.toFixed(1).replace('-', '−') + ' pp price', C.off)
    ].join('');
    document.getElementById('ov-note').innerHTML = 'Both markets peaked in 2022. Since 2010 US imports grew ' + u.cagr + '% a year and EU imports ' + e.cagr +
      '% a year. The EU27 took ' + o.eu_share_2023 + '% of world imports from Bangladesh in 2023.';
    var ev = function (x, name) { return { xAxis: x, label: { formatter: name, color: C.muted, fontSize: 11, position: 'insideEndTop' } }; };
    var opt = base();
    opt.tooltip.valueFormatter = function (v) { return v == null ? '–' : bn(v); };
    opt.xAxis = xMonths(o.months, 2);
    opt.yAxis = yBn(1);
    opt.dataZoom = [{ type: 'inside' }];
    opt.series = [
      { name: 'EU27', type: 'line', data: o.eu, showSymbol: false, lineStyle: { width: 2, color: C.eu }, itemStyle: { color: C.eu },
        markLine: { symbol: 'none', silent: true, lineStyle: { color: C.muted, type: 'dashed' }, data: [ev('2013-04', 'Rana Plaza')] },
        markArea: { silent: true, itemStyle: { color: 'rgba(100,116,139,.12)' }, label: { color: C.muted, fontSize: 11 },
          data: [[{ name: 'COVID-19', xAxis: '2020-03' }, { xAxis: '2020-06' }], [{ name: 'Unrest', xAxis: '2024-07' }, { xAxis: '2024-08' }]] } },
      { name: 'United States', type: 'line', data: o.us, showSymbol: false, lineStyle: { width: 2, color: C.us }, itemStyle: { color: C.us } }
    ];
    chart('c-monthly').setOption(opt);
  }

  // ---------- Products & markets ----------
  var mkt = { v: 'US' };
  function renderMix() {
    var m = D.products.markets[mkt.v];
    var opt = base();
    opt.legend = { type: 'scroll', top: 0, left: 0, right: 0, textStyle: { color: C.muted, fontSize: 11 } };
    opt.grid.top = 40;
    opt.tooltip.valueFormatter = function (v) { return bn(v); };
    opt.xAxis = { type: 'category', data: m.years, axisLabel: { color: C.muted } };
    opt.yAxis = yBn(0);
    opt.series = m.groups.map(function (g, i) { return { name: g, type: 'bar', stack: 'a', data: m.values[i], itemStyle: { color: PAL[i % PAL.length] }, emphasis: { focus: 'series' } }; });
    chart('c-mix').setOption(opt, true);

    var data = [];
    m.yoy.forEach(function (row, i) { row.forEach(function (v, j) { data.push([j, i, v]); }); });
    var h = {
      textStyle: base().textStyle,
      tooltip: { confine: true, formatter: function (p) { return esc(m.groups[p.value[1]]) + '<br>' + m.yoy_years[p.value[0]] + ': <b>' + (p.value[2] > 0 ? '+' : '') + p.value[2] + '%</b>'; } },
      grid: { left: 8, right: 8, top: 8, bottom: 56, containLabel: true },
      xAxis: { type: 'category', data: m.yoy_years.map(function (y) { return "'" + String(y).slice(2); }), axisLabel: { color: C.muted, fontSize: 10 }, splitArea: { show: false } },
      yAxis: { type: 'category', data: m.groups.map(function (g) { return mobile() && g.length > 16 ? g.slice(0, 15) + '…' : g; }), inverse: true, axisLabel: { color: C.muted, fontSize: 10 } },
      visualMap: { min: -40, max: 40, calculable: false, orient: 'horizontal', left: 'center', bottom: 0, itemHeight: 140, text: ['+40%', '−40%'], textStyle: { color: C.muted, fontSize: 11 },
        inRange: { color: ['#D55E00', '#f3c3a6', '#f8fafc', '#a9cfe8', '#0072B2'] } },
      series: [{ type: 'heatmap', data: data, label: { show: !mobile() && m.groups.length <= 2, fontSize: 10, formatter: function (p) { return Math.round(p.value[2]); } } }]
    };
    chart('c-yoy').setOption(h, true);
  }
  function marketSeg(id, state, cb) {
    var el = document.getElementById(id);
    el.innerHTML = [['US', 'United States'], ['EU', 'EU27']].map(function (o) { return '<button type="button" role="radio" data-v="' + o[0] + '" aria-checked="' + (o[0] === state.v) + '">' + o[1] + '</button>'; }).join('');
    el.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      state.v = b.dataset.v;
      Array.prototype.forEach.call(el.children, function (c) { c.setAttribute('aria-checked', c === b); });
      cb();
    });
  }
  function renderComp() {
    var c = D.competitors.markets[mkt.v];
    var o = base();
    o.legend.textStyle = { color: C.muted, fontSize: 11 };
    o.tooltip.valueFormatter = function (v) { return v == null ? '–' : v.toFixed(1) + '%'; };
    o.xAxis = { type: 'category', data: c.years, axisLabel: { color: C.muted } };
    o.yAxis = { type: 'value', axisLabel: { color: C.muted, formatter: '{value}%' }, splitLine: { lineStyle: { color: C.grid } } };
    var col = { Bangladesh: C.off, China: C.text, Vietnam: C.green, Cambodia: '#CC79A7', India: C.sky, 'Türkiye': C.eu };
    o.series = c.countries.map(function (n, i) {
      var bd = n === 'Bangladesh';
      return { name: n, type: 'line', data: c.share[i], symbol: 'none', z: bd ? 5 : 2, lineStyle: { width: bd ? 3 : 1.6 }, itemStyle: { color: col[n] || '#a3aab5' } };
    });
    chart('c-share').setOption(o, true);

    var rk = c.rank, o2 = base();
    o2.legend = { show: false }; o2.grid.top = 8; o2.grid.right = 48;
    o2.tooltip = { trigger: 'axis', confine: true, formatter: function (p) { var r = rk[p[0].dataIndex]; return esc(r[1]) + '<br><b>$' + r[2].toFixed(2) + 'bn</b> · ' + r[3].toFixed(1) + '% share'; } };
    o2.yAxis = { type: 'category', data: rk.map(function (r) { return r[0] + '. ' + r[1]; }), inverse: true, axisLabel: { color: C.muted } };
    o2.xAxis = { type: 'value', axisLabel: { color: C.muted, formatter: '${value}bn' }, splitLine: { lineStyle: { color: C.grid } } };
    o2.series = [{ type: 'bar', data: rk.map(function (r) { return { value: r[2], itemStyle: { color: r[1] === 'Bangladesh' ? C.off : (mkt.v === 'US' ? C.us : C.eu) } }; }),
      label: { show: true, position: 'right', color: C.muted, fontSize: 11, formatter: function (p) { return rk[p.dataIndex][3].toFixed(1) + '%'; } } }];
    chart('c-rank').setOption(o2, true);

    var ss = c.shift, o3 = base();
    document.getElementById('ss-hint').textContent = '$bn; the whole market changed ' + (c.market_growth > 0 ? '+' : '') + c.market_growth.toFixed(1) + '%';
    o3.tooltip = { trigger: 'axis', confine: true, formatter: function (p) { var r = ss[p[0].dataIndex]; return esc(r[0]) + '<br>Total change <b>$' + r[1].toFixed(2) + 'bn</b><br>Market size: $' + r[2].toFixed(2) + 'bn<br>Share: $' + r[3].toFixed(2) + 'bn'; } };
    o3.xAxis = { type: 'category', data: ss.map(function (r) { return r[0]; }), axisLabel: { color: C.muted, interval: 0, rotate: mobile() ? 45 : 0, fontSize: 11 } };
    o3.yAxis = { type: 'value', axisLabel: { color: C.muted, formatter: '${value}bn' }, splitLine: { lineStyle: { color: C.grid } } };
    o3.series = [
      { name: 'Market-size effect', type: 'bar', stack: 's', data: ss.map(function (r) { return r[2]; }), itemStyle: { color: C.muted } },
      { name: 'Share effect', type: 'bar', stack: 's', data: ss.map(function (r) { return { value: r[3], itemStyle: { color: r[0] === 'Bangladesh' ? C.off : C.sky } }; }), itemStyle: { color: C.sky } }
    ];
    chart('c-shift').setOption(o3, true);
  }
  function renderStrategic() {
    marketSeg('seg-mkt', mkt, function () { renderMix(); renderComp(); });
    renderComp();
    renderMix();
    var t = D.products.top10, opt = base();
    opt.legend = { show: false };
    opt.tooltip = { trigger: 'axis', confine: true, formatter: function (p) { var i = p[0].dataIndex; return esc(t.market[i]) + '<br><b>' + bn(t.value[i]) + '</b> · ' + t.share[i] + '% of world'; } };
    opt.yAxis = { type: 'category', data: t.market, inverse: true, axisLabel: { color: C.muted } };
    opt.xAxis = yBn(0);
    opt.grid.top = 8;
    opt.series = [{ type: 'bar', data: t.value.map(function (v, i) { return { value: v, itemStyle: { color: t.market[i] === 'United States' ? C.us : (['United Kingdom', 'Canada', 'Japan'].indexOf(t.market[i]) >= 0 ? C.muted : C.eu) } }; }),
      label: { show: true, position: 'right', color: C.muted, fontSize: 11, formatter: function (p) { return t.share[p.dataIndex] + '%'; } } }];
    opt.grid.right = 40;
    chart('c-top').setOption(opt);

    var hh = D.products.hhi, o2 = base();
    o2.tooltip.valueFormatter = function (v) { return Math.round(v).toLocaleString('en-US'); };
    o2.xAxis = { type: 'category', data: hh.year, axisLabel: { color: C.muted } };
    o2.yAxis = { type: 'value', name: 'HHI', nameTextStyle: { color: C.muted }, axisLabel: { color: C.muted }, splitLine: { lineStyle: { color: C.grid } } };
    o2.series = [
      { name: 'EU counted as one bloc', type: 'line', data: hh.bloc, itemStyle: { color: C.eu }, lineStyle: { width: 2 } },
      { name: 'Each country separately', type: 'line', data: hh.countries, itemStyle: { color: C.us }, lineStyle: { width: 2 } }
    ];
    chart('c-hhi').setOption(o2);
  }

  // ---------- Forecast ----------
  function renderSeries() {
    var s = D.forecast.series[+document.getElementById('f-series').value];
    document.getElementById('fc-title').textContent = s.id.replace(' | ', ': ') + ' (' + s.model + ')';
    document.getElementById('kpis-f').innerHTML = [
      kpiCard('Last 12 months', bn(s.last12), 'actual', C.muted),
      kpiCard('Next 12 months', bn(s.next12), win(s.window), s.market === 'US' ? C.us : C.eu),
      kpiCard('Change', '<span class="' + cls(s.change) + '">' + pct(s.change, 1, true) + '</span>', 'point forecast vs last 12m', C.green)
    ].join('');
    var x = s.hist_x.concat(s.fc_x), nH = s.hist_x.length, pad = function (a) { return new Array(nH).fill(null).concat(a); };
    var diff = function (hi, lo) { return hi.map(function (v, i) { return v - lo[i]; }); };
    var col = s.market === 'US' ? C.us : C.eu;
    var pointLine = new Array(nH - 1).fill(null).concat([s.hist[nH - 1]], s.point);
    var opt = base();
    opt.tooltip = { trigger: 'axis', confine: true, formatter: function (ps) {
      var i = ps[0].dataIndex, k = i - nH, out = monthName(x[i]);
      if (k < 0) return out + '<br>Actual: <b>' + bn(s.hist[i], 3) + '</b>';
      return out + '<br>Forecast: <b>' + bn(s.point[k], 3) + '</b><br>80%: ' + bn(s.lo80[k], 3) + ' to ' + bn(s.hi80[k], 3) + '<br>95%: ' + bn(s.lo95[k], 3) + ' to ' + bn(s.hi95[k], 3);
    } };
    opt.legend.data = ['Actual', 'Forecast', '80% interval', '95% interval'];
    opt.xAxis = xMonths(x);
    var mx = Math.max.apply(null, s.hi95.concat(s.hist));
    opt.yAxis = yBn(mx < 3e8 ? 2 : mx < 3e9 ? 1 : 0);
    opt.series = [
      { name: '95% base', type: 'line', data: pad(s.lo95), stack: 'b95', symbol: 'none', lineStyle: { opacity: 0 }, tooltip: { show: false } },
      { name: '95% interval', type: 'line', data: pad(diff(s.hi95, s.lo95)), stack: 'b95', symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: col, opacity: 0.12 }, itemStyle: { color: col, opacity: 0.3 } },
      { name: '80% base', type: 'line', data: pad(s.lo80), stack: 'b80', symbol: 'none', lineStyle: { opacity: 0 } },
      { name: '80% interval', type: 'line', data: pad(diff(s.hi80, s.lo80)), stack: 'b80', symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: col, opacity: 0.22 }, itemStyle: { color: col, opacity: 0.5 } },
      { name: 'Actual', type: 'line', data: s.hist, symbol: 'none', lineStyle: { width: 2, color: C.text }, itemStyle: { color: C.text } },
      { name: 'Forecast', type: 'line', data: pointLine, symbol: 'circle', symbolSize: 4, lineStyle: { width: 2, color: col, type: 'dashed' }, itemStyle: { color: col } }
    ];
    chart('c-fc').setOption(opt, true);
    document.querySelector('#t-bt tbody').innerHTML = s.backtest.map(function (b) {
      var on = b[0] === s.model;
      return '<tr' + (on ? ' class="chosen"' : '') + '><td>' + esc(b[0]) + (on ? '<span class="badge">in use</span>' : '') + '</td><td class="num">' + b[1].toFixed(2) +
        '</td><td class="num">' + b[2].toFixed(2) + '</td><td class="num">' + b[3].toFixed(1) + '%</td></tr>';
    }).join('');
  }
  function renderForecast() {
    var sel = document.getElementById('f-series');
    sel.innerHTML = D.forecast.series.map(function (s, i) {
      var name = s.id === 'US | Total' ? 'US total' : s.id === 'EU | Total' ? 'EU27 total' : s.market === 'EU' ? 'EU27 ' + s.id.split('| ')[1].toLowerCase() : 'US ' + s.id.split('| ')[1];
      return '<option value="' + i + '">' + esc(name) + '</option>';
    }).join('');
    sel.addEventListener('change', renderSeries);
    renderSeries();
  }

  // ---------- Scenarios (same formulas as src/scenarios.py) ----------
  var E1 = { low: 0.8, mid: 1.0, high: 1.5 };
  var E2 = { low: { Knit: 2.7, Woven: 2.7 }, mid: { Knit: 3.0, Woven: 5.02 }, high: { Knit: 7.3, Woven: 7.3 } };
  var st = { e1: 'mid', e2: 'mid' };
  function seg(id, opts, key) {
    var el = document.getElementById(id);
    el.innerHTML = opts.map(function (o) { return '<button type="button" role="radio" data-v="' + o[0] + '" aria-checked="' + (o[0] === st[key]) + '">' + o[1] + '</button>'; }).join('');
    el.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      st[key] = b.dataset.v;
      Array.prototype.forEach.call(el.children, function (c) { c.setAttribute('aria-checked', c === b); });
      compute();
    });
  }
  function compute() {
    var S = D.scenarios, shock = +document.getElementById('s-us').value / 100, duty = +document.getElementById('s-eu').value / 100;
    document.getElementById('o-us').textContent = pct(shock, 0, true);
    document.getElementById('o-eu').textContent = (duty * 100).toFixed(1) + '%';
    var usRows = S.us_groups.map(function (g) { return { name: 'US ' + g.group, base: g.base, chg: g.base * shock * g.beta * E1[st.e1] }; });
    var euRows = S.eu_chapters.map(function (c) { return { name: 'EU27 ' + c.chapter.toLowerCase(), base: c.base, chg: c.base * (Math.pow(1 + duty, -E2[st.e2][c.chapter]) - 1) }; });
    var sum = function (a, k) { return a.reduce(function (t, r) { return t + r[k]; }, 0); };
    var usL = -sum(usRows, 'chg'), usB = sum(usRows, 'base'), euL = -sum(euRows, 'chg'), euB = sum(euRows, 'base');
    document.getElementById('r-us').textContent = bn(usL);
    document.getElementById('r-us-pct').textContent = pct(usL / usB) + ' of the ' + bn(usB) + ' baseline';
    document.getElementById('r-eu').textContent = bn(euL);
    document.getElementById('r-eu-pct').textContent = pct(euL / euB) + ' of the ' + bn(euB) + ' baseline';

    var b = S.benchmark;
    var lab = function (r) {
      var s = r[0];
      if (s.indexOf('WTO') >= 0) return s.indexOf('preference') >= 0 ? 'WTO: preference markets' : 'WTO: all markets';
      var lv = s.match(/\[(\w+)\]/)[1];
      return (s.indexOf('S2b') >= 0 ? 'Repo 9.6% GSP ' : 'Repo 12% MFN ') + lv;
    };
    var rows = [['Your setting', euL / 1e9, euL / euB, C.off]].concat(b.map(function (r) { return [lab(r), r[2], r[3], r[0].indexOf('WTO') >= 0 ? C.green : C.eu]; }));
    var o = base();
    o.legend = { show: false };
    o.grid.top = 8; o.grid.right = 48;
    o.tooltip = { trigger: 'axis', confine: true, formatter: function (p) { var r = rows[p[0].dataIndex]; return esc(r[0]) + '<br><b>$' + r[1].toFixed(2) + 'bn</b> (' + pct(r[2]) + ')'; } };
    o.yAxis = { type: 'category', data: rows.map(function (r) { return r[0]; }), inverse: true, axisLabel: { color: C.muted, fontSize: 11 } };
    o.xAxis = { type: 'value', axisLabel: { color: C.muted, formatter: '${value}bn' }, splitLine: { lineStyle: { color: C.grid } } };
    o.series = [{ type: 'bar', data: rows.map(function (r) { return { value: +r[1].toFixed(3), itemStyle: { color: r[3] } }; }),
      label: { show: true, position: 'right', fontSize: 11, color: C.muted, formatter: function (p) { return '$' + p.value.toFixed(2) + 'bn'; } } }];
    chart('c-bench').setOption(o, true);

    var all = usRows.concat(euRows).sort(function (a, b) { return a.chg - b.chg; });
    var o2 = base();
    o2.legend = { show: false };
    o2.grid.top = 8; o2.grid.right = 48;
    o2.tooltip = { trigger: 'axis', confine: true, formatter: function (p) { var r = all[p[0].dataIndex]; return esc(r.name) + '<br>Loss <b>' + bn(-r.chg, 3) + '</b> of ' + bn(r.base) + ' (' + pct(-r.chg / r.base) + ')'; } };
    o2.yAxis = { type: 'category', data: all.map(function (r) { var n = r.name; return mobile() && n.length > 22 ? n.slice(0, 21) + '…' : n; }), inverse: true, axisLabel: { color: C.muted, fontSize: 10 } };
    o2.xAxis = { type: 'value', axisLabel: { color: C.muted, formatter: function (v) { return '$' + (v / 1e9).toFixed(1) + 'bn'; } }, splitLine: { lineStyle: { color: C.grid } } };
    o2.series = [{ type: 'bar', data: all.map(function (r) { return { value: Math.max(0, -r.chg), itemStyle: { color: r.name.indexOf('EU') === 0 ? C.eu : C.us } }; }) }];
    chart('c-risk').setOption(o2, true);
  }
  function renderTactical() { renderForecast(); renderScenarios(); }
  function renderScenarios() {
    var S = D.scenarios;
    document.getElementById('s1-window').textContent = 'Baseline ' + win(S.us_window);
    document.getElementById('s2-window').textContent = 'Baseline ' + win(S.eu_window);
    seg('seg-e1', [['low', 'Low 0.8'], ['mid', 'Mid 1.0'], ['high', 'High 1.5']], 'e1');
    seg('seg-e2', [['low', 'Low 2.7'], ['mid', 'Mid: knit 3.0, woven 5.02'], ['high', 'High 7.3']], 'e2');
    ['s-us', 's-eu'].forEach(function (id) { document.getElementById(id).addEventListener('input', compute); });
    document.querySelectorAll('[data-duty]').forEach(function (b) { b.addEventListener('click', function () { document.getElementById('s-eu').value = b.dataset.duty; compute(); }); });
    document.querySelector('#t-ass tbody').innerHTML = S.assumptions.map(function (a) { return '<tr><td>' + a.map(esc).join('</td><td>') + '</td></tr>'; }).join('');
    compute();
  }

  // ---------- Operational ----------
  var trk = { v: 'US' };
  function renderTrack() {
    var t = D.tracking[trk.v], o = D.overview, col = trk.v === 'US' ? C.us : C.eu;
    document.getElementById('trk-model').textContent = '$bn, ' + t.model + ' model';
    document.querySelector('#t-last tbody').innerHTML = t.last.map(function (r) {
      return '<tr><td>' + monthName(r[0]) + '</td><td class="num">' + bn(r[1], 2) + '</td><td class="num">' + bn(r[2], 2) + '</td><td class="num ' + cls(r[3]) + '">' + pct(r[3], 1, true) + '</td></tr>';
    }).join('');
    document.querySelector('#t-next tbody').innerHTML = t.next.map(function (r) {
      return '<tr><td>' + monthName(r[0]) + '</td><td class="num">' + bn(r[1], 2) + '</td><td class="num">' + bn(r[2], 2) + ' to ' + bn(r[3], 2) + '</td><td class="num">' + bn(r[4], 2) + '</td></tr>';
    }).join('');
    var act = trk.v === 'US' ? o.us : o.eu, mo = o.months;
    var end = mo.length; while (end > 0 && act[end - 1] == null) end--;
    var hx = mo.slice(end - 18, end), ha = act.slice(end - 18, end), ly = act.slice(end - 30, end - 12);
    var fx = t.next.map(function (r) { return r[0]; }), x = hx.concat(fx), nH = hx.length;
    var lyAll = ly.concat(t.next.map(function (r) { return r[4]; }));
    var pad = function (a) { return new Array(nH).fill(null).concat(a); };
    var opt = base();
    opt.legend.data = ['Actual', 'Same month last year', 'Forecast', '80% interval'];
    opt.tooltip.valueFormatter = function (v) { return v == null ? '–' : bn(v); };
    opt.xAxis = xMonths(x);
    opt.yAxis = yBn(1);
    opt.series = [
      { name: '80% base', type: 'line', data: pad(t.next.map(function (r) { return r[2]; })), stack: 'b', symbol: 'none', lineStyle: { opacity: 0 }, tooltip: { show: false } },
      { name: '80% interval', type: 'line', data: pad(t.next.map(function (r) { return r[3] - r[2]; })), stack: 'b', symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: col, opacity: 0.2 }, itemStyle: { color: col, opacity: 0.4 }, tooltip: { show: false } },
      { name: 'Actual', type: 'line', data: ha, symbol: 'circle', symbolSize: 4, lineStyle: { width: 2, color: C.text }, itemStyle: { color: C.text } },
      { name: 'Same month last year', type: 'line', data: lyAll, symbol: 'none', lineStyle: { width: 1.5, color: C.muted, type: 'dotted' }, itemStyle: { color: C.muted } },
      { name: 'Forecast', type: 'line', data: new Array(nH - 1).fill(null).concat([ha[nH - 1]], t.next.map(function (r) { return r[1]; })), symbol: 'circle', symbolSize: 4, lineStyle: { width: 2, color: col, type: 'dashed' }, itemStyle: { color: col } }
    ];
    chart('c-trk').setOption(opt, true);
  }
  function renderOperational() {
    marketSeg('seg-trk', trk, renderTrack);
    renderTrack();
    var P = D.price_volume, k = P.months.length, s0 = Math.max(0, k - 60);
    var opt = base();
    opt.tooltip.valueFormatter = function (v) { return v == null ? '–' : (v > 0 ? '+' : '') + v.toFixed(1) + '%'; };
    opt.xAxis = xMonths(P.months.slice(s0));
    opt.yAxis = { type: 'value', axisLabel: { color: C.muted, formatter: '{value}%' }, splitLine: { lineStyle: { color: C.grid } } };
    opt.series = [
      { name: 'Value (EUR)', type: 'line', data: P.value_yoy.slice(s0), symbol: 'none', lineStyle: { width: 2, color: C.text }, itemStyle: { color: C.text } },
      { name: 'Volume (kg)', type: 'line', data: P.qty_yoy.slice(s0), symbol: 'none', lineStyle: { width: 1.6, color: C.eu }, itemStyle: { color: C.eu } },
      { name: 'Unit value (EUR/kg)', type: 'line', data: P.uv_yoy.slice(s0), symbol: 'none', lineStyle: { width: 1.6, color: C.green }, itemStyle: { color: C.green } }
    ];
    chart('c-pvm').setOption(opt);
    var A = P.annual, o2 = base();
    o2.tooltip.valueFormatter = function (v) { return v == null ? '–' : (v > 0 ? '+' : '') + v.toFixed(1); };
    o2.xAxis = { type: 'category', data: A.map(function (r) { return r[0].replace(' Jan-Aug', '\nJan-Aug'); }), axisLabel: { color: C.muted, fontSize: 11 } };
    o2.yAxis = { type: 'value', axisLabel: { color: C.muted }, splitLine: { lineStyle: { color: C.grid } } };
    o2.series = [
      { name: 'Price (pp)', type: 'bar', stack: 'pv', data: A.map(function (r) { return r[2]; }), itemStyle: { color: C.green } },
      { name: 'Volume (pp)', type: 'bar', stack: 'pv', data: A.map(function (r) { return r[3]; }), itemStyle: { color: C.eu } },
      { name: 'Value change (%)', type: 'line', data: A.map(function (r) { return r[1]; }), symbol: 'circle', symbolSize: 5, lineStyle: { width: 0 }, itemStyle: { color: C.text } }
    ];
    chart('c-pva').setOption(o2);
    var y23 = A.filter(function (r) { return r[0] === '2023'; })[0], ytd = A[A.length - 1];
    document.getElementById('pv-note').textContent = 'Log split, so price and volume add up to about the value change. In 2023 value fell ' + Math.abs(y23[1]).toFixed(1) + '%, ' +
      Math.abs(y23[3]).toFixed(1) + ' pp of it from volume. In ' + ytd[0] + ' value is down ' + Math.abs(ytd[1]).toFixed(1) + '%, ' + Math.abs(ytd[2]).toFixed(1) + ' pp of it from price (provisional months).';
    fillStatus();
  }
  function fillStatus() {
    var st = D.status;
    if (st) {
      document.getElementById('st-hint').textContent = 'Last run ' + st.last_run_utc.slice(0, 16).replace('T', ' ') + ' UTC · checks ' + (st.checks_passed ? 'passed' : 'failed') + ' · latest month US ' + monthName(st.latest_month_us) + ', EU ' + monthName(st.latest_month_eu);
      document.querySelector('#t-status tbody').innerHTML = st.steps.map(function (r) { return '<tr><td>' + esc(r.step) + '</td><td>' + esc(r.path) + '</td><td>' + esc(r.status) + (r.seconds != null ? ' (' + r.seconds + ' s)' : '') + '</td></tr>'; }).join('');
    }
  }

  var RENDER = { overview: renderOverview, strategic: renderStrategic, tactical: renderTactical, operational: renderOperational };
  var ALIAS = { products: 'strategic', forecast: 'tactical', scenarios: 'tactical', tracking: 'operational' };
  function tabFor(h) { return document.getElementById('tab-' + (ALIAS[h] || h)); }

  // ---------- load ----------
  fetch('data/refresh_status.json').then(function (r) { return r.ok ? r.json() : null; }).then(function (st) {
    if (!st) return;
    D.status = st; if (rendered.operational) fillStatus();
    var t = '<strong>Data status:</strong> refreshed ' + st.last_run_utc.slice(0, 10) + ' · latest month US ' +
      st.latest_month_us + ', EU ' + st.latest_month_eu;
    if (st.sources_stale && st.sources_stale.length) t += ' · some sources unavailable, cached data used';
    document.getElementById('data-status').innerHTML = t;
  }).catch(function () {});

  Promise.all(['overview', 'products', 'forecast', 'scenarios', 'competitors', 'price_volume', 'tracking'].map(function (n) {
    return fetch('data/' + n + '.json').then(function (r) { if (!r.ok) throw new Error(n + ': ' + r.status); return r.json(); }).then(function (j) { D[n] = j; });
  })).then(function () {
    document.getElementById('loading').remove();
    document.getElementById('gen').textContent = 'Data built ' + D.overview.generated;
    var h = location.hash.slice(1), t = tabFor(h);
    show(t || tabs[0]);
  }).catch(function (err) {
    document.getElementById('loading').textContent = 'Could not load data (' + err.message + ').';
  });
})();
