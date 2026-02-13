# Korea Working Visa (KWV)
**외국인 계절근로자 통합 관리 플랫폼**

## 프로젝트 개요
한국 지자체의 외국인 계절근로자 TO(배정) 관리를 위한 종합 플랫폼입니다.
MOU 협정 관리, 근로자 출퇴근·위치추적·포인트제·AI 이상감지 등을 통해 지자체 담당자에게 플랫폼의 가치를 입증합니다.

- **버전**: v1.1.20260213
- **상태**: Phase 1 완료 (시스템 설정 + 지자체 등록)
- **스택**: FastAPI + Vanilla JavaScript + MariaDB
- **운영사**: 글로벌워크센터 (대표: 김성식)

## 주요 기능

### Phase 1 - 시스템 설정 + 지자체 등록 (v1.1.20260213)
- **시스템 설정**: 플랫폼 제목, 승인모드, 포인트 설정, GPS 반경, API 키 관리
- **지자체 CRUD**: 등록/수정/삭제/상세, TO 배정 관리, 지역 필터
- **랜딩 페이지**: 플랫폼 소개, 기능 안내, 프로세스, 통계
- **개인정보처리방침**: 법률 준수 개인정보처리방침 페이지
- **회원가입/로그인**: Google OAuth, 프로필 사진, 파일 업로드, 5개국어

### 예정 기능
- Phase 2: 회원가입 승인 워크플로우 + 근로자-지자체 연결
- Phase 3: 대시보드 차트 + MOU 협정 관리
- Phase 4: 출퇴근 시스템 + QR 체크인 (GPS)
- Phase 5: 활동일지 + 포인트 시스템
- Phase 6: 상담일지
- Phase 7: 리포트 + Excel/PDF 내보내기
- Phase 8: AI 이상감지 + 알림
- Phase 9: 보험 관리

## 파일 구조
```
backend/
  kwv_api.py          # FastAPI 라우터 (모든 KWV API)
  kwv_server.py       # 독립 실행 서버
  file_uploads/       # 업로드 파일 저장소

frontend/
  kwv-landing.html    # 랜딩 페이지
  kwv-login.html      # 로그인
  kwv-register.html   # 회원가입
  kwv-dashboard.html  # 관리자 대시보드
  kwv-privacy.html    # 개인정보처리방침
  kwv-google-callback.html  # Google OAuth 콜백

migrations/
  0005_kwv_enhanced_schema.sql  # 기본 스키마
  0006_system_and_lg.sql        # 시스템설정 + 지자체
```

## 연락처
- **이메일**: eden1191@naver.com
- **전화**: 042-545-1155
- **운영시간**: 평일 09:00~18:00 / 토 10:00~17:00 / 일·공휴일 휴무

---
**버전**: v1.1.20260213
**마지막 업데이트**: 2026-02-13
