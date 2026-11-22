"""미국 기업: SEC EDGAR의 companyfacts에서 실적을 받아 data/fetched/<id>.json에 저장해요.

필요한 것: 환경변수 SEC_CONTACT_EMAIL (SEC가 요청마다 연락처를 남기라고 해요)
사용하는 API: https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
"""

import datetime
import math
import os

from common import FETCHED_DIR, get_json, load_companies, read_json, write_json

BASE = 'https://data.sec.gov/api/xbrl/companyfacts/CIK%s.json'
# 같은 줄(묶음) 안의 이름은 같은 뜻이라 섞어 써요. 뒤 묶음은 앞 묶음에 값이 없는 기간에만 써요.
CONCEPTS = {
    'rev': [('RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet',
             'RevenueFromContractWithCustomerIncludingAssessedTax')],
    'op': [('OperatingIncomeLoss',)],
    'ni': [('NetIncomeLoss',), ('NetIncomeLossAvailableToCommonStockholdersBasic',), ('ProfitLoss',)],
}


def days(a, b):
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days


def periods(facts, tiers):
    """기간(시작~끝)별 값을 모아요.

    회사가 해마다 다른 이름(예: Revenues → RevenueFromContract…)으로 공시하기도 해서,
    같은 묶음의 이름을 모두 합친 뒤 같은 기간이면 가장 최근에 낸 공시 값을 써요.
    """
    out = {}
    for names in tiers:
        found = {}
        for name in names:
            units = facts.get('us-gaap', {}).get(name, {}).get('units', {}).get('USD', [])
            for f in units:
                if 'start' not in f or f.get('form') not in ('10-K', '10-Q', '10-K/A', '10-Q/A', '10-KT', 'S-1', 'S-1/A'):
                    continue
                k = (f['start'], f['end'])
                if k not in found or f.get('filed', '') > found[k]['filed']:
                    found[k] = {'val': f['val'], 'filed': f.get('filed', '')}
        for k, v in found.items():
            out.setdefault(k, v['val'])
    return out


def split(vals):
    """1년짜리 기간과 3개월짜리 기간을 나누고, 빠진 분기는 다른 기간끼리 빼서 계산해요.

    예) 1년 − 9개월 = 4분기, 6개월 − 2분기 = 1분기, 9개월 − 6개월 = 3분기
    """
    annual = {k: v for k, v in vals.items() if 350 <= days(*k) <= 380}
    quarter = {k: v for k, v in vals.items() if 80 <= days(*k) <= 100}
    def shift(d, n):
        return (datetime.date.fromisoformat(d) + datetime.timedelta(days=n)).isoformat()
    for _ in range(3):  # 새로 계산된 분기로 또 다른 분기를 계산할 수 있어서 몇 번 반복해요
        added = False
        keys = list(vals.items()) + [(k, v) for k, v in quarter.items() if k not in vals]
        for (s1, e1), v1 in keys:
            for (s2, e2), v2 in keys:
                # 같은 날 시작, 긴 기간 − 짧은 기간 = 뒤쪽 기간
                if s1 == s2 and e2 > e1:
                    k = (shift(e1, 1), e2)
                # 같은 날 끝, 긴 기간 − 짧은 기간 = 앞쪽 기간
                elif e1 == e2 and s2 < s1:
                    k = (s2, shift(s1, -1))
                else:
                    continue
                if 80 <= days(*k) <= 100 and k not in quarter:
                    quarter[k] = v2 - v1
                    added = True
        if not added:
            break
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
    debug = {}
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
            debug[c['id']] = concept_summary(data.get('facts', {}))
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
            # 정확한 금액(달러 단위): 그래프에서 기간을 누르면 보여줘요
            'exact_unit': '달러',
            'annual_exact': annual,
            'quarterly_exact': quarterly,
            'overview': {},
        })
        print('[완료] %s: 연간 %d개, 분기 %d개' % (c['name'], len(annual), len(quarterly)))
    # 확인용 기록: 회사별 매출·이익 관련 계정 이름과 마지막 기간 (자료가 늦거나 빠질 때 원인을 찾으려고)
    write_json(os.path.join(FETCHED_DIR, '_debug_sec.json'), debug)
    return ok


def concept_summary(facts):
    out = {}
    for name, body in facts.get('us-gaap', {}).items():
        if not any(w in name for w in ('Revenue', 'NetIncome', 'OperatingIncome', 'ProfitLoss')):
            continue
        units = body.get('units', {}).get('USD', [])
        dur = [u for u in units if 'start' in u]
        if dur:
            last = max(dur, key=lambda u: u['end'])
            out[name] = {'n': len(dur), 'last_end': last['end'], 'last_form': last.get('form'), 'last_filed': max(u.get('filed', '') for u in dur)}
    return out


if __name__ == '__main__':
    main()
