# 🚀 빠른 시작 가이드

## 1분 만에 시작하기!

### Step 1: API 키 발급 (무료)

1. [국가법령정보센터 Open API](https://open.law.go.kr/) 접속
2. 회원가입 → 로그인
3. **공동활용 서비스** → **Open API 신청**
4. 즉시 승인 → **인증키(OC)** 복사 ✅

### Step 2: 설치 및 실행

```bash
# 의존성 설치
cd korean-law-mcp
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일을 열고 LAW_API_KEY에 발급받은 키 입력

# 서버 실행
python -m src.main
```

### Step 3: Claude Desktop 연동

Claude Desktop 설정 파일 수정:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "korean-law": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "C:/Users/사용자명/Desktop/news_mcp-main/korean-law-mcp",
      "env": {
        "LAW_API_KEY": "발급받은_API_키"
      }
    }
  }
}
```

Claude Desktop 재시작 후 완료! 🎉

## 사용 예시

```
"민법 제750조 찾아줘"
"부당해고 관련 판례 검색해줘"
"개인정보보호법 상세 내용 알려줘"
```

## 문제 해결

### API 키 오류
→ .env 파일과 claude_desktop_config.json에 키가 올바르게 입력되었는지 확인

### 도구가 안 보임
→ Claude Desktop을 완전히 종료 후 재시작 (트레이에서도 종료)

### 더 자세한 가이드
→ `USAGE_GUIDE.md` 참조

---

Happy Legal Research! ⚖️

