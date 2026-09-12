import XCTest
@testable import SovereigntyGuard

final class DiamondAccelerationTests: XCTestCase {
    func testMemoryHandleRejectsNonObjectID() {
        XCTAssertTrue((try? makeHandle(Data(repeating: 0, count: 31))) == nil)
    }

    func testFoldTraversalStopsAfterAuthorityDenial() async {
        let authority = TestAuthority(shouldAllow: false)
        let traversal = DiamondFoldTraversal(authority: authority)
        let step = DiamondFoldStep(sequence: 0, objectID: Data(repeating: 1, count: 32), orientation: .inward, presentedEpoch: 17)
        let first = await traversal.step(step)
        if case .success = first { XCTFail("denied authority unexpectedly succeeded") }
        let state = await traversal.state
        XCTAssertEqual(state, .interrupted)
        let second = await traversal.step(step)
        if case .success = second { XCTFail("interrupted traversal executed another step") }
        XCTAssertEqual(await authority.calls, 1)
    }

    func testANEWithoutBackendFailsClosed() async {
        let backend = DiamondANEBridge()
        do {
            _ = try await backend.execute(input: Data([1]), objectID: Data(repeating: 1, count: 32))
            XCTFail("missing ANE backend must fail closed")
        } catch let error as DiamondANEError {
            XCTAssertEqual(error, .backendNotInstalled)
        } catch {
            XCTFail("unexpected error: \(error)")
        }
    }

    private func makeHandle(_ objectID: Data) throws -> DiamondMemoryHandle {
        guard objectID.count == 32 else { throw TestError.invalid }
        return DiamondMemoryHandle(objectID: objectID, byteCount: 1, tier: .shared)
    }

    private enum TestError: Error, Sendable { case invalid }

    private actor TestAuthority: DiamondFoldAuthority {
        let shouldAllow: Bool
        private(set) var calls = 0
        init(shouldAllow: Bool) { self.shouldAllow = shouldAllow }
        func authorizeAndCommitStep(_ step: DiamondFoldStep) async throws {
            calls += 1
            if !shouldAllow { throw TestError.invalid }
        }
    }
}
