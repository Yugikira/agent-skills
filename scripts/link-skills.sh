#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGETS=(
  "${HOME}/.claude/skills"
  "${HOME}/.cursor/skills"
  "${HOME}/.agents/skills"
)
PROMOTED_BUCKETS=("meta" "custom")

for target in "${TARGETS[@]}"; do
  mkdir -p "${target}"
  # Remove stale symlinks pointing into this repo
  for link in "${target}"/*; do
    if [[ -L "${link}" ]]; then
      dest="$(readlink "${link}")"
      if [[ "${dest}" == "${REPO_ROOT}/skills/"* ]]; then
        rm "${link}"
      fi
    fi
  done

  # Symlink every promoted skill
  for bucket in "${PROMOTED_BUCKETS[@]}"; do
    bucket_dir="${REPO_ROOT}/skills/${bucket}"
    [[ -d "${bucket_dir}" ]] || continue
    for skill_dir in "${bucket_dir}"/*; do
      [[ -d "${skill_dir}" && -f "${skill_dir}/SKILL.md" ]] || continue
      skill_name="$(basename "${skill_dir}")"
      ln -sfn "${skill_dir}" "${target}/${skill_name}"
    done
  done
  echo "Linked promoted skills into ${target}"
done
