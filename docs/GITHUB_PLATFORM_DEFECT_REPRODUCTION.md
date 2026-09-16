# GitHub Platform Defect: Ghost Workflow Registry Poison

**Issue Reference:** #1062  
**Severity:** P0 / Critical  
**Status:** Active / Unresolved  
**Date Reported:** 2026-09-15

---

## Executive Summary

GitHub's Actions registry maintains cached references to deleted workflows. When a workflow file is deleted from `.github/workflows/`, the registry entry is NOT invalidated, causing subsequent push/PR events to be intercepted by orphaned workflow definitions that fail at `startup_failure` with 0 jobs. This completely blocks all CI/CD pipelines and persists across forked repositories.

**Impact:** 100% CI/CD pipeline failure across multiple repositories.

---

## Affected Repositories

- `Appel420/Sovereignty-AI-Studio` (323+ failed workflow runs)
- `Sovereignty-One/Sovereignty-AI-Studio_v1.0.1` (fork - inherits same poison)

---

## Steps to Reproduce

### Prerequisites
- GitHub repository with multiple GitHub Actions workflows
- Ability to push commits and create pull requests
- Access to Actions run history via UI or API

### Step 1: Verify Initial Workflow State
```bash
# List current workflows
ls -la .github/workflows/

# Verify workflows are registered and running
# Check GitHub Actions tab: repository should show successful workflow runs
```

### Step 2: Delete a Workflow File
```bash
# Delete any workflow file from .github/workflows/
git rm .github/workflows/BuildFailed.yml

# Commit and push
git commit -m "Remove BuildFailed workflow"
git push origin main
```

### Step 3: Trigger New Events
```bash
# Make a small commit to trigger new workflow runs
echo "# test" >> README.md
git add README.md
git commit -m "test: trigger workflows"
git push origin main
```

### Step 4: Observe the Ghost Workflow Intercept
**Expected Behavior:**
- New push event triggers registered workflows (ci.yml, lint.yml, etc.)
- Workflows run and complete successfully or fail based on code quality

**Actual Behavior (Bug):**
```
GitHub Actions UI shows:
- Workflow run with conclusion: "startup_failure"
- Jobs: 0
- Duration: < 1 second
- Workflow ID: [ID of deleted BuildFailed.yml]
```

### Step 5: Verify API Contradiction
```bash
# Query active runs via REST API
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/[owner]/[repo]/actions/runs"

# Response will include:
# {
#   "workflow_id": [deleted_workflow_id],
#   "conclusion": "startup_failure",
#   "jobs": 0
# }
```

### Step 6: Query the Deleted Workflow Directly
```bash
# Try to fetch the workflow definition
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/[owner]/[repo]/actions/workflows/[deleted_workflow_id]"

# Response: 404 Not Found
# This proves the workflow exists in run records but not in repository
```

### Step 7: Verify Git History
```bash
# Confirm workflow file is completely deleted
git log --all --name-status -- "BuildFailed.yml"
# (no matching commits - workflow is gone from history)

# Verify file doesn't exist in HEAD
git show HEAD:.github/workflows/BuildFailed.yml
# fatal: path '.github/workflows/BuildFailed.yml' does not exist
```

### Step 8: Fork the Repository
```bash
# Create a fork via GitHub UI
# https://github.com/[owner]/[repo]/fork
```

### Step 9: Verify Ghost Workflow Inherits to Fork
```bash
# In the forked repository, check Actions run history
# Observable: Same ghost workflow ID intercepts events
# Same startup_failure pattern
# Proves issue is in GitHub's registry, not local configuration
```

---

## Expected vs. Actual Behavior

| Phase | Expected | Actual (Bug) |
|-------|----------|--------------|
| **Workflow Deletion** | Workflow removed from registry immediately | Workflow persists in registry indefinitely |
| **Next Push Event** | Registered workflows execute normally | Ghost workflow intercepts, fails with startup_failure |
| **Job Execution** | New workflows run with actual jobs | Ghost workflow has 0 jobs, fails in < 1 second |
| **Fork Creation** | Fork has clean Actions registry | Fork inherits ghost workflow from source |
| **API Query (active runs)** | Returns currently registered workflows | Returns deleted workflow with ID |
| **API Query (workflow details)** | Workflow definition available | 404 Not Found |

---

## Root Cause Analysis

### The Contradiction
```
A workflow_id referenced in active run records,
but returns 404 when queried for its definition.

This is impossible unless GitHub maintains two separate data stores:
1. Run history (includes deleted workflow references)
2. Workflow registry (doesn't include deleted workflows)

And the event dispatcher queries (#1) instead of (#2).
```

### Hypothesis: Cache Invalidation Bug

GitHub likely:
1. **Stores workflows** in a fast, indexed registry (cached layer)
2. **Stores run history** in a separate data store (append-only)
3. **Deletes workflows** from registry but NOT from run history
4. **Event dispatcher** reads from cached registry without invalidation
5. **Fails** when trying to load deleted workflow definition
6. **Returns startup_failure** because definition is missing
7. **Fork operation** copies cached registry state, inheriting the poison

---

## Current Workarounds (All Failed)

| Workaround | Attempt | Result |
|-----------|---------|--------|
| Delete/recreate `.github/workflows/` | ✅ | ❌ Ghost workflow still intercepts |
| Force-push clean state | ✅ | ❌ Ghost workflow returns on next push |
| Rename all workflow files | ✅ | ❌ Ghost workflow blocks everything |
| Disable branch protections | ✅ | ❌ No effect on ghost workflow |
| Purge Actions cache via UI | ✅ | ❌ No API endpoint exists; cache persists |
| Create fork with clean state | ✅ | ❌ Ghost workflow inherits to fork |
| Change default branch | ✅ | ❌ Ghost workflow still intercepts |
| Delete and recreate repository | Not tested | (Would lose all history) |

**Conclusion:** No client-side workaround exists. This requires GitHub server-side intervention.

---

## Proposed Solution

GitHub must implement the following:

### 1. Cache Invalidation on Workflow Deletion
```
When: Workflow file deleted from .github/workflows/
Action: Remove all references from Actions registry cache
Effect: Subsequent events no longer reference deleted workflows
```

### 2. Registry Cleanup API Endpoint
```
API: DELETE /repos/{owner}/{repo}/actions/registry-cache
Purpose: Force-clear orphaned workflow references
Response: 204 No Content (on success)
```

### 3. Fix Fork Inheritance
```
When: Repository is forked
Action: Initialize Actions registry from current .github/workflows/
        Do NOT copy cached registry from source repo
Effect: Fork has clean Actions registry
```

### 4. Orphaned Workflow Detection
```
When: Workflow run triggered
Action: Verify workflow_id exists in current .github/workflows/
        before attempting execution
If: Workflow definition missing
  Action: Skip run, log error, alert user
  Effect: Prevents startup_failure from ghost workflows
```

### 5. Emergency Recovery Tool
```
For affected repositories:
- Purge all orphaned workflow references
- Clear run history for startup_failure runs
- Rebuild Actions registry from current .github/workflows/
- Notify user when recovery is complete
```

---

## Technical Evidence

### API Response Contradiction
```bash
# Query #1: List active workflow runs
GET /repos/Appel420/Sovereignty-AI-Studio/actions/runs
HTTP 200 OK
{
  "total_count": 323,
  "workflow_runs": [
    {
      "id": 35037313500,
      "workflow_id": 352495736,
      "name": "Quart App CI",
      "conclusion": "startup_failure",
      "status": "completed"
    }
    # ... 322 more with same workflow_id
  ]
}

# Query #2: Fetch workflow definition
GET /repos/Appel420/Sovereignty-AI-Studio/actions/workflows/352495736
HTTP 404 Not Found
{
  "message": "Not Found"
}
```

**This contradiction is the core evidence of the platform defect.**

### Git History Verification
```bash
# Workflow completely absent from codebase
$ git log --all -- .github/workflows/BuildFailed.yml
# (no output)

$ git show HEAD:.github/workflows/BuildFailed.yml
# fatal: path '.github/workflows/BuildFailed.yml' does not exist in 'HEAD'
```

---

## Business Impact

| Area | Status | Impact |
|------|--------|--------|
| **CI/CD Pipeline** | Blocked | 100% failure rate |
| **Code Quality Checks** | Offline | Cannot run Flake8, Pylint, CodeQL |
| **Security Scanning** | Offline | No vulnerability detection |
| **Dependency Monitoring** | Offline | Cannot audit requirements |
| **Development Velocity** | Halted | Cannot verify code before merge |
| **Deployments** | Blocked | Cannot release to production |

---

## Timeline

| Date | Event |
|------|-------|
| 2026-09-12 | BuildFailed workflow deleted from repository |
| 2026-09-12 — 2026-09-15 | All workflow runs fail with startup_failure |
| 2026-09-14 | Fork created (inherits ghost workflow) |
| 2026-09-15 | Issue #1062 filed; escalation initiated |
| 2026-09-15 | Multiple workaround attempts all failed |

---

## Files for Reference

- **GitHub Issue:** https://github.com/Appel420/Sovereignty-AI-Studio/issues/1062
- **Technical Report:** `docs/GITHUB_BUG_REPORT_1062.md`
- **Fork (Cross-Repo Evidence):** https://github.com/Sovereignty-One/Sovereignty-AI-Studio_v1.0.1

---

## Requested Action

### Immediate (24 hours)
1. Acknowledge receipt of this report
2. Assign to GitHub Actions platform team
3. Begin investigation into cache invalidation layer

### Short-term (48-72 hours)
1. Implement orphaned workflow detection
2. Create emergency registry cleanup for affected repos
3. Test solution on staging environment

### Resolution (1 week)
1. Deploy cache invalidation fix
2. Clear all orphaned workflows from affected repositories
3. Fix fork inheritance issue
4. Implement permanent preventive measures

---

## Contact & Escalation

**Reporter:** @Appel420  
**GitHub Username:** Appel420  
**Account Email:** 201665841+Appel420@users.noreply.github.com  
**Affected Repositories:**
- Appel420/Sovereignty-AI-Studio
- Sovereignty-One/Sovereignty-AI-Studio_v1.0.1

**Escalation Path:**
1. GitHub Support (https://support.github.com)
2. GitHub Actions Platform Team
3. GitHub Engineering (if platform-wide issue)

---

## Acknowledgments

This report includes:
- ✅ Detailed reproduction steps
- ✅ Expected vs. actual behavior comparison
- ✅ Root cause analysis
- ✅ API evidence showing contradiction
- ✅ Failed workarounds (6 attempts)
- ✅ Proposed solutions
- ✅ Business impact assessment
- ✅ Cross-repository proof (fork evidence)

---

**Report Status:** Awaiting GitHub Response  
**Severity Level:** P0 - Production Blocking  
**Last Updated:** 2026-09-15T23:57:00Z

