# ZIP 홈페이지 → Google 고객명단 + Gmail 알림

이 버전은 **Netlify에는 ZIP만 업로드**하고, Google이 문의 입력·시트 저장·메일 발송을 담당합니다. GitHub 연결이나 Netlify 함수 배포를 진행할 필요가 없습니다.

고객이 홈페이지 안의 Google 문의창에 입력 → Google 스프레드시트 `이사 문의`에 저장 → 운영자의 Google 이메일로 새 문의 알림을 보냅니다. 홈페이지는 Google의 **저장 완료 응답을 받은 뒤** 접수 성공을 표시합니다. 저장과 메일은 별개이므로 실제 수신함까지 확인해야 합니다.

## 1. 기존 Google 코드 교체

이미 만든 Google 시트와 Apps Script 프로젝트를 사용하세요. 새 프로젝트를 만들 필요는 없습니다.

1. Google 스프레드시트에서 **확장 프로그램 → Apps Script**를 엽니다. 독립형 프로젝트라면 기존 Apps Script 탭을 엽니다.
2. [새 Code.gs 전체 보기](https://github.com/rhwnssla133-jpg/-/blob/main/google-apps-script/Code.gs)를 엽니다. GitHub의 복사 버튼 또는 Raw 화면에서 전체 코드를 복사합니다.
3. Apps Script 왼쪽의 **Code.gs**를 누르고 기존 내용을 전부 선택해 새 코드로 교체한 뒤 저장합니다. HTML 파일은 별도로 만들지 않습니다.
4. 톱니바퀴 **프로젝트 설정 → appsscript.json 매니페스트 파일 표시**를 켭니다. 편집기에서 [appsscript.json](../google-apps-script/appsscript.json)의 내용을 적용해 시간대·V8·필요 권한을 맞춥니다. 기존 프로젝트에 다른 기능이 있으면 별도 사본에서 검토 후 적용하세요.
5. 편집기 상단 함수 목록에서 **setupAndSendTest**를 선택하고 **실행**합니다. 본인 Google 계정으로 요청된 시트·메일 권한을 확인하고 승인합니다.
6. 본인 Google 메일함의 **[OK익스프레스] 연동 테스트** 메일을 엽니다. 본문에 고객명단 시트 주소가 들어 있습니다. 받은편지함·스팸함을 모두 확인하세요.

`setupAndSendTest`는 기존 `SPREADSHEET_ID`를 우선 사용하고, 없으면 연결된 시트 또는 새 시트를 사용합니다. 기존 행을 지우지 않으며, 첫 행의 제목·순서가 다르면 오류로 중단합니다. 기존 시트 `이사 문의`의 A~R열을 임의로 바꾸지 마세요.

**초기 수신자는 실행한 Google 계정 이메일**입니다. 기존 `ALERT_EMAIL` 속성이 있으면 그 값을 유지합니다. 다른 본인 Google 주소로 받고 싶으면 **프로젝트 설정 → 스크립트 속성 → ALERT_EMAIL**을 수정하고 `sendTestNotification`을 실행하세요. 홈페이지 푸터의 네이버 문의 메일은 이 수신 설정과 별개입니다. Gmail 앱의 기기 푸시 알림은 휴대전화 Gmail 앱에서도 별도로 켜야 합니다.

빈 고객명단 파일을 먼저 사용하려면 [XLSX 템플릿 다운로드](https://github.com/rhwnssla133-jpg/-/raw/refs/heads/main/templates/ok-express-customer-list.xlsx) → Google 시트 **파일 → 가져오기 → 업로드**를 이용하세요. 자동 설정으로 만든 시트는 `이사 문의` 탭만 생성하며, XLSX의 `상담 관리`는 선택적인 수동 관리 탭입니다.

## 2. 스크립트 속성 확인

Apps Script의 **프로젝트 설정 → 스크립트 속성**에서 확인합니다. 값을 채팅이나 공개 파일에 올리지 마세요.

| 속성 | 용도 |
| --- | --- |
| `SPREADSHEET_ID` | 자동 설정한 실제 고객명단 시트 ID |
| `ALERT_EMAIL` | 알림받을 본인 Google 이메일 |
| `FORM_TOKEN_KEY` | 새 코드가 자동 생성하는 서버 내부 값. 수정하거나 홈페이지에 넣지 않음 |
| `SITE_ORIGIN` | `https://helpful-granita-0cfa57.netlify.app` — 끝에 경로 없이 실제 홈페이지 주소 |
| `INTEGRATION_ENABLED` | 접수 서버 사용 여부. 기존에 true로 설정했다면 유지될 수 있음 |
| `PUBLIC_FORM_CONFIRMED` | **새로 추가됨. 기본 false.** 사업·개인정보 안내 확정 후 true로 변경 |
| `MAX_DAILY_INQUIRIES` | 기본 40. 한국 시간 기준 하루 신규 접수 상한. 1~100 범위 |

초기 설정과 테스트 메일은 공개 접수를 켜지 않아도 가능합니다. 신규 접수는 두 스위치가 모두 `true`여야 합니다. 기존 방식의 `WEBHOOK_SECRET`과 Netlify의 `GOOGLE_WEBHOOK_SECRET`, `GOOGLE_SHEETS_ENABLED`는 **새 코드에서 사용하지 않습니다**. Google 내부 자동 생성 값은 Netlify로 복사하지 않습니다.

관리자 초기 설정·테스트 메일·실패 메일 재전송은 본인 Google 계정의 편집기 또는 시트 메뉴에서 실행합니다. 익명 방문자의 같은 함수 호출은 거부합니다.

## 3. 기존 웹 앱을 새 버전으로 배포

코드 저장만으로 현재 공개된 웹 앱이 바뀌지 않습니다.

1. Apps Script 오른쪽 위 **배포 → 배포 관리**를 누릅니다.
2. 기존 웹 앱 배포를 선택하고 연필 모양 **수정**을 누릅니다.
3. 버전을 **새 버전**으로 선택합니다.
4. 실행 사용자는 **나**, 액세스 권한은 고객이 로그인 없이 사용할 수 있는 **모든 사용자**로 설정하고 **배포**합니다. 조직 계정에서 공개 사용이 제한되면 관리자 정책을 확인해야 합니다.
5. 기존 배포를 수정하면 같은 `/exec` 주소를 유지합니다. 이미 제공한 주소를 홈페이지 설정에 넣어 두었습니다.

```text
https://script.google.com/macros/s/AKfycbxnTt2a9XHONplzfDfP5y4_FHbjU8LWZ1ujTI8ZcA8xa5Gvc2Tizep72SaeXShJglsf/exec
```

새 코드의 기본 주소를 열면 **문의창**이 나옵니다. 설정 상태를 확인하려면 주소 끝에 **?status=1**을 붙입니다. 새 코드라면 `mode`는 `direct-google-form`입니다. 상태 화면에는 이메일·시트 ID·내부 키를 표시하지 않습니다. `enabled:false`면 두 스위치와 초기 설정을 확인하세요. 개인정보 준비 전의 false는 정상입니다.

`service: OK Express 문의 수신자` 같은 예전 JSON만 나오면 아직 **이전 버전**입니다. 배포 관리에서 새 버전 선택을 다시 확인하세요. `/dev` 주소나 로그인 후 리디렉션된 `script.googleusercontent.com` 주소를 홈페이지에 넣지 않습니다.

다른 `/exec` 주소를 새로 만들었다면 `config.json`의 `integrations.googleSheets.webAppUrl`을 바꾸고 홈페이지를 다시 빌드해야 합니다.

## 4. 홈페이지 설정과 Netlify ZIP

현재 ZIP은 사업자 상세정보·담당자·국외이전 조건이 미확정이라 전화 문의 상태입니다. 최초 제작 요청에 따라 사실을 만들거나 미확정 안내로 개인정보를 접수하지 않도록 잠갔습니다. 코드는 준비되었지만 ZIP 업로드만으로 Google 계정 설정까지 완료되지는 않습니다.

`config.json`에 다음 실제 정보를 반영합니다. 편집이 어렵다면 확인한 정보를 정리해 사이트 제작 담당자에게 전달해 ZIP 재생성을 요청하세요. 키·비밀번호는 전달하지 않습니다.

- `business`의 대표자·등록번호·주소·허가·운영시간·보험 현황.
- `privacy`의 담당자·부서·삭제 절차 확인·검토일.
- `integrations.googleSheets.transfer`의 실제 수탁 법인·연락처·처리 국가·재위탁·이전 항목·시기·방법·목적·보유/삭제/백업 조건·적용 문서 URL·확인일. 개인 계정에 Workspace 계약이 당연히 적용된다고 가정하거나 임의 국가를 넣지 않습니다.
- `site.effectiveDate`, `site.policyVersion`, 실제 `site.url`.
- `operation.contractAndCompensationReviewedOn`, Google의 `privacyReviewedOn`.
- 계정 설정 확인 후 Google의 `deliveryConfigured:true`, 공개 개시 시 `operation.onlineRequested:true`.

확정한 안내가 실제 홈페이지에 게시되는 시점에 Google의 `INTEGRATION_ENABLED`와 `PUBLIC_FORM_CONFIRMED`를 모두 `true`로 바꿉니다. 아래 명령은 홈페이지 ZIP과 같은 설정의 Google 코드를 함께 생성합니다. 동의문 버전 변경 시에도 **Google 새 버전 배포와 Netlify 재업로드를 함께** 해야 합니다.

```sh
python3 scripts/package.py
```

빌드 결과 `online inquiry: ENABLED`를 확인하고, 새로 생성된 **Code.gs를 Google에 적용해 새 버전 배포**한 다음 루트 `ok-express-netlify.zip`을 업로드합니다. `LOCKED`이면 출력된 누락 키를 확인하세요. 기본 제공 파일에는 테스트용 사업정보나 합성 고객 기록이 없습니다.

Netlify에서 기존 사이트 → **Deploys** → 수동 업로드 영역을 이용합니다. ZIP을 직접 받지 않으면 압축을 풀어 `index.html`이 최상단인 폴더를 올립니다. **Link repository, Functions, Forms 메뉴는 새 방식의 필수 단계가 아닙니다.** 정적 ZIP에는 Google 서버 코드가 포함되지 않으며 Google 코드 배포는 3단계에서 따로 진행합니다.

## 5. 실제 접수와 메일 확인

공개 개시 전 관리되는 시험 단계에서 다음을 확인합니다. 이 저장소의 자동 검사는 실제 Google 계정 수신을 대신하지 않습니다.

1. 시크릿 창과 휴대전화에서 실제 Netlify 홈페이지를 엽니다. 로그인 없이 문의창이 나와야 합니다. 인앱 브라우저·타사 쿠키 제한도 확인합니다. 안 열리면 **별도 문의창 열기** 또는 전화 문의를 사용합니다.
2. 본인 연락처와 비민감 시험 내용으로 접수합니다. 필수 동의·국외이전 동의를 확인하고, 선택 동의는 거부한 경우와 동의한 경우를 각각 시험합니다.
3. 성공창의 문의 참조번호와 시트의 `접수 ID`가 같은지 확인합니다. 전화번호 앞자리 0, 지역·서비스·동의문 버전·동의 여부를 확인합니다. 선택 미동의 시 호칭·날짜·요청사항이 비어 있어야 합니다.
4. Google 메일함에서 **[OK익스프레스] 새 이사 문의 · OK-…**를 확인합니다. 제목에는 전화번호가 없고 본문에 문의 내용과 비공개 시트 링크가 있습니다.
5. 시트 `알림 상태`의 `SENT`는 MailApp 전송 호출 성공입니다. 받은편지함 도착을 보증하지 않으므로 실제 메일함·스팸함을 확인합니다.
6. 메일 실패 시 행은 남고 `FAILED`로 표시됩니다. 권한·주소·할당량을 확인한 후 Apps Script에서 `retryFailedNotifications` 실행 또는 시트 새로고침 후 **OK익스프레스 연동 → 실패 메일 다시 보내기**를 사용합니다. 1회 최대 10건입니다.
7. 테스트 문의를 시트·메일·휴지통·관리 기록·사본에서 삭제합니다.

동일 참조번호 재시도는 같은 행을 확인하고 이미 발송했다면 다시 보내지 않습니다. 메일 발송 직후 실행이 중단돼 상태 저장이 안 된 예외에는 재발송될 수 있어 완전한 1회 배달을 보장하지 않습니다. 응답을 못 받으면 고객 화면은 입력을 유지하고 완료를 단정하지 않습니다. 수정한 내용으로 같은 참조번호를 재시도하면 충돌로 거부하므로 이미 저장되었을 가능성을 전화로 확인하세요.

## 운영·삭제와 제한

새 버전은 Netlify Forms에 문의 원본을 저장하지 않습니다. 이전 버전의 접수·알림이 이미 있다면 자동 삭제되지 않으므로 별도로 관리하세요. Netlify 정적 호스팅 접속/보안 기록과 Google 처리 안내는 실제 계정 조건에 맞춰 확정해야 합니다.

목적 달성 시 파기, 미계약 문의 최대 90일은 운영안이며 자동 삭제나 법정기간을 의미하지 않습니다. Google 시트·상담 관리·Gmail·휴지통·다운로드/전달 사본과 실제 버전 기록·백업 정책을 함께 관리합니다. 고객명단은 비공개로 두고 관리자 권한과 다중 인증을 설정합니다.

Google 계정의 Apps Script·MailApp 실제 일일 할당량/실행 제한이 적용됩니다. 코드의 하루 40건 상한과 별개이며, 영구 무료·무제한·즉시 알림을 약속하지 않습니다. 공개 문의창에는 완전한 봇 차단 기능이 없으므로 남용과 일일 제한을 관리하고 장애 시 전화 상담을 유지하세요.

기준일 2026-10-19. 실제 권한 승인·웹 앱 새 버전 배포·시트 기록·Gmail 수신은 이 환경에서 미실행입니다. [검증 보고서](VALIDATION.md)와 [공식 자료 확인 현황](SOURCES.md)을 참고하세요.
