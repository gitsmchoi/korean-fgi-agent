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

    return sample_diverse_personas(filtered, sample_size)
