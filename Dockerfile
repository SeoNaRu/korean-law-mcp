# Dockerfile for Korean Law & Precedent MCP Server
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY src/ ./src/
COPY .env* ./

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PORT=8096

# 포트 노출
EXPOSE 8096

# MCP 서버 실행
CMD ["python", "-m", "src.law_main"]

