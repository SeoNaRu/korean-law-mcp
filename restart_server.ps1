#!/usr/bin/env pwsh
# 서버 재시작 스크립트
# 포트 8096이 사용 중이면 프로세스를 종료하고 서버를 다시 시작합니다

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Korean Law MCP Server 재시작 스크립트" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 포트 8096 사용 중인 프로세스 확인
Write-Host "[1/3] 포트 8096 사용 중인 프로세스 확인 중..." -ForegroundColor Yellow

$port = 8096
$connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue

if ($connections) {
    $processIds = $connections | Select-Object -Unique -ExpandProperty OwningProcess
    
    foreach ($pid in $processIds) {
        try {
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "  발견된 프로세스: PID=$pid, 이름=$($process.ProcessName)" -ForegroundColor Yellow
                Write-Host "  프로세스 종료 중..." -ForegroundColor Yellow
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Write-Host "  프로세스 종료 완료" -ForegroundColor Green
            }
        } catch {
            Write-Host "  프로세스 종료 실패: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    # 프로세스 종료 대기
    Start-Sleep -Seconds 2
    Write-Host ""
} else {
    Write-Host "  포트 $port 사용 중인 프로세스 없음" -ForegroundColor Green
    Write-Host ""
}

# 포트가 해제되었는지 확인
$stillInUse = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($stillInUse) {
    Write-Host "[경고] 포트 $port가 아직 사용 중입니다. 수동으로 확인해주세요." -ForegroundColor Red
    Write-Host ""
} else {
    Write-Host "[2/3] 포트 $port 해제 확인 완료" -ForegroundColor Green
    Write-Host ""
}

# 서버 시작
Write-Host "[3/3] 서버 시작 중..." -ForegroundColor Yellow
Write-Host ""

# HTTP_MODE 환경 변수 설정
$env:HTTP_MODE = "1"

# 서버 실행
try {
    Write-Host "서버 실행 명령: python -m src.main" -ForegroundColor Cyan
    Write-Host "포트: $port" -ForegroundColor Cyan
    Write-Host "종료하려면 Ctrl+C를 누르세요" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    python -m src.main
} catch {
    Write-Host ""
    Write-Host "[오류] 서버 시작 실패: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

