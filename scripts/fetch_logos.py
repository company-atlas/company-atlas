"""기업 로고: 각 회사 공식 웹사이트에서 아이콘을 받아 data/logos/<id>.<확장자>에 보관해요.

순서: 홈페이지의 apple-touch-icon(보통 180px) → 크기가 큰 icon → /favicon.ico
이미 받은 로고는 90일 동안 다시 받지 않아요. 받지 못하면 페이지에는 첫 글자 상자가 나와요.
특정 회사 로고를 쓰지 않으려면 content/companies/<id>.json에 "logo": false 를 넣으세요.
"""

import datetime
import html.parser
import os
import re
import urllib.parse
import urllib.request

from common import ROOT, load_companies, read_json, write_json

LOGO_DIR = os.path.join(ROOT, 'data', 'logos')
INDEX = os.path.join(ROOT, 'data', 'logos.json')
UA = {'User-Agent': 'Mozilla/5.0 (compatible; CompanyAtlasBot/1.0; +https://github.com)'}
TYPES = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/svg+xml': 'svg', 'image/x-icon': 'ico',
         'image/vnd.microsoft.icon': 'ico', 'image/webp': 'webp', 'image/gif': 'gif'}
MAX_BYTES = 500 * 1024


class IconFinder(html.parser.HTMLParser):
    """홈페이지 HTML에서 <link rel="...icon..." href="..."> 를 모아요."""

    def __init__(self):
        super().__init__()
        self.icons = []

    def handle_starttag(self, tag, attrs):
        if tag != 'link':
            return
        a = {k.lower(): (v or '') for k, v in attrs}
        rel = a.get('rel', '').lower()
        if 'icon' in rel and a.get('href'):
            self.icons.append((rel, a['href'], a.get('sizes', ''), a.get('type', '')))


def score(icon):
    rel, href, sizes, typ = icon
    s = 0
    if 'apple-touch-icon' in rel:
        s += 1000
    m = re.search(r'(\d+)x\1', sizes)
    if m:
        s += min(int(m.group(1)), 512)
    if href.lower().endswith('.svg') or 'svg' in typ:
        s += 300
    return s


def download(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as res:
        ctype = res.headers.get('Content-Type', '').split(';')[0].strip().lower()
        data = res.read(MAX_BYTES + 1)
        final = res.geturl()
    return ctype, data, final


def candidates(site):
    out = []
    try:
        ctype, data, final = download(site)
        finder = IconFinder()
        finder.feed(data.decode('utf-8', 'ignore'))
        for icon in sorted(finder.icons, key=score, reverse=True):
            out.append(urllib.parse.urljoin(final, icon[1]))
    except Exception as e:
        print('  홈페이지를 읽지 못했어요: %s' % e)
    parts = urllib.parse.urlparse(site)
    out.append('%s://%s/favicon.ico' % (parts.scheme or 'https', parts.netloc))
    return out


def fetch_one(c):
    for url in candidates(c['website']):
        if url.startswith('data:'):
            continue
        try:
            ctype, data, _ = download(url)
        except Exception:
            continue
        ext = TYPES.get(ctype) or {'.png': 'png', '.svg': 'svg', '.ico': 'ico', '.jpg': 'jpg'}.get(
            os.path.splitext(urllib.parse.urlparse(url).path)[1].lower())
        if not ext or len(data) > MAX_BYTES or len(data) < 100:
            continue
        if ext == 'svg' and b'<svg' not in data[:2000].lower():
            continue
        return ext, data, url
    return None


def main():
    os.makedirs(LOGO_DIR, exist_ok=True)
    index = read_json(INDEX) or {}
    today = datetime.date.today()
    for c in load_companies():
        if c.get('logo') is False or not c.get('website'):
            index.pop(c['id'], None)
            continue
        old = index.get(c['id'])
        if old and old.get('saved', '') >= (today - datetime.timedelta(days=90)).isoformat() \
                and os.path.exists(os.path.join(ROOT, old['path'])):
            continue
        got = fetch_one(c)
        if not got:
            print('[로고 없음] %s: 첫 글자 상자로 보여줘요' % c['name'])
            continue
        ext, data, url = got
        for name in os.listdir(LOGO_DIR):  # 예전 확장자 파일 정리
            if name.startswith(c['id'] + '.'):
                os.remove(os.path.join(LOGO_DIR, name))
        rel = 'data/logos/%s.%s' % (c['id'], ext)
        with open(os.path.join(ROOT, rel), 'wb') as f:
            f.write(data)
        index[c['id']] = {'path': rel, 'from': url, 'saved': today.isoformat()}
        print('[로고] %s ← %s' % (c['name'], url))
    write_json(INDEX, index)
    return True


if __name__ == '__main__':
    main()
