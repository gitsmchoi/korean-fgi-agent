# personas.py

import json
import random


LOCAL_PERSONA_PATH = "data/personas_sample.jsonl"


def normalize_gender(gender):
    if gender is None:
        return None

    gender = gender.strip()

    if gender in ["여성", "여자", "여"]:
        return "여자"

    if gender in ["남성", "남자", "남"]:
        return "남자"

    return gender


def load_local_personas(path=LOCAL_PERSONA_PATH):
    personas = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                personas.append(json.loads(line))

    return personas


def sample_personas_from_dataset(
    gender=None,
    min_age=None,
    max_age=None,
    sample_size=5
):
    personas = load_local_personas()
    gender = normalize_gender(gender)

    filtered = []

    for persona in personas:
        try:
            age = int(persona.get("age", 0))
        except ValueError:
            continue

        if min_age is not None and age < min_age:
            continue

        if max_age is not None and age > max_age:
            continue

        if gender is not None:
            sex = str(persona.get("gender", ""))
            if gender not in sex:
                continue

        filtered.append(persona)

    if len(filtered) == 0:
        raise ValueError(
            "조건에 맞는 페르소나를 찾지 못했습니다. "
            "성별/나이 조건을 완화하거나 로컬 캐시 데이터를 더 많이 생성해 주세요."
        )

    sample_size = min(sample_size, len(filtered))

    return random.sample(filtered, sample_size)