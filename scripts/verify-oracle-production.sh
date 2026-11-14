#!/usr/bin/env bash
set -euo pipefail
[[ "$GITHUB_REPOSITORY" == izafar22/voltx && "$GITHUB_EVENT_NAME" == workflow_dispatch ]]
[[ "$GITHUB_REF" =~ ^refs/heads/release_[0-9]{8}_version[0-9]+\.[0-9]+\.[0-9]+$ ]]
[[ "${UNIFIED_ENABLED:-}" == true && "${LEGACY_ENABLED:-}" != true ]] ||
  { echo 'Unified production must be explicitly enabled and legacy deployment disabled'; exit 1; }
gh api "repos/$GITHUB_REPOSITORY/environments/production" |
  jq -e '.can_admins_bypass == false and .deployment_branch_policy.custom_branch_policies == true and
    any(.protection_rules[]; .type == "required_reviewers" and .prevent_self_review == true and (.reviewers | length) > 0)' >/dev/null ||
  { echo 'Production reviewer policy is missing or unsafe'; exit 1; }

if [[ "${1:-}" == approval ]]; then
  gh api "repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/approvals" |
    jq -e --arg actor "$GITHUB_ACTOR" 'any(.[]; .state == "approved" and .user.login != $actor and
      any(.environments[]; .name == "production"))' >/dev/null ||
    { echo 'No independent production approval recorded'; exit 1; }
  exit
fi

[[ "$APPROVED_SHA" =~ ^[0-9a-f]{40}$ && "$APPROVED_SHA" == "$GITHUB_SHA" ]]
gh api --method GET "repos/$GITHUB_REPOSITORY/actions/workflows/tests.yml/runs" \
  -f branch="$GITHUB_REF_NAME" -f event=push -f head_sha="$GITHUB_SHA" -f status=completed |
  jq -er --arg sha "$GITHUB_SHA" --arg branch "$GITHUB_REF_NAME" --arg repo "$GITHUB_REPOSITORY" '
    .workflow_runs | map(select(.head_sha == $sha and .head_branch == $branch and .event == "push"
      and .head_repository.full_name == $repo)) | max_by(.run_number) |
    select(.conclusion == "success") |
    "run_id=\(.id)\nattempt=\(.run_attempt)\nsequence=\(.run_number)"' >> "$GITHUB_OUTPUT"
