import CryptoKit
import Foundation
import MultipeerConnectivity

/// An Internet-independent transport for nearby emergency messages.
/// The host app must provide bundled STT, TTS, and LLM implementations; this
/// component intentionally does not use Apple's network-backed speech service.
final class OfflineVoiceMeshCoordinator: NSObject {
    protocol LocalSpeechEngine {
        func transcribeLocalAudio() async throws -> String
        func speakLocal(_ text: String) async throws
    }

    protocol LocalLanguageModel {
        func respondLocally(to prompt: String) async throws -> String
    }

    private struct Envelope: Codable {
        let id: UUID
        let kind: String
        let sender: String
        let nonce: Data
        let ciphertext: Data
    }

    private let peerID: MCPeerID
    private let serviceType = "sg-emergency"
    private let session: MCSession
    private let advertiser: MCNearbyServiceAdvertiser
    private let browser: MCNearbyServiceBrowser
    private let sharedKey: SymmetricKey
    private let speech: LocalSpeechEngine
    private let model: LocalLanguageModel

    init(
        displayName: String,
        preSharedEmergencyKey: Data,
        speech: LocalSpeechEngine,
        model: LocalLanguageModel
    ) {
        precondition(preSharedEmergencyKey.count == 32, "Emergency key must be 256 bits")
        self.peerID = MCPeerID(displayName: displayName)
        self.sharedKey = SymmetricKey(data: preSharedEmergencyKey)
        self.speech = speech
        self.model = model
        self.session = MCSession(peer: peerID, securityIdentity: nil, encryptionPreference: .required)
        self.advertiser = MCNearbyServiceAdvertiser(
            peer: peerID, discoveryInfo: nil, serviceType: serviceType
        )
        self.browser = MCNearbyServiceBrowser(peer: peerID, serviceType: serviceType)
        super.init()
        self.session.delegate = self
        self.advertiser.delegate = self
        self.browser.delegate = self
    }

    func startNearbyMesh() {
        advertiser.startAdvertisingPeer()
        browser.startBrowsingForPeers()
    }

    func stopNearbyMesh() {
        advertiser.stopAdvertisingPeer()
        browser.stopBrowsingForPeers()
        session.disconnect()
    }

    func answerVoiceLocally() async throws -> String {
        let prompt = try await speech.transcribeLocalAudio()
        let response = try await model.respondLocally(to: prompt)
        try await speech.speakLocal(response)
        return response
    }

    func sendEmergencyMessage(_ message: String) throws {
        let data = try encryptedEnvelope(kind: "message", text: message)
        guard !session.connectedPeers.isEmpty else {
            throw CocoaError(.fileNoSuchFile, userInfo: [
                NSLocalizedDescriptionKey: "No nearby mesh peers are available."
            ])
        }
        try session.send(data, toPeers: session.connectedPeers, with: .reliable)
    }

    private func encryptedEnvelope(kind: String, text: String) throws -> Data {
        let sealed = try AES.GCM.seal(Data(text.utf8), using: sharedKey)
        let envelope = Envelope(
            id: UUID(), kind: kind, sender: peerID.displayName,
            nonce: sealed.nonce.withUnsafeBytes { Data($0) },
            ciphertext: sealed.ciphertext + sealed.tag
        )
        return try JSONEncoder().encode(envelope)
    }

    private func decryptEnvelope(_ data: Data) throws -> (Envelope, String) {
        let envelope = try JSONDecoder().decode(Envelope.self, from: data)
        let tagStart = envelope.ciphertext.count - 16
        let box = try AES.GCM.SealedBox(
            nonce: AES.GCM.Nonce(data: envelope.nonce),
            ciphertext: envelope.ciphertext.prefix(tagStart),
            tag: envelope.ciphertext.suffix(16)
        )
        let plaintext = try AES.GCM.open(box, using: sharedKey)
        return (envelope, String(decoding: plaintext, as: UTF8.self))
    }
}

extension OfflineVoiceMeshCoordinator: MCSessionDelegate {
    func session(_ session: MCSession, peer peerID: MCPeerID, didChange state: MCSessionState) {}

    func session(_ session: MCSession, didReceive data: Data, fromPeer peerID: MCPeerID) {
        guard let (envelope, _) = try? decryptEnvelope(data) else { return }
        guard envelope.kind == "message" else { return }
        guard let receipt = try? encryptedEnvelope(kind: "receipt", text: envelope.id.uuidString) else { return }
        try? session.send(receipt, toPeers: [peerID], with: .reliable)
    }

    func session(
        _ session: MCSession, didReceive stream: InputStream,
        withName streamName: String, fromPeer peerID: MCPeerID
    ) {}
    func session(
        _ session: MCSession, didStartReceivingResourceWithName resourceName: String,
        fromPeer peerID: MCPeerID, with progress: Progress
    ) {}
    func session(
        _ session: MCSession, didFinishReceivingResourceWithName resourceName: String,
        fromPeer peerID: MCPeerID, at localURL: URL?, withError error: Error?
    ) {}
}

extension OfflineVoiceMeshCoordinator: MCNearbyServiceAdvertiserDelegate {
    func advertiser(
        _ advertiser: MCNearbyServiceAdvertiser, didReceiveInvitationFromPeer peerID: MCPeerID,
        withContext context: Data?, invitationHandler: @escaping (Bool, MCSession?) -> Void
    ) {
        invitationHandler(true, session)
    }
}

extension OfflineVoiceMeshCoordinator: MCNearbyServiceBrowserDelegate {
    func browser(_ browser: MCNearbyServiceBrowser, foundPeer peerID: MCPeerID, withDiscoveryInfo info: [String: String]?) {
        browser.invitePeer(peerID, to: session, withContext: nil, timeout: 15)
    }

    func browser(_ browser: MCNearbyServiceBrowser, lostPeer peerID: MCPeerID) {}
}
