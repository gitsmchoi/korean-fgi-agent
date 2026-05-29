# planner.py

import json
from llm_client import ask_llm


def extract_json_from_text(text):
    """
    LLM 응답에서 JSON 부분만 추출한다.
    모델이 앞뒤에 설명을 붙여도 JSON만 파싱하기 위한 함수.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or start >= end:
        raise ValueError("LLM 응답에서 JSON 객체를 찾지 못했습니다.")

    json_text = text[start:end + 1]
    return json.loads(json_text)


def normalize_gender(gender):
    """
    성별 표현을 데이터셋 필터링에 맞게 정규화한다.
    """
    if gender is None:
        return None

    gender = str(gender).strip()

    if gender in ["여성", "여자", "여"]:
        return "여자"

    if gender in ["남성", "남자", "남"]:
        return "남자"

    return None


def normalize_int(value):
    """
    LLM이 숫자를 문자열로 주거나 null로 줄 때를 대비한다.
    """
    if value is None:
        return None

    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def normalize_plan(plan, user_request):
    """
    LLM이 누락하거나 이상하게 준 값을 기본값으로 보정한다.
    """
    item_type = str(plan.get("item_type", "상품/서비스")).strip()
    item_description = str(plan.get("item_description", "")).strip()
    task_type = str(plan.get("task_type", "소비자 반응 평가")).strip()
    target_description = str(plan.get("target_description", "")).strip()

    if item_description == "":
        item_description = user_request

    if target_description == "":
        target_description = "사용자 요청에서 명시된 타깃 고객"

    gender = normalize_gender(plan.get("gender", None))
    min_age = normalize_int(plan.get("min_age", None))
    max_age = normalize_int(plan.get("max_age", None))

    # 사용자 원문 기반 보정 규칙
    # LLM이 성별/나이를 놓치는 경우를 방지한다.
    request_text = user_request.lower()

    female_keywords = [
        "여성", "여자", "워킹맘", "엄마", "맘", "주부", "산모", "직장맘"
    ]

    male_keywords = [
        "남성", "남자", "아빠", "대디", "직장인 남성"
    ]

    if any(keyword in user_request for keyword in female_keywords):
        gender = "여자"

    if any(keyword in user_request for keyword in male_keywords):
        gender = "남자"

    if "20대" in user_request:
        min_age = 20
        max_age = 29

    if "30대" in user_request:
        min_age = 30
        max_age = 39

    if "40대" in user_request:
        min_age = 40
        max_age = 49

    if "50대" in user_request:
        min_age = 50
        max_age = 59

    if "60대" in user_request:
        min_age = 60
        max_age = 69

    if "5060" in user_request or "50~60" in user_request or "50-60" in user_request:
        min_age = 50
        max_age = 69

    sample_size = normalize_int(plan.get("sample_size", 3))
    if sample_size is None:
        sample_size = 3

    # 로컬 LLM 테스트 속도를 위해 1~5명으로 제한
    sample_size = max(1, min(sample_size, 5))

    panel_strategy = str(plan.get("panel_strategy", "타깃 조건에 맞는 동질적 패널")).strip()

    fgi_questions = plan.get("fgi_questions", [])
    if not isinstance(fgi_questions, list) or len(fgi_questions) == 0:
        fgi_questions = [
            "이 상품/서비스/문구를 처음 봤을 때 어떤 인상을 받는가?",
            "가장 매력적으로 느껴지는 요소는 무엇인가?",
            "구매 또는 이용을 망설이게 하는 요소는 무엇인가?",
            "실제로 어떤 상황에서 구매하거나 이용할 것 같은가?",
            "더 설득력 있게 전달하려면 어떤 메시지가 필요한가?"
        ]

    # 질문은 너무 많으면 모델이 산만해지므로 최대 5개
    fgi_questions = fgi_questions[:5]

    return {
        "item_type": item_type,
        "item_description": item_description,
        "task_type": task_type,
        "target_description": target_description,
        "gender": gender,
        "min_age": min_age,
        "max_age": max_age,
        "sample_size": sample_size,
        "panel_strategy": panel_strategy,
        "fgi_questions": fgi_questions
    }


def plan_research_request(user_request):
    """
    사용자의 자연어 요청을 읽고,
    소비자 반응 시뮬레이션 실행 계획을 JSON 형태로 만든다.
    """
    prompt = f"""
너는 소비자 리서치 프로젝트를 설계하는 Research Planner Agent다.
사용자의 요청을 읽고, 한국형 페르소나 패널 기반 소비자 반응 시뮬레이션 실행 계획을 JSON으로만 출력하라.

[사용자 요청]
{user_request}

[해야 할 일]
1. 분석 대상이 무엇인지 파악한다.
   - 상품, 서비스, 광고 문구, 상세페이지, 정책/공공서비스, 앱, 브랜드 콘셉트 등
2. 분석 목적을 분류한다.
   - 콘셉트 평가, 광고 문구 평가, 상세페이지 평가, 서비스 수용성 평가, 구매 반응 평가 등
3. 타깃 고객 설명을 추출한다.
4. 성별과 나이 조건을 추론한다.
5. 페르소나 패널 구성 전략을 정한다.
6. 분석 목적에 맞는 FGI 질문 5개를 만든다.

[중요 규칙]
- 반드시 JSON만 출력한다.
- markdown 코드블록을 쓰지 않는다.
- 설명 문장을 붙이지 않는다.
- 성별은 "여자", "남자", null 중 하나로 쓴다.
- 나이 범위를 알 수 없으면 min_age와 max_age는 null로 둔다.
- sample_size는 기본 3으로 설정한다. 사용자가 더 많은 패널을 원하면 최대 5까지 가능하다.
- FGI 질문은 분석 대상과 분석 목적에 직접 관련된 질문이어야 한다.
- 향수뿐 아니라 모든 상품/서비스/문구에 적용 가능한 형태로 작성한다.

[출력 JSON 형식]
{{
  "item_type": "상품/서비스/광고 문구/정책/앱/브랜드 콘셉트 중 적절한 유형",
  "item_description": "분석 대상 설명",
  "task_type": "분석 목적",
  "target_description": "타깃 고객 설명",
  "gender": "여자 또는 남자 또는 null",
  "min_age": 30,
  "max_age": 39,
  "sample_size": 3,
  "panel_strategy": "패널 구성 전략",
  "fgi_questions": [
    "질문 1",
    "질문 2",
    "질문 3",
    "질문 4",
    "질문 5"
  ]
}}
"""
    raw = ""
    try:
        raw = ask_llm(prompt, temperature=0.2)
        plan = extract_json_from_text(raw)
        return normalize_plan(plan, user_request)

    except Exception as e:
        print("\n실행 계획 생성 중 문제가 발생했습니다.")
        print("원인:", e)
        print("LLM 원본 응답:")
        print(raw)

        # 실패해도 프로그램이 멈추지 않도록 기본 계획 반환
        return {
            "item_type": "상품/서비스/문구",
            "item_description": user_request,
            "task_type": "소비자 반응 평가",
            "target_description": "사용자 요청에서 명시된 타깃 고객",
            "gender": None,
            "min_age": None,
            "max_age": None,
            "sample_size": 3,
            "panel_strategy": "조건을 특정하지 않은 일반 패널",
            "fgi_questions": [
                "이 상품/서비스/문구를 처음 봤을 때 어떤 인상을 받는가?",
                "가장 매력적으로 느껴지는 요소는 무엇인가?",
                "구매 또는 이용을 망설이게 하는 요소는 무엇인가?",
                "실제로 어떤 상황에서 구매하거나 이용할 것 같은가?",
                "더 설득력 있게 전달하려면 어떤 메시지가 필요한가?"
            ]
        }
