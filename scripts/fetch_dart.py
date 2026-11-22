"""한국 기업: 금융감독원 Open DART에서 실적과 기업 개요를 받아 data/fetched/<id>.json에 저장해요.

필요한 것: 환경변수 DART_API_KEY (Open DART 인증키)
사용하는 API
  - company.json        기업개황 (대표, 설립일, 주소, 홈페이지)
  - fnlttSinglAcnt.json 단일회사 주요계정 (매출액, 영업이익, 당기순이익)
  - fnlttSinglAcntAll.json 단일회사 전체 재무제표: 주요계정에 매출이나 순이익이 없을 때(금융회사 등) 여기서 찾아요
보고서 코드: 11013 1분기, 11012 반기, 11014 3분기, 11011 사업보고서(연간)
"""

import datetime
import math
import os
import re

import io
import xml.etree.ElementTree as ET
import zipfile

from common import FETCHED_DIR, get_bytes, get_json, load_companies, read_json, write_json

BASE = 'https://opendart.fss.or.kr/api/'
REPORTS = [('11013', 1), ('11012', 2), ('11014', 3), ('11011', 4)]
ACCOUNTS = {'rev': ('매출액', '수익(매출액)', '영업수익', '순영업수익', '보험수익'), 'op': ('영업이익',), 'ni': ('당기순이익',)}


def to_won(text):
    """'1,234,567' 같은 글자를 숫자로 바꿔요. 비어 있으면 None."""
    if text is None:
        return None
    text = str(text).replace(',', '').strip()
    if text in ('', '-'):
        return None
    try:
        return int(text)
    except ValueError:
        return None


def pick(rows, names):
    """계정 이름이 맞는 줄을 찾아요. 연결재무제표(CFS)를 먼저, 없으면 별도(OFS)."""
    for fs in ('CFS', 'OFS'):
        for row in rows:
            if row.get('fs_div', 'CFS') != fs:
                continue
            nm = (row.get('account_nm') or '').replace(' ', '')
            if any(nm.startswith(n) for n in names):
                return row
    return None


# 전체 재무제표에서 찾을 때 쓰는 표준 계정 코드와 이름 (금융회사는 '매출' 대신 '영업수익'을 써요)
FULL_IDS = {'rev': ('ifrs-full_Revenue', 'ifrs_Revenue', 'dart_OperatingRevenue', 'ifrs-full_RevenueFromContractsWithCustomers'),
            'op': ('dart_OperatingIncomeLoss',),
            'ni': ('ifrs-full_ProfitLoss', 'ifrs_ProfitLoss')}
FULL_NAMES = {'rev': ('영업수익', '영업수익합계', '매출액', '수익(매출액)', '매출', '순영업수익'),
              'op': ('영업이익', '영업이익(손실)'),
              'ni': ('당기순이익', '당기순이익(손실)', '연결당기순이익', '분기순이익', '반기순이익',
                     '분기순이익(손실)', '반기순이익(손실)', '당기순손익')}
DEBUG = {}  # 회사별로 전체 재무제표의 손익 계정 이름을 남겨, 나중에 빠진 값이 있으면 원인을 볼 수 있게 해요


def clean_name(nm):
    """'Ⅰ. 영업수익' → '영업수익'처럼 앞 번호와 빈칸을 지워요."""
    return re.sub(r'^[\sⅠ-Ⅻ0-9IVX.\-()]+(?=[가-힣])', '', (nm or '')).replace(' ', '')


def full_report(key, corp_code, year, code):
    """전체 재무제표에서 매출(영업수익)·영업이익·순이익을 찾아요. 연결(CFS)을 먼저, 없으면 별도(OFS)."""
    for fs in ('CFS', 'OFS'):
        data = get_json(BASE + 'fnlttSinglAcntAll.json', {
            'crtfc_key': key, 'corp_code': corp_code, 'bsns_year': str(year), 'reprt_code': code, 'fs_div': fs})
        if data.get('status') != '000':
            continue
        rows = [r for r in data.get('list', []) if r.get('sj_div') in ('IS', 'CIS')]
        if not rows:
            continue
        out = {}
        for k in ('rev', 'op', 'ni'):
            # 이름을 먼저(앞에 있는 이름일수록 우선), 없으면 표준 계정 코드로 찾아요
            row = None
            for name in FULL_NAMES[k]:
                row = next((r for r in rows if clean_name(r.get('account_nm')) == name), None)
                if row:
                    break
            if not row:
                row = next((r for r in rows if (r.get('account_id') or '') in FULL_IDS[k]), None)
            out[k] = {'q': to_won(row.get('thstrm_amount')), 'cum': to_won(row.get('thstrm_add_amount')), 'fs': fs} if row else None
        out['_fs'] = fs
        out['_names'] = [(r.get('sj_div'), r.get('account_id'), r.get('account_nm')) for r in rows][:80]
        return out
    return None


def report(key, corp_code, year, code, accounts=ACCOUNTS, debug_id=None, full_first=False):
    out = summary_report(key, corp_code, year, code, accounts)
    if out is None:
        if debug_id and code == '11011':
            DEBUG.setdefault(debug_id, {}).setdefault('_no_summary', []).append(year)
        return None
    # 주요계정에 매출이나 순이익이 없거나, 일부가 연결이 아닌 별도 재무제표 값이면
    # 전체 재무제표(연결 우선)에서 찾아 채워요 (금융회사 등)
    fs = {v.get('fs') for v in out.values() if v}
    if full_first or out.get('rev') is None or out.get('ni') is None or len(fs) > 1:
        try:
            full = full_report(key, corp_code, year, code)
        except Exception as e:
            print('  전체 재무제표를 받지 못했어요 (%s %s): %s' % (year, code, e))
            full = None
        if full:
            for k in ('rev', 'op', 'ni'):
                mixed = out.get(k) and out[k].get('fs') == 'OFS' and full.get('_fs') == 'CFS'
                if full.get(k) and (out.get(k) is None or mixed or full_first):
                    out[k] = full[k]
            if debug_id and code == '11011':
                DEBUG.setdefault(debug_id, {})[str(year)] = full['_names']
        # 연결 값과 별도 값을 섞지 않아요 (지주회사의 별도 매출은 배당금 등이라 뜻이 달라요)
        if any(v and v.get('fs') == 'CFS' for v in out.values()):
            for k in ('rev', 'op', 'ni'):
                if out.get(k) and out[k].get('fs') == 'OFS':
                    out[k] = None
    return out


def summary_report(key, corp_code, year, code, accounts=ACCOUNTS):
    data = get_json(BASE + 'fnlttSinglAcnt.json', {
        'crtfc_key': key, 'corp_code': corp_code, 'bsns_year': str(year), 'reprt_code': code})
    status = data.get('status')
    if status == '013':  # 조회된 데이터 없음 (아직 공시 전)
        return None
    if status != '000':
        raise RuntimeError('DART 오류 %s: %s' % (status, data.get('message')))
    rows = [r for r in data.get('list', []) if r.get('sj_div', 'IS') in ('IS', 'CIS')]
    out = {}
    for k, names in accounts.items():
        row = pick(rows, names)
        if not row:
            out[k] = None
            continue
        # 분기·반기 보고서: thstrm_amount = 그 3개월, thstrm_add_amount = 연초부터 누적
        out[k] = {'q': to_won(row.get('thstrm_amount')), 'cum': to_won(row.get('thstrm_add_amount')),
                  'fs': row.get('fs_div', 'CFS')}
    return out


def collect(key, corp_code, years, accounts=ACCOUNTS, debug_id=None, full_first=False):
    annual, quarterly = [], []
    for year in years:
        got = {}
        for code, q in REPORTS:
            r = report(key, corp_code, year, code, accounts, debug_id, full_first)
            if r:
                got[q] = r
        if 4 in got:
            annual.append([str(year)] + [got[4][k]['q'] if got[4][k] else None for k in ('rev', 'op', 'ni')])
        for q in (1, 2, 3, 4):
            if q not in got:
                continue
            vals = []
            for k in ('rev', 'op', 'ni'):
                cell = got[q][k]
                if cell is None:
                    vals.append(None)
                elif q < 4:
                    vals.append(cell['q'])
                else:
                    # 4분기 = 연간 − 3분기까지 누적 (누적이 없으면 1~3분기 합으로)
                    prev = got.get(3, {}).get(k)
                    cum3 = prev['cum'] if prev and prev['cum'] is not None else None
                    if cum3 is None and all(got.get(i, {}).get(k) for i in (1, 2, 3)):
                        cum3 = sum(got[i][k]['q'] or 0 for i in (1, 2, 3))
                    vals.append(cell['q'] - cum3 if cell['q'] is not None and cum3 is not None else None)
            quarterly.append(['%02d.%dQ' % (year % 100, q)] + vals)
    return annual, quarterly


def overview(key, corp_code):
    d = get_json(BASE + 'company.json', {'crtfc_key': key, 'corp_code': corp_code})
    if d.get('status') != '000':
        return {}
    est = d.get('est_dt') or ''
    return {
        'founded': est[:4] + '년' if len(est) >= 4 else None,
        'ceo': d.get('ceo_nm'),
        'address': d.get('adres'),
        'website': d.get('hm_url'),
        'stock_code': d.get('stock_code'),
    }


def corp_codes(key):
    """종목코드 → DART 고유번호 표. 한 달에 한 번만 새로 받아 data/fetched에 보관해요."""
    cache_path = os.path.join(FETCHED_DIR, '_dart_corp_codes.json')
    cache = read_json(cache_path) or {}
    fresh = cache.get('saved', '') >= (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    if cache.get('codes') and fresh:
        return cache['codes']
    raw = get_bytes(BASE + 'corpCode.xml', {'crtfc_key': key})
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        xml = z.read(z.namelist()[0])
    codes = {}
    for item in ET.fromstring(xml).iter('list'):
        stock = (item.findtext('stock_code') or '').strip()
        if stock:
            codes[stock] = item.findtext('corp_code').strip()
    write_json(cache_path, {'saved': datetime.date.today().isoformat(), 'codes': codes})
    return codes


def trillion(v):
    """원을 조 원으로 (소수 첫째 자리까지, 반올림)."""
    return None if v is None else math.floor(v / 1e11 + 0.5) / 10


def main():
    key = os.environ.get('DART_API_KEY')
    if not key and not os.environ.get('ATLAS_FIXTURES'):
        print('DART_API_KEY가 없어서 한국 기업 자동 수집을 건너뛰어요.')
        return True
    this_year = int(os.environ.get('ATLAS_YEAR') or datetime.date.today().year)
    years = list(range(this_year - 5, this_year + 1))
    ok = True
    codes = None
    for c in load_companies():
        ids = c.get('sources_ids') or {}
        corp = ids.get('dart_corp_code')
        if not corp and ids.get('krx_stock_code'):
            try:
                codes = codes or corp_codes(key)
            except Exception as e:
                print('[실패] DART 고유번호 목록을 받지 못했어요: %s' % e)
                return False
            corp = codes.get(ids['krx_stock_code'])
            if not corp:
                print('[실패] %s: 종목코드 %s를 DART에서 찾지 못했어요' % (c['name'], ids['krx_stock_code']))
                ok = False
                continue
        if not corp:
            continue
        accounts = dict(ACCOUNTS)
        for k, names in (ids.get('dart_accounts') or {}).items():
            accounts[k] = tuple(names)
        try:
            # 금융·투자회사는 'dart_full': true로 처음부터 전체 재무제표(영업수익 등)를 써요
            annual, quarterly = collect(key, corp, years, accounts, c['id'], bool(ids.get('dart_full')))
            info = overview(key, corp)
        except Exception as e:  # 한 기업이 실패해도 나머지는 계속해요
            print('[실패] %s: %s' % (c['name'], e))
            ok = False
            continue
        conv = lambda rows: [[r[0]] + [trillion(v) for v in r[1:]] for r in rows if r[3] is not None]
        write_json(os.path.join(FETCHED_DIR, c['id'] + '.json'), {
            'source': 'Open DART',
            'fetched_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
            'unit': '조 원',
            'annual': conv(annual)[-5:],
            'quarterly': conv(quarterly)[-8:],
            # 정확한 금액(원 단위): 그래프에서 기간을 누르면 보여줘요
            'exact_unit': '원',
            'annual_exact': [r for r in annual if r[3] is not None][-5:],
            'quarterly_exact': [r for r in quarterly if r[3] is not None][-8:],
            'overview': info,
        })
        print('[완료] %s: 연간 %d개, 분기 %d개' % (c['name'], len(conv(annual)[-5:]), len(conv(quarterly)[-8:])))
    # 확인용 기록: 전체 재무제표를 쓴 회사의 손익 계정 이름 (최근 2년)
    write_json(os.path.join(FETCHED_DIR, '_debug_dart.json'),
               {k: dict(sorted(v.items())[-2:]) for k, v in DEBUG.items()})
    return ok


if __name__ == '__main__':
    main()
