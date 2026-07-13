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