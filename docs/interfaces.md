# # 서브에이전트 간 인터페이스 계약

이 문서는 CADO v2 파이프라인을 구성하는 서브에이전트들이 서로 주고받는 데이터의

스키마와 함수 시그니처를 정의한다. 서브에이전트를 호출하기 전에 관련 섹션을 반드시

확인하고, 인터페이스를 변경하는 경우 코드와 함께 이 문서도 갱신해야 한다.

전체 흐름: `infra-dev` → `pipeline-dev` → `scoring-dev` → `ai-dev` → `api`

---

## 1. pipeline-dev → scoring-dev

`pipeline-dev`가 수집·정제한 데이터를 `scoring-dev`가 소비하는 계약.

- 모듈: `src/cado/collectors/`, `src/cado/pipeline/` → `src/cado/scoring/`
- 입력 스키마: raw_metrics 테이블
(instance_id, metric_name, value, observed_at)
- 출력 스키마: zone_aggregated_metrics 테이블
(zone_id, aggregated_at, avg_cpu_usage, avg_memory_usage, avg_workload_intensity)
※ zone_aggregated_metrics 산출(집계) 로직 자체는 아직 미구현. 현재 구현된 범위는
raw_metrics row 생성(`CloudWatchCollector`)과 instance_id → zone_id 매핑(`ZoneMapper`)까지이며,
이 둘을 조합해 zone 단위로 집계하는 코드는 `scoring-dev` 또는 별도 파이프라인 단계에서 작성 필요.
- 함수 시그니처 (구현 위치: `src/cado/collectors/cloudwatch_collector.py`,
`src/cado/pipeline/zone_mapper.py`):
`CloudWatchCollector().collect() -> list[dict]`  # async def. raw_metrics row 리스트 반환
`ZoneMapper().map(instance_id: str) -> str`  # zone_id 반환. 실패 시 `ZoneMappingError` 발생
- `collect()`가 반환하는 dict의 정확한 키/타입:
`{"instance_id": str, "metric_name": str, "value": float, "observed_at": datetime}`
(metric_name은 "CPUUtilization" 또는 "MemoryUtilization", observed_at은 UTC aware datetime)
- `ZoneMapper` 세부:
  - 생성자: `ZoneMapper(config_path: str | Path | None = None)`. 기본 경로는
  `src/cado/config.yaml`.
  - 매핑 파일 형식: `config.yaml`의 `instance_to_zone: {instance_id: zone_id}` 딕셔너리.
  zone은 zone_1~zone_10 10개 고정, v1 기준 instance는 1개만 매핑 예정(아직 실제
  인스턴스 ID 미확정 — `.env`의 `CLOUDWATCH_TARGET_INSTANCE_ID`가 채워지면
  `config.yaml`에 해당 키를 추가해야 함).
  - 매핑에 없는 instance_id로 `map()` 호출 시 `ZoneMappingError` 예외 발생 (기본값 반환 없음).
  - 설정 파일이 없으면 `FileNotFoundError`, YAML 파싱 실패 시 `yaml.YAMLError` 발생.
- 에러/재시도 정책:
CloudWatch `get_metric_data` 호출 실패 시 메트릭별로 3회 재시도(지수 백오프), 실패하면 WARN
로그 후 해당 메트릭만 스킵 — `collect()` 전체는 예외를 던지지 않고 빈 리스트/부분 결과를 반환.
- 테스트: `tests/test_cloudwatch_collector.py`, `tests/test_zone_mapper.py` (moto로 CloudWatch
mock, `uv run pytest tests/` 로 실행 — 2026-07-13 기준 8개 전부 통과 확인).

---

## 2. infra-dev → pipeline-dev

`infra-dev`가 프로비저닝한 리소스(자격 증명, 대상 인스턴스, CloudWatch 설정 등)를

`pipeline-dev`가 소비하는 계약.

- 모듈: `terraform/` → `src/cado/pipeline/`, `src/cado/collectors/`
- 제공 리소스: TBD (예: CloudWatch 대상 인스턴스 ID, IAM 역할/정책)
- 환경 변수/출력값: TBD `.env.example` 참고)
- 가정/제약: TBD

---

## 3. scoring-dev → ai-dev

`scoring-dev`가 산출한 점수/랭킹 결과를 `ai-dev`가 소비하는 계약.

- 모듈: `src/cado/pipeline/aggregator.py`, `src/cado/scoring/risk_calculator.py`,
`src/cado/scoring/status_classifier.py` → `src/cado/agents/`
- 입력 스키마: zone_aggregated_metrics 테이블
- 출력 스키마: derived_operational_status 테이블 (zone_id, evaluated_at, heat_risk_score,
cooling_stress_score, zone_imbalance_score, status_level, disclaimer)
※ status_level 매핑은 `StatusClassifier`로 구현됨. disclaimer 생성은 아직 미구현으로
`ai-dev` 또는 별도 단계에서 작성 필요. 현재 구현된 범위는 zone 단위 원시 집계
(`Aggregator`), zone 하나에 대한 3개 score 계산(`RiskCalculator`), score → status_level
band 매핑(`StatusClassifier`)까지.
- 함수 시그니처:
`Aggregator().aggregate() -> None`  # Supabase RPC `aggregate_zone_metrics()` 호출만 수행.
GROUP BY/AVG 등 집계 계산은 SQL 함수 내부에서 처리하고 `zone_aggregated_metrics`에 직접
insert함 — Python 쪽은 RPC 실패 여부만 확인. 실패 시 `AggregationError` 발생.
`RiskCalculator().calculate(zone_metrics: dict, zone_imbalance_score: float = 0.0) -> dict`  #
zone_aggregated_metrics 한 행을 입력받아 아래 3개 score를 계산해 반환:
`{"heat_risk_score": float, "cooling_stress_score": float, "zone_imbalance_score": float}`
(모두 0~~100 clamp). zone_imbalance_score는 파라미터로 전달받으며, 별도로 `calculate_imbalance()`
호출을 통해 계산된 값을 사용해야 함
`StatusClassifier().classify(scores: dict) -> str`  # RiskCalculator.calculate() 반환값
(heat_risk_score/cooling_stress_score/zone_imbalance_score를 포함한 dict)을 입력받아
status_level enum 문자열 중 하나를 반환: "NORMAL", "ADVISORY", "ELEVATED", "WARNING", "CRITICAL".
분류는 우선순위 기반 규칙 체인(CRITICAL → WARNING → ELEVATED → ADVISORY → NORMAL)으로
수행하며, 첫 매칭 규칙에서 결정.
`score_to_band(score: float) -> str`  # 헬퍼. risk score(0~~100)를 band로 매핑:
"LOW"(0~~<30), "MEDIUM"(30~~<55), "HIGH"(55~~<75), "EXTREME"(75~~)
`imbalance_to_band(score: float) -> str`  # 헬퍼. imbalance score(0~~100)를 band로 매핑:
"NONE"(0~~<20), "MODERATE"(20~~<50), "SEVERE"(50~~)
- `RiskCalculator` 세부:
  - 생성자: `RiskCalculator(config_path: str | Path | None = None)`. 기본 경로는
  `src/cado/config.yaml`.
  - 가중치는 `config.yaml`의 `risk_weights.heat_risk` / `risk_weights.cooling_stress` 섹션에서
  로드 (하드코딩 없음). `risk_weights` 섹션이 없으면 `RiskCalculationError` 발생.
  - `zone_metrics`에 `temperature`/`humidity` 키가 없거나 값이 `None`이면 0으로 처리
  (NULL-safe) — 현재 `zone_aggregated_metrics` 스키마엔 이 두 컬럼이 아예 없음.
  - `zone_imbalance_score`는 `calculate()` 호출 시 파라미터로 전달해야 하며, 기본값은 0.0.
  실제 값은 `calculate_imbalance(all_zones)` 메서드로 zone 간 비교를 수행하여 얻음.
- `Aggregator` 세부:
  - 호출하는 RPC: `aggregate_zone_metrics` (Supabase/Postgres 쪽에 이미 정의되어 있다고 가정).
  - RPC 실패(에러 응답 또는 호출 자체 실패) 시 `AggregationError` 발생 — 조용히 삼키지 않음.
- 우선순위/임계값 정의: `docs/status-classification.md` 참고 (score band: LOW/MEDIUM/HIGH/EXTREME,
imbalance band: NONE/MODERATE/SEVERE — band 매핑은 `StatusClassifier`로 구현됨. 13개
우선순위 규칙에 따라 status_level 분류)
- 테스트: `tests/test_risk_calculator.py` (RiskCalculator.calculate() 8개 + calculate_imbalance()
7개), `tests/test_status_classifier.py` (StatusClassifier 13개 + band helper 7개)
(`uv run pytest tests/` 로 실행 — 2026-07-14 기준 전체 43개 전부 통과 확인). Aggregator는
Supabase RPC 의존이라 별도 테스트 없음 (요청 범위 아님).
- status_level enum 값: NORMAL, ADVISORY, ELEVATED, WARNING, CRITICAL
`RiskCalculator().calculate_imbalance(all_zones: list[dict]) -> dict[str, float]`  #
zone 간 CPU 사용률 비교를 통해 각 zone의 imbalance_score를 계산. 입력:
`all_zones`는 zone_aggregated_metrics 여러 행(dict 리스트), 각 dict는 최소 `zone_id`와
`avg_cpu_usage` 키를 포함해야 함. 반환: `{zone_id: imbalance_score(0~~100)}` dict.
zone이 1개뿐이면 해당 zone에 0.0 반환(비교 대상 없음). 모든 zone의 avg_cpu_usage가 동일하면
전부 0.0 반환(편차 없음). MAD(median absolute deviation) 기반으로 정규화하며,
median으로부터 MAD만큼 떨어진 zone은 약 50점, 2*MAD 이상 떨어지면 100점(clamp됨)

---

## 4. ai-dev → api

`ai-dev`가 생성한 조사/분석 결과를 `api`가 소비하여 클라이언트에 노출하는 계약.

- 모듈: `src/cado/agents/` → `src/cado/api/`
- 입력 스키마: TBD
- 응답(API) 스키마: TBD
- 엔드포인트 목록: TBD
- 에러 응답 형식: TBD

---

## 5. scoring-dev → api (직접 연동, ai-dev 이전 임시 경로)

`ai-dev`의 disclaimer 생성이 아직 없어, `derived_operational_status` 테이블에
쓰는 별도 배치 없이 `api` 레이어가 `zone_aggregated_metrics`를 직접 읽어
`RiskCalculator`/`StatusClassifier`로 즉석 계산한다. `ai-dev`가 disclaimer를
포함한 영속 계층을 만들면 이 경로는 대체될 예정.

- 모듈: `src/cado/scoring/risk_calculator.py`, `src/cado/scoring/status_classifier.py`
  → `src/cado/api/routes.py`
- 입력: `zone_aggregated_metrics` 테이블에서 zone_id별 최신 row(aggregated_at desc, 첫 row)만
  사용. `CloudWatchCollector`/`ZoneMapper`/`Aggregator`는 이 테이블을 채우는 업스트림
  파이프라인 단계이며, API 요청 경로에서 직접 호출하지 않는다(GET 요청에서 수집·집계를
  트리거하지 않음).
- 엔드포인트:
  - `GET /api/zones`: config.yaml의 `zones`(zone_1~zone_10) 10개 전체를 반환하며, 각 zone의
    `status_level`을 포함. `zone_aggregated_metrics`에 아직 집계 데이터가 없는 zone은
    `status_level: null`로 표시(목록에서 누락하지 않음).
  - `GET /api/zones/{zone_id}/status`: 단일 zone의 `heat_risk_score`, `cooling_stress_score`,
    `zone_imbalance_score`, `status_level` 반환.
- 에러 응답: `zone_id`가 config.yaml의 10개 zone 목록에 없거나, 유효한 zone_id이지만
  `zone_aggregated_metrics`에 아직 데이터가 없는 경우 모두 404 반환(둘 다 "해당 zone의
  상태를 알 수 없음"으로 취급). 두 경우는 `detail` 메시지 문구로만 구분됨.
- imbalance 계산: 매 요청마다 그 시점에 데이터가 존재하는 zone들만 모아
  `RiskCalculator.calculate_imbalance()`로 재계산(캐싱 없음).

---

## 모듈 의존성 그래프 (병렬 작업 판단용)

```
collectors/ (CloudWatch)     ─┐
pipeline/ (Aggregator)        ├─→ scoring/ (Risk, Status)  ─→ agents/ (AI) ─→ api/
                              ─┘
```

병렬 가능 조합 예시:
- collectors/ 작업 중 agents/ 작업 (agents는 mock 데이터로 개발 가능)
- infra/ 작업 중 scoring/ 작업 (서로 파일 안 겹침)

병렬 불가 조합:
- collectors/ 작업 중 pipeline/ 작업 (pipeline이 collectors 출력에 의존)

