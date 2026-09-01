import Foundation
#if canImport(Metal)
import Metal
#endif

/// Physical placement is an implementation detail. Consumers receive a
/// bounded handle, never a physical address or unrestricted memory authority.
public enum DiamondMemoryTier: Sendable, Equatable {
    case shared
    case privateGPU
}

public struct DiamondMemoryHandle: Sendable, Equatable {
    public let objectID: Data
    public let byteCount: Int
    public let tier: DiamondMemoryTier

    public init(objectID: Data, byteCount: Int, tier: DiamondMemoryTier) {
        precondition(objectID.count == 32, "ObjectID must be 32 bytes")
        precondition(byteCount >= 0, "byteCount must be non-negative")
        self.objectID = objectID
        self.byteCount = byteCount
        self.tier = tier
    }
}

#if canImport(Metal)
@available(iOS 16.0, *)
public final class DiamondMetalMemory: @unchecked Sendable {
    public let device: MTLDevice
    private let queue: MTLCommandQueue

    public init?(device: MTLDevice? = MTLCreateSystemDefaultDevice()) {
        guard let device, let queue = device.makeCommandQueue() else { return nil }
        self.device = device
        self.queue = queue
    }

    /// Apple Silicon shared storage is the unified-memory path. The ObjectID
    /// remains the authority boundary; MTLBuffer is never authority.
    public func makeSharedBuffer(handle: DiamondMemoryHandle, contents: Data) -> MTLBuffer? {
        guard handle.tier == .shared, contents.count <= handle.byteCount else { return nil }
        return contents.withUnsafeBytes { raw in
            guard let base = raw.baseAddress else { return nil }
            return device.makeBuffer(bytes: base, length: contents.count, options: .storageModeShared)
        }
    }

    public func synchronize() {
        // Reserved synchronization boundary for future non-shared tiers.
    }

    public func commitEmptyWork() -> Bool {
        guard let commandBuffer = queue.makeCommandBuffer() else { return false }
        commandBuffer.commit()
        commandBuffer.waitUntilCompleted()
        return commandBuffer.status == .completed
    }
}
#endif
