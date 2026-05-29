# llm_client.py

import json
import os
import re

import ollama

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


MODEL_NAME = "qwen2.5:3b"
OPENAI_MODEL_NAME = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "너는 한국어 문장력이 좋은 소비자 리서처이자 FGI 분석가다. "
    "응답은 반드시 자연스러운 한국어로 작성한다. "
    "분석 대상과 직접 관련된 내용만 다룬다. "
    "페르소나 설명을 그대로 반복하지 말고, 소비자 반응으로 재해석한다. "
    "어색한 조어, 번역투, 비문을 피한다. "
    "없는 사실을 과도하게 지어내지 않는다. "
    "JSON을 요구받으면 반드시 유효한 JSON 객체 하나만 출력한다."
)


def get_secret(name, default=None):
    value = os.getenv(name)
    if value:
        return value

    try:
        import streamlit as st

        value = st.secrets.get(name)
        return value if value else default
    except Exception:
        return default


def ask_openai(prompt, temperature=0.6, json_mode=False):
    if OpenAI is None:
        raise RuntimeError("openai 패키지가 설치되어 있지 않습니다. requirements.txt에 openai>=1.0.0을 추가하세요.")

    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다. Streamlit Secrets에 값을 추가하세요.")

    model = get_secret("OPENAI_MODEL", OPENAI_MODEL_NAME)
    client = OpenAI(api_key=api_key)

    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as first_error:
        # 일부 최신/특수 모델은 temperature나 response_format 제약이 다를 수 있다.
        if not json_mode:
            raise

        kwargs.pop("response_format", None)
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception:
            kwargs.pop("temperature", None)
            try:
                response = client.chat.completions.create(**kwargs)
            except Exception:
                raise first_error

    return response.choices[0].message.content or ""


def ask_ollama(prompt, temperature=0.6, json_mode=False):
    kwargs = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": temperature},
    }

    if json_mode:
        kwargs["format"] = "json"

    try:
        response = ollama.chat(**kwargs)
    except TypeError:
        kwargs.pop("format", None)
        response = ollama.chat(**kwargs)

    return response["message"]["content"]


def ask_llm(prompt, temperature=0.6, json_mode=False):
    provider = str(get_secret("LLM_PROVIDER", "openai")).strip().lower()

    if provider in ["openai", "auto"]:
        return ask_openai(prompt, temperature=temperature, json_mode=json_mode)

    if provider == "ollama":
        return ask_ollama(prompt, temperature=temperature, json_mode=json_mode)

    raise RuntimeError(f"지원하지 않는 LLM_PROVIDER입니다: {provider}")


def _strip_json_fences(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _remove_trailing_commas(text):
    return re.sub(r",\s*([}\]])", r"\1", text)


def extract_json_from_text(text):
    if not isinstance(text, str):
        raise ValueError("LLM 응답이 문자열이 아닙니다.")

    text = _strip_json_fences(text)

    for candidate in [text, _remove_trailing_commas(text)]:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    decoder = json.JSONDecoder()
    for idx, char in enumerate(text):
        if char != "{":
            continue

        for candidate in [text[idx:], _remove_trailing_commas(text[idx:])]:
            try:
                parsed, _ = decoder.raw_decode(candidate)
                return parsed
            except json.JSONDecodeError:
                pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise ValueError("LLM 응답에서 JSON 객체를 찾지 못했습니다.")

    json_text = _remove_trailing_commas(text[start : end + 1])
    return json.loads(json_text)


def repair_json_response(raw_text, schema_hint):
    repair_prompt = f"""
아래 텍스트를 유효한 JSON 객체 하나로만 고쳐서 출력하라.
설명, markdown, 코드블록은 절대 출력하지 마라.
누락된 필드는 빈 문자열, 빈 배열, 기본 점수 3으로 채워라.

[필수 JSON 구조]
{schema_hint}

[고쳐야 할 텍스트]
{raw_text}
"""
    repaired = ask_llm(repair_prompt, temperature=0.0, json_mode=True)
    return extract_json_from_text(repaired)


def safe_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if value is None:
        return []

    value = str(value).strip()
    return [value] if value else []


def safe_text(value, default=""):
    if value is None:
        return default

    value = str(value).strip()
    return value if value else default


def normalize_journey_map(value):
    default_steps = [
        {
            "stage": "노출",
            "action": "분석 대상을 처음 접한다.",
            "emotion_score": 3,
            "emotion_label": "관심은 있지만 판단 보류",
            "touchpoint": "광고/소개 문구",
            "need": "핵심 혜택을 빠르게 이해하고 싶다.",
            "opportunity": "첫 문장에서 가장 강한 혜택을 제시한다.",
        },
        {
            "stage": "탐색",
            "action": "상세 정보를 확인한다.",
            "emotion_score": 3,
            "emotion_label": "정보를 더 보고 싶음",
            "touchpoint": "상세페이지/후기/검색",
            "need": "근거와 후기를 확인하고 싶다.",
            "opportunity": "신뢰 근거와 실제 사용 사례를 제시한다.",
        },
        {
            "stage": "비교",
            "action": "가격, 대안, 조건을 비교한다.",
            "emotion_score": 3,
            "emotion_label": "망설임",
            "touchpoint": "가격표/비교 정보",
            "need": "내게 맞는 선택인지 확인하고 싶다.",
            "opportunity": "가격, 혜택, 차별점을 명확히 비교해준다.",
        },
        {
            "stage": "결정",
            "action": "구매 또는 이용 여부를 결정한다.",
            "emotion_score": 3,
            "emotion_label": "조건 확인",
            "touchpoint": "결제/신청/가입 화면",
            "need": "불이익 없이 쉽게 시작하고 싶다.",
            "opportunity": "환불, 해지, 체험 조건을 명확히 안내한다.",
        },
        {
            "stage": "공유",
            "action": "사용 후 만족 여부를 주변에 공유한다.",
            "emotion_score": 3,
            "emotion_label": "경험 평가",
            "touchpoint": "후기/SNS/지인 추천",
            "need": "사용 경험이 기대와 맞았는지 확인하고 싶다.",
            "opportunity": "후기 작성, 추천 보상, 재구매 혜택을 제공한다.",
        },
    ]

    if not isinstance(value, list):
        value = []

    normalized = []
    for idx in range(5):
        fallback = default_steps[idx]
        item = value[idx] if idx < len(value) and isinstance(value[idx], dict) else {}

        try:
            emotion_score = float(item.get("emotion_score", fallback["emotion_score"]))
        except (ValueError, TypeError):
            emotion_score = fallback["emotion_score"]

        normalized.append(
            {
                "stage": safe_text(item.get("stage"), fallback["stage"]),
                "action": safe_text(item.get("action"), fallback["action"]),
                "emotion_score": max(1, min(5, emotion_score)),
                "emotion_label": safe_text(item.get("emotion_label"), fallback["emotion_label"]),
                "touchpoint": safe_text(item.get("touchpoint"), fallback["touchpoint"]),
                "need": safe_text(item.get("need"), fallback["need"]),
                "opportunity": safe_text(item.get("opportunity"), fallback["opportunity"]),
            }
        )

    return normalized


def normalize_persona_response(data):
    if not isinstance(data, dict):
        data = {}

    try:
        appeal_score = int(float(data.get("appeal_score", 3)))
    except (ValueError, TypeError):
        appeal_score = 3

    return {
        "persona_story": safe_text(data.get("persona_story")),
        "persona_issue": safe_text(data.get("persona_issue")),
        "first_impression": safe_text(data.get("first_impression")),
        "positive_points": safe_list(data.get("positive_points")),
        "concerns": safe_list(data.get("concerns")),
        "pain_points": safe_list(data.get("pain_points")),
        "needs": safe_list(data.get("needs")),
        "response_tags": safe_list(data.get("response_tags")),
        "appeal_score": max(1, min(5, appeal_score)),
        "appeal_reason": safe_text(data.get("appeal_reason")),
        "usage_context": safe_text(data.get("usage_context")),
        "persuasion_points": safe_list(data.get("persuasion_points")),
        "message_suggestions": safe_list(data.get("message_suggestions")),
        "journey_map": normalize_journey_map(data.get("journey_map")),
        "raw_text": safe_text(data.get("raw_text")),
    }


def fallback_persona_response(raw_text, error=None):
    reason = f"LLM 응답을 JSON으로 구조화하지 못했습니다: {error}" if error else "LLM 응답이 JSON 형식으로 생성되지 않았습니다."

    return {
        "persona_story": "응답을 구조화하는 데 실패했습니다.",
        "persona_issue": "원문 응답 확인이 필요합니다.",
        "first_impression": "응답을 구조화하는 데 실패했습니다. 원문 응답을 확인해야 합니다.",
        "positive_points": [],
        "concerns": [reason],
        "pain_points": [],
        "needs": [],
        "response_tags": ["JSON 파싱 실패"],
        "appeal_score": 3,
        "appeal_reason": "점수를 안정적으로 추출하지 못했습니다.",
        "usage_context": "",
        "persuasion_points": [],
        "message_suggestions": [],
        "journey_map": normalize_journey_map([]),
        "raw_text": raw_text,
    }


PERSONA_SCHEMA_HINT = """
{
  "persona_story": "string",
  "persona_issue": "string",
  "first_impression": "string",
  "positive_points": ["string", "string"],
  "concerns": ["string", "string"],
  "pain_points": ["string", "string", "string"],
  "needs": ["string", "string", "string"],
  "response_tags": ["string", "string", "string"],
  "appeal_score": 4,
  "appeal_reason": "string",
  "usage_context": "string",
  "persuasion_points": ["string", "string"],
  "message_suggestions": ["string", "string"],
  "journey_map": [
    {"stage": "노출", "action": "string", "emotion_score": 3, "emotion_label": "string", "touchpoint": "string", "need": "string", "opportunity": "string"},
    {"stage": "탐색", "action": "string", "emotion_score": 4, "emotion_label": "string", "touchpoint": "string", "need": "string", "opportunity": "string"},
    {"stage": "비교", "action": "string", "emotion_score": 3, "emotion_label": "string", "touchpoint": "string", "need": "string", "opportunity": "string"},
    {"stage": "결정", "action": "string", "emotion_score": 4, "emotion_label": "string", "touchpoint": "string", "need": "string", "opportunity": "string"},
    {"stage": "공유", "action": "string", "emotion_score": 4, "emotion_label": "string", "touchpoint": "string", "need": "string", "opportunity": "string"}
  ]
}
"""


def generate_persona_response(persona, plan):
    item_type = plan.get("item_type", "상품/서비스")
    item_description = plan.get("item_description", "")
    task_type = plan.get("task_type", "소비자 반응 평가")
    target_description = plan.get("target_description", "")
    fgi_questions = plan.get("fgi_questions", [])

    question_text = "\n".join([f"{idx + 1}. {q}" for idx, q in enumerate(fgi_questions)])

    prompt = f"""
너는 한국 소비자 FGI에 참여한 응답자 1명이다.
아래 페르소나 정보에 기반해, 분석 대상에 대한 소비자 반응을 JSON 객체 하나로만 출력하라.

[분석 대상]
- 유형: {item_type}
- 설명: {item_description}
- 분석 목적: {task_type}
- 타깃 고객: {target_description}

[FGI 질문지]
{question_text}

[페르소나 정보]
- 이름: {persona.get("name")}
- 나이: {persona.get("age")}
- 성별: {persona.get("gender")}
- 지역: {persona.get("region")}
- 직업: {persona.get("job")}
- 기본 설명: {persona.get("description")}
- 직업/전문성 설명: {persona.get("professional_persona")}
- 예술/취향 설명: {persona.get("arts_persona")}
- 음식/라이프스타일 설명: {persona.get("culinary_persona")}
- 가족/생활 설명: {persona.get("family_persona")}
- 여행/여가 설명: {persona.get("travel_persona")}

[중요 원칙]
- 반드시 분석 대상에 대한 반응만 작성한다.
- 페르소나 정보는 반응의 근거로만 사용한다.
- 페르소나 설명을 그대로 요약하지 않는다.
- 분석 대상과 무관한 음식, 가족, 직장, 취미 이야기를 길게 확장하지 않는다.
- 실제 시장조사 결과처럼 단정하지 않는다.
- 자연스러운 한국어 문장으로 작성한다.
- markdown 코드블록, 주석, 설명 문장을 절대 출력하지 않는다.
- 반드시 아래 JSON 스키마와 같은 키를 모두 포함한다.

[출력 JSON 스키마]
{PERSONA_SCHEMA_HINT}
"""

    raw = ""
    try:
        raw = ask_llm(prompt, temperature=0.0, json_mode=True)
        data = extract_json_from_text(raw)
        return normalize_persona_response(data)
    except Exception as first_error:
        try:
            data = repair_json_response(raw, PERSONA_SCHEMA_HINT)
            return normalize_persona_response(data)
        except Exception as repair_error:
            print("\n개별 페르소나 응답 JSON 파싱 실패")
            print("원인:", first_error)
            print("복구 실패:", repair_error)
            print("LLM 원본 응답:")
            print(raw)
            return fallback_persona_response(raw, error=first_error)


def _fallback_journey_map_from_personas(plan, persona_responses):
    stages = normalize_journey_map([])
    journey = []

    for idx, fallback in enumerate(stages):
        scores = []
        values = {"action": [], "emotion_label": [], "touchpoint": [], "need": [], "opportunity": []}

        for response in persona_responses:
            persona_journey = normalize_journey_map(response.get("journey_map"))
            step = persona_journey[idx]

            try:
                scores.append(float(step.get("emotion_score", 3)))
            except (ValueError, TypeError):
                scores.append(3)

            for key in values:
                value = safe_text(step.get(key))
                if value:
                    values[key].append(value)

        avg_score = sum(scores) / len(scores) if scores else fallback["emotion_score"]
        journey.append(
            {
                "stage": fallback["stage"],
                "action": values["action"][0] if values["action"] else fallback["action"],
                "emotion_score": round(avg_score, 2),
                "emotion_label": values["emotion_label"][0] if values["emotion_label"] else fallback["emotion_label"],
                "touchpoint": values["touchpoint"][0] if values["touchpoint"] else fallback["touchpoint"],
                "need": values["need"][0] if values["need"] else fallback["need"],
                "opportunity": values["opportunity"][0] if values["opportunity"] else fallback["opportunity"],
            }
        )

    return {
        "scenario": f"{plan.get('target_description', '대표 고객')}이 {plan.get('item_description', '분석 대상')}을 인지하고 검토하는 과정",
        "journey_map": journey,
    }


def normalize_journey_result(data, plan, persona_responses):
    if not isinstance(data, dict):
        return _fallback_journey_map_from_personas(plan, persona_responses)

    scenario = safe_text(data.get("scenario"))
    if not scenario:
        scenario = f"{plan.get('target_description', '대표 고객')}이 분석 대상을 탐색하고 구매/이용을 검토하는 과정"

    return {"scenario": scenario, "journey_map": normalize_journey_map(data.get("journey_map"))}


JOURNEY_SCHEMA_HINT = """
{
  "scenario": "대표 고객이 분석 대상을 발견하고 구매/이용을 검토하는 한 문장 시나리오",
  "journey_map": [
    {"stage": "노출", "action": "string", "emotion_score": 3, "emotion_label": "string", "touchpoint": "string", "need": "string", "opportunity": "string"},
    {"stage": "탐색", "action": "string", "emotion_score": 4, "emotion_label": "string", "touchpoint": "string", "need": "string", "opportunity": "string"},
    {"stage": "비교", "action": "string", "emotion_score": 3, "emotion_label": "string", "touchpoint": "string", "need": "string", "opportunity": "string"},
    {"stage": "결정", "action": "string", "emotion_score": 4, "emotion_label": "string", "touchpoint": "string", "need": "string", "opportunity": "string"},
    {"stage": "공유", "action": "string", "emotion_score": 4, "emotion_label": "string", "touchpoint": "string", "need": "string", "opportunity": "string"}
  ]
}
"""


def generate_journey_map(plan, persona_responses):
    response_summary = json.dumps(persona_responses, ensure_ascii=False, indent=2)

    prompt = f"""
너는 FGI 결과를 바탕으로 고객 여정지도를 만드는 UX 리서처다.
아래 분석 대상과 페르소나별 반응을 종합해, 대표 고객 Journey Map을 JSON 객체 하나로만 출력하라.

[분석 개요]
- 분석 대상 유형: {plan.get("item_type", "상품/서비스")}
- 분석 대상 설명: {plan.get("item_description", "")}
- 분석 목적: {plan.get("task_type", "소비자 반응 평가")}
- 타깃 고객: {plan.get("target_description", "")}

[페르소나별 구조화 응답 JSON]
{response_summary}

[작성 원칙]
- 반드시 분석 대상과 직접 관련된 여정만 작성한다.
- 5단계는 "노출", "탐색", "비교", "결정", "공유" 순서를 유지한다.
- emotion_score는 1~5 숫자로 쓴다.
- markdown 코드블록, 주석, 설명 문장을 절대 출력하지 않는다.

[출력 JSON 스키마]
{JOURNEY_SCHEMA_HINT}
"""

    raw = ""
    try:
        raw = ask_llm(prompt, temperature=0.0, json_mode=True)
        data = extract_json_from_text(raw)
        return normalize_journey_result(data, plan, persona_responses)
    except Exception as first_error:
        try:
            data = repair_json_response(raw, JOURNEY_SCHEMA_HINT)
            return normalize_journey_result(data, plan, persona_responses)
        except Exception as repair_error:
            print("\nJourney Map JSON 파싱 실패")
            print("원인:", first_error)
            print("복구 실패:", repair_error)
            print("LLM 원본 응답:")
            print(raw)
            return _fallback_journey_map_from_personas(plan, persona_responses)


def generate_overall_insight(plan, persona_responses):
    response_summary = json.dumps(persona_responses, ensure_ascii=False, indent=2)

    prompt = f"""
너는 FGI 결과를 분석하는 한국 소비자 리서처다.
아래는 특정 분석 대상에 대한 페르소나별 구조화 응답이다.
이를 바탕으로 전문적인 소비자 반응 시뮬레이션 종합 보고서를 작성하라.

[분석 개요]
- 분석 대상 유형: {plan.get("item_type", "상품/서비스")}
- 분석 대상 설명: {plan.get("item_description", "")}
- 분석 목적: {plan.get("task_type", "소비자 반응 평가")}
- 타깃 고객: {plan.get("target_description", "")}
- 패널 구성 전략: {plan.get("panel_strategy", "")}

[구조화된 개별 응답 JSON]
{response_summary}

[작성 지침]
- 단순 요약이 아니라, 공통된 니즈와 갈리는 반응을 구분한다.
- 분석 대상의 강점, 리스크, 메시지 방향을 제안한다.
- 개별 응답에 없는 내용을 과도하게 지어내지 않는다.
- synthetic persona 기반 가상 FGI라는 한계를 명시한다.
- 한국어로 자연스럽게 작성한다.
- 실제 시장조사처럼 단정하지 말고 "패널에서는 ~로 나타났다"라고 표현한다.

[출력 형식]
## 종합 인사이트

### 1. 전반적 반응
...

### 2. 강하게 작동한 매력 포인트
- ...

### 3. 구매/이용을 망설이게 하는 리스크
- ...

### 4. 타깃 커뮤니케이션 방향
...

### 5. 커뮤니케이션 메시지 A/B/C 제안
A안: ...
B안: ...
C안: ...

### 6. 한계 및 추가 검증 필요사항
...
"""

    try:
        return ask_llm(prompt, temperature=0.4)
    except Exception as e:
        return (
            "## 종합 인사이트\n\n"
            "LLM 호출에 실패해 자동 종합 인사이트를 생성하지 못했습니다.\n\n"
            f"- 원인: {e}\n"
            "- Streamlit Secrets의 OPENAI_API_KEY, LLM_PROVIDER, OPENAI_MODEL 설정을 확인해 주세요.\n"
        )
