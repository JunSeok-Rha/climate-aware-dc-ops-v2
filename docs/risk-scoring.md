# Risk Scoring

## v1 가중치 초기값

heatRiskScore = temperature(0.4) + cpu(0.35) + workload(0.25)

coolingStressScore = temperature(0.35) + humidity(0.25) + cpu(0.25) + memory(0.15)

zoneImbalanceScore = MAD 기반 정규화 (0~100)

## Threshold 초기값

score band: LOW(0~30) / MEDIUM(30~55) / HIGH(55~75) / EXTREME(75+)

imbalance band: NONE(0~20) / MODERATE(20~50) / SEVERE(50+)

## 설계 전제

가중치는 config.yaml 외부화. 검증 결과 후 조정 가능.

temperature 데이터 없는 환경(CloudWatch만 사용)에서는

temperature 항목을 0으로 처리 (NULL-safe).

## zoneImbalanceScore v2 (재설계)

기존 문제 (2026-07-13 발견):

calculate(zone_metrics: dict) -> dict 형태로 zone 하나만 입력받는 구조라

"zone 간 편차"를 계산할 방법이 없었음. 임시로 동일 row 내

cpu/memory/workload 3개 지표 간 MAD로 근사 처리했음.

v2 설계:

calculate_imbalance(all_zones: list[dict]) -> dict[str, float]

- all_zones: zone_aggregated_metrics 여러 행 (동일 aggregated_at 기준)

- 각 zone의 avg_cpu_usage를 전체 zone 평균과 비교해 MAD 기반 편차 계산

- 0~100으로 정규화, zone_id를 key로 하는 dict 반환

- zone이 1개뿐이면 해당 zone에 0 반환 (비교 대상 없음)

## 가중치 파일 참고

config.yaml의 risk_weights 섹션에 heat_risk, cooling_stress 가중치 있음.

zoneImbalance는 가중치가 아닌 통계적 정규화 방식이라 별도 파라미터 없음.

