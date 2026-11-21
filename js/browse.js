// 전체 보기 화면: 국가별/산업별 탭과 이름 찾기

document.addEventListener('DOMContentLoaded', function () {
  var tab = Atlas.param('tab') === 'industry' ? 'industry' : 'country';
  var filter = document.getElementById('filter');
  var tabs = { country: document.getElementById('tab-country'), industry: document.getElementById('tab-industry') };

  function render() {
    tabs.country.setAttribute('aria-pressed', tab === 'country' ? 'true' : 'false');
    tabs.industry.setAttribute('aria-pressed', tab === 'industry' ? 'true' : 'false');
    filter.placeholder = tab === 'country' ? '국가 이름으로 찾기' : '산업 이름으로 찾기';

    var names = (tab === 'country' ? Atlas.COUNTRIES : Atlas.ALL_INDUSTRIES).slice()
      .sort(function (a, b) { return a.localeCompare(b, 'ko'); });
    var needle = filter.value.trim();
    if (needle) names = names.filter(function (n) { return n.indexOf(needle) !== -1; });

    document.getElementById('browse-list').innerHTML = names.map(function (n) {
      return '<a class="grid-item" href="search.html?' + tab + '=' + encodeURIComponent(n) + '">' +
        '<strong>' + Atlas.esc(n) + '</strong>' +
        '<span class="small muted">' + Atlas.count(tab, n) + '개 기업</span></a>';
    }).join('') || '<div class="empty">찾는 이름이 없어요.</div>';
  }

  tabs.country.addEventListener('click', function () { tab = 'country'; filter.value = ''; render(); });
  tabs.industry.addEventListener('click', function () { tab = 'industry'; filter.value = ''; render(); });
  filter.addEventListener('input', render);
  render();
});
