# Source of Truth
작업 전 반드시 실제 파일을 확인한다. 프롬프트에 임의 버전/값을 넣지 않는다.

- Python 버전: pyproject.toml
- DB 스키마: Supabase Table Editor (원본) / docs/data-model.md (문서)
- 인터페이스 계약: docs/interfaces.md
- 가중치/threshold: config.yaml / docs/risk-scoring.md
- 상태 분류 조건: docs/status-classification.md
- 로컬 개발 환경 주의사항: 프로젝트가 iCloud 동기화 범위(예: ~/Desktop) 안에 있으면 .venv가 dataless 파일화되어 pytest가 극도로 느려질 수 있음. venv는 iCloud 밖에 위치해야 함 (예: UV_PROJECT_ENVIRONMENT + direnv).
