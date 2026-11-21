# Company Atlas

한국·미국 상장사 정보를 쉽게 보여주는 웹사이트예요. 지금은 예시로 삼성전자와 애플 두 기업이 들어 있어요.

## 내 컴퓨터에서 열어 보기

1. 압축 파일을 풀어요.
2. `company-atlas` 폴더 안의 `index.html`을 더블클릭해요.
3. 웹 브라우저(크롬, 엣지, 사파리 등)에서 홈 화면이 열려요.

따로 설치할 프로그램은 없어요.

## 폴더 구성

| 파일·폴더 | 하는 일 |
| --- | --- |
| `index.html` | 홈 화면 |
| `search.html` | 검색 결과 화면 |
| `browse.html` | 전체 보기 (국가별·산업별) |
| `company.html` | 기업 페이지 (주소 끝의 `?id=samsung` 같은 값으로 기업을 골라요) |
| `about.html` | 사이트 소개 |
| `css/style.css` | 색, 글꼴, 배치 같은 디자인 |
| `js/` | 화면을 움직이게 하는 코드 |
| `data/companies.js` | 기업 정보와 숫자 (나중에 자동으로 갱신할 파일) |

## 인터넷에 공개하기 (GitHub Pages, 무료)

1. [github.com](https://github.com)에서 계정을 만들어요.
2. 오른쪽 위 `+` → `New repository`를 눌러 저장소를 만들어요. 이름은 `company-atlas`, 공개 범위는 `Public`으로 해요.
3. 만든 저장소 화면에서 `uploading an existing file` 링크를 눌러요.
4. `company-atlas` 폴더 **안의 파일과 폴더 전부**를 끌어다 놓고, 아래 `Commit changes`를 눌러요.
5. 저장소의 `Settings` → 왼쪽 `Pages`로 가요.
6. `Branch`를 `main`, 폴더를 `/ (root)`로 고르고 `Save`를 눌러요.
7. 1~2분 뒤 같은 화면 위쪽에 사이트 주소(`https://내아이디.github.io/company-atlas/`)가 나타나요.

## 다음 단계

- DART·SEC에서 데이터를 받아 `data/companies.js`를 자동으로 다시 만드는 부분
- 매일·매 분기 자동 갱신
- 기업 수 늘리기
