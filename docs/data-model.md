# Data Model

## raw_metrics 컬럼 매핑

- instance_id: EC2 인스턴스 ID

- metric_name: CPUUtilization, MemoryUtilization 등

- value: 메트릭 값

- observed_at: CloudWatch 타임스탬프 (UTC)

## Zone 매핑 규칙 (v1)

10개 zone 고정. instance_id 기준 매핑.

- 현재는 EC2 B 1대만 존재 예정 (2주차)

- Zone 매핑은 config.yaml에서 instance_id → zone_id 딕셔너리로 관리

- 향후 인스턴스 늘어나면 여기에 추가

## workload_intensity 계산

(cpu_usage + memory_usage) / 2 — 임시 계산식