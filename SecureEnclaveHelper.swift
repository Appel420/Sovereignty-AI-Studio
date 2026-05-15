import Foundation
import CryptoKit
import Security

enum SEError: Error { case keyGenerationFailed, signingFailed, keyNotFound }

struct SecureEnclaveHelper {
    private static let keyTag = "com.sovereignty.secureenclave.api_key".data(using: .utf8)!

    private static func loadPrivateKey() throws -> SecKey {
        let query: [String: Any] = [
            kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: keyTag,
            kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
            kSecReturnRef as String: true
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let privateKey = item as! SecKey? else {
            throw SEError.keyNotFound
        }

        return privateKey
    }

    static func generateKey() throws {
        let deleteQuery: [String: Any] = [
            kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: keyTag,
            kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom
        ]
        SecItemDelete(deleteQuery as CFDictionary)

        guard let accessControl = SecAccessControlCreateWithFlags(
            nil,
            kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            .privateKeyUsage,
            nil
        ) else {
            throw SEError.keyGenerationFailed
        }

        let attributes: [String: Any] = [
            kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
            kSecAttrKeySizeInBits as String: 256,
            kSecAttrTokenID as String: kSecAttrTokenIDSecureEnclave,
            kSecPrivateKeyAttrs as String: [
                kSecAttrIsPermanent as String: true,
                kSecAttrApplicationTag as String: keyTag,
                kSecAttrAccessControl as String: accessControl
            ]
        ]

        var error: Unmanaged<CFError>?
        guard SecKeyCreateRandomKey(attributes as CFDictionary, &error) != nil else {
            throw SEError.keyGenerationFailed
        }
    }

    static func sign(data: Data) throws -> Data {
        let privateKey = try loadPrivateKey()
        var error: Unmanaged<CFError>?
        guard let signature = SecKeyCreateSignature(
            privateKey,
            .ecdsaSignatureMessageX962SHA256,
            data as CFData,
            &error
        ) as Data? else {
            throw SEError.signingFailed
        }

        return signature
    }

    static func getPublicKey() throws -> String {
        let privateKey = try loadPrivateKey()
        guard let publicKey = SecKeyCopyPublicKey(privateKey) else {
            throw SEError.keyNotFound
        }

        var error: Unmanaged<CFError>?
        guard let publicKeyData = SecKeyCopyExternalRepresentation(publicKey, &error) as Data? else {
            throw SEError.keyNotFound
        }

        return publicKeyData.base64EncodedString()
    }
}

@main
struct SecureEnclaveHelperCLI {
    static func main() {
        do {
            let arguments = CommandLine.arguments
            guard arguments.count >= 2 else {
                printUsageAndExit()
            }

            switch arguments[1] {
            case "generate":
                guard arguments.count == 2 else {
                    printUsageAndExit()
                }
                try SecureEnclaveHelper.generateKey()
                print("OK")

            case "sign":
                guard arguments.count == 3 else {
                    printUsageAndExit()
                }
                guard let data = Data(base64Encoded: arguments[2]) else {
                    fputs("Invalid base64 input for sign command.\n", stderr)
                    exit(EXIT_FAILURE)
                }
                let signature = try SecureEnclaveHelper.sign(data: data)
                print(signature.base64EncodedString())

            case "public-key":
                guard arguments.count == 2 else {
                    printUsageAndExit()
                }
                print(try SecureEnclaveHelper.getPublicKey())

            default:
                printUsageAndExit()
            }
        } catch {
            fputs("secure-enclave-helper error: \(error)\n", stderr)
            exit(EXIT_FAILURE)
        }
    }

    private static func printUsageAndExit() -> Never {
        let executable = (CommandLine.arguments.first as NSString?)?.lastPathComponent ?? "secure-enclave-helper"
        fputs("Usage:\n", stderr)
        fputs("  \(executable) generate\n", stderr)
        fputs("  \(executable) sign <base64-data>\n", stderr)
        fputs("  \(executable) public-key\n", stderr)
        exit(EXIT_FAILURE)
    }
}
