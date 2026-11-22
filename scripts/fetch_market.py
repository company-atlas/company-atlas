"""환율을 매일 받아 data/fetched/_market.json 에 저장해요.

Frankfurter API: 유럽중앙은행(ECB)이 매일 발표하는 기준환율로 1달러 = 몇 원인지 계산해요.
인증키가 필요 없고, 출처를 밝히면 상업적으로 써도 되는 자료예요.
받지 못하면 이전 값(없으면 content/site.json의 값)을 써요.

시가총액·주가는 숫자로 보여주지 않고 시세 사이트로 연결해요(scripts/build.py의 capLink).
시세 자료는 상업적으로 쓰려면 거래소·데이터 회사와 유료 계약이 필요하기 때문이에요.
"""

import datetime
import os

from common import FETCHED_DIR, get_json, read_json, write_json

OUT = os.path.join(FETCHED_DIR, '_market.json')
FX_URLS = ['https://api.frankfurter.dev/v1/latest?base=USD&symbols=KRW',
           'https://api.frankfurter.app/latest?from=USD&to=KRW']


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


def main():
    old = read_json(OUT) or {}
    out = {'fx': old.get('fx')}
    fx = fetch_fx()
    if fx:
        out['fx'] = fx
        print('[환율] 1달러 = %s원 (%s)' % (fx['usdKrw'], fx['date']))
    write_json(OUT, out)
    return True


if __name__ == '__main__':
    main()
