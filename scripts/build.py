"""사이트 만들기: 손으로 쓴 내용(content/) + 자동으로 받은 숫자(data/fetched/)를 합쳐서
  - data/companies.js        (검색·그래프가 쓰는 데이터)
  - company/<id>/index.html  (기업마다 자기 주소를 가진 페이지)
  - sitemap.xml, robots.txt  (검색엔진 안내)
를 다시 만들어요.

사이트 주소는 환경변수 SITE_URL로 받아요. (예: https://내아이디.github.io/company-atlas/)
"""

import datetime
import html
import json
import os
import shutil

from common import FETCHED_DIR, ROOT, load_companies, read_json

KST = datetime.timezone(datetime.timedelta(hours=9))
COLORS = ['var(--s1)', 'var(--s2)', 'var(--s3)', 'var(--s4)', 'var(--s5)', 'var(--s6)']
SERIES_COLORS = ['var(--s1)', 'var(--s2)', 'var(--s3)']
DEFAULT_LABELS = ['매출', '영업이익', '순이익']
NAV = [('about', '소개'), ('info', '핵심 정보'), ('biz', '사업'), ('nums', '숫자'), ('perf', '실적'), ('history', '연혁'), ('rivals', '경쟁사')]


def e(s):
    return html.escape(str(s), quote=True)


def num(v, digits=0):
    return format(round(v, digits), ',.%df' % digits)


def to_krw_trillion(value, unit, rate):
    if unit == '억 달러':
        return value * rate / 10000
    if unit == '조 달러':
        return value * rate
    return None


def merge(c, fetched):
    """손으로 쓴 내용에 자동 수집 숫자를 덮어써요. 수집 값이 없으면 예비 값을 써요."""
    fin = dict(c['financials_text'])
    fin.setdefault('labels', DEFAULT_LABELS)
    fb = c.get('financials_fallback', {})
    src = fetched if fetched and (fetched.get('annual') or fetched.get('quarterly')) else None
    # 자동 수집 값이 있으면 그것을, 없는 칸은 손으로 넣은 예비 값을 써요
    fin['annual'] = (src or {}).get('annual') or fb.get('annual', [])
    fin['quarterly'] = (src or {}).get('quarterly') or fb.get('quarterly', [])
    fin['source'] = src['source'] if src else '직접 정리'

    out = {k: v for k, v in c.items() if k not in ('financials_fallback', 'financials_text', 'sources_ids')}
    out['financials'] = fin

    # 숫자로 보기의 매출·영업이익은 가장 최근 연간 실적으로 자동 갱신
    cap = [h for h in c['highlights'] if h['label'] == '시가총액']
    out['highlights'] = cap
    if fin['annual'] and fin['annual'][-1][1] is not None:
        label, rev, op = fin['annual'][-1][0], fin['annual'][-1][1], fin['annual'][-1][2]
        names = fin['labels']
        year_word = label[2:] + ' 회계연도' if label.startswith('FY') else label + '년'
        unit = fin['unit']
        if unit == '조 원':
            per_day = rev * 10000 / 365  # 억 원
            day_text = '하루 평균 약 %s억 원' % num(round(per_day, -3) if per_day >= 1000 else round(per_day))
        else:
            per_day = rev / 365
            if per_day >= 1:
                day_text = '하루 평균 약 %s억 달러' % num(per_day)
            else:
                day_text = '하루 평균 약 %s만 달러' % num(round(per_day * 10000, -2))
        first = [{'value': rev, 'unit': unit, 'label': year_word + ' ' + names[0], 'note': day_text}]
        if op is not None:
            first.append({'value': op, 'unit': unit, 'label': year_word + ' ' + names[1],
                          'note': '본업으로 남긴 돈' if op >= 0 else '본업에서 본 손실'})
        out['highlights'] = first + cap
    elif fin['annual'] and fin['annual'][-1][3] is not None:
        label, ni = fin['annual'][-1][0], fin['annual'][-1][3]
        year_word = label[2:] + ' 회계연도' if label.startswith('FY') else label + '년'
        out['highlights'] = [{'value': ni, 'unit': fin['unit'], 'label': year_word + ' 순이익',
                              'note': '1년 동안 최종적으로 남긴 돈' if ni >= 0 else '1년 동안의 최종 손실'}] + cap

    # 매출(첫 칸)이 전부 비어 있으면(금융회사 등) 그 칸을 빼고 영업이익·순이익만 보여줘요
    rows_all = fin['annual'] + fin['quarterly']
    if rows_all and all(r[1] is None for r in rows_all):
        fin['annual'] = [[r[0]] + r[2:] for r in fin['annual']]
        fin['quarterly'] = [[r[0]] + r[2:] for r in fin['quarterly']]
        fin['labels'] = fin['labels'][1:]
        if c['financials_text'].get('labelNoteNoRevenue'):
            fin['labelNote'] = c['financials_text']['labelNoteNoRevenue']

    # 기업 개요: 손으로 쓴 값이 없을 때만 DART 값으로 채워요
    ov = (fetched or {}).get('overview') or {}
    info = dict(c['info'])
    auto = {}
    if ov.get('founded'):
        auto['설립연도'] = ov['founded']
    if ov.get('address'):
        auto['본사 위치'] = ' '.join(ov['address'].split()[:2])  # 예: "경기도 이천시"
    if ov.get('ceo'):
        auto['대표'] = ' · '.join(n.strip() for n in ov['ceo'].replace('/', ',').split(',') if n.strip())
    ordered = {}
    for k in ('설립연도', '본사 위치', '대표', '직원 수', '상장 여부'):
        if k in info:
            ordered[k] = info[k]
        elif k in auto:
            ordered[k] = auto[k]
    for k, v in info.items():
        ordered.setdefault(k, v)
    out['info'] = [[k, v] for k, v in ordered.items()]
    if not out.get('website') and ov.get('website'):
        w = ov['website']
        out['website'] = w if w.startswith('http') else 'https://' + w
    return out


def logo_box(c, root):
    """로고가 있으면 그림을, 없으면 첫 글자 상자를 보여줘요."""
    if c.get('logo'):
        return ('<div class="logo-box has-logo"><img src="%s%s" alt="%s 로고" loading="lazy" '
                'onerror="this.parentNode.classList.remove(\'has-logo\');this.parentNode.textContent=\'%s\'"></div>' % (
                    root, e(c['logo']), e(c['name']), e(c['name'][0])))
    return '<div class="logo-box" aria-hidden="true">%s</div>' % e(c['name'][0])


def render_company(c, companies, meta):
    by_id = {x['id']: x for x in companies}
    root = '../../'
    is_usd = c['currency'] == 'USD'
    fx = meta['fx']
    h = []
    h.append('<div class="crumb"><a href="%sindex.html">홈</a> &gt; <a href="%ssearch.html?country=%s">%s</a> &gt; '
             '<a href="%ssearch.html?industry=%s">%s</a> &gt; %s</div>' % (
                 root, root, e(c['country']), e(c['country']), root, e(c['industry']), e(c['industry']), e(c['name'])))
    h.append('<div class="co-head">%s'
             '<div style="display: flex; flex-direction: column; gap: 4px"><h1>%s<span class="en">%s</span></h1>'
             '<span class="meta">%s · %s</span><span class="tagline">%s</span></div></div>' % (
                 logo_box(c, root), e(c['name']), e(c['nameEn']), e(c['country']), e(c['industry']), e(c['tagline'])))
    h.append('<nav class="in-nav" aria-label="페이지 안 이동">%s</nav>' % ''.join(
        '<a href="#%s">%s</a>' % n for n in NAV))
    h.append('<div class="co-body">')

    h.append('<section class="sec" id="about"><h2>이 기업은?</h2><p class="about">%s</p></section>' % e(c['about']))

    cells = ''.join('<div class="cell"><div class="lbl">%s</div><div class="val">%s</div></div>' % (e(k), e(v)) for k, v in c['info'])
    site = c['website'].replace('https://', '').replace('http://', '').replace('www.', '')
    cells += ('<div class="cell"><div class="lbl">공식 웹사이트</div><div class="val"><a href="%s" target="_blank" '
              'rel="noopener" style="color: var(--accent)">%s</a></div></div>' % (e(c['website']), e(site)))
    h.append('<section class="sec" id="info"><h2>핵심 정보</h2><div class="cards info">%s</div></section>' % cells)

    h.append('<section class="sec" id="biz"><h2>무엇을 하는 기업인가요?</h2><div class="cards">%s</div></section>' % ''.join(
        '<div class="card"><strong>%s</strong><span class="lbl">%s</span></div>' % (e(b[0]), e(b[1])) for b in c['businesses']))

    # 숫자로 보기
    parts = []
    for hl in c['highlights']:
        v = hl['value']
        big = ('약 ' if hl.get('approx') else '') + num(v, 1 if v % 1 else 0) + hl['unit']
        big = big.replace('-', '−')
        note = hl['note']
        krw_line = ''
        if is_usd:
            krw = to_krw_trillion(v, hl['unit'], fx['usdKrw'])
            krw_line = '<div class="krw">≈ 약 %s조 원</div>' % num(krw)
            other = by_id.get(hl.get('compareTo', ''))
            if other:
                cap = [x for x in other['highlights'] if x['label'] == '시가총액']
                if cap:
                    ratio = krw / cap[0]['value']
                    note += ' · %s의 약 %s배' % (other['name'], ('%.1f' % ratio).rstrip('0').rstrip('.') if ratio < 10 else '%d' % round(ratio))
        parts.append('<div class="cell"><div class="big">%s</div>%s<div class="lbl" style="margin-top: 4px">%s · %s</div></div>' % (
            e(big), krw_line, e(hl['label']), e(note)))
    fx_note = ('<p class="note">원화 금액은 1달러 = %s원(%s)으로 환산한 대략적인 값이에요.</p>' % (num(fx['usdKrw'], 1), e(fx['asOf']))) if is_usd else ''
    h.append('<section class="sec" id="nums"><h2>숫자로 보기</h2>%s<div class="cards nums">%s</div></section>' % (fx_note, ''.join(parts)))

    # 사업별 비중 (자료가 있을 때만)
    items = (c.get('share') or {}).get('items') or []
    if not items:
        pass
    else:
        h.append(render_share(c, items))

    # 실적 흐름 (막대는 js/company.js가 그려요)
    f = c['financials']
    h.append(render_perf(c, f, is_usd))
    rest_of_page(h, c, by_id, root, fx, meta, is_usd, f)
    return ''.join(h)


def render_share(c, items):
    total = sum(v for _, v in items)
    pcts = [round(v / total * 1000) / 10 for _, v in items]
    pcts[0] = round(pcts[0] + round(100 - sum(pcts), 1), 1)
    bar = ''.join('<div style="width: %s%%; background: %s"></div>' % (p, COLORS[i % 6]) for i, p in enumerate(pcts))
    legend = ''.join('<div><span class="sw" style="background: %s"></span><span class="n">%s</span><strong>%.1f%%</strong></div>' % (
        COLORS[i % 6], e(n), pcts[i]) for i, (n, _) in enumerate(items))
    return ('<section class="sec" id="share"><h2>어디서 돈을 버나요?</h2><div class="share-bar" role="img" aria-label="%s">%s</div>'
            '<div class="share-legend">%s</div><p class="note">%s</p></section>' % (e(c['share']['title']), bar, legend, e(c['share']['note'])))


def render_perf(c, f, is_usd):
    if not f['annual'] and not f['quarterly']:
        return ('<section class="sec" id="perf"><h2>실적 흐름</h2><div class="empty">실적 자료를 준비하고 있어요. 매일 아침 자동 업데이트 때 공시 자료로 채워져요.</div>%s</section>' %
                (('<p class="note">%s</p>' % e(c['fiscalNote'])) if c.get('fiscalNote') else ''))
    labels = f['labels']
    q_tab = ('<button type="button" class="tab" data-mode="quarterly">분기별 (최근 %d분기)</button>' % len(f['quarterly'])) if f['quarterly'] else ''
    a_tab = ('<button type="button" class="tab" data-mode="annual">%s</button>' % e(f['annualTitle'])) if f['annual'] else ''
    cur_tabs = ('<div class="tabs" role="group" aria-label="통화"><button type="button" class="tab" data-cur="orig">달러</button>'
                '<button type="button" class="tab" data-cur="krw">원화로 보기</button></div>') if is_usd else ''
    return ('<section class="sec" id="perf"><h2>실적 흐름</h2><div class="chart-controls"><div class="tabs" role="group" aria-label="기간">'
            '%s%s</div>%s</div>'
            '<div class="legend">%s<span class="unit" id="unit"></span></div>'
            '<div class="chart-scroll"><div class="chart" id="chart" role="img"></div><div class="chart-labels" id="chart-labels"></div></div>'
            '<table class="fin-table" id="fin-table"><thead><tr><th scope="col">기간</th>%s</tr></thead><tbody></tbody></table>'
            '<p class="chart-note" id="chart-note"></p>%s%s</section>' % (
                a_tab, q_tab, cur_tabs,
                ''.join('<span><span class="sw" style="background: %s"></span>%s</span>' % (col, e(n)) for n, col in zip(labels, SERIES_COLORS)),
                ''.join('<th scope="col">%s</th>' % e(n) for n in labels),
                ('<p class="note">%s</p>' % e(f['labelNote'])) if f.get('labelNote') else '',
                ('<p class="note">%s</p>' % e(c['fiscalNote'])) if c.get('fiscalNote') else ''))


def rest_of_page(h, c, by_id, root, fx, meta, is_usd, f):
    h.append('<section class="sec" id="history"><h2>걸어온 길</h2><div class="timeline">%s</div></section>' % ''.join(
        '<div><strong>%s</strong><span>%s</span></div>' % (e(y), e(t)) for y, t in c['history']))

    rows = []
    for biz, comps in c['rivals']:
        chips = []
        for x in comps:
            inner = '<strong>%s</strong><span class="c">%s</span>' % (e(x[0]), e(x[1]))
            if len(x) > 2 and x[2] in by_id:
                chips.append('<a class="rival-chip linked" href="%scompany/%s/">%s</a>' % (root, e(x[2]), inner))
            else:
                chips.append('<span class="rival-chip">%s</span>' % inner)
        rows.append('<div class="rival-row"><strong>%s</strong><div class="row-wrap">%s</div></div>' % (e(biz), ''.join(chips)))
    h.append('<section class="sec" id="rivals"><h2>경쟁사</h2><p class="note" style="font-size: 15px">사업마다 겨루는 상대가 달라요</p>'
             '<div class="rivals">%s</div></section>' % ''.join(rows))

    src = c['sources']
    if f.get('source') and f['source'] != '직접 정리':
        src = '실적 %s 자동 수집, %s' % (f['source'], src)
    fx_src = ' · 환율 1달러 = %s원(%s)' % (num(fx['usdKrw'], 1), e(fx['asOf'])) if is_usd else ''
    h.append('<div class="sources">출처: %s%s · 마지막 업데이트: %s</div>' % (e(src), fx_src, e(meta['updated'])))
    h.append('</div>')


PAGE = '''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} 기업 정보 · Company Atlas</title>
<meta name="description" content="{desc}">
{canonical}<meta property="og:title" content="{name} · Company Atlas">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../../css/style.css">
<script>window.ATLAS_ROOT = '../../'; window.ATLAS_COMPANY_ID = '{id}';</script>
</head>
<body>
<div class="page-shell">
  <header id="site-header"></header>
  <main class="wrap page" id="company">{body}</main>
  <footer id="site-footer"></footer>
</div>
<script src="../../data/companies.js"></script>
<script src="../../js/common.js"></script>
<script src="../../js/company.js"></script>
</body>
</html>
'''


def main():
    site_url = (os.environ.get('SITE_URL') or '').rstrip('/') + '/' if os.environ.get('SITE_URL') else ''
    site = read_json(os.path.join(ROOT, 'content', 'site.json'))
    now = datetime.datetime.now(KST)
    meta = {'fx': site['fx'], 'updated': '%d년 %d월 %d일' % (now.year, now.month, now.day)}

    logos = read_json(os.path.join(ROOT, 'data', 'logos.json')) or {}
    companies = []
    for c in load_companies():
        fetched = read_json(os.path.join(FETCHED_DIR, c['id'] + '.json'))
        m = merge(c, fetched)
        lg = logos.get(c['id'])
        if lg and c.get('logo') is not False and os.path.exists(os.path.join(ROOT, lg['path'])):
            m['logo'] = lg['path']
        companies.append(m)

    with open(os.path.join(ROOT, 'data', 'companies.js'), 'w', encoding='utf-8') as f:
        f.write('// 이 파일은 scripts/build.py가 자동으로 만들어요. 직접 고치지 말고 content/ 폴더를 고쳐 주세요.\n')
        f.write('window.ATLAS_META = %s;\n' % json.dumps(meta, ensure_ascii=False))
        f.write('window.ATLAS_COMPANIES = %s;\n' % json.dumps(companies, ensure_ascii=False, indent=1))

    out_dir = os.path.join(ROOT, 'company')
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    for c in companies:
        page_dir = os.path.join(out_dir, c['id'])
        os.makedirs(page_dir)
        canonical = '<link rel="canonical" href="%scompany/%s/">\n' % (site_url, c['id']) if site_url else ''
        with open(os.path.join(page_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(PAGE.format(name=e(c['name']), desc=e(c['tagline']), canonical=canonical, id=e(c['id']),
                                body=render_company(c, companies, meta)))

    if site_url:
        urls = [site_url, site_url + 'browse.html', site_url + 'about.html'] + [site_url + 'company/%s/' % c['id'] for c in companies]
        today = now.date().isoformat()
        with open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
            for u in urls:
                f.write('  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n' % (e(u), today))
            f.write('</urlset>\n')
        with open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8') as f:
            f.write('User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n' % site_url)
    print('사이트를 다시 만들었어요: 기업 %d개' % len(companies))


if __name__ == '__main__':
    main()
