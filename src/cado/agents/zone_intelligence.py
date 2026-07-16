"""Zone Intelligence Agent - provides natural language analysis of zone operational status."""

import anthropic
from cado.config import settings


def analyze(zone_id: str, recent_status: list[dict]) -> str:
    """Analyze recent operational status for a zone and return natural language explanation.

    Args:
        zone_id: The zone identifier (e.g., "zone_1")
        recent_status: List of 1-3 recent derived_operational_status dicts, each containing:
            - zone_id: str
            - evaluated_at: timestamp
            - heat_risk_score: float (0-100)
            - cooling_stress_score: float (0-100)
            - zone_imbalance_score: float (0-100)
            - status_level: str (NORMAL/ADVISORY/ELEVATED/WARNING/CRITICAL)

    Returns:
        1-2 sentence natural language analysis explaining why the zone is in its current state,
        or exactly "분석 일시 불가" if API call fails.
    """
    if not recent_status:
        return "분석 일시 불가"

    # Build context from recent status
    status_summary = []
    for status in recent_status:
        status_summary.append(
            f"Status: {status.get('status_level', 'UNKNOWN')}, "
            f"Heat Risk: {status.get('heat_risk_score', 0):.1f}, "
            f"Cooling Stress: {status.get('cooling_stress_score', 0):.1f}, "
            f"Zone Imbalance: {status.get('zone_imbalance_score', 0):.1f}"
        )

    prompt = f"""Zone {zone_id}의 최근 상태 데이터를 분석해주세요:

{chr(10).join(status_summary)}

이 zone이 현재 상태가 된 이유를 1-2문장으로 간결하게 설명해주세요.
수치를 단순 나열하지 말고 해석을 제공하세요.
이 분석은 heuristic indicator에 기반한 것임을 암시하는 표현을 사용하세요."""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=150,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Extract text from response
        if message.content and len(message.content) > 0:
            return message.content[0].text
        else:
            return "분석 일시 불가"

    except Exception:
        # Any API error (network, rate limit, authentication, etc.) returns fallback
        return "분석 일시 불가"
