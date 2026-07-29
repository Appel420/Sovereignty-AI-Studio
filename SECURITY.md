# Security Policy

## Supported versions

This project is developed and operated as a local/self-hosted application. Security fixes are applied to the current default branch and released versions that are still in active use. Older snapshots are not guaranteed to receive updates.

| Version | Support |
| --- | --- |
| Current default branch | :white_check_mark: |
| Older snapshots | :warning: Best effort only |

## Dependency and runtime policy

- Runtime dependencies must be available from the repository, an approved local package cache, or an administrator-controlled internal mirror.
- Builds, tests, vulnerability checks, SBOM generation, signing, and deployment must run with local or self-hosted tools.
- Do not add required calls to hosted CI services, cloud registries, SaaS scanners, telemetry providers, or remote AI APIs.
- Network access is disabled by default for local and air-gapped operation. If a dependency must be downloaded during setup, fetch and review it before entering the isolated environment, then use the local cache or mirror.
- Keep credentials, private keys, model files, audit logs, and generated reports on systems controlled by the operator. Never commit secrets.

The repository's local validation entry point is:

```bash
./scripts/local-ci.sh
```

Run it on the host that owns the checkout. Optional tools such as `syft` must already be installed locally; the script must not install them or upload results. Missing local tools are reported as skipped or failed according to the script's documented behavior.

## Reporting a vulnerability

Please do not disclose exploitable details in a public issue. Use the repository's private security-reporting channel when it is enabled. If private reporting is unavailable, contact the project maintainer through an existing trusted repository-maintainer channel and include:

- the affected commit, file, or version;
- reproduction steps or a minimal proof of concept;
- impact and required privileges;
- any suggested mitigation; and
- whether the report may be shared with other maintainers.

Reports are triaged locally. The maintainer will acknowledge receipt when practical, work with the reporter to reproduce and assess the issue, and coordinate a fix or mitigation before public disclosure. Do not include secrets or personal/regulated data in a report.

## Compliance and regulated-use notice

Local or self-hosted CI/CD guardrails—testing, dependency review, vulnerability scanning, SBOM generation, provenance, and signing—do **not** by themselves certify HIPAA, GDPR, or any other regulatory compliance.

For medical or regulated deployments, operators must also implement appropriate organizational and operational controls, including access governance, retention and deletion procedures, incident response, backup and recovery, audit review, BAAs/DPAs where applicable, and legal/compliance review. Where encryption master keys are used, apply Shamir secret-sharing and keep key reconstruction outside automated build and deployment jobs.
