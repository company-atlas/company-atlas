"""기업 로고: 각 회사 공식 웹사이트에서 아이콘을 받아 data/logos/<id>.<확장자>에 보관해요.

찾는 곳 (모두 받아 본 뒤 실제 크기가 가장 큰 것을 골라요)
  1. 홈페이지의 apple-touch-icon, icon 링크
  2. 홈페이지가 알려 주는 앱 설정 파일(manifest)의 아이콘 (보통 192~512px)
  3. /apple-touch-icon.png, /favicon.ico
  4. 위에서 못 찾거나 작으면: 구글 공개 파비콘 서비스 (그 회사 사이트 아이콘을 256px까지 제공)

기업 파일(content/companies/<id>.json)에서 바꿀 수 있는 것
  "logo": false            로고를 쓰지 않아요 (첫 글자 상자)
  "logo_reject": ["SK_logo"]  주소에 이 글자가 들어간 그림은 쓰지 않아요 (예: 계열사가 그룹 로고를 받아오는 것 막기)
  "logo_url": "https://…"  공식 로고 파일 주소를 직접 지정해요 (가장 우선)
                           여러 개를 목록으로 적으면 받아지는 첫 번째 것을 써요.
                           {"url": "…", "bg": "#14213D"}처럼 배경색을 같이 적을 수도 있어요.
                           주소 대신 아래처럼 '찾는 방법'을 적을 수도 있어요.
                             "commons:LG Energy Solution"  위키미디어 커먼즈에서 이름이 맞는 로고 파일 검색
                             "wiki:ko:LG에너지솔루션"       위키백과 문서의 대표 그림(로고 파일일 때만)
                             "page:https://…"              그 웹페이지 맨 위에 걸린 로고 그림 ("page:"만 쓰면 홈페이지)
                           모두 실패하면 아래의 자동 방법으로 찾아요.
  "logo_site": "https://…" 로고를 찾을 사이트를 바꿔요 (예: 알파벳 → 구글)

크기가 64px보다 작은 로고는 7일마다, 나머지는 90일마다 다시 확인해요.
"""

import datetime
import html.parser
import json
import os
import re
import struct
import urllib.parse
import urllib.request

from common import ROOT, load_companies, read_json, write_json

LOGO_DIR = os.path.join(ROOT, 'data', 'logos')
INDEX = os.path.join(ROOT, 'data', 'logos.json')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36 CompanyAtlasBot/1.0',
      'Accept-Language': 'ko,en;q=0.8'}
TYPES = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/svg+xml': 'svg', 'image/x-icon': 'ico',
         'image/vnd.microsoft.icon': 'ico', 'image/webp': 'webp', 'image/gif': 'gif'}
# 위키미디어는 연락처가 있는 이름(User-Agent)을 쓰라고 해요
WIKI_UA = {'User-Agent': 'CompanyAtlas/1.0 (https://company-atlas.github.io/company-atlas/; logo fetch) python-urllib'}
MAX_BYTES = 800 * 1024
GOOD_PX = 64


class HeadFinder(html.parser.HTMLParser):
    """홈페이지 HTML에서 아이콘 링크와 manifest 주소를 모아요."""

    def __init__(self):
        super().__init__()
        self.icons, self.manifest = [], None

    def handle_starttag(self, tag, attrs):
        if tag != 'link':
            return
        a = {k.lower(): (v or '') for k, v in attrs}
        rel, href = a.get('rel', '').lower(), a.get('href', '')
        if not href or href.startswith('data:'):
            return
        if 'manifest' in rel:
            self.manifest = href
        elif 'icon' in rel and 'mask-icon' not in rel:
            self.icons.append(href)


def download(url):
    req = urllib.request.Request(url, headers=WIKI_UA if 'wikimedia.org' in url or 'wikipedia.org' in url else UA)
    with urllib.request.urlopen(req, timeout=30) as res:
        ctype = res.headers.get('Content-Type', '').split(';')[0].strip().lower()
        data = res.read(MAX_BYTES + 1)
        final = res.geturl()
    return ctype, data, final


def pixel_size(data, ext):
    """그림의 실제 크기(가로 픽셀)를 알아내요. SVG는 크기에 상관없이 선명하므로 크게 쳐요."""
    try:
        if ext == 'svg':
            return 1024
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            w, h = struct.unpack('>II', data[16:24])
            return min(w, h) if max(w, h) <= 2 * min(w, h) else min(w, h) // 2  # 가로로 긴 글자 로고는 낮게 쳐요
        if data[:4] == b'\x00\x00\x01\x00':  # ICO: 안에 든 그림 중 가장 큰 것
            n = struct.unpack('<H', data[4:6])[0]
            best = 0
            for i in range(n):
                w = data[6 + 16 * i] or 256
                off = struct.unpack('<I', data[18 + 16 * i:22 + 16 * i])[0]
                if data[off:off + 8] == b'\x89PNG\r\n\x1a\n':
                    w = struct.unpack('>I', data[off + 16:off + 20])[0]
                best = max(best, w)
            return best
        if data[:6] in (b'GIF87a', b'GIF89a'):
            return struct.unpack('<H', data[6:8])[0]
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            kind = data[12:16]
            if kind == b'VP8X':
                return 1 + int.from_bytes(data[24:27], 'little')
            if kind == b'VP8L':
                return 1 + (struct.unpack('<I', data[21:25])[0] & 0x3FFF)
            if kind == b'VP8 ':
                return struct.unpack('<H', data[26:28])[0] & 0x3FFF
        if data[:2] == b'\xff\xd8':  # JPEG
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2):
                    return struct.unpack('>H', data[i + 7:i + 9])[0]
                i += 2 + struct.unpack('>H', data[i + 2:i + 4])[0]
    except Exception:
        pass
    return 0


def ratio(data, ext):
    """가로 ÷ 세로. 글자로 된 가로로 긴 로고는 상자를 넓게 보여주려고 재요. 모르면 1."""
    try:
        if ext == 'svg':
            head = data[:4000].decode('utf-8', 'ignore')
            tag = re.search(r'<svg[^>]*>', head, re.S | re.I)
            tag = tag.group(0) if tag else ''
            vb = re.search(r'viewBox\s*=\s*["\']\s*([-\d.e]+)[\s,]+([-\d.e]+)[\s,]+([\d.e]+)[\s,]+([\d.e]+)', tag, re.I)
            if vb and float(vb.group(4)) > 0:
                return round(float(vb.group(3)) / float(vb.group(4)), 2)
            w = re.search(r'\swidth\s*=\s*["\']([\d.]+)', tag)
            h = re.search(r'\sheight\s*=\s*["\']([\d.]+)', tag)
            if w and h and float(h.group(1)) > 0:
                return round(float(w.group(1)) / float(h.group(1)), 2)
        elif data[:8] == b'\x89PNG\r\n\x1a\n':
            w, h = struct.unpack('>II', data[16:24])
            return round(w / h, 2) if h else 1
    except Exception:
        pass
    return 1


def overrides(c):
    """기업 파일의 logo_url을 [(주소, 배경색), …] 목록으로 바꿔요."""
    v = c.get('logo_url')
    if not v:
        return []
    out = []
    for item in (v if isinstance(v, list) else [v]):
        if isinstance(item, dict) and item.get('url'):
            out.append((item['url'], item.get('bg')))
        elif isinstance(item, str):
            out.append((item, None))
    return out


def api_json(url):
    _, data, _ = download(url)
    return json.loads(data.decode('utf-8', 'ignore'))


def words(text):
    return [w for w in re.split(r'[^0-9a-z가-힣]+', text.lower()) if w]


def commons_search(query):
    """커먼즈에서 '회사 이름 + logo'로 파일을 찾아, 이름의 낱말이 모두 들어간 로고 파일만 골라요 (SVG 먼저)."""
    url = ('https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srnamespace=6&srlimit=20&srsearch='
           + urllib.parse.quote(query + ' logo'))
    need = words(query)
    hits = []
    for r in api_json(url).get('query', {}).get('search', []):
        title = r['title'].split(':', 1)[1]
        name = words(title)
        joined = ''.join(name)
        # 회사 이름의 낱말이 파일 이름에 '붙어서 순서대로' 있어야 해요
        # (예: 'Aktuality.sk-logo-square'는 sk와 square가 떨어져 있어서 SK Square로 보지 않아요)
        n = len(need)
        phrase = any(name[i:i + n] == need for i in range(len(name) - n + 1)) or ''.join(need) in joined
        if ('logo' in name or 'ci' in name or '로고' in joined) and phrase:
            hits.append(title)
    hits.sort(key=lambda t: (not t.lower().endswith('.svg'), len(t)))
    return ['https://commons.wikimedia.org/wiki/Special:FilePath/' + urllib.parse.quote(t.replace(' ', '_')) for t in hits[:3]]


def wiki_image(lang, title):
    """위키백과 문서의 대표 그림. 파일 이름에 logo/로고/CI가 있거나 SVG일 때만 써요 (건물 사진 방지)."""
    url = ('https://%s.wikipedia.org/w/api.php?action=query&format=json&prop=pageimages&piprop=original|name'
           '&pilicense=any&redirects=1&titles=%s' % (lang, urllib.parse.quote(title)))
    out = []
    for page in api_json(url).get('query', {}).get('pages', {}).values():
        src, name = (page.get('original') or {}).get('source'), (page.get('pageimage') or '').lower()
        if src and ('logo' in name or '로고' in name or 'ci' in words(name) or name.endswith('.svg')):
            out.append(src)
    return out


class LogoImgFinder(html.parser.HTMLParser):
    """웹페이지에서 로고 그림을 찾아요: 이름·설명에 logo가 들어간 그림, 또는 logo 상자 안의 첫 그림."""

    def __init__(self):
        super().__init__()
        self.found, self.armed = [], 0

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or '') for k, v in attrs}
        mark = ' '.join([a.get('class', ''), a.get('id', '')]).lower()
        if tag == 'img':
            src = a.get('src') or a.get('data-src') or ''
            text = ' '.join([src, a.get('alt', ''), mark]).lower()
            if src and not src.startswith('data:') and ('logo' in text or '로고' in text or self.armed):
                self.found.append(src)
            self.armed = 0
        elif 'logo' in mark:
            self.armed = 4  # 다음 몇 개 태그 안에 나오는 그림을 로고로 봐요
        elif self.armed:
            self.armed -= 1


def page_logos(page):
    """웹페이지 맨 위 로고: 그림 파일 주소 목록과, 페이지 안에 직접 그려진 SVG 로고."""
    _, data, final = download(page)
    text = data.decode('utf-8', 'ignore')
    finder = LogoImgFinder()
    finder.feed(text)
    urls = [urllib.parse.urljoin(final, u) for u in finder.found[:4]]
    inline = []
    for m in re.finditer(r'<svg\b.*?</svg>', text, re.S | re.I):
        before = text[max(0, m.start() - 300):m.start()].lower()
        svg = m.group(0)
        if ('logo' in before[-300:] or 'logo' in svg[:300].lower()) and len(svg) > 300:
            if 'xmlns=' not in svg[:300]:
                svg = svg.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"', 1)
            inline.append(svg.encode('utf-8'))
        if len(inline) >= 2:
            break
    return urls, inline


def resolve(entry, site):
    """logo_url 한 칸을 실제 그림 후보(주소 또는 SVG 내용)로 바꿔요."""
    if entry.startswith('commons:'):
        return commons_search(entry[8:].strip()), []
    if entry.startswith('wiki:'):
        _, lang, title = entry.split(':', 2)
        return wiki_image(lang, title), []
    if entry.startswith('page:'):
        return page_logos(entry[5:].strip() or site)
    return [entry], []


def candidates(site):
    """받아 볼 주소 목록."""
    out = []
    parts = urllib.parse.urlparse(site)
    origin = '%s://%s' % (parts.scheme or 'https', parts.netloc)
    try:
        _, data, final = download(site)
        finder = HeadFinder()
        finder.feed(data.decode('utf-8', 'ignore'))
        out += [urllib.parse.urljoin(final, h) for h in finder.icons]
        if finder.manifest:
            try:
                _, mdata, mfinal = download(urllib.parse.urljoin(final, finder.manifest))
                for icon in json.loads(mdata.decode('utf-8', 'ignore')).get('icons', []):
                    if icon.get('src') and 'monochrome' not in (icon.get('purpose') or ''):
                        out.append(urllib.parse.urljoin(mfinal, icon['src']))
            except Exception:
                pass
        origin = '%s://%s' % (urllib.parse.urlparse(final).scheme, urllib.parse.urlparse(final).netloc)
    except Exception as e:
        print('  홈페이지를 읽지 못했어요 (%s): %s' % (site, e))
    out += [origin + '/apple-touch-icon.png', origin + '/favicon.ico']
    seen, uniq = set(), []
    for u in out:
        if u and u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq[:12], parts.netloc


def google_favicon(domain):
    return 'https://www.google.com/s2/favicons?domain=%s&sz=256' % urllib.parse.quote(domain)


def try_url(url):
    try:
        ctype, data, _ = download(url)
    except Exception:
        return None
    path_ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
    ext = TYPES.get(ctype) or {'.png': 'png', '.svg': 'svg', '.ico': 'ico', '.jpg': 'jpg', '.webp': 'webp'}.get(path_ext)
    if not ext or len(data) > MAX_BYTES or len(data) < 100:
        return None
    if ext == 'svg' and b'<svg' not in data[:3000].lower():
        return None
    if ext != 'svg' and data[:1] == b'<':  # 그림 대신 웹페이지가 온 경우
        return None
    return {'ext': ext, 'data': data, 'url': url, 'px': pixel_size(data, ext), 'ratio': ratio(data, ext)}


def fetch_one(c):
    # 1) 직접 지정한 공식 로고 파일: 받아지는 첫 번째 것을 그대로 써요
    site = c.get('logo_site') or c['website']
    for entry, bg in overrides(c):
        try:
            urls, inline = resolve(entry, site)
        except Exception as e:
            print('  로고 찾기 실패 (%s): %s' % (entry, e))
            continue
        for url in urls:
            if any(r.lower() in url.lower() for r in (c.get('logo_reject') or [])):
                print('  제외한 로고: %s' % url)
                continue
            got = try_url(url)
            if got:
                got['override'], got['bg'] = True, bg
                return got
        for svg in inline:
            got = {'ext': 'svg', 'data': svg, 'url': entry, 'px': 1024, 'ratio': ratio(svg, 'svg'),
                   'override': True, 'bg': bg}
            if got['ratio'] != 1 or b'viewbox' in svg[:400].lower():
                return got
        print('  지정한 로고를 받지 못했어요: %s' % entry)
    # 2) 자동: 회사 사이트 아이콘 중 가장 큰 것
    urls, domain = candidates(site)
    found = []
    for url in urls:
        got = try_url(url)
        if got:
            found.append(got)
    best = max(found, key=lambda g: g['px'], default=None)
    if not best or best['px'] < 128:
        g = try_url(google_favicon(domain))
        if g and (not best or g['px'] > best['px']):
            best = g
    return best


def main():
    os.makedirs(LOGO_DIR, exist_ok=True)
    index = read_json(INDEX) or {}
    today = datetime.date.today()
    for c in load_companies():
        if c.get('logo') is False or not c.get('website'):
            index.pop(c['id'], None)
            continue
        old = index.get(c['id'])
        if old and os.path.exists(os.path.join(ROOT, old['path'])) and old.get('px') is not None and 'ratio' in old \
                and old.get('logo_url') == c.get('logo_url') and old.get('logo_site') == c.get('logo_site'):
            days = 90 if old['px'] >= GOOD_PX else 7
            if old.get('saved', '') >= (today - datetime.timedelta(days=days)).isoformat():
                continue
        got = fetch_one(c)
        same_setting = bool(old) and old.get('logo_url') == c.get('logo_url') and old.get('logo_site') == c.get('logo_site')
        if not got:
            if old and not same_setting:  # 설정을 바꿨는데 새 로고를 못 찾으면, 예전(잘못된) 로고는 지워요
                path = os.path.join(ROOT, old['path'])
                if os.path.exists(path):
                    os.remove(path)
                index.pop(c['id'], None)
            print('[로고 없음] %s: 첫 글자 상자로 보여줘요' % c['name'])
            continue
        if same_setting and not got.get('override') and old.get('px', 0) > got['px'] and os.path.exists(os.path.join(ROOT, old['path'])):
            old['saved'] = today.isoformat()  # 예전 것이 더 크면 그대로 둬요
            continue
        for name in os.listdir(LOGO_DIR):
            if name.startswith(c['id'] + '.'):
                os.remove(os.path.join(LOGO_DIR, name))
        rel = 'data/logos/%s.%s' % (c['id'], got['ext'])
        with open(os.path.join(ROOT, rel), 'wb') as f:
            f.write(got['data'])
        index[c['id']] = {'path': rel, 'from': got['url'], 'px': got['px'], 'saved': today.isoformat(),
                          'logo_url': c.get('logo_url'), 'logo_site': c.get('logo_site'),
                          'ratio': got['ratio'], 'override': bool(got.get('override')), 'bg': got.get('bg')}
        print('[로고] %s %s ← %s%s' % (c['name'], '공식 파일' if got.get('override') else '%dpx' % got['px'], got['url'], '' if got['px'] >= GOOD_PX else '  (작은 로고)'))
    write_json(INDEX, index)
    return True


if __name__ == '__main__':
    main()
