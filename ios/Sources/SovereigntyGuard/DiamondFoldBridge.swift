import Foundation

/// Fold remains a consumer of the Diamond authority contract. This bridge owns
/// traversal metadata only; it cannot grant authority and has no capability
/// cache. Every step must be authorized by the caller's authoritative store.
public enum DiamondFoldOrientation: Sendable {
    case inward
    case outward
}

public struct DiamondFoldStep: Sendable, Equatable {
    public let sequence: UInt64
    public let objectID: Data
    public let orientation: DiamondFoldOrientation
    public let presentedEpoch: UInt64

    public init(sequence: UInt64, objectID: Data, orientation: DiamondFoldOrientation, presentedEpoch: UInt64) {
        self.sequence = sequence
        self.objectID = objectID
        self.orientation = orientation
        self.presentedEpoch = presentedEpoch
    }
}

public protocol DiamondFoldAuthority: Sendable {
    func authorizeAndCommitStep(_ step: DiamondFoldStep) async throws
}

public actor DiamondFoldTraversal {
    public enum State: Sendable, Equatable {
        case active
        case interrupted
        case completed
    }

    private let authority: any DiamondFoldAuthority
    public private(set) var state: State = .active

    public init(authority: any DiamondFoldAuthority) {
        self.authority = authority
    }

    public func step(_ step: DiamondFoldStep) async -> Result<Void, Error> {
        guard state == .active else {
            return .failure(DiamondFoldError.notActive)
        }

        do {
            // Deliberately one authority call. No read/check API exists here.
            try await authority.authorizeAndCommitStep(step)
            return .success(())
        } catch {
            state = .interrupted
            return .failure(error)
        }
    }

    public func complete() {
        guard state == .active else { return }
        state = .completed
    }
}

public enum DiamondFoldError: Error, Equatable, Sendable {
    case notActive
}
