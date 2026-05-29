# planner.py

import json
import re

from llm_client import ask_llm, extract_json_from_text


def normalize_gender(gender):
    if gender is None:
        return None

    gender = str(gender).strip()

    if gender in ["여성", "여자", "여", "female", "Female", "F"]:
        return "여자"

    if gender in ["남성", "남자", "남", "male", "Male", "M"]:
        return "남자"

    return None


def normalize_int(value):
    if value is None:
        return None

    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def infer_age_range_from_text(user_request):
    text = str(user_request)

    decade_match = re.search(r"([2-7]0)대", text)
    if decade_match:
        start = int(decade_match.group(1))
        return start, start + 9

    combo_match = re.search(r"([2-7]0)\s*[~\-]\s*([2-7]0)", text)
    if combo_match:
        start = int(combo_match.group(1))
        end = int(combo_match.group(2)) + 9
        return start, end

    if "5060" in text or "50·60" in text:
        return 50, 69

    if "2030" in text:
        return 20, 39

    if "3040" in text:
        return 30, 49

    return None, None


def infer_gender_from_text(user_request):
    text = str(user_request)

    female_keywords = ["여성", "여자", "워킹맘", "엄마", "맘", "주부", "산모", "직장맘", "어머니"]
    male_keywords = ["남성", "남자", "아빠", "대디", "아버지", "직장인 남성"]

    if any(keyword in text for keyword in female_keywords):
        return "여자"

    if any(keyword in text for keyword in male_keywords):
        return "남자"

    return None


def normalize_plan(plan, user_request):
    if not isinstance(plan, dict):
        plan = {}

    item_type = str(plan.get("item_type", "상품/서비스/문구")).strip()
    item_description = str(plan.get("item_description", "")).strip() or user_request
    task_type = str(plan.get("task_type", "소비자 반응 평가")).strip()
    target_description = str(plan.get("target_description", "")).strip()

    if not target_description:
        target_description = "사용자 요청에서 명시된 타깃 고객"

    gender = normalize_gender(plan.get("gender"))
    inferred_gender = infer_gender_from_text(user_request)
    if inferred_gender:
        gender = inferred_gender

    min_age = normalize_int(plan.get("min_age"))
    max_age = normalize_int(plan.get("max_age"))
    inferred_min_age, inferred_max_age = infer_age_range_from_text(user_request)
    if inferred_min_age is not None:
        min_age = inferred_min_age
        max_age = inferred_max_age

    sample_size = normalize_int(plan.get("sample_size", 3))
    if sample_size is None:
        sample_size = 3
    sample_size = max(1, min(sample_size, 5))

    panel_strategy = str(plan.get("panel_strategy", "타깃 조건에 맞는 동질적 패널")).strip()

    fgi_questions = plan.get("fgi_questions", [])
    if not isinstance(fgi_questions, list) or not fgi_questions:
        fgi_questions = [
            "이 상품/서비스/문구를 처음 봤을 때 어떤 인상을 받는가?",
            "가장 매력적으로 느껴지는 요소는 무엇인가?",
            "구매 또는 이용을 망설이게 하는 요소는 무엇인가?",
            "실제로 어떤 상황에서 구매하거나 이용할 것 같은가?",
            "더 설득력 있게 전달하려면 어떤 메시지가 필요한가?",
        ]

    fgi_questions = [str(question).strip() for question in fgi_questions if str(question).strip()][:5]

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
        "fgi_questions": fgi_questions,
    }


PLAN_SCHEMA_HINT = """
{
  "item_type": "상품/서비스/광고 문구/정책/앱/브랜드 콘셉트 중 적절한 유형",
  "item_description": "분석 대상 설명",
  "task_type": "분석 목적",
  "target_description": "타깃 고객 설명",
  "gender": "여자 또는 남자 또는 null",
  "min_age": 30,
  "max_age": 39,
  "sample_size": 3,
  "panel_strategy": "패널 구성 전략",
  "fgi_questions": ["질문 1", "질문 2", "질문 3", "질문 4", "질문 5"]
}
"""


def plan_research_request(user_request):
    prompt = f"""
너는 소비자 리서치 프로젝트를 설계하는 Research Planner Agent다.
사용자의 요청을 읽고, 한국형 페르소나 패널 기반 소비자 반응 시뮬레이션 실행 계획을 JSON 객체 하나로만 출력하라.

[사용자 요청]
{user_request}

[해야 할 일]
1. 분석 대상이 무엇인지 파악한다.
2. 분석 목적을 분류한다.
3. 타깃 고객 설명을 추출한다.
4. 성별과 나이 조건을 추론한다.
5. 페르소나 패널 구성 전략을 정한다.
6. 분석 목적에 맞는 FGI 질문 5개를 만든다.

[중요 규칙]
- 반드시 JSON 객체 하나만 출력한다.
- markdown 코드블록, 주석, 설명 문장을 절대 출력하지 않는다.
- 성별은 "여자", "남자", null 중 하나로 쓴다.
- 나이 범위를 알 수 없으면 min_age와 max_age는 null로 둔다.
- sample_size는 기본 3으로 설정한다. 최대 5까지 가능하다.
- FGI 질문은 분석 대상과 분석 목적에 직접 관련된 질문이어야 한다.

[출력 JSON 스키마]
{PLAN_SCHEMA_HINT}
"""

    raw = ""
    try:
        raw = ask_llm(prompt, temperature=0.0, json_mode=True)
        plan = extract_json_from_text(raw)
        return normalize_plan(plan, user_request)
    except Exception as e:
        print("\n실행 계획 생성 중 문제가 발생했습니다.")
        print("원인:", e)
        print("LLM 원본 응답:")
        print(raw)
        return normalize_plan({}, user_request)
