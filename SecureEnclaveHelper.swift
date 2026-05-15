import Foundation

#if canImport(Security)
import Security

enum SEError: Error, LocalizedError {
    case keyGenerationFailed(String)
    case signingFailed(String)
    case keyNotFound
    case invalidArguments

    var errorDescription: String? {
        switch self {
        case .keyGenerationFailed(let message):
            return "Secure Enclave key generation failed: \(message)"
        case .signingFailed(let message):
            return "Secure Enclave signing failed: \(message)"
        case .keyNotFound:
            return "Secure Enclave key not found. Run `secure-enclave-helper generate` first."
        case .invalidArguments:
            return "Usage: secure-enclave-helper <generate|sign|public-key> [payload]"
        }
    }
}

struct SecureEnclaveHelper {
    private static let keyTag = "com.sovereignty.secureenclave.api_key".data(using: .utf8)!

    private static func existingPrivateKey() throws -> SecKey {
        let query: [String: Any] = [
            kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: keyTag,
            kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
            kSecReturnRef as String: true,
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let key = item as? SecKey else {
            throw SEError.keyNotFound
        }
        return key
    }

    static func generateKey() throws {
        if (try? existingPrivateKey()) != nil {
            return
        }

        guard let accessControl = SecAccessControlCreateWithFlags(
            nil,
            kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            [.privateKeyUsage],
            nil
        ) else {
            throw SEError.keyGenerationFailed("unable to configure access control")
        }

        let attributes: [String: Any] = [
            kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
            kSecAttrKeySizeInBits as String: 256,
            kSecAttrTokenID as String: kSecAttrTokenIDSecureEnclave,
            kSecPrivateKeyAttrs as String: [
                kSecAttrIsPermanent as String: true,
                kSecAttrApplicationTag as String: keyTag,
                kSecAttrAccessControl as String: accessControl,
            ],
        ]

        var error: Unmanaged<CFError>?
        guard SecKeyCreateRandomKey(attributes as CFDictionary, &error) != nil else {
            let message = (error?.takeRetainedValue() as Error?)?.localizedDescription ?? "unknown error"
            throw SEError.keyGenerationFailed(message)
        }
    }

    static func sign(data: Data) throws -> Data {
        let privateKey = try existingPrivateKey()
        var error: Unmanaged<CFError>?
        guard let signature = SecKeyCreateSignature(
            privateKey,
            .ecdsaSignatureMessageX962SHA256,
            data as CFData,
            &error
        ) as Data? else {
            let message = (error?.takeRetainedValue() as Error?)?.localizedDescription ?? "unknown error"
            throw SEError.signingFailed(message)
        }
        return signature
    }

    static func getPublicKey() throws -> String {
        let publicKey = SecKeyCopyPublicKey(try existingPrivateKey())
        var error: Unmanaged<CFError>?
        guard let data = SecKeyCopyExternalRepresentation(publicKey, &error) as Data? else {
            let message = (error?.takeRetainedValue() as Error?)?.localizedDescription ?? "unknown error"
            throw SEError.keyGenerationFailed(message)
        }
        return data.base64EncodedString()
    }
}

do {
    let args = Array(CommandLine.arguments.dropFirst())
    guard let command = args.first else {
        throw SEError.invalidArguments
    }

    switch command {
    case "generate":
        try SecureEnclaveHelper.generateKey()
        print(try SecureEnclaveHelper.getPublicKey())
    case "sign":
        guard args.count >= 2 else {
            throw SEError.invalidArguments
        }
        try SecureEnclaveHelper.generateKey()
        let payload = args.dropFirst().joined(separator: " ")
        print(try SecureEnclaveHelper.sign(data: Data(payload.utf8)).base64EncodedString())
    case "public-key":
        try SecureEnclaveHelper.generateKey()
        print(try SecureEnclaveHelper.getPublicKey())
    default:
        throw SEError.invalidArguments
    }
} catch {
    fputs("\((error as? LocalizedError)?.errorDescription ?? error.localizedDescription)\n", stderr)
    Foundation.exit(1)
}
#else
fputs("Secure Enclave helper requires macOS with the Security framework.\n", stderr)
Foundation.exit(1)
#endif
