# Korea Working Visa (KWV)
**외국인 계절근로자 통합 관리 플랫폼**

## 프로젝트 개요
한국 지자체의 외국인 계절근로자 TO(배정) 관리를 위한 종합 플랫폼입니다.
MOU 협정 관리, 근로자 출퇴근·위치추적·포인트제·AI 이상감지 등을 통해 지자체 담당자에게 플랫폼의 가치를 입증합니다.

- **버전**: v2.0.20260214
- **상태**: v2.0 완료 (전체 Phase 1-9 + 구인구직 + 관리자관리 + 테마)
- **스택**: FastAPI + Vanilla JavaScript + MariaDB
- **운영사**: 글로벌워크센터 (대표: 김성식)

## 주요 기능

### v2.0 - 대시보드 재구조화 + 구인구직 + 테마 (v2.0.20260214)
- **메뉴 재구조화**: 7개 그룹 (시스템설정, 지자체, 근로자관리, 근로자, 리포트&AI, AI Helper)
- **구인 관리**: CRUD (등록/수정/삭제/목록), 비자/지자체 필터, 상태 관리
- **구직 목록**: 카드 그리드 레이아웃, 비자/지자체 필터
- **관리자 관리**: CRUD (추가/수정/비활성화), 등급 관리 (Super Admin 전용)
- **테마 프리셋**: 7종 (블루/그린/퍼플/오렌지/틸/로즈/슬레이트) + 커스텀 색상
- **다크모드 수정**: 헤더 제목, 메뉴 드롭다운 어두운 배경
- **유저 드롭다운 확장**: 내 프로필, 개인 설정 접근

### Phase 1-9 완료 기능
- Phase 1: 시스템 설정 + 지자체 등록
- Phase 2: 회원가입 승인 워크플로우
- Phase 3: 대시보드 차트 + MOU 협정 관리
- Phase 4: 출퇴근 시스템 + QR 체크인 (GPS)
- Phase 5: 활동일지 + 포인트 시스템
- Phase 6: 상담일지
- Phase 7: 리포트 + Excel/PDF 내보내기
- Phase 8: AI 이상감지 + 알림
- Phase 9: 보험 관리
- v1.10: 공지사항 (전체/지자체별)

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
**버전**: v2.0.20260214
**마지막 업데이트**: 2026-02-14
