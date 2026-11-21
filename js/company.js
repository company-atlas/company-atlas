// 기업 페이지의 실적 그래프: 기간(연도별/분기별)과 통화(달러/원화) 탭에 맞춰 막대를 그려요.
// 페이지의 나머지 내용은 scripts/build.py가 미리 만들어 둬요.

document.addEventListener('DOMContentLoaded', function () {
  var c = Atlas.find(window.ATLAS_COMPANY_ID);
  var root = document.getElementById('company');
  if (!c || !document.getElementById('chart')) return;

  var e = Atlas.esc;
  var fx = window.ATLAS_META.fx;
  var f = c.financials;
  var SERIES = ['var(--s1)', 'var(--s2)', 'var(--s3)'];
  var state = { mode: 'annual', cur: 'orig' };

  function rows() {
    var src = state.mode === 'annual' ? f.annual : f.quarterly;
    if (state.cur !== 'krw') return src;
    return src.map(function (r) {
      return [r[0]].concat(r.slice(1).map(function (v) { return Atlas.toKrwTrillion(v, f.unit); }));
    });
  }
  function unitLabel() { return state.cur === 'krw' ? '조 원' : f.unit; }
  function fmt(v) { return unitLabel() === '억 달러' ? Atlas.num(v, 0) : Atlas.num(v, 1); }

  function draw() {
    var data = rows();
    var max = 0;
    data.forEach(function (r) { r.slice(1).forEach(function (v) { max = Math.max(max, Math.abs(v)); }); });
    var mobile = window.innerWidth <= 640;
    var maxH = mobile ? 168 : 240;

    var chart = document.getElementById('chart');
    chart.setAttribute('aria-label', (state.mode === 'annual' ? f.annualTitle : '분기별') + ' 매출·영업이익·순이익 막대 그래프, 단위 ' + unitLabel());
    chart.innerHTML = data.map(function (r) {
      return '<div class="group">' + r.slice(1).map(function (v, i) {
        // 적자(마이너스)는 막대를 옅게 그리고 숫자에 빼기 표시가 남아요
        var hgt = Math.max(2, Math.round(Math.abs(v) / max * maxH));
        return '<div class="bar-col"><span>' + fmt(v) + '</span><div class="bar" style="height: ' + hgt + 'px; background: ' +
          SERIES[i] + (v < 0 ? '; opacity: 0.4' : '') + '"></div></div>';
      }).join('') + '</div>';
    }).join('');
    document.getElementById('chart-labels').innerHTML = data.map(function (r) { return '<div>' + e(r[0]) + '</div>'; }).join('');
    document.querySelector('#fin-table tbody').innerHTML = data.map(function (r) {
      return '<tr><td>' + e(r[0]) + '</td><td>' + fmt(r[1]) + '</td><td>' + fmt(r[2]) + '</td><td>' + fmt(r[3]) + '</td></tr>';
    }).join('');

    var wide = state.mode === 'quarterly' && mobile && data.length > 5;
    chart.style.minWidth = wide ? '470px' : '';
    document.getElementById('chart-labels').style.minWidth = wide ? '470px' : '';

    document.getElementById('unit').textContent = '단위: ' + unitLabel() +
      (state.cur === 'krw' ? ' (1달러 = ' + Atlas.num(fx.usdKrw, 1) + '원 환산)' : '');
    document.getElementById('chart-note').textContent = state.mode === 'annual' ? (f.annualNote || '') : (f.quarterlyNote || '');

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
