// 검색 결과 화면: 주소에 담긴 검색어·국가·산업으로 기업을 골라 목록으로 보여줘요

document.addEventListener('DOMContentLoaded', function () {
  var q = Atlas.param('q').trim();
  var country = Atlas.param('country');
  var industry = Atlas.param('industry');

  var qInput = document.getElementById('q');
  var countrySel = document.getElementById('country');
  var industrySel = document.getElementById('industry');
  Atlas.COUNTRIES.forEach(function (c) { countrySel.add(new Option(c, c)); });
  Atlas.usedIndustries().forEach(function (i) { industrySel.add(new Option(i, i)); });
  qInput.value = q;
  countrySel.value = country;
  industrySel.value = industry;

  var selects = document.querySelector('.selects');
  function arrange() { selects.style.display = window.innerWidth <= 640 ? 'flex' : 'contents'; }
  arrange();
  window.addEventListener('resize', arrange);

  // 국가·산업 칸을 바꾸면 바로 다시 검색해요
  [countrySel, industrySel].forEach(function (s) {
    s.addEventListener('change', function () { s.form.submit(); });
  });

  var needle = q.toLowerCase().replace(/\s+/g, '');
  var list = Atlas.companies().filter(function (c) {
    if (country && c.country !== country) return false;
    if (industry && c.industry !== industry) return false;
    if (!needle) return true;
    var hay = (c.name + c.nameEn + c.id).toLowerCase().replace(/\s+/g, '');
    return hay.indexOf(needle) !== -1;
  });

  var label = [q && '“' + q + '”', country, industry].filter(Boolean).join(' · ') || '전체';
  document.getElementById('result-title').textContent = label + ' 검색 결과 · ' + list.length + '개 기업';
  document.title = label + ' 검색 결과 · Company Atlas';

  var out = document.getElementById('results');
  if (!list.length) {
    out.innerHTML = '<div class="empty">찾는 기업이 아직 없어요. 지금은 예시로 삼성전자와 애플만 들어 있어요.</div>';
    return;
  }
  out.innerHTML = list.map(function (c) {
    return '<a class="result" href="' + Atlas.companyUrl(c.id) + '">' +
      Atlas.logoBox(c) +
      '<div class="info"><span class="name">' + Atlas.esc(c.name) + '</span>' +
      '<span class="small muted">' + Atlas.esc(c.country) + ' · ' + Atlas.esc(c.industry) + '</span>' +
      '<span style="font-size: 15px">' + Atlas.esc(c.tagline) + '</span></div>' +
      '<span class="go">자세히 보기 &gt;</span></a>';
  }).join('');
});
