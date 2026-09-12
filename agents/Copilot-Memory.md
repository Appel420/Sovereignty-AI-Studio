# Copilot branch implementation note

Branch: `copilot/main`

Added the first focused dashboard integration boundary:

- `frontend/runtime/dashboard-runtime-controller.js`
  - one shared owner for local/offline, hybrid, and online mode selection;
  - synchronizes any top/bottom controls supplied with `data-sg-mode`;
  - persists only the selected mode locally;
  - keeps transport connectivity and authorization separate from mode selection;
  - reports device-local state and external-memory status explicitly.
- `frontend/scripts/test-dashboard-runtime-controller.js`
  - verifies shared control synchronization;
  - verifies local mode state semantics;
  - verifies invalid-mode fallback.

Not yet changed: the monolithic `SGHv119.html` wiring. Its complete mode-control and inline bridge regions must be read before removing duplicate owners. The next patch should load this controller once from the canonical dashboard and bind the existing controls without deleting the alternate dashboard.

Verification status: files added; tests not executed by the GitHub file API.
