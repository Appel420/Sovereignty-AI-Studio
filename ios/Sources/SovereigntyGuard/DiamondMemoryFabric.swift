import Foundation
#if canImport(Metal)
import Metal
#endif

/// Physical memory placement is an implementation detail. Consumers receive a
/// bounded handle rather than a raw physical address or unrestricted buffer.
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

    /// Shared storage is the Apple Silicon unified-memory path. The object ID
    /// remains the authority boundary; the MTLBuffer is never itself authority.
    public func makeSharedBuffer(handle: DiamondMemoryHandle, contents: Data) -> MTLBuffer? {
        guard handle.tier == .shared, contents.count <= handle.byteCount else { return nil }
        return device.makeBuffer(bytes: contents.withUnsafeBytes { $0.baseAddress! },
                                 length: contents.count,
                                 options: .storageModeShared)
    }

    public func synchronize() {
        // Shared Apple-Silicon memory does not require an explicit blit for CPU/GPU
        // visibility. Keeping this method explicit gives callers a stable boundary
        // if a future tier requires synchronization.
    }

    public func commitEmptyWork() -> Bool {
        guard let commandBuffer = queue.makeCommandBuffer() else { return false }
        commandBuffer.commit()
        commandBuffer.waitUntilCompleted()
        return commandBuffer.status == .completed
    }
}
#endif
