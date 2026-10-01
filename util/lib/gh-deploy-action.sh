#!/usr/bin/env bash
# gh-deploy-action.sh — Run pre-flight checks, dispatch the Deploy GitHub
# Actions workflow (.github/workflows/deploy.yml) with gh, and wait for it.
#
# Internal helper for `packman.sh <beta|prod> deploy`. Arguments:
#   TARGET BRANCH RESET_DB ASSUME_YES FORCE DRY_RUN COMPACT
# (booleans are "true"/"false"; an empty BRANCH means the current branch).

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/logging.sh"

[[ $# -eq 7 ]] || error "Usage: gh-deploy-action.sh TARGET BRANCH RESET_DB ASSUME_YES FORCE DRY_RUN COMPACT"
target="$1"
branch="$2"
reset_db="$3"
assume_yes="$4"
force="$5"
dry_run="$6"
compact="$7"

require_cmd() {
    command -v "$1" &>/dev/null || error "Required command '$1' not found on PATH"
}

require_cmd git
current_branch="$(git symbolic-ref --quiet --short HEAD || true)"
if [[ -z "$branch" ]]; then
    [[ -n "$current_branch" ]] || error "Not on a branch — pass --branch NAME."
    branch="$current_branch"
fi

header "Deploy $branch to $target"

# ── Hard checks (not overridable) ─────────────────────────────────────────────
case "$target" in
    beta|prod) ;;
    *) error "Unknown deploy target '$target'" ;;
esac

if [[ "$target" == "prod" && "$branch" != "main" ]]; then
    error "Only 'main' can be deployed to prod from this script. To deploy '$branch' to prod, use the Deploy workflow in the GitHub Actions UI."
fi
if [[ "$target" == "prod" && "$reset_db" == "true" ]]; then
    error "--reset-db is only supported for beta"
fi

require_cmd gh
gh auth status >/dev/null 2>&1 || error "gh is not authenticated — run 'gh auth login'"

git ls-remote --exit-code --heads origin "$branch" >/dev/null \
    || error "Branch '$branch' does not exist on origin — push it first"
git fetch --quiet origin "$branch"
sha="$(git rev-parse "origin/$branch")"
info "origin/$branch is at $sha"

if [[ "$target" == "prod" ]]; then
    ci_summary="$(gh run list --workflow django.yml --commit "$sha" --limit 20 \
        --json status,conclusion \
        --jq '(map(select(.conclusion == "success")) | length | tostring) + " " + (map(select(.status != "completed")) | length | tostring)')"
    read -r ci_passed ci_pending <<<"$ci_summary"
    if (( ci_passed == 0 )); then
        if (( ci_pending > 0 )); then
            error "Django CI is still running for $sha — wait for it to pass and try again"
        fi
        error "Django CI has not passed for $sha — prod deploys require a green CI run"
    fi
    success "Django CI passed for $sha"
fi

# ── Workspace checks (overridable with --force) ───────────────────────────────
problems=()

# Local state is irrelevant when deploying a branch other than the one checked out.
if [[ "$current_branch" == "$branch" ]]; then
    if [[ -n "$(git status --porcelain)" ]]; then
        problems+=("This workspace has uncommitted or untracked changes (see 'git status').")
    fi
    ahead="$(git rev-list --count "origin/$branch..HEAD")"
    behind="$(git rev-list --count "HEAD..origin/$branch")"
    (( ahead == 0 )) || problems+=("Local '$branch' has $ahead commit(s) not pushed to origin/$branch.")
    (( behind == 0 )) || problems+=("Local '$branch' is $behind commit(s) behind origin/$branch — origin has code you haven't pulled.")
fi

if [[ "$target" == "prod" ]]; then
    beta_runs="$(gh run list --workflow deploy.yml --status success --commit "$sha" --limit 50 \
        --json displayTitle \
        --jq 'map(select(.displayTitle | test(" to beta( \\(reset db\\))?$"))) | length')"
    (( beta_runs > 0 )) || problems+=("$sha has not been successfully deployed to beta.")
fi

if (( ${#problems[@]} > 0 )); then
    for problem in "${problems[@]}"; do
        warn "$problem"
    done
    if [[ "$force" != "true" ]]; then
        error "Deploy blocked by the warnings above. Resolve them, or re-run with --force to deploy anyway."
    fi
    warn "Continuing despite the warnings above (--force)."
else
    success "Workspace checks passed"
fi

# ── Dispatch ──────────────────────────────────────────────────────────────────
run_cmd=(gh workflow run deploy.yml --ref "$branch" -f "target=$target" -f "reset_db=$reset_db")

if [[ "$dry_run" == "true" ]]; then
    header "Dry run — nothing dispatched"
    info "Target:   $target"
    info "Branch:   $branch"
    info "Commit:   $sha"
    info "Reset DB: $reset_db"
    [[ "$target" == "prod" ]] && info "A prod deploy will require confirmation (or --yes when non-interactive)."
    info "Command:  ${run_cmd[*]}"
    exit 0
fi

if [[ "$target" == "prod" && "$assume_yes" != "true" ]]; then
    [[ -t 0 ]] || error "Prod deploys require confirmation — re-run with --yes when not interactive"
    read -rp "Type 'prod' to deploy $sha to production: " answer
    [[ "$answer" == "prod" ]] || error "Prod deploy cancelled"
fi

dispatched_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
dispatch_output="$("${run_cmd[@]}" 2>&1)" || error "gh workflow run failed: $dispatch_output"
run_url="$(grep -Eo 'https://[^ ]+/actions/runs/[0-9]+' <<<"$dispatch_output" | head -n1 || true)"

if [[ -z "$run_url" ]]; then
    for _ in {1..10}; do
        run_url="$(gh run list --workflow deploy.yml --event workflow_dispatch --branch "$branch" \
            --created ">=$dispatched_at" --limit 1 --json url --jq '.[0].url // empty')"
        [[ -n "$run_url" ]] && break
        sleep 3
    done
fi
[[ -n "$run_url" ]] || error "Dispatched the workflow but could not find its run — check the Actions tab"

run_id="${run_url##*/}"
echo "Run URL: $run_url"

watch_args=(gh run watch "$run_id" --exit-status)
[[ "$compact" == "true" ]] && watch_args+=(--compact)
if "${watch_args[@]}"; then
    success "Deployed $branch ($sha) to $target — $run_url"
else
    error "Deploy of $branch to $target failed — $run_url"
fi
