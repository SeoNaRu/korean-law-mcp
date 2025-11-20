#!/bin/bash
# 서버 재시작 스크립트 (Linux/Mac용)
# 포트 8096이 사용 중이면 프로세스를 종료하고 서버를 다시 시작합니다

echo "========================================"
echo "Korean Law MCP Server 재시작 스크립트"
echo "========================================"
echo ""

PORT=8096

# 포트 8096 사용 중인 프로세스 확인
echo "[1/3] 포트 $PORT 사용 중인 프로세스 확인 중..."

PID=$(lsof -ti:$PORT 2>/dev/null)

if [ ! -z "$PID" ]; then
    echo "  발견된 프로세스: PID=$PID"
    echo "  프로세스 종료 중..."
    kill -9 $PID 2>/dev/null
    sleep 2
    echo "  프로세스 종료 완료"
    echo ""
else
    echo "  포트 $PORT 사용 중인 프로세스 없음"
    echo ""
fi

# 포트가 해제되었는지 확인
if lsof -ti:$PORT >/dev/null 2>&1; then
    echo "[경고] 포트 $PORT가 아직 사용 중입니다. 수동으로 확인해주세요."
    echo ""
else
    echo "[2/3] 포트 $PORT 해제 확인 완료"
    echo ""
fi

# 서버 시작
echo "[3/3] 서버 시작 중..."
echo ""

# HTTP_MODE 환경 변수 설정
export HTTP_MODE=1

# 서버 실행
echo "서버 실행 명령: python -m src.main"
echo "포트: $PORT"
echo "종료하려면 Ctrl+C를 누르세요"
echo ""
echo "========================================"
echo ""

python -m src.main

