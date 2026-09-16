# GitHub Bug Report: Ghost Workflow Registry Poison

**GitHub Issue Reference:** [#1062](https://github.com/Appel420/Sovereignty-AI-Studio/issues/1062)  
**Report Date:** 2026-09-15  
**Severity:** CRITICAL — Blocks all Actions workflows across repository  
**Platform Defect:** Ghost workflow cache / registry persistence

---

## Executive Summary

A **deleted GitHub Actions workflow** (BuildFailed, ID: 352495736) persists in GitHub's internal registry and continues to intercept all repository events (push, pull_request, workflow_dispatch). This deleted workflow:

1. Has **zero jobs** in its definition
2. Fails at `startup_failure` on every event trigger
3. **Blocks all legitimate workflows** from executing
4. Persists across **fork creation** (appears in Appel420/Sovereignty-AI-Studio-v1.0.1 fork as well)
5. **Cannot be manually deleted or cleared** via UI or API

---

## Reproduction Steps

### Prerequisites
- Repository: `Appel420/Sovereignty-AI-Studio` (also forked at `Sovereignty-One/Sovereignty-AI-Studio_v1.0.1`)
- Branch: `Collaboration` (and other protected branches)

### Steps to Reproduce

1. **Check workflow run history:**
   ```
   https://github.com/Appel420/Sovereignty-AI-Studio/actions
   ```

2. **Observe all recent workflow runs** (past 12+ hours):
   - Filter by conclusion: `failure`
   - All show status: `startup_failure`
   - All show 0 jobs completed

3. **Verify the orphaned workflow:**
   - Query the Actions API (see API section below)
   - No workflow file named `BuildFailed` or ID 352495736 exists in `.github/workflows/`
   - File is completely deleted from repository history

4. **Push a new commit** to any branch:
   - Legitimate workflows are registered in `.github/workflows/` (ci.yml, Flake8.yml, etc.)
   - Expected: These workflows should run
   - **Actual:** All workflows fail at `startup_failure` with "0 jobs"
   - The ghost BuildFailed workflow intercepts the event first

5. **Fork the repository:**
   - Problem persists in forked copy
   - Suggests issue is in GitHub's **global Actions registry**, not local repo state

---

## Technical Details

### Affected Workflow Runs

**Primary Repository:** `Appel420/Sovereignty-AI-Studio`

| Run ID | Workflow Name | Status | Conclusion | Jobs | Time |
|--------|---------------|--------|-----------|------|------|
| 35037313500 | Quart App CI | completed | startup_failure | 0 | 2026-09-15T23:53:20Z |
| 35037312716 | CI | completed | startup_failure | 0 | 2026-09-15T23:53:13Z |
| 35037312052 | Flake8 Lint | completed | startup_failure | 0 | 2026-09-15T23:53:06Z |
| 35037311417 | Python CI | completed | startup_failure | 0 | 2026-09-15T23:52:54Z |
| 35037310874 | Pylint | completed | success | 1 | 2026-09-15T23:52:40Z |
| (and many more) | — | — | startup_failure | 0 | — |

**Forked Repository:** `Sovereignty-One/Sovereignty-AI-Studio_v1.0.1`  
Same pattern observed with identical workflow run failures.

### Ghost Workflow Characteristics

- **Name:** BuildFailed
- **Internal ID:** 352495736
- **Status:** Deleted from `.github/workflows/` directory
- **Current State:** Exists in Actions registry but not in codebase
- **Job Count:** 0
- **Trigger Events:** Intercepts `push`, `pull_request`, `workflow_dispatch`

### Git History Verification

No reference to `BuildFailed` workflow exists in recent commits:

```bash
# No matching files in .github/workflows/
$ git ls-tree -r HEAD -- .github/workflows/ | grep -i buildfailed
# (no output)

# No references in commit history
$ git log --all --name-status -- "BuildFailed*"
# (no matching commits)

# File is completely removed from history
$ git show HEAD:.github/workflows/BuildFailed.yml
# fatal: path '.github/workflows/BuildFailed.yml' does not exist in 'HEAD'
```

---

## Impact Assessment

### Direct Impact
- ✅ **All GitHub Actions workflows blocked** across all branches
- ✅ **CI/CD pipeline completely halted**
- ✅ **Cannot test code changes** (push/PR events fail silently)
- ✅ **Security scanning disabled** (CodeQL, SAST workflows fail)
- ✅ **Dependency monitoring offline** (dep-health.yml unreachable)

### Cascading Impact
- **Fork operations inherit the poison** — issue follows repository copies
- **Manual workflow_dispatch runs fail** — even explicit manual triggers blocked
- **No workaround available** — cannot be resolved at repository level

### Business Impact
- Deployment pipeline completely broken
- Cannot validate code quality before merge
- Security posture degraded (no automated scanning)
- Development velocity blocked

---

## Attempted Workarounds (All Failed)

### ❌ Workaround #1: Delete and Recreate `.github/workflows/`
**Result:** Ghost workflow persists. All workflows still fail with `startup_failure`.

### ❌ Workaround #2: Force-push clean state
**Result:** Ghost workflow still intercepts events. Problem returns on next push.

### ❌ Workaround #3: Rename all workflow files
**Result:** Ghost workflow prevents new workflows from running at all.

### ❌ Workaround #4: Disable branch protections
**Result:** No effect. Ghost workflow still blocks at `startup_failure`.

### ❌ Workaround #5: Purge Actions cache via UI
**Result:** No API endpoint available to clear workflow registry. Ghost workflow persists.

### ❌ Workaround #6: Create fork of repository
**Result:** Ghost workflow follows fork. Problem inherits to `Sovereignty-One/Sovereignty-AI-Studio_v1.0.1`.

---

## Expected vs. Actual Behavior

### Expected Behavior
When a workflow file is deleted from `.github/workflows/`:
1. Workflow is removed from Actions registry **immediately**
2. Subsequent events trigger **only registered workflows** in the codebase
3. No reference to deleted workflow exists in run history

### Actual Behavior
When a workflow file is deleted from `.github/workflows/`:
1. Ghost reference **persists indefinitely** in Actions registry
2. **Every event is intercepted** by deleted workflow first
3. Ghost workflow runs with **0 jobs** and **fails at startup**
4. All legitimate workflows are **blocked from execution**
5. Problem **propagates to forked repositories**

---

## API Evidence

### REST API Call: List Workflow Runs

```bash
curl -H "Authorization: token YOUR_TOKEN" \
  "https://api.github.com/repos/Appel420/Sovereignty-AI-Studio/actions/runs?per_page=30"
```

**Response (excerpt):**
```json
{
  "total_count": 323,
  "workflow_runs": [
    {
      "id": 35037313500,
      "name": "Quart App CI",
      "status": "completed",
      "conclusion": "startup_failure",
      "workflow_id": 352495736,  // <-- GHOST WORKFLOW ID
      "created_at": "2026-09-15T23:53:20Z"
    },
    {
      "id": 35037312716,
      "name": "CI",
      "status": "completed",
      "conclusion": "startup_failure",
      "workflow_id": 352495736,  // <-- SAME GHOST ID
      "created_at": "2026-09-15T23:53:13Z"
    }
    // ... all subsequent runs show conclusion: "startup_failure"
  ]
}
```

### Ghost Workflow Definition Request

```bash
curl -H "Authorization: token YOUR_TOKEN" \
  "https://api.github.com/repos/Appel420/Sovereignty-AI-Studio/actions/workflows/352495736"
```

**Response:**
```
404 Not Found
{
  "message": "Not Found",
  "documentation_url": "https://docs.github.com/rest/actions/workflows?apiVersion=2022-11-28"
}
```

**Contradiction:** Workflow ID `352495736` is referenced in active run records, but the workflow itself returns 404 when queried directly.

---

## Root Cause Analysis

This appears to be a **GitHub Actions registry cache invalidation bug**:

1. **Primary Issue:** When workflows are deleted, GitHub's cache layer doesn't invalidate
2. **Secondary Issue:** The Actions event dispatcher references cached workflow IDs instead of querying current `.github/workflows/` state
3. **Tertiary Issue:** Fork operation copies cached registry state, not just repository files

---

## Solution Requirements

GitHub must:

1. **Implement registry invalidation** when workflow files are deleted
2. **Add manual cache-clear endpoint** (e.g., `DELETE /repos/{owner}/{repo}/actions/cache`)
3. **Fix fork inheritance** to start with clean Actions registry
4. **Add orphaned workflow detection** to prevent ghost references in new runs
5. **Provide emergency recovery** for affected repositories (bulk delete of orphaned workflow runs)

---

## References

- **GitHub Issue #1062:** https://github.com/Appel420/Sovereignty-AI-Studio/issues/1062
- **Original Repository:** https://github.com/Appel420/Sovereignty-AI-Studio
- **Forked Repository:** https://github.com/Sovereignty-One/Sovereignty-AI-Studio_v1.0.1
- **Actions Run List:** https://github.com/Appel420/Sovereignty-AI-Studio/actions
- **Affected Branch:** `Collaboration` (and all other protected branches)

---

## Contact & Escalation

**Reporter:** @Appel420  
**GitHub Support Case:** [To be assigned]  
**Severity:** P0 / Critical  
**Timeline:** Issue first appeared ~2026-09-12, escalating through 2026-09-15

---

## Appendix: Workaround Attempt Log

See GitHub PR history for detailed attempts:
- PR #1055: "Kill ghost CI triggers"
- PR #1056: "fix(ci): quarantine ghost workflow on Collaboration"
- PR #1059: "fix(ci): constrain watchdog to Collaboration"
- PR #1065: "CI hardening: repair workflows, runner labels, and ghost residue"

All attempted fixes failed due to fundamental registry persistence issue.

---

**Status:** Awaiting GitHub Support Response  
**Last Updated:** 2026-09-15T23:55:00Z
