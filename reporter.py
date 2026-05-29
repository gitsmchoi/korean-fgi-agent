# reporter.py

from llm_client import generate_overall_insight


def join_list(items):
    """
    리스트를 보고서에 넣기 좋게 문자열로 변환한다.
    """
    if not items:
        return "-"

    return "<br>".join([str(item) for item in items])


def save_report(plan, responses, output_path="output/persona_panel_report.md"):
    report = "# 한국형 페르소나 패널 소비자 반응 시뮬레이션 보고서\n\n"

    report += "## 1. 분석 개요\n\n"
    report += f"- 분석 대상 유형: {plan.get('item_type')}\n"
    report += f"- 분석 대상 설명: {plan.get('item_description')}\n"
    report += f"- 분석 목적: {plan.get('task_type')}\n"
    report += f"- 타깃 고객: {plan.get('target_description')}\n"
    report += f"- 패널 구성 전략: {plan.get('panel_strategy')}\n\n"

    report += "## 2. Agent가 생성한 FGI 질문지\n\n"
    for idx, question in enumerate(plan.get("fgi_questions", []), start=1):
        report += f"{idx}. {question}\n"
    report += "\n"

    report += "## 3. 페르소나 패널 구성\n\n"

    for idx, r in enumerate(responses, start=1):
        persona_name = r.get("persona_name", "익명 페르소나")
        profile = r.get("profile", "프로필 정보 없음")
        report += f"{idx}. **{persona_name}** — {profile}\n"

    report += "\n"

    report += "## 4. 반응 요약표\n\n"
    report += "| 응답자 | 프로필 | 매력도 | 주요 긍정 요소 | 주요 우려 사항 | 설득 포인트 |\n"
    report += "|---|---|---:|---|---|---|\n"

    for idx, r in enumerate(responses, start=1):
        sr = r.get("structured_response", {})
        persona_name = r.get("persona_name", f"응답자 {idx}")
        profile = r.get("profile", "프로필 정보 없음")
        score = sr.get("appeal_score", "-")
        positives = join_list(sr.get("positive_points", []))
        concerns = join_list(sr.get("concerns", []))
        persuasion = join_list(sr.get("persuasion_points", []))

        report += (
            f"| {persona_name} | {profile} | {score} | "
            f"{positives} | {concerns} | {persuasion} |\n"
        )

    report += "\n"

    scores = []
    for r in responses:
        sr = r.get("structured_response", {})
        score = sr.get("appeal_score")
        if isinstance(score, int):
            scores.append(score)

    if scores:
        avg_score = sum(scores) / len(scores)
        report += f"**평균 구매/이용 매력도:** {avg_score:.2f} / 5\n\n"

    report += "## 5. 개별 페르소나 상세 반응\n\n"

    for idx, r in enumerate(responses, start=1):
        persona_name = r.get("persona_name", "익명 페르소나")
        profile = r.get("profile", "프로필 정보 없음")
        sr = r.get("structured_response", {})

        report += f"### 응답자 {idx}. {persona_name}\n\n"
        report += f"- 프로필: {profile}\n\n"

        report += "#### 첫인상\n"
        report += f"{sr.get('first_impression', '-')}\n\n"

        report += "#### 긍정 요소\n"
        for item in sr.get("positive_points", []):
            report += f"- {item}\n"
        report += "\n"

        report += "#### 우려 사항\n"
        for item in sr.get("concerns", []):
            report += f"- {item}\n"
        report += "\n"

        report += "#### 구매/이용 매력도\n"
        report += f"- 점수: {sr.get('appeal_score', '-')} / 5\n"
        report += f"- 이유: {sr.get('appeal_reason', '-')}\n\n"

        report += "#### 예상 사용 상황\n"
        report += f"{sr.get('usage_context', '-')}\n\n"

        report += "#### 설득 포인트\n"
        for item in sr.get("persuasion_points", []):
            report += f"- {item}\n"
        report += "\n"

        report += "#### 커뮤니케이션 메시지 제안\n"
        for item in sr.get("message_suggestions", []):
            report += f"- {item}\n"
        report += "\n"

        raw_text = sr.get("raw_text", "")
        if raw_text:
            report += "#### 원문 응답 확인 필요\n"
            report += raw_text
            report += "\n\n"

        report += "---\n\n"

    print("\n종합 인사이트 생성 중...")

    structured_responses = [
        {
            "persona_name": r.get("persona_name"),
            "profile": r.get("profile"),
            **r.get("structured_response", {})
        }
        for r in responses
    ]

    overall_insight = generate_overall_insight(
        plan=plan,
        persona_responses=structured_responses
    )

    report += "## 6. 소비자 반응 종합 분석\n\n"
    report += overall_insight
    report += "\n\n"

    report += "## 7. 주의사항\n\n"
    report += (
        "본 결과는 Nemotron-Personas-Korea 기반 합성 페르소나를 활용한 "
        "가상 소비자 반응 시뮬레이션 결과입니다. 실제 소비자 조사 결과가 아니며, "
        "시장 출시 전 실제 인터뷰, 설문조사, A/B 테스트 등을 통한 검증이 필요합니다.\n"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    return output_path