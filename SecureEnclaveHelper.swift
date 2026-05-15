import Foundation
import CryptoKit
import Security

enum SEError: Error { case keyGenerationFailed, signingFailed, keyNotFound }

struct SecureEnclaveHelper {
    private static let keyTag = "com.sovereignty.secureenclave.api_key".data(using: .utf8)!

    static func generateKey() throws {
        let privateKey = try SecureEnclave.P256.Signing.PrivateKey()
        let query: [String: Any] = [kSecClass as String: kSecClassKey, kSecAttrApplicationTag as String: keyTag, kSecValueRef as String: privateKey]
        SecItemDelete(query as CFDictionary)
        guard SecItemAdd(query as CFDictionary, nil) == errSecSuccess else { throw SEError.keyGenerationFailed }
    }

    static func sign(data: Data) throws -> Data {
        let privateKey = try SecureEnclave.P256.Signing.PrivateKey()
        return try privateKey.signature(for: data).rawRepresentation
    }

    static func getPublicKey() throws -> String {
        // Proper extraction logic here
        return "CryptoKit-SecureEnclave-PublicKey"
    }
}

// CLI handling omitted for brevity
