# SCAR Scope Addendum — Mail-Transport Layer Exclusion

**Effective:** Logged alongside the AUDIT/external-mail-dependency finding.

## Clarification

SCAR zero-tolerance policy governs artifacts, infrastructure, and services
deployed or controlled by the device owner. It applies to embedded Google
Fonts/APIs/CDNs, Firebase, Vertex AI, Meta services, third-party cloud
services, runtime dependencies pulled into the local stack, and selected
model/inference integrations.

It does **not** extend to third-party organizations' internal mail-transport
infrastructure—such as MX records or SMTP relays—for domains not owned or
operated by the device owner.

## Provider boundary

Sanctioned AI providers may be approved at the app, model, or inference layer
within Sovereignty-AI-Gate and related projects. A provider's corporate email
infrastructure is outside the device owner's authority and is not itself a
runtime dependency of this repository.

A domain routing its own mail through Google, Microsoft, or another provider
does not by itself create a SCAR violation or disqualify that provider from
sanctioned status.

## SCAR applies to

- Fonts, APIs, CDNs, and cloud services embedded in deliverables.
- Runtime dependencies pulled into the local stack.
- Model and inference providers selected for the sanctioned list.
- Infrastructure deployed or controlled by the device owner.

## SCAR does not apply to

- Third-party organizations' internal corporate infrastructure.
- Public DNS records outside the device owner's zone.
- MX records and mail transport for domains not owned or operated locally.

## Enforcement rule

The local audit remains read-only and offline. It must classify third-party
mail-transport references as **OUT_OF_SCAR_SCOPE** rather than as a local
runtime violation. This exclusion does not authorize cloud execution, external
provider calls, online fallback, or any network access by the local runtime.
