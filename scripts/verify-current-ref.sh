#!/usr/bin/env bash
# Exit successfully only while the named branch/tag still points to this commit.
set -euo pipefail
remote="${1:?remote required}"
ref_type="${2:?branch or tag required}"
name="${3:?ref name required}"
expected="${4:?commit SHA required}"
[[ "$expected" =~ ^[0-9a-f]{40}$ ]] || exit 1
case "$ref_type" in
  branch) ref="refs/heads/$name" ;;
  tag) ref="refs/tags/$name" ;;
  *) exit 1 ;;
esac
[[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9_./-]*$ ]] || exit 1
listing="$(git ls-remote "$remote" "$ref" "$ref^{}")" || exit 1
found=""
dereferenced=""
while read -r sha candidate; do
  if [ "$candidate" = "$ref" ]; then found="$sha"; fi
  if [ "$candidate" = "$ref^{}" ]; then dereferenced="$sha"; fi
done <<< "$listing"
[ -n "$found" ] && [ "${dereferenced:-$found}" = "$expected" ]
