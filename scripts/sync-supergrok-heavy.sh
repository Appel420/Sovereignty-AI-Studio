#!/usr/bin/env bash
set -euo pipefail

SOURCE_REPO="https://github.com/Sovereignty-One/SuperGrok-Heavy-4-2-Skeleton.git"
SOURCE_REMOTE="supergrok-heavy"
SOURCE_BRANCH="main"
TARGET_PREFIX="vendor/supergrok-heavy-4-2-skeleton"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: run this script from inside the Sovereignty-AI-Studio git repository" >&2
  exit 1
fi

if ! git remote get-url "${SOURCE_REMOTE}" >/dev/null 2>&1; then
  git remote add "${SOURCE_REMOTE}" "${SOURCE_REPO}"
fi

git fetch "${SOURCE_REMOTE}" "${SOURCE_BRANCH}"

if git log --oneline -- "${TARGET_PREFIX}" | grep -q .; then
  echo "Updating ${TARGET_PREFIX} from ${SOURCE_REMOTE}/${SOURCE_BRANCH} using git subtree pull"
  git subtree pull --prefix="${TARGET_PREFIX}" "${SOURCE_REMOTE}" "${SOURCE_BRANCH}" --squash
else
  echo "Adding ${TARGET_PREFIX} from ${SOURCE_REMOTE}/${SOURCE_BRANCH} using git subtree add"
  git subtree add --prefix="${TARGET_PREFIX}" "${SOURCE_REMOTE}" "${SOURCE_BRANCH}" --squash
fi

echo "SuperGrok Heavy sync complete. Review changes, run checks, then open a pull request."
