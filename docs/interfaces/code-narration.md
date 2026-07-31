# Code Narration Contract

## Layer

Code Narration belongs to the Experience Layer, alongside the Dashboard, Terminal, and Mobile UI. It is not part of core governance or the authority plane.

## Purpose

Provide human-readable, speech-friendly explanations for source-heavy assistant responses and architecture review. It is an accessibility and comprehension feature, not a code execution feature.

## Input

- source code or source-heavy assistant response
- repository context
- architecture and interface metadata

## Output

A plain-language explanation of purpose, inputs, outputs, security boundary, policy role, and architecture relationship.

## Rules

- Never execute, import, evaluate, or modify code.
- Never bypass permissions or policy.
- Never upload source or private repository context.
- Keep the original source visible separately from generated narration.
- Use repository contracts to explain behavior, not only syntax.

## Example

Instead of:

> Class PolicyEngine has method evaluate with parameters.

Prefer:

> PolicyEngine is the authorization boundary. It evaluates requested capabilities against active policy and records decisions in SCARLedger.

## Local TTS

Narration is sent only to the existing local TTS path. TTS failure must not execute code, modify source, or block governance validation.

## Test contract

Tests cover fenced Python, JavaScript, and TypeScript, indented code, mixed prose/code, architecture-aware terminology, and the absence of execution or remote dependencies.
