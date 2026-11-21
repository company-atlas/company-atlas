// 기업 페이지: 주소의 ?id= 값으로 기업을 찾아 모든 블록을 그려요

document.addEventListener('DOMContentLoaded', function () {
  var e = Atlas.esc;
  var root = document.getElementById('company');
  var c = Atlas.find(Atlas.param('id'));

  if (!c) {
    root.innerHTML = '<div class="empty">찾는 기업이 없어요. <a href="index.html" style="color: #1D4ED8">홈으로 돌아가기</a></div>';
    return;
  }
  document.title = c.name + ' · Company Atlas';

  var isUsd = c.currency === 'USD';
  var fx = window.ATLAS_META.fx;
  var COLORS = ['var(--s1)', 'var(--s2)', 'var(--s3)', 'var(--s4)', 'var(--s5)', 'var(--s6)'];
  var SERIES = [['매출', 'var(--s1)'], ['영업이익', 'var(--s2)'], ['순이익', 'var(--s3)']];

  // ---------- 머리말 ----------
  var html = '';
  html += '<div class="crumb"><a href="index.html">홈</a> &gt; <a href="search.html?country=' + encodeURIComponent(c.country) + '">' + e(c.country) +
    '</a> &gt; <a href="search.html?industry=' + encodeURIComponent(c.industry) + '">' + e(c.industry) + '</a> &gt; ' + e(c.name) + '</div>';
  html += '<div class="co-head"><div class="logo-box" aria-hidden="true">' + Atlas.initials(c) + '</div>' +
    '<div style="display: flex; flex-direction: column; gap: 4px"><h1>' + e(c.name) + '<span class="en">' + e(c.nameEn) + '</span></h1>' +
    '<span class="meta">' + e(c.country) + ' · ' + e(c.industry) + '</span>' +
    '<span class="tagline">' + e(c.tagline) + '</span></div></div>';

  var NAV = [['about', '소개'], ['info', '핵심 정보'], ['biz', '사업'], ['nums', '숫자'], ['perf', '실적'], ['history', '연혁'], ['rivals', '경쟁사']];
  html += '<nav class="in-nav" aria-label="페이지 안 이동">' + NAV.map(function (n) {
    return '<a href="#' + n[0] + '">' + n[1] + '</a>';
  }).join('') + '</nav>';

  html += '<div class="co-body">';

  // ---------- 이 기업은? ----------
  html += '<section class="sec" id="about"><h2>이 기업은?</h2><p class="about">' + e(c.about) + '</p></section>';

  // ---------- 핵심 정보 ----------
  html += '<section class="sec" id="info"><h2>핵심 정보</h2><div class="cards info">' +
    c.info.map(function (row) {
      return '<div class="cell"><div class="lbl">' + e(row[0]) + '</div><div class="val">' + e(row[1]) + '</div></div>';
    }).join('') +
    '<div class="cell"><div class="lbl">공식 웹사이트</div><div class="val"><a href="' + e(c.website) + '" target="_blank" rel="noopener" style="color: var(--accent)">' +
    e(c.website.replace(/^https?:\/\/(www\.)?/, '')) + '</a></div></div></div></section>';

  // ---------- 무엇을 하는 기업인가요? ----------
  html += '<section class="sec" id="biz"><h2>무엇을 하는 기업인가요?</h2><div class="cards">' +
    c.businesses.map(function (b) {
      return '<div class="card"><strong>' + e(b[0]) + '</strong><span class="lbl">' + e(b[1]) + '</span></div>';
    }).join('') + '</div></section>';

  // ---------- 숫자로 보기 ----------
  html += '<section class="sec" id="nums"><h2>숫자로 보기</h2>';
  if (isUsd) {
    html += '<p class="note">원화 금액은 1달러 = ' + Atlas.num(fx.usdKrw, 1) + '원(' + e(fx.asOf) + ')으로 환산한 대략적인 값이에요.</p>';
  }
  html += '<div class="cards nums">' + c.highlights.map(function (h) {
    var big = (h.approx ? '약 ' : '') + Atlas.num(h.value, h.value % 1 ? 1 : 0) + h.unit;
    var krwLine = '';
    var note = h.note;
    if (isUsd) {
      var krw = Atlas.toKrwTrillion(h.value, h.unit);
      krwLine = '<div class="krw">≈ 약 ' + Atlas.num(krw, 0) + '조 원</div>';
      if (h.compareTo) {
        var other = Atlas.find(h.compareTo);
        var otherCap = other && other.highlights.filter(function (x) { return x.label === '시가총액'; })[0];
        if (otherCap) note += ' · ' + other.name + '의 약 ' + Math.round(krw / otherCap.value) + '배';
      }
    }
    return '<div class="cell"><div class="big">' + e(big) + '</div>' + krwLine +
      '<div class="lbl" style="margin-top: 4px">' + e(h.label) + ' · ' + e(note) + '</div></div>';
  }).join('') + '</div></section>';

  // ---------- 어디서 돈을 버나요? ----------
  var total = c.share.items.reduce(function (s, it) { return s + it[1]; }, 0);
  var pcts = c.share.items.map(function (it) { return Math.round(it[1] / total * 1000) / 10; });
  var drift = Math.round((100 - pcts.reduce(function (a, b) { return a + b; }, 0)) * 10) / 10;
  pcts[0] = Math.round((pcts[0] + drift) * 10) / 10;
  html += '<section class="sec" id="share"><h2>어디서 돈을 버나요?</h2>' +
    '<div class="share-bar" role="img" aria-label="' + e(c.share.title) + '">' +
    c.share.items.map(function (it, i) {
      return '<div style="width: ' + pcts[i] + '%; background: ' + COLORS[i % COLORS.length] + '"></div>';
    }).join('') + '</div><div class="share-legend">' +
    c.share.items.map(function (it, i) {
      return '<div><span class="sw" style="background: ' + COLORS[i % COLORS.length] + '"></span><span class="n">' + e(it[0]) +
        '</span><strong>' + pcts[i].toFixed(1) + '%</strong></div>';
    }).join('') + '</div><p class="note">' + e(c.share.note) + '</p></section>';

  // ---------- 실적 흐름 (그래프 자리) ----------
  html += '<section class="sec" id="perf"><h2>실적 흐름</h2>' +
    '<div class="chart-controls"><div class="tabs" role="group" aria-label="기간">' +
    '<button type="button" class="tab" data-mode="annual">' + e(c.financials.annualTitle) + '</button>' +
    '<button type="button" class="tab" data-mode="quarterly">분기별 (최근 8분기)</button></div>' +
    (isUsd ? '<div class="tabs" role="group" aria-label="통화"><button type="button" class="tab" data-cur="orig">달러</button>' +
      '<button type="button" class="tab" data-cur="krw">원화로 보기</button></div>' : '') +
    '</div>' +
    '<div class="legend">' + SERIES.map(function (s) {
      return '<span><span class="sw" style="background: ' + s[1] + '"></span>' + s[0] + '</span>';
    }).join('') + '<span class="unit" id="unit"></span></div>' +
    '<div class="chart-scroll"><div class="chart" id="chart" role="img"></div><div class="chart-labels" id="chart-labels"></div></div>' +
    '<table class="fin-table" id="fin-table"><thead><tr><th scope="col">기간</th><th scope="col">매출</th><th scope="col">영업이익</th><th scope="col">순이익</th></tr></thead><tbody></tbody></table>' +
    '<p class="chart-note" id="chart-note"></p>' +
    (c.fiscalNote ? '<p class="note">' + e(c.fiscalNote) + '</p>' : '') +
    '</section>';

  // ---------- 걸어온 길 ----------
  html += '<section class="sec" id="history"><h2>걸어온 길</h2><div class="timeline">' +
    c.history.map(function (h) { return '<div><strong>' + e(h[0]) + '</strong><span>' + e(h[1]) + '</span></div>'; }).join('') +
    '</div></section>';

  // ---------- 경쟁사 ----------
  html += '<section class="sec" id="rivals"><h2>경쟁사</h2><p class="note" style="font-size: 15px">사업마다 겨루는 상대가 달라요</p><div class="rivals">' +
    c.rivals.map(function (r) {
      return '<div class="rival-row"><strong>' + e(r[0]) + '</strong><div class="row-wrap">' + r[1].map(function (x) {
        var inner = '<strong>' + e(x[0]) + '</strong><span class="c">' + e(x[1]) + '</span>';
        return x[2] && Atlas.find(x[2])
          ? '<a class="rival-chip linked" href="company.html?id=' + encodeURIComponent(x[2]) + '">' + inner + '</a>'
          : '<span class="rival-chip">' + inner + '</span>';
      }).join('') + '</div></div>';
    }).join('') + '</div></section>';

  html += '<div class="sources">출처: ' + e(c.sources) + (isUsd ? ' · 환율 1달러 = ' + Atlas.num(fx.usdKrw, 1) + '원(' + e(fx.asOf) + ')' : '') +
    ' · 마지막 업데이트: ' + e(window.ATLAS_META.updated) + '</div>';
  html += '</div>';
  root.innerHTML = html;

  // ---------- 그래프 그리기 ----------
  var state = { mode: 'annual', cur: 'orig' };
  var f = c.financials;

  function rows() {
    var src = state.mode === 'annual' ? f.annual : f.quarterly;
    if (state.cur === 'krw') {
      return src.map(function (r) {
        return [r[0]].concat(r.slice(1).map(function (v) { return Atlas.toKrwTrillion(v, f.unit); }));
      });
    }
    return src;
  }
  function unitLabel() {
    return state.cur === 'krw' ? '조 원' : f.unit;
  }
  function fmt(v) {
    return unitLabel() === '억 달러' ? Atlas.num(v, 0) : Atlas.num(v, 1);
  }

  function draw() {
    var data = rows();
    var max = 0;
    data.forEach(function (r) { r.slice(1).forEach(function (v) { max = Math.max(max, v); }); });
    var mobile = window.innerWidth <= 640;
    var maxH = mobile ? 168 : 240;

    var chart = document.getElementById('chart');
    chart.setAttribute('aria-label', (state.mode === 'annual' ? f.annualTitle : '최근 8분기') + ' 매출·영업이익·순이익 막대 그래프, 단위 ' + unitLabel());
    chart.innerHTML = data.map(function (r) {
      return '<div class="group">' + r.slice(1).map(function (v, i) {
        var h = Math.max(2, Math.round(v / max * maxH));
        return '<div class="bar-col"><span>' + fmt(v) + '</span><div class="bar" style="height: ' + h + 'px; background: ' + SERIES[i][1] + '"></div></div>';
      }).join('') + '</div>';
    }).join('');
    document.getElementById('chart-labels').innerHTML = data.map(function (r) { return '<div>' + e(r[0]) + '</div>'; }).join('');
    document.querySelector('#fin-table tbody').innerHTML = data.map(function (r) {
      return '<tr><td>' + e(r[0]) + '</td><td>' + fmt(r[1]) + '</td><td>' + fmt(r[2]) + '</td><td>' + fmt(r[3]) + '</td></tr>';
    }).join('');

    // 분기별은 칸이 많아서 휴대폰에서는 옆으로 밀어 보게 해요
    var wide = state.mode === 'quarterly' && mobile;
    chart.style.minWidth = wide ? '470px' : '';
    document.getElementById('chart-labels').style.minWidth = wide ? '470px' : '';

    document.getElementById('unit').textContent = '단위: ' + unitLabel() +
      (state.cur === 'krw' ? ' (1달러 = ' + Atlas.num(fx.usdKrw, 1) + '원 환산)' : '');
    document.getElementById('chart-note').textContent = state.mode === 'annual' ? f.annualNote : f.quarterlyNote;

    root.querySelectorAll('[data-mode]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-mode') === state.mode ? 'true' : 'false');
    });
    root.querySelectorAll('[data-cur]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-cur') === state.cur ? 'true' : 'false');
    });
  }

  root.querySelectorAll('[data-mode]').forEach(function (b) {
    b.addEventListener('click', function () { state.mode = b.getAttribute('data-mode'); draw(); });
  });
  root.querySelectorAll('[data-cur]').forEach(function (b) {
    b.addEventListener('click', function () { state.cur = b.getAttribute('data-cur'); draw(); });
  });
  var lastMobile = window.innerWidth <= 640;
  window.addEventListener('resize', function () {
    var m = window.innerWidth <= 640;
    if (m !== lastMobile) { lastMobile = m; draw(); }
  });
  draw();
});
