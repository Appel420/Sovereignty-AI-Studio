import Foundation

/// Capability-gated ANE integration boundary. The core contract deliberately
/// does not depend on Apple's Neural Engine APIs; platform-specific inference
/// remains behind this adapter.
public protocol DiamondInferenceBackend: Sendable {
    func execute(input: Data, objectID: Data) async throws -> Data
}

public struct DiamondANEBridge: DiamondInferenceBackend, Sendable {
    public init() {}

    public func execute(input: Data, objectID: Data) async throws -> Data {
        guard objectID.count == 32 else { throw DiamondANEError.invalidObjectID }
        guard !input.isEmpty else { throw DiamondANEError.emptyInput }
        // No ANE call is made here. This is the fail-closed contract boundary;
        // a concrete Core ML/ANE backend can be attached without becoming an
        // authority path or bypassing Diamond Core authorization.
        throw DiamondANEError.backendNotInstalled
    }
}

public enum DiamondANEError: Error, Equatable, Sendable {
    case invalidObjectID
    case emptyInput
    case backendNotInstalled
}
