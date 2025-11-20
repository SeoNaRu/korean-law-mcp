#!/usr/bin/env python3
"""
Gemini Function Calling 테스트 스크립트
이 스크립트는 korean-law-mcp 서버의 도구들을 Gemini API를 통해 테스트합니다.
"""
import os
import json
import asyncio
import time
import re
from typing import Optional
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.generative_models import GenerativeModel
from google.api_core import exceptions as google_exceptions

# .env 파일 로드
load_dotenv()

# Gemini API 키 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LAW_API_KEY = os.environ.get("LAW_API_KEY")

if not GEMINI_API_KEY:
    print("[ERROR] GEMINI_API_KEY 환경 변수를 설정해주세요.")
    print("   .env 파일에 GEMINI_API_KEY=your_gemini_api_key 추가")
    exit(1)

if not LAW_API_KEY:
    print("[WARNING] LAW_API_KEY가 설정되지 않았습니다. 일부 기능이 작동하지 않을 수 있습니다.")
    print("   .env 파일에 LAW_API_KEY=your_law_api_key 추가")

# Gemini API 키 설정
if GEMINI_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

if GEMINI_API_KEY:
    try:
        configure_func = getattr(genai, 'configure', None)
        if configure_func:
            configure_func(api_key=GEMINI_API_KEY)
            print("[OK] genai.configure()로 API 키 설정 완료")
    except Exception as e:
        pass

def get_mcp_tools() -> Optional[list]:
    """
    MCP 서버에서 도구 목록을 가져와서 Gemini Function Calling 형식으로 변환합니다.
    """
    import requests
    try:
        response = requests.get("http://localhost:8096/tools", timeout=10)
        response.raise_for_status()
        tools_list = response.json()
        
        # Gemini Function Calling 형식으로 변환
        function_declarations = []
        
        for tool in tools_list:
            tool_name = tool.get("name", "")
            description = tool.get("description", "")
            parameters = tool.get("parameters", {})
            
            # health 도구는 제외 (테스트용이 아님)
            if tool_name == "health":
                continue
            
            # Gemini는 default, minimum, maximum 필드를 지원하지 않으므로 제거
            if isinstance(parameters, dict) and "properties" in parameters:
                for prop_name, prop_value in parameters["properties"].items():
                    if isinstance(prop_value, dict):
                        prop_value.pop("default", None)
                        prop_value.pop("minimum", None)
                        prop_value.pop("maximum", None)
            
            # Gemini 형식으로 변환
            function_declaration = {
                "name": tool_name,
                "description": description,
                "parameters": parameters
            }
            
            function_declarations.append(function_declaration)
        
        return [{
            "function_declarations": function_declarations
        }]
        
    except Exception as e:
        print(f"[WARNING] MCP 서버에서 도구 목록을 가져오지 못했습니다: {str(e)}")
        print("   하드코딩된 도구 목록을 사용합니다.")
        return None


# Function Calling을 위한 도구 정의 (Gemini 형식)
# MCP 서버에서 동적으로 가져오거나, fallback으로 하드코딩된 목록 사용
TOOLS = [
    {
        "function_declarations": [
            {
                "name": "search_law_tool",
                "description": "법령을 키워드로 검색합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "검색할 법령 키워드 (예: '민법', '상법', '근로기준법')"
                        },
                        "page": {
                            "type": "integer",
                            "description": "페이지 번호 (기본값: 1)"
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "페이지당 결과 수 (기본값: 10, 최대: 50)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_law_detail_tool",
                "description": "특정 법령의 상세 정보 및 전문(조문)을 조회합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "law_id": {
                            "type": "string",
                            "description": "법령 ID (법령 검색 결과에서 얻은 법령ID)"
                        }
                    },
                    "required": ["law_id"]
                }
            },
            {
                "name": "search_precedent_tool",
                "description": "판례를 키워드로 검색합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "검색할 판례 키워드 (예: '손해배상', '계약', '부당해고')"
                        },
                        "page": {
                            "type": "integer",
                            "description": "페이지 번호 (기본값: 1)"
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "페이지당 결과 수 (기본값: 10, 최대: 50)"
                        },
                        "court": {
                            "type": "string",
                            "description": "법원 구분 (예: '대법원', '헌법재판소')"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_precedent_detail_tool",
                "description": "특정 판례의 상세 정보를 조회합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "precedent_id": {
                            "type": "string",
                            "description": "판례 일련번호 (판례 검색 결과에서 얻은 판례일련번호)"
                        }
                    },
                    "required": ["precedent_id"]
                }
            },
            {
                "name": "search_administrative_rule_tool",
                "description": "행정규칙을 키워드로 검색합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "검색할 행정규칙 키워드"
                        },
                        "page": {
                            "type": "integer",
                            "description": "페이지 번호 (기본값: 1)"
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "페이지당 결과 수 (기본값: 10, 최대: 50)"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
    }
]


def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """
    MCP 서버의 도구를 호출합니다.
    """
    import requests
    
    # API 키를 env에 포함
    request_data = {
        **arguments,
        "env": {
            "LAW_API_KEY": LAW_API_KEY
        }
    }
    
    try:
        response = requests.post(
            f"http://localhost:8096/tools/{tool_name}",
            json=request_data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API 요청 실패: {str(e)}"}


async def test_gemini_function_calling():
    """
    Gemini Function Calling을 테스트합니다.
    """
    print("=" * 80)
    print("Gemini Function Calling 테스트 - Korean Law & Precedent MCP")
    print("=" * 80)
    print()
    
    # MCP 서버에서 도구 목록 가져오기 시도
    mcp_tools = get_mcp_tools()
    tools_to_use = mcp_tools if mcp_tools else TOOLS
    
    if mcp_tools:
        print("[OK] MCP 서버에서 도구 목록을 가져왔습니다.")
    else:
        print("[WARNING] 하드코딩된 도구 목록을 사용합니다.")
    print()
    
    # Gemini 모델 초기화
    try:
        model = GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            tools=tools_to_use
        )
        print("[OK] Gemini 모델 초기화 완료: gemini-2.0-flash-exp")
    except Exception as e:
        print(f"[WARNING] gemini-2.0-flash-exp 모델을 사용할 수 없습니다: {str(e)}")
        try:
            model = GenerativeModel(
                model_name="gemini-1.5-pro",
                tools=tools_to_use
            )
            print("[OK] Gemini 모델 초기화 완료: gemini-1.5-pro")
        except Exception as e2:
            print(f"[ERROR] Gemini 모델 초기화 실패: {str(e2)}")
            return
    
    print()
    
    # 테스트 쿼리들
    test_queries = [
        "민법을 검색해줘",
        "손해배상 관련 판례를 찾아줘",
        "근로기준법에 대해 알려줘"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"테스트 {i}: {query}")
        print('=' * 80)
        print()
        
        try:
            # 채팅 시작
            chat = model.start_chat()
            
            # 사용자 메시지 전송
            print(f"[USER] 사용자: {query}")
            print()
            
            response = chat.send_message(query)
            
            # 응답 처리
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                # Function Call이 있는지 확인
                if hasattr(candidate, 'content') and candidate.content:
                    parts = candidate.content.parts if hasattr(candidate.content, 'parts') else []
                    
                    function_calls = []
                    for part in parts:
                        if hasattr(part, 'function_call'):
                            function_calls.append(part.function_call)
                    
                    if function_calls:
                        print("[FUNCTION CALL] Function Calls 감지:")
                        for fc in function_calls:
                            # fc.args를 dict로 변환
                            if hasattr(fc.args, 'items'):
                                args_dict = dict(fc.args)
                            elif hasattr(fc.args, '__dict__'):
                                args_dict = fc.args.__dict__
                            else:
                                args_dict = {}
                            
                            print(f"   - {fc.name}({json.dumps(args_dict, ensure_ascii=False, indent=2)})")
                        print()
                        
                        # Function Call 실행
                        for fc in function_calls:
                            tool_name = fc.name
                            
                            # tool_name이 비어있으면 건너뛰기
                            if not tool_name:
                                print(f"[WARNING] Function call name이 비어있습니다. 건너뜁니다.")
                                continue
                            
                            # fc.args를 dict로 변환
                            if hasattr(fc.args, 'items'):
                                arguments = dict(fc.args)
                            elif hasattr(fc.args, '__dict__'):
                                arguments = fc.args.__dict__
                            else:
                                arguments = {}
                            
                            print(f"[CALL] MCP 도구 호출: {tool_name}")
                            result = call_mcp_tool(tool_name, arguments)
                            
                            # 결과를 모델에 전달
                            function_response = {
                                "function_response": {
                                    "name": tool_name,
                                    "response": result
                                }
                            }
                            
                            print(f"[RESULT] 결과 수신 (요약): {str(result)[:200]}...")
                            print()
                            
                            # Function Response를 모델에 전달
                            response = chat.send_message(function_response)
                    
                    # 최종 응답 출력
                    if hasattr(response, 'text'):
                        print("[GEMINI] Gemini 응답:")
                        print(response.text)
                    elif hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content'):
                            if hasattr(candidate.content, 'parts'):
                                text_parts = [p.text for p in candidate.content.parts if hasattr(p, 'text')]
                                if text_parts:
                                    print("[GEMINI] Gemini 응답:")
                                    print("\n".join(text_parts))
                else:
                    print("[GEMINI] Gemini 응답:")
                    if hasattr(response, 'text'):
                        print(response.text)
                    else:
                        print(str(response))
            else:
                print("[GEMINI] Gemini 응답:")
                if hasattr(response, 'text'):
                    print(response.text)
                else:
                    print(str(response))
            
            print()
            time.sleep(1)  # API 호출 간격
            
        except google_exceptions.ResourceExhausted as e:
            print(f"[ERROR] API 할당량 초과: {str(e)}")
            print("   잠시 후 다시 시도해주세요.")
            break
        except Exception as e:
            print(f"[ERROR] 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 80)
    print("테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    # 서버가 실행 중인지 확인
    import requests
    try:
        response = requests.get("http://localhost:8096/health", timeout=5)
        if response.status_code == 200:
            print("[OK] MCP 서버가 실행 중입니다.")
        else:
            print("[WARNING] MCP 서버 응답이 예상과 다릅니다.")
    except Exception as e:
        print("[ERROR] MCP 서버에 연결할 수 없습니다.")
        print("   먼저 다음 명령으로 서버를 실행해주세요:")
        print("   HTTP_MODE=1 python -m src.main")
        print()
        print("   또는 .env 파일에 HTTP_MODE=1 추가 후:")
        print("   python -m src.main")
        exit(1)
    
    print()
    asyncio.run(test_gemini_function_calling())

