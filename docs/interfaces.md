# 서브에이전트 간 인터페이스 계약

이 문서는 CADO v2 파이프라인을 구성하는 서브에이전트들이 서로 주고받는 데이터의
스키마와 함수 시그니처를 정의한다. 서브에이전트를 호출하기 전에 관련 섹션을 반드시
확인하고, 인터페이스를 변경하는 경우 코드와 함께 이 문서도 갱신해야 한다.

전체 흐름: `infra-dev` → `pipeline-dev` → `scoring-dev` → `ai-dev` → `api`

---

## 1. pipeline-dev → scoring-dev

`pipeline-dev`가 수집·정제한 데이터를 `scoring-dev`가 소비하는 계약.

- **모듈**: `src/cado/pipeline/` → `src/cado/scoring/`
- **입력 스키마**: TBD
- **출력 스키마**: TBD
- **함수 시그니처**: TBD
- **에러/재시도 정책**: TBD

---

## 2. infra-dev → pipeline-dev

`infra-dev`가 프로비저닝한 리소스(자격 증명, 대상 인스턴스, CloudWatch 설정 등)를
`pipeline-dev`가 소비하는 계약.

- **모듈**: `terraform/` → `src/cado/pipeline/`, `src/cado/collectors/`
- **제공 리소스**: TBD (예: CloudWatch 대상 인스턴스 ID, IAM 역할/정책)
- **환경 변수/출력값**: TBD (`.env.example` 참고)
- **가정/제약**: TBD

---

## 3. scoring-dev → ai-dev

`scoring-dev`가 산출한 점수/랭킹 결과를 `ai-dev`가 소비하는 계약.

- **모듈**: `src/cado/scoring/` → `src/cado/agents/`
- **입력 스키마**: TBD
- **출력 스키마**: TBD
- **함수 시그니처**: TBD
- **우선순위/임계값 정의**: TBD

---

## 4. ai-dev → api

`ai-dev`가 생성한 조사/분석 결과를 `api`가 소비하여 클라이언트에 노출하는 계약.

- **모듈**: `src/cado/agents/` → `src/cado/api/`
- **입력 스키마**: TBD
- **응답(API) 스키마**: TBD
- **엔드포인트 목록**: TBD
- **에러 응답 형식**: TBD
