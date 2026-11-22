"""환율과 시가총액을 매일 받아 data/fetched/_market.json 에 저장해요.

환율 (인증키 필요 없음)
  Frankfurter API: 유럽중앙은행(ECB)이 매일 발표하는 기준환율로 1달러 = 몇 원인지 계산해요.

시가총액
  한국: 공공데이터포털 '금융위원회_주식시세정보' (환경변수 DATA_GO_KR_KEY)
        보통주와 우선주의 시가총액을 더해요. 우선주 종목코드는 기업 파일의 sources_ids.krx_pref_codes 에 적어요.
        자료는 하루 늦게(전 영업일 종가 기준) 올라와요.
  미국: Finnhub (환경변수 FINNHUB_API_KEY) 의 회사 정보에 있는 시가총액을 써요.

인증키가 없거나 받기에 실패하면, 기업 파일에 손으로 넣어 둔 시가총액을 그대로 써요.
"""

import datetime
import os
import urllib.parse

from common import FETCHED_DIR, get_json, load_companies, read_json, write_json

OUT = os.path.join(FETCHED_DIR, '_market.json')
FX_URLS = ['https://api.frankfurter.dev/v1/latest?base=USD&symbols=KRW',
           'https://api.frankfurter.app/latest?from=USD&to=KRW']
KR_URL = 'https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo'
US_URL = 'https://finnhub.io/api/v1/stock/profile2'


def kdate(iso):
    d = datetime.date.fromisoformat(iso)
    return '%d년 %d월 %d일' % (d.year, d.month, d.day)


def fetch_fx():
    for url in FX_URLS:
        try:
            d = get_json(url)
            rate = (d.get('rates') or {}).get('KRW')
            if rate:
                return {'usdKrw': round(float(rate), 1), 'date': d.get('date'),
                        'asOf': '%s 유럽중앙은행 기준환율' % kdate(d['date']), 'source': 'Frankfurter (ECB)'}
        except Exception as e:
            print('  환율 받기 실패 (%s): %s' % (url, e))
    return None


def kr_cap(key, code):
    """종목 하나의 가장 최근 시가총액(원)과 날짜."""
    begin = (datetime.date.today() - datetime.timedelta(days=14)).strftime('%Y%m%d')
    d = get_json(KR_URL, {'serviceKey': key, 'resultType': 'json', 'numOfRows': 30, 'pageNo': 1,
                          'likeSrtnCd': code, 'beginBasDt': begin})
    items = (((d.get('response') or {}).get('body') or {}).get('items') or {}).get('item') or []
    if isinstance(items, dict):
        items = [items]
    rows = [i for i in items if str(i.get('srtnCd', '')).lstrip('A') == code]
    if not rows:
        return None
    last = max(rows, key=lambda i: i['basDt'])
    return int(last['mrktTotAmt']), last['basDt']


def main():
    old = read_json(OUT) or {}
    out = {'fx': old.get('fx'), 'caps': old.get('caps') or {}}
    fx = fetch_fx()
    if fx:
        out['fx'] = fx
        print('[환율] 1달러 = %s원 (%s)' % (fx['usdKrw'], fx['date']))

    kr_key = os.environ.get('DATA_GO_KR_KEY')
    if kr_key and '%' in kr_key:
        kr_key = urllib.parse.unquote(kr_key)  # '인코딩' 키를 넣어도 되도록 풀어서 써요
    us_key = os.environ.get('FINNHUB_API_KEY')
    if not kr_key:
        print('DATA_GO_KR_KEY가 없어서 한국 기업 시가총액은 손으로 넣은 값을 써요.')
    if not us_key:
        print('FINNHUB_API_KEY가 없어서 미국 기업 시가총액은 손으로 넣은 값을 써요.')

    for c in load_companies():
        ids = c.get('sources_ids') or {}
        try:
            if kr_key and ids.get('krx_stock_code'):
                total, dates = 0, []
                for code in [ids['krx_stock_code']] + list(ids.get('krx_pref_codes') or []):
                    got = kr_cap(kr_key, code)
                    if not got:
                        raise RuntimeError('종목 %s 시세를 찾지 못했어요' % code)
                    total += got[0]
                    dates.append(got[1])
                day = min(dates)
                out['caps'][c['id']] = {
                    'value': round(total / 1e12, 1), 'unit': '조 원',
                    'note': '%s 기준%s' % (kdate('%s-%s-%s' % (day[:4], day[4:6], day[6:])),
                                          ', 보통주·우선주 합계' if ids.get('krx_pref_codes') else ''),
                    'source': '금융위원회 주식시세정보'}
                print('[시가총액] %s %.1f조 원' % (c['name'], total / 1e12))
            elif us_key and ids.get('ticker'):
                d = get_json(US_URL, {'symbol': ids['ticker'], 'token': us_key})
                mc = d.get('marketCapitalization')  # 백만 달러 단위
                if not mc:
                    raise RuntimeError('시가총액이 비어 있어요')
                out['caps'][c['id']] = {
                    'value': round(mc / 1e6, 3), 'unit': '조 달러',
                    'note': '%s 기준' % kdate(datetime.date.today().isoformat()),
                    'source': 'Finnhub'}
                print('[시가총액] %s %.3f조 달러' % (c['name'], mc / 1e6))
        except Exception as e:
            print('[시가총액 실패] %s: %s (이전 값을 써요)' % (c['name'], e))
    write_json(OUT, out)
    return True


if __name__ == '__main__':
    main()
