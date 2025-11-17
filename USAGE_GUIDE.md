# 🎯 한국 법률/판례 MCP 사용 가이드

## 빠른 시작

### 1. API 키 발급 (5분)

1. [국가법령정보센터 Open API](https://open.law.go.kr/) 접속
2. 회원가입 및 로그인
3. **공동활용 서비스** > **Open API 신청** 클릭
4. 간단한 정보 입력 후 **즉시 승인**
5. **인증키(OC)** 복사

> 💡 **무료**이며, 일일 API 호출 제한이 충분히 넉넉합니다!

### 2. 설치 및 실행 (2분)

```bash
# 1) 의존성 설치
pip install -r requirements.txt

# 2) 환경 변수 설정
cp env.law.example .env
# .env 파일에서 LAW_API_KEY를 발급받은 키로 변경

# 3) 서버 실행
python -m src.law_main
```

### 3. Claude Desktop 연동 (3분)

Claude Desktop 설정 파일 편집:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "korean-law": {
      "command": "python",
      "args": ["-m", "src.law_main"],
      "cwd": "C:/Users/사용자명/Desktop/news_mcp-main",
      "env": {
        "LAW_API_KEY": "발급받은_API_키_입력"
      }
    }
  }
}
```

Claude Desktop 재시작 후 바로 사용 가능! 🎉

## 💬 사용 예시

### 법령 검색

**사용자**: "민법에서 손해배상 관련 조항 찾아줘"

**Claude**:
1. `search_law_tool(query="민법")` 호출
2. 법령ID 확인
3. `get_law_detail_tool(law_id="001122")` 호출
4. 제750조, 제751조 등 손해배상 관련 조문 추출
5. 사용자에게 설명

---

**사용자**: "근로기준법 검색해줘"

**Claude**: 
```
근로기준법을 검색했습니다:

📋 법령명: 근로기준법
🏢 소관부처: 고용노동부
📅 공포일자: 1997-03-13
📅 시행일자: 1997-03-13

이 법은 근로조건의 기준을 정한 법률입니다.
상세 내용을 확인하시겠습니까?
```

### 판례 검색

**사용자**: "부당해고 판례 찾아줘"

**Claude**:
1. `search_precedent_tool(query="부당해고")` 호출
2. 관련 판례 목록 제공
3. 주요 판례 요약 설명

---

**사용자**: "이 계약서 검토해줘" (계약서 첨부)

**Claude**:
1. 계약서 분석
2. 관련 법령 자동 검색
3. 위험 요소 식별
4. 관련 판례 제시

### 법률 자문

**사용자**: "임대차 계약 중도 해지하고 싶은데 위약금이 너무 비싼 것 같아"

**Claude**:
1. `search_law_tool(query="민법 임대차")` - 민법 관련 조항 검색
2. `search_law_tool(query="주택임대차보호법")` - 특별법 확인
3. `search_precedent_tool(query="임대차 위약금")` - 관련 판례 검색
4. 법령과 판례를 종합하여 답변

---

**사용자**: "개인정보보호법 위반 기준이 뭐야?"

**Claude**:
1. `search_law_tool(query="개인정보보호법")` 호출
2. 주요 위반 조항 설명
3. `search_precedent_tool(query="개인정보보호법 위반")` - 실제 판례 제시
4. 위반 기준 및 처벌 내용 설명

## 🎨 고급 활용

### 1. 법령 비교 분석

**사용자**: "민법과 상법의 계약 관련 차이점 알려줘"

**Claude**:
- 민법 계약 조항 조회
- 상법 계약 조항 조회
- 두 법령 비교 분석 제공

### 2. 판례 경향 분석

**사용자**: "최근 5년간 산업재해 관련 판례 경향 분석해줘"

**Claude**:
- 산업재해 관련 판례 검색
- 선고일자 기준 정렬
- 판결 경향 분석 및 통계 제공

### 3. 법률 리서치

**사용자**: "AI 서비스 출시 전 확인해야 할 법률 정리해줘"

**Claude**:
1. 개인정보보호법 검색
2. 정보통신망법 검색
3. 저작권법 검색
4. 관련 조항 및 체크리스트 제공

## 🔧 트러블슈팅

### "API 키가 설정되지 않았습니다" 오류

**원인**: LAW_API_KEY 환경 변수가 설정되지 않음

**해결**:
```bash
# .env 파일 확인
cat .env

# LAW_API_KEY=your_key_here 형식으로 설정되어 있는지 확인
```

### "응답 파싱 실패" 오류

**원인**: API 응답이 XML 형식이 아니거나 API 키가 잘못됨

**해결**:
1. API 키가 올바른지 확인
2. [국가법령정보센터](https://open.law.go.kr/)에서 API 키 상태 확인
3. 로그 레벨을 DEBUG로 변경하여 상세 오류 확인:
   ```bash
   LOG_LEVEL=DEBUG python -m src.law_main
   ```

### "API 요청 실패" 오류

**원인**: 네트워크 문제 또는 API 서버 장애

**해결**:
1. 인터넷 연결 확인
2. [국가법령정보센터 API 상태](https://open.law.go.kr/) 확인
3. 잠시 후 재시도

### Claude Desktop에서 도구가 보이지 않음

**해결**:
1. `claude_desktop_config.json` 파일 경로 확인
2. JSON 형식이 올바른지 확인 (콤마, 따옴표 등)
3. Claude Desktop 완전 종료 후 재시작
4. 로그 파일 확인 (Windows: `%APPDATA%\Claude\logs`)

## 📊 성능 최적화 팁

### 1. 캐시 활용
- 동일한 법령/판례는 24시간 캐싱됨
- 반복 조회 시 즉시 응답

### 2. 페이지 크기 조정
```python
# 빠른 검색 (5개만)
search_law_tool(query="민법", page_size=5)

# 상세 검색 (50개)
search_law_tool(query="민법", page_size=50)
```

### 3. 구체적인 키워드 사용
- ❌ "법" - 너무 광범위
- ✅ "민법 제750조" - 구체적

## 💼 실전 활용 케이스

### 변호사/법무사
```
"이 사건과 유사한 판례 찾아줘"
"이 조항의 해석에 대한 판례는?"
"최근 개정된 법령 있어?"
```

### 기업 법무팀
```
"우리 약관이 전자상거래법에 맞는지 확인해줘"
"근로계약서 검토해줘"
"개인정보처리방침 작성 시 참고할 법령 알려줘"
```

### 스타트업
```
"플랫폼 서비스 관련 법률 리스크 분석해줘"
"이용약관 초안 작성해줘"
"특허 관련 법령 찾아줘"
```

### 일반 사용자
```
"전세 계약 관련 법 알려줘"
"부당해고 당했는데 어떻게 해야 해?"
"소비자 환불 권리에 대해 알려줘"
```

## 🎓 API 상세 가이드

### search_law_tool
```python
# 기본 사용
search_law_tool(query="민법")

# 페이징
search_law_tool(query="민법", page=2, page_size=20)
```

### get_law_detail_tool
```python
# 법령ID는 search_law_tool의 결과에서 확인
get_law_detail_tool(law_id="001122")
```

### search_precedent_tool
```python
# 기본 검색
search_precedent_tool(query="손해배상")

# 법원 필터링
search_precedent_tool(query="손해배상", court="대법원")
```

### get_precedent_detail_tool
```python
# 판례일련번호는 search_precedent_tool의 결과에서 확인
get_precedent_detail_tool(precedent_id="202012345")
```

## 📈 다음 단계

1. ⭐ GitHub Star 주기
2. 🐛 이슈 리포트하기
3. 💡 기능 제안하기
4. 🤝 기여하기

---

**더 궁금한 점이 있으신가요?**

- 📧 이메일: law-mcp@example.com
- 💬 Discord: [링크]
- 📚 문서: [Wiki]

Happy Legal Research! 🎉

