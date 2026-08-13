/**
 * Local voice capture helpers.
 *
 * This module only captures microphone data on the device. Uploading is a
 * separate explicit step owned by the caller, which can enforce a loopback-only
 * endpoint and local/offline policy before sending anything.
 */

export interface LocalRecording {
  blob: Blob;
  mimeType: string;
}

export interface LocalRecordingController {
  readonly mimeType: string;
  readonly result: Promise<LocalRecording>;
  stop: () => void;
  cancel: () => void;
}

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

export async function startLocalRecording(): Promise<LocalRecordingController> {
  if (!supportsLocalRecording()) {
    throw new Error('Local microphone recording is unavailable in this browser.');
  }

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream);
  const chunks: Blob[] = [];
  const mimeType = recorder.mimeType || 'audio/webm';
  let settled = false;
  let rejectResult: (reason?: unknown) => void = () => undefined;

  const result = new Promise<LocalRecording>((resolve, reject) => {
    rejectResult = reject;
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data);
    };
    recorder.onerror = () => {
      if (settled) return;
      settled = true;
      stream.getTracks().forEach((track) => track.stop());
      reject(new Error('Local microphone recording failed.'));
    };
    recorder.onstop = () => {
      if (settled) return;
      settled = true;
      stream.getTracks().forEach((track) => track.stop());
      resolve({ blob: new Blob(chunks, { type: mimeType }), mimeType });
    };
    recorder.start();
  });

  const cancel = () => {
    if (settled) return;
    if (recorder.state !== 'inactive') recorder.stop();
    settled = true;
    stream.getTracks().forEach((track) => track.stop());
    rejectResult(new DOMException('Recording cancelled.', 'AbortError'));
  };

  return {
    mimeType,
    result,
    stop: () => {
      if (!settled && recorder.state !== 'inactive') recorder.stop();
    },
    cancel,
  };
}

/** Compatibility helper for callers that want capture-to-completion. */
export async function recordLocalAudio(
  _onChunk?: (chunk: Blob) => void,
  signal?: AbortSignal,
): Promise<LocalRecording> {
  if (!signal) {
    throw new Error('recordLocalAudio requires an AbortSignal; use startLocalRecording() for manual control.');
  }

  const controller = await startLocalRecording();

  if (signal.aborted) {
    controller.cancel();
    throw new DOMException('Recording cancelled.', 'AbortError');
  }

  const stop = () => controller.stop();
  signal.addEventListener('abort', stop, { once: true });
  try {
    return await controller.result;
  } finally {
    signal.removeEventListener('abort', stop);
  }
}
