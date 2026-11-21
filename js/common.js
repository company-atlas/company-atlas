// 여러 화면이 같이 쓰는 부분: 상단 메뉴, 하단 안내, 아이콘, 숫자 표시 도우미

var Atlas = (function () {
  // 이 페이지가 사이트 맨 위 폴더에서 얼마나 깊이 있는지 ('' 또는 '../../')
  var ROOT = window.ATLAS_ROOT || '';
  var COUNTRIES = ['한국', '미국'];
  // 홈 화면에 카드로 보여주는 주요 산업 8개
  var INDUSTRIES = ['반도체·전자', '자동차', 'IT·소프트웨어', '금융·은행', '바이오·제약', '에너지·화학', '유통·소비재', '통신·미디어'];
  // 전체 보기·검색 칸에만 나오는 그 밖의 산업
  var MORE_INDUSTRIES = ['항공우주', '지주·투자'];
  var ALL_INDUSTRIES = INDUSTRIES.concat(MORE_INDUSTRIES);

  var ICON_PATHS = {
    '반도체·전자': '<rect x="7" y="7" width="10" height="10" rx="1.5"/><rect x="10" y="10" width="4" height="4"/><path d="M10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4"/>',
    '자동차': '<path d="M5 16V12l2-5h10l2 5v4"/><path d="M3 16h18v2H3z"/><path d="M5 12h14"/><circle cx="7.5" cy="18.5" r="1.5"/><circle cx="16.5" cy="18.5" r="1.5"/>',
    'IT·소프트웨어': '<rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M2 19h20"/><path d="M10 19l.5-1h3l.5 1"/>',
    '금융·은행': '<path d="M3 9l9-5 9 5"/><path d="M4 9h16"/><path d="M6 9v8M10 9v8M14 9v8M18 9v8"/><path d="M3 20h18"/>',
    '바이오·제약': '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-9V3"/><path d="M7.5 15h9"/>',
    '에너지·화학': '<path d="M13 2L5 13h6l-1 9 8-11h-6l1-9z"/>',
    '유통·소비재': '<path d="M5 8h14l-1 12H6L5 8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
    '통신·미디어': '<circle cx="12" cy="12" r="2"/><path d="M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7M5.6 5.6a9 9 0 0 0 0 12.8M18.4 5.6a9 9 0 0 1 0 12.8"/>'
  };

  function icon(industry) {
    return '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#1D4ED8" stroke-width="1.8" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICON_PATHS[industry] || '') + '</svg>';
  }

  // 글자를 화면에 넣기 전에 특수문자를 안전하게 바꿔요
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function companies() { return window.ATLAS_COMPANIES || []; }
  function find(id) { return companies().filter(function (c) { return c.id === id; })[0]; }
  function param(name) { return new URLSearchParams(location.search).get(name) || ''; }
  function count(key, value) { return companies().filter(function (c) { return c[key] === value; }).length; }

  // 숫자 표시: 1151 → "1,151", 333.6 → "333.6"
  function num(v, digits) {
    return Number(v).toLocaleString('ko-KR', { minimumFractionDigits: digits || 0, maximumFractionDigits: digits || 0 });
  }

  // 달러 금액을 조 원으로 바꿔요 (unit: '억 달러' 또는 '조 달러')
  function toKrwTrillion(value, unit) {
    var rate = window.ATLAS_META.fx.usdKrw;
    if (unit === '억 달러') return value * rate / 10000;
    if (unit === '조 달러') return value * rate;
    return null;
  }

  function header() {
    var el = document.getElementById('site-header');
    if (!el) return;
    el.className = 'site-header';
    el.innerHTML =
      '<div class="wrap">' +
        '<a class="logo" href="' + ROOT + 'index.html">Company Atlas</a>' +
        '<nav class="site-nav" id="site-nav" aria-label="주 메뉴">' +
          '<a href="' + ROOT + 'browse.html?tab=country">국가별</a>' +
          '<a href="' + ROOT + 'browse.html?tab=industry">산업별</a>' +
          '<a href="' + ROOT + 'about.html">소개</a>' +
        '</nav>' +
        '<button type="button" class="menu-btn" aria-label="메뉴 열기" aria-expanded="false" aria-controls="site-nav">' +
          '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#14213D" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>' +
        '</button>' +
      '</div>';
    var btn = el.querySelector('.menu-btn');
    var nav = el.querySelector('.site-nav');
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  function footer() {
    var el = document.getElementById('site-footer');
    if (!el) return;
    el.className = 'site-footer';
    el.innerHTML =
      'Company Atlas · 정보는 각 기업의 공시와 공개 자료를 바탕으로 정리했으며, 투자 판단의 책임은 이용자에게 있어요.' +
      '<br>기업 로고는 각 회사의 상표이며, 기업을 알아보기 쉽도록 보여드리는 것이에요.' +
      '<br>마지막 업데이트: ' + esc(window.ATLAS_META.updated);
  }

  function initials(c) { return esc(c.name.slice(0, 1)); }

  // 로고가 있으면 그림, 없으면(또는 못 불러오면) 첫 글자 상자
  function logoBox(c) {
    if (!c.logo) return '<div class="logo-box" aria-hidden="true">' + initials(c) + '</div>';
    return '<div class="logo-box has-logo' + (c.logoSmall ? ' small-logo' : '') + '"' +
      (c.logoBg ? ' style="background: ' + esc(c.logoBg) + '"' : '') + '><img src="' + ROOT + esc(c.logo) + '" alt="' + esc(c.name) + ' 로고" loading="lazy" ' +
      'onerror="this.parentNode.classList.remove(\'has-logo\');this.parentNode.textContent=\'' + initials(c) + '\'"></div>';
  }

  // 기업 페이지 주소. 내 컴퓨터에서 파일로 열 때는 폴더 주소가 안 열려서 index.html을 붙여요
  function companyUrl(id) {
    return ROOT + 'company/' + encodeURIComponent(id) + '/' + (location.protocol === 'file:' ? 'index.html' : '');
  }

  // 내 컴퓨터에서 열었을 때 폴더 주소(…/)로 끝나는 링크에 index.html을 붙여 줘요
  function fixLocalLinks() {
    if (location.protocol !== 'file:') return;
    document.querySelectorAll('a[href$="/"]').forEach(function (a) {
      var h = a.getAttribute('href');
      if (!/^https?:/.test(h)) a.setAttribute('href', h + 'index.html');
    });
  }

  document.addEventListener('DOMContentLoaded', function () { header(); footer(); fixLocalLinks(); });

  return {
    COUNTRIES: COUNTRIES, INDUSTRIES: INDUSTRIES, ALL_INDUSTRIES: ALL_INDUSTRIES, icon: icon, esc: esc, companies: companies,
    find: find, param: param, count: count, num: num, toKrwTrillion: toKrwTrillion, initials: initials, logoBox: logoBox,
    companyUrl: companyUrl, ROOT: ROOT
  };
})();
