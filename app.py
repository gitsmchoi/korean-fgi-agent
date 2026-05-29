# app.py

import streamlit as st
import pandas as pd
import math
from html import escape
from textwrap import dedent

from planner import plan_research_request
from personas import sample_personas_from_dataset
from simulator import simulate_response
from llm_client import generate_overall_insight, generate_journey_map


st.set_page_config(
    page_title="K-Persona Panel Studio",
    page_icon="💗",
    layout="wide"
)


# =========================================================
# Helper functions
# =========================================================

def safe_text(value, default="-"):
    if value is None:
        return default
    value = str(value).strip()
    return value if value else default


def join_list(items, sep=" · "):
    if not items:
        return "-"
    return sep.join([safe_text(x) for x in items])


def render_html(html):
    st.markdown(dedent(html).strip(), unsafe_allow_html=True)


def render_list_items(items, limit=None):
    if not items:
        return "<li>-</li>"

    selected = items[:limit] if limit else items
    return "".join([f"<li>{escape(str(item))}</li>" for item in selected])


def render_tag_chips(tags):
    if not tags:
        return ""

    return "".join([f"<span class='tag-mini'>#{escape(str(tag))}</span>" for tag in tags])


def make_summary_dataframe(responses):
    rows = []

    for r in responses:
        sr = r.get("structured_response", {})

        rows.append({
            "응답자": r.get("persona_name"),
            "프로필": r.get("profile"),
            "매력도": sr.get("appeal_score"),
            "긍정 요소": join_list(sr.get("positive_points", [])),
            "우려 사항": join_list(sr.get("concerns", [])),
            "Needs": join_list(sr.get("needs", [])),
            "Tags": join_list(sr.get("response_tags", [])),
        })

    return pd.DataFrame(rows)


def get_average_score(responses):
    scores = []

    for r in responses:
        sr = r.get("structured_response", {})
        score = sr.get("appeal_score")
        if isinstance(score, int):
            scores.append(score)

    if not scores:
        return None

    return sum(scores) / len(scores)


def build_markdown_report(plan, responses, insight):
    md = "# Korean Persona Panel 소비자 반응 시뮬레이션 보고서\n\n"

    md += "## 1. 분석 개요\n\n"
    md += f"- 분석 대상 유형: {plan.get('item_type')}\n"
    md += f"- 분석 대상 설명: {plan.get('item_description')}\n"
    md += f"- 분석 목적: {plan.get('task_type')}\n"
    md += f"- 타깃 고객: {plan.get('target_description')}\n"
    md += f"- 패널 구성 전략: {plan.get('panel_strategy')}\n\n"

    md += "## 2. FGI 질문지\n\n"
    for idx, q in enumerate(plan.get("fgi_questions", []), start=1):
        md += f"{idx}. {q}\n"
    md += "\n"

    md += "## 3. 페르소나 패널 반응\n\n"
    for idx, r in enumerate(responses, start=1):
        sr = r.get("structured_response", {})

        md += f"### 응답자 {idx}. {r.get('persona_name')}\n\n"
        md += f"- 프로필: {r.get('profile')}\n"
        md += f"- Story: {sr.get('persona_story', '-')}\n"
        md += f"- Issue: {sr.get('persona_issue', '-')}\n"
        md += f"- 첫인상: {sr.get('first_impression', '-')}\n"
        md += f"- 매력도: {sr.get('appeal_score', '-')} / 5\n"
        md += f"- 긍정 요소: {join_list(sr.get('positive_points', []))}\n"
        md += f"- 우려 사항: {join_list(sr.get('concerns', []))}\n"
        md += f"- Pain Points: {join_list(sr.get('pain_points', []))}\n"
        md += f"- Needs: {join_list(sr.get('needs', []))}\n"
        md += f"- Tags: {join_list(sr.get('response_tags', []))}\n"
        md += f"- 메시지 제안: {join_list(sr.get('message_suggestions', []))}\n\n"

    md += "## 4. 종합 인사이트\n\n"
    md += insight
    md += "\n\n"

    md += "## 5. 주의사항\n\n"
    md += (
        "본 결과는 Nemotron-Personas-Korea 기반 합성 페르소나를 활용한 "
        "가상 소비자 반응 시뮬레이션 결과입니다. 실제 소비자 조사 결과가 아니며, "
        "시장 출시 전 실제 인터뷰, 설문조사, A/B 테스트 등을 통한 검증이 필요합니다.\n"
    )

    return md


def aggregate_journey_map(responses):
    """
    여러 페르소나의 journey_map을 5단계 기준으로 평균화한다.
    """
    default_stages = ["노출", "탐색", "비교", "결정", "공유"]
    stage_data = []

    for i, default_stage in enumerate(default_stages):
        scores = []
        actions = []
        labels = []
        touchpoints = []
        needs = []
        opportunities = []

        for r in responses:
            sr = r.get("structured_response", {})
            journey = sr.get("journey_map", [])

            if isinstance(journey, list) and len(journey) > i:
                step = journey[i]
                if not isinstance(step, dict):
                    continue

                try:
                    score = float(step.get("emotion_score", 3))
                except (ValueError, TypeError):
                    score = 3

                scores.append(score)
                actions.append(step.get("action", ""))
                labels.append(step.get("emotion_label", ""))
                touchpoints.append(step.get("touchpoint", ""))
                needs.append(step.get("need", ""))
                opportunities.append(step.get("opportunity", ""))

        avg_score = sum(scores) / len(scores) if scores else 3

        stage_data.append({
            "stage": default_stage,
            "emotion_score": round(avg_score, 2),
            "emotion_label": labels[0] if labels else "감정 정보 없음",
            "action": actions[0] if actions else "-",
            "touchpoint": touchpoints[0] if touchpoints else "-",
            "need": needs[0] if needs else "-",
            "opportunity": opportunities[0] if opportunities else "-"
        })

    return stage_data


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background: #fafbff;
        color: #0b1124;
    }

    .block-container {
        max-width: 1280px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 22px;
    }

    .brand-wrap {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .brand-logo {
        width: 42px;
        height: 42px;
        border-radius: 14px;
        background: conic-gradient(from 210deg, #ff3d8b, #9d8bff, #7cb4ff, #ff3d8b);
        box-shadow: 0 8px 18px rgba(255,61,139,.35);
        position: relative;
    }

    .brand-logo:after {
        content: "";
        position: absolute;
        inset: 7px;
        border-radius: 9px;
        background: #fff;
    }

    .brand-core {
        position: absolute;
        inset: 14px;
        border-radius: 50%;
        background: linear-gradient(135deg, #ff3d8b, #0f1d4d);
        z-index: 2;
    }

    .brand-title {
        font-weight: 900;
        font-size: 19px;
        letter-spacing: -0.3px;
    }

    .brand-sub {
        font-size: 12px;
        color: #7a8095;
        margin-top: 2px;
    }

    .pill {
        display: inline-block;
        font-size: 12px;
        padding: 7px 12px;
        border-radius: 999px;
        border: 1px solid #e1e5ee;
        background: #fff;
        color: #3d4357;
        font-weight: 700;
        margin-left: 6px;
    }

    .pill-live {
        background: #ff3d8b;
        color: #fff;
        border-color: #ff3d8b;
    }

    .hero {
        position: relative;
        border-radius: 30px;
        padding: 38px;
        overflow: hidden;
        background: linear-gradient(135deg, #0f1d4d 0%, #1f2f6b 55%, #3a2160 100%);
        color: #fff;
        box-shadow: 0 12px 30px rgba(15,29,77,.08);
        margin-bottom: 34px;
    }

    .hero:before {
        content: "";
        position: absolute;
        width: 280px;
        height: 280px;
        border-radius: 50%;
        background: #ff3d8b;
        right: -70px;
        top: -80px;
        filter: blur(45px);
        opacity: .55;
    }

    .hero:after {
        content: "";
        position: absolute;
        width: 220px;
        height: 220px;
        border-radius: 50%;
        background: #7cb4ff;
        left: 34%;
        bottom: -110px;
        filter: blur(45px);
        opacity: .55;
    }

    .hero-inner {
        position: relative;
        z-index: 2;
        display: grid;
        grid-template-columns: 1.35fr 1fr;
        gap: 30px;
        align-items: center;
    }

    .tag-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 14px;
    }

    .tag {
        font-size: 12px;
        background: rgba(255,255,255,.12);
        padding: 6px 12px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,.18);
        font-weight: 700;
    }

    .tag-hot {
        background: #ff3d8b;
        border-color: #ff3d8b;
    }

    .hero-title {
        font-size: 40px;
        line-height: 1.18;
        font-weight: 900;
        letter-spacing: -0.7px;
        margin: 8px 0 12px;
    }

    .hero-title .acc {
        background: linear-gradient(120deg, #ff3d8b, #ffd84d);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }

    .hero-desc {
        color: #d6dcff;
        font-size: 15px;
        line-height: 1.8;
        max-width: 620px;
    }

    .stat-row {
        display: flex;
        gap: 14px;
        flex-wrap: wrap;
        margin-top: 22px;
    }

    .stat-box {
        background: rgba(255,255,255,.08);
        border: 1px solid rgba(255,255,255,.13);
        padding: 14px 18px;
        border-radius: 18px;
        min-width: 128px;
        backdrop-filter: blur(8px);
    }

    .stat-n {
        font-size: 22px;
        font-weight: 900;
    }

    .stat-l {
        font-size: 11px;
        color: #bcc4f0;
        margin-top: 3px;
        font-weight: 700;
        text-transform: uppercase;
    }

    .input-preview {
        background: #fff;
        color: #0b1124;
        border-radius: 24px;
        padding: 24px;
        box-shadow: 0 20px 50px rgba(255,61,139,.18);
    }

    .preview-label {
        font-size: 12px;
        color: #ff3d8b;
        font-weight: 900;
        text-transform: uppercase;
    }

    .preview-title {
        margin-top: 6px;
        font-size: 18px;
        font-weight: 900;
    }

    .preview-box {
        margin-top: 12px;
        border: 1.5px dashed #c8cdd9;
        border-radius: 16px;
        background: #f7f7fb;
        padding: 15px;
        font-size: 13.5px;
        line-height: 1.7;
        color: #3d4357;
    }

    .section-head {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        margin-top: 34px;
        margin-bottom: 16px;
    }

    .section-left {
        display: flex;
        gap: 12px;
        align-items: center;
    }

    .step-no {
        width: 36px;
        height: 36px;
        border-radius: 12px;
        background: #ff3d8b;
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        box-shadow: 0 6px 14px rgba(255,61,139,.35);
    }

    .section-title {
        font-size: 23px;
        font-weight: 900;
        letter-spacing: -0.3px;
    }

    .section-sub {
        font-size: 12.5px;
        color: #7a8095;
        margin-top: 4px;
        font-weight: 600;
    }

    .plan-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 14px;
    }

    .plan-card {
        background: #fff;
        border-radius: 20px;
        padding: 18px;
        border: 1px solid #eef0f6;
        box-shadow: 0 12px 30px rgba(15,29,77,.08);
    }

    .plan-ico {
        width: 38px;
        height: 38px;
        border-radius: 13px;
        background: #ffe3ee;
        color: #d81e6c;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 19px;
        margin-bottom: 10px;
    }

    .plan-k {
        font-size: 11px;
        color: #7a8095;
        font-weight: 900;
        text-transform: uppercase;
    }

    .plan-v {
        font-size: 15px;
        font-weight: 900;
        margin-top: 5px;
        line-height: 1.45;
    }

    .plan-card.accent {
        background: linear-gradient(135deg, #0f1d4d, #1f2f6b);
        color: #fff;
        border: none;
    }

    .plan-card.accent .plan-k {
        color: #bcc4f0;
    }

    .plan-card.accent .plan-ico {
        background: rgba(255,255,255,.15);
        color: #fff;
    }

    .fgi-card {
        background: #fff;
        border-radius: 24px;
        padding: 24px;
        box-shadow: 0 12px 30px rgba(15,29,77,.08);
        border: 1px solid #eef0f6;
        margin-top: 16px;
    }

    .fgi-list {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 10px;
        margin-top: 12px;
    }

    .fgi-item {
        background: #f7f7fb;
        border-radius: 15px;
        padding: 14px;
        border-left: 3px solid #ff3d8b;
        font-size: 12.5px;
        color: #3d4357;
        line-height: 1.6;
        font-weight: 600;
    }

    .fgi-q {
        display: block;
        color: #ff3d8b;
        font-weight: 900;
        font-size: 11px;
        margin-bottom: 6px;
    }

    .persona-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 18px;
    }

    .persona-card {
        background: #fff;
        border-radius: 24px;
        padding: 23px;
        box-shadow: 0 12px 30px rgba(15,29,77,.08);
        border: 1px solid #eef0f6;
        min-height: 680px;
    }

    .persona-top {
        display: flex;
        align-items: center;
        gap: 13px;
    }

    .avatar {
        width: 64px;
        height: 64px;
        border-radius: 20px;
        background: linear-gradient(135deg, #ffe3ee, #ffd1e3);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        flex-shrink: 0;
    }

    .persona-name {
        font-size: 17px;
        font-weight: 900;
    }

    .persona-meta {
        font-size: 12px;
        color: #7a8095;
        margin-top: 2px;
        font-weight: 700;
        line-height: 1.45;
    }

    .score-pill {
        margin-left: auto;
        background: #ff3d8b;
        color: #fff;
        border-radius: 15px;
        padding: 8px 12px;
        text-align: center;
        min-width: 62px;
        box-shadow: 0 6px 14px rgba(255,61,139,.3);
    }

    .score-num {
        font-size: 18px;
        font-weight: 900;
        line-height: 1;
    }

    .score-lab {
        font-size: 10px;
        font-weight: 800;
        opacity: .9;
    }

    .story-box {
        margin-top: 15px;
        background: #f7f7fb;
        border-radius: 15px;
        padding: 13px;
        border-left: 3px solid #0f1d4d;
        font-size: 13px;
        line-height: 1.7;
        color: #3d4357;
        font-weight: 600;
    }

    .mini-grid {
        margin-top: 14px;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }

    .mini-box {
        background: #f7f7fb;
        border-radius: 14px;
        padding: 12px;
    }

    .mini-title {
        font-size: 11px;
        font-weight: 900;
        margin-bottom: 7px;
        text-transform: uppercase;
    }

    .mini-title.pos { color: #10916c; }
    .mini-title.neg { color: #d81e6c; }
    .mini-title.pain { color: #0f1d4d; }
    .mini-title.need { color: #6b55d9; }

    .mini-box ul {
        padding-left: 16px;
        margin: 0;
        font-size: 12px;
        line-height: 1.55;
        color: #3d4357;
        font-weight: 600;
    }

    .tag-mini {
        display: inline-block;
        font-size: 11px;
        padding: 4px 9px;
        border-radius: 999px;
        font-weight: 800;
        margin-right: 5px;
        margin-top: 10px;
        background: #ffe3ee;
        color: #d81e6c;
    }

    .panel-stack {
        display: grid;
        gap: 16px;
    }

    .panel-summary-card {
        background: #fff;
        border: 1px solid #eef0f6;
        border-radius: 18px;
        box-shadow: 0 10px 28px rgba(15,29,77,.06);
        padding: 20px;
    }

    .panel-summary-top {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 18px;
        align-items: start;
        padding-bottom: 16px;
        border-bottom: 1px solid #eef0f6;
    }

    .panel-persona-title {
        font-size: 22px;
        font-weight: 900;
        color: #0b1124;
        line-height: 1.25;
    }

    .panel-profile {
        color: #697184;
        font-size: 13px;
        font-weight: 700;
        margin-top: 6px;
        line-height: 1.5;
    }

    .score-badge {
        min-width: 82px;
        padding: 10px 12px;
        border-radius: 14px;
        background: #fff7fb;
        border: 1px solid #ffd4e8;
        text-align: center;
        color: #d81e6c;
        font-weight: 900;
    }

    .score-badge span {
        display: block;
        color: #7a8095;
        font-size: 11px;
        margin-bottom: 3px;
    }

    .panel-summary-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-top: 16px;
    }

    .insight-box {
        border-radius: 14px;
        padding: 14px 15px;
        min-height: 126px;
        border: 1px solid #eef0f6;
    }

    .insight-box.pos { background: #f1fbf7; border-color: #cceee1; }
    .insight-box.neg { background: #fff6f8; border-color: #ffd8e3; }
    .insight-box.need { background: #f5f2ff; border-color: #ddd5ff; }

    .insight-label {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 900;
        margin-bottom: 10px;
    }

    .insight-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
    }

    .insight-dot.pos { background: #13a56f; }
    .insight-dot.neg { background: #e03a6d; }
    .insight-dot.need { background: #7657e6; }

    .insight-box ul,
    .persona-section ul {
        margin: 0;
        padding-left: 18px;
        color: #20283a;
        font-size: 13px;
        font-weight: 650;
        line-height: 1.65;
    }

    .panel-tags {
        margin-top: 13px;
        padding-top: 13px;
        border-top: 1px dashed #e3e6ef;
    }

    .persona-detail-card {
        background: #fff;
        border: 1px solid #eef0f6;
        border-radius: 18px;
        box-shadow: 0 10px 28px rgba(15,29,77,.06);
        padding: 18px;
        min-height: 780px;
    }

    .persona-detail-head {
        display: grid;
        grid-template-columns: auto 1fr auto;
        gap: 12px;
        align-items: center;
        padding-bottom: 14px;
        border-bottom: 1px solid #eef0f6;
    }

    .persona-avatar-small {
        width: 46px;
        height: 46px;
        border-radius: 15px;
        background: linear-gradient(135deg, #ffe1ef, #e7ddff);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 23px;
    }

    .persona-detail-name {
        font-size: 20px;
        font-weight: 900;
        color: #0b1124;
        line-height: 1.25;
    }

    .persona-detail-score {
        border-radius: 13px;
        padding: 8px 10px;
        background: #ff3d8b;
        color: #fff;
        min-width: 60px;
        text-align: center;
        font-size: 13px;
        font-weight: 900;
    }

    .persona-section {
        margin-top: 14px;
        border-radius: 15px;
        border: 1px solid #eef0f6;
        background: #fbfcff;
        padding: 14px;
    }

    .persona-section.story { border-left: 5px solid #0f1d4d; }
    .persona-section.issue { border-left: 5px solid #e84f9a; }
    .persona-section.first { background: #eff7ff; border-color: #cfe6ff; }

    .persona-section-title {
        font-size: 13px;
        font-weight: 900;
        color: #0b1124;
        margin-bottom: 8px;
    }

    .persona-section p {
        margin: 0;
        color: #20283a;
        font-size: 13.5px;
        line-height: 1.65;
        font-weight: 650;
    }

    .persona-two-col {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-top: 12px;
    }

    .persona-two-col .persona-section {
        margin-top: 0;
    }

    .journey-card {
        background: #fff;
        border-radius: 26px;
        padding: 25px;
        box-shadow: 0 12px 30px rgba(15,29,77,.08);
        border: 1px solid #eef0f6;
    }

    .stage-row {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        margin-bottom: 10px;
    }

    .stage {
        border: 2px solid #ff3d8b;
        border-radius: 15px;
        padding: 10px;
        text-align: center;
        font-weight: 900;
        color: #d81e6c;
        background: #fff;
        font-size: 13px;
    }

    .stage small {
        display: block;
        font-size: 10px;
        color: #7a8095;
        margin-top: 3px;
    }

    .journey-table {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
    }

    .journey-box {
        background: #f7f7fb;
        border-radius: 13px;
        padding: 12px;
        font-size: 12px;
        color: #3d4357;
        line-height: 1.55;
        font-weight: 600;
    }

    .journey-box b {
        display: block;
        font-size: 10px;
        color: #7a8095;
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .opp-box {
        background: #ff3d8b;
        color: #fff;
        border-radius: 13px;
        padding: 12px;
        font-size: 12px;
        line-height: 1.55;
        font-weight: 700;
        box-shadow: 0 8px 18px rgba(255,61,139,.25);
    }

    .journey-board {
        background: #fff;
        border: 1px solid #eef0f6;
        border-radius: 18px;
        padding: 24px 26px 28px;
        box-shadow: 0 12px 30px rgba(15,29,77,.08);
        overflow-x: auto;
    }

    .journey-title {
        font-size: 34px;
        font-weight: 900;
        color: #e84f9a;
        margin-bottom: 4px;
    }

    .journey-title span {
        font-size: 15px;
        color: #555;
        font-weight: 600;
        margin-left: 10px;
    }

    .journey-scenario {
        display: grid;
        grid-template-columns: 96px 1fr;
        gap: 14px;
        align-items: center;
        margin: 18px 0 28px;
    }

    .journey-avatar {
        width: 58px;
        height: 58px;
        border-radius: 50%;
        background: linear-gradient(135deg, #ffd9ed, #c996cf);
        border: 2px solid #111;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        justify-self: center;
        box-shadow: 0 6px 14px rgba(232,79,154,.18);
    }

    .journey-scenario-text {
        background: #f9d7e9;
        color: #e84f9a;
        border-radius: 999px;
        padding: 14px 24px;
        font-weight: 900;
        line-height: 1.5;
    }

    .journey-row {
        display: grid;
        grid-template-columns: 112px minmax(820px, 1fr);
        gap: 14px;
        align-items: stretch;
        margin-bottom: 10px;
    }

    .journey-row-label {
        color: #e84f9a;
        font-weight: 900;
        text-align: right;
        padding-top: 14px;
        font-size: 14px;
    }

    .journey-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(150px, 1fr));
        gap: 10px;
    }

    .journey-stage-cell {
        border: 2px solid #ff3d8b;
        border-radius: 8px;
        padding: 12px 10px;
        text-align: center;
        color: #e84f9a;
        font-weight: 900;
        background: #fff;
        min-height: 42px;
    }

    .journey-cell {
        border-radius: 8px;
        padding: 14px;
        line-height: 1.55;
        font-size: 12.5px;
        font-weight: 800;
        color: #171923;
        min-height: 74px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
    }

    .journey-cell.action,
    .journey-cell.touch {
        background: #eef0f6;
    }

    .journey-cell.needs {
        background: #fde0ef;
        color: #d81e6c;
    }

    .journey-cell.opp {
        background: #e84f9a;
        color: #fff;
    }

    .journey-curve-wrap {
        margin: 14px 0 18px;
    }

    .emotion-chart {
        display: grid;
        grid-template-columns: 112px minmax(820px, 1fr);
        gap: 14px;
        align-items: stretch;
        overflow-x: auto;
        padding: 4px 0 0;
    }

    .emotion-axis {
        position: relative;
        height: 260px;
    }

    .emotion-plot {
        position: relative;
        min-width: 820px;
        height: 260px;
    }

    .emotion-axis-label {
        position: absolute;
        left: 0;
        right: 0;
        transform: translateY(-50%);
        color: #7a8095;
        font-size: 12px;
        font-weight: 700;
        text-align: right;
    }

    .emotion-grid-line {
        position: absolute;
        left: 0;
        right: 0;
        height: 1px;
        background: #f1d9e7;
    }

    .emotion-segment {
        position: absolute;
        height: 4px;
        background: #ff3d8b;
        border-radius: 999px;
        transform-origin: left center;
        box-shadow: 0 5px 12px rgba(255,61,139,.18);
    }

    .emotion-node {
        position: absolute;
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: #ffe6f2;
        border: 3px solid #ff3d8b;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 19px;
        transform: translate(-50%, -50%);
        box-shadow: 0 8px 18px rgba(255,61,139,.18);
        z-index: 2;
    }

    .emotion-caption {
        position: absolute;
        width: 150px;
        transform: translateX(-50%);
        background: #fff;
        border-radius: 999px;
        padding: 7px 10px;
        font-size: 11px;
        text-align: center;
        color: #3d4357;
        box-shadow: 0 4px 12px rgba(15,29,77,.08);
        line-height: 1.3;
        font-weight: 700;
        z-index: 3;
    }

    .insight-card {
        background: linear-gradient(135deg, #0f1d4d 0%, #241a4f 100%);
        color: #fff;
        border-radius: 26px;
        padding: 28px;
        box-shadow: 0 12px 30px rgba(15,29,77,.08);
    }

    .download-card {
        background: #fff;
        border-radius: 22px;
        padding: 22px;
        border: 1px solid #eef0f6;
        box-shadow: 0 12px 30px rgba(15,29,77,.08);
    }

    .footer-note {
        margin-top: 28px;
        background: #fff;
        border-radius: 18px;
        padding: 18px 22px;
        border: 1px dashed #c8cdd9;
        font-size: 12px;
        color: #7a8095;
        line-height: 1.7;
    }

    /* Streamlit button readability fix */
    div.stButton > button {
        background: #ffffff !important;
        color: #0f1d4d !important;
        border: 1.5px solid #dfe3ef !important;
        border-radius: 14px !important;
        font-weight: 800 !important;
        box-shadow: 0 8px 18px rgba(15,29,77,.06) !important;
        transition: all .18s ease-in-out !important;
    }

    div.stButton > button:hover {
        background: linear-gradient(135deg, #ff3d8b, #d81e6c) !important;
        color: #ffffff !important;
        border-color: #ff3d8b !important;
        transform: translateY(-1px);
        box-shadow: 0 10px 22px rgba(255,61,139,.28) !important;
    }

    div.stButton > button:active {
        transform: translateY(0px);
    }

    /* Streamlit tab readability fix */
    button[data-baseweb="tab"] {
        color: #3d4357 !important;
        font-weight: 800 !important;
        font-size: 15px !important;
    }

    button[data-baseweb="tab"]:hover {
        color: #ff3d8b !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ff3d8b !important;
        border-bottom-color: #ff3d8b !important;
    }

    div[data-baseweb="tab-highlight"] {
        background-color: #ff3d8b !important;
    }

    /* Text area readability fix */
    textarea {
        background-color: #ffffff !important;
        color: #0b1124 !important;
        border: 1.5px solid #dfe3ef !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
    }

    textarea:focus {
        border-color: #ff3d8b !important;
        box-shadow: 0 0 0 2px rgba(255,61,139,.12) !important;
    }

    label, .stTextArea label {
        color: #0f1d4d !important;
        font-weight: 800 !important;
    }

    @media (max-width: 1000px) {
        .hero-inner,
        .plan-grid,
        .persona-grid,
        .fgi-list,
        .stage-row,
        .journey-table {
            grid-template-columns: 1fr;
        }
        .journey-board {
            padding: 18px;
        }
        .journey-title {
            font-size: 28px;
        }
        .journey-title span {
            display: block;
            margin-left: 0;
            margin-top: 4px;
        }
        .journey-scenario,
        .journey-row {
            grid-template-columns: 1fr;
        }
        .journey-row-label {
            text-align: left;
            padding-top: 6px;
        }
        .panel-summary-grid,
        .persona-two-col {
            grid-template-columns: 1fr;
        }
        .persona-detail-card {
            min-height: auto;
        }
        .hero-title {
            font-size: 30px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# Render functions
# =========================================================

def render_topbar():
    st.markdown(
        """
        <div class="topbar">
            <div class="brand-wrap">
                <div class="brand-logo"><span class="brand-core"></span></div>
                <div>
                    <div class="brand-title">K-Persona Panel <span style="color:#ff3d8b">·</span> Studio</div>
                    <div class="brand-sub">한국형 합성 페르소나 패널 반응 시뮬레이터</div>
                </div>
            </div>
            <div>
                <span class="pill">v 1.0 · Nemotron-Personas-Korea</span>
                <span class="pill pill-live">LIVE DEMO</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_hero():
    st.markdown(
        """
        <div class="hero">
            <div class="hero-inner">
                <div>
                    <div class="tag-row">
                        <span class="tag tag-hot">NEW</span>
                        <span class="tag">FGI Simulation</span>
                        <span class="tag">Synthetic Panel</span>
                        <span class="tag">Marketing AI</span>
                    </div>
                    <div class="hero-title">
                        아이디어를 입력하면,<br>
                        <span class="acc">한국 소비자 패널이 반응</span>합니다.
                    </div>
                    <div class="hero-desc">
                        상품, 서비스, 광고 카피, 상세페이지, 정책 아이디어까지 자연어로 입력하세요.
                        한국형 합성 페르소나 패널이 FGI 인터뷰를 시뮬레이션하고,
                        초기 반응·구매 장벽·Needs·커뮤니케이션 포인트를 한눈에 보여줍니다.
                    </div>
                    <div class="stat-row">
                        <div class="stat-box"><div class="stat-n">Local</div><div class="stat-l">Persona Cache</div></div>
                        <div class="stat-box"><div class="stat-n">1–5명</div><div class="stat-l">Panel Size</div></div>
                        <div class="stat-box"><div class="stat-n">JSON</div><div class="stat-l">Structured Output</div></div>
                        <div class="stat-box"><div class="stat-n">Report</div><div class="stat-l">Auto Generate</div></div>
                    </div>
                </div>
                <div class="input-preview">
                    <div class="preview-label">자연어 입력 예시</div>
                    <div class="preview-title">분석할 상품/서비스/문구 작성 예시</div>
                    <div class="preview-box">
                        “30대 워킹맘을 위한 5분 완성 새벽배송 클린뷰티 세럼.<br>
                        광고 카피: <i>엄마의 5분, 피부의 30대를 되돌려요</i><br>
                        가격은 39,000원, 정기구독 시 20% 할인.”
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_section_header(no, title, subtitle, right_text=None):
    right = f"<div style='font-size:12px;color:#7a8095;font-weight:700'>{escape(right_text)}</div>" if right_text else ""
    st.markdown(
        f"""
        <div class="section-head">
            <div class="section-left">
                <div class="step-no">{no}</div>
                <div>
                    <div class="section-title">{escape(title)}</div>
                    <div class="section-sub">{escape(subtitle)}</div>
                </div>
            </div>
            {right}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_plan(plan):
    item_type = escape(safe_text(plan.get("item_type")))
    task_type = escape(safe_text(plan.get("task_type")))
    target = escape(safe_text(plan.get("target_description")))
    strategy = escape(safe_text(plan.get("panel_strategy")))
    sample = escape(f"{plan.get('sample_size', 3)}명 / {plan.get('gender') or '전체'} / {plan.get('min_age') or '?'}–{plan.get('max_age') or '?'}세")

    st.markdown(
        f"""
        <div class="plan-grid">
            <div class="plan-card">
                <div class="plan-ico">📦</div>
                <div class="plan-k">분석 대상 유형</div>
                <div class="plan-v">{item_type}</div>
            </div>
            <div class="plan-card">
                <div class="plan-ico">🎯</div>
                <div class="plan-k">분석 목적</div>
                <div class="plan-v">{task_type}</div>
            </div>
            <div class="plan-card">
                <div class="plan-ico">👥</div>
                <div class="plan-k">타깃 고객</div>
                <div class="plan-v">{target}</div>
            </div>
            <div class="plan-card">
                <div class="plan-ico">🧬</div>
                <div class="plan-k">패널 구성 전략</div>
                <div class="plan-v">{strategy}</div>
            </div>
            <div class="plan-card accent">
                <div class="plan-ico">⚙️</div>
                <div class="plan-k">샘플 조건</div>
                <div class="plan-v">{sample}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    questions = plan.get("fgi_questions", [])
    q_html = ""
    for i, q in enumerate(questions, start=1):
        q_html += f"""
        <div class="fgi-item">
            <span class="fgi-q">Q{i}</span>
            {escape(str(q))}
        </div>
        """

    st.markdown(
        f"""
        <div class="fgi-card">
            <b>🎙️ Agent가 생성한 FGI 질문지</b>
            <div class="fgi-list">{q_html}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_response_summary_cards(responses):
    """
    기존 긴 dataframe 대신, 웹에서 보기 좋은 반응 요약 카드로 렌더링한다.
    구조는 유지하되 가독성을 높인다.
    """
    cards_html = ""

    for idx, r in enumerate(responses, start=1):
        sr = r.get("structured_response", {})

        name = escape(safe_text(r.get("persona_name"), f"응답자 {idx}"))
        profile = escape(safe_text(r.get("profile")))
        score = escape(str(sr.get("appeal_score", "-")))

        positives = sr.get("positive_points", []) or []
        concerns = sr.get("concerns", []) or []
        needs = sr.get("needs", []) or []
        tags = sr.get("response_tags", []) or []

        cards_html += f"""
<div class="panel-summary-card">
  <div class="panel-summary-top">
    <div>
      <div class="panel-persona-title">{idx}. {name}</div>
      <div class="panel-profile">{profile}</div>
    </div>
    <div class="score-badge"><span>매력도</span>{score}/5</div>
  </div>
  <div class="panel-summary-grid">
    <div class="insight-box pos">
      <div class="insight-label"><span class="insight-dot pos"></span>긍정 요소</div>
      <ul>{render_list_items(positives, limit=2)}</ul>
    </div>
    <div class="insight-box neg">
      <div class="insight-label"><span class="insight-dot neg"></span>우려 사항</div>
      <ul>{render_list_items(concerns, limit=2)}</ul>
    </div>
    <div class="insight-box need">
      <div class="insight-label"><span class="insight-dot need"></span>Needs</div>
      <ul>{render_list_items(needs, limit=2)}</ul>
    </div>
  </div>
  <div class="panel-tags">{render_tag_chips(tags)}</div>
</div>
"""

    render_html(f"""
<div class="panel-stack">
{cards_html}
</div>
""")

def render_persona_card(response, idx):
    """
    HTML이 코드처럼 노출되는 문제를 피하기 위해
    Streamlit 네이티브 컴포넌트 중심으로 렌더링한다.
    """
    sr = response.get("structured_response", {})

    name = escape(safe_text(response.get("persona_name"), f"응답자 {idx}"))
    profile = escape(safe_text(response.get("profile")))
    score = escape(str(sr.get("appeal_score", "-")))

    story = escape(safe_text(sr.get("persona_story")))
    issue = escape(safe_text(sr.get("persona_issue")))
    first = escape(safe_text(sr.get("first_impression")))

    positives = sr.get("positive_points", []) or []
    concerns = sr.get("concerns", []) or []
    pain_points = sr.get("pain_points", []) or []
    needs = sr.get("needs", []) or []
    tags = sr.get("response_tags", []) or []

    render_html(f"""
<div class="persona-detail-card">
  <div class="persona-detail-head">
    <div class="persona-avatar-small">👤</div>
    <div>
      <div class="persona-detail-name">{name}</div>
      <div class="panel-profile">{profile}</div>
    </div>
    <div class="persona-detail-score">{score}/5</div>
  </div>

  <div class="persona-section story">
    <div class="persona-section-title">Story</div>
    <p>{story}</p>
  </div>

  <div class="persona-section issue">
    <div class="persona-section-title">Issue</div>
    <p>{issue}</p>
  </div>

  <div class="persona-section first">
    <div class="persona-section-title">첫인상</div>
    <p>{first}</p>
  </div>

  <div class="persona-two-col">
    <div class="persona-section">
      <div class="insight-label"><span class="insight-dot pos"></span>긍정 요소</div>
      <ul>{render_list_items(positives)}</ul>
    </div>
    <div class="persona-section">
      <div class="insight-label"><span class="insight-dot neg"></span>우려 사항</div>
      <ul>{render_list_items(concerns)}</ul>
    </div>
    <div class="persona-section">
      <div class="insight-label"><span class="insight-dot need"></span>Needs</div>
      <ul>{render_list_items(needs)}</ul>
    </div>
    <div class="persona-section">
      <div class="insight-label"><span class="insight-dot neg"></span>Pain Points</div>
      <ul>{render_list_items(pain_points)}</ul>
    </div>
  </div>

  <div class="panel-tags">{render_tag_chips(tags)}</div>
</div>
""")



def emotion_y(score):
    """
    감정 점수 1~5를 SVG y 좌표로 변환한다.
    점수가 높을수록 위쪽에 위치한다.
    """
    try:
        score = float(score)
    except (ValueError, TypeError):
        score = 3

    score = max(1, min(5, score))
    return 220 - ((score - 1) / 4) * 160


def render_emotion_curve(journey):
    """
    Journey Map 감정 곡선을 HTML/CSS 문자열로 만든다.
    """
    xs = [10, 30, 50, 70, 90]
    ys = [emotion_y(step.get("emotion_score", 3)) for step in journey]
    axis_labels = [
        ("매우 만족", 60),
        ("만족", 100),
        ("보통", 140),
        ("불만", 180),
        ("매우 불만", 220),
    ]

    grid_html = ""
    axis_html = ""
    for label, y in axis_labels:
        grid_html += f"<div class='emotion-grid-line' style='top:{y}px'></div>"
        axis_html += f"<div class='emotion-axis-label' style='top:{y}px'>{label}</div>"

    segment_html = ""
    for idx in range(len(xs) - 1):
        x1, y1 = xs[idx], ys[idx]
        x2, y2 = xs[idx + 1], ys[idx + 1]
        dx = (x2 - x1) * 10
        dy = y2 - y1
        length = (dx ** 2 + dy ** 2) ** 0.5
        angle = math.degrees(math.atan2(dy, dx))
        segment_html += (
            f"<div class='emotion-segment' "
            f"style='left:{x1}%;top:{y1}px;width:{length / 10:.2f}%;transform:rotate({angle:.2f}deg)'></div>"
        )

    node_html = ""
    for x, y, step in zip(xs, ys, journey):
        try:
            score = float(step.get("emotion_score", 3))
        except (ValueError, TypeError):
            score = 3
        comment = escape(str(step.get("emotion_label", "")))
        emoji = "😊" if score >= 4 else "🤔" if score >= 3 else "😟"
        caption = comment if comment else f"감정 점수 {score:g}/5"
        caption_y = min(y + 34, 232)
        node_html += (
            f"<div class='emotion-node' style='left:{x}%;top:{y}px'>{emoji}</div>"
            f"<div class='emotion-caption' style='left:{x}%;top:{caption_y}px'>{caption}</div>"
        )

    return (
        "<div class='emotion-chart'>"
        f"<div class='emotion-axis'>{axis_html}</div>"
        "<div class='emotion-plot'>"
        f"{grid_html}{segment_html}{node_html}"
        "</div>"
        "</div>"
    )


def render_journey_map(journey_result):
    """
    사용자가 첨부한 Journey Map 샘플에 가까운 형태로 렌더링한다.
    """
    if not journey_result:
        st.warning("Journey Map 데이터가 없습니다.")
        return

    scenario = journey_result.get("scenario", "대표 고객 여정 시나리오")
    journey = journey_result.get("journey_map", [])

    if not journey:
        st.warning("Journey Map 데이터가 없습니다.")
        return

    stage_html = ""
    action_html = ""
    touch_html = ""
    needs_html = ""
    opp_html = ""

    for step in journey:
        stage_html += f"<div class='journey-stage-cell'>{escape(str(step.get('stage', '-')))}</div>"
        action_html += f"<div class='journey-cell action'>{escape(str(step.get('action', '-')))}</div>"
        touch_html += f"<div class='journey-cell touch'>{escape(str(step.get('touchpoint', '-')))}</div>"
        needs_html += f"<div class='journey-cell needs'>{escape(str(step.get('need', '-')))}</div>"
        opp_html += f"<div class='journey-cell opp'>{escape(str(step.get('opportunity', '-')))}</div>"

    render_html(f"""
<div class="journey-board">
  <div class="journey-title">
    Journey Map
    <span>유저 시나리오를 토대로 한 고객 여정지도</span>
  </div>
  <div class="journey-scenario">
    <div class="journey-avatar">👤</div>
    <div class="journey-scenario-text">Scenario. {escape(str(scenario))}</div>
  </div>
  <div class="journey-row">
    <div class="journey-row-label">Step</div>
    <div class="journey-grid">{stage_html}</div>
  </div>
  <div class="journey-row">
    <div class="journey-row-label">Action</div>
    <div class="journey-grid">{action_html}</div>
  </div>
  <div class="journey-curve-wrap">
    {render_emotion_curve(journey)}
  </div>
  <div class="journey-row">
    <div class="journey-row-label">Touch point</div>
    <div class="journey-grid">{touch_html}</div>
  </div>
  <div class="journey-row">
    <div class="journey-row-label">Needs</div>
    <div class="journey-grid">{needs_html}</div>
  </div>
  <div class="journey-row">
    <div class="journey-row-label">Opportunity</div>
    <div class="journey-grid">{opp_html}</div>
  </div>
</div>
""")


# =========================================================
# Session state
# =========================================================

for key in ["plan", "responses", "insight", "summary_df", "report_md", "journey_result"]:
    if key not in st.session_state:
        st.session_state[key] = None

if "input_text" not in st.session_state:
    st.session_state["input_text"] = ""


# =========================================================
# Main UI
# =========================================================

render_topbar()
render_hero()

with st.sidebar:
    st.header("⚙️ 실행 옵션")
    sample_size_override = st.slider("패널 수", 1, 5, 3)
    st.caption(
        "현재 버전은 로컬 Ollama 모델과 로컬 persona cache를 사용하는 데모입니다. "
        "배포 시에는 LLM 호출 방식을 API 기반으로 교체하는 것을 추천합니다."
    )

render_section_header(
    "0",
    "분석 요청 입력",
    "상품, 서비스, 광고 문구, 상세페이지, 정책 아이디어를 자연어로 입력하세요."
)

c1, c2, c3 = st.columns(3)

with c1:
    if st.button("클린뷰티 예시", use_container_width=True):
        st.session_state["input_text"] = (
            "30대 워킹맘을 위한 5분 완성 새벽배송 클린뷰티 세럼의 광고 카피를 평가해줘. "
            "광고 카피는 '엄마의 5분, 피부의 30대를 되돌려요'이고 가격은 39,000원, 정기구독 시 20% 할인돼."
        )

with c2:
    if st.button("건강관리 앱 예시", use_container_width=True):
        st.session_state["input_text"] = (
        "5060세대를 대상으로 한 모바일 건강관리 앱 소개 문구가 설득력 있는지 평가해줘. "
        "소개 문구는 '혈압부터 복약 알림, 병원 예약까지. 부모님의 건강 일정을 한눈에 챙기는 쉬운 건강관리 앱'이야. "
        "이 앱은 혈압 기록, 복약 알림, 병원 예약 일정을 한 번에 관리해주는 서비스야."
        )

with c3:
    if st.button("향수 예시", use_container_width=True):
        st.session_state["input_text"] = (
            "비 오는 날의 흙냄새, 젖은 나무, 깨끗한 비누향이 나는 니치 향수를 "
            "30대 한국 여성 직장인에게 팔고 싶어. 너무 무겁지 않고 출근길에도 쓸 수 있는 느낌이면 좋겠어."
        )

user_request = st.text_area(
    "분석 요청",
    key="input_text",
    height=140,
    placeholder="예: 30대 워킹맘을 위한 새벽배송 클린뷰티 세럼 광고 카피를 평가해줘..."
)

run_button = st.button("✨ 패널 소집 후 시뮬레이션 실행", type="primary", use_container_width=True)

if run_button:
    if not user_request.strip():
        st.warning("분석 요청을 입력해 주세요.")
        st.stop()

    with st.spinner("Planner Agent가 리서치 플랜을 설계하는 중..."):
        plan = plan_research_request(user_request)

    plan["sample_size"] = sample_size_override

    with st.spinner("조건에 맞는 페르소나 패널을 구성하는 중..."):
        personas = sample_personas_from_dataset(
            gender=plan.get("gender"),
            min_age=plan.get("min_age"),
            max_age=plan.get("max_age"),
            sample_size=plan.get("sample_size", 3)
        )

    responses = []
    progress = st.progress(0, text="페르소나 응답 생성 중...")

    for idx, persona in enumerate(personas, start=1):
        response = simulate_response(persona=persona, plan=plan)
        responses.append(response)
        progress.progress(idx / len(personas), text=f"{idx}/{len(personas)}명 응답 완료")

    progress.empty()

    structured_responses = [
        {
            "persona_name": r.get("persona_name"),
            "profile": r.get("profile"),
            **r.get("structured_response", {})
        }
        for r in responses
    ]

    with st.spinner("Insight Synthesizer가 종합 인사이트를 생성하는 중..."):
        insight = generate_overall_insight(
            plan=plan,
            persona_responses=structured_responses
        )

    with st.spinner("Journey Map을 생성하는 중..."):
        journey_result = generate_journey_map(
            plan=plan,
            persona_responses=structured_responses
        )

    summary_df = make_summary_dataframe(responses)
    report_md = build_markdown_report(plan, responses, insight)

    st.session_state["plan"] = plan
    st.session_state["responses"] = responses
    st.session_state["insight"] = insight
    st.session_state["summary_df"] = summary_df
    st.session_state["report_md"] = report_md
    st.session_state["journey_result"] = journey_result


# =========================================================
# Results
# =========================================================

if st.session_state["plan"] and st.session_state["responses"]:
    plan = st.session_state["plan"]
    responses = st.session_state["responses"]
    insight = st.session_state["insight"]
    summary_df = st.session_state["summary_df"]
    report_md = st.session_state["report_md"]
    journey_result = st.session_state["journey_result"]

    avg_score = get_average_score(responses)
    avg_score_text = f"{avg_score:.2f} / 5" if avg_score else "-"

    render_section_header(
        "1",
        "리서치 플랜 자동 설계",
        "Planner Agent가 입력을 해석해 패널 구성과 FGI 질문지를 생성합니다.",
        right_text=f"평균 매력도 {avg_score_text}"
    )

    render_plan(plan)

    render_section_header(
        "2",
        "합성 페르소나 패널 반응",
        "Nemotron-Personas-Korea 기반 페르소나가 구조화된 반응을 생성합니다."
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        ["👥 Persona Panel", "🗺 Journey Map", "🎯 Insight", "📥 Download"]
    )

    with tab1:
        st.markdown("### 반응 요약")
        st.caption("표 형태의 원자료는 Download 탭에서 CSV로 받을 수 있습니다. 웹 화면에서는 핵심 반응만 카드형으로 요약합니다.")
        render_response_summary_cards(responses)

        st.divider()

        st.markdown("### 페르소나별 상세 카드")
        row_size = 3

        for start in range(0, len(responses), row_size):
            row = responses[start:start + row_size]
            cols = st.columns(len(row))

            for offset, (col, response) in enumerate(zip(cols, row), start=0):
                with col:
                    render_persona_card(response, start + offset + 1)

    with tab2:
        render_journey_map(journey_result)

    with tab3:
        st.markdown('<div class="insight-card">', unsafe_allow_html=True)
        st.markdown(insight)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab4:
        st.markdown('<div class="download-card">', unsafe_allow_html=True)

        d1, d2 = st.columns(2)

        with d1:
            st.download_button(
                label="CSV 요약표 다운로드",
                data=summary_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="persona_panel_summary.csv",
                mime="text/csv",
                use_container_width=True
            )

        with d2:
            st.download_button(
                label="Markdown 리포트 다운로드",
                data=report_md.encode("utf-8"),
                file_name="persona_panel_report.md",
                mime="text/markdown",
                use_container_width=True
            )

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="footer-note">
        ⚠️ 본 결과는 Nemotron-Personas-Korea 기반 합성 페르소나를 활용한 소비자 반응 가설 생성 결과입니다.
        실제 소비자 조사나 시장 검증을 대체하지 않으며, 후속 인터뷰·설문·A/B 테스트 설계를 위한 탐색적 분석 자료로 활용해야 합니다.
        </div>
        """,
        unsafe_allow_html=True
    )

else:
    st.info("예시 버튼을 누르거나 분석 요청을 입력한 뒤, 시뮬레이션을 실행해 주세요.")
