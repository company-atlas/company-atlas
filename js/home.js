// 홈 화면: 검색창의 선택 칸, 산업 카드, 국가 버튼 채우기

document.addEventListener('DOMContentLoaded', function () {
  var countrySel = document.getElementById('country');
  var industrySel = document.getElementById('industry');
  Atlas.COUNTRIES.forEach(function (c) { countrySel.add(new Option(c, c)); });
  Atlas.usedIndustries().forEach(function (i) { industrySel.add(new Option(i, i)); });

  // 휴대폰에서는 국가·산업 선택 칸을 한 줄에 나란히 놓아요
  var selects = document.querySelector('.selects');
  function arrange() { selects.style.display = window.innerWidth <= 640 ? 'flex' : 'contents'; }
  arrange();
  window.addEventListener('resize', arrange);

  var cards = Atlas.homeIndustries().map(function (i) {
    return '<a class="cat" href="search.html?industry=' + encodeURIComponent(i) + '">' +
      '<div class="ico">' + Atlas.icon(i) + '</div>' +
      '<span>' + Atlas.esc(i) + '<br><span class="count">' + Atlas.count('industry', i) + '개 기업</span></span></a>';
  });
  cards.push('<a class="cat chip more" href="browse.html?tab=industry" style="justify-content: center; align-items: center">산업 전체 보기</a>');
  document.getElementById('industry-cards').innerHTML = cards.join('');

  var chips = Atlas.COUNTRIES.map(function (c) {
    return '<a class="chip" href="search.html?country=' + encodeURIComponent(c) + '">' + Atlas.esc(c) + '</a>';
  });
  chips.push('<a class="chip more" href="browse.html?tab=country">전체 보기</a>');
  document.getElementById('country-chips').innerHTML = chips.join('');

  // 기업 둘러보기: 로고 카드로 기업을 보여줘요 (처음엔 12개, '더 보기'로 전체)
  var order = (window.ATLAS_META && window.ATLAS_META.homeOrder) || {};
  function ordered(country) {
    var list = Atlas.companies().filter(function (c) { return !country || c.country === country; });
    var ids = country ? (order[country] || []) : [];
    if (!country) {
      // 전체: 한국·미국을 번갈아 보여줘요
      var kr = order['한국'] || [], us = order['미국'] || [];
      for (var i = 0; i < Math.max(kr.length, us.length); i++) {
        if (kr[i]) ids.push(kr[i]);
        if (us[i]) ids.push(us[i]);
      }
    }
    function rank(c) { var r = ids.indexOf(c.id); return r < 0 ? 9999 : r; }
    return list.sort(function (a, b) { return rank(a) - rank(b) || a.name.localeCompare(b.name, 'ko'); });
  }
  var state = { country: '', all: false };
  // 처음 보여줄 개수: 컴퓨터는 한 줄 5개 × 2줄, 휴대폰은 2개 × 6줄
  var SHOW = window.innerWidth > 640 ? 10 : 12;
  function card(c) {
    return '<a class="co-card" href="' + Atlas.companyUrl(c.id) + '">' + Atlas.logoBox(c) +
      '<strong>' + Atlas.esc(c.name) + '</strong><span>' + Atlas.esc(c.country) + ' · ' + Atlas.esc(c.industry) + '</span></a>';
  }
  function drawExplore() {
    var list = ordered(state.country);
    var shown = state.all ? list : list.slice(0, SHOW);
    document.getElementById('explore-grid').innerHTML = shown.map(card).join('');
    var more = document.getElementById('explore-more');
    more.style.display = list.length > SHOW ? '' : 'none';
    more.textContent = state.all ? '접기' : '더 보기 (전체 ' + list.length + '개)';
    document.querySelectorAll('#explore-tabs .tab').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-country') === state.country ? 'true' : 'false');
    });
  }
  document.getElementById('explore-tabs').innerHTML = [''].concat(Atlas.COUNTRIES).map(function (c) {
    return '<button type="button" class="tab" data-country="' + Atlas.esc(c) + '">' + (c ? Atlas.esc(c) : '전체') + '</button>';
  }).join('');
  document.querySelectorAll('#explore-tabs .tab').forEach(function (b) {
    b.addEventListener('click', function () { state.country = b.getAttribute('data-country'); state.all = false; drawExplore(); });
  });
  document.getElementById('explore-more').addEventListener('click', function () {
    state.all = !state.all;
    drawExplore();
    if (!state.all) document.getElementById('explore').scrollIntoView({ behavior: 'smooth' });
  });
  drawExplore();
});
