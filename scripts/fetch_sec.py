"""미국 기업: SEC EDGAR의 companyfacts에서 실적을 받아 data/fetched/<id>.json에 저장해요.

필요한 것: 환경변수 SEC_CONTACT_EMAIL (SEC가 요청마다 연락처를 남기라고 해요)
사용하는 API: https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
"""

import datetime
import math
import os

from common import FETCHED_DIR, get_json, load_companies, read_json, write_json

BASE = 'https://data.sec.gov/api/xbrl/companyfacts/CIK%s.json'
CONCEPTS = {
    'rev': ('RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet'),
    'op': ('OperatingIncomeLoss',),
    'ni': ('NetIncomeLoss',),
}


def days(a, b):
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days


def periods(facts, names):
    """기간(시작~끝)별 값을 모아요.

    회사가 해마다 다른 이름(예: Revenues → RevenueFromContract…)으로 공시하기도 해서,
    후보 이름을 모두 합친 뒤 같은 기간이면 가장 최근에 낸 공시 값을 써요.
    """
    found = {}
    for name in names:
        units = facts.get('us-gaap', {}).get(name, {}).get('units', {}).get('USD', [])
        for f in units:
            if 'start' not in f or f.get('form') not in ('10-K', '10-Q', '10-K/A', '10-Q/A', '10-KT', 'S-1', 'S-1/A'):
                continue
            k = (f['start'], f['end'])
            if k not in found or f.get('filed', '') > found[k]['filed']:
                found[k] = {'val': f['val'], 'filed': f.get('filed', '')}
    return {k: v['val'] for k, v in found.items()}


def split(vals):
    """1년짜리 기간과 3개월짜리 기간을 나누고, 4분기 값을 계산해요."""
    annual = {k: v for k, v in vals.items() if 350 <= days(*k) <= 380}
    quarter = {k: v for k, v in vals.items() if 80 <= days(*k) <= 100}
    for (s, e), total in annual.items():
        inside = sorted(k for k in quarter if s <= k[0] and k[1] <= e)
        if len(inside) == 3 and inside[-1][1] < e:
            # 4분기 = 1년 값 − 1~3분기 합
            start = (datetime.date.fromisoformat(inside[-1][1]) + datetime.timedelta(days=1)).isoformat()
            quarter[(start, e)] = total - sum(quarter[k] for k in inside)
    return annual, quarter


def label_quarter(start, end):
    """기간의 가운데 날짜가 속한 달력 분기로 이름을 붙여요. (예: 9월 28일~12월 27일 → 4분기)"""
    s, e = datetime.date.fromisoformat(start), datetime.date.fromisoformat(end)
    d = s + (e - s) / 2
    return '%02d.%dQ' % (d.year % 100, (d.month - 1) // 3 + 1)


def collect(facts):
    series = {k: split(periods(facts, names)) for k, names in CONCEPTS.items()}
    ends_a = sorted({k for k in series['rev'][0]}, key=lambda k: k[1])
    annual = []
    for k in ends_a:
        row = ['FY%s' % k[1][:4]] + [series[m][0].get(k) for m in ('rev', 'op', 'ni')]
        if row[1] is not None and row[3] is not None:
            annual.append(row)
    ends_q = sorted({k for k in series['rev'][1]}, key=lambda k: k[1])
    quarterly = []
    for k in ends_q:
        row = [label_quarter(*k)] + [series[m][1].get(k) for m in ('rev', 'op', 'ni')]
        if row[1] is not None and row[3] is not None:
            quarterly.append(row)
    return annual[-5:], quarterly[-8:]


def eok(v):
    """달러를 억 달러로 (소수 없이, 반올림). 값이 없으면 None."""
    return None if v is None else int(math.floor(v / 1e8 + 0.5))


def ciks(headers):
    """티커 → SEC 고유번호(CIK) 표. 한 달에 한 번만 새로 받아요."""
    cache_path = os.path.join(FETCHED_DIR, '_sec_ciks.json')
    cache = read_json(cache_path) or {}
    fresh = cache.get('saved', '') >= (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    if cache.get('ciks') and fresh:
        return cache['ciks']
    data = get_json('https://www.sec.gov/files/company_tickers.json', headers=headers)
    out = {str(v['ticker']).upper(): str(v['cik_str']).zfill(10) for v in data.values()}
    write_json(cache_path, {'saved': datetime.date.today().isoformat(), 'ciks': out})
    return out


def main():
    email = os.environ.get('SEC_CONTACT_EMAIL')
    if not email and not os.environ.get('ATLAS_FIXTURES'):
        print('SEC_CONTACT_EMAIL이 없어서 미국 기업 자동 수집을 건너뛰어요.')
        return True
    headers = {'User-Agent': 'CompanyAtlas %s' % email, 'Accept-Encoding': 'identity'}
    ok = True
    table = None
    for c in load_companies():
        ids = c.get('sources_ids') or {}
        cik = ids.get('sec_cik')
        if not cik and ids.get('ticker'):
            try:
                table = table or ciks(headers)
            except Exception as e:
                print('[실패] SEC 고유번호 목록을 받지 못했어요: %s' % e)
                return False
            cik = table.get(ids['ticker'].upper())
            if not cik:
                print('[실패] %s: 티커 %s를 SEC에서 찾지 못했어요' % (c['name'], ids['ticker']))
                ok = False
                continue
        if not cik:
            continue
        try:
            data = get_json(BASE % cik.zfill(10), headers=headers)
            annual, quarterly = collect(data.get('facts', {}))
        except Exception as e:
            print('[실패] %s: %s' % (c['name'], e))
            ok = False
            continue
        conv = lambda rows: [[r[0]] + [eok(v) for v in r[1:]] for r in rows]
        write_json(os.path.join(FETCHED_DIR, c['id'] + '.json'), {
            'source': 'SEC EDGAR',
            'fetched_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
            'unit': '억 달러',
            'annual': conv(annual),
            'quarterly': conv(quarterly),
            'overview': {},
        })
        print('[완료] %s: 연간 %d개, 분기 %d개' % (c['name'], len(annual), len(quarterly)))
    return ok


if __name__ == '__main__':
    main()
