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

- 모듈: `src/cado/scoring/` → `src/cado/agents/`

- 입력 스키마: TBD

- 출력 스키마: TBD

- 함수 시그니처: TBD

- 우선순위/임계값 정의: TBD

---

## 4. ai-dev → api

`ai-dev`가 생성한 조사/분석 결과를 `api`가 소비하여 클라이언트에 노출하는 계약.

- 모듈: `src/cado/agents/` → `src/cado/api/`

- 입력 스키마: TBD

- 응답(API) 스키마: TBD

- 엔드포인트 목록: TBD

- 에러 응답 형식: TBD

