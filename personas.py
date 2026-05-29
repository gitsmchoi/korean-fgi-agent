# personas.py

import json
import random
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LOCAL_PERSONA_PATH = BASE_DIR / "data" / "personas_sample.jsonl"
FALLBACK_PERSONAS = [
    {
        "name": "김서연",
        "age": 32,
        "gender": "여자",
        "region": "서울-마포구",
        "job": "브랜드 마케터",
        "description": "새로운 상품을 빠르게 탐색하지만 실제 구매 전에는 후기와 가격 조건을 꼼꼼히 확인한다.",
        "professional_persona": "업무상 광고 메시지와 브랜드 톤에 민감하며, 과장된 표현보다 구체적인 근거를 선호한다.",
        "arts_persona": "감각적인 이미지와 짧은 영상 콘텐츠에 반응한다.",
        "culinary_persona": "편리함과 품질의 균형을 중시한다.",
        "family_persona": "평일에는 시간이 부족해 모바일로 정보를 빠르게 훑어보는 편이다.",
        "travel_persona": "짧은 휴식과 자기관리에 돈을 쓰는 것을 긍정적으로 본다.",
    },
    {
        "name": "박민정",
        "age": 37,
        "gender": "여자",
        "region": "경기-성남시 분당구",
        "job": "초등학교 교사",
        "description": "안정성과 신뢰를 중요하게 보고, 주변 추천과 실제 사용 사례를 확인한 뒤 결정한다.",
        "professional_persona": "교육 현장에서 검증된 정보와 명확한 설명에 익숙해 근거 없는 혜택 문구에는 조심스럽다.",
        "arts_persona": "차분하고 정돈된 표현을 선호한다.",
        "culinary_persona": "가성비보다 실패 가능성이 낮은 선택을 선호한다.",
        "family_persona": "가족 일정과 본인 시간을 함께 고려해 구매 결정을 내린다.",
        "travel_persona": "주말 중심의 짧은 외출과 회복 시간을 중요하게 생각한다.",
    },
    {
        "name": "이하늘",
        "age": 41,
        "gender": "남자",
        "region": "부산-해운대구",
        "job": "자영업자",
        "description": "효율과 비용 대비 효과를 중시하며, 실제 매출이나 생활 개선에 도움이 되는지 따진다.",
        "professional_persona": "현장에서 바로 쓸 수 있는 실용적인 정보와 명확한 가격 조건에 반응한다.",
        "arts_persona": "화려한 표현보다 이해하기 쉬운 설명을 선호한다.",
        "culinary_persona": "지역 상권과 고객 반응에 관심이 많다.",
        "family_persona": "가족과 사업 시간을 함께 관리해야 해서 시간 절약형 솔루션에 관심이 있다.",
        "travel_persona": "장기 여행보다 짧고 확실한 휴식을 선호한다.",
    },
    {
        "name": "최유진",
        "age": 29,
        "gender": "여자",
        "region": "대전-서구",
        "job": "콘텐츠 디자이너",
        "description": "시각적 완성도와 사용 후 공유할 만한 경험을 중요하게 생각한다.",
        "professional_persona": "디자인과 UX 관점에서 첫인상, 문구, 상세페이지 흐름을 빠르게 판단한다.",
        "arts_persona": "트렌디한 비주얼과 간결한 메시지에 민감하다.",
        "culinary_persona": "새로운 브랜드를 시도하되 후기가 부족하면 망설인다.",
        "family_persona": "혼자 사는 생활 패턴에 맞는 간편한 구매 경험을 선호한다.",
        "travel_persona": "SNS에서 발견한 장소나 제품을 저장해두고 비교한다.",
    },
    {
        "name": "정태훈",
        "age": 52,
        "gender": "남자",
        "region": "광주-북구",
        "job": "공공기관 사무직",
        "description": "낯선 상품에는 신중하지만, 신뢰할 수 있는 기관이나 명확한 보증이 있으면 검토한다.",
        "professional_persona": "절차와 조건이 명확한 정보를 선호하며 숨은 비용이나 약관을 중요하게 본다.",
        "arts_persona": "차분하고 직접적인 설명을 편하게 느낀다.",
        "culinary_persona": "검증된 선택지를 반복 구매하는 편이다.",
        "family_persona": "가족 구성원의 의견과 장기적인 비용을 함께 고려한다.",
        "travel_persona": "계획적인 소비와 안정적인 서비스를 선호한다.",
    },
]


def normalize_gender(gender):
    if gender is None:
        return None

    gender = gender.strip()

    if gender in ["여성", "여자", "여"]:
        return "여자"

    if gender in ["남성", "남자", "남"]:
        return "남자"

    return gender


def resolve_persona_path(path=LOCAL_PERSONA_PATH):
    path = Path(path)
    candidates = [
        path,
        BASE_DIR / path,
        Path.cwd() / path,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    searched = "\n".join(str(candidate) for candidate in candidates)
    print(
        "페르소나 데이터 파일을 찾지 못해 내장 예비 데이터를 사용합니다.\n"
        f"찾아본 경로:\n{searched}"
    )
    return None


def load_local_personas(path=LOCAL_PERSONA_PATH):
    personas = []
    persona_path = resolve_persona_path(path)
    if persona_path is None:
        return list(FALLBACK_PERSONAS)

    with open(persona_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                personas.append(json.loads(line))

    return personas or list(FALLBACK_PERSONAS)


def normalize_int(value):
    if value is None:
        return None

    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def filter_personas(personas, gender=None, min_age=None, max_age=None):
    filtered = []

    for persona in personas:
        age = normalize_int(persona.get("age"))
        if age is None:
            continue

        if min_age is not None and age < min_age:
            continue

        if max_age is not None and age > max_age:
            continue

        if gender is not None:
            sex = normalize_gender(str(persona.get("gender", "")))
            if sex != gender:
                continue

        filtered.append(persona)

    return filtered


def persona_diversity_key(persona):
    return (
        str(persona.get("job", "")).strip(),
        str(persona.get("region", "")).strip(),
        str(persona.get("family_persona", "")).strip()[:40],
        str(persona.get("professional_persona", "")).strip()[:40],
    )


def diversity_score(persona, selected):
    if not selected:
        return 4

    job = str(persona.get("job", "")).strip()
    region = str(persona.get("region", "")).strip()
    family = str(persona.get("family_persona", "")).strip()
    professional = str(persona.get("professional_persona", "")).strip()

    selected_jobs = {str(item.get("job", "")).strip() for item in selected}
    selected_regions = {str(item.get("region", "")).strip() for item in selected}
    selected_families = {str(item.get("family_persona", "")).strip() for item in selected}
    selected_professionals = {str(item.get("professional_persona", "")).strip() for item in selected}

    score = 0
    score += 2 if job and job not in selected_jobs else 0
    score += 1 if region and region not in selected_regions else 0
    score += 1 if family and family not in selected_families else 0
    score += 1 if professional and professional not in selected_professionals else 0
    return score


def sample_diverse_personas(personas, sample_size):
    candidates = list({persona_diversity_key(persona): persona for persona in personas}.values())
    random.shuffle(candidates)

    selected = []
    while candidates and len(selected) < sample_size:
        best = max(candidates, key=lambda persona: diversity_score(persona, selected))
        selected.append(best)
        candidates.remove(best)

    return selected


def sample_personas_from_dataset(
    gender=None,
    min_age=None,
    max_age=None,
    sample_size=5
):
    personas = load_local_personas()
    gender = normalize_gender(gender)
    min_age = normalize_int(min_age)
    max_age = normalize_int(max_age)
    sample_size = normalize_int(sample_size) or 3
    sample_size = max(1, min(sample_size, 5))

    fallback_pools = [
        filter_personas(personas, gender=gender, min_age=min_age, max_age=max_age),
        filter_personas(personas, gender=None, min_age=min_age, max_age=max_age),
        filter_personas(personas, gender=gender, min_age=None, max_age=None),
        list(personas),
        list(FALLBACK_PERSONAS),
    ]

    filtered = next((pool for pool in fallback_pools if pool), list(FALLBACK_PERSONAS))
    sample_size = min(sample_size, len(filtered))

    return sample_diverse_personas(filtered, sample_size)
