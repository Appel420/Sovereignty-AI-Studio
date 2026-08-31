from __future__ import annotations

from pathlib import Path

WORKFLOW_DIR = Path('.github/workflows')
FORBIDDEN_REDIRECT = '2>/dev/null'
FORBIDDEN_SHELL_GATE = 'ALLOW_SHELL'


def main() -> int:
    violations: list[str] = []
    workflow_files = sorted(WORKFLOW_DIR.glob('*.yml')) + sorted(WORKFLOW_DIR.glob('*.yaml'))
    if not workflow_files:
        raise SystemExit('No GitHub Actions workflow files found')

    for path in workflow_files:
        text = path.read_text(encoding='utf-8', errors='strict')
        if FORBIDDEN_REDIRECT in text:
            violations.append(f'{path}: contains silent stderr suppression: {FORBIDDEN_REDIRECT}')
        if FORBIDDEN_SHELL_GATE in text:
            violations.append(f'{path}: references forbidden shell authorization gate: {FORBIDDEN_SHELL_GATE}')

    if violations:
        print('VISIBILITY_CONTRACT=FAIL')
        for violation in violations:
            print(violation)
        return 1

    print(f'VISIBILITY_CONTRACT=PASS workflow_files={len(workflow_files)}')
    for path in workflow_files:
        print(f'VISIBLE_WORKFLOW={path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
