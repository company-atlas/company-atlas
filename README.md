# Company Atlas

한국·미국 상장사 정보를 쉽게 보여주는 웹사이트예요. 지금은 예시로 삼성전자와 애플이 들어 있어요.

## 내 컴퓨터에서 열어 보기

압축을 풀고 `company-atlas` 폴더 안의 `index.html`을 더블클릭하면 브라우저에서 열려요.

## 폴더 구성

| 파일·폴더 | 하는 일 | 직접 고치나요? |
| --- | --- | --- |
| `index.html`, `search.html`, `browse.html`, `about.html` | 홈·검색 결과·전체 보기·소개 화면 | 가끔 |
| `content/companies/*.json` | 기업마다 손으로 쓴 내용 (쉬운 설명, 사업, 경쟁사, 연혁, 시가총액) | **예, 여기를 고쳐요** |
| `content/site.json` | 환율 | 예 |
| `company/<기업>/index.html` | 기업 페이지 | 아니요, 자동으로 만들어져요 |
| `data/companies.js` | 검색·그래프용 데이터 | 아니요, 자동으로 만들어져요 |
| `data/fetched/` | DART·SEC에서 받은 숫자 | 아니요, 자동으로 만들어져요 |
| `scripts/` | 자료를 받고 페이지를 만드는 프로그램 | 아니요 |
| `.github/workflows/update.yml` | 매일 아침 자동 실행 설정 | 아니요 |
| `css/`, `js/` | 디자인과 화면 동작 | 가끔 |

## 자동 업데이트 켜기 (한 번만)

1. GitHub 저장소 → `Settings` → 왼쪽 `Secrets and variables` → `Actions` → `New repository secret`
2. 두 가지를 등록해요.
   - 이름 `DART_API_KEY`, 값: Open DART 인증키
   - 이름 `SEC_CONTACT_EMAIL`, 값: 연락받을 이메일 주소 (SEC가 요청마다 연락처를 남기라고 해요)
3. 저장소 위쪽 `Actions` 탭 → 왼쪽 `기업 자료 업데이트` → `Run workflow`를 누르면 바로 한 번 실행돼요.
4. 그 뒤로는 매일 한국 시간 오전 6시쯤 자동으로 실행돼요.

인증키가 없어도 사이트는 손으로 넣은 예비 숫자로 계속 만들어져요.

## 기업 추가하기

`content/companies/` 안의 파일 하나를 복사해서 이름과 내용을 바꾸면 돼요.

- 한국 기업: `sources_ids`에 `dart_corp_code`(DART 고유번호 8자리)
- 미국 기업: `sources_ids`에 `sec_cik`(SEC 고유번호)
