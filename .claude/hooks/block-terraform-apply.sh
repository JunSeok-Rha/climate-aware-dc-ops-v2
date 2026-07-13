#!/usr/bin/env bash
# PreToolUse hook: Bash 툴로 실행되는 terraform apply/destroy 명령을 차단한다.
# 실제 인프라 적용/삭제는 사람이 직접 해야 한다 (CLAUDE.md 오케스트레이션 원칙 참고).

set -euo pipefail

input="$(cat)"
command="$(echo "$input" | jq -r '.tool_input.command // empty')"

if [ -z "$command" ]; then
  exit 0
fi

if echo "$command" | grep -Eiq '(^|[;&|[:space:]])terraform[[:space:]]+(apply|destroy)([[:space:]]|$)'; then
  echo "차단됨: terraform apply/destroy는 서브에이전트가 실행할 수 없습니다. 사람이 직접 실행해야 합니다." >&2
  exit 2
fi

exit 0
