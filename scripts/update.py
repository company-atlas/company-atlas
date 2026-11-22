"""한 번에 실행: 한국(DART)·미국(SEC) 실적을 받고, 사이트 페이지를 다시 만들어요.

자료 받기가 실패해도 이전에 받아 둔 값(또는 손으로 넣은 예비 값)으로 사이트는 계속 만들어요.
"""

import sys

import build
import fetch_dart
import fetch_logos
import fetch_market
import fetch_photos
import fetch_sec


def main():
    ok = True
    print('== 한국 기업 (Open DART) ==')
    ok = fetch_dart.main() and ok
    print('== 미국 기업 (SEC EDGAR) ==')
    ok = fetch_sec.main() and ok
    print('== 환율 ==')
    try:
        fetch_market.main()
    except Exception as e:  # 받지 못하면 이전 값을 써요
        print('[환율 실패] %s' % e)
    print('== 기업 로고 ==')
    try:
        fetch_logos.main()
    except Exception as e:  # 로고는 없어도 사이트는 만들어요
        print('[로고 실패] %s' % e)
    print('== 사업 설명 사진 ==')
    try:
        fetch_photos.main()
    except Exception as e:  # 사진은 없어도 사이트는 만들어요
        print('[사진 실패] %s' % e)
    print('== 사이트 만들기 ==')
    build.main()
    if not ok:
        print('일부 기업의 자료를 받지 못했어요. 위의 [실패] 줄을 확인해 주세요.')
        sys.exit(1)


if __name__ == '__main__':
    main()
