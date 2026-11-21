"""기업 로고: 각 회사 공식 웹사이트에서 아이콘을 받아 data/logos/<id>.<확장자>에 보관해요.

찾는 곳 (모두 받아 본 뒤 실제 크기가 가장 큰 것을 골라요)
  1. 홈페이지의 apple-touch-icon, icon 링크
  2. 홈페이지가 알려 주는 앱 설정 파일(manifest)의 아이콘 (보통 192~512px)
  3. /apple-touch-icon.png, /favicon.ico
  4. 위에서 못 찾거나 작으면: 구글 공개 파비콘 서비스 (그 회사 사이트 아이콘을 256px까지 제공)

기업 파일(content/companies/<id>.json)에서 바꿀 수 있는 것
  "logo": false            로고를 쓰지 않아요 (첫 글자 상자)
  "logo_url": "https://…"  회사가 공개한 로고 파일 주소를 직접 지정해요 (가장 우선)
  "logo_site": "https://…" 로고를 찾을 사이트를 바꿔요 (예: 알파벳 → 구글)

크기가 64px보다 작은 로고는 7일마다, 나머지는 90일마다 다시 확인해요.
"""

import datetime
import html.parser
import json
import os
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
    req = urllib.request.Request(url, headers=UA)
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


def candidates(site, override=None):
    """받아 볼 주소 목록."""
    out = [override] if override else []
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
    return {'ext': ext, 'data': data, 'url': url, 'px': pixel_size(data, ext)}


def fetch_one(c):
    site = c.get('logo_site') or c['website']
    urls, domain = candidates(site, c.get('logo_url'))
    found = []
    for url in urls:
        got = try_url(url)
        if got:
            if url == c.get('logo_url'):
                return got  # 직접 지정한 로고는 그대로 써요
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
        if old and os.path.exists(os.path.join(ROOT, old['path'])) and old.get('px') is not None \
                and old.get('logo_url') == c.get('logo_url') and old.get('logo_site') == c.get('logo_site'):
            days = 90 if old['px'] >= GOOD_PX else 7
            if old.get('saved', '') >= (today - datetime.timedelta(days=days)).isoformat():
                continue
        got = fetch_one(c)
        if not got:
            print('[로고 없음] %s: 첫 글자 상자로 보여줘요' % c['name'])
            continue
        if old and old.get('px', 0) > got['px'] and os.path.exists(os.path.join(ROOT, old['path'])):
            old['saved'] = today.isoformat()  # 예전 것이 더 크면 그대로 둬요
            continue
        for name in os.listdir(LOGO_DIR):
            if name.startswith(c['id'] + '.'):
                os.remove(os.path.join(LOGO_DIR, name))
        rel = 'data/logos/%s.%s' % (c['id'], got['ext'])
        with open(os.path.join(ROOT, rel), 'wb') as f:
            f.write(got['data'])
        index[c['id']] = {'path': rel, 'from': got['url'], 'px': got['px'], 'saved': today.isoformat(),
                          'logo_url': c.get('logo_url'), 'logo_site': c.get('logo_site')}
        print('[로고] %s %dpx ← %s%s' % (c['name'], got['px'], got['url'], '' if got['px'] >= GOOD_PX else '  (작은 로고)'))
    write_json(INDEX, index)
    return True


if __name__ == '__main__':
    main()
