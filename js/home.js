// 홈 화면: 검색창의 선택 칸, 산업 카드, 국가 버튼 채우기

document.addEventListener('DOMContentLoaded', function () {
  var countrySel = document.getElementById('country');
  var industrySel = document.getElementById('industry');
  Atlas.COUNTRIES.forEach(function (c) { countrySel.add(new Option(c, c)); });
  Atlas.ALL_INDUSTRIES.forEach(function (i) { industrySel.add(new Option(i, i)); });

  // 휴대폰에서는 국가·산업 선택 칸을 한 줄에 나란히 놓아요
  var selects = document.querySelector('.selects');
  function arrange() { selects.style.display = window.innerWidth <= 640 ? 'flex' : 'contents'; }
  arrange();
  window.addEventListener('resize', arrange);

  var cards = Atlas.INDUSTRIES.map(function (i) {
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
});
