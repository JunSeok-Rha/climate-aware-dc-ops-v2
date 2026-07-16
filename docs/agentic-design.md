# Agentic Design

## Zone Intelligence Agent
입력: zone_id + 최근 derived_operational_status 1~3개 행
출력: 1~2문장 자연어 분석
목적: "이 zone이 왜 이 상태인지" 사람이 읽을 수 있게 설명

## 프롬프트 원칙
- 수치를 그대로 나열하지 않고 해석을 제공
- disclaimer 원칙 유지 (heuristic indicator라는 걸 응답에 은연중 반영)
- 응답은 1~2문장으로 제한 (토큰 비용 관리)