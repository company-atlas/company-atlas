"""여러 스크립트가 같이 쓰는 도구: 인터넷에서 자료 받기, 파일 읽고 쓰기."""

import json
import os
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(ROOT, 'content', 'companies')
FETCHED_DIR = os.path.join(ROOT, 'data', 'fetched')


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def load_companies():
    out = []
    for name in sorted(os.listdir(CONTENT_DIR)):
        if name.endswith('.json'):
            out.append(read_json(os.path.join(CONTENT_DIR, name)))
    return out


def get_json(url, params=None, headers=None, pause=0.15):
    """주소에서 JSON을 받아요.

    시험할 때는 ATLAS_FIXTURES 폴더를 지정하면 인터넷 대신 그 폴더의 파일을 읽어요.
    """
    if params:
        url = url + '?' + urllib.parse.urlencode(params)
    fixtures = os.environ.get('ATLAS_FIXTURES')
    if fixtures:
        key = fixture_key(url)
        path = os.path.join(fixtures, key + '.json')
        if not os.path.exists(path):
            raise FileNotFoundError('시험용 파일이 없어요: ' + path)
        return read_json(path)
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as res:
        body = res.read().decode('utf-8')
    time.sleep(pause)  # 상대 서버에 부담을 주지 않도록 잠깐 쉬어요
    return json.loads(body)


def get_bytes(url, params=None, headers=None):
    """주소에서 파일(압축 파일 등)을 그대로 받아요. 시험할 때는 ATLAS_FIXTURES 폴더의 .bin 파일을 읽어요."""
    if params:
        url = url + '?' + urllib.parse.urlencode(params)
    fixtures = os.environ.get('ATLAS_FIXTURES')
    if fixtures:
        with open(os.path.join(fixtures, fixture_key(url) + '.bin'), 'rb') as f:
            return f.read()
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=120) as res:
        return res.read()


def fixture_key(url):
    """시험용 파일 이름: 인증키를 빼고 주소를 파일 이름으로 바꿔요."""
    parsed = urllib.parse.urlparse(url)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query) if k != 'crtfc_key']
    tail = '_'.join(v for _, v in q)
    base = os.path.basename(parsed.path).replace('.json', '')
    return (base + ('_' + tail if tail else '')).replace('/', '_')
