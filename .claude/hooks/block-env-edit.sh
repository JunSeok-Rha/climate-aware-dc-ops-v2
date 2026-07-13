#!/usr/bin/env bash
# PreToolUse hook: .env 파일 수정을 차단한다 (.env.example은 허용).
# Edit/Write 툴의 file_path와 Bash 툴의 command(리다이렉션 등) 모두 검사한다.
# 비밀값 관리는 사람이 직접 해야 한다 (CLAUDE.md 오케스트레이션 원칙 참고).

set -euo pipefail

input="$(cat)"
tool_name="$(echo "$input" | jq -r '.tool_name // empty')"

is_blocked_env_path() {
  local path="$1"
  # .env.example 등 .env.* 접미사가 붙은 파일은 허용, 순수 .env(경로 끝)만 차단
  if [[ "$path" =~ (^|/)\.env$ ]]; then
    return 0
  fi
  return 1
}

case "$tool_name" in
  Edit|Write)
    file_path="$(echo "$input" | jq -r '.tool_input.file_path // empty')"
    if [ -n "$file_path" ] && is_blocked_env_path "$file_path"; then
      echo "차단됨: .env 파일은 서브에이전트가 직접 수정할 수 없습니다. 필요한 키는 .env.example에 반영하고, 실제 값 설정은 사람이 직접 해야 합니다." >&2
      exit 2
    fi
    ;;
  Bash)
    command="$(echo "$input" | jq -r '.tool_input.command // empty')"
    if [ -n "$command" ] && echo "$command" | grep -Eq '(^|[^.[:alnum:]_])\.env([^.[:alnum:]_]|$)' \
       && ! echo "$command" | grep -Eq '\.env\.[[:alnum:]_.]+'; then
      if echo "$command" | grep -Eq '(>>?|tee|cp[[:space:]].*[[:space:]]|mv[[:space:]].*[[:space:]]|rm[[:space:]]|sed[[:space:]]+-i|vi[m]?[[:space:]]|nano[[:space:]]).*\.env([^.[:alnum:]_]|$)'; then
        echo "차단됨: .env 파일은 서브에이전트가 직접 수정할 수 없습니다. 필요한 키는 .env.example에 반영하고, 실제 값 설정은 사람이 직접 해야 합니다." >&2
        exit 2
      fi
    fi
    ;;
esac

exit 0
