# Changelog

모든 주요 변경 사항은 이 파일에 문서화됩니다.

## [1.0.0] - 2025-11-17

### ✨ 추가
- 법령 검색 기능 (`search_law_tool`)
  - 키워드 기반 법령 검색
  - 페이징 지원
  - 법령ID, 법령명, 소관부처, 공포일자 등 상세 정보

- 법령 상세 조회 (`get_law_detail_tool`)
  - 특정 법령의 전체 조문 조회
  - 조문 번호, 제목, 내용 포함

- 판례 검색 기능 (`search_precedent_tool`)
  - 키워드 기반 판례 검색
  - 법원 필터링 지원
  - 사건명, 사건번호, 선고일자, 판시사항 등

- 판례 상세 조회 (`get_precedent_detail_tool`)
  - 판례 전문 조회
  - 판결요지, 참조조문, 참조판례 포함

- 행정규칙 검색 (`search_administrative_rule_tool`)
  - 행정규칙 키워드 검색
  - 소관부처, 제정일자 정보

- 캐싱 시스템
  - 24시간 TTL 캐시
  - API 호출 최소화

### 🔧 기술 스택
- FastMCP - MCP 프로토콜 구현
- FastAPI - HTTP 엔드포인트 제공
- Pydantic - 데이터 검증
- Requests - HTTP 클라이언트
- Cachetools - 캐싱
- XML Parser - 국가법령정보센터 API 응답 파싱

### 📚 문서
- README.md - 전체 프로젝트 문서
- USAGE_GUIDE.md - 상세 사용 가이드
- QUICK_START.md - 빠른 시작 가이드

### 🐳 배포
- Docker 지원
- Dockerfile 포함

## [Unreleased]

### 계획 중
- [ ] 법령 개정 이력 조회
- [ ] 법령 비교 기능
- [ ] 판례 유사도 분석
- [ ] 자연어 기반 법령 해석
- [ ] 웹 UI 대시보드
- [ ] 통계 및 분석 기능

