"""사업 설명 사진: 위키미디어 커먼즈에서 자유 이용 사진을 찾아 data/photos/에 보관해요.

기업 파일(content/companies/<id>.json)의 business_details[n].photo 에 적은 검색어로 찾아요.
  "photo": "file:Exact_file_name.jpg"     정확한 파일 이름을 직접 지정 (가장 확실해요)
  "photo": {"q": "Tesla Megapack", "need": ["megapack"]}
                                          검색어로 찾되, 파일 이름에 need의 낱말이 모두 들어간 사진만 써요
                                          (관련 없는 사진이 들어오지 않게 하려고 꼭 넣어요)
  "photo": [위 형식 여러 개]              앞에서부터 차례로 찾아 처음 찾은 사진을 써요
  "photo": null                           사진 없이 설명만 보여줘요 (대표성 있는 사진이 없을 때)

자유 이용 라이선스(CC0, 퍼블릭 도메인, CC BY, CC BY-SA)인 사진만 쓰고,
사진마다 만든 사람과 라이선스를 data/photos.json에 기록해 화면에 함께 표시해요.
검색어가 바뀌지 않으면 다시 받지 않아요.
"""

import datetime
import json
import os
import re
import time
import urllib.parse
import urllib.request

from common import ROOT, load_companies, read_json, write_json

PHOTO_DIR = os.path.join(ROOT, 'data', 'photos')
INDEX = os.path.join(ROOT, 'data', 'photos.json')
API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'CompanyAtlas/1.0 (https://company-atlas.github.io/company-atlas/; photo fetch) python-urllib'}
FREE = re.compile(r'^(cc0|public domain|pd\b|cc[ -]by(-sa)?([ -][\d.]+)?\b)', re.I)
SKIP_WORDS = ('logo', 'icon', 'map', 'diagram', 'chart', 'graph', 'flag', 'coat of arms', 'signature',
              'lockup', 'wordmark', 'banner', 'slide', 'screenshot')


def api(params):
    params = dict(params, format='json')
    req = urllib.request.Request(API + '?' + urllib.parse.urlencode(params), headers=UA)
    with urllib.request.urlopen(req, timeout=30) as res:
        data = json.loads(res.read().decode('utf-8'))
    time.sleep(0.3)
    return data


def strip_html(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s or '')).strip()


def candidates(query):
    common = {'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size|mime', 'iiurlwidth': 800}
    if query.startswith('file:'):
        data = api(dict(common, action='query', titles='File:' + query[5:]))
    else:
        data = api(dict(common, action='query', generator='search', gsrnamespace=6,
                        gsrsearch=query + ' filetype:bitmap', gsrlimit=15))
    pages = sorted((data.get('query') or {}).get('pages', {}).values(), key=lambda p: p.get('index', 0))
    return pages


def pick(query, need=()):
    for p in candidates(query):
        title = p.get('title', '')
        low = title.lower().replace('_', ' ')
        if need and not all(w.lower() in low for w in need):
            continue
        info = (p.get('imageinfo') or [{}])[0]
        meta = info.get('extmetadata') or {}
        lic = strip_html((meta.get('LicenseShortName') or {}).get('value'))
        if not query.startswith('file:'):
            if any(w in title.lower() for w in SKIP_WORDS):
                continue
            if info.get('width', 0) < 600 or info.get('height', 0) < 300:
                continue
            if info.get('mime') != 'image/jpeg':  # 검색으로 찾을 때는 사진(JPG)만: PNG는 대부분 로고·그림이에요
                continue
        if info.get('mime') not in ('image/jpeg', 'image/png') or not FREE.match(lic):
            continue
        if not info.get('thumburl'):
            continue
        return {
            'url': info['thumburl'],
            'title': title.split(':', 1)[-1],
            'page': info.get('descriptionurl'),
            'artist': strip_html((meta.get('Artist') or {}).get('value'))[:80] or '알 수 없음',
            'license': lic,
            'ext': 'jpg' if info['mime'] == 'image/jpeg' else 'png',
        }
    return None


def main():
    os.makedirs(PHOTO_DIR, exist_ok=True)
    index = read_json(INDEX) or {}
    keep = set()
    for c in load_companies():
        for i, d in enumerate(c.get('business_details') or []):
            key = '%s-%d' % (c['id'], i + 1)
            spec = (d or {}).get('photo')
            if not spec:
                continue
            keep.add(key)
            query = json.dumps(spec, ensure_ascii=False, sort_keys=True)  # 설정이 바뀌면 다시 찾아요
            old = index.get(key)
            if old and old.get('query') == query and os.path.exists(os.path.join(ROOT, old['path'])):
                continue
            try:
                got = None
                for item in (spec if isinstance(spec, list) else [spec]):
                    if isinstance(item, dict):
                        got = pick(item['q'], item.get('need') or ())
                    else:
                        got = pick(item)
                    if got:
                        break
                if not got:
                    print('[사진 없음] %s: %s 에 맞는 자유 이용 사진을 찾지 못했어요' % (key, query))
                    if old:  # 예전 사진은 지워요 (설정과 맞지 않으니까)
                        path = os.path.join(ROOT, old['path'])
                        if os.path.exists(path):
                            os.remove(path)
                        del index[key]
                    continue
                req = urllib.request.Request(got['url'], headers=UA)
                with urllib.request.urlopen(req, timeout=60) as res:
                    data = res.read()
            except Exception as e:
                print('[사진 실패] %s: %s' % (key, e))
                continue
            for name in os.listdir(PHOTO_DIR):
                if name.startswith(key + '.'):
                    os.remove(os.path.join(PHOTO_DIR, name))
            rel = 'data/photos/%s.%s' % (key, got['ext'])
            with open(os.path.join(ROOT, rel), 'wb') as f:
                f.write(data)
            index[key] = {'path': rel, 'query': query, 'title': got['title'], 'page': got['page'],
                          'artist': got['artist'], 'license': got['license'],
                          'saved': datetime.date.today().isoformat()}
            print('[사진] %s ← %s (%s)' % (key, got['title'], got['license']))
    # 더 이상 쓰지 않는 사진은 지워요
    for key in list(index):
        if key not in keep:
            path = os.path.join(ROOT, index[key]['path'])
            if os.path.exists(path):
                os.remove(path)
            del index[key]
    write_json(INDEX, index)
    return True


if __name__ == '__main__':
    main()
