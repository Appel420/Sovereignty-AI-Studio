import React, { useRef, useState } from 'react';
import { SpeakerWaveIcon, MicrophoneIcon, StopIcon } from '@heroicons/react/24/outline';
import { VoiceAPI } from '../services/api';
import { containsCode, narrationText, type NarrationMode } from '../lib/codeNarration';
import { startLocalRecording, supportsLocalRecording, type LocalRecordingController } from '../lib/localVoice';

interface VoiceMessage {
  role: 'user' | 'assistant';
  text: string;
}

const VoiceChat: React.FC = () => {
  const [message, setMessage] = useState('');
  const [history, setHistory] = useState<VoiceMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [speaking, setSpeaking] = useState<number | null>(null);
  const [recording, setRecording] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState('LOCAL VOICE: READY');
  const recorderRef = useRef<LocalRecordingController | null>(null);

  const playAudio = async (audioFile: string | null) => {
    if (!audioFile) return;
    const audio = new Audio(audioFile);
    await audio.play();
  };

  const speak = async (text: string, index: number, mode: NarrationMode) => {
    if (!text.trim()) return;
    setSpeaking(index);
    try {
      const result = await VoiceAPI.speak(narrationText(text, mode));
      if (result.audio_file) await playAudio(result.audio_file);
    } finally {
      setSpeaking(null);
    }
  };

  const appendAssistantResponse = async (response: string, audioFile: string | null = null) => {
    if (!response.trim()) return;
    setHistory((prev) => [...prev, { role: 'assistant', text: response }]);
    if (audioFile) {
      try {
        await playAudio(audioFile);
      } catch {
        setVoiceStatus('SPEAKER: UNAVAILABLE');
      }
    }
  };

  const handleSend = async () => {
    if (!message.trim() || loading) return;
    const userMsg = message.trim();
    setHistory((prev) => [...prev, { role: 'user', text: userMsg }]);
    setMessage('');
    setLoading(true);
    setVoiceStatus('LOCAL RESPONSE: PROCESSING');

    try {
      const data = await VoiceAPI.chat(userMsg);
      await appendAssistantResponse(data.response, data.audio_file);
      setVoiceStatus(data.audio_file ? 'LOCAL STT: READY · PIPER: READY' : 'LOCAL STT: READY · PIPER: UNAVAILABLE');
    } catch {
      await appendAssistantResponse('Local voice service is unavailable. No remote fallback was attempted.');
      setVoiceStatus('LOCAL VOICE: UNAVAILABLE · REMOTE FALLBACK: DISABLED');
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    if (!supportsLocalRecording() || recording || loading) {
      setVoiceStatus('MICROPHONE: UNAVAILABLE');
      return;
    }

    try {
      const controller = await startLocalRecording();
      recorderRef.current = controller;
      setRecording(true);
      setVoiceStatus('MICROPHONE: LISTENING · NETWORK: NONE');

      controller.result.then(async ({ blob, mimeType }) => {
        if (!blob.size) {
          setVoiceStatus('MICROPHONE: EMPTY RECORDING');
          return;
        }
        setLoading(true);
        setVoiceStatus('LOCAL STT: PROCESSING');
        try {
          const result = await VoiceAPI.input(blob, `voice.${mimeType.includes('mp4') ? 'mp4' : 'webm'}`);
          const transcript = result.transcription?.text?.trim();
          if (transcript) setHistory((prev) => [...prev, { role: 'user', text: transcript }]);
          const response = result.processing?.response?.trim();
          if (response) await appendAssistantResponse(response, result.processing?.audio_file || null);
          setVoiceStatus(response ? 'LOCAL VOICE: READY' : 'LOCAL STT: READY · PIPER: UNAVAILABLE');
        } catch {
          await appendAssistantResponse('Local voice processing failed. No remote fallback was attempted.');
          setVoiceStatus('LOCAL VOICE: ERROR · REMOTE FALLBACK: DISABLED');
        } finally {
          setLoading(false);
        }
      }).catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        setVoiceStatus('MICROPHONE: ERROR');
      }).finally(() => {
        recorderRef.current = null;
        setRecording(false);
      });
    } catch {
      setVoiceStatus('MICROPHONE: PERMISSION OR DEVICE ERROR');
    }
  };

  const stopRecording = () => {
    recorderRef.current?.stop();
    setVoiceStatus('LOCAL STT: QUEUED');
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <div className="flex justify-center items-center mb-4">
          <SpeakerWaveIcon className="h-12 w-12 text-teal-500" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 font-space-grotesk">Voice Chat</h1>
        <p className="text-lg text-gray-600 mt-2">Local voice communication with Ara</p>
        <p className="text-xs text-gray-500 mt-2" role="status" aria-live="polite">{voiceStatus}</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="h-96 overflow-y-auto p-6 space-y-4 bg-gray-50">
          {history.length === 0 && (
            <div className="text-center text-gray-400 mt-20">
              <SpeakerWaveIcon className="h-16 w-16 mx-auto mb-4 opacity-30" />
              <p>Start a local conversation with Ara</p>
              <p className="text-sm mt-1">Remote STT, TTS, and memory fallback are disabled.</p>
            </div>
          )}
          {history.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-xs md:max-w-md px-4 py-3 rounded-2xl ${msg.role === 'user' ? 'bg-primary-600 text-white' : 'bg-white border border-gray-200 text-gray-900'}`}>
                {msg.role === 'assistant' && <span className="text-xs font-medium text-teal-600 block mb-1">🔊 Ara</span>}
                <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                {msg.role === 'assistant' && (
                  <div className="mt-3 flex flex-wrap gap-2" aria-label="Voice narration actions">
                    <button type="button" onClick={() => speak(msg.text, i, 'read')} disabled={speaking === i} className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-50">
                      {speaking === i ? 'Speaking…' : '▶ Listen'}
                    </button>
                    {containsCode(msg.text) && <button type="button" onClick={() => speak(msg.text, i, 'explain-code')} disabled={speaking === i} className="text-xs px-2 py-1 rounded border border-teal-300 text-teal-700 hover:bg-teal-50 disabled:opacity-50">🧠 Explain code</button>}
                    <button type="button" onClick={() => speak(msg.text, i, 'summarize')} disabled={speaking === i} className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-50">Summarize implementation</button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="p-4 border-t border-gray-200 bg-white space-y-3">
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={recording ? stopRecording : startRecording} disabled={loading} className="px-5 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors font-medium disabled:opacity-50 flex items-center gap-2">
              {recording ? <StopIcon className="h-5 w-5" /> : <MicrophoneIcon className="h-5 w-5" />}
              {recording ? 'Stop voice' : 'Start voice'}
            </button>
            <span className="text-xs text-gray-500 self-center">Device-local capture · no remote fallback</span>
          </div>
          <div className="flex space-x-3">
            <input type="text" value={message} onChange={(e) => setMessage(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSend()} placeholder="Type a message or use Start voice…" className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
            <button onClick={handleSend} disabled={loading} className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium disabled:opacity-50">{loading ? '...' : 'Send'}</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VoiceChat;
