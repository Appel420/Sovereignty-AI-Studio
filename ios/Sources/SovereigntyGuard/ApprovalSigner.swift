import CryptoKit
import Foundation
import Security

public enum ApprovalKeyStorage: String, Codable, Sendable {
    case secureEnclave
    case keychainSoftwareFallback
}

public enum ApprovalKeyError: Error {
    case secureEnclaveUnavailable
    case invalidStoredKey
}

public final class ApprovalSigner: @unchecked Sendable {
    public let keyID: String
    public let storage: ApprovalKeyStorage

    private let softwareKey: P256.Signing.PrivateKey?
    #if canImport(UIKit) || canImport(Darwin)
    private let secureEnclaveKey: SecureEnclave.P256.Signing.PrivateKey?
    #endif

    public init(keyID: String = "owner-approval-key") throws {
        self.keyID = keyID

        #if canImport(UIKit) || canImport(Darwin)
        if SecureEnclave.isAvailable {
            do {
                self.secureEnclaveKey = try SecureEnclave.P256.Signing.PrivateKey()
                self.softwareKey = nil
                self.storage = .secureEnclave
                return
            } catch {
                // Fall through to the documented software-key fallback.
            }
        }
        self.secureEnclaveKey = nil
        #endif

        self.softwareKey = P256.Signing.PrivateKey()
        self.storage = .keychainSoftwareFallback
    }

    public var publicKeyData: Data {
        #if canImport(UIKit) || canImport(Darwin)
        if let key = secureEnclaveKey { return key.publicKey.rawRepresentation }
        #endif
        return softwareKey!.publicKey.rawRepresentation
    }

    public func sign(_ payload: Data) throws -> Data {
        #if canImport(UIKit) || canImport(Darwin)
        if let key = secureEnclaveKey {
            return try key.signature(for: payload).rawRepresentation
        }
        #endif
        return try softwareKey!.signature(for: payload).rawRepresentation
    }

    public func makeEnvelope(
        operation: ApprovalOperation,
        subject: String,
        payload: Data,
        decision: ApprovalDecision = .approved,
        expiresAt: Date? = nil
    ) throws -> ApprovalEnvelope {
        let digest = SHA256.hash(data: payload).map { String(format: "%02x", $0) }.joined()
        let unsigned = ApprovalEnvelope(
            approvalID: UUID().uuidString,
            operation: operation,
            subject: subject,
            payloadDigest: "sha256:\(digest)",
            decision: decision,
            ownerKeyID: keyID,
            expiresAt: expiresAt,
            classicalSignature: Data()
        )
        let signature = try sign(unsigned.signingPayload())
        return ApprovalEnvelope(
            approvalID: unsigned.approvalID,
            operation: operation,
            subject: subject,
            payloadDigest: unsigned.payloadDigest,
            decision: decision,
            ownerKeyID: keyID,
            createdAt: unsigned.createdAt,
            expiresAt: expiresAt,
            classicalSignature: signature
        )
    }

    public func verify(_ envelope: ApprovalEnvelope, payload: Data, now: Date = Date()) -> Bool {
        let digest = SHA256.hash(data: payload).map { String(format: "%02x", $0) }.joined()
        guard envelope.payloadDigest == "sha256:\(digest)" else { return false }
        guard envelope.ownerKeyID == keyID else { return false }
        #if canImport(UIKit) || canImport(Darwin)
        if let key = secureEnclaveKey {
            return ApprovalEnvelopeVerifier.verifyClassical(envelope: envelope, publicKey: key.publicKey, now: now)
        }
        #endif
        return ApprovalEnvelopeVerifier.verifyClassical(envelope: envelope, publicKey: softwareKey!.publicKey, now: now)
    }
}
