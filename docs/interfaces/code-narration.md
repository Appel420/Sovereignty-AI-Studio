# Code Narration Contract

## Purpose

Code Narration provides speech-friendly explanations for source-heavy assistant responses. It is an accessibility and comprehension feature; it is not a code execution feature.

## Modes

- **Read message:** sends the original response to the existing local TTS path.
- **Explain code:** extracts fenced or code-like sections and narrates purpose, structure, checks, security, and architecture role.
- **Summarize implementation:** narrates a short implementation summary without reading raw syntax.

## Safety boundary

The parser treats code as untrusted text. It never executes, imports, evaluates, or uploads source code. The raw response remains visible in the interface, while only generated narration text is sent to `VoiceAPI.speak`.

## Parser behavior

The shared parser recognizes fenced code blocks for Python, JavaScript, TypeScript, JSON, YAML, and shell syntax. It also detects common indented or code-like content. Unknown languages are preserved as source code.

## Source-file narration headers

New core source files should begin with a concise header:

```text
Purpose: why this file exists.
Depends on: direct local interfaces or modules.
Used by: known consumers.
Security: authority, privacy, and execution boundary.
```

The header is documentation for humans and future narration tooling; it is not runtime metadata.

## TTS integration

The frontend calls `VoiceAPI.speak` using narration text. The existing Piper-backed voice service remains responsible for audio generation. If an audio URL is returned, the frontend attempts local playback; TTS failures do not execute or modify the source response.

## Test contract

Tests cover fenced Python, JavaScript, and TypeScript, indented Python, and mixed prose/code. They also verify that narration does not include Markdown fence delimiters.
