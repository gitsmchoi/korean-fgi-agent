# personas.py

import json
import random
from pathlib import Path


LOCAL_PERSONA_FILES = [
    "personas_sample.jsonl",
    "data/personas_sample.jsonl",
    "personas_cache.jsonl",
    "data/personas_cache.jsonl",
    "personas_cache.json",
    "data/personas_cache.json",
]


FALLBACK_PERSONAS = [
    {
        "name": "김민정",
        "age": 34,
        "gender": "여자",
        "region": "서울-마포구",
        "job": "마케팅 기획자",
        "description": "김민정 씨는 서울 마포구에 거주하는 30대 직장인으로, 업무와 육아를 병행하며 시간 효율을 중요하게 생각합니다.",
        "professional_persona": "브랜드 캠페인과 소비자 트렌드 분석 업무를 담당하며, 새로운 제품이나 서비스의 메시지와 사용성을 빠르게 판단하는 편입니다.",
        "arts_persona": "감각적인 디자인과 세련된 패키지에 관심이 많지만, 과장된 표현보다는 진정성 있는 메시지를 선호합니다.",
        "culinary_persona": "평일에는 간편식과 배달을 자주 이용하고, 주말에는 가족과 함께 외식하거나 직접 요리하는 것을 즐깁니다.",
        "family_persona": "어린 자녀를 둔 워킹맘으로, 본인을 위한 소비를 할 때도 가족 일정과 비용을 함께 고려합니다.",
        "travel_persona": "짧은 휴식과 근교 여행을 선호하며, 동선이 편하고 예약이 쉬운 서비스를 선호합니다."
    },
    {
        "name": "박지영",
        "age": 37,
        "gender": "여자",
        "region": "경기-성남시",
        "job": "초등학교 교사",
        "description": "박지영 씨는 안정적인 생활 패턴을 중시하며, 건강과 자기관리에 관심이 많은 30대 여성입니다.",
        "professional_persona": "학생과 학부모를 자주 응대하는 직업 특성상 단정한 인상과 신뢰감을 중요하게 생각합니다.",
        "arts_persona": "화려한 유행보다는 깔끔하고 오래 사용할 수 있는 취향을 선호합니다.",
        "culinary_persona": "자극적인 음식보다는 건강하고 부담 없는 식사를 선호합니다.",
        "family_persona": "가족과의 시간을 중요하게 생각하며, 소비를 결정할 때 실용성과 가격을 함께 고려합니다.",
        "travel_persona": "방학이나 주말을 활용해 조용한 휴식형 여행을 즐깁니다."
    },
    {
        "name": "최현우",
        "age": 36,
        "gender": "남자",
        "region": "서울-강서구",
        "job": "IT 서비스 기획자",
        "description": "최현우 씨는 새로운 디지털 서비스에 관심이 많고, 기능의 명확성과 사용 편의성을 중요하게 생각합니다.",
        "professional_persona": "서비스 정책, 사용자 흐름, 데이터 기반 의사결정에 익숙하며 복잡한 기능도 구조적으로 이해하는 편입니다.",
        "arts_persona": "미니멀한 디자인과 직관적인 인터페이스를 선호합니다.",
        "culinary_persona": "평일에는 간편하고 효율적인 식사를 선호하며, 주말에는 새로운 맛집을 탐색합니다.",
        "family_persona": "가족과 생활비를 함께 고려하며, 구독형 서비스의 가격과 해지 조건을 꼼꼼히 확인합니다.",
        "travel_persona": "여행 전 리뷰와 가격 비교를 충분히 확인하고 결정하는 편입니다."
    }
]


def normalize_gender(value):
    if value is None:
        return None

    value = str(value).strip().lower()

    if value in ["여자", "여성", "female", "f", "woman", "women"]:
        return "여자"

    if value in ["남자", "남성", "male", "m", "man", "men"]:
        return "남자"

    return str(value).strip()


def parse_age(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_name_from_text(text):
    if not text:
        return None

    text = str(text).strip()

    if " 씨" in text:
        before = text.split(" 씨")[0].strip()
        if before:
            return before.split()[-1]

    return None


def normalize_persona(raw):
    """
    Nemotron-Personas-Korea 또는 로컬 jsonl의 필드를 앱 공통 필드로 정규화한다.
    """
    if not isinstance(raw, dict):
        raw = {}

    name = raw.get("name")
    if not name:
        for key in ["description", "professional_persona", "persona", "family_persona"]:
            name = extract_name_from_text(raw.get(key))
            if name:
                break

    if not name:
        name = "이름 없음"

    age = parse_age(raw.get("age"))

    gender = normalize_gender(raw.get("gender") or raw.get("sex"))

    region = raw.get("region")
    if not region:
        province = raw.get("province")
        district = raw.get("district")

        if province and district:
            region = f"{province}-{district}"
        elif province:
            region = str(province)
        elif district:
            region = str(district)
        else:
            region = "지역 미상"

    job = (
        raw.get("job")
        or raw.get("occupation")
        or raw.get("profession")
        or "직업 미상"
    )

    description = (
        raw.get("description")
        or raw.get("persona")
        or raw.get("professional_persona")
        or ""
    )

    return {
        "name": str(name).strip(),
        "age": age,
        "gender": gender,
        "region": str(region).strip(),
        "job": str(job).strip(),
        "description": str(description).strip(),
        "professional_persona": str(raw.get("professional_persona", description)).strip(),
        "arts_persona": str(raw.get("arts_persona", "")).strip(),
        "culinary_persona": str(raw.get("culinary_persona", "")).strip(),
        "family_persona": str(raw.get("family_persona", "")).strip(),
        "travel_persona": str(raw.get("travel_persona", "")).strip(),
    }


def load_jsonl_file(path):
    personas = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                item = json.loads(line)
                personas.append(normalize_persona(item))
            except json.JSONDecodeError:
                continue

    return personas


def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        if "personas" in data:
            data = data["personas"]
        elif "data" in data:
            data = data["data"]
        else:
            data = list(data.values())

    if not isinstance(data, list):
        return []

    return [normalize_persona(item) for item in data if isinstance(item, dict)]


def load_local_personas():
    """
    repo에 포함된 personas_sample.jsonl을 우선 사용한다.
    """
    for file_path in LOCAL_PERSONA_FILES:
        path = Path(file_path)

        if not path.exists():
            continue

        try:
            if path.suffix == ".jsonl":
                personas = load_jsonl_file(path)
            else:
                personas = load_json_file(path)

            if personas:
                print(f"로컬 페르소나 파일 로드 성공: {file_path} / {len(personas)}명")
                return personas

        except Exception as e:
            print(f"로컬 페르소나 파일 로드 실패: {file_path} / {e}")

    return []


def load_huggingface_personas(limit=1000):
    """
    로컬 샘플 파일이 없을 때 Hugging Face 원본 데이터셋을 시도한다.
    Streamlit Cloud에서는 네트워크/설치 상태에 따라 실패할 수 있으므로 fallback으로만 사용한다.
    """
    try:
        from datasets import load_dataset
    except Exception as e:
        print(f"datasets 패키지를 사용할 수 없어 Hugging Face 로드를 건너뜁니다: {e}")
        return []

    try:
        dataset = load_dataset(
            "nvidia/Nemotron-Personas-Korea",
            split="train",
            trust_remote_code=True,
            streaming=True
        )

        personas = []

        for idx, item in enumerate(dataset):
            personas.append(normalize_persona(item))

            if len(personas) >= limit:
                break

        if personas:
            print(f"Hugging Face 페르소나 로드 성공: {len(personas)}명")
            return personas

    except Exception as e:
        print(f"Hugging Face 페르소나 로드 실패: {e}")

    return []


def load_personas():
    """
    페르소나 로드 우선순위:
    1. repo에 포함된 personas_sample.jsonl
    2. Hugging Face 원본 데이터셋 일부
    3. 최소 내장 fallback
    """
    personas = load_local_personas()

    if personas:
        return personas

    personas = load_huggingface_personas(limit=1000)

    if personas:
        return personas

    print("로컬/Hugging Face 페르소나 로드가 모두 실패해 최소 fallback personas를 사용합니다.")
    return [normalize_persona(item) for item in FALLBACK_PERSONAS]


def persona_matches(persona, gender=None, min_age=None, max_age=None):
    if gender:
        target_gender = normalize_gender(gender)
        persona_gender = normalize_gender(persona.get("gender"))

        if target_gender and persona_gender != target_gender:
            return False

    age = persona.get("age")

    if min_age is not None:
        try:
            if age is None or int(age) < int(min_age):
                return False
        except (TypeError, ValueError):
            return False

    if max_age is not None:
        try:
            if age is None or int(age) > int(max_age):
                return False
        except (TypeError, ValueError):
            return False

    return True


def sample_personas_from_dataset(
    gender=None,
    min_age=None,
    max_age=None,
    sample_size=3
):
    """
    조건에 맞는 페르소나를 샘플링한다.
    조건에 맞는 샘플이 부족하면 성별 조건만 완화하고,
    그래도 부족하면 전체에서 보충한다.
    """
    personas = load_personas()

    matched = [
        p for p in personas
        if persona_matches(
            p,
            gender=gender,
            min_age=min_age,
            max_age=max_age
        )
    ]

    # 조건이 너무 좁아 부족한 경우: 성별만 맞는 후보로 완화
    if len(matched) < sample_size and gender:
        gender_only = [
            p for p in personas
            if persona_matches(p, gender=gender)
        ]

        for p in gender_only:
            if p not in matched:
                matched.append(p)

    # 그래도 부족하면 전체에서 보충
    if len(matched) < sample_size:
        for p in personas:
            if p not in matched:
                matched.append(p)

    if not matched:
        matched = [normalize_persona(item) for item in FALLBACK_PERSONAS]

    sample_size = max(1, min(int(sample_size), len(matched)))

    return random.sample(matched, sample_size)
