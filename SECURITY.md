# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are
currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 5.1.x   | :white_check_mark: |
| 5.0.x   | :x:                |
| 4.0.x   | :white_check_mark: |
| < 4.0   | :x:                |

## Reporting a Vulnerability

Use this section to tell people how to report a vulnerability.

Tell them where to go, how often they can expect to get an update on a
reported vulnerability, what to expect if the vulnerability is accepted or
declined, etc.

## Compliance and regulated-use notice

The CI/CD workflows add technical guardrails (testing, dependency review,
vulnerability scanning, SBOM/provenance, and signing), but they do **not**
alone certify HIPAA/GDPR compliance.

For medical/regulated deployments, you must also implement operational and
organizational controls (access governance, retention/deletion procedures,
incident response, BAAs/DPAs, and legal/compliance review). Where encryption
master keys are used, apply SHAMIR secret-sharing and keep reconstruction
outside CI/CD.
