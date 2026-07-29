// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "SovereigntyGuard",
    platforms: [.iOS(.v16)],
    products: [
        .library(name: "SovereigntyGuard", targets: ["SovereigntyGuard"])
    ],
    targets: [
        .target(name: "SovereigntyGuard", path: "Sources/SovereigntyGuard"),
        .testTarget(
            name: "SovereigntyGuardTests",
            dependencies: ["SovereigntyGuard"],
            path: "Tests/SovereigntyGuardTests"
        )
    ]
)
