/**
 * Central API client for Sovereignty AI Studio.
 * Local voice calls are explicitly loopback-only; no remote speech fallback is
 * permitted by this adapter.
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:9898/api/v1';
const BRIDGE_BASE_URL = API_BASE_URL.replace(/\/api\/v1$/, '');

function isLoopbackOrigin(value: string): boolean {
  try {
    const hostname = new URL(value).hostname;
    return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1';
  } catch {
    return false;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token');

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => response.statusText);
    throw new Error(`API Error ${response.status}: ${errorBody}`);
  }

  return response.json();
}

async function localMultipart<T>(endpoint: string, form: FormData): Promise<T> {
  if (!isLoopbackOrigin(API_BASE_URL)) {
    throw new Error('Local voice routing refused: API endpoint is not loopback.');
  }

  const token = localStorage.getItem('access_token');
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    body: form,
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => response.statusText);
    throw new Error(`Local voice API Error ${response.status}: ${errorBody}`);
  }

  return response.json();
}

export const HealthAPI = {
  check: () => request<{ status: string }>('/status'),
  bridgeHealth: () => fetch(`${BRIDGE_BASE_URL}/health`).then((r) => r.json()),
  bridgeStatus: () => fetch(`${BRIDGE_BASE_URL}/api/bridge/status`).then((r) => r.json()),
};

export const VoiceAPI = {
  chat: (text: string, voice_model?: string) =>
    request<{
      input: string;
      response: string;
      audio_file: string | null;
      status: string;
    }>('/voice/chat', {
      method: 'POST',
      body: JSON.stringify({ text, voice_model }),
    }),

  speak: (text: string) =>
    request<{ status: string; message: string; audio_file: string | null }>(
      '/voice/speak',
      { method: 'POST', body: JSON.stringify({ text }) },
    ),

  input: (audio: Blob, filename = 'voice.webm') => {
    const form = new FormData();
    form.append('audio', audio, filename);
    form.append('process_after_transcription', 'true');
    return localMultipart<import('../lib/localVoice').VoiceInputResult>('/voice/input', form);
  },

  status: () => request<{ piper_tts: object; voice_models: string[]; status: string }>('/voice/status'),
};

export const AvatarAPI = {
  getState: () => request<Record<string, unknown>>('/avatar/state'),
  interact: (message: string) => request<{ response: string; mood: string; expression: string }>(
    '/avatar/interact', { method: 'POST', body: JSON.stringify({ message }) },
  ),
  updateMood: (mood: string) => request<Record<string, unknown>>('/avatar/mood', {
    method: 'PUT', body: JSON.stringify({ mood }),
  }),
  toggleEEGLink: (enabled: boolean) => request<Record<string, unknown>>('/avatar/eeg-link', {
    method: 'POST', body: JSON.stringify({ enabled }),
  }),
};

export const MediaAPI = {
  generate: (user_id: string, media_type: string, prompt: string) => request<Record<string, unknown>>(
    '/studio/media/generate', { method: 'POST', body: JSON.stringify({ user_id, media_type, prompt }) },
  ),
  getJob: (jobId: string) => request<Record<string, unknown>>(`/studio/media/job/${jobId}`),
  list: (file_type?: string) => request<Array<Record<string, unknown>>>(
    `/media${file_type ? `?file_type=${file_type}` : ''}`,
  ),
};

export const MusicAPI = {
  compose: (prompt: string, genre: string, duration_seconds: number, bpm?: number) => request<Record<string, unknown>>(
    '/music/compose', { method: 'POST', body: JSON.stringify({ prompt, genre, duration_seconds, bpm }) },
  ),
  list: () => request<Array<Record<string, unknown>>>('/music'),
  genres: () => request<{ genres: Record<string, unknown>[] }>('/music/genres'),
};

export const GenerationAPI = {
  create: (generation_type: string, prompt: string, parameters?: Record<string, unknown>, project_id?: number) =>
    request<{ id: number; status: string; generation_type: string; message: string }>('/generation/', {
      method: 'POST', body: JSON.stringify({ generation_type, prompt, parameters, project_id }),
    }),
  list: (generation_type?: string) => request<Array<Record<string, unknown>>>(
    `/generation${generation_type ? `?generation_type=${generation_type}` : ''}`,
  ),
  get: (id: number) => request<Record<string, unknown>>(`/generation/${id}`),
  supportedTypes: () => request<{ types: Record<string, unknown> }>('/generation/types/supported'),
};

export const ProjectAPI = {
  create: (user_id: string, name: string, project_type: string) => request<Record<string, unknown>>(
    '/studio/dashboard/project', { method: 'POST', body: JSON.stringify({ user_id, name, project_type }) },
  ),
  build: (projectId: string) => request<Record<string, unknown>>(`/studio/dashboard/build/${projectId}`, { method: 'POST' }),
  status: () => request<Record<string, unknown>>('/studio/dashboard/status'),
};

export const SyntaxAPI = {
  check: (code: string, filename?: string) => request<Record<string, unknown>>(
    '/syntax/check', { method: 'POST', body: JSON.stringify({ code, filename }) },
  ),
  colors: () => request<{ colors: Record<string, unknown> }>('/syntax/colors'),
};
