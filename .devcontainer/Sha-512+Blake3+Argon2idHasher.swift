import Foundation
import Crypto

/// Computes integrity hashes over arbitrary data using a Blake3-shaped API.
///
/// **Current algorithm: SHA-512** (from `swift-crypto`).
/// The struct exposes the same interface that a native Blake3 implementation
/// would use, so callers need no changes when a dedicated Blake3 Swift package
/// is wired in. CryptoSwift (>= 1.8.3, the version range used here) does not
/// ship a Blake3 implementation.
public struct Blake3Hasher: Sendable {

    // MARK: - Hash

    /// Returns the hex-encoded SHA-512 digest of `data`.
    public static func hash(_ data: Data) -> String {
        let digest = SHA512.hash(data: data)
        return digest.compactMap { String(format: "%02x", $0) }.joined()
    }

    /// Returns the hex-encoded SHA-512 digest of a UTF-8 encoded string.
    public static func hash(_ string: String) -> String {
        hash(Data(string.utf8))
    }

    // MARK: - Verification

    /// Returns `true` when `data` hashes to `expectedHex`.
    public static func verify(data: Data, expectedHex: String) -> Bool {
        hash(data) == expectedHex.lowercased()
    }
}
