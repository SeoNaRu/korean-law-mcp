#!/usr/bin/env python3
"""
Korean Law & Precedent MCP Server using FastMCP
국가법령정보센터 Open API를 활용한 법률/판례 검색 서버
"""
import asyncio
import sys
import os
import logging
from fastmcp import FastMCP
from fastapi import FastAPI
from pydantic import BaseModel, Field
from .tools import (
    search_law, 
    get_law_detail, 
    search_precedent, 
    get_precedent_detail,
    search_administrative_rule
)
from typing import Optional
from dotenv import load_dotenv
from contextlib import contextmanager

# .env 파일 로드
load_dotenv()

# FastAPI / FastMCP 앱 구성
api = FastAPI()
mcp_logger = logging.getLogger("law-mcp")
level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
mcp_logger.setLevel(level)
if not mcp_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    mcp_logger.addHandler(handler)
mcp_logger.propagate = True
mcp = FastMCP()


# Pydantic 모델 정의
class LawSearchRequest(BaseModel):
    query: str = Field(..., description="검색할 법령 키워드")
    page: int = Field(1, description="페이지 번호 (기본값: 1)", ge=1)
    page_size: int = Field(10, description="페이지당 결과 수 (기본값: 10, 최대: 50)", ge=1, le=50)


class LawDetailRequest(BaseModel):
    law_id: str = Field(..., description="조회할 법령 ID")


class PrecedentSearchRequest(BaseModel):
    query: str = Field(..., description="검색할 판례 키워드")
    page: int = Field(1, description="페이지 번호 (기본값: 1)", ge=1)
    page_size: int = Field(10, description="페이지당 결과 수 (기본값: 10, 최대: 50)", ge=1, le=50)
    court: Optional[str] = Field(None, description="법원 구분 (예: '대법원', '헌법재판소')")


class PrecedentDetailRequest(BaseModel):
    precedent_id: str = Field(..., description="조회할 판례 일련번호")


class AdminRuleSearchRequest(BaseModel):
    query: str = Field(..., description="검색할 행정규칙 키워드")
    page: int = Field(1, description="페이지 번호 (기본값: 1)", ge=1)
    page_size: int = Field(10, description="페이지당 결과 수 (기본값: 10, 최대: 50)", ge=1, le=50)


# 실제 구현 함수들
async def search_law_impl(req: LawSearchRequest):
    """법령 검색 구현"""
    try:
        return await asyncio.to_thread(search_law, req.query, req.page, req.page_size)
    except Exception as e:
        return {"error": f"법령 검색 중 오류가 발생했습니다: {str(e)}"}


async def get_law_detail_impl(req: LawDetailRequest):
    """법령 상세 조회 구현"""
    try:
        return await asyncio.to_thread(get_law_detail, req.law_id)
    except Exception as e:
        return {"error": f"법령 상세 조회 중 오류가 발생했습니다: {str(e)}"}


async def search_precedent_impl(req: PrecedentSearchRequest):
    """판례 검색 구현"""
    try:
        return await asyncio.to_thread(
            search_precedent, 
            req.query, 
            req.page, 
            req.page_size, 
            req.court
        )
    except Exception as e:
        return {"error": f"판례 검색 중 오류가 발생했습니다: {str(e)}"}


async def get_precedent_detail_impl(req: PrecedentDetailRequest):
    """판례 상세 조회 구현"""
    try:
        return await asyncio.to_thread(get_precedent_detail, req.precedent_id)
    except Exception as e:
        return {"error": f"판례 상세 조회 중 오류가 발생했습니다: {str(e)}"}


async def search_administrative_rule_impl(req: AdminRuleSearchRequest):
    """행정규칙 검색 구현"""
    try:
        return await asyncio.to_thread(
            search_administrative_rule, 
            req.query, 
            req.page, 
            req.page_size
        )
    except Exception as e:
        return {"error": f"행정규칙 검색 중 오류가 발생했습니다: {str(e)}"}


async def health_impl():
    """서비스 상태 확인 구현"""
    api_key = os.environ.get("LAW_API_KEY", "")
    api_key_status = "설정됨" if api_key else "설정되지 않음"
    return {
        "status": "ok",
        "service": "Korean Law & Precedent MCP Server",
        "environment": {
            "law_api_key": api_key_status,
            "api_key_preview": api_key[:10] + "..." if api_key else "None"
        }
    }


# 일시 환경 변수 적용용 컨텍스트 매니저
@contextmanager
def temporary_env(overrides: dict):
    saved_values = {}
    try:
        for key, value in (overrides or {}).items():
            saved_values[key] = os.environ.get(key)
            if value is not None:
                os.environ[key] = str(value)
        yield
    finally:
        for key, original in saved_values.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original


# HTTP 엔드포인트
@api.get("/health")
async def health_check():
    return await health_impl()


# HTTP 엔드포인트: 도구 호출
@api.post("/tools/{tool_name}")
async def call_tool_http(tool_name: str, request_data: dict):
    mcp_logger.debug("HTTP call_tool | tool=%s request=%s", tool_name, request_data)
    env = request_data.get("env", {}) if isinstance(request_data, dict) else {}

    async def run_sync(func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    try:
        # 크레덴셜 추출
        creds = {}
        if isinstance(env, dict):
            for k in ("LAW_API_KEY", "LAW_API_URL"):
                if k in env:
                    creds[k] = env[k]
        
        if creds:
            masked = dict(creds)
            if "LAW_API_KEY" in masked and masked["LAW_API_KEY"]:
                masked["LAW_API_KEY"] = masked["LAW_API_KEY"][:6] + "***"
            mcp_logger.debug("Applying temp env | %s", masked)

        async def run_with_env(coro_func):
            with temporary_env(creds):
                return await coro_func

        if tool_name == "health":
            return await run_with_env(health_impl())

        if tool_name == "search_law_tool":
            query = request_data.get("query")
            if not query:
                return {"error": "Missing required parameter: query"}
            page = request_data.get("page", 1)
            page_size = request_data.get("page_size", 10)
            return await run_with_env(
                run_sync(search_law, query, page, page_size, request_data)
            )

        if tool_name == "get_law_detail_tool":
            law_id = request_data.get("law_id")
            if not law_id:
                return {"error": "Missing required parameter: law_id"}
            return await run_with_env(
                run_sync(get_law_detail, law_id, request_data)
            )

        if tool_name == "search_precedent_tool":
            query = request_data.get("query")
            if not query:
                return {"error": "Missing required parameter: query"}
            page = request_data.get("page", 1)
            page_size = request_data.get("page_size", 10)
            court = request_data.get("court")
            return await run_with_env(
                run_sync(search_precedent, query, page, page_size, court, request_data)
            )

        if tool_name == "get_precedent_detail_tool":
            precedent_id = request_data.get("precedent_id")
            if not precedent_id:
                return {"error": "Missing required parameter: precedent_id"}
            return await run_with_env(
                run_sync(get_precedent_detail, precedent_id, request_data)
            )

        if tool_name == "search_administrative_rule_tool":
            query = request_data.get("query")
            if not query:
                return {"error": "Missing required parameter: query"}
            page = request_data.get("page", 1)
            page_size = request_data.get("page_size", 10)
            return await run_with_env(
                run_sync(search_administrative_rule, query, page, page_size, request_data)
            )

        return {"error": "Tool not found"}
    except Exception as e:
        mcp_logger.exception("Error in call_tool_http: %s", str(e))
        return {"error": f"Error calling tool: {str(e)}"}


# MCP 도구 정의
@mcp.tool()
async def health():
    """서비스 상태 확인"""
    return await health_impl()


@mcp.tool()
async def search_law_tool(
    query: str,
    page: int = 1,
    page_size: int = 10
):
    """
    법령을 키워드로 검색합니다.
    
    Args:
        query: 검색할 법령 키워드 (예: '민법', '상법', '근로기준법')
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과 수 (기본값: 10, 최대: 50)
    
    Returns:
        검색된 법령 목록
    """
    req = LawSearchRequest(query=query, page=page, page_size=page_size)
    return await search_law_impl(req)


@mcp.tool()
async def get_law_detail_tool(law_id: str):
    """
    특정 법령의 상세 정보 및 전문(조문)을 조회합니다.
    
    Args:
        law_id: 법령 ID (법령 검색 결과에서 얻은 법령ID)
    
    Returns:
        법령의 상세 정보와 조문 내용
    """
    req = LawDetailRequest(law_id=law_id)
    return await get_law_detail_impl(req)


@mcp.tool()
async def search_precedent_tool(
    query: str,
    page: int = 1,
    page_size: int = 10,
    court: Optional[str] = None
):
    """
    판례를 키워드로 검색합니다.
    
    Args:
        query: 검색할 판례 키워드 (예: '손해배상', '계약', '부당해고')
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과 수 (기본값: 10, 최대: 50)
        court: 법원 구분 (예: '대법원', '헌법재판소')
    
    Returns:
        검색된 판례 목록
    """
    req = PrecedentSearchRequest(
        query=query, 
        page=page, 
        page_size=page_size, 
        court=court
    )
    return await search_precedent_impl(req)


@mcp.tool()
async def get_precedent_detail_tool(precedent_id: str):
    """
    특정 판례의 상세 정보를 조회합니다.
    
    Args:
        precedent_id: 판례 일련번호 (판례 검색 결과에서 얻은 판례일련번호)
    
    Returns:
        판례의 상세 정보 (판결요지, 판례내용 등)
    """
    req = PrecedentDetailRequest(precedent_id=precedent_id)
    return await get_precedent_detail_impl(req)


@mcp.tool()
async def search_administrative_rule_tool(
    query: str,
    page: int = 1,
    page_size: int = 10
):
    """
    행정규칙을 키워드로 검색합니다.
    
    Args:
        query: 검색할 행정규칙 키워드
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과 수 (기본값: 10, 최대: 50)
    
    Returns:
        검색된 행정규칙 목록
    """
    req = AdminRuleSearchRequest(query=query, page=page, page_size=page_size)
    return await search_administrative_rule_impl(req)


async def main():
    """MCP 서버를 실행합니다."""
    print("MCP Korean Law & Precedent Server starting...", file=sys.stderr)
    print("Server: korean-law-service", file=sys.stderr)
    print("Available tools: health, search_law_tool, get_law_detail_tool, search_precedent_tool, get_precedent_detail_tool, search_administrative_rule_tool", file=sys.stderr)
    
    try:
        await mcp.run_stdio_async()
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise


if __name__ == "__main__":
    # HTTP 서버로 실행 (uvicorn)
    import uvicorn
    port = int(os.environ.get('PORT', 8096))
    uvicorn.run("src.main:api", host="0.0.0.0", port=port, reload=False)

