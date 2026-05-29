# simulator.py

from llm_client import generate_persona_response


def simulate_response(persona, plan):
    """
    한 명의 페르소나 반응을 LLM으로 생성한다.
    이제 응답은 구조화된 dict 형태로 저장된다.
    """
    structured_response = generate_persona_response(
        persona=persona,
        plan=plan
    )

    return {
        "persona_name": persona.get("name", "익명 페르소나"),
        "profile": f"{persona.get('age')}세 {persona.get('gender')}, {persona.get('region')} 거주, {persona.get('job')}",
        "age": persona.get("age"),
        "gender": persona.get("gender"),
        "region": persona.get("region"),
        "job": persona.get("job"),
        "structured_response": structured_response
    }