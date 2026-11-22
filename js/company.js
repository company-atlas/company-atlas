// 기업 페이지의 실적 그래프: 기간(연도별/분기별)과 통화(달러/원화) 탭에 맞춰 막대를 그려요.
// 페이지의 나머지 내용은 scripts/build.py가 미리 만들어 둬요.
//  - 이익은 가운데 0 선 위로, 손실(적자)은 0 선 아래로 그려요.
//  - 기간에 마우스를 올리거나(컴퓨터) 누르면(휴대폰) 그래프 밑에 정확한 금액이 나와요.

// 무엇을 하는 기업인가요? — 칸을 누르면 자세한 설명을 열고 닫아요 (컴퓨터는 마우스만 올려도 떠요)
document.addEventListener('DOMContentLoaded', function () {
  var cards = document.querySelectorAll('.biz-card');
  function place(card) {
    // 화면 오른쪽 끝을 넘으면 설명 칸을 오른쪽에 맞춰요
    var pop = card.querySelector('.biz-pop');
    pop.classList.remove('pop-right');
    if (card.getBoundingClientRect().left + 380 > document.documentElement.clientWidth - 16) pop.classList.add('pop-right');
  }
  function setOpen(card, open) {
    card.classList.toggle('open', open);
    card.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  cards.forEach(function (card) {
    card.addEventListener('mouseenter', function () { place(card); });
    card.addEventListener('focus', function () { place(card); });
    card.addEventListener('click', function (ev) {
      if (ev.target.closest('.biz-pop a')) return;  // 사진 출처 링크는 그대로 열려요
      if (ev.target.closest('.biz-pop') && !card.classList.contains('open')) return;
      var open = !card.classList.contains('open');
      cards.forEach(function (o) { if (o !== card) setOpen(o, false); });
      place(card);
      setOpen(card, open);
    });
    card.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); card.click(); }
      if (ev.key === 'Escape') { setOpen(card, false); card.blur(); }
    });
  });
  document.addEventListener('click', function (ev) {
    if (!ev.target.closest('.biz-card')) cards.forEach(function (o) { setOpen(o, false); });
  });
});

document.addEventListener('DOMContentLoaded', function () {
  var c = Atlas.find(window.ATLAS_COMPANY_ID);
  var root = document.getElementById('company');
  if (!c || !document.getElementById('chart')) return;
  if (!c.financials.annual.length && !c.financials.quarterly.length) return;

  var e = Atlas.esc;
  var fx = window.ATLAS_META.fx;
  var f = c.financials;
  var SERIES = ['var(--s1)', 'var(--s2)', 'var(--s3)'];
  var state = { mode: f.annual.length ? 'annual' : 'quarterly', cur: 'orig', active: null };

  function rows() {
    var src = state.mode === 'annual' ? f.annual : f.quarterly;
    if (state.cur !== 'krw') return src;
    return src.map(function (r) {
      return [r[0]].concat(r.slice(1).map(function (v) { return v == null ? null : Atlas.toKrwTrillion(v, f.unit); }));
    });
  }
  function unitLabel() { return state.cur === 'krw' ? '조 원' : f.unit; }
  function fmt(v) {
    if (v == null) return '—';
    return (unitLabel() === '억 달러' ? Atlas.num(v, 0) : Atlas.num(v, 1)).replace('-', '−');
  }

  // 큰 금액을 "79조 1,405억 원", "1,024억 3,500만 달러"처럼 읽기 쉽게 써요
  function korean(amount, kind) {
    var neg = amount < 0, a = Math.abs(amount), parts = [];
    if (kind === '원') {
      var eok = Math.round(a / 1e8);               // 억 원 단위까지
      var jo = Math.floor(eok / 10000), rest = eok % 10000;
      if (jo) parts.push(Atlas.num(jo) + '조');
      if (rest || !jo) parts.push(Atlas.num(rest) + '억');
      if (!jo && !rest) parts = [Atlas.num(Math.round(a / 1e4)) + '만'];
    } else {
      var man = Math.round(a / 1e6) * 100;          // 백만 달러(=100만) 단위까지
      var eokD = Math.floor(man / 10000), restD = man % 10000;
      if (eokD) parts.push(Atlas.num(eokD) + '억');
      if (restD || !eokD) parts.push(Atlas.num(restD) + '만');
    }
    return (neg ? '−' : '') + parts.join(' ') + ' ' + kind;
  }

  // 정확한 금액 (자동 수집한 기간만 있어요). 없으면 그래프 숫자를 그대로 써요
  function exactText(label, i, rounded) {
    var ex = f.exact && f.exact[label];
    var v = ex ? ex[i] : null;
    if (v == null) return rounded == null ? '—' : fmt(rounded) + unitLabel();
    if (f.exactUnit === '달러' && state.cur === 'krw') return '약 ' + korean(v * fx.usdKrw, '원');
    return korean(v, f.exactUnit);
  }

  // 비교할 기간 이름: 연도별은 1년 전(2025 → 2024, FY2025 → FY2024), 분기별은 1년 전 같은 분기(26.3Q → 25.3Q)
  function prevLabel(label) {
    var m = /^(FY)?(\d{4})$/.exec(label);
    if (m) return (m[1] || '') + (Number(m[2]) - 1);
    m = /^(\d{2})\.(\d)Q$/.exec(label);
    if (m) return ('0' + (Number(m[1]) + 99) % 100).slice(-2) + '.' + m[2] + 'Q';
    return null;
  }
  // 기간의 값 (정확한 금액이 있으면 그것, 없으면 그래프 숫자). 비율 계산에만 써서 통화는 상관없어요
  function valueOf(label, k) {
    if (f.exact && f.exact[label] && f.exact[label][k] != null) return f.exact[label][k];
    var src = state.mode === 'annual' ? f.annual : f.quarterly;
    var row = src.filter(function (r) { return r[0] === label; })[0];
    return row ? row[k + 1] : null;
  }
  // 전년(동기) 대비 변화: 증가는 빨간 ▲, 감소는 파란 ▼ (주식 시세 표시와 같은 색)
  function change(label, k) {
    var pl = prevLabel(label);
    if (!pl) return '';
    var cur = valueOf(label, k), prev = valueOf(pl, k);
    if (cur == null || prev == null) return '';
    var what = state.mode === 'annual' ? '전년 대비' : '전년 동기 대비';
    var text, cls = '';
    if (prev > 0 && cur >= 0) {
      var pct = (cur - prev) / prev * 100;
      if (Math.abs(pct) < 0.05) text = '변동 없음';
      else { cls = pct > 0 ? 'up' : 'down'; text = (pct > 0 ? '▲ ' : '▼ ') + Atlas.num(Math.abs(pct), 1) + '% ' + (pct > 0 ? '증가' : '감소'); }
    } else if (prev < 0 && cur >= 0) { cls = 'up'; text = '흑자 전환'; }
    else if (prev >= 0 && cur < 0) { cls = 'down'; text = '적자 전환'; }
    else if (prev < 0 && cur < 0) {
      cls = cur > prev ? 'up' : 'down';
      text = '적자 지속 (손실 ' + (cur > prev ? '축소' : '확대') + ')';
    } else return '';
    return '<span class="cd-chg ' + cls + '" title="' + what + ' (' + e(pl) + '과 비교)">' + what + ' ' + text + '</span>';
  }

  function showDetail(i) {
    var data = rows();
    if (i == null || !data[i]) i = data.length - 1;
    state.active = i;
    var r = data[i];
    var names = f.labels || [];
    document.getElementById('chart-detail').innerHTML =
      '<div class="cd-head"><strong>' + e(r[0]) + '</strong>' +
      (i === data.length - 1 ? '<span class="cd-tag">가장 최근</span>' : '') + '</div>' +
      '<div class="cd-rows">' + r.slice(1).map(function (v, k) {
        return '<div><span class="sw" style="background: ' + SERIES[k] + '"></span><span class="n">' + e(names[k] || '') + '</span>' +
          '<strong class="' + (v < 0 ? 'loss' : '') + '">' + exactText(r[0], k, v) + '</strong>' +
          (v < 0 ? '<span class="cd-loss">손실</span>' : '') + change(r[0], k) + '</div>';
      }).join('') + '</div>' +
      '<p class="cd-hint">' + (window.matchMedia('(hover: hover)').matches ? '막대에 마우스를 올리면' : '막대를 누르면') +
      ' 그 기간의 정확한 금액을 볼 수 있어요.</p>';
    root.querySelectorAll('.chart .group, .chart-labels div').forEach(function (g) {
      g.classList.toggle('active', Number(g.getAttribute('data-i')) === i);
    });
  }

  function draw() {
    var data = rows();
    var pos = 0, neg = 0;
    data.forEach(function (r) {
      r.slice(1).forEach(function (v) {
        if (v == null) return;
        if (v > 0) pos = Math.max(pos, v); else neg = Math.max(neg, -v);
      });
    });
    var mobile = window.innerWidth <= 640;
    var total = mobile ? 168 : 240;
    var range = (pos + neg) || 1;
    // 0 선 위(이익)와 아래(손실) 높이를 금액 크기에 맞춰 나눠요
    var upH = Math.round(total * pos / range), downH = total - upH;
    if (!neg) { upH = total; downH = 0; }
    var labelSpace = mobile ? 0 : 18;

    var chart = document.getElementById('chart');
    chart.style.height = (upH + downH + labelSpace * (neg ? 2 : 1) + 8) + 'px';
    chart.classList.toggle('has-loss', neg > 0);
    chart.setAttribute('aria-label', (state.mode === 'annual' ? f.annualTitle : '분기별') + ' ' + (f.labels || []).join('·') +
      ' 막대 그래프, 단위 ' + unitLabel() + (neg ? ', 0 선 아래 막대는 손실' : ''));
    chart.innerHTML = data.map(function (r, gi) {
      return '<div class="group" data-i="' + gi + '" tabindex="0" role="button" aria-label="' + e(r[0]) + ' 자세한 금액 보기">' +
        r.slice(1).map(function (v, i) {
          var up = '', down = '';
          if (v == null) {
            up = '<span>—</span>';
          } else if (v >= 0) {
            var h1 = Math.max(2, Math.round(v / (pos || 1) * upH));
            up = '<span>' + fmt(v) + '</span><div class="bar" style="height: ' + h1 + 'px; background: ' + SERIES[i] + '"></div>';
          } else {
            var h2 = Math.max(2, Math.round(-v / neg * downH));
            down = '<div class="bar neg" style="height: ' + h2 + 'px; background: ' + SERIES[i] + '"></div><span class="loss">' + fmt(v) + '</span>';
          }
          return '<div class="bar-col"><div class="up" style="height: ' + (upH + labelSpace) + 'px">' + up + '</div>' +
            (neg ? '<div class="down" style="height: ' + (downH + labelSpace) + 'px">' + down + '</div>' : '') + '</div>';
        }).join('') + '</div>';
    }).join('') + (neg ? '<div class="zero" style="top: ' + (8 + upH + labelSpace) + 'px" aria-hidden="true"></div>' : '');
    document.getElementById('chart-labels').innerHTML = data.map(function (r, gi) {
      return '<div data-i="' + gi + '">' + e(r[0]) + '</div>';
    }).join('');
    document.querySelector('#fin-table tbody').innerHTML = data.map(function (r) {
      return '<tr><td>' + e(r[0]) + '</td>' + r.slice(1).map(function (v) { return '<td>' + fmt(v) + '</td>'; }).join('') + '</tr>';
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
    showDetail(state.active);
  }

  // 기간(막대 묶음이나 밑의 기간 이름)에 마우스를 올리거나, 누르거나, 키보드로 고르면 정확한 금액을 보여줘요
  function pick(ev) {
    var g = ev.target.closest('[data-i]');
    if (g) showDetail(Number(g.getAttribute('data-i')));
  }
  ['chart', 'chart-labels'].forEach(function (id) {
    var el = document.getElementById(id);
    el.addEventListener('mouseover', pick);
    el.addEventListener('click', pick);
    el.addEventListener('focusin', pick);
  });

  root.querySelectorAll('[data-mode]').forEach(function (b) {
    b.addEventListener('click', function () { state.mode = b.getAttribute('data-mode'); state.active = null; draw(); });
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
