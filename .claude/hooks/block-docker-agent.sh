#!/usr/bin/env bash
# PreToolUse hook: Bash 툴로 실행되는 docker run/build/compose/exec 명령을 차단한다.
# Docker 실행은 사람이 직접 해야 한다 (CLAUDE.md 오케스트레이션 원칙 참고).

set -euo pipefail

input="$(cat)"
command="$(echo "$input" | jq -r '.tool_input.command // empty')"

if [ -z "$command" ]; then
  exit 0
fi

# 실행되는 첫 번째 토큰만 확인한다 (예: git commit -m 안의 "docker build" 같은
# 텍스트 오탐을 방지하기 위해, 커맨드 문자열 전체가 아니라 실제 실행 명령만 본다).
read -r first second _ <<< "$command"

if [ "$first" = "docker" ] && [[ "$second" =~ ^(run|build|compose|exec)$ ]]; then
  echo "차단됨: Docker 실행/빌드 명령은 서브에이전트가 실행할 수 없습니다. 사람이 직접 실행해야 합니다." >&2
  exit 2
fi

exit 0
