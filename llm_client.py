# llm_client.py

import json
import os
import re
import ollama

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# 현재 사용 모델
# 한국어 품질이 너무 떨어지면 아래 모델도 테스트:
# MODEL_NAME = "exaone3.5:2.4b"
# MODEL_NAME = "qwen2.5:3b"
MODEL_NAME = "qwen2.5:3b"
OPENAI_MODEL_NAME = "gpt-4o-mini"


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
        raise RuntimeError("openai 패키지가 설치되어 있지 않습니다.")

    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    model = get_secret("OPENAI_MODEL", OPENAI_MODEL_NAME)
    client = OpenAI(api_key=api_key)

    kwargs = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "너는 한국어 문장력이 좋은 소비자 리서처이자 FGI 분석가다. "
                    "응답은 반드시 자연스러운 한국어로 작성한다. "
                    "분석 대상과 직접 관련된 내용만 다룬다. "
                    "페르소나 설명을 그대로 반복하지 말고, 소비자 반응으로 재해석한다. "
                    "어색한 조어, 번역투, 비문을 피한다. "
                    "없는 사실을 과도하게 지어내지 않는다."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def ask_llm(prompt, temperature=0.6, json_mode=False):
    """
    Ollama 로컬 LLM에게 프롬프트를 보내고 응답 텍스트를 받는다.
    json_mode=True일 때는 Ollama의 JSON 출력 모드를 시도한다.
    """
    provider = str(get_secret("LLM_PROVIDER", "auto")).lower()

    if provider == "openai" or (provider == "auto" and get_secret("OPENAI_API_KEY")):
        return ask_openai(prompt, temperature=temperature, json_mode=json_mode)

    kwargs = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": (
                    "너는 한국어 문장력이 좋은 소비자 리서처이자 FGI 분석가다. "
                    "응답은 반드시 자연스러운 한국어로 작성한다. "
                    "분석 대상과 직접 관련된 내용만 다룬다. "
                    "페르소나 설명을 그대로 반복하지 말고, 소비자 반응으로 재해석한다. "
                    "어색한 조어, 번역투, 비문을 피한다. "
                    "없는 사실을 과도하게 지어내지 않는다."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "options": {
            "temperature": temperature
        }
    }

    if json_mode:
        kwargs["format"] = "json"

    try:
        response = ollama.chat(**kwargs)
    except TypeError:
        kwargs.pop("format", None)
        response = ollama.chat(**kwargs)

    return response["message"]["content"]


def extract_json_from_text(text):
    """
    LLM 응답에서 JSON 객체만 추출한다.
    모델이 실수로 앞뒤에 설명을 붙여도 JSON 부분만 파싱하기 위한 함수.
    """
    if not isinstance(text, str):
        raise ValueError("LLM 응답이 문자열이 아닙니다.")

    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for idx, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[idx:])
            return parsed
        except json.JSONDecodeError:
            continue

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or start >= end:
        raise ValueError("LLM 응답에서 JSON 객체를 찾지 못했습니다.")

    json_text = text[start:end + 1]
    json_text = re.sub(r",\s*([}\]])", r"\1", json_text)
    return json.loads(json_text)


def safe_list(value):
    """
    값이 리스트가 아니면 리스트로 바꾼다.
    """
    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [str(value)]


def normalize_journey_map(value):
    """
    journey_map을 안정적인 5단계 구조로 보정한다.
    """
    default_steps = [
        {
            "stage": "노출",
            "action": "분석 대상을 처음 접한다.",
            "emotion_score": 3,
            "emotion_label": "관심은 있지만 판단 보류",
            "touchpoint": "광고/소개 문구",
            "need": "핵심 혜택을 빠르게 이해하고 싶다.",
            "opportunity": "첫 문장에서 가장 강한 혜택을 제시한다."
        },
        {
            "stage": "탐색",
            "action": "상세 정보를 확인한다.",
            "emotion_score": 3,
            "emotion_label": "정보를 더 보고 싶음",
            "touchpoint": "상세페이지/후기/검색",
            "need": "근거와 후기를 확인하고 싶다.",
            "opportunity": "신뢰 근거와 실제 사용 사례를 제시한다."
        },
        {
            "stage": "비교",
            "action": "가격, 대안, 조건을 비교한다.",
            "emotion_score": 3,
            "emotion_label": "망설임",
            "touchpoint": "가격표/비교 정보",
            "need": "내게 맞는 선택인지 확인하고 싶다.",
            "opportunity": "가격, 혜택, 차별점을 명확히 비교해준다."
        },
        {
            "stage": "결정",
            "action": "구매 또는 이용 여부를 결정한다.",
            "emotion_score": 3,
            "emotion_label": "조건 확인",
            "touchpoint": "결제/신청/가입 화면",
            "need": "불이익 없이 쉽게 시작하고 싶다.",
            "opportunity": "환불, 해지, 체험 조건을 명확히 안내한다."
        },
        {
            "stage": "공유",
            "action": "사용 후 만족 여부를 주변에 공유한다.",
            "emotion_score": 3,
            "emotion_label": "경험 평가",
            "touchpoint": "후기/SNS/지인 추천",
            "need": "사용 경험이 기대와 맞았는지 확인하고 싶다.",
            "opportunity": "후기 작성, 추천 보상, 재구매 혜택을 제공한다."
        }
    ]

    if not isinstance(value, list) or len(value) == 0:
        return default_steps

    normalized = []

    for idx, item in enumerate(value[:5]):
        if not isinstance(item, dict):
            continue

        fallback = default_steps[min(idx, len(default_steps) - 1)]
        emotion_score = item.get("emotion_score", fallback["emotion_score"])

        try:
            emotion_score = float(emotion_score)
        except (ValueError, TypeError):
            emotion_score = fallback["emotion_score"]

        emotion_score = max(1, min(5, emotion_score))

        normalized.append({
            "stage": str(item.get("stage", fallback["stage"])).strip() or fallback["stage"],
            "action": str(item.get("action", fallback["action"])).strip() or fallback["action"],
            "emotion_score": emotion_score,
            "emotion_label": str(item.get("emotion_label", fallback["emotion_label"])).strip() or fallback["emotion_label"],
            "touchpoint": str(item.get("touchpoint", fallback["touchpoint"])).strip() or fallback["touchpoint"],
            "need": str(item.get("need", fallback["need"])).strip() or fallback["need"],
            "opportunity": str(item.get("opportunity", fallback["opportunity"])).strip() or fallback["opportunity"]
        })

    while len(normalized) < 5:
        normalized.append(default_steps[len(normalized)])

    return normalized


def normalize_persona_response(data):
    """
    LLM이 반환한 JSON의 누락값/이상값을 보정한다.
    """
    appeal_score = data.get("appeal_score", 3)

    try:
        appeal_score = int(appeal_score)
    except (ValueError, TypeError):
        appeal_score = 3

    appeal_score = max(1, min(5, appeal_score))

    return {
        "persona_story": str(data.get("persona_story", "")).strip(),
        "persona_issue": str(data.get("persona_issue", "")).strip(),
        "first_impression": str(data.get("first_impression", "")).strip(),
        "positive_points": safe_list(data.get("positive_points", [])),
        "concerns": safe_list(data.get("concerns", [])),
        "pain_points": safe_list(data.get("pain_points", [])),
        "needs": safe_list(data.get("needs", [])),
        "response_tags": safe_list(data.get("response_tags", [])),
        "appeal_score": appeal_score,
        "appeal_reason": str(data.get("appeal_reason", "")).strip(),
        "usage_context": str(data.get("usage_context", "")).strip(),
        "persuasion_points": safe_list(data.get("persuasion_points", [])),
        "message_suggestions": safe_list(data.get("message_suggestions", [])),
        "journey_map": normalize_journey_map(data.get("journey_map", [])),
        "raw_text": str(data.get("raw_text", "")).strip()
    }


def fallback_persona_response(raw_text):
    """
    JSON 파싱에 실패했을 때 프로그램이 멈추지 않도록 기본 구조를 만든다.
    """
    return {
        "persona_story": "응답을 구조화하는 데 실패했습니다.",
        "persona_issue": "원문 응답 확인이 필요합니다.",
        "first_impression": "응답을 구조화하는 데 실패했습니다. 원문 응답을 확인해야 합니다.",
        "positive_points": [],
        "concerns": ["LLM 응답이 JSON 형식으로 생성되지 않았습니다."],
        "pain_points": [],
        "needs": [],
        "response_tags": ["JSON 파싱 실패"],
        "appeal_score": 3,
        "appeal_reason": "점수를 안정적으로 추출하지 못했습니다.",
        "usage_context": "",
        "persuasion_points": [],
        "message_suggestions": [],
        "journey_map": normalize_journey_map([]),
        "raw_text": raw_text
    }


def generate_persona_response(persona, plan):
    """
    한 명의 페르소나가 분석 대상에 어떻게 반응할지 JSON으로 생성한다.
    """
    item_type = plan.get("item_type", "상품/서비스")
    item_description = plan.get("item_description", "")
    task_type = plan.get("task_type", "소비자 반응 평가")
    target_description = plan.get("target_description", "")
    fgi_questions = plan.get("fgi_questions", [])

    question_text = "\n".join(
        [f"{idx + 1}. {q}" for idx, q in enumerate(fgi_questions)]
    )

    prompt = f"""
너는 한국 소비자 FGI에 참여한 응답자 1명이다.
아래 페르소나 정보에 기반해, 분석 대상에 대한 소비자 반응을 JSON으로만 출력하라.

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
- 반드시 JSON만 출력한다.
- markdown 코드블록을 쓰지 않는다.
- JSON 앞뒤에 설명 문장을 붙이지 않는다.

[출력 JSON 형식]
{{
  "persona_story": "이 페르소나가 분석 대상에 관심을 가질 법한 상황을 2문장으로 요약",
  "persona_issue": "이 페르소나가 분석 대상과 관련해 겪고 있을 문제나 고민을 2문장으로 요약",
  "first_impression": "분석 대상을 처음 접했을 때의 반응 2~3문장",
  "positive_points": [
    "긍정 요소 1",
    "긍정 요소 2"
  ],
  "concerns": [
    "우려 사항 1",
    "우려 사항 2"
  ],
  "pain_points": [
    "구체적인 pain point 1",
    "구체적인 pain point 2",
    "구체적인 pain point 3"
  ],
  "needs": [
    "구체적인 needs 1",
    "구체적인 needs 2",
    "구체적인 needs 3"
  ],
  "response_tags": [
    "짧은 태그 1",
    "짧은 태그 2",
    "짧은 태그 3"
  ],
  "appeal_score": 4,
  "appeal_reason": "1~5점 중 해당 점수를 준 이유 2문장",
  "usage_context": "이 사람이 언제, 어디서, 어떤 필요 때문에 이 상품/서비스/문구를 접하거나 사용할지",
  "persuasion_points": [
    "이 사람을 설득하기 위해 강조해야 할 점 1",
    "이 사람을 설득하기 위해 강조해야 할 점 2"
  ],
  "message_suggestions": [
    "커뮤니케이션 메시지 제안 1",
    "커뮤니케이션 메시지 제안 2"
  ],
  "journey_map": [
    {{
      "stage": "노출",
      "action": "분석 대상을 처음 접하는 행동",
      "emotion_score": 3,
      "emotion_label": "감정 상태",
      "touchpoint": "접점",
      "need": "이 단계의 니즈",
      "opportunity": "개선 기회"
    }},
    {{
      "stage": "탐색",
      "action": "정보를 탐색하는 행동",
      "emotion_score": 4,
      "emotion_label": "감정 상태",
      "touchpoint": "접점",
      "need": "이 단계의 니즈",
      "opportunity": "개선 기회"
    }},
    {{
      "stage": "비교",
      "action": "대안과 비교하는 행동",
      "emotion_score": 3,
      "emotion_label": "감정 상태",
      "touchpoint": "접점",
      "need": "이 단계의 니즈",
      "opportunity": "개선 기회"
    }},
    {{
      "stage": "결정",
      "action": "구매 또는 이용을 결정하는 행동",
      "emotion_score": 4,
      "emotion_label": "감정 상태",
      "touchpoint": "접점",
      "need": "이 단계의 니즈",
      "opportunity": "개선 기회"
    }},
    {{
      "stage": "공유",
      "action": "사용 후 평가하거나 공유하는 행동",
      "emotion_score": 4,
      "emotion_label": "감정 상태",
      "touchpoint": "접점",
      "need": "이 단계의 니즈",
      "opportunity": "개선 기회"
    }}
  ]
}}
"""
    raw = ""
    try:
        raw = ask_llm(prompt, temperature=0.0, json_mode=True)
        data = extract_json_from_text(raw)
        return normalize_persona_response(data)

    except Exception as e:
        print("\n개별 페르소나 응답 JSON 파싱 실패")
        print("원인:", e)
        print("LLM 원본 응답:")
        print(raw)
        return fallback_persona_response(raw)


def _fallback_journey_map_from_personas(plan, persona_responses):
    """
    별도 journey map 생성이 실패해도 페르소나별 journey_map을 합성해 화면에 표시한다.
    """
    stages = normalize_journey_map([])
    journey = []

    for idx, fallback in enumerate(stages):
        scores = []
        values = {
            "action": [],
            "emotion_label": [],
            "touchpoint": [],
            "need": [],
            "opportunity": []
        }

        for response in persona_responses:
            persona_journey = normalize_journey_map(response.get("journey_map", []))
            step = persona_journey[idx]

            try:
                scores.append(float(step.get("emotion_score", 3)))
            except (ValueError, TypeError):
                scores.append(3)

            for key in values:
                value = str(step.get(key, "")).strip()
                if value:
                    values[key].append(value)

        avg_score = sum(scores) / len(scores) if scores else fallback["emotion_score"]

        journey.append({
            "stage": fallback["stage"],
            "action": values["action"][0] if values["action"] else fallback["action"],
            "emotion_score": round(avg_score, 2),
            "emotion_label": values["emotion_label"][0] if values["emotion_label"] else fallback["emotion_label"],
            "touchpoint": values["touchpoint"][0] if values["touchpoint"] else fallback["touchpoint"],
            "need": values["need"][0] if values["need"] else fallback["need"],
            "opportunity": values["opportunity"][0] if values["opportunity"] else fallback["opportunity"]
        })

    return {
        "scenario": f"{plan.get('target_description', '대표 고객')}이 {plan.get('item_description', '분석 대상')}을 인지하고 검토하는 과정",
        "journey_map": journey
    }


def normalize_journey_result(data, plan, persona_responses):
    if not isinstance(data, dict):
        return _fallback_journey_map_from_personas(plan, persona_responses)

    scenario = str(data.get("scenario", "")).strip()
    if not scenario:
        scenario = f"{plan.get('target_description', '대표 고객')}이 분석 대상을 탐색하고 구매/이용을 검토하는 과정"

    return {
        "scenario": scenario,
        "journey_map": normalize_journey_map(data.get("journey_map", []))
    }


def generate_journey_map(plan, persona_responses):
    """
    페르소나별 반응을 대표 고객 여정지도 JSON으로 합성한다.
    """
    item_type = plan.get("item_type", "상품/서비스")
    item_description = plan.get("item_description", "")
    task_type = plan.get("task_type", "소비자 반응 평가")
    target_description = plan.get("target_description", "")

    response_summary = json.dumps(
        persona_responses,
        ensure_ascii=False,
        indent=2
    )

    prompt = f"""
너는 FGI 결과를 바탕으로 고객 여정지도를 만드는 UX 리서처다.
아래 분석 대상과 페르소나별 반응을 종합해, 대표 고객 Journey Map을 JSON으로만 출력하라.

[분석 대상]
- 유형: {item_type}
- 설명: {item_description}
- 분석 목적: {task_type}
- 타깃 고객: {target_description}

[페르소나별 구조화 응답 JSON]
{response_summary}

[작성 원칙]
- 반드시 분석 대상과 직접 관련된 여정만 작성한다.
- 5단계는 "노출", "탐색", "비교", "결정", "공유" 순서를 유지한다.
- emotion_score는 1~5 숫자로 쓴다. 1은 매우 부정, 5는 매우 긍정이다.
- action, touchpoint, need, opportunity는 각 단계별로 구체적이고 짧게 작성한다.
- markdown 코드블록 없이 JSON만 출력한다.

[출력 JSON 형식]
{{
  "scenario": "대표 고객이 분석 대상을 발견하고 구매/이용을 검토하는 한 문장 시나리오",
  "journey_map": [
    {{
      "stage": "노출",
      "action": "이 단계의 대표 행동",
      "emotion_score": 3,
      "emotion_label": "감정 상태",
      "touchpoint": "대표 접점",
      "need": "이 단계의 핵심 니즈",
      "opportunity": "마케팅/제품 개선 기회"
    }},
    {{
      "stage": "탐색",
      "action": "이 단계의 대표 행동",
      "emotion_score": 4,
      "emotion_label": "감정 상태",
      "touchpoint": "대표 접점",
      "need": "이 단계의 핵심 니즈",
      "opportunity": "마케팅/제품 개선 기회"
    }},
    {{
      "stage": "비교",
      "action": "이 단계의 대표 행동",
      "emotion_score": 3,
      "emotion_label": "감정 상태",
      "touchpoint": "대표 접점",
      "need": "이 단계의 핵심 니즈",
      "opportunity": "마케팅/제품 개선 기회"
    }},
    {{
      "stage": "결정",
      "action": "이 단계의 대표 행동",
      "emotion_score": 4,
      "emotion_label": "감정 상태",
      "touchpoint": "대표 접점",
      "need": "이 단계의 핵심 니즈",
      "opportunity": "마케팅/제품 개선 기회"
    }},
    {{
      "stage": "공유",
      "action": "이 단계의 대표 행동",
      "emotion_score": 4,
      "emotion_label": "감정 상태",
      "touchpoint": "대표 접점",
      "need": "이 단계의 핵심 니즈",
      "opportunity": "마케팅/제품 개선 기회"
    }}
  ]
}}
"""
    raw = ""
    try:
        raw = ask_llm(prompt, temperature=0.0, json_mode=True)
        data = extract_json_from_text(raw)
        return normalize_journey_result(data, plan, persona_responses)
    except Exception as e:
        print("\nJourney Map JSON 파싱 실패")
        print("원인:", e)
        print("LLM 원본 응답:")
        print(raw)
        return _fallback_journey_map_from_personas(plan, persona_responses)


def generate_overall_insight(plan, persona_responses):
    """
    여러 페르소나 응답을 종합해서 FGI 리서처 관점의 인사이트를 생성한다.
    persona_responses는 구조화된 dict 리스트다.
    """
    item_type = plan.get("item_type", "상품/서비스")
    item_description = plan.get("item_description", "")
    task_type = plan.get("task_type", "소비자 반응 평가")
    target_description = plan.get("target_description", "")
    panel_strategy = plan.get("panel_strategy", "")

    response_summary = json.dumps(
        persona_responses,
        ensure_ascii=False,
        indent=2
    )

    prompt = f"""
너는 FGI 결과를 분석하는 한국 소비자 리서처다.
아래는 특정 분석 대상에 대한 페르소나별 구조화 응답이다.
이를 바탕으로 전문적인 소비자 반응 시뮬레이션 종합 보고서를 작성하라.

[분석 개요]
- 분석 대상 유형: {item_type}
- 분석 대상 설명: {item_description}
- 분석 목적: {task_type}
- 타깃 고객: {target_description}
- 패널 구성 전략: {panel_strategy}

[구조화된 개별 응답 JSON]
{response_summary}

[작성 지침]
- 단순 요약이 아니라, 공통된 니즈와 갈리는 반응을 구분한다.
- 분석 대상의 강점, 리스크, 메시지 방향을 제안한다.
- 개별 응답에 없는 내용을 과도하게 지어내지 않는다.
- 실제 시장조사가 아니라 synthetic persona 기반 가상 FGI라는 한계를 명시한다.
- 한국어로 자연스럽게 작성한다.
- 분석 대상과 무관한 내용은 종합 인사이트에서 제외한다.
- 시장 출시 전 검증해야 할 내용을 명확히 제시한다.
- "소비자는 반드시 ~한다"처럼 단정하지 말고, "패널에서는 ~로 나타났다"라고 표현한다.

[출력 형식]
## 종합 인사이트

### 1. 전반적 반응
...

### 2. 강하게 작동한 매력 포인트
- ...
- ...

### 3. 구매/이용을 망설이게 하는 리스크
- ...
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
            "로컬 LLM 호출에 실패해 자동 종합 인사이트를 생성하지 못했습니다.\n\n"
            f"- 원인: {e}\n"
            "- Ollama가 실행 중인지, 설정된 모델이 설치되어 있는지 확인한 뒤 다시 실행해 주세요.\n"
            "- 개별 페르소나 응답이 생성되어 있다면 CSV/Markdown 다운로드로 원자료를 확인할 수 있습니다.\n"
        )
