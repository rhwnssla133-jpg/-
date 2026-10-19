# 공식 자료 확인 현황

기준일: 2026-10-19. 아래는 요청문에서 제공한 자료와 구현에 필요한 확인 항목입니다.
현재 환경에서 해당 공식 사이트에 HTTPS 읽기 요청을 했으나 프록시가 모두 `Tunnel connection failed: 403 Forbidden`으로 차단했습니다. 인증서 검증을 해제하거나 차단을 우회하지 않았습니다. 따라서 **현행 원문 확인 완료가 아닙니다.**

| 자료 | 주소 | 남은 확인 |
| --- | --- | --- |
| 영구크린 공개 접수 절차 | https://www.mcygclean.com/service/process.jsp | 공개 흐름 확인. 보험·처리기한은 전용하지 않음 |
| 공정위 이사화물 표준약관 | https://www.ftc.go.kr/www/selectBbsNttView.do?bordCd=201&key=202&nttSn=11148 | 현행 약관, 30일 통지의 범위·은폐 등 예외, 별도 책임 소멸기간 |
| 이사 분쟁 안내 | https://www.easylaw.go.kr/CSP/CnpClsMain.laf?ccfNo=3&cciNo=1&cnpClsNo=1&csmSeq=629&popMenu=ov | 적용 법령·분쟁 기준 |
| 개인정보 수집·이용 | https://www.easylaw.go.kr/CSP/CnpClsMainBtr.laf?ccfNo=2&cciNo=1&cnpClsNo=1&csmSeq=1257&popMenu=ov | 법정 고지 항목과 실제 처리의 일치 |
| 개인정보 보호법 | https://www.law.go.kr/법령/개인정보보호법 | 배포일 현행 제28조의8과 별도 동의 요건, 처리 위탁 |
| Netlify Forms | https://docs.netlify.com/manage/forms/setup/ | 감지 활성화·재배포·정적 필드·POST·honeypot |
| 공식 이메일 알림 | https://docs.netlify.com/manage/forms/notifications/ | Submission notifications, hidden subject 반영, 본문 필드 |
| DPA·재위탁 | https://www.netlify.com/trust-center/ | 실제 계정 DPA, 관련 재위탁자·처리 국가·연락처·삭제/백업 기간 |

다음 직접 주소도 시도했으나 같은 네트워크 차단으로 내용을 확인하지 못했습니다. 공식 현재 위치나 적용 문서라는 보장은 하지 않습니다.

- https://www.netlify.com/legal/data-processing-addendum/
- https://www.netlify.com/legal/sub-processors/
- https://www.netlify.com/privacy/

환경 설정 초안에는 `docs.netlify.com`, `www.netlify.com`, `www.ftc.go.kr`, `www.easylaw.go.kr`, `www.law.go.kr`, `www.mcygclean.com` 읽기용 도메인을 추가했습니다. 초안 저장은 현재 머신의 네트워크 적용이나 환경 게시를 뜻하지 않습니다. 환경 설정을 저장·게시한 뒤 접근 가능 여부를 다시 검증해야 합니다. 법령·사업정보·계정 확인을 마치기 전까지 온라인 접수 잠금을 유지합니다.
