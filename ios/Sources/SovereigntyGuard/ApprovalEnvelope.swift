import CryptoKit
import Foundation

public enum ApprovalOperation: String, Codable, Sendable {
    case process = "PROCESS"
    case deployment = "DEPLOYMENT"
    case commit = "COMMIT"
}

public enum ApprovalDecision: String, Codable, Sendable {
    case approved = "APPROVED"
    case denied = "DENIED"
}

public struct ApprovalEnvelope: Codable, Sendable, Equatable {
    public let protocolVersion: String
    public let approvalID: String
    public let operation: ApprovalOperation
    public let subject: String
    public let payloadDigest: String
    public let decision: ApprovalDecision
    public let ownerKeyID: String
    public let createdAt: Date
    public let expiresAt: Date?
    public let classicalAlgorithm: String
    public let postQuantumAlgorithm: String?
    public let classicalSignature: Data
    public let postQuantumSignature: Data?

    public init(
        approvalID: String,
        operation: ApprovalOperation,
        subject: String,
        payloadDigest: String,
        decision: ApprovalDecision,
        ownerKeyID: String,
        createdAt: Date = Date(),
        expiresAt: Date? = nil,
        classicalSignature: Data,
        postQuantumSignature: Data? = nil,
        postQuantumAlgorithm: String? = nil
    ) {
        self.protocolVersion = "SG-HYBRID-APPROVAL-1"
        self.approvalID = approvalID
        self.operation = operation
        self.subject = subject
        self.payloadDigest = payloadDigest
        self.decision = decision
        self.ownerKeyID = ownerKeyID
        self.createdAt = createdAt
        self.expiresAt = expiresAt
        self.classicalAlgorithm = "P256.Signing"
        self.postQuantumAlgorithm = postQuantumAlgorithm
        self.classicalSignature = classicalSignature
        self.postQuantumSignature = postQuantumSignature
    }

    public func signingPayload() throws -> Data {
        let payload: [String: String] = [
            "protocolVersion": protocolVersion,
            "approvalID": approvalID,
            "operation": operation.rawValue,
            "subject": subject,
            "payloadDigest": payloadDigest,
            "decision": decision.rawValue,
            "ownerKeyID": ownerKeyID,
            "createdAt": ISO8601DateFormatter().string(from: createdAt),
            "expiresAt": expiresAt.map { ISO8601DateFormatter().string(from: $0) } ?? "",
            "classicalAlgorithm": classicalAlgorithm,
            "postQuantumAlgorithm": postQuantumAlgorithm ?? ""
        ]
        return try JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
    }
}

public enum ApprovalEnvelopeVerifier {
    public static func verifyClassical(
        envelope: ApprovalEnvelope,
        publicKey: P256.Signing.PublicKey,
        now: Date = Date()
    ) -> Bool {
        guard envelope.decision == .approved else { return false }
        if let expiresAt = envelope.expiresAt, expiresAt <= now { return false }
        guard let payload = try? envelope.signingPayload(),
              let signature = try? P256.Signing.ECDSASignature(rawRepresentation: envelope.classicalSignature)
        else { return false }
        return publicKey.isValidSignature(signature, for: payload)
    }
}
