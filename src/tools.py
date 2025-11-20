# tools.py
"""
한국 법률/판례 검색을 위한 도구 모음
국가법령정보센터 Open API 사용
"""
import os
import logging
import requests
import xml.etree.ElementTree as ET
import time
from cachetools import cached, TTLCache
from typing import Optional, Dict, List
from datetime import datetime

# 기본 API URL
DEFAULT_LAW_API_URL = "https://www.law.go.kr/DRF"

# Logger
logger = logging.getLogger("law-mcp")
level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
logger.setLevel(level)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
logger.propagate = True

# 캐시 설정
law_cache = TTLCache(maxsize=100, ttl=86400)  # 24시간 유지
precedent_cache = TTLCache(maxsize=100, ttl=86400)
detail_cache = TTLCache(maxsize=50, ttl=86400)
# 실패한 요청 캐시 (불필요한 재시도 방지, 5분 유지)
failure_cache = TTLCache(maxsize=200, ttl=300)  # 5분


def get_credentials(arguments: Optional[dict] = None) -> dict:
    """
    환경 변수에서 API 인증 정보를 가져옵니다.
    우선순위: 1) arguments.env, 2) .env 파일
    
    Args:
        arguments: 도구 호출 인자
        
    Returns:
        인증 정보가 담긴 딕셔너리
    """
    api_key = ""
    api_url = DEFAULT_LAW_API_URL
    key_source = "none"
    
    # 우선순위 1: arguments.env에서 받기 (메인 서버에서 받은 키)
    if isinstance(arguments, dict) and "env" in arguments:
        env = arguments["env"]
        if isinstance(env, dict):
            if "LAW_API_KEY" in env:
                api_key = env["LAW_API_KEY"]
                key_source = "arguments.env"
            if "LAW_API_URL" in env:
                api_url = env["LAW_API_URL"]
    
    # 우선순위 2: .env 파일에서 받기 (로컬 개발용)
    if not api_key:
        api_key = os.environ.get("LAW_API_KEY", "")
        if api_key:
            key_source = ".env file"
    
    if not api_url or api_url == DEFAULT_LAW_API_URL:
        api_url = os.environ.get("LAW_API_URL", DEFAULT_LAW_API_URL)
    
    credentials = {
        "LAW_API_KEY": api_key,
        "LAW_API_URL": api_url
    }
    
    # 로깅 (키 마스킹)
    masked_key = credentials["LAW_API_KEY"]
    if masked_key:
        masked_key = masked_key[:6] + "***" + f"({len(masked_key)} chars)"
    logger.debug(
        "Resolved credentials | base_url=%s, api_key=%s, source=%s",
        credentials.get("LAW_API_URL", DEFAULT_LAW_API_URL),
        masked_key or "<empty>",
        key_source
    )
    
    return credentials


def make_request_with_retry(url: str, params: dict, max_retries: int = 3, timeout: int = 30) -> requests.Response:
    """
    네트워크 요청을 재시도 로직과 함께 수행
    
    Args:
        url: 요청 URL
        params: 요청 파라미터
        max_retries: 최대 재시도 횟수
        timeout: 타임아웃 (초)
    
    Returns:
        Response 객체
    
    Raises:
        requests.exceptions.RequestException: 모든 재시도 실패 시
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 1  # 1초, 2초, 3초...
                logger.warning("Request timeout (attempt %d/%d), retrying in %ds...", 
                             attempt + 1, max_retries, wait_time)
                time.sleep(wait_time)
            else:
                logger.error("Request timeout after %d attempts", max_retries)
        except requests.exceptions.ConnectionError as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 1
                logger.warning("Connection error (attempt %d/%d), retrying in %ds...", 
                             attempt + 1, max_retries, wait_time)
                time.sleep(wait_time)
            else:
                logger.error("Connection error after %d attempts", max_retries)
        except requests.exceptions.RequestException as e:
            # 재시도 불가능한 오류 (4xx, 5xx 등)
            logger.error("Request failed (non-retryable): %s", str(e))
            raise
    
    # 모든 재시도 실패
    if last_exception:
        raise last_exception
    else:
        raise requests.exceptions.RequestException("모든 재시도가 실패했습니다.")


def parse_xml_response(xml_text: str) -> Dict:
    """
    XML 응답을 파싱하여 딕셔너리로 변환합니다.
    
    Args:
        xml_text: XML 형식의 응답 텍스트
        
    Returns:
        파싱된 데이터 딕셔너리
    """
    try:
        root = ET.fromstring(xml_text)
        return root
    except ET.ParseError as e:
        logger.error(f"XML 파싱 오류: {str(e)}")
        return None


def _search_law_impl(query: str, page: int, page_size: int, arguments: Optional[dict] = None) -> Dict:
    """
    법령을 키워드로 검색합니다.
    
    Args:
        query: 검색할 키워드
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과 수 (기본값: 10, 최대: 50)
        arguments: 추가 인자
        
    Returns:
        검색 결과 딕셔너리
    """
    logger.debug("search_law called | query=%r page=%s page_size=%s", query, page, page_size)
    
    # 캐시 키 생성 (arguments는 hashable하지 않으므로 제외)
    cache_key = (query, page, page_size)
    
    # 실패 캐시 확인
    if cache_key in failure_cache:
        logger.debug("Failure cache hit, skipping | query=%r", query)
        return failure_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["LAW_API_KEY"]
    base_url = credentials["LAW_API_URL"]
    
    if not api_key:
        error_result = {"error": "API 키가 설정되지 않았습니다. LAW_API_KEY 환경 변수를 설정해주세요."}
        failure_cache[cache_key] = error_result
        return error_result
    
    # API 엔드포인트: 법령검색
    api_url = f"{base_url}/lawSearch.do"
    
    params = {
        "OC": api_key,
        "target": "law",
        "type": "XML",
        "query": query,
        "display": min(page_size, 50),  # 최대 50개
        "page": page
    }
    
    try:
        response = make_request_with_retry(api_url, params, max_retries=3, timeout=30)
        
        logger.debug("Law API response | status=%s", response.status_code)
        
        # XML 파싱
        root = parse_xml_response(response.text)
        if root is None:
            error_result = {"error": "응답 파싱 실패"}
            failure_cache[cache_key] = error_result
            return error_result
        
        # 결과 추출
        laws = []
        for law in root.findall(".//law"):
            law_data = {
                "법령ID": law.findtext("법령ID", ""),
                "법령명": law.findtext("법령명한글", ""),
                "법령명_약칭": law.findtext("법령약칭명", ""),
                "법령구분": law.findtext("법령구분명", ""),
                "소관부처": law.findtext("소관부처명", ""),
                "공포일자": law.findtext("공포일자", ""),
                "공포번호": law.findtext("공포번호", ""),
                "시행일자": law.findtext("시행일자", ""),
                "제개정구분": law.findtext("제개정구분명", "")
            }
            laws.append(law_data)
        
        total_count = root.findtext(".//totalCnt", "0")
        
        result = {
            "total": int(total_count),
            "page": page,
            "page_size": page_size,
            "laws": laws
        }
        
        logger.debug("Law search results | total=%s returned=%d", total_count, len(laws))
        return result
        
    except requests.exceptions.RequestException as e:
        error_msg = f"API 요청 실패: {str(e)}"
        logger.exception("Law API request failed: %s", str(e))
        error_result = {"error": error_msg}
        failure_cache[cache_key] = error_result
        return error_result
    except Exception as e:
        error_msg = f"법령 검색 중 오류 발생: {str(e)}"
        logger.exception("Law search error: %s", str(e))
        error_result = {"error": error_msg}
        failure_cache[cache_key] = error_result
        return error_result


def search_law(query: str, page: int = 1, page_size: int = 10, arguments: Optional[dict] = None) -> Dict:
    """
    법령을 키워드로 검색합니다.
    
    Args:
        query: 검색할 키워드
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과 수 (기본값: 10, 최대: 50)
        arguments: 추가 인자
        
    Returns:
        검색 결과 딕셔너리
    """
    # 캐시 키 생성 (arguments는 hashable하지 않으므로 제외)
    cache_key = (query, page, page_size)
    
    # 캐시 확인
    if cache_key in law_cache:
        logger.debug("Cache hit | query=%r", query)
        return law_cache[cache_key]
    
    # 실제 구현 호출
    result = _search_law_impl(query, page, page_size, arguments)
    
    # 성공한 경우에만 캐시에 저장
    if "error" not in result:
        law_cache[cache_key] = result
    
    return result


def _get_law_detail_impl(law_id: str, arguments: Optional[dict] = None) -> Dict:
    """
    특정 법령의 상세 정보 및 전문을 조회합니다.
    
    Args:
        law_id: 법령 ID (법령 일련번호)
        arguments: 추가 인자
        
    Returns:
        법령 상세 정보 딕셔너리
    """
    logger.debug("get_law_detail called | law_id=%s", law_id)
    
    # 캐시 키 생성
    cache_key = (law_id,)
    
    # 실패 캐시 확인
    if cache_key in failure_cache:
        logger.debug("Failure cache hit, skipping | law_id=%s", law_id)
        return failure_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["LAW_API_KEY"]
    base_url = credentials["LAW_API_URL"]
    
    if not api_key:
        error_result = {"error": "API 키가 설정되지 않았습니다."}
        failure_cache[cache_key] = error_result
        return error_result
    
    # API 엔드포인트: 법령 상세
    api_url = f"{base_url}/lawService.do"
    
    params = {
        "OC": api_key,
        "target": "law",
        "type": "XML",
        "MST": law_id,
    }
    
    try:
        response = make_request_with_retry(api_url, params, max_retries=3, timeout=30)
        
        # XML 파싱
        root = parse_xml_response(response.text)
        if root is None:
            error_result = {"error": "응답 파싱 실패"}
            failure_cache[cache_key] = error_result
            return error_result
        
        # 기본 정보
        law_info = {
            "법령ID": root.findtext(".//법령ID", ""),
            "법령명": root.findtext(".//법령명한글", ""),
            "법령구분": root.findtext(".//법령구분명", ""),
            "소관부처": root.findtext(".//소관부처명", ""),
            "공포일자": root.findtext(".//공포일자", ""),
            "시행일자": root.findtext(".//시행일자", ""),
        }
        
        # 조문 정보
        articles = []
        for article in root.findall(".//조문"):
            article_data = {
                "조문번호": article.findtext("조문번호", ""),
                "조문제목": article.findtext("조문제목", ""),
                "조문내용": article.findtext("조문내용", "")
            }
            articles.append(article_data)
        
        law_info["조문"] = articles
        law_info["조문수"] = len(articles)
        
        logger.debug("Law detail retrieved | law_id=%s articles=%d", law_id, len(articles))
        return law_info
        
    except requests.exceptions.RequestException as e:
        error_msg = f"API 요청 실패: {str(e)}"
        logger.exception("Law detail API request failed: %s", str(e))
        error_result = {"error": error_msg}
        failure_cache[cache_key] = error_result
        return error_result
    except Exception as e:
        error_msg = f"법령 상세 조회 중 오류 발생: {str(e)}"
        logger.exception("Law detail error: %s", str(e))
        error_result = {"error": error_msg}
        failure_cache[cache_key] = error_result
        return error_result


def get_law_detail(law_id: str, arguments: Optional[dict] = None) -> Dict:
    """
    특정 법령의 상세 정보 및 전문을 조회합니다.
    
    Args:
        law_id: 법령 ID (법령 일련번호)
        arguments: 추가 인자
        
    Returns:
        법령 상세 정보 딕셔너리
    """
    # 캐시 키 생성 (arguments는 hashable하지 않으므로 제외)
    cache_key = (law_id,)
    
    # 캐시 확인
    if cache_key in detail_cache:
        logger.debug("Cache hit | law_id=%s", law_id)
        return detail_cache[cache_key]
    
    # 실제 구현 호출
    result = _get_law_detail_impl(law_id, arguments)
    
    # 성공한 경우에만 캐시에 저장
    if "error" not in result:
        detail_cache[cache_key] = result
    
    return result


def search_precedent(query: str, page: int = 1, page_size: int = 10, court: Optional[str] = None, arguments: Optional[dict] = None) -> Dict:
    """
    판례를 키워드로 검색합니다.
    
    Args:
        query: 검색할 키워드
        page: 페이지 번호 (기본값: 1)
        page_size: 페이지당 결과 수 (기본값: 10, 최대: 50)
        court: 법원 구분 (대법원, 헌법재판소 등)
        arguments: 추가 인자
        
    Returns:
        판례 검색 결과 딕셔너리
    """
    # 캐시 키 생성 (arguments는 hashable하지 않으므로 제외)
    cache_key = (query, page, page_size, court)
    
    # 캐시 확인
    if cache_key in precedent_cache:
        logger.debug("Cache hit | query=%r", query)
        return precedent_cache[cache_key]
    
    # 실제 구현 호출
    result = _search_precedent_impl(query, page, page_size, court, arguments)
    
    # 성공한 경우에만 캐시에 저장
    if "error" not in result:
        precedent_cache[cache_key] = result
    
    return result


def _search_precedent_impl(query: str, page: int = 1, page_size: int = 10, court: Optional[str] = None, arguments: Optional[dict] = None) -> Dict:
    """
    판례를 키워드로 검색합니다. (내부 구현)
    
    Args:
        query: 검색할 키워드
        page: 페이지 번호
        page_size: 페이지당 결과 수
        court: 법원 구분 (대법원, 헌법재판소 등)
        arguments: 추가 인자
        
    Returns:
        판례 검색 결과 딕셔너리
    """
    logger.debug("search_precedent called | query=%r page=%s page_size=%s court=%s", 
                 query, page, page_size, court)
    
    # 캐시 키 생성
    cache_key = (query, page, page_size, court)
    
    # 실패 캐시 확인
    if cache_key in failure_cache:
        logger.debug("Failure cache hit, skipping | query=%r", query)
        return failure_cache[cache_key]
    
    credentials = get_credentials(arguments)
    api_key = credentials["LAW_API_KEY"]
    base_url = credentials["LAW_API_URL"]
    
    if not api_key:
        error_result = {"error": "API 키가 설정되지 않았습니다."}
        failure_cache[cache_key] = error_result
        return error_result
    
    # API 엔드포인트: 판례검색
    api_url = f"{base_url}/lawSearch.do"
    
    params = {
        "OC": api_key,
        "target": "prec",  # 판례
        "type": "XML",
        "query": query,
        "display": min(page_size, 50),
        "page": page
    }
    
    try:
        response = make_request_with_retry(api_url, params, max_retries=3, timeout=30)
        
        # XML 파싱
        root = parse_xml_response(response.text)
        if root is None:
            error_result = {"error": "응답 파싱 실패"}
            failure_cache[cache_key] = error_result
            return error_result
        
        # 결과 추출
        precedents = []
        for prec in root.findall(".//prec"):
            prec_data = {
                "판례일련번호": prec.findtext("판례일련번호", ""),
                "사건명": prec.findtext("사건명", ""),
                "사건번호": prec.findtext("사건번호", ""),
                "선고일자": prec.findtext("선고일자", ""),
                "선고": prec.findtext("선고", ""),
                "법원명": prec.findtext("법원명", ""),
                "사건종류명": prec.findtext("사건종류명", ""),
                "판시사항": prec.findtext("판시사항", ""),
                "판결요지": prec.findtext("판결요지", "")
            }
            precedents.append(prec_data)
        
        total_count = root.findtext(".//totalCnt", "0")
        
        result = {
            "total": int(total_count),
            "page": page,
            "page_size": page_size,
            "precedents": precedents
        }
        
        logger.debug("Precedent search results | total=%s returned=%d", total_count, len(precedents))
        return result
        
    except requests.exceptions.RequestException as e:
        error_msg = f"API 요청 실패: {str(e)}"
        logger.exception("Precedent API request failed: %s", str(e))
        error_result = {"error": error_msg}
        failure_cache[cache_key] = error_result
        return error_result
    except Exception as e:
        error_msg = f"판례 검색 중 오류 발생: {str(e)}"
        logger.exception("Precedent search error: %s", str(e))
        error_result = {"error": error_msg}
        failure_cache[cache_key] = error_result
        return error_result


def get_precedent_detail(precedent_id: str, arguments: dict = None) -> Dict:
    """
    특정 판례의 상세 정보를 조회합니다.
    
    Args:
        precedent_id: 판례 일련번호
        arguments: 추가 인자
        
    Returns:
        판례 상세 정보 딕셔너리
    """
    logger.debug("get_precedent_detail called | precedent_id=%s", precedent_id)
    
    credentials = get_credentials(arguments)
    api_key = credentials["LAW_API_KEY"]
    base_url = credentials["LAW_API_URL"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}
    
    # API 엔드포인트: 판례 상세
    api_url = f"{base_url}/lawService.do"
    
    params = {
        "OC": api_key,
        "target": "prec",
        "type": "XML",
        "ID": precedent_id,
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        
        # XML 파싱
        root = parse_xml_response(response.text)
        if root is None:
            return {"error": "응답 파싱 실패"}
        
        # 상세 정보 추출
        prec_info = {
            "판례일련번호": root.findtext(".//판례일련번호", ""),
            "사건명": root.findtext(".//사건명", ""),
            "사건번호": root.findtext(".//사건번호", ""),
            "선고일자": root.findtext(".//선고일자", ""),
            "선고": root.findtext(".//선고", ""),
            "법원명": root.findtext(".//법원명", ""),
            "사건종류명": root.findtext(".//사건종류명", ""),
            "판시사항": root.findtext(".//판시사항", ""),
            "판결요지": root.findtext(".//판결요지", ""),
            "참조조문": root.findtext(".//참조조문", ""),
            "참조판례": root.findtext(".//참조판례", ""),
            "판례내용": root.findtext(".//판례내용", "")
        }
        
        logger.debug("Precedent detail retrieved | precedent_id=%s", precedent_id)
        return prec_info
        
    except requests.exceptions.RequestException as e:
        logger.exception("Precedent detail API request failed: %s", str(e))
        return {"error": f"API 요청 실패: {str(e)}"}
    except Exception as e:
        logger.exception("Precedent detail error: %s", str(e))
        return {"error": f"판례 상세 조회 중 오류 발생: {str(e)}"}


def search_administrative_rule(query: str, page: int = 1, page_size: int = 10, 
                               arguments: dict = None) -> Dict:
    """
    행정규칙을 키워드로 검색합니다.
    
    Args:
        query: 검색할 키워드
        page: 페이지 번호
        page_size: 페이지당 결과 수
        arguments: 추가 인자
        
    Returns:
        행정규칙 검색 결과 딕셔너리
    """
    logger.debug("search_administrative_rule called | query=%r page=%s page_size=%s", 
                 query, page, page_size)
    
    credentials = get_credentials(arguments)
    api_key = credentials["LAW_API_KEY"]
    base_url = credentials["LAW_API_URL"]
    
    if not api_key:
        return {"error": "API 키가 설정되지 않았습니다."}
    
    # API 엔드포인트: 행정규칙 검색
    api_url = f"{base_url}/lawSearch.do"
    
    params = {
        "OC": api_key,
        "target": "admrul",  # 행정규칙
        "type": "XML",
        "query": query,
        "display": min(page_size, 50),
        "page": page
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        
        # XML 파싱
        root = parse_xml_response(response.text)
        if root is None:
            return {"error": "응답 파싱 실패"}
        
        # 결과 추출
        rules = []
        for rule in root.findall(".//admrul"):
            rule_data = {
                "행정규칙ID": rule.findtext("행정규칙ID", ""),
                "행정규칙명": rule.findtext("행정규칙명", ""),
                "소관부처": rule.findtext("소관부처명", ""),
                "제정일자": rule.findtext("제정일자", ""),
                "시행일자": rule.findtext("시행일자", "")
            }
            rules.append(rule_data)
        
        total_count = root.findtext(".//totalCnt", "0")
        
        result = {
            "total": int(total_count),
            "page": page,
            "page_size": page_size,
            "rules": rules
        }
        
        logger.debug("Administrative rule search results | total=%s returned=%d", 
                    total_count, len(rules))
        return result
        
    except requests.exceptions.RequestException as e:
        logger.exception("Administrative rule API request failed: %s", str(e))
        return {"error": f"API 요청 실패: {str(e)}"}
    except Exception as e:
        logger.exception("Administrative rule search error: %s", str(e))
        return {"error": f"행정규칙 검색 중 오류 발생: {str(e)}"}

