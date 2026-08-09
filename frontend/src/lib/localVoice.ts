/**
 * Local voice transport helpers.
 *
 * Audio is captured in the browser and sent to the local voice endpoint as a
 * multipart upload. The backend owns transcription and may use a bundled local
 * STT implementation. This module never calls a remote speech provider.
 */

export interface VoiceInputResult {
  status: string;
  transcription?: {
    status?: string;
    text?: string;
    [key: string]: unknown;
  };
  processing?: {
    response?: string;
    audio_file?: string | null;
    [key: string]: unknown;
  };
  offline?: boolean;
  [key: string]: unknown;
}

export function supportsLocalRecording(): boolean {
  return typeof navigator !== 'undefined'
    && Boolean(navigator.mediaDevices?.getUserMedia)
    && typeof MediaRecorder !== 'undefined';
}

export async function recordLocalAudio(
  onChunk: (chunk: Blob) => void,
  signal?: AbortSignal,
): Promise<{ blob: Blob; mimeType: string }> {
  if (!supportsLocalRecording()) {
    throw new Error('Local microphone recording is unavailable in this browser.');
  }

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream);
  const chunks: Blob[] = [];

  return new Promise((resolve, reject) => {
    const cleanup = () => {
      stream.getTracks().forEach((track) => track.stop());
      signal?.removeEventListener('abort', abort);
    };

    const abort = () => {
      if (recorder.state !== 'inactive') recorder.stop();
      cleanup();
      reject(new DOMException('Recording cancelled.', 'AbortError'));
    };

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
        onChunk(event.data);
      }
    };
    recorder.onerror = () => {
      cleanup();
      reject(new Error('Local microphone recording failed.'));
    };
    recorder.onstop = () => {
      cleanup();
      const mimeType = recorder.mimeType || 'audio/webm';
      resolve({ blob: new Blob(chunks, { type: mimeType }), mimeType });
    };

    signal?.addEventListener('abort', abort, { once: true });
    recorder.start();
  });
}
