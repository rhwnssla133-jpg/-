# 새 Google 스프레드시트 + 내 이메일 알림 연결

구조: **홈페이지 → Netlify Forms 접수 원본 → Netlify `submission-created` 함수 → Google Apps Script → Google Sheets 기록 + 운영자 이메일 알림**.

코드는 작성되어 있지만 **아직 실제 Google 계정·시트·Netlify 사이트와 연결되지 않았습니다.** 실제 행 생성과 메일 수신은 계정 설정 후 검증해야 합니다. 현재 홈페이지의 온라인 접수 잠금도 유지되어 있습니다. 이 코드가 있는 것만으로 접수가 열리거나 메일이 발송되지는 않습니다.

## 시트 생성과 테스트 메일을 한 번에 준비하기

시트를 아직 만들지 않았다면 [Apps Script 새 프로젝트](https://script.google.com/home/start)에서 시작해도 됩니다. [Code.gs 전체](../google-apps-script/Code.gs)를 붙여넣어 저장하고 **`setupAndSendTest` → 실행**을 선택합니다. 본인 Google 계정으로 권한을 승인하면 고객명단 시트를 만들고, 본인 이메일로 테스트 알림과 시트 주소를 보냅니다. 기존 연결 시트가 있으면 재사용하며 반복 실행해도 새 시트를 계속 만들지 않습니다. 이미 구글 시트에서 연 Apps Script라면 그 시트를 사용합니다.

수신 주소를 바꾸려면 **프로젝트 설정 → 스크립트 속성 → `ALERT_EMAIL`**에 직접 입력하세요. 비밀번호나 SMTP 설정은 필요하지 않습니다. 테스트 메일에는 비밀키와 고객 정보가 들어가지 않습니다. 이 단계는 시트 준비·메일 단독 테스트이며, 홈페이지 자동 연결에는 아래 웹 앱 배포·Netlify 설정이 필요합니다.

독립형 프로젝트에서 만든 시트에는 관리 메뉴가 자동으로 생기지 않습니다. 이 경우 실패 메일 재전송은 Apps Script 편집기에서 `retryFailedNotifications`를 직접 실행합니다. 구글 시트의 확장 프로그램에서 연 바인딩 프로젝트는 시트의 연동 메뉴를 사용할 수 있습니다.

운영 주소는 사용자가 제공한 `https://helpful-granita-0cfa57.netlify.app`로 설정했습니다. 이 환경의 프록시가 해당 사이트 읽기를 403으로 차단하여 현재 배포 내용과 GitHub 자동 배포 연결 여부는 확인하지 못했습니다.

사용자가 전달한 Apps Script `/exec` 주소도 `config.json`의 `integrations.googleSheets.webAppUrl`에 반영했습니다. 주소는 공개 연결 정보이며 비밀키가 아닙니다. Netlify에 `GOOGLE_APPS_SCRIPT_URL`을 따로 등록하지 않으면 이 주소를 사용합니다. 실제 Google 배포 상태 조회는 현재 프록시 403으로 확인하지 못했고, 주소를 반영한 것만으로 연결 완료라고 보고하지 않습니다.

## 준비할 것

- 알림받을 **본인 Google 계정**으로 만든 새 Google 스프레드시트.
- GitHub 저장소 `rhwnssla133-jpg/-`를 연결한 Netlify 사이트.
- 원래 홈페이지의 사업정보·개인정보·국외이전 미확정 항목 확인.

**정적 ZIP만 끌어다 올린 사이트에는 Netlify Functions가 배포되지 않습니다.** 이번 연동은 Netlify에서 GitHub 저장소를 연결해 배포하세요. 같은 사이트를 Git 연동으로 전환할 수 있는지 현재 계정의 배포 설정을 확인합니다. Git 연결은 되어 있어도 실제 Functions 목록과 이벤트 실행을 확인해야 합니다.

## 1. Google 스프레드시트 만들기

빈 고객명단 템플릿을 사용하려면 먼저 [고객명단 XLSX](https://github.com/rhwnssla133-jpg/-/raw/refs/heads/main/templates/ok-express-customer-list.xlsx)를 내려받으세요. Google 스프레드시트에서 **파일 → 가져오기 → 업로드 → 새 스프레드시트 만들기**로 가져옵니다. `이사 문의`(연동 코드와 동일한 18개 열), `상담 관리`(수동 입력용), `사용 안내` 탭이 있습니다. 실제 고객이나 예시 고객은 없습니다. 가져온 뒤 `이사 문의` 탭 이름과 첫 행 열 이름·순서를 유지하세요. 템플릿만 가져오는 것으로 Apps Script가 설치되거나 메일이 연결되지는 않습니다. 아래 3단계부터 진행합니다.

1. 알림받을 Google 계정으로 로그인해 [새 Google 스프레드시트](https://sheets.google.com)를 만듭니다.
2. 제목은 `OK익스프레스 고객 문의`처럼 정합니다. **공유는 비공개**로 유지하고 필요한 담당자만 접근하게 합니다.
3. 시트 상단 **확장 프로그램 → Apps Script**를 엽니다.
4. 기본 `Code.gs` 내용을 지우고 저장소의 [Code.gs](../google-apps-script/Code.gs) 전체를 붙여넣습니다.
5. Apps Script 프로젝트 설정에서 manifest 표시를 켜 `appsscript.json`이 보이면, 저장소의 [manifest](../google-apps-script/appsscript.json) 내용으로 설정합니다. 시간대는 `Asia/Seoul`, 실행 환경은 V8입니다. 필요한 권한은 스프레드시트, 이메일 전송, 본인 이메일 확인입니다.

## 2. 초기 설정과 메일 단독 테스트

1. 함수 선택 목록에서 **`setup` → 실행**을 선택합니다. 자신이 붙여넣은 코드와 요청 권한을 확인하고 Google 계정의 승인 절차를 진행합니다. 조직 정책으로 배포·권한이 차단되면 관리자에게 확인하며 우회하지 않습니다.
2. 새 `이사 문의` 탭과 열 제목이 생성됩니다. 반복 실행해도 기존 고객 행을 지우거나 비밀키를 바꾸지 않습니다. 열 이름·순서를 임의로 변경하지 마세요.
3. **프로젝트 설정 → 스크립트 속성**에서 아래 값이 생성되었는지 확인합니다. 값은 채팅이나 GitHub에 올리지 않습니다.

| 속성 | 의미 |
| --- | --- |
| `SPREADSHEET_ID` | 연결할 시트 ID. 초기 설정이 자동 저장하며 기존 값은 재사용 |
| `ALERT_EMAIL` | `setup` 실행자의 Google 이메일. 자동 확인이 안 되면 여기에 실제 수신 주소 직접 입력 |
| `WEBHOOK_SECRET` | 자동 생성된 64자리 키. 나중에 Netlify에 같은 값 입력 |
| `INTEGRATION_ENABLED` | 초기값 `false`. 개인정보 안내 확정과 배포 설정 전에는 그대로 유지 |

4. **`sendTestNotification` → 실행**을 선택합니다. 본인 메일로 `[OK익스프레스] 연동 테스트`가 도착하는지 수신함·스팸함에서 확인합니다. 이 테스트는 고객 행을 만들지 않습니다. Google이 요청을 받아도 실제 수신함 도착까지 보장하지 않으므로 직접 확인해야 합니다.

이메일 주소를 채팅에 따로 보내지 않아도 이 방법으로 본인의 계정을 수신자로 설정할 수 있습니다. Apps Script 웹 앱은 다음 단계에서 반드시 **본인 권한으로 실행**해야 합니다.

## 3. Apps Script 웹 앱 배포

1. Apps Script의 **배포 → 새 배포 → 웹 앱**을 선택합니다.
2. **실행 사용자: 나(소유자)**, **접근할 수 있는 사용자: 모든 사용자**로 설정합니다. 로그인하지 않은 Netlify 서버가 요청할 수 있어야 하며, 아래 코드가 별도로 HMAC 서명을 확인합니다. Google Workspace 정책에 따라 이 배포 옵션이 없으면 해당 계정에서 이 방식은 사용할 수 없습니다.
3. 배포 후 **`https://script.google.com/macros/s/…/exec`** 주소를 복사합니다. `/dev` 테스트 주소를 사용하지 않습니다.
4. 주소를 브라우저에서 열면 `sheetConfigured`, `emailConfigured`, `enabled` 상태만 나옵니다. 실제 이메일·시트 ID·비밀키는 표시하지 않습니다. **열기만으로 시트에 고객을 추가하거나 메일을 보내지 않습니다.** 상태 값이 참이어도 실제 고객 접수나 메일 도착을 검증했다는 의미는 아닙니다.
5. 코드를 수정한 뒤에는 배포 관리에서 새 버전으로 업데이트해야 반영됩니다. 스크립트 속성은 코드에 넣지 않고 설정에서 관리합니다.

## 4. Netlify 서버 설정

Netlify 사이트의 Git 배포 저장소를 연결합니다. `main`, 빌드 명령 `python3 scripts/build.py`, 공개 폴더 `dist`입니다. `netlify.toml`에 함수 폴더와 Node 22 설정을 포함했습니다. Netlify 함수 목록에서 **`submission-created`**가 배포되었는지 확인하세요. 이 예약 이벤트 함수는 Netlify Forms 접수 이벤트를 처리하기 위한 함수입니다. 브라우저 폼이나 Apps Script URL로 직접 접수를 우회하지 않습니다.

Netlify 사이트의 **환경 변수**에 아래 설정을 등록합니다. 배포 주소가 코드에 반영되어 있으므로 URL 변수는 선택입니다. `GOOGLE_WEBHOOK_SECRET`은 보안 값으로 처리하고 Functions 런타임에 제공되게 설정하세요. 코드·브라우저 스크립트·커밋·공개 로그에 넣지 않습니다.

| 변수 | 값 |
| --- | --- |
| `GOOGLE_APPS_SCRIPT_URL` (선택) | 다른 배포 주소로 바꿀 때 등록. 없으면 코드의 `webAppUrl` 사용 |
| `GOOGLE_WEBHOOK_SECRET` | Apps Script 스크립트 속성의 `WEBHOOK_SECRET`과 **동일한 값** |
| `GOOGLE_SHEETS_ENABLED` | 초기에는 `false`. 설정과 개인정보 안내 확인 후 `true` |

서버가 Google로 보내는 요청은 타임스탬프·임의값·내용에 대한 HMAC-SHA256 서명을 포함합니다. Apps Script는 서명이 다르거나 5분 이상 지난 요청을 거부합니다. 키 자체는 요청 본문이나 URL에 보내지 않습니다. 개인 데이터도 URL에 넣지 않습니다.

## 5. 개인정보 안내와 접수 개시

기존 `config.json`의 사업자·담당자·Netlify 국외이전 항목을 먼저 확정합니다. Google 사본 저장과 Gmail 알림으로 처리자가 추가되므로 **별도 Google 처리·국외이전 조건도 확인**해야 합니다.

`integrations.googleSheets`의 다음 값을 실제 확인 후 채웁니다.

- `transfer`: 실제 계약 주체·연락처·국가·관련 재위탁자·이전 항목·시기·방법·목적·보유/삭제/백업 조건·적용 계약 URL·확인일. 개인 Google 계정에 Google Workspace DPA가 당연히 적용된다고 가정하지 마세요. 확인되지 않은 국가·기간을 추정해서 넣지 않습니다.
- `privacyReviewedOn`: 실제 검토일.
- `deliveryConfigured`: 시트·스크립트·Netlify 함수 환경 변수 설정을 확인한 뒤 `true`.
- `requested`: 이 알림 방식을 사용하려면 `true`.

`requested: true`로 빌드하면 개인정보처리방침에 Google 처리 안내 표가 추가되고, 미확정 항목이 있으면 온라인 접수가 계속 잠깁니다. 필수 수집 동의·선택 동의·국외이전 동의와 새 동의문 버전을 함께 확인합니다. 선택 동의 없는 선택정보는 Google로도 보내지 않습니다.

Google 방식을 선택하면 기존 `operation.emailNotificationConfigured` 확인 대신 Google 설정·고지 확인을 요구합니다. Netlify 공식 네이버메일 알림도 남겨 두면 두 경로로 알림이 올 수 있습니다. 불필요한 기존 알림은 Netlify 계정에서 직접 조정하고, 남기는 사본은 개인정보 안내·삭제 대상에 포함합니다.

모든 확인 후 Apps Script의 `INTEGRATION_ENABLED`와 Netlify의 `GOOGLE_SHEETS_ENABLED`를 모두 `true`로 바꿉니다. GitHub의 설정 변경을 반영하고 Netlify를 재배포합니다. 기존 `operation.onlineRequested`와 Forms 감지 설정, 실제 도메인 등 접수 필수 조건도 충족해야 합니다. 화면 잠금은 계정 설정의 서버 접근 제어를 대신하지 않으므로 준비 전에는 Forms 감지를 켜지 않습니다.

## 6. 실제 연결 테스트

1. 실제 Netlify HTTPS 주소에서 비민감 테스트 내용으로 견적 문의를 접수합니다.
2. **Netlify Forms에 원본 생성**, **Google 시트에 한 행 추가**, **본인 Google 메일에 알림 수신**을 각각 확인합니다. 프런트 성공창은 Netlify 원본 접수 응답을 뜻하며 Google 전달·메일 수신까지 뜻하지 않습니다.
3. 선택정보 미동의 시 호칭·날짜·요청사항 칸이 비어 있는지 확인합니다. 전화번호의 앞자리 `0`이 유지되어야 합니다.
4. 이메일 제목은 `[OK익스프레스] 새 이사 문의 · <Netlify 접수 ID>`이며 전화번호를 제목에 넣지 않습니다. 내용과 동의 기록은 본문·시트에서 확인합니다.
5. 행의 **알림 상태가 `SENT`**인지 확인합니다. 이는 Google 메일 전송 호출이 성공했다는 뜻이며 수신함 도착까지 증명하지는 않습니다. `FAILED`이면 권한·수신 주소·현재 할당량을 확인하고, 시트를 새로고침해 메뉴 **OK익스프레스 연동 → 실패·미완료 메일 다시 보내기**를 실행합니다. 한 번에 최대 10건이며 자동 무한 재시도는 하지 않습니다.
6. 테스트 기록을 Netlify, 시트, 메일, 휴지통과 별도 사본에서 삭제합니다.

같은 접수 ID를 다시 전달받으면 같은 행을 사용하고 `SENT` 상태면 중복 발송하지 않습니다. 다만 메일 발송 직후 실행이 끊겨 상태 저장이 되지 않는 경우에는 재발송될 수 있습니다. 완전한 1회 배달을 보장하지 않습니다. Google 장애로 행 자체를 저장하지 못하면 Netlify 원본을 확인해 미전달 문의를 복구해야 합니다. Netlify의 이벤트 자동 재시도·보존 조건은 현재 서비스에서 확인하고, 자동 재시도가 있다고 가정하지 않습니다.

## 보유기간·삭제·운영 제한

기존 운영안인 목적 달성 시 파기, 미계약 문의 최대 90일이 **Netlify 원본·Google 시트·이메일 사본**에 모두 적용되도록 운영합니다. 자동 삭제는 추가하지 않았습니다. 시트에서 해당 행을 삭제하고, 별도 복사본·다운로드·공유·버전 기록·제공자 백업의 보유/복구 가능성도 실제 계정 정책으로 검토하세요. 단순 셀 지우기를 모든 사본의 완전 삭제라고 단정하지 마세요. 메일은 휴지통·스팸함·전달된 사본까지 관리합니다.

계약 전환 기록은 실제 법적 근거·항목·기간을 확인해 필요한 범위만 별도 보관합니다. 시트를 공개 공유하거나 고객 명단을 공개 로그에 출력하지 않습니다. 법적 검토·서비스의 국외이전 조건 확인이 끝났다고 인증하지 않습니다.

Google Apps Script와 MailApp에는 계정별 일일 할당량과 실행 제한이 있고, Netlify Forms/Functions도 플랜·접수량 제한이 있습니다. 영구 무료·무제한·즉시 도착을 약속하지 않습니다. 별도 SMTP 비밀번호나 유료 자동화 도구는 필요하지 않습니다.

## 코드·검증·공식 참고자료

- 서버: [submission-created.mjs](../netlify/functions/submission-created.mjs)
- Google 코드: [Code.gs](../google-apps-script/Code.gs), [appsscript.json](../google-apps-script/appsscript.json)
- 모의 통합 검사: `node --test tests/google-integration.test.mjs` — 실제 시트·메일로 전송하지 않습니다.
- [Netlify 이벤트 함수](https://docs.netlify.com/build/functions/trigger-on-events/)
- [Apps Script 웹 앱 배포](https://developers.google.com/apps-script/guides/web)
- [MailApp](https://developers.google.com/apps-script/reference/mail/mail-app)
- [Apps Script 할당량](https://developers.google.com/apps-script/guides/services/quotas)

기준일 2026-10-19. 이 환경에서는 위 공식 사이트 읽기 요청이 프록시 403으로 차단되어 현재 서비스 화면·원문을 확인하지 못했습니다. 실제 계정에서 배포일 문서와 동작을 확인해야 합니다. 사용자 계정의 실제 권한 승인·웹 앱 배포·환경 변수 등록·Forms 이벤트 실행·시트 행 생성·메일 수신은 아직 실행하지 않았습니다.
