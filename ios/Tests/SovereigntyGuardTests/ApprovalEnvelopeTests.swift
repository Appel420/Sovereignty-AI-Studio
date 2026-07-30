import XCTest
@testable import SovereigntyGuard

final class ApprovalEnvelopeTests: XCTestCase {
    func testCommitEnvelopeVerifiesExactPayload() throws {
        let signer = try ApprovalSigner(keyID: "test-owner")
        let payload = Data("commit abc123".utf8)
        let envelope = try signer.makeEnvelope(
            operation: .commit,
            subject: "abc123",
            payload: payload
        )

        XCTAssertTrue(signer.verify(envelope, payload: payload))
        XCTAssertFalse(signer.verify(envelope, payload: Data("different commit".utf8)))
    }

    func testDeniedEnvelopeDoesNotVerify() throws {
        let signer = try ApprovalSigner(keyID: "test-owner")
        let envelope = try signer.makeEnvelope(
            operation: .deployment,
            subject: "build-1",
            payload: Data("artifact".utf8),
            decision: .denied
        )

        XCTAssertFalse(signer.verify(envelope, payload: Data("artifact".utf8)))
    }
}
