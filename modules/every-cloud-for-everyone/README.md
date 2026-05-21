# Every Cloud For Everyone — Integration Module

This directory is a git submodule referencing [appel420/every-cloud-for-everyone](https://github.com/appel420/every-cloud-for-everyone).

## Initialize

```bash
git submodule update --init modules/every-cloud-for-everyone
```

## What Every Cloud Provides

A Swift Package Manager library applying client-side encryption on top of 22 cloud providers:
- iCloud, Google Drive, OneDrive, Dropbox, AWS S3, Azure Blob, Nextcloud, and 15+ more
- Scrypt key derivation → AES-256-GCM encryption before any cloud upload
- BLAKE3 integrity digests stored locally
- `QResist` uplink kill-switch — kills connection on digest mismatch
- `LockdownMode` — blocks all non-essential network traffic

## Integration with Sovereignty AI Studio

This Swift package is not executed by the Node/Python server at runtime.

| Component | How to use |
|-----------|------------|
| Swift library | Build into iOS/macOS companion app via SPM |
| `Cloud_fortress` docs | Reference for equivalent browser-JS implementation |
| Encryption patterns | Port `UniversalCloudSealer` logic to TypeScript for web frontend |
| `infrastructure/` | Daemon and Google Citadel deployment configs |

## Platform Requirements

- Swift 5.9+, macOS 13+
- Dependencies: `swift-crypto`, `CryptoSwift`
- 49 tests across 7 suites
