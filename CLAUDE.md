# CADO v2

CADO v2는 AWS 인프라 이상 징후를 수집·분석하고, LLM 기반 에이전트로 점수화·조사·보고까지
자동화하는 파이프라인이다.

## 기술 스택

- **언어/런타임**: Python 3.12
- **웹 프레임워크**: FastAPI
- **DB / 백엔드**: Supabase (Postgres)
- **AWS 연동**: boto3 (CloudWatch, EC2 등)
- **LLM**: Anthropic SDK (Claude)
- **테스트**: pytest
- **패키지/환경 관리**: uv

## 디렉토리 구조

```
src/cado/
  collectors/   # AWS/CloudWatch 등 원시 데이터 수집
  pipeline/     # 수집 데이터 정제 및 오케스트레이션
  scoring/      # 이상 징후 스코어링 로직
  agents/       # LLM 기반 조사/분석 에이전트
  api/          # FastAPI 엔드포인트
  db/           # Supabase/Postgres 액세스 레이어
docs/
  interfaces.md     # 서브에이전트 간 인터페이스 계약
  postmortem/        # 장애/이슈 회고 문서
tests/
terraform/            # 인프라 정의 (apply는 사람이 직접 실행)
.claude/
  agents/             # 서브에이전트 정의
  hooks/              # PreToolUse 등 안전장치 훅
```

## 오케스트레이션 원칙

이 프로젝트는 메인 Claude Code 세션이 **마스터 오케스트레이터** 역할을 하고,
실제 구현 작업은 `.claude/agents/`에 정의된 서브에이전트에게 Task tool로 위임하는
구조로 진행한다.

1. **메인 세션 = 마스터.** 메인 세션은 직접 코드를 대량으로 작성하지 않고,
   작업을 적절한 서브에이전트(`pipeline-dev`, `scoring-dev`, `ai-dev`, `infra-dev`,
   `test-writer`)에게 분배하고 결과를 통합하는 역할을 한다.
2. **서브에이전트 호출 전 `docs/interfaces.md`를 반드시 확인한다.** 서브에이전트 간
   주고받는 데이터 스키마와 함수 시그니처는 이 문서에 계약으로 명시되어 있으며,
   서브에이전트에게 작업을 위임할 때 관련 인터페이스 섹션을 함께 전달한다.
   인터페이스가 바뀌면 반드시 `docs/interfaces.md`를 함께 갱신한다.
3. **중첩 서브에이전트는 `infra-dev`만 허용한다.** 다른 서브에이전트는 Agent(Task)
   tool을 사용할 수 없다. `infra-dev`만 인프라 관련 하위 작업을 추가로 위임할 수 있다.
4. **사람이 직접 해야 하는 작업**은 서브에이전트에게 위임하지 않는다:
   - Docker 실행/빌드 (`docker run`, `docker build`, `docker compose`, `docker exec`)
   - `terraform apply` / `terraform destroy`
   - `.env` 파일 수정 (`.env.example`은 예외적으로 자유롭게 수정 가능)

   이 세 가지는 `.claude/hooks/`에 등록된 PreToolUse 훅으로 강제 차단된다.

## 작업 시 체크리스트

- 새 기능을 시작하기 전, 관련 인터페이스가 `docs/interfaces.md`에 정의되어 있는지 확인한다.
- 서브에이전트를 호출할 때는 해당 에이전트의 `context_files`에 명시된 문서를 함께 참고하게 한다.
- 인프라 변경(terraform, Docker)은 계획만 세우고 실제 적용은 사람에게 요청한다.
- 비밀값은 `.env`에만 두고 커밋하지 않는다. 필요한 키 목록은 `.env.example`에 반영한다.
