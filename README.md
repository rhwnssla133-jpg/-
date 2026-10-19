# OK익스프레스 홈페이지

광주광역시 OK익스프레스의 반응형 정적 홈페이지입니다. Netlify에는 **업로드용 ZIP만** 배포합니다. 고객은 홈페이지 안의 Google 문의창에 정보를 입력하고, Google Apps Script가 스프레드시트에 저장한 뒤 운영자의 Google 이메일로 알립니다. GitHub 연결, Netlify Forms·Functions, Netlify 환경 변수, SMTP 비밀번호는 이 방식에 필요하지 않습니다.

**현재 공개 파일은 전화 문의 모드입니다.** 제공되지 않은 사업자 상세정보·개인정보 담당자·Google 처리/국외이전 조건을 추정하지 않았습니다. 온라인 접수 코드는 구현했으며 실제 Google 계정의 새 버전 배포·권한 승인·시트 저장·메일 수신은 아직 확인하지 못했습니다. 기존 Apps Script 코드와 호환되는 업데이트가 아니므로 **새 Code.gs 전체 교체 및 기존 웹 앱의 새 버전 배포가 필요합니다.**

## 바로 사용할 파일

| 파일 | 용도 |
| --- | --- |
| [홈페이지 ZIP 다운로드](https://github.com/rhwnssla133-jpg/-/raw/refs/heads/main/ok-express-netlify.zip) | Netlify 수동 업로드. 최상단에 `index.html` 포함 |
| [Google 연결 순서](docs/GOOGLE-SHEETS.md) | 기존 시트·스크립트를 유지하면서 새 코드 적용 |
| [Google 코드 전체](google-apps-script/Code.gs) | Apps Script의 Code.gs에 전부 붙여넣는 파일. HTML 추가 파일 불필요 |
| [빈 고객명단 XLSX](templates/ok-express-customer-list.xlsx) | `이사 문의`·`상담 관리`·`사용 안내` 탭. 실제 고객 0명 |
| [네이버 파워링크 준비 안내](docs/NAVER-POWERLINK.md) | 광고 연결 주소·문구 예시·게시 전 확인 |
| [검증 결과](docs/VALIDATION.md) | 실행한 모의 검사와 실제 계정에서 필요한 검사 구분 |

ZIP이 미리보기로 열리면 GitHub 파일 화면의 **Download raw file**로 저장하세요. Netlify 수동 배포 화면이 ZIP을 받지 않으면 압축을 풀고 `index.html`이 들어 있는 폴더를 업로드합니다. 소스 저장소 ZIP은 배포용 ZIP과 다릅니다.

## 화면과 접수 동작

- 업체 소개·서비스·진행 과정·보상·FAQ·문의·사업정보 푸터와 개인정보/수집/보상 안내 페이지.
- 전화 버튼은 모두 `tel:01025432424`. 모바일 전화·문의 고정 바 제공.
- Google 문의창에서 전화번호·이사 종류·출발/도착 지역, 선택 호칭·날짜·요청사항 입력.
- 필수 수집·선택 수집·국외이전 동의를 분리하며 기본 미선택. 선택 동의 없는 정보는 서버에서도 제외.
- 전화·길이·과거 날짜·상세주소 검사, 오류 위치 이동, 전송 중 잠금, 실패 시 입력 유지와 전화 대안.
- Google이 실제 행 저장을 확인한 응답에만 성공 표시. Gmail 발송 실패 시 행을 보존하고 관리자가 재전송.
- 개인정보를 URL·브라우저 저장소·콘솔에 기록하지 않음. 홈페이지와 Google 사이에는 높이·포커스·완료 신호만 전달.
- Google 문의창이 차단된 브라우저를 위한 별도 문의창 링크와 전화 문의 제공.

직접 작성한 SVG는 예시 일러스트이며 실제 현장 사진이 아닙니다. 후기·별점·보험 가입·보장금액·인증·누적 실적을 만들지 않았습니다. 제공받은 ‘30년 노하우’ 문구만 사용했습니다. 계약·결제·광고 추적·마케팅 발송 기능은 없습니다.

## 설정과 활성화

정보의 기준은 `config.json`입니다. `dist/`를 직접 수정하면 다음 빌드 때 사라집니다. 비밀번호나 API 키를 설정 파일에 넣지 않습니다.

| 설정 | 실제 확인할 내용 |
| --- | --- |
| `business.*`의 미확정 값 | 대표자·사업자등록번호·사업장·운송/주선 허가·운영시간·보험 현황. 보험이 없다면 실제 사실을 기재 |
| `privacy.*` | 담당자·부서·수동 삭제 절차 확인·방침 검토일 |
| `integrations.googleSheets.transfer.*` | 실제 계정의 수탁자·연락처·국가·재위탁·항목·시기·방법·목적·삭제/백업 기간·적용 문서·확인일 |
| `site.*` | 실제 HTTPS 주소·방침 시행일·동의문 버전 |
| `operation.contractAndCompensationReviewedOn` | 실제 계약서·현행 약관·보상 안내 확인일 |
| `integrations.googleSheets.deliveryConfigured`, `privacyReviewedOn` | Google 계정 설정 확인 후 true 및 검토일 |
| `operation.onlineRequested` | 위 항목 확정 후 true |

Google에서는 별도로 `INTEGRATION_ENABLED`와 `PUBLIC_FORM_CONFIRMED`가 모두 `true`여야 접수합니다. 기본값은 비활성입니다. 고객 명단과 메일함을 공개 공유하지 마세요. 설정값이 채워졌다는 사실만으로 법적 검토나 실제 메일 연결이 완료되지는 않습니다. 상세 순서는 [Google 연결 안내](docs/GOOGLE-SHEETS.md)에 있습니다.

Netlify는 정적 화면과 접속/보안 기록을 처리하고, **문의 원본은 Google에서 직접 접수**합니다. 새 버전에는 Netlify Forms 선언이나 이벤트 함수가 없습니다. 예전 버전에서 이미 수집한 Forms 기록·알림 사본이 있다면 기존 계정에서 별도로 관리해야 합니다.

## 빌드·배포

Python 3.12 이상, 표준 라이브러리만으로 홈페이지와 Google 코드를 생성합니다. 기존 체크아웃을 사용하며 별도 Git worktree가 필요하지 않습니다.

```sh
python3 scripts/package.py
```

생성물은 `dist/`, 루트 및 `artifacts/ok-express-netlify.zip`, `google-apps-script/Code.gs`, `artifacts/ok-express-source.zip`입니다. 소스 ZIP에는 편집할 설정·화면·코드·문서·테스트가 있습니다. 고객명단 템플릿을 재생성할 때만 개발 의존성 openpyxl이 필요합니다.

1. 새 Google 코드를 계정에 적용하고 [배포 순서](docs/GOOGLE-SHEETS.md)를 진행합니다.
2. 확인된 설정으로 다시 빌드합니다. `online inquiry: ENABLED`면 Google 문의창을 포함하며, `LOCKED`면 누락한 키를 출력합니다.
3. Netlify의 기존 프로젝트 `helpful-granita-0cfa57` → **Deploys**에서 배포 ZIP 또는 압축 해제 폴더를 수동 업로드합니다. 저장소 연결 화면은 사용하지 않습니다.
4. 공개 HTTPS 홈페이지에서 시트 행과 실제 Gmail 수신을 각각 확인합니다. 테스트 기록은 시트·메일·사본에서 삭제합니다.

Netlify ZIP에는 자체 보안 헤더 `_headers`가 들어 있습니다. `netlify.toml`은 선택적으로 Git 배포를 사용할 때만 필요합니다. 이 프로젝트는 Git 배포 없이도 작동하도록 구성했습니다. Netlify 플랜·Google 할당량과 실제 서비스 UI는 배포일 계정에서 확인하세요.

도메인을 변경하면 `site.url`과 Google의 `SITE_ORIGIN`을 함께 변경하고, 코드 재생성·Google 새 버전 배포·Netlify ZIP 재업로드를 진행합니다. canonical·OG·sitemap은 실제 설정 도메인으로 생성합니다. 감사 페이지는 검색 제외이며 직접 방문해도 접수 성공을 표시하지 않습니다.

## 개발과 검사

내부 확인용 서버는 다음처럼 실행합니다. 클라우드 온보딩 화면에서는 localhost 미리보기 링크를 제공하지 않습니다. 공유하려면 Netlify 배포를 이용하세요. 로컬 화면에서는 Google 접수가 비활성입니다.

```sh
python3 scripts/build.py
python3 -m http.server 8000 --bind 0.0.0.0 --directory dist
```

필수 검사는 Python 빌드와 Node.js 22 이상에서 실행하는 Google 모의 서버 검사입니다.

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/google_bundle.py
node --test tests/google-integration.test.mjs
```

선택 브라우저 검사는 `requirements-dev.txt`의 Python Playwright와 Chromium이 필요합니다. Chromium 설치 후 `CHROMIUM_PATH`에 경로를 지정할 수 있습니다. 현재 환경에서는 `/usr/bin/chromium`을 사용합니다.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python tests/browser_check.py
```

브라우저 검사는 실제 Chromium에서 화면을 실행하고 Google iframe·RPC 응답은 모의 처리합니다. 실제 Google 서비스에 테스트 정보를 보내지 않습니다. 합성 활성화 설정은 임시 폴더에만 생성하며 공개 ZIP에는 포함하지 않습니다.

Google 코드 원본은 `google-apps-script/src/server.gs`와 `src/assets/google-form.js`, `validation.js`입니다. `scripts/google_bundle.py`가 폼·스타일·검사·서버를 단일 Code.gs로 묶습니다. 생성된 Code.gs만 수정하면 다음 생성 때 사라집니다.

## 보유·삭제·보상 운영

목적 달성 시 파기, 미계약 문의 최대 90일은 상담 운영안이며 법정기간을 뜻하지 않습니다. 자동 삭제는 구현하지 않았습니다. 담당자가 Google 문의 행·상담 관리·메일·휴지통·내보낸 사본·출력물을 함께 관리해야 합니다. 셀 삭제만으로 버전 기록·제공자 백업의 완전 삭제를 보장하지 않으므로 실제 계정 정책을 확인합니다. 계약 전환 기록은 실제 근거·기간에 따라 필요한 범위만 별도 보관합니다.

보상 페이지는 사고 접수 → 사실 확인 → 처리 결과 안내를 제공합니다. 영수증이 없으면 대체 자료를 검토하고, 고객 포장·잔금 지급·당일 미신고만으로 일괄 배제하지 않습니다. 실제 계약서와 현행 표준약관을 확인하고, 일부 분실·훼손의 통지 기준·은폐 등 예외·별도 책임 기간을 구분해야 합니다. 홈페이지가 표준약관 자동 적용이나 보험 가입을 뜻하지 않습니다.

[공식 자료 확인 현황](docs/SOURCES.md)의 외부 원문은 네트워크 제한으로 현행 내용을 확인하지 못했습니다. 실제 사업정보·계약·개인정보 처리 조건을 확정한 뒤 온라인 접수와 광고를 개시하세요.
